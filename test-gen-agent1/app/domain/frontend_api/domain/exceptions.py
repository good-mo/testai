"""前端兼容领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class FrontendApiError(DomainException):
    status_code = 400
