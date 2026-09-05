"""缺陷领域异常。"""
from app.domain.common.exceptions import DomainException, InvariantViolation


class InvalidDefectStatusTransition(InvariantViolation):
    """缺陷状态非法迁移。"""

    def __init__(self, current: str, target: str):
        super().__init__(f"不允许从状态 '{current}' 迁移到 '{target}'")


class DefectNotFound(DomainException):
    status_code = 404

    def __init__(self, message: str = "缺陷不存在"):
        super().__init__(message)
