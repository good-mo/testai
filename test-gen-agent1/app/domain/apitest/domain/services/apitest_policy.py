"""接口测试领域服务：跨聚合/对象的不变量策略。

承载不适合放入单个实体方法、或依赖多个聚合的业务规则。目前包含：
  - 状态迁移合法性校验（ApiCase / Scenario 共用状态机策略）
  - 接口用例引用的定义是否存在等关联校验
"""
from __future__ import annotations

from app.domain.apitest.domain.value_objects.status import (
    ApiCaseStatus,
    ScenarioStatus,
)
from app.domain.common.exceptions import DomainValidationError


class ApiStatePolicy:
    """接口测试状态机策略（无状态领域服务）。"""

    def ensure_case_transition_allowed(
        self, current: ApiCaseStatus, target: ApiCaseStatus
    ) -> None:
        """校验接口用例状态迁移合法性。"""
        if target.is_deprecated:
            raise DomainValidationError(
                "不应直接置为 'deprecated'；请使用 ApiCase.delete() 触发软删除"
            )
        if not current.can_transition_to(target):
            raise DomainValidationError(
                f"不允许接口用例从状态 '{current}' 迁移到 '{target}'"
            )

    def ensure_scenario_transition_allowed(
        self, current: ScenarioStatus, target: ScenarioStatus
    ) -> None:
        """校验接口场景状态迁移合法性。"""
        if target.is_deprecated:
            raise DomainValidationError(
                "不应直接置为 'deprecated'；请使用 Scenario.delete() 触发软删除"
            )
        if not current.can_transition_to(target):
            raise DomainValidationError(
                f"不允许接口场景从状态 '{current}' 迁移到 '{target}'"
            )
