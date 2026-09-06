"""项目应用配置领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class ProjectConfigNotFound(DomainException):
    """配置不存在。"""
    status_code = 404
