"""数据工厂领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException


class DataTemplateNotFound(DomainException):
    """数据模板不存在。"""

    status_code = 404

    def __init__(self, message: str = "数据模板不存在"):
        super().__init__(message)


class DataBatchNotFound(DomainException):
    """生成批次不存在。"""

    status_code = 404

    def __init__(self, message: str = "数据批次不存在"):
        super().__init__(message)


__all__ = ["DataTemplateNotFound", "DataBatchNotFound"]
