"""数据模板类别值对象。

对齐既有 app/repositories/datafactory_repo.VALID_CATEGORIES。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class CategoryEnum(str, Enum):
    USER = "user"
    ORDER = "order"
    PRODUCT = "product"
    INVENTORY = "inventory"
    COUPON = "coupon"
    PAYMENT = "payment"
    CUSTOM = "custom"


VALID: Set[str] = {e.value for e in CategoryEnum}


@dataclass(frozen=True)
class Category(ValueObject):
    """数据模板类别值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).lower()
        if not v:
            v = CategoryEnum.CUSTOM.value
        if v not in VALID:
            raise DomainValidationError(
                f"非法数据类别 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


__all__ = ["Category", "CategoryEnum", "VALID"]
