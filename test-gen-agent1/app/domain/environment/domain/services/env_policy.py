"""环境领域策略：状态迁移与生命周期。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainValidationError
from app.domain.environment.domain.value_objects.env_status import (
    EnvStatus,
    EnvStatusEnum,
)


class EnvLifecyclePolicy:
    """环境生命周期策略（无状态领域服务）。"""

    def ensure_transition_allowed(self, current: EnvStatus, target: EnvStatus) -> None:
        if not current.can_transition_to(target):
            raise DomainValidationError(
                f"不允许从环境状态 '{current}' 迁移到 '{target}'"
            )

    def ensure_active(self, env_status: EnvStatus) -> None:
        if env_status.value in (EnvStatusEnum.ERROR.value,):
            raise DomainValidationError(
                f"环境处于错误状态 '{env_status}'，请先修复"
            )

    def ensure_online(self, env_status: EnvStatus) -> None:
        if env_status.value != EnvStatusEnum.ONLINE.value:
            raise DomainValidationError(
                f"环境当前状态 '{env_status}'，不是在线状态"
            )


__all__ = ["EnvLifecyclePolicy"]
