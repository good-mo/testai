"""项目成员角色值对象。

成员在项目内的角色：admin（管理员）/ member（成员）/ guest（访客）。
"""
from __future__ import annotations

from enum import Enum

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class MemberRoleEnum(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class MemberRole(ValueObject):
    """项目成员角色（不可变值对象）。"""

    def __init__(self, value):
        if isinstance(value, MemberRoleEnum):
            v = value
        else:
            raw = str(value).lower()
            if raw in ("", "none"):
                raw = MemberRoleEnum.MEMBER.value
            try:
                v = MemberRoleEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法成员角色 '{value}'，仅支持 admin/member/guest"
                )
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MemberRole):
            return self.value is other.value
        if isinstance(other, MemberRoleEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other
        return NotImplemented
