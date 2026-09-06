"""评审通过规则值对象。

控制一个评审会话在何种条件下算作全部用例通过：
  - SINGLE   单人通过制（任一评审人通过即通过）
  - ALL      全员通过制（全部评审人都通过才通过）
"""
from __future__ import annotations

from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class ReviewPassRuleEnum(str, Enum):
    SINGLE = "SINGLE"   # 单人通过制（默认）
    ALL = "ALL"         # 全员通过制


VALID: Set[str] = {e.value for e in ReviewPassRuleEnum}


class ReviewPassRule(ValueObject):
    """评审通过规则值对象。"""

    value: ReviewPassRuleEnum

    def __init__(self, value):
        if isinstance(value, ReviewPassRuleEnum):
            v = value
        else:
            raw = str(value or "").upper()
            if raw in ("", "NONE"):
                raw = ReviewPassRuleEnum.SINGLE.value
            try:
                v = ReviewPassRuleEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法评审通过规则 '{value}'，仅支持 {sorted(VALID)}"
                )
        object.__setattr__(self, "value", v)

    @property
    def requires_all_reviewers(self) -> bool:
        return self.value is ReviewPassRuleEnum.ALL

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ReviewPassRule):
            return self.value is other.value
        if isinstance(other, ReviewPassRuleEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other
        return NotImplemented
