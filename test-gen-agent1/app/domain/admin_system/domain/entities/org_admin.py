"""组织管理聚合根 OrganizationAdmin。

系统管理（admin_system）限界上下文中对组织启停/成员移除操作的**领域视图**。
本域为轻域：组织核心数据（名称/描述/成员列表等）由 identity 上下文拥有。
此处聚合建模的是「管理员对某组织的操作意图与结果状态」这一轻量概念：

  - 每条记录代表对某个组织发起的一次管理动作；
  - 守护操作前置条件（org_id 非空等）；
  - 记录领域事件供应用层发布（审计/通知等副作用解耦）。

聚合边界内的组成：
  - OrganizationAdmin（聚合根：org_id + 目标操作 + 操作人/时间）
"""
from __future__ import annotations

import time
from typing import Optional

from app.domain.admin_system.domain.events import (
    AdminOrganizationDisabled,
    AdminOrganizationEnabled,
)
from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError

# 管理动作类型常量
ACTION_ENABLE = "enable"
ACTION_DISABLE = "disable"
ACTION_REMOVE_MEMBER = "remove_member"


class OrganizationAdmin(AggregateRoot):
    """系统管理视图下的组织管理操作聚合根。"""

    def __init__(
        self,
        *,
        org_id: str,
        user_id: str = "",
        action: str = ACTION_ENABLE,
        operator: str = "system",
        created_at: Optional[float] = None,
    ):
        if not org_id:
            raise DomainValidationError("组织 ID 不能为空")
        if action not in (ACTION_ENABLE, ACTION_DISABLE, ACTION_REMOVE_MEMBER):
            raise DomainValidationError(f"非法管理动作: {action}")
        self.id = Identifier.of(org_id)
        self._user_id = user_id or ""
        self._action = action
        self._operator = operator or "system"
        self._created_at = created_at if created_at is not None else time.time()
        self._domain_events = []
        self.version = 0

    @property
    def org_id(self) -> str:
        return self.id.value

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def action(self) -> str:
        return self._action

    @property
    def operator(self) -> str:
        return self._operator

    @property
    def created_at(self) -> float:
        return self._created_at

    # ── 业务命令 ─────────────────────────────────────
    def enable_organization(self) -> None:
        """启用组织（记录启用领域事件）。"""
        if self._action != ACTION_ENABLE:
            self._action = ACTION_ENABLE
        self.record_event(AdminOrganizationEnabled(self.org_id, self._operator))

    def disable_organization(self) -> None:
        """停用组织（记录停用领域事件）。"""
        if self._action != ACTION_DISABLE:
            self._action = ACTION_DISABLE
        self.record_event(AdminOrganizationDisabled(self.org_id, self._operator))

    def remove_member(self, user_id: str) -> None:
        """移除组织成员。"""
        if not user_id:
            raise DomainValidationError("用户 ID 不能为空")
        self._user_id = user_id
        self._action = ACTION_REMOVE_MEMBER
        # 移除成员不做专属事件——由身份域发出 MemberRemoved

    # ── 持久化 / 序列化 ─────────────────────────────
    def to_dict(self) -> dict:
        return {
            "orgId": self.org_id,
            "id": self.org_id,
            "action": self._action,
            "userId": self._user_id,
            "operator": self._operator,
            "createdAt": self._created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "OrganizationAdmin":
        return OrganizationAdmin(
            org_id=str(data.get("orgId") or data.get("org_id") or data.get("id") or ""),
            user_id=data.get("userId") or data.get("user_id") or "",
            action=data.get("action", ACTION_ENABLE),
            operator=data.get("operator", "system"),
            created_at=data.get("createdAt") or data.get("created_at"),
        )


__all__ = [
    "OrganizationAdmin",
    "ACTION_ENABLE",
    "ACTION_DISABLE",
    "ACTION_REMOVE_MEMBER",
]
