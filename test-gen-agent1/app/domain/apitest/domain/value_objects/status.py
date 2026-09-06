"""接口用例/场景状态值对象 + 状态机定义。"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class ApiCaseStatusEnum(str, Enum):
    DRAFT = "draft"            # 草稿
    ACTIVE = "active"          # 启用（可执行）
    APPROVED = "approved"      # 已通过评审（legacy 兼容）
    DEPRECATED = "deprecated"  # 已废弃（软删除/回收站）


# 用例状态迁移矩阵（业务不变量）
ALLOWED_CASE_TRANSITIONS: Dict[ApiCaseStatusEnum, Set[ApiCaseStatusEnum]] = {
    ApiCaseStatusEnum.DRAFT: {ApiCaseStatusEnum.ACTIVE, ApiCaseStatusEnum.APPROVED,
                              ApiCaseStatusEnum.DEPRECATED},
    ApiCaseStatusEnum.ACTIVE: {ApiCaseStatusEnum.DRAFT, ApiCaseStatusEnum.APPROVED,
                               ApiCaseStatusEnum.DEPRECATED},
    ApiCaseStatusEnum.APPROVED: {ApiCaseStatusEnum.DRAFT, ApiCaseStatusEnum.ACTIVE,
                                 ApiCaseStatusEnum.DEPRECATED},
    ApiCaseStatusEnum.DEPRECATED: set(),  # 回收站内不可再流转
}


class ApiCaseStatus(ValueObject):
    """接口用例状态值对象，自带状态机校验。"""

    def __init__(self, value):
        if isinstance(value, ApiCaseStatusEnum):
            v = value
        else:
            raw = str(value).lower()
            try:
                v = ApiCaseStatusEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法接口用例状态 '{value}'，仅支持 "
                    f"{[e.value for e in ApiCaseStatusEnum]}"
                )
        object.__setattr__(self, "value", v)

    @property
    def is_deprecated(self) -> bool:
        return self.value is ApiCaseStatusEnum.DEPRECATED

    def can_transition_to(self, target: "ApiCaseStatus") -> bool:
        return target.value in ALLOWED_CASE_TRANSITIONS.get(self.value, set())

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ApiCaseStatus):
            return self.value is other.value
        if isinstance(other, ApiCaseStatusEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other
        return NotImplemented


class ScenarioStatusEnum(str, Enum):
    DRAFT = "draft"            # 草稿
    ACTIVE = "active"          # 启用
    APPROVED = "approved"      # 已通过评审（legacy 兼容）
    DEPRECATED = "deprecated"  # 已废弃（软删除/回收站）


ALLOWED_SCENARIO_TRANSITIONS: Dict[ScenarioStatusEnum, Set[ScenarioStatusEnum]] = {
    ScenarioStatusEnum.DRAFT: {ScenarioStatusEnum.ACTIVE, ScenarioStatusEnum.APPROVED,
                               ScenarioStatusEnum.DEPRECATED},
    ScenarioStatusEnum.ACTIVE: {ScenarioStatusEnum.DRAFT, ScenarioStatusEnum.APPROVED,
                                ScenarioStatusEnum.DEPRECATED},
    ScenarioStatusEnum.APPROVED: {ScenarioStatusEnum.DRAFT, ScenarioStatusEnum.ACTIVE,
                                  ScenarioStatusEnum.DEPRECATED},
    ScenarioStatusEnum.DEPRECATED: set(),
}


class ScenarioStatus(ValueObject):
    """接口场景状态值对象，自带状态机校验。"""

    def __init__(self, value):
        if isinstance(value, ScenarioStatusEnum):
            v = value
        else:
            raw = str(value).lower()
            try:
                v = ScenarioStatusEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法场景状态 '{value}'，仅支持 "
                    f"{[e.value for e in ScenarioStatusEnum]}"
                )
        object.__setattr__(self, "value", v)

    @property
    def is_deprecated(self) -> bool:
        return self.value is ScenarioStatusEnum.DEPRECATED

    def can_transition_to(self, target: "ScenarioStatus") -> bool:
        return target.value in ALLOWED_SCENARIO_TRANSITIONS.get(self.value, set())

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ScenarioStatus):
            return self.value is other.value
        if isinstance(other, ScenarioStatusEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other
        return NotImplemented
