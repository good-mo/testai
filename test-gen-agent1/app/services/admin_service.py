# app/services/admin_service.py
"""系统管理业务逻辑层（admin_system 域 DDD 接入 · 阶段 C 薄门面）。

系统管理（管理后台的组织启停 / 组织成员移除）已收敛到 admin_system 域 DDD
应用服务 `admin_app_service`（见 `app/domain/admin_system/`，其仓储适配层
`AdminRepoAdapter` 委托 identity 域 DDD 门面，去除对 `organization_service`
的冗余中间层转发）。本 Service 收敛为对 DDD 应用门面的**薄委托门面**，仅保留
既有方法签名以兼容 `app/routers/missing_admin.py` 等调用方，返回语义
（组织启停/成员移除成功与否的 bool）与重构前一致，对外 API 零回归、可回滚。

> 推荐调用方直接使用 `admin_app_service`；本类仅作过渡兼容层保留。
用户组（角色）能力已移交 `auth_service`（经 `UserGroupRepo`），本服务不再
代理用户组数据。
"""
from __future__ import annotations

from app.domain.admin_system.application.admin_app_service import (
    admin_app_service as _ddd,
)
from app.domain.admin_system.application.dto import (
    DisableOrgCommand,
    EnableOrgCommand,
    RemoveMemberCommand,
)


class AdminService:
    """系统管理服务（组织启停 / 组织成员，DDD 薄门面）。"""

    # ── 组织启停 / 成员管理 ───────────────────────────────
    def enable_organization(self, org_id: str) -> bool:
        return _ddd.enable_organization(EnableOrgCommand(org_id=org_id))

    def disable_organization(self, org_id: str) -> bool:
        return _ddd.disable_organization(DisableOrgCommand(org_id=org_id))

    def remove_org_member(self, org_id: str, user_id: str) -> bool:
        return _ddd.remove_org_member(RemoveMemberCommand(
            org_id=org_id, user_id=user_id))


admin_service = AdminService()
