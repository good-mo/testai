"""用户视图领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class UserViewNotFound(DomainException):
    status_code = 404
