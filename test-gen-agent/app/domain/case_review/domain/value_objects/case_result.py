"""评审用例结果值对象。

评审会话中每个关联用例单独记录评审结论：
  - UN_REVIEWED      未评审（默认）
  - UNDER_REVIEWED   评审中
  - PASS             通过
  - UN_PASS          不通过
  - RE_REVIEWED      需重新评审（评审人认为需修改后再评审）
"""
from __future__ import annotations

from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class CaseReviewResultEnum(str, Enum):
    UN_REVIEWED = "UN_REVIEWED"          # 未评审
    UNDER_REVIEWED = "UNDER_REVIEWED"    # 评审中
    PASS = "PASS"                        # 通过
    UN_PASS = "UN_PASS"                  # 不通过
    RE_REVIEWED = "RE_REVIEWED"          # 需重新评审


class CaseReviewResult(ValueObject):
    """单用例在评审会话中的结论值对象。"""

    value: CaseReviewResultEnum

    def __init__(self, value):
        if isinstance(value, CaseReviewResultEnum):
            v = value
        else:
            raw = str(value or "").upper()
            if raw in ("", "NONE"):
                raw = CaseReviewResultEnum.UN_REVIEWED.value
            try:
                v = CaseReviewResultEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法用例评审结果 '{value}'，仅支持 "
                    f"{[e.value for e in CaseReviewResultEnum]}"
                )
        object.__setattr__(self, "value", v)

    @property
    def is_reviewed(self) -> bool:
        """该用例是否已有明确结论（非未评审/评审中）。"""
        return self.value in (
            CaseReviewResultEnum.PASS,
            CaseReviewResultEnum.UN_PASS,
            CaseReviewResultEnum.RE_REVIEWED,
        )

    @property
    def is_passed(self) -> bool:
        return self.value is CaseReviewResultEnum.PASS

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CaseReviewResult):
            return self.value is other.value
        if isinstance(other, CaseReviewResultEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other
        return NotImplemented
