"""导出任务领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class ExportTaskNotFound(DomainException):
    status_code = 404
