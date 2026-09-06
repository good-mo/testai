"""评审会话状态值对象 + 状态机定义。

一个评审（Case Review）会话拥有自己的生命周期：
  - PREPARED   筹备中（可继续关联用例 / 修改评审人）
  - UNDERWAY   评审中（默认，正在逐条评审）
  - COMPLETED  已完成（全部用例有结论后由系统或用户触发）
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class ReviewStatusEnum(str, Enum):
    PREPARED = "PREPARED"      # 筹备中
    UNDERWAY = "UNDERWAY"      # 评审中（默认）
    COMPLETED = "COMPLETED"    # 已完成


# 业务允许的状态迁移矩阵
ALLOWED_TRANSITIONS: Dict[ReviewStatusEnum, Set[ReviewStatusEnum]] = {
    ReviewStatusEnum.PREPARED: {
        ReviewStatusEnum.UNDERWAY, ReviewStatusEnum.COMPLETED,
    },
    ReviewStatusEnum.UNDERWAY: {
        ReviewStatusEnum.COMPLETED, ReviewStatusEnum.PREPARED,
    },
    ReviewStatusEnum.COMPLETED: {
        ReviewStatusEnum.UNDERWAY,   # 允许重新开启评审（补充新用例/再评审）
    },
}


class ReviewStatus(ValueObject):
    """评审会话状态值对象。"""

    def __init__(self, value):
        if isinstance(value, ReviewStatusEnum):
            v = value
        else:
            raw = str(value or "").upper()
            if raw in ("", "NONE"):
                raw = ReviewStatusEnum.UNDERWAY.value
            try:
                v = ReviewStatusEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法评审状态 '{value}'，仅支持 "
                    f"{[e.value for e in ReviewStatusEnum]}"
                )
        object.__setattr__(self, "value", v)

    def can_transition_to(self, target: "ReviewStatus") -> bool:
        return target.value in ALLOWED_TRANSITIONS.get(self.value, set())

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ReviewStatus):
            return self.value is other.value
        if isinstance(other, ReviewStatusEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other
        return NotImplemented
