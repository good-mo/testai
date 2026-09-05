"""缺陷领域服务：跨聚合/对象的不变量策略。

将"状态迁移合法性"与"是否可进入处理中/关闭"等业务规则独立成可测试的
无状态策略，供聚合与状态流转复用，避免规则散落各处。
"""
from __future__ import annotations

from app.domain.common.exceptions import DomainValidationError
from app.domain.defects.domain.value_objects.status import (
    DefectStatus,
    DefectStatusEnum,
)


class DefectLifecyclePolicy:
    """缺陷生命周期策略（无状态领域服务）。"""

    def ensure_transition_allowed(self, current: DefectStatus, target: DefectStatus) -> None:
        if target.is_trashed:
            raise DomainValidationError(
                "不应直接流转到回收站；请使用 Defect.delete() 触发软删除"
            )
        if not current.can_transition_to(target):
            raise DomainValidationError(
                f"不允许从状态 '{current}' 迁移到 '{target}'"
            )

    def is_closed(self, status: DefectStatus) -> bool:
        """缺陷是否处于已终结状态（关闭/不予修复）。"""
        return status.value in (DefectStatusEnum.CLOSED, DefectStatusEnum.WONT_FIX)
