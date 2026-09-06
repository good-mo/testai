"""展示配置领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class DisplayConfigNotFound(DomainException):
    """配置项不存在。"""
    status_code = 404
