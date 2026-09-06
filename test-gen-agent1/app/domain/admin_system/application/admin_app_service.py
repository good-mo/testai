"""系统管理应用服务（委托 identity 上下文）。"""
from __future__ import annotations

from app.domain.admin_system.application.dto import (
    DisableOrgCommand,
    EnableOrgCommand,
    RemoveMemberCommand,
)
from app.domain.admin_system.infrastructure.admin_repository_impl import (
    AdminRepoAdapter,
)


class AdminAppService:
    """系统管理用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or AdminRepoAdapter()

    def enable_organization(self, cmd: EnableOrgCommand) -> bool:
        return self._repo.enable_organization(cmd.org_id)

    def disable_organization(self, cmd: DisableOrgCommand) -> bool:
        return self._repo.disable_organization(cmd.org_id)

    def remove_org_member(self, cmd: RemoveMemberCommand) -> bool:
        return self._repo.remove_org_member(cmd.org_id, cmd.user_id)


admin_app_service = AdminAppService()
