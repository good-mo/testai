"""组织成员子实体 Member。

属于 Organization 聚合边界内的子实体，记录用户在某组织内的角色。
"""
from __future__ import annotations

import time
from typing import Optional

from app.domain.common.entities import Entity, Identifier
from app.domain.identity.domain.value_objects.member_role import MemberRole, MemberRoleEnum


class Member(Entity):
    """组织成员子实体。"""

    def __init__(
        self,
        *,
        member_id: str,
        organization_id: str,
        user_id: str,
        username: str = "",
        name: str = "",
        email: str = "",
        role: str = MemberRoleEnum.MEMBER.value,
        created_at: Optional[float] = None,
    ):
        self.id = Identifier.of(member_id)
        self._organization_id = organization_id or ""
        self._user_id = user_id or ""
        self._username = username or ""
        self._name = name or ""
        self._email = email or ""
        self._role = MemberRole(role)
        self._created_at = created_at if created_at is not None else time.time()
        self._domain_events = []

    # ── 只读属性 ─────────────────────────────────────
    @property
    def organization_id(self) -> str:
        return self._organization_id

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def name(self) -> str:
        return self._name

    @property
    def email(self) -> str:
        return self._email

    @property
    def role(self) -> MemberRole:
        return self._role

    @property
    def created_at(self) -> float:
        return self._created_at

    def change_role(self, role: str) -> bool:
        """变更成员角色；返回是否真实变更。"""
        new_role = MemberRole(role)
        if new_role == self._role:
            return False
        self._role = new_role
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "organization_id": self._organization_id,
            "user_id": self._user_id,
            "username": self._username,
            "name": self._name,
            "email": self._email,
            "role": self._role.value,
            "create_time": self._created_at,
        }
