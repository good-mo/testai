"""用例应用服务（Application Service / Use Case 门面）。

职责：
  1. 作为路由器与领域层之间的唯一用例编排入口；
  2. 承载"用例"用例的事务边界：加载聚合 → 执行领域命令 → 保存聚合 →
     发布领域事件 → 驱动审计日志/版本快照/缓存失效等副作用；
  3. 将领域异常透传给上层（由 Web 层统一翻译为 HTTP 响应）。

保持瘦：只做编排，不写业务规则（业务规则在领域层聚合内）。
"""
from __future__ import annotations

import logging
from typing import List, Optional

from app.domain.cases.application.dto import (
    ChangeStatusCommand,
    CreateCaseCommand,
    DeleteCaseCommand,
    ListQuery,
    RestoreCaseCommand,
    ReviewCommand,
    UpdateCaseCommand,
)
from app.domain.cases.domain.entities.case import TestCase
from app.domain.cases.domain.repository import CaseRepository
from app.domain.cases.infrastructure.case_repository_impl import case_repository
from app.domain.common.domain_events import DomainEvent, event_bus

logger = logging.getLogger(__name__)

# 审计动作常量（对齐既有 case_change_logs）
_ACT_CREATED = "created"
_ACT_UPDATED = "updated"
_ACT_DELETED = "deleted"
_ACT_RESTORED = "restored"
_ACT_REVIEW = "review_submitted"

class CaseAppService:
    """测试用例用例编排服务。"""

    def __init__(self, repo: CaseRepository = None):
        # 允许依赖注入（便于测试替身）；默认使用 DDD Repository
        self._repo: CaseRepository = repo or case_repository

    # ── 聚合级基础操作 ─────────────────────────────
    def create(self, cmd: CreateCaseCommand) -> dict:
        """创建用例聚合：建聚合 → 保存 → 发布事件 → 落版本/审计。"""
        case = TestCase(
            case_id=cmd.case_id or self._repo.next_id(),
            title=cmd.title,
            status=cmd.status,
            description=cmd.description,
            source_code=cmd.source_code,
            test_code=cmd.test_code,
            file_path=cmd.file_path,
            tags=cmd.tags,
            priority=cmd.priority,
            requirement_ref=cmd.requirement_ref,
            test_type=cmd.test_type,
            structured_cases=cmd.structured_cases,
            metadata=cmd.metadata,
        )
        self._repo.save(case)
        try:
            self._repo.record_change(case.id.value, _ACT_CREATED,
                                     field="title", new_value=case.title,
                                     operator=cmd.operator)
            self._repo.create_version(case.id.value, case.snapshot(), 1,
                                      operator=cmd.operator, change_desc="初始版本")
            self._repo.invalidate_mindmap_cache()
        except Exception as exc:  # 副作用失败不影响主流程
            logger.warning("create 副作用失败 [case=%s, err=%s]", case.id.value, exc)
        return case.to_dict()

    def get(self, case_id: str) -> Optional[dict]:
        case = self._find_or_none(case_id)
        return case.to_dict() if case else None

    def update(self, cmd: UpdateCaseCommand) -> Optional[dict]:
        """更新聚合并记录字段级审计 + 版本快照。"""
        case = self._find_or_raise(cmd.case_id)
        before = case.to_dict()

        def _diff(attr):
            return str(before.get(attr, ""))

        if cmd.metadata is not None:
            meta_merge = dict(cmd.metadata)
            case._metadata.update(meta_merge)
            case._touch()

        case.set_content(
            source_code=cmd.source_code if cmd.source_code is not None else None,
            test_code=cmd.test_code if cmd.test_code is not None else None,
            file_path=cmd.file_path if cmd.file_path is not None else None,
            tags=cmd.tags,
            structured_cases=cmd.structured_cases,
            requirement_ref=cmd.requirement_ref,
        )
        if cmd.title is not None:
            case.rename(cmd.title, cmd.operator)
        if cmd.description is not None:
            case.change_description(cmd.description, cmd.operator)
        if cmd.priority is not None:
            case.change_priority(cmd.priority)
        if cmd.test_type is not None:
            case.change_test_type(cmd.test_type)
        if cmd.status is not None and str(cmd.status) != before.get("status", ""):
            case.change_status(str(cmd.status), cmd.operator)

        self._repo.update(case)
        self._publish(case)
        try:
            after = case.to_dict()
            for k in ("title", "description", "source_code", "test_code",
                      "file_path", "priority", "test_type", "requirement_ref"):
                ov = _diff(k)
                nv = str(after.get(k, ""))
                if ov != nv:
                    self._repo.record_change(case.id.value, _ACT_UPDATED,
                                             field=k, old_value=ov, new_value=nv,
                                             operator=cmd.operator)
            if cmd.status is not None and str(cmd.status) != before.get("status", ""):
                self._repo.record_change(case.id.value, _ACT_UPDATED,
                                         field="status",
                                         old_value=before.get("status", ""),
                                         new_value=case.status.value.value,
                                         operator=cmd.operator)
            self._repo.create_version(case.id.value, case.snapshot(), case.version,
                                      operator=cmd.operator, change_desc="用例更新")
            self._repo.invalidate_mindmap_cache()
        except Exception as exc:
            logger.warning("update 副作用失败 [case=%s, err=%s]", case.id.value, exc)
        return case.to_dict()

    def change_status(self, cmd: ChangeStatusCommand) -> Optional[dict]:
        case = self._find_or_raise(cmd.case_id)
        case.change_status(cmd.target_status, cmd.operator)
        self._repo.update(case)
        self._publish(case)
        try:
            self._repo.create_version(case.id.value, case.snapshot(), case.version,
                                      operator=cmd.operator, change_desc="状态变更")
            self._repo.invalidate_mindmap_cache()
        except Exception as exc:
            logger.warning("status 副作用失败 [%s, %s]", case.id.value, exc)
        return case.to_dict()

    def submit_review(self, cmd: ReviewCommand) -> Optional[dict]:
        """提交评审（草稿→评审中）。"""
        case = self._find_or_raise(cmd.case_id)
        case.submit_for_review(reviewer=cmd.reviewer, operator=cmd.operator)
        self._repo.update(case)
        self._publish(case)
        try:
            self._repo.record_change(case.id.value, _ACT_REVIEW,
                                     new_value="pending", operator=cmd.operator)
            self._repo.submit_review_record(case.id.value,
                                            reviewer=cmd.reviewer,
                                            comment=cmd.comment)
        except Exception as exc:
            logger.warning("submit_review 副作用失败 [%s]", exc)
        return case.to_dict()

    def review(self, cmd: ReviewCommand) -> Optional[dict]:
        """处理评审结论（approve/reject/need_revise）。"""
        case = self._find_or_raise(cmd.case_id)
        case.review(outcome=cmd.outcome, reviewer=cmd.reviewer, comment=cmd.comment)
        self._repo.update(case)
        self._publish(case)
        try:
            action = f"review_{cmd.outcome}"
            self._repo.record_change(case.id.value, action,
                                     new_value=cmd.outcome, operator=cmd.operator)
            if cmd.outcome == "approved":
                self._repo.approve_review_record(case.id.value,
                                                 reviewer=cmd.reviewer,
                                                 comment=cmd.comment)
            elif cmd.outcome == "rejected":
                self._repo.reject_review_record(case.id.value,
                                                reviewer=cmd.reviewer,
                                                comment=cmd.comment,
                                                review_status="rejected")
            elif cmd.outcome == "need_revise":
                self._repo.reject_review_record(case.id.value,
                                                reviewer=cmd.reviewer,
                                                comment=cmd.comment,
                                                review_status="need_revise")
            self._repo.invalidate_mindmap_cache()
        except Exception as exc:
            logger.warning("review 副作用失败 [%s]", exc)
        return case.to_dict()

    def get_reviews(self, case_id: str) -> list:
        """查询用例评审记录。"""
        return self._repo.get_reviews(case_id)

    def soft_delete(self, cmd: DeleteCaseCommand) -> bool:
        case = self._find_or_raise(cmd.case_id)
        case.delete(cmd.operator, cmd.reason)
        self._repo.soft_delete(case.id.value, deleted_by=cmd.operator, reason=cmd.reason)
        self._publish(case)
        try:
            self._repo.invalidate_mindmap_cache()
        except Exception as exc:
            logger.warning("delete 副作用失败 [%s]", exc)
        return True

    def restore(self, cmd: RestoreCaseCommand) -> bool:
        case = self._find_deleted_or_raise(cmd.case_id)
        case.restore(cmd.operator)
        self._repo.restore(case.id.value, operator=cmd.operator)
        self._publish(case)
        try:
            self._repo.invalidate_mindmap_cache()
        except Exception as exc:
            logger.warning("restore 副作用失败 [%s]", exc)
        return True

    # ── 副属方法：关联 / 依赖 ──────────────────────────
    def add_relation(self, case_id: str, related_case_id: str,
                     relation_type: str = "related") -> dict:
        return self._repo.add_relation(case_id, related_case_id, relation_type)

    def remove_relation(self, case_id: str, related_id: str) -> bool:
        return self._repo.remove_relation(case_id, related_id)

    def list_relations(self, case_id: str) -> list:
        return self._repo.list_relations(case_id)

    def add_dependency(self, case_id: str, depends_on: str,
                       dep_type: str = "before", description: str = "") -> dict:
        return self._repo.add_dependency(case_id, depends_on, dep_type, description)

    def remove_dependency(self, case_id: str, depends_on: str) -> bool:
        return self._repo.remove_dependency(case_id, depends_on)

    def list_dependencies(self, case_id: str) -> list:
        return self._repo.list_dependencies(case_id)

    # ── 查询（读模型，返回聚合视图）─────────────────
    def list_cases(self, query: ListQuery) -> dict:
        items, total = self._repo.list_cases(
            status=query.status, priority=query.priority, tag=query.tag,
            search=query.search, test_type=query.test_type,
            module_id=query.module_id, limit=query.limit, offset=query.offset,
        )
        return {"list": [c.to_dict() for c in items], "total": total}

    def list_trash(self, limit: int = 100, offset: int = 0) -> dict:
        items, total = self._repo.list_deleted(limit=limit, offset=offset)
        return {"list": [c.to_dict() for c in items], "total": total}

    # ── 导入 / 导出 ──────────────────────────────────
    def export_excel(self, cases: list) -> bytes:
        return self._repo.export_excel(cases)

    def export_mindmap(self, cases: list = None) -> str:
        return self._repo.export_mindmap(cases)

    def import_excel(self, content: str, operator: str = "") -> dict:
        return self._repo.import_excel(content, operator)

    def import_mindmap(self, content: str, operator: str = "") -> dict:
        return self._repo.import_mindmap(content, operator)

    # ── 旁路方法（统一通过 DDD Repository）──────────────
    def get_stats(self) -> dict:
        """用例统计。"""
        return self._repo.get_stats()

    def update_case_result(self, case_id: str, result: dict) -> Optional[dict]:
        """更新用例最后执行结果。"""
        import json as _json
        case = self._find_or_none(case_id)
        if case is None:
            return None
        return self._repo.update_case(case_id, {"last_result": _json.dumps(result, ensure_ascii=False)})

    def get_mindmap(self, project_filter: str = "") -> dict:
        """获取思维导图。"""
        return self._repo.get_mindmap(project_filter)

    def get_full_info(self, case_id: str) -> Optional[dict]:
        """获取用例完整信息（含版本/评审等聚合视图）。"""
        return self._repo.get_full_info(case_id)

    def hard_delete(self, case_id: str) -> bool:
        """物理删除用例（连同关联子表）。"""
        return self._repo.delete(case_id)

    def purge_case(self, case_id: str) -> bool:
        """从回收站彻底删除用例。"""
        return self._repo.delete(case_id)

    def list_trash_cases(self) -> list:
        """列出回收站用例（原始存储行形态）。"""
        return self._repo.list_trash_cases()

    def list_versions(self, case_id: str) -> list:
        """列出用例版本历史。"""
        return self._repo.list_case_versions(case_id)

    def get_version(self, case_id: str, version: int) -> Optional[dict]:
        """获取指定版本快照。"""
        return self._repo.get_case_version(case_id, version)

    def rollback(self, case_id: str, version: int, operator: str = "") -> bool:
        """回滚到指定版本。"""
        return self._repo.rollback_case(case_id, version, operator=operator)

    def list_changes(self, case_id: str, limit: int = 50) -> list:
        """列出用例变更日志。"""
        return self._repo.list_case_changes(case_id, limit=limit)

    def count_changes(self, case_id: str) -> int:
        """统计用例变更日志数。"""
        return self._repo.count_case_changes(case_id)

    def add_requirement(self, case_id: str, requirement_id: str,
                        requirement_type: str = "jira",
                        requirement_title: str = "",
                        requirement_url: str = "") -> dict:
        """为用例绑定需求。"""
        return self._repo.add_requirement(
            case_id, requirement_id=requirement_id,
            requirement_type=requirement_type,
            requirement_title=requirement_title,
            requirement_url=requirement_url,
        )

    def remove_requirement(self, case_id: str, requirement_id: str) -> bool:
        """移除用例绑定的需求。"""
        return self._repo.remove_requirement(case_id, requirement_id)

    def list_requirements(self, case_id: str) -> list:
        """列出用例绑定的需求。"""
        return self._repo.list_requirements(case_id)

    # ── 内部助手 ────────────────────────────────────
    def _find_or_raise(self, case_id: str) -> TestCase:
        from app.domain.common.exceptions import AggregateNotFound
        case = self._repo.find_by_id(case_id)
        if case is None:
            raise AggregateNotFound(f"用例不存在或已删除: {case_id}")
        return case

    def _find_deleted_or_raise(self, case_id: str) -> TestCase:
        from app.domain.common.exceptions import AggregateNotFound
        case = self._repo.find_deleted(case_id)
        if case is None:
            raise AggregateNotFound(f"回收站中不存在该用例: {case_id}")
        return case

    def _find_or_none(self, case_id: str) -> Optional[TestCase]:
        return self._repo.find_by_id(case_id)

    def _publish(self, case: TestCase) -> None:
        """发布聚合记录的领域事件（事务提交后）。"""
        events: List[DomainEvent] = case.pull_domain_events()
        for ev in events:
            event_bus.dispatch(ev)

# 单例门面（进程内复用）
case_app_service = CaseAppService()
case_service = case_app_service