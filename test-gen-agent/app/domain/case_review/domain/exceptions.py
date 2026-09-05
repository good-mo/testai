"""用例评审领域异常。"""
from app.domain.common.exceptions import DomainException, InvariantViolation


class InvalidReviewTransition(InvariantViolation):
    """评审会话状态非法迁移。"""

    def __init__(self, current: str, target: str):
        super().__init__(
            f"不允许从评审状态 '{current}' 迁移到 '{target}'"
        )


class ReviewNotFound(DomainException):
    status_code = 404


class ReviewStatusConflict(DomainException):
    status_code = 409
