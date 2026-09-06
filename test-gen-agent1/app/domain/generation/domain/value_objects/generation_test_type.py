"""生成任务测试类型值对象（行业标准 7 分类）。

与用例域/既有 generators.test_types 的取值保持一致。
"""
from __future__ import annotations

from enum import Enum

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class GenerationTestTypeEnum(str, Enum):
    FUNCTIONAL = "functional"
    API = "api"
    UI = "ui"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPATIBILITY = "compatibility"
    RELIABILITY = "reliability"


class GenerationTestType(ValueObject):
    """生成任务测试类型值对象。"""

    value: GenerationTestTypeEnum

    def __init__(self, value):
        if isinstance(value, GenerationTestTypeEnum):
            v = value
        else:
            try:
                v = GenerationTestTypeEnum(str(value).lower())
            except ValueError:
                raise DomainValidationError(
                    f"非法测试类型 '{value}'，支持 {[e.value for e in GenerationTestTypeEnum]}"
                )
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value.value


__all__ = ["GenerationTestType", "GenerationTestTypeEnum"]
