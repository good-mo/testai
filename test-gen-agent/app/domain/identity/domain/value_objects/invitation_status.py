"""邀请状态值对象。

邀请生命周期：待使用 → 已使用 / 已过期 / 已撤销。值对象承载状态判定，
避免散落的 used 0/1 与 expire_time 判断。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class InvitationStatusEnum(str, Enum):
    PENDING = "pending"      # 待使用
    USED = "used"            # 已使用
    EXPIRED = "expired"      # 已过期
    REVOKED = "revoked"      # 已撤销


VALID: Set[str] = {e.value for e in InvitationStatusEnum}


@dataclass(frozen=True)
class InvitationStatus(ValueObject):
    """邀请状态值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).lower()
        if v not in VALID:
            raise DomainValidationError(
                f"非法邀请状态 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    @property
    def usable(self) -> bool:
        """是否仍可被用于注册。"""
        return self.value == InvitationStatusEnum.PENDING.value

    def __str__(self) -> str:
        return self.value
