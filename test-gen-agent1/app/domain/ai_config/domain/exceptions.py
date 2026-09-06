"""AI 配置领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class AiConfigNotFound(DomainException):
    """AI 配置不存在。"""

    status_code = 404
