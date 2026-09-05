"""项目成员（聚合内子实体值对象）。

成员在 project_members 表中以独立行存储，但从聚合一致性看属于 Project
聚合的内聚内容。这里以不可变值对象承载成员快照，供聚合与仓储在
聚合粒度内整体读写。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.domain.common.value_objects import ValueObject
from app.domain.project.domain.value_objects.member_role import MemberRole


@dataclass(frozen=True)
class ProjectMember(ValueObject):
    """项目成员值对象。"""

    user_id: str = ""
    username: str = ""
    name: str = ""
    email: str = ""
    role: str = "member"
    user_group: str = ""

    def __post_init__(self) -> None:
        # 归一化角色
        normalized = MemberRole(self.role)
        object.__setattr__(self, "role", str(normalized))

    @property
    def identity(self) -> str:
        """成员去重标识：优先 user_id，其次 username。"""
        return self.user_id or self.username

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "name": self.name or self.username,
            "email": self.email,
            "role": self.role,
            "user_group": self.user_group,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectMember":
        data = data or {}
        return cls(
            user_id=str(data.get("user_id") or ""),
            username=str(data.get("username") or ""),
            name=str(data.get("name") or ""),
            email=str(data.get("email") or ""),
            role=str(data.get("role") or "member"),
            user_group=str(data.get("user_group") or ""),
        )
