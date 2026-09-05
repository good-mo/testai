"""调试领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class DebugItemNotFound(DomainException):
    """调试项不存在。"""
    status_code = 404
