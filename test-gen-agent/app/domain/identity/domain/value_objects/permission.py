"""用户组/角色权限码值对象。

权限以字符串码表达（形如 'case:create' / 'org:manage' / '*'），
用户组拥有权限集合。此值对象负责权限集合的规范化与包含关系判定，
避免散落的字符串拼接与 set 魔法。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from app.domain.common.value_objects import ValueObject

# 通配权限：代表拥有所有权限
WILDCARD = "*"


@dataclass(frozen=True)
class PermissionSet(ValueObject):
    """一组权限码（不可变）。"""

    codes: frozenset = field(default_factory=frozenset)

    def __init__(self, codes):
        norm = set()
        for c in (codes or []):
            c = str(c).strip()
            if c:
                norm.add(c)
        object.__setattr__(self, "codes", frozenset(norm))

    def has(self, code: str) -> bool:
        """是否拥有某权限（含通配）。"""
        return WILDCARD in self.codes or str(code) in self.codes

    def union(self, other: "PermissionSet") -> "PermissionSet":
        return PermissionSet(self.codes | other.codes)

    def to_list(self) -> List[str]:
        return sorted(self.codes)

    @classmethod
    def from_list(cls, codes) -> "PermissionSet":
        return cls(codes)

    def __contains__(self, code: str) -> bool:
        return self.has(code)

    def _as_tuple(self) -> tuple:
        return tuple(sorted(self.codes))
