"""接口测试领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException, InvariantViolation


class InvalidApiStatusTransition(InvariantViolation):
    """接口用例/场景状态非法迁移。"""

    def __init__(self, resource: str, current: str, target: str):
        super().__init__(
            f"{resource}不允许从状态 '{current}' 迁移到 '{target}'"
        )


class ApiTestNotFound(DomainException):
    """接口测试资源不存在。"""

    status_code = 404

    def __init__(self, resource: str = "接口测试资源", rid: str = ""):
        msg = f"{resource}不存在"
        if rid:
            msg += f": {rid}"
        super().__init__(msg)
