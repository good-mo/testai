"""组织成员角色值对象。

约束组织内成员可被授予的固定角色集合，超出即抛领域异常；
角色承载权限语义（owner 具备全部管理权限，admin 可管理成员，member 为普通成员）。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class MemberRoleEnum(str, Enum):
    OWNER = "owner"        # 组织所有者（最高权限，唯一）
    ADMIN = "admin"        # 管理员
    MEMBER = "member"      # 普通成员


VALID_ROLES: Set[str] = {e.value for e in MemberRoleEnum}

# 角色权限权重：数值越大权限越高，便于比较/越权守卫
_ROLE_LEVEL = {
    MemberRoleEnum.MEMBER.value: 0,
    MemberRoleEnum.ADMIN.value: 1,
    MemberRoleEnum.OWNER.value: 2,
}


@dataclass(frozen=True)
class MemberRole(ValueObject):
    """组织成员角色值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).lower()
        if v not in VALID_ROLES:
            raise DomainValidationError(
                f"非法成员角色 '{self.value}'，仅支持 {sorted(VALID_ROLES)}"
            )
        object.__setattr__(self, "value", v)

    @property
    def level(self) -> int:
        return _ROLE_LEVEL[self.value]

    def can_manage(self) -> bool:
        """是否具备成员管理权限（owner/admin）。"""
        return self.value in (MemberRoleEnum.OWNER.value, MemberRoleEnum.ADMIN.value)

    def is_owner(self) -> bool:
        return self.value == MemberRoleEnum.OWNER.value

    def __str__(self) -> str:
        return self.value
