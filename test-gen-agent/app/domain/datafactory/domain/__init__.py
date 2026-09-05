"""数据工厂领域层（domain layer）。

仅表达数据模板/批次业务概念与规则，不依赖 FastAPI / sqlite / 具体存储实现。
"""
from app.domain.datafactory.domain.entities.data_batch import DataBatch
from app.domain.datafactory.domain.entities.data_template import DataTemplate
from app.domain.datafactory.domain.repository import DataFactoryRepository
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
    "DataTemplate",
    "DataBatch",
    "DataFactoryRepository",
    "Category",
    "CategoryEnum",
    "FieldStrategy",
    "FieldStrategyEnum",
    "TemplateStatus",
    "TemplateStatusEnum",
]
