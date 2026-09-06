"""用户组/角色聚合根 Role（UserGroup）。

聚合边界内的组成：
  - Role（聚合根：角色基本信息 + 权限集合 + 组内成员）

说明：本项目将"角色（Role）"与"用户组（UserGroup）"统一落到 user_groups
表，角色即一类内聚权限的用户组。此处以 Role 表达该聚合根，方便领域层
统一守护"角色名唯一、内置角色不可删、权限集合"等不变量。
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError, InvariantViolation
from app.domain.identity.domain.events import (
    PermissionGranted,
    RoleDeleted,
    RoleRenamed,
)
from app.domain.identity.domain.value_objects.permission import PermissionSet


class Role(AggregateRoot):
    """角色（用户组）聚合根。"""

    def __init__(
        self,
        *,
        role_id: str,
        name: str,
        description: str = "",
        group_type: str = "SYSTEM",
        scope_id: str = "",
        internal: int = 0,
        permissions: Optional[list] = None,
        member_ids: Optional[list] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
    ):
        nm = (name or "").strip()
        if not nm:
            raise DomainValidationError("角色名称不能为空")
        self.id = Identifier.of(role_id)
        self._name = nm
        self._description = description or ""
        self._group_type = group_type or "SYSTEM"
        self._scope_id = scope_id or ""
        self._internal = int(internal or 0)
        self._permissions = PermissionSet(permissions or [])
        self._member_ids = list(member_ids or [])
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._domain_events = []
        self.version = 0

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def group_type(self) -> str:
        return self._group_type

    @property
    def scope_id(self) -> str:
        return self._scope_id

    @property
    def internal(self) -> bool:
        return self._internal == 1

    @property
    def permissions(self) -> PermissionSet:
        return self._permissions

    @property
    def member_ids(self) -> List[str]:
        return list(self._member_ids)

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 业务命令 ─────────────────────────────────────
    def rename(self, new_name: str, operator: str = "system") -> None:
        nn = (new_name or "").strip()
        if not nn:
            raise DomainValidationError("角色名称不能为空")
        if nn == self._name:
            return
        old = self._name
        self._name = nn
        self._touch()
        self.record_event(RoleRenamed(self.id.value, old, nn, operator))

    def set_permissions(self, permissions: list, operator: str = "system") -> None:
        """整体覆盖角色权限集合。"""
        new_set = PermissionSet(permissions or [])
        if new_set == self._permissions:
            return
        self._permissions = new_set
        self._touch()
        self.record_event(PermissionGranted(self.id.value, self._permissions.to_list(), operator))

    def grant_permission(self, code: str) -> None:
        if self._permissions.has(code):
            return
        self.set_permissions(self._permissions.to_list() + [code], operator="system")

    def revoke_permission(self, code: str) -> None:
        if not self._permissions.has(code):
            return
        remaining = [c for c in self._permissions.to_list() if c != code and c != "*"]
        self.set_permissions(remaining, operator="system")

    def add_member(self, user_id: str) -> None:
        if user_id not in self._member_ids:
            self._member_ids.append(user_id)
            self._touch()

    def remove_member(self, user_id: str) -> bool:
        if user_id in self._member_ids:
            self._member_ids.remove(user_id)
            self._touch()
            return True
        return False

    def can_delete(self) -> bool:
        """内置角色不可删除。"""
        return not self.internal

    def delete(self, operator: str = "system") -> None:
        if not self.can_delete():
            raise InvariantViolation(f"内置角色 '{self._name}' 不允许删除")
        self.record_event(RoleDeleted(self.id.value, operator))

    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "name": self._name,
            "description": self._description,
            "type": self._group_type,
            "scope_id": self._scope_id,
            "internal": self._internal,
            "permissions": self._permissions.to_list(),
            "member_ids": list(self._member_ids),
            "created_at": self._created_at,
            "updated_at": self._updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Role":
        return Role(
            role_id=str(data.get("id") or data.get("group_id") or ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            group_type=data.get("type") or data.get("group_type") or "SYSTEM",
            scope_id=data.get("scope_id", ""),
            internal=data.get("internal", 0),
            permissions=data.get("permissions") or [],
            member_ids=data.get("member_ids") or [],
            created_at=data.get("created_at") or data.get("create_time"),
            updated_at=data.get("updated_at") or data.get("update_time"),
        )
