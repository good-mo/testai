"""资源池领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class ResourcePoolNotFound(DomainException):
    status_code = 404
