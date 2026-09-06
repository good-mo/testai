"""测试计划领域服务：跨聚合/对象的不变量策略。

把"状态迁移是否合法"“归档规则”“是否具备发布/关闭条件”等业务规则独立成
可测试的无状态策略，供聚合与流程复用，避免规则散落各处。
"""
from __future__ import annotations

from app.domain.common.exceptions import DomainValidationError
from app.domain.test_plan.domain.value_objects.status import PlanStatus, PlanStatusEnum


class TestPlanPolicy:
    """测试计划生命周期策略（无状态领域服务）。"""

    def ensure_transition_allowed(self, current: PlanStatus, target: PlanStatus) -> None:
        if current == target:
            return
        if not current.can_transition_to(target):
            raise DomainValidationError(
                f"不允许从状态 '{current}' 迁移到 '{target}'"
            )

    def is_finished(self, status: PlanStatus) -> bool:
        """计划是否处于已完成/已归档的终结态。"""
        return status.value in (PlanStatusEnum.COMPLETED, PlanStatusEnum.ARCHIVED)
