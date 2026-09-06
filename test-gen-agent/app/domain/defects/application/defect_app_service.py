"""缺陷应用服务（Application Service / Use Case 门面）。

修复说明：
  - 修改 import：从 DefectRepoAdapter 改为 DefectRepositoryImpl
  - 使用模块级单例 defect_repository

职责：
  1. 作为路由器与领域层之间的用例编排入口；
  2. 承载"缺陷"用例的事务边界：加载聚合 → 执行领域命令 → 保存聚合 →
     发布领域事件；
  3. 将领域异常透传给上层（由 Web 层统一翻译为 HTTP 响应）。

保持瘦：只做编排，不写业务规则（业务规则在领域层聚合内）。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.domain.common.domain_events import event_bus
from app.domain.common.exceptions import AggregateNotFound
from app.domain.defects.application.dto import (
    AutoCreateFromResultCommand,
    ChangeStatusCommand,
    CreateCommentCommand,
    CreateDefectCommand,
    DefectListQuery,
    DeleteCommentCommand,
    ListCommentsQuery,
    PermanentDeleteCommand,
    UpdateCommentCommand,
    UpdateDefectCommand,
)
from app.domain.defects.domain.entities.defect import Defect

# ── 修复：改 import ──────────────────────────────────────────
from app.domain.defects.infrastructure.defect_repository_impl import (
    DefectRepositoryImpl,
    defect_repository,
)

logger = logging.getLogger(__name__)


class DefectAppService:
    """缺陷用例编排服务。"""

    def __init__(self, repo=None):
        # ── 修复：使用新的 Repository 单例 ──────────────────
        self._repo = repo or defect_repository

    # ── 聚合级基础操作 ─────────────────────────────
    def create(self, cmd: CreateDefectCommand) -> dict:
        defect = Defect(
            defect_id=self._repo.next_id(),
            title=cmd.title,
            description=cmd.description,
            severity=cmd.severity,
            status=cmd.status,
            file_path=cmd.file_path,
            test_case_id=cmd.test_case_id,
            error_snippet=cmd.error_snippet,
            assignee=cmd.assignee,
            tags=cmd.tags,
        )
        self._repo.save(defect)
        self._publish(defect)
        return defect.to_dict()

    def get(self, defect_id: str) -> Optional[dict]:
        defect = self._repo.find_by_id(defect_id)
        return defect.to_dict() if defect else None

    def get_or_raise(self, defect_id: str) -> dict:
        defect = self._repo.find_by_id(defect_id)
        if defect is None:
            raise AggregateNotFound(f"缺陷不存在或已删除: {defect_id}")
        return defect.to_dict()

    def update(self, cmd: UpdateDefectCommand) -> Optional[dict]:
        defect = self._find_or_raise(cmd.defect_id)
        if cmd.title is not None:
            defect.rename(cmd.title, cmd.operator)
        if cmd.description is not None:
            defect.change_description(cmd.description, cmd.operator)
        if cmd.severity is not None:
            defect.change_severity(cmd.severity, cmd.operator)
        if cmd.assignee is not None:
            defect.assign(cmd.assignee, cmd.operator)
        if cmd.tags is not None:
            defect.set_tags(cmd.tags, cmd.operator)
        if cmd.file_path is not None:
            defect._file_path = cmd.file_path
            defect._touch()
        if cmd.test_case_id is not None:
            defect._test_case_id = cmd.test_case_id
            defect._touch()
        if cmd.error_snippet is not None:
            defect._error_snippet = cmd.error_snippet
            defect._touch()
        # status 单独走状态机
        if cmd.status is not None and cmd.status != defect.status.value.value:
            defect.change_status(cmd.status, cmd.operator)
        self._repo.update(defect)
        self._publish(defect)
        return defect.to_dict()

    def change_status(self, cmd: ChangeStatusCommand) -> Optional[dict]:
        defect = self._find_or_raise(cmd.defect_id)
        defect.change_status(cmd.target_status, cmd.operator)
        self._repo.update(defect)
        self._publish(defect)
        return defect.to_dict()

    # ── 回收站 ─────────────────────────────────────
    def soft_delete(self, defect_id: str, operator: str = "system") -> bool:
        defect = self._find_or_raise(defect_id)
        defect.delete(operator)
        self._repo.soft_delete(defect_id)
        self._publish(defect)
        return True

    def restore(self, defect_id: str, operator: str = "system") -> bool:
        defect = self._find_deleted_or_raise(defect_id)
        defect.restore(operator)
        self._repo.restore(defect_id)
        self._publish(defect)
        return True

    def purge(self, defect_id: str) -> bool:
        if not self._repo.purge(defect_id):
            raise AggregateNotFound(f"缺陷不存在: {defect_id}")
        return True

    # ── 查询（读模型）──────────────────────────────
    def list(self, query: DefectListQuery) -> dict:
        items, total = self._repo.list(
            status=query.status, severity=query.severity,
            limit=query.limit, offset=query.offset,
        )
        return {"list": [d.to_dict() for d in items], "total": total}

    def list_trash(self, limit: int = 100, offset: int = 0) -> dict:
        items, total = self._repo.list_trash(limit=limit, offset=offset)
        return {"list": [d.to_dict() for d in items], "total": total}

    def stats(self) -> dict:
        return self._repo.stats()

    # ── 内部助手 ───────────────────────────────────
    def _find_or_raise(self, defect_id: str) -> Defect:
        defect = self._repo.find_by_id(defect_id)
        if defect is None:
            raise AggregateNotFound(f"缺陷不存在或已删除: {defect_id}")
        return defect

    def _find_deleted_or_raise(self, defect_id: str) -> Defect:
        defect = self._repo.find_by_id(defect_id, include_deleted=True)
        if defect is None or not defect.deleted:
            raise AggregateNotFound(f"回收站中不存在该缺陷: {defect_id}")
        return defect

    def _publish(self, defect: Defect) -> None:
        events = defect.pull_domain_events()
        for ev in events:
            event_bus.dispatch(ev)

    # ── 评论（子表旁路读写门面）────────────────────────
    def list_comments(self, query: "ListCommentsQuery") -> list:
        """列出某缺陷下的评论。"""
        return self._repo.list_comments(query.bug_id)

    def create_comment(self, cmd: "CreateCommentCommand") -> dict:
        """创建缺陷评论。"""
        return self._repo.create_comment(
            bug_id=cmd.bug_id, content=cmd.content, parent_id=cmd.parent_id,
            create_user=cmd.create_user, reply_user=cmd.reply_user,
            notifier=cmd.notifier,
        )

    def update_comment(self, cmd: "UpdateCommentCommand") -> Optional[dict]:
        """更新缺陷评论，不存在返回 None。"""
        return self._repo.update_comment(cmd.comment_id, cmd.content)

    def delete_comment(self, cmd: "DeleteCommentCommand") -> bool:
        """软删除缺陷评论并级联删除子评论。"""
        return self._repo.delete_comment(cmd.comment_id)

    # ── 旁路：自动创建 / 永久删除 ─────────────────────
    def auto_create_from_result(self, cmd: "AutoCreateFromResultCommand") -> Optional[dict]:
        """测试失败时自动创建缺陷。"""
        return self._repo.auto_create_from_result(
            file_path=cmd.file_path, test_result=cmd.test_result,
            test_case_id=cmd.test_case_id,
        )

    def permanent_delete(self, cmd: "PermanentDeleteCommand") -> bool:
        """彻底删除缺陷（绕过回收站流，直删存储行）。"""
        if not self._repo.permanent_delete(cmd.defect_id):
            raise AggregateNotFound(f"缺陷不存在: {cmd.defect_id}")
        return True


# 单例门面
defect_app_service = DefectAppService()
