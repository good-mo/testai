"""组织（租户）聚合根 Organization。

聚合边界内的组成：
  - Organization（聚合根：租户基本信息 + 状态）
  - Member[]（组织成员，子实体）

职责：守护组织的不变量（名称非空、停用/启用、成员增删与角色变更的越权
守卫）。所有变更必须经由聚合根方法触发，业务命令校验通过后记录领域事件。

说明：项目绑定/组织成员数量等只读信息由 infrastructure 层附加上，领域层
不依赖具体表结构。
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError, InvariantViolation
from app.domain.identity.domain.entities.member import Member
from app.domain.identity.domain.events import (
    MemberAdded,
    MemberRemoved,
    MemberRoleChanged,
    OrganizationDisabled,
    OrganizationEnabled,
    OrganizationRenamed,
)
from app.domain.identity.domain.value_objects.member_role import (
    MemberRole,
    MemberRoleEnum,
)


class Organization(AggregateRoot):
    """组织（租户）聚合根。"""

    def __init__(
        self,
        *,
        org_id: str,
        name: str,
        description: str = "",
        status: str = "enabled",
        members: Optional[List[dict]] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
    ):
        nm = (name or "").strip()
        if not nm:
            raise DomainValidationError("组织名称不能为空")
        self.id = Identifier.of(org_id)
        self._name = nm
        self._description = description or ""
        self._status = status  # enabled/disabled
        self._members: List[Member] = []
        for m in (members or []):
            self._members.append(
                Member(**m) if isinstance(m, dict) else m
            )
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
    def status(self) -> str:
        return self._status

    @property
    def members(self) -> List[Member]:
        return list(self._members)

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def enabled(self) -> bool:
        return self._status == "enabled"

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 业务命令 ─────────────────────────────────────
    def rename(self, new_name: str, operator: str = "system") -> None:
        nn = (new_name or "").strip()
        if not nn:
            raise DomainValidationError("组织名称不能为空")
        if nn == self._name:
            return
        old = self._name
        self._name = nn
        self._touch()
        self.record_event(OrganizationRenamed(self.id.value, old, nn, operator))

    def change_description(self, text: str, operator: str = "system") -> None:
        self._description = text or ""
        self._touch()

    def disable(self, operator: str = "system") -> None:
        """停用组织（租户冻结）。"""
        if not self.enabled:
            return
        self._status = "disabled"
        self._touch()
        self.record_event(OrganizationDisabled(self.id.value, operator))

    def enable(self, operator: str = "system") -> None:
        if self.enabled:
            return
        self._status = "enabled"
        self._touch()
        self.record_event(OrganizationEnabled(self.id.value, operator))

    # ── 成员管理 ─────────────────────────────────────
    def add_member(self, *, member_id: str, user_id: str, username: str = "",
                   name: str = "", email: str = "", role: str = "member",
                   operator: str = "system") -> Member:
        """添加成员；若已存在则更新角色。"""
        existing = self.get_member_by_user(user_id)
        if existing is not None:
            old = existing.role.value
            if existing.change_role(role):
                self._touch()
                self.record_event(MemberRoleChanged(
                    self.id.value, user_id, old, role, operator))
            return existing
        m = Member(member_id=member_id, organization_id=self.id.value,
                   user_id=user_id, username=username, name=name, email=email,
                   role=role)
        self._members.append(m)
        self._touch()
        self.record_event(MemberAdded(self.id.value, user_id, role, operator))
        return m

    def change_member_role(self, user_id: str, new_role: str, operator: str = "system") -> bool:
        member = self.get_member_by_user(user_id)
        if member is None:
            raise DomainValidationError(f"成员不存在于组织: {user_id}")
        # 组织所有者不可被降级（owner 唯一，避免失去管理入口）
        if member.role.is_owner() and MemberRole(new_role).value != MemberRoleEnum.OWNER.value:
            if operator == "system" and self._owner_count() == 1:
                raise InvariantViolation("组织至少需要保留一名所有者")
        old = member.role.value
        if not member.change_role(new_role):
            return False
        self._touch()
        self.record_event(MemberRoleChanged(self.id.value, user_id, old, new_role, operator))
        return True

    def remove_member(self, user_id: str, operator: str = "system") -> bool:
        member = self.get_member_by_user(user_id)
        if member is None:
            return False
        if member.role.is_owner() and self._owner_count() <= 1:
            raise InvariantViolation("组织至少需要保留一名所有者，不能移除唯一所有者")
        self._members = [m for m in self._members if m.user_id != user_id]
        self._touch()
        self.record_event(MemberRemoved(self.id.value, user_id, operator))
        return True

    def get_member_by_user(self, user_id: str) -> Optional[Member]:
        for m in self._members:
            if m.user_id == user_id:
                return m
        return None

    def member_count(self) -> int:
        return len(self._members)

    def _owner_count(self) -> int:
        return sum(1 for m in self._members if m.role.is_owner())

    # ── 快照 / 持久化 ───────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "name": self._name,
            "description": self._description,
            "status": self._status,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "members": [m.to_dict() for m in self._members],
        }

    @staticmethod
    def from_dict(data: dict) -> "Organization":
        members = data.get("members") or []
        return Organization(
            org_id=str(data.get("id") or data.get("oid") or ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            status=data.get("status", "enabled"),
            members=members,
            created_at=data.get("created_at") or data.get("create_time"),
            updated_at=data.get("updated_at") or data.get("update_time"),
        )
