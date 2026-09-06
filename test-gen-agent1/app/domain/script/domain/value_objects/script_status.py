"""脚本健康状态与框架类型值对象。

脚本状态：
  healthy（健康）→ unstable（不稳定）→ degraded（严重退化）
通过健康度评分（0-100）驱动状态转换。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class ScriptStatusEnum(str, Enum):
    HEALTHY = "healthy"       # 健康（评分 >= 85）
    UNSTABLE = "unstable"     # 不稳定（评分 >= 60）
    DEGRADED = "degraded"     # 严重退化（评分 < 60）


# 业务允许的状态迁移
ALLOWED_TRANSITIONS: Dict[ScriptStatusEnum, Set[ScriptStatusEnum]] = {
    ScriptStatusEnum.HEALTHY: {ScriptStatusEnum.UNSTABLE, ScriptStatusEnum.DEGRADED},
    ScriptStatusEnum.UNSTABLE: {ScriptStatusEnum.HEALTHY, ScriptStatusEnum.DEGRADED},
    ScriptStatusEnum.DEGRADED: {ScriptStatusEnum.HEALTHY, ScriptStatusEnum.UNSTABLE},
}


@dataclass(frozen=True)
class ScriptStatus(ValueObject):
    """脚本健康状态值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).lower()
        try:
            ScriptStatusEnum(v)
        except ValueError:
            raise DomainValidationError(
                f"非法脚本状态 '{self.value}'，仅支持 "
                f"{[e.value for e in ScriptStatusEnum]}"
            )
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ScriptFramework(ValueObject):
    """脚本框架类型（pytest/playwright/selenium 等）。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).strip() or "pytest"
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


__all__ = ["ScriptStatus", "ScriptStatusEnum", "ALLOWED_TRANSITIONS", "ScriptFramework"]
