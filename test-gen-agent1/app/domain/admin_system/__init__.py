"""系统管理限界上下文。

管理后台能力（组织启停/成员移除）。本域为轻域：主要业务逻辑委托
`identity` 上下文中的组织管理能力。

对应现有：`services/admin_service.py`
"""
from app.domain.admin_system.application.admin_app_service import (
    AdminAppService,
    admin_app_service,
)
from app.domain.admin_system.domain.entities.org_admin import OrganizationAdmin

__all__ = ["AdminAppService", "admin_app_service", "OrganizationAdmin"]
