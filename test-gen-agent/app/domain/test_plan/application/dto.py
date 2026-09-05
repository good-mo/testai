"""测试计划应用层输入/输出 DTO。

面向聚合操作接收显式 DTO（而非裸 dict），与 Web 层 Pydantic 请求体解耦。
此处用 dataclass 表达简单命令，保持零框架依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CreatePlanCommand:
    name: str
    description: str = ""
    priority: str = "P2"
    module_id: str = "root"
    project_id: str = ""
    created_by: str = "admin"
    start_time: float = 0
    end_time: float = 0
    tags: List[str] = field(default_factory=list)
    pass_threshold: float = 100
    test_planning: bool = False
    auto_update_status: bool = False
    repeat_case: bool = False
    plan_type: str = "TEST_PLAN"
    group_id: str = "NONE"
    operator: str = "system"


@dataclass
class UpdatePlanCommand:
    plan_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    module_id: Optional[str] = None
    project_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    tags: Optional[List[str]] = None
    pass_threshold: Optional[float] = None
    test_planning: Optional[bool] = None
    auto_update_status: Optional[bool] = None
    repeat_case: Optional[bool] = None
    operator: str = "system"


@dataclass
class ChangeStatusCommand:
    plan_id: str
    target_status: str
    operator: str = "system"


@dataclass
class AddCaseCommand:
    plan_id: str
    case_id: str
    case_type: str = "functional"
    operator: str = "system"


@dataclass
class RemoveCaseCommand:
    plan_id: str
    rel_id: str
    operator: str = "system"


@dataclass
class UpdateCaseStatusCommand:
    plan_id: str
    rel_id: str
    status: str
    operator: str = "system"


@dataclass
class ReorderCasesCommand:
    plan_id: str
    ordered_rel_ids: List[str]
    operator: str = "system"


@dataclass
class PlanListQuery:
    keyword: str = ""
    status: str = ""
    project_id: str = ""
    module_ids: Optional[List[str]] = None
    plan_type: str = ""
    group_id: str = ""
    limit: int = 100
    offset: int = 0
