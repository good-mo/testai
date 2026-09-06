"""生成任务来源值对象。

标识一次生成任务的发起渠道，对齐既有 run_records.source 取值
（single / project / websocket / task）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject

VALID: Set[str] = {"single", "project", "websocket", "task"}
VALID_SET = frozenset(VALID)


@dataclass(frozen=True)
class JobSource(ValueObject):
    """生成任务来源值对象。"""

    value: str

    def __post_init__(self) -> None:
        raw = str(self.value).lower()
        if raw not in VALID_SET:
            raise DomainValidationError(
                f"非法任务来源 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", raw)

    def __str__(self) -> str:
        return self.value


__all__ = ["JobSource", "VALID"]
