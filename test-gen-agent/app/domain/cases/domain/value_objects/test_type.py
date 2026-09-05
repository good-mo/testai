"""测试类型值对象（行业标准分类）。"""
from __future__ import annotations

from enum import Enum

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class TestTypeEnum(str, Enum):
    FUNCTIONAL = "functional"
    API = "api"
    UI = "ui"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPATIBILITY = "compatibility"
    RELIABILITY = "reliability"


class TestType(ValueObject):
    """测试类型值对象。"""

    value: TestTypeEnum

    def __init__(self, value):
        if isinstance(value, TestTypeEnum):
            v = value
        else:
            try:
                v = TestTypeEnum(str(value).lower())
            except ValueError:
                raise DomainValidationError(
                    f"非法测试类型 '{value}'，支持 {[e.value for e in TestTypeEnum]}"
                )
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value.value
