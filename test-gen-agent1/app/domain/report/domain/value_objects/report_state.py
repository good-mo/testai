"""报告产物生命周期状态值对象 + 状态机。

报告产物是落在"报告中心"的文件制品，其生命周期为：
    active（可用/在报告列表） ⇄ trash（回收站）
  - active → trash：移入回收站（软删除）
  - trash  → active：从回收站恢复
  - trash  → purged：彻底清除（最终销毁，无状态回退）

主动作不进入状态迁移矩阵（purge 是物理删除），状态机只约束可被
再次装载的状态切换，避免从"已彻底清除"的产物上继续执行命令。
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class ReportStateEnum(str, Enum):
    ACTIVE = "active"    # 在报告列表（可用）
    TRASH = "trash"      # 在回收站
    PURGED = "purged"    # 已彻底删除（终态，无文件可装载）


# 业务允许的状态迁移（不变量：产物文件生命周期）
ALLOWED_TRANSITIONS: Dict[ReportStateEnum, Set[ReportStateEnum]] = {
    ReportStateEnum.ACTIVE: {ReportStateEnum.TRASH},
    ReportStateEnum.TRASH: {ReportStateEnum.ACTIVE},
    ReportStateEnum.PURGED: set(),
}


class ReportState(ValueObject):
    """报告产物状态值对象，自带状态机校验。"""

    def __init__(self, value):
        if isinstance(value, ReportStateEnum):
            v = value
        else:
            raw = str(value).lower()
            if raw in ("", "none"):
                raw = ReportStateEnum.ACTIVE.value
            try:
                v = ReportStateEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法报告状态 '{value}'，仅支持 "
                    f"{[e.value for e in ReportStateEnum]}"
                )
        object.__setattr__(self, "value", v)

    @property
    def is_active(self) -> bool:
        return self.value is ReportStateEnum.ACTIVE

    @property
    def is_trashed(self) -> bool:
        return self.value is ReportStateEnum.TRASH

    @property
    def is_purged(self) -> bool:
        return self.value is ReportStateEnum.PURGED

    def can_transition_to(self, target: "ReportState") -> bool:
        return target.value in ALLOWED_TRANSITIONS.get(self.value, set())

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ReportState):
            return self.value is other.value
        if isinstance(other, ReportStateEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other
        return NotImplemented


__all__ = ["ReportState", "ReportStateEnum", "ALLOWED_TRANSITIONS"]
