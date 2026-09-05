"""数据模板生命周期状态值对象。

模板生命周期简单：active（启用，可造数）/ inactive（停用）。软删除/清理
由仓储直接置对应标记，不走状态机流转。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class TemplateStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


VALID = {e.value for e in TemplateStatusEnum}


@dataclass(frozen=True)
class TemplateStatus(ValueObject):
    """数据模板状态值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).lower()
        if not v:
            v = TemplateStatusEnum.ACTIVE.value
        if v not in VALID:
            raise DomainValidationError(
                f"非法数据模板状态 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    @property
    def is_active(self) -> bool:
        return self.value == TemplateStatusEnum.ACTIVE.value

    def __str__(self) -> str:
        return self.value


__all__ = ["TemplateStatus", "TemplateStatusEnum"]
