"""缺陷生命周期状态值对象 + 状态机定义。"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class DefectStatusEnum(str, Enum):
    OPEN = "open"              # 待处理
    IN_PROGRESS = "in_progress"  # 处理中
    FIXED = "fixed"            # 已修复
    CLOSED = "closed"          # 已关闭
    WONT_FIX = "wont_fix"      # 不予修复
    # 软删除/回收站状态（由仓储软删除，不直接流转到）
    TRASHED = "__trashed__"


# 业务允许的状态迁移矩阵（不变量：来自缺陷处理流程）
ALLOWED_TRANSITIONS: Dict[DefectStatusEnum, Set[DefectStatusEnum]] = {
    DefectStatusEnum.OPEN: {
        DefectStatusEnum.IN_PROGRESS, DefectStatusEnum.FIXED,
        DefectStatusEnum.CLOSED, DefectStatusEnum.WONT_FIX,
    },
    DefectStatusEnum.IN_PROGRESS: {
        DefectStatusEnum.FIXED, DefectStatusEnum.CLOSED,
        DefectStatusEnum.WONT_FIX, DefectStatusEnum.OPEN,
    },
    DefectStatusEnum.FIXED: {DefectStatusEnum.CLOSED, DefectStatusEnum.IN_PROGRESS},
    DefectStatusEnum.CLOSED: {DefectStatusEnum.OPEN},   # 允许重开
    DefectStatusEnum.WONT_FIX: {DefectStatusEnum.OPEN},
}


class DefectStatus(ValueObject):
    """缺陷状态值对象，自带状态机校验。"""

    def __init__(self, value):
        if isinstance(value, DefectStatusEnum):
            v = value
        else:
            raw = str(value).lower()
            # 兼容外部可能传入空字符串 -> 默认 open
            if raw in ("", "none"):
                raw = DefectStatusEnum.OPEN.value
            try:
                v = DefectStatusEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法缺陷状态 '{value}'，仅支持 "
                    f"{[e.value for e in DefectStatusEnum if e.value != '__trashed__']}"
                )
        object.__setattr__(self, "value", v)

    @property
    def is_trashed(self) -> bool:
        return self.value is DefectStatusEnum.TRASHED

    def can_transition_to(self, target: "DefectStatus") -> bool:
        return target.value in ALLOWED_TRANSITIONS.get(self.value, set())

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DefectStatus):
            return self.value is other.value
        if isinstance(other, DefectStatusEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other
        return NotImplemented
