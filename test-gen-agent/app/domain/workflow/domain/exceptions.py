"""工作流状态领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class WorkflowStatusNotFound(DomainException):
    status_code = 404
