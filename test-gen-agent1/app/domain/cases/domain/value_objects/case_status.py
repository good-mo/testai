"""用例生命周期状态值对象 + 状态机定义。"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class CaseStatusEnum(str, Enum):
    DRAFT = "draft"          # 草稿
    REVIEW = "review"        # 评审中
    APPROVED = "approved"    # 已批准
    DEPRECATED = "deprecated"  # 已废弃（软删除/回收站）


# 允许的状态迁移矩阵（业务不变量）
ALLOWED_TRANSITIONS: Dict[CaseStatusEnum, Set[CaseStatusEnum]] = {
    CaseStatusEnum.DRAFT: {CaseStatusEnum.REVIEW, CaseStatusEnum.DEPRECATED, CaseStatusEnum.APPROVED},
    CaseStatusEnum.REVIEW: {CaseStatusEnum.APPROVED, CaseStatusEnum.DRAFT, CaseStatusEnum.DEPRECATED},
    CaseStatusEnum.APPROVED: {CaseStatusEnum.DEPRECATED},
    CaseStatusEnum.DEPRECATED: set(),  # 回收站内不可再流转
}


class CaseStatus(ValueObject):
    """用例状态值对象，自带状态机校验（内聚不变量于值对象）。"""

    value: CaseStatusEnum

    def __init__(self, value):
        if isinstance(value, CaseStatusEnum):
            v = value
        else:
            raw = str(value).lower()
            try:
                v = CaseStatusEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法用例状态 '{value}'，仅支持 "
                    f"{[e.value for e in CaseStatusEnum]}"
                )
        object.__setattr__(self, "value", v)

    @property
    def is_deprecated(self) -> bool:
        return self.value is CaseStatusEnum.DEPRECATED

    def can_transition_to(self, target: "CaseStatus") -> bool:
        return target.value in ALLOWED_TRANSITIONS.get(self.value, set())

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CaseStatus):
            return self.value is other.value
        if isinstance(other, CaseStatusEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other
        return NotImplemented
