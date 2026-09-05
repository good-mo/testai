"""数据工厂上下文值对象集。"""
from app.domain.datafactory.domain.value_objects.category import Category, CategoryEnum
from app.domain.datafactory.domain.value_objects.field_strategy import (
    FieldStrategy,
    FieldStrategyEnum,
)
from app.domain.datafactory.domain.value_objects.template_status import (
    TemplateStatus,
    TemplateStatusEnum,
)

__all__ = [
    "Category",
    "CategoryEnum",
    "FieldStrategy",
    "FieldStrategyEnum",
    "TemplateStatus",
    "TemplateStatusEnum",
]
