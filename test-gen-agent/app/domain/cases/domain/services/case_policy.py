"""用例领域服务：跨聚合/跨对象的不变量策略。

领域服务承载不适合放入单个实体方法、且依赖多个聚合或外部上下文读取的
业务规则。本服务将"状态迁移是否允许"独立成可测试策略，供聚合与评审
流程复用，避免状态机规则散落在各处。
"""
from __future__ import annotations

from app.domain.cases.domain.value_objects.case_status import (
    CaseStatus,
    CaseStatusEnum,
)
from app.domain.common.exceptions import DomainValidationError


class CaseStatePolicy:
    """用例状态机策略（无状态领域服务）。"""

    def ensure_transition_allowed(self, current: CaseStatus, target: CaseStatus) -> None:
        """校验迁移合法性，非法时抛领域异常。"""
        if not current.can_transition_to(target):
            raise DomainValidationError(
                f"不允许从状态 '{current}' 迁移到 '{target}'"
            )
        if target.is_deprecated:
            # 软删除需显式走 delete()，不应通过 set_status 直接置为 deprecated
            raise DomainValidationError(
                "不应直接置为 'deprecated'；请使用 TestCase.delete() 触发软删除"
            )

    def review_approves_case(self, current: CaseStatus) -> CaseStatusEnum:
        """评审通过：仅 review/草稿 状态可被批准。"""
        if current.value not in (CaseStatusEnum.REVIEW, CaseStatusEnum.DRAFT):
            raise DomainValidationError(
                f"状态 '{current}' 的用例不可被评审通过"
            )
        return CaseStatusEnum.APPROVED
