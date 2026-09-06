"""计划关联用例类型值对象。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject

# 规范化的用例类型集合（兼容历史写入的同义值）
VALID_ALIASES = {
    "functional": "functional",
    "function": "functional",
    "api": "api",
    "api_case": "api",
    "API": "api",
    "scenario": "scenario",
    "api_scenario": "scenario",
    "SCENARIO": "scenario",
}
VALID: Set[str] = {"functional", "api", "scenario"}


@dataclass(frozen=True)
class CaseType(ValueObject):
    """计划关联用例类型值对象（功能/接口/场景）。"""

    value: str

    def __post_init__(self) -> None:
        raw = str(self.value or "").strip()
        normalized = VALID_ALIASES.get(raw, raw.lower() if raw.lower() in VALID else raw)
        if normalized not in VALID:
            raise DomainValidationError(
                f"非法计划用例类型 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
