"""用例评审值对象。

用例评审是 TestCase 聚合内部的子值对象，不具备独立仓储，
随聚合一起存取，保证事务一致性。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class ReviewOutcome(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEED_REVISE = "need_revise"


@dataclass(frozen=True)
class CaseReview(ValueObject):
    """单次评审记录（值对象，不可变）。"""

    reviewer: str = ""
    comment: str = ""
    outcome: ReviewOutcome = ReviewOutcome.PENDING
    reviewed_at: Optional[float] = None
    review_seq: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, ReviewOutcome):
            try:
                object.__setattr__(self, "outcome", ReviewOutcome(self.outcome))
            except ValueError:
                raise DomainValidationError(
                    f"非法评审结果 '{self.outcome}'，支持 {[e.value for e in ReviewOutcome]}"
                )
