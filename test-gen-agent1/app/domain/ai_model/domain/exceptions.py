"""AI 模型源领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class AiModelNotFound(DomainException):
    """模型源不存在。"""

    status_code = 404
