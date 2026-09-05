"""用例领域异常。"""
from app.domain.common.exceptions import DomainException, InvariantViolation


class InvalidCaseStatusTransition(InvariantViolation):
    """用例状态非法迁移。"""

    def __init__(self, current: str, target: str):
        super().__init__(
            f"不允许从状态 '{current}' 迁移到 '{target}'"
        )


class CaseStatusConflict(DomainException):
    status_code = 409
