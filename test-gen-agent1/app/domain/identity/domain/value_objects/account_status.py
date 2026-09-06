"""用户账号可用状态值对象。

将用户 enable 字段归一化为强类型状态，避免散落的 0/1 魔法值。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class AccountStatusEnum(str, Enum):
    ENABLED = "enabled"        # 正常
    DISABLED = "disabled"      # 已停用（禁登录）


VALID: Set[str] = {e.value for e in AccountStatusEnum}


@dataclass(frozen=True)
class AccountStatus(ValueObject):
    """用户账号状态值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).lower()
        if v in ("1", "true", "on", "active"):
            v = AccountStatusEnum.ENABLED.value
        elif v in ("0", "false", "off", "inactive", "banned"):
            v = AccountStatusEnum.DISABLED.value
        if v not in VALID:
            raise DomainValidationError(
                f"非法账号状态 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    @property
    def enabled(self) -> bool:
        return self.value == AccountStatusEnum.ENABLED.value

    def __str__(self) -> str:
        return self.value
