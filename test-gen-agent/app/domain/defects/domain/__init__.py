"""缺陷管理领域层（domain layer）。

仅表达缺陷业务概念与规则，不依赖 FastAPI / sqlite / 具体存储实现。
"""
from app.domain.defects.domain.entities.defect import Defect
from app.domain.defects.domain.repository import DefectRepository
from app.domain.defects.domain.value_objects.severity import Severity, SeverityEnum
from app.domain.defects.domain.value_objects.status import DefectStatus, DefectStatusEnum

__all__ = [
    "Defect",
    "DefectRepository",
    "DefectStatus",
    "DefectStatusEnum",
    "Severity",
    "SeverityEnum",
]
