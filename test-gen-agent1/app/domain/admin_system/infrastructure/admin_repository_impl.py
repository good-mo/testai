"""系统管理仓储实现（直接委托 identity DDD 应用门面）。

不再反向依赖 `app.services.organization_service`（避免 domain → services → domain
循环依赖风险）。identity 域已收敛核心组织生命周期方法，此处直接调用其应用门面。
"""
from __future__ import annotations

from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainValidationError,
    InvariantViolation,
)
from app.domain.identity.application.identity_app_service import (
    identity_app_service,
)


class AdminRepoAdapter:
    """将 AdminRepository 委托给 IdentityAppService（identity DDD 的应用门面）。"""

    def enable_organization(self, org_id: str) -> bool:
        try:
            identity_app_service.set_organization_enabled(
                org_id, True, operator="system")
        except (AggregateNotFound, DomainValidationError, InvariantViolation):
            return False
        return True

    def disable_organization(self, org_id: str) -> bool:
        try:
            identity_app_service.set_organization_enabled(
                org_id, False, operator="system")
        except (AggregateNotFound, DomainValidationError, InvariantViolation):
            return False
        return True

    def remove_org_member(self, org_id: str, user_id: str) -> bool:
        try:
            return identity_app_service.remove_member(
                org_id, user_id, operator="system")
        except (AggregateNotFound, DomainValidationError, InvariantViolation):
            return False
