"""计划关联用例（聚合内值对象）。

TestPlan 聚合内以"关联用例"的方式编排用例（功能/接口/场景），每条关联
记录了用例来源、类型、执行状态与排序位置。作为不可变值对象被聚合根托管，
修改通过聚合根方法重建新值（保持聚合一致性）。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.common.value_objects import ValueObject
from app.domain.test_plan.domain.value_objects.case_status import CaseExecutionStatus
from app.domain.test_plan.domain.value_objects.case_type import CaseType


@dataclass(frozen=True)
class PlanCase(ValueObject):
    """计划关联用例值对象。"""

    rel_id: str
    plan_id: str
    case_id: str
    case_type: CaseType = CaseType("functional")
    status: CaseExecutionStatus = CaseExecutionStatus("pending")
    position: int = 0

    def __post_init__(self) -> None:
        # 统一把入参归一化为类型化值对象
        object.__setattr__(
            self, "case_type",
            self.case_type if isinstance(self.case_type, CaseType) else CaseType(str(self.case_type)),
        )
        object.__setattr__(
            self, "status",
            self.status if isinstance(self.status, CaseExecutionStatus)
            else CaseExecutionStatus(str(self.status)),
        )
        object.__setattr__(self, "position", int(self.position))

    def with_status(self, status: str) -> "PlanCase":
        return PlanCase(
            rel_id=self.rel_id,
            plan_id=self.plan_id,
            case_id=self.case_id,
            case_type=self.case_type,
            status=status,
            position=self.position,
        )

    def with_position(self, pos: int) -> "PlanCase":
        return PlanCase(
            rel_id=self.rel_id,
            plan_id=self.plan_id,
            case_id=self.case_id,
            case_type=self.case_type,
            status=self.status,
            position=pos,
        )
