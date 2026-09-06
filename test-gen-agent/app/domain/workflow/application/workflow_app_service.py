"""工作流状态应用服务。

修复说明：
  - 修改 import：从 WorkflowRepoAdapter 改为 WorkflowRepositoryImpl
  - 使用模块级单例 workflow_repository
"""
from __future__ import annotations

from typing import Optional

from app.domain.workflow.application.dto import (
    CreateStatusCommand,
    DeleteStatusCommand,
    GetStatusCommand,
    ListStatusesCommand,
    SeedDefaultsCommand,
    SetDefinitionCommand,
    SortStatusesCommand,
    UpdateFlowsCommand,
    UpdateStatusCommand,
)
from app.domain.workflow.domain.entities.workflow_status import WorkflowStatus

# ── 修复：改 import ──────────────────────────────────────────
from app.domain.workflow.infrastructure.workflow_repository_impl import (
    WorkflowRepositoryImpl,
    workflow_repository,
)


class WorkflowAppService:
    """工作流状态用例编排服务。"""

    def __init__(self, repo=None):
        # ── 修复：使用新的 Repository 单例 ──────────────────
        self._repo = repo or workflow_repository

    def list(self, cmd: ListStatusesCommand) -> list:
        statuses = self._repo.list(cmd.scope_type, cmd.scope_id, cmd.scene)
        return [s.to_dict() for s in statuses]

    def get(self, cmd: GetStatusCommand) -> Optional[dict]:
        s = self._repo.get(cmd.status_id)
        return s.to_dict() if s else None

    def create(self, cmd: CreateStatusCommand) -> dict:
        status = WorkflowStatus(
            status_id=self._repo.next_id() if hasattr(self._repo, 'next_id') else str(__import__('uuid').uuid4()),
            scope_type=cmd.scope_type,
            scope_id=cmd.scope_id,
            scene=cmd.scene,
            name=cmd.name,
            remark=cmd.remark,
            create_user=cmd.create_user,
            _created=True,
        )
        saved = self._repo.save(status)
        return saved.to_dict()

    def update(self, cmd: UpdateStatusCommand) -> Optional[dict]:
        status = self._repo.get(cmd.status_id)
        if not status:
            return None  # 与既有 service 语义一致：不存在返回 None，由门面映射 404
        status.update_info(
            # 兼容旧语义：空 name 视为"不改名"（原 repo `name or row['name']`）
            name=cmd.name if (cmd.name or "").strip() else None,
            remark=cmd.remark,
            status_definitions=cmd.status_definitions,
        )
        saved = self._repo.save(status)
        return saved.to_dict()

    def delete(self, cmd: DeleteStatusCommand) -> bool:
        return self._repo.delete(cmd.status_id)

    def sort(self, cmd: SortStatusesCommand) -> bool:
        return self._repo.sort(cmd.status_ids)

    def update_flows(self, cmd: UpdateFlowsCommand) -> bool:
        return self._repo.update_flows(cmd.status_id, cmd.target_ids)

    def set_definition(self, cmd: SetDefinitionCommand) -> bool:
        status = self._repo.get(cmd.status_id)
        if not status:
            return False
        # START 唯一约束：如启用 START，需清除其他状态
        if cmd.definition_id == "START" and cmd.enable:
            # 以目标状态自身 scope 唯一定位同范围其他 START（PROJECT/ORGANIZATION 通用）
            self._repo.set_start_status(cmd.status_id, status.scope_type,
                                        status.scope_id, status.scene)
        status.set_definition(cmd.definition_id, cmd.enable)
        self._repo.save(status)
        return True

    def seed_defaults(self, cmd: SeedDefaultsCommand) -> list:
        statuses = self._repo.list(cmd.scope_type, cmd.scope_id, cmd.scene)
        if statuses:
            return [s.to_dict() for s in statuses]
        seeded = self._repo.seed_defaults(cmd.scope_type, cmd.scope_id, cmd.scene)
        return [s.to_dict() for s in seeded]


workflow_app_service = WorkflowAppService()
