"""项目领域服务：跨聚合/对象的不变量策略。

将项目生命周期（active/archived）迁移合法性与软删除边界独立成可测试的
无状态策略，供聚合与生命周期流转复用，避免规则散落各处。
"""
from __future__ import annotations

from app.domain.common.exceptions import DomainValidationError
from app.domain.project.domain.value_objects.project_status import (
    ProjectStatus,
    ProjectStatusEnum,
)


class ProjectLifecyclePolicy:
    """项目生命周期策略（无状态领域服务）。"""

    def ensure_transition_allowed(self, current: ProjectStatus, target: ProjectStatus) -> None:
        """校验迁移合法性，非法时抛领域异常。"""
        if target.is_deleted:
            raise DomainValidationError(
                "不应直接流转到回收站；请使用 Project.delete() 触发软删除"
            )
        if not current.can_transition_to(target):
            raise DomainValidationError(
                f"不允许从状态 '{current}' 迁移到 '{target}'"
            )

    def is_deleted(self, status: ProjectStatus) -> bool:
        """项目是否处于回收站（软删除）状态。"""
        return status.is_deleted or status.value is ProjectStatusEnum.DELETED
