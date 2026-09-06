"""误报规则领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class FakeErrorRuleNotFound(DomainException):
    """误报规则不存在。"""
    status_code = 404
