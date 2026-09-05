"""报告格式值对象：报告导出格式的类型约束。

对应当前报告中心支持的三类导出格式（HTML / JUnit XML / Markdown）。
任何非法/不支持的值越界即抛领域异常，杜绝字符串散落导致的"不支持格式"
运行时分支判断。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class ReportFormatEnum(str, Enum):
    HTML = "html"
    JUNIT = "junit"
    MARKDOWN = "markdown"


VALID: Set[str] = {e.value for e in ReportFormatEnum}


@dataclass(frozen=True)
class ReportFormat(ValueObject):
    """报告导出格式值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).lower()
        if v not in VALID:
            raise DomainValidationError(
                f"不支持的报告格式 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


__all__ = ["ReportFormat", "ReportFormatEnum", "VALID"]
