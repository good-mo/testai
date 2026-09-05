"""测试异常归因值对象。

用于回答"线上为什么没测出来/当时为什么失败"：
需求变更、环境异常、数据问题、代码回归、覆盖遗漏等。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class AttributionEnum(str, Enum):
    REQUIREMENT_CHANGE = "requirement_change"   # 需求变更
    ENV_ANOMALY = "environment_anomaly"         # 环境异常
    DATA_ISSUE = "data_issue"                   # 数据问题
    CODE_REGRESSION = "code_regression"         # 代码回归（新缺陷）
    COVERAGE_GAP = "coverage_gap"               # 覆盖遗漏

    @property
    def label(self) -> str:
        return {
            AttributionEnum.REQUIREMENT_CHANGE: "需求变更",
            AttributionEnum.ENV_ANOMALY: "环境异常",
            AttributionEnum.DATA_ISSUE: "数据问题",
            AttributionEnum.CODE_REGRESSION: "代码回归",
            AttributionEnum.COVERAGE_GAP: "覆盖遗漏",
        }[self]


VALID: Set[str] = {e.value for e in AttributionEnum}
ATTRIBUTION_LABELS = {e.value: e.label for e in AttributionEnum}


@dataclass(frozen=True)
class Attribution(ValueObject):
    """异常归因值对象，带人类可读标签。"""

    value: str

    def __post_init__(self) -> None:
        raw = self.value.value if isinstance(self.value, AttributionEnum) else self.value
        v = str(raw).strip().lower()
        if v not in VALID:
            raise DomainValidationError(
                f"非法异常归因 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    @property
    def enum(self) -> AttributionEnum:
        return AttributionEnum(self.value)

    @property
    def label(self) -> str:
        return AttributionEnum(self.value).label

    def __str__(self) -> str:
        return self.value
