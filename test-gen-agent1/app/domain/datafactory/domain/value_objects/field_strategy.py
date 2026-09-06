"""字段生成策略值对象。

数据模板的 schema 形如 {"字段名": {strategy, value, ...}}，strategy 决定
生成算法。此处把策略码建模为值对象，便于领域层统一校验与描述。

策略码对齐既有 app/repositories/datafactory_repo 常量。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class FieldStrategyEnum(str, Enum):
    SEQUENCE = "sequence"        # 序列递增（支持 {n} 占位 / 格式化）
    FIXED = "fixed"              # 固定值
    UUID = "uuid"                # 随机 UUID
    RANDOM = "random"            # 随机（choices 或 min~max）
    TIMESTAMP = "timestamp"      # 时间戳/时间格式化
    REFERENCE = "reference"      # 引用其它模板字段（registry）


VALID: Set[str] = {e.value for e in FieldStrategyEnum}


@dataclass(frozen=True)
class FieldStrategy(ValueObject):
    """字段生成策略值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).lower()
        if v not in VALID:
            raise DomainValidationError(
                f"非法字段生成策略 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    @property
    def is_reference(self) -> bool:
        return self.value == FieldStrategyEnum.REFERENCE.value

    def __str__(self) -> str:
        return self.value


__all__ = ["FieldStrategy", "FieldStrategyEnum"]
