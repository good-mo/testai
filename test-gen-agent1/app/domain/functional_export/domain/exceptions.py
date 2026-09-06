"""功能用例导出领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class ExportError(DomainException):
    status_code = 400
