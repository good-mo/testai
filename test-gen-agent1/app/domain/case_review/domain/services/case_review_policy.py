"""用例评审领域服务：评审会话状态流转与结论不变量策略。

将"评审会话状态是否可迁移"以及"评审结论是否符合通过规则"等业务
规则独立成可测试的无状态策略，供聚合与流程复用，规则单一出处。
"""
from __future__ import annotations

from app.domain.case_review.domain.exceptions import InvalidReviewTransition
from app.domain.case_review.domain.value_objects.review_status import (
    ReviewStatus,
    ReviewStatusEnum,
)


class CaseReviewPolicy:
    """评审会话状态与通过规则策略（无状态领域服务）。"""

    def ensure_status_transition(self, current: ReviewStatus,
                                 target: ReviewStatus) -> None:
        """校验评审状态迁移是否合法。"""
        if not current.can_transition_to(target):
            raise InvalidReviewTransition(str(current), str(target))

    def can_start(self, status: ReviewStatus) -> bool:
        """评审是否可进入评审中（UNDERWAY）状态。"""
        return status.value in (
            ReviewStatusEnum.PREPARED,
            ReviewStatusEnum.COMPLETED,
        )

    def can_complete(self, status: ReviewStatus) -> bool:
        """评审是否可标记完成（COMPLETED）。"""
        return status.value in (
            ReviewStatusEnum.UNDERWAY,
            ReviewStatusEnum.PREPARED,
        )

    def should_auto_complete(self, review) -> bool:
        """在批量更新用例评审结果后是否应自动完成评审。

        当所有关联用例均有明确结论时，系统可将评审自动置为 COMPLETED。
        """
        return review.is_completed() and review.status.value is not ReviewStatusEnum.COMPLETED
