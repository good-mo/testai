"""计划关联用例的执行状态值对象。

描述计划内某个用例（functional/api/scenario）的执行进度：pending → 已执行
（passed/failed/blocked）。用于守护"计划用例执行状态"的取值合法性。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class CaseExecutionStatusEnum(str, Enum):
    PENDING = "pending"   # 未执行（默认）
    PASSED = "passed"     # 通过
    FAILED = "failed"     # 失败
    BLOCKED = "blocked"   # 阻塞


@dataclass(frozen=True)
class CaseExecutionStatus(ValueObject):
    """计划关联用例执行状态值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).strip().lower()
        if v not in {e.value for e in CaseExecutionStatusEnum}:
            raise DomainValidationError(
                f"非法用例执行状态 '{self.value}'，仅支持 "
                f"{[e.value for e in CaseExecutionStatusEnum]}"
            )
        object.__setattr__(self, "value", v)

    @property
    def executed(self) -> bool:
        return self.value != CaseExecutionStatusEnum.PENDING.value

    def __str__(self) -> str:
        return self.value
