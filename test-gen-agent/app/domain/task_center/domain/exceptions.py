"""任务中心领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class TaskCenterValidationError(DomainException):
    status_code = 422
