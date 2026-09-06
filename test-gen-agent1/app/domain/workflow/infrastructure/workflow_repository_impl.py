"""工作流状态聚合仓储实现。"""
from __future__ import annotations

import uuid
from typing import List, Optional

from app.domain.workflow.domain.entities.workflow_status import WorkflowStatus
from app.repositories import workflow_repo


class WorkflowRepoAdapter:
    """将既有 workflow_repo 封装为面向 WorkflowStatus 的仓储。"""

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def save(self, status: WorkflowStatus) -> WorkflowStatus:
        existing = self.get(status.id.value)
        if existing:
            workflow_repo.update_status(
                status.id.value,
                name=status.name,
                remark=status.remark,
                status_definitions=status.status_definitions,
            )
        else:
            # 以聚合根 id 落库，保证返回的 status id == 落库 id（消除双写旁路）
            workflow_repo.add_status(
                name=status.name,
                scene=status.scene,
                scope_id=status.scope_id,
                scope_type=status.scope_type,
                remark=status.remark,
                status_id=status.id.value,
            )
        # 回读权威行（含 pos / create_time / 流转目标），确保 to_dict 完整一致
        refreshed = self.get(status.id.value)
        return refreshed if refreshed is not None else status

    def get(self, status_id: str) -> Optional[WorkflowStatus]:
        row = workflow_repo.get_status(status_id)
        return WorkflowStatus.from_dict(dict(row)) if row else None

    def list(self, scope_type: str, scope_id: str, scene: str) -> List[WorkflowStatus]:
        rows = workflow_repo.list_statuses(scope_type, scope_id, scene)
        return [WorkflowStatus.from_dict(dict(r)) for r in rows]

    def delete(self, status_id: str) -> bool:
        return workflow_repo.delete_status(status_id)

    def sort(self, status_ids: List[str]) -> bool:
        return workflow_repo.sort_statuses(status_ids)

    def update_flows(self, status_id: str, target_ids: List[str]) -> bool:
        return workflow_repo.update_flows(status_id, target_ids)

    def seed_defaults(self, scope_type: str, scope_id: str, scene: str) -> List[WorkflowStatus]:
        rows = workflow_repo.seed_default_statuses(scope_type, scope_id, scene)
        return [WorkflowStatus.from_dict(dict(r)) for r in rows]

    def set_start_status(self, status_id: str, scope_type: str, scope_id: str, scene: str) -> None:
        """确保只保留一个 START 状态。"""
        statuses = self.list(scope_type, scope_id, scene)
        for s in statuses:
            if s.id.value != status_id and s.is_start():
                s.set_definition("START", False)
                self.save(s)
