"""模板场景（业务领域）值对象。

模板按业务场景分类：FUNCTIONAL（功能用例）、API（接口）、UI、
TEST_PLAN（测试计划）、BUG（缺陷）等。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class TemplateSceneEnum(str, Enum):
    FUNCTIONAL = "FUNCTIONAL"
    API = "API"
    UI = "UI"
    TEST_PLAN = "TEST_PLAN"
    BUG = "BUG"


VALID: Set[str] = {e.value for e in TemplateSceneEnum}


@dataclass(frozen=True)
class TemplateScene(ValueObject):
    """模板场景值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).upper()
        if v not in VALID:
            raise DomainValidationError(
                f"不支持的模板场景 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ScopeType(ValueObject):
    """模板作用域类型（PROJECT / ORGANIZATION）。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).upper()
        if v not in ("PROJECT", "ORGANIZATION"):
            raise DomainValidationError(
                f"不支持的模板作用域类型 '{self.value}'，仅支持 PROJECT / ORGANIZATION"
            )
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


__all__ = ["TemplateScene", "TemplateSceneEnum", "VALID", "ScopeType"]
