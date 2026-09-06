"""运行记录来源值对象。

对齐既有 run_records.source 取值（single / project / websocket / task），
任何非法/越界值在构造时即抛领域异常，杜绝字符串散落导致的脏数据。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject

# 与 app.repositories.run_repo.VALID_SOURCES 保持一致
VALID_SOURCES: Set[str] = {"single", "project", "websocket", "task"}
_DEFAULT = "single"


@dataclass(frozen=True)
class RunSource(ValueObject):
    """运行记录来源值对象。"""

    value: str

    def __post_init__(self) -> None:
        raw = str(self.value or _DEFAULT).lower()
        if raw not in VALID_SOURCES:
            raise DomainValidationError(
                f"非法运行来源 '{self.value}'，仅支持 {sorted(VALID_SOURCES)}"
            )
        object.__setattr__(self, "value", raw)

    def __str__(self) -> str:
        return self.value


__all__ = ["RunSource", "VALID_SOURCES"]
