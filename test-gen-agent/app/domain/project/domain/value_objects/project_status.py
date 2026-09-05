"""项目生命周期状态值对象 + 状态机定义。

项目生命周期：active（启用）⇄ archived（归档/停用），以及软删除 deleted
（进入回收站，由仓储软删除处理，不直接流转）。
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class ProjectStatusEnum(str, Enum):
    ACTIVE = "active"          # 启用
    ARCHIVED = "archived"      # 归档/停用
    # 软删除/回收站状态（由仓储软删除，不直接流转到）
    DELETED = "__deleted__"


# 业务允许的状态迁移矩阵（不变量）
ALLOWED_TRANSITIONS: Dict[ProjectStatusEnum, Set[ProjectStatusEnum]] = {
    ProjectStatusEnum.ACTIVE: {
        ProjectStatusEnum.ARCHIVED,
    },
    ProjectStatusEnum.ARCHIVED: {
        ProjectStatusEnum.ACTIVE,
    },
    ProjectStatusEnum.DELETED: set(),
}


class ProjectStatus(ValueObject):
    """项目状态值对象，自带状态机校验。"""

    def __init__(self, value):
        if isinstance(value, ProjectStatusEnum):
            v = value
        else:
            raw = str(value).lower()
            # 兼容空字符串 -> 默认 active
            if raw == "deleted":
                v = ProjectStatusEnum.DELETED
                object.__setattr__(self, "value", v)
                return
            # 兼容空字符串 -> 默认 active
            if raw in ("", "none", "disabled"):
                raw = ProjectStatusEnum.ACTIVE.value
            try:
                v = ProjectStatusEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法项目状态 '{value}'，仅支持 active/archived"
                )
        object.__setattr__(self, "value", v)

    @property
    def is_deleted(self) -> bool:
        return self.value is ProjectStatusEnum.DELETED

    def can_transition_to(self, target: "ProjectStatus") -> bool:
        return target.value in ALLOWED_TRANSITIONS.get(self.value, set())

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ProjectStatus):
            return self.value is other.value
        if isinstance(other, ProjectStatusEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other
        return NotImplemented


# 可持久化/对外暴露的状态字符串（不含内部软删占位）
PERSISTABLE_STATUSES = [
    e.value for e in ProjectStatusEnum if e.value != ProjectStatusEnum.DELETED.value
]
