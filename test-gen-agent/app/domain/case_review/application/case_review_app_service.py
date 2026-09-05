"""用例评审应用服务（Application Service / Use Case 门面）。

职责：
  1. 作为路由器与领域层之间的唯一用例编排入口；
  2. 承载"评审会话"用例的事务边界：加载聚合 → 执行领域命令 → 保存聚合 →
     发布领域事件；
  3. 将领域异常透传给上层（由 Web 层统一翻译为 HTTP 响应）。

保持瘦：只做编排，不写业务规则（业务规则在领域层聚合内）。
"""
from __future__ import annotations

import logging
from typing import List, Optional

from app.domain.case_review.application.dto import (
    CaseReviewListQuery,
    CopyReviewCommand,
    CreateReviewCommand,
    DeleteReviewCommand,
    LinkCasesCommand,
    ToggleFollowCommand,
    UnlinkCasesCommand,
    UpdateLinkResultCommand,
    UpdateReviewCommand,
)
from app.domain.case_review.domain.entities.case_review import CaseReview
from app.domain.case_review.domain.repository import CaseReviewRepository
from app.domain.case_review.infrastructure.case_review_repository_impl import (
    case_review_repo_adapter,
)
from app.domain.common.domain_events import event_bus
from app.domain.common.exceptions import AggregateNotFound

logger = logging.getLogger(__name__)


class CaseReviewAppService:
    """用例评审用例编排服务。"""

    def __init__(self, repo: CaseReviewRepository = None):
        # 允许依赖注入（便于测试替身）；默认使用既有存储适配器
        self._repo: CaseReviewRepository = repo or case_review_repo_adapter

    # ── 聚合级基础操作 ─────────────────────────────
    def create(self, cmd: CreateReviewCommand) -> dict:
        """创建评审会话：建聚合 → 保存 → 关联用例 → 发布事件。"""
        review = CaseReview(
            review_id=self._repo.next_id(),
            name=cmd.name,
            description=cmd.description,
            status=cmd.status,
            module_id=cmd.module_id,
            project_id=cmd.project_id,
            review_pass_rule=cmd.review_pass_rule,
            reviewers=cmd.reviewers,
            tags=cmd.tags,
            start_time=cmd.start_time,
            end_time=cmd.end_time,
            create_user=cmd.operator,
            update_user=cmd.operator,
        )
        self._repo.save(review)
        if cmd.case_ids:
            review.link_cases(cmd.case_ids, cmd.operator)
            self._repo.link_cases(review.id.value, cmd.case_ids)
        self._publish(review)
        return review.to_dict()

    def get(self, review_id: str) -> Optional[dict]:
        review = self._find_or_none(review_id)
        if review is None:
            return None
        return self._to_view(review)

    def get_detail(self, review_id: str) -> Optional[dict]:
        """获取评审完整视图（含统计信息）。"""
        review = self._find_or_none(review_id)
        if review is None:
            return None
        d = review.to_dict()
        d["counts"] = review.get_result_counts()
        return d

    def update(self, cmd: UpdateReviewCommand) -> Optional[dict]:
        """更新评审基本信息（状态走状态机）。"""
        review = self._find_or_raise(cmd.review_id)
        if cmd.name is not None:
            review.rename(cmd.name, cmd.operator)
        if cmd.description is not None:
            review.change_description(cmd.description, cmd.operator)
        if cmd.module_id is not None:
            review.change_module(cmd.module_id, cmd.operator)
        if cmd.project_id is not None:
            review.change_project(cmd.project_id, cmd.operator)
        if cmd.review_pass_rule is not None:
            review.change_pass_rule(cmd.review_pass_rule, cmd.operator)
        if cmd.reviewers is not None:
            review.set_reviewers(cmd.reviewers, cmd.operator)
        if cmd.tags is not None:
            review.set_tags(cmd.tags, cmd.operator)
        if cmd.start_time is not None or cmd.end_time is not None:
            st = cmd.start_time if cmd.start_time is not None else review.start_time
            et = cmd.end_time if cmd.end_time is not None else (review.end_time or 0)
            review.set_time_range(st, et, cmd.operator)
        if cmd.status is not None:
            review.change_status(cmd.status, cmd.operator)
        self._repo.update(review)
        self._publish(review)
        return self._to_view(review)

    def soft_delete(self, cmd: DeleteReviewCommand) -> bool:
        """软删除评审会话。"""
        review = self._find_or_raise(cmd.review_id)
        review.delete(cmd.operator)
        self._repo.soft_delete(cmd.review_id, cmd.operator)
        self._publish(review)
        return True

    def copy(self, cmd: CopyReviewCommand) -> Optional[dict]:
        """复制评审会话（含已关联用例）。"""
        review = self._find_or_raise(cmd.source_id)
        new_review = self._repo.copy(cmd.source_id, cmd.new_name, cmd.operator)
        if new_review is None:
            raise AggregateNotFound(f"评审不存在或已删除: {cmd.source_id}")
        # 产生领域事件，通知副效应
        from app.domain.case_review.domain.events import CaseReviewCopied
        from app.domain.common.domain_events import DomainEvent
        review.record_event(CaseReviewCopied(cmd.source_id, new_review.id.value, cmd.operator))
        self._publish(review)
        return new_review.to_dict()

    def link_cases(self, cmd: LinkCasesCommand) -> dict:
        """向评审关联用例。"""
        review = self._find_or_raise(cmd.review_id)
        review.link_cases(cmd.case_ids, cmd.operator)
        self._repo.link_cases(cmd.review_id, cmd.case_ids)
        self._repo.update(review)
        self._publish(review)
        return review.to_dict()

    def unlink_cases(self, cmd: UnlinkCasesCommand) -> dict:
        """解除评审与用例的关联。"""
        review = self._find_or_raise(cmd.review_id)
        review.unlink_cases(cmd.case_ids, cmd.operator)
        self._repo.unlink_cases(cmd.review_id, cmd.case_ids)
        self._repo.update(review)
        self._publish(review)
        return review.to_dict()

    def update_link_result(self, cmd: UpdateLinkResultCommand) -> dict:
        """批量更新评审中关联用例的评审结论。"""
        review = self._find_or_raise(cmd.review_id)
        updated = review.update_links_result(
            cmd.case_ids, cmd.status,
            reviewer=cmd.reviewer, comment=cmd.comment,
            operator=cmd.operator,
        )
        self._repo.update_link_status(
            cmd.review_id, cmd.case_ids, cmd.status,
            reviewer=cmd.reviewer, comment=cmd.comment,
        )
        self._repo.update(review)
        self._publish(review)
        return {
            "updated": updated,
            "counts": review.get_result_counts(),
        }

    def toggle_follow(self, cmd: ToggleFollowCommand) -> bool:
        """关注/取消关注评审。"""
        return self._repo.toggle_follow(cmd.review_id, cmd.user_id)

    def is_following(self, review_id: str, user_id: str) -> bool:
        """用户是否已关注该评审。"""
        return self._repo.is_following(review_id, user_id)

    # ── 查询（读模型）──────────────────────────────
    def list_reviews(self, query: CaseReviewListQuery) -> dict:
        """分页列出评审会话。"""
        items, total = self._repo.list(
            keyword=query.keyword,
            project_id=query.project_id,
            status=query.status,
            limit=query.limit,
            offset=query.offset,
        )
        return {
            "list": [self._to_view(r) for r in items],
            "total": total,
        }

    def list_link_case_ids(self, review_id: str) -> set:
        """列出评审下已关联用例 id 集合。"""
        return self._repo.list_link_case_ids(review_id)

    def list_links(self, review_id: str) -> list:
        """列出评审关联的用例记录（原始 link 行）。"""
        if not review_id:
            return []
        return self._repo.list_links(review_id)

    def get_status_counts(self, review_id: str) -> dict:
        """评审下用例状态汇总计数。"""
        review = self._find_or_none(review_id)
        if review is None:
            return {"passCount": 0, "unPassCount": 0, "unReviewCount": 0,
                    "underReviewedCount": 0, "reReviewedCount": 0, "reviewedCount": 0}
        return review.get_result_counts()

    def count_by_module(self, project_id: str = "") -> dict:
        """模块下评审数量统计。"""
        return self._repo.count_by_module(project_id)

    # ── 内部助手 ───────────────────────────────────
    def _find_or_raise(self, review_id: str) -> CaseReview:
        review = self._repo.find_by_id(review_id)
        if review is None:
            raise AggregateNotFound(f"评审不存在或已删除: {review_id}")
        return review

    @staticmethod
    def _find_or_none(review_id: str) -> Optional[CaseReview]:
        return case_review_repo_adapter.find_by_id(review_id)

    @staticmethod
    def _to_view(review: CaseReview) -> dict:
        """将聚合转换为对外视图（包含统计信息）。"""
        d = review.to_dict()
        d["counts"] = review.get_result_counts()
        return d

    def _publish(self, review: CaseReview) -> None:
        """发布聚合记录的领域事件。"""
        events = review.pull_domain_events()
        for ev in events:
            event_bus.dispatch(ev)


# 单例门面（进程内复用）
case_review_app_service = CaseReviewAppService()
