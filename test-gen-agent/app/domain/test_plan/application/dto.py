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


# ==============================================================================
# 从 models/test_plan.py 迁移
# ==============================================================================

# app/models/test_plan.py
"""测试计划域 Pydantic 请求体模型。

覆盖：测试计划 CRUD/归档/复制/排序、模块管理、需求/用例关联、
功能用例分页与批量操作、报告生成/重命名/删除。
字段含 TestPilot 风格驼峰别名（moduleId/projectId/current/pageSize）。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── 测试计划 ─────────────────────────────────────────────
class TestPlanCreate(BaseModel):
    """创建测试计划。"""

    id: Optional[str] = Field("", description="计划 ID")
    name: str = Field("", description="计划名称")
    description: str = Field("", description="计划描述")
    priority: str = Field("P2", description="优先级: P0/P1/P2/P3")
    module_id: str = Field("root", description="所属模块 ID")
    moduleId: str = Field("root", description="所属模块 ID（别名）")
    project_id: str = Field("", description="所属项目 ID")
    projectId: str = Field("", description="所属项目 ID（别名）")
    create_user: str = Field("admin", description="创建人")
    createUser: str = Field("admin", description="创建人（别名）")
    start_time: Optional[float] = Field(None, description="开始时间戳")
    end_time: Optional[float] = Field(None, description="结束时间戳")
    planned_start_time: Optional[float] = Field(None, description="计划开始时间")
    planned_end_time: Optional[float] = Field(None, description="计划结束时间")
    plannedStartTime: Optional[float] = Field(None, description="计划开始时间（前端别名）")
    plannedEndTime: Optional[float] = Field(None, description="计划结束时间（前端别名）")
    startTime: Optional[float] = Field(None, description="开始时间戳（前端别名）")
    endTime: Optional[float] = Field(None, description="结束时间戳（前端别名）")
    tags: Optional[List[str]] = Field([], description="标签")
    passThreshold: Optional[float] = Field(100, description="通过阈值（%）")
    pass_threshold: Optional[float] = Field(100, description="通过阈值（%）（别名）")
    testPlanning: Optional[bool] = Field(False, description="是否开启测试规划")
    automaticStatusUpdate: Optional[bool] = Field(False, description="自动更新功能用例状态")
    repeatCase: Optional[bool] = Field(False, description="允许重复添加用例")
    type: Optional[str] = Field("TEST_PLAN", description="类型: TEST_PLAN 测试计划 / GROUP 计划组")
    group_id: Optional[str] = Field("NONE", description="所属计划组 ID")
    groupId: Optional[str] = Field("NONE", description="所属计划组 ID（前端别名）")

    model_config = {"extra": "allow"}


class TestPlanUpdate(BaseModel):
    """更新测试计划。"""

    id: str = Field("", description="计划 ID")
    name: Optional[str] = Field(None, description="计划名称")
    description: Optional[str] = Field(None, description="计划描述")
    priority: Optional[str] = Field(None, description="优先级")
    status: Optional[str] = Field(None, description="状态")
    module_id: Optional[str] = Field(None, description="所属模块 ID")
    moduleId: Optional[str] = Field(None, description="所属模块 ID（别名）")
    start_time: Optional[float] = Field(None, description="开始时间戳")
    end_time: Optional[float] = Field(None, description="结束时间戳")
    planned_start_time: Optional[float] = Field(None, description="计划开始时间")
    planned_end_time: Optional[float] = Field(None, description="计划结束时间")
    plannedStartTime: Optional[float] = Field(None, description="计划开始时间（前端别名）")
    plannedEndTime: Optional[float] = Field(None, description="计划结束时间（前端别名）")
    startTime: Optional[float] = Field(None, description="开始时间戳（前端别名）")
    endTime: Optional[float] = Field(None, description="结束时间戳（前端别名）")
    tags: Optional[List[str]] = Field(None, description="标签")
    passThreshold: Optional[float] = Field(None, description="通过阈值（%）")
    pass_threshold: Optional[float] = Field(None, description="通过阈值（%）（别名）")
    testPlanning: Optional[bool] = Field(None, description="是否开启测试规划")
    automaticStatusUpdate: Optional[bool] = Field(None, description="自动更新功能用例状态")
    repeatCase: Optional[bool] = Field(None, description="允许重复添加用例")

    model_config = {"extra": "allow"}


class TestPlanPageQuery(BaseModel):
    """测试计划分页查询。"""

    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, le=500, description="每页条数")
    keyword: str = Field("", description="搜索关键字")
    projectId: Optional[str] = Field("", description="所属项目 ID")
    moduleId: Optional[str] = Field("", description="模块 ID 过滤")
    status: Optional[str] = Field(None, description="状态过滤")
    priority: Optional[str] = Field(None, description="优先级过滤")
    moduleIds: Optional[Any] = Field(None, description="模块 ID 列表（可为字符串或列表）")
    combine: Optional[Dict[str, Any]] = Field(None, description="附加过滤")
    sort: Optional[Dict[str, Any]] = Field(None, description="排序")
    type: Optional[str] = Field("", description="类型过滤: TEST_PLAN/GROUP/ALL(默认全部)")
    groupId: Optional[str] = Field("", description="所属计划组 ID 过滤")

    model_config = {"extra": "allow"}


class TestPlanIdBody(BaseModel):
    """按 ID 操作单个测试计划（删除/归档/复制等）。"""

    id: str = Field("", description="计划 ID")

    model_config = {"extra": "allow"}


class TestPlanIdsBody(BaseModel):
    """测试计划批量操作（删除/归档/复制/编辑/移动）。"""

    ids: List[str] = Field([], description="计划 ID 列表")

    model_config = {"extra": "allow"}


# ── 模块管理 ─────────────────────────────────────────────
class TestPlanModuleAdd(BaseModel):
    """新增测试计划模块。"""

    name: str = Field("", description="模块名称")
    parent_id: str = Field("root", description="父模块 ID")
    parentId: str = Field("root", description="父模块 ID（别名）")

    model_config = {"extra": "allow"}


class TestPlanModuleUpdate(BaseModel):
    """更新测试计划模块。"""

    id: str = Field("", description="模块 ID")
    name: str = Field("", description="模块名称")

    model_config = {"extra": "allow"}


# ── 关联管理 ─────────────────────────────────────────────
class AssociationPageQuery(BaseModel):
    """关联分页查询。"""

    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, description="每页条数")
    keyword: str = Field("", description="搜索关键字")
    plan_id: Optional[str] = Field("", description="测试计划 ID")
    planId: Optional[str] = Field("", description="测试计划 ID（别名）")
    project_id: Optional[str] = Field("", description="所属项目 ID")
    projectId: Optional[str] = Field("", description="所属项目 ID（别名）")

    model_config = {"extra": "allow"}


# ── 功能用例 ─────────────────────────────────────────────
class FunctionalCasePageQuery(BaseModel):
    """测试计划功能用例分页。"""

    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, description="每页条数")
    keyword: str = Field("", description="搜索关键字")
    plan_id: Optional[str] = Field("", description="测试计划 ID")
    planId: Optional[str] = Field("", description="测试计划 ID（别名）")
    module_id: Optional[str] = Field("", description="模块 ID 过滤")
    moduleId: Optional[str] = Field("", description="模块 ID 过滤（别名）")
    combine: Optional[Dict[str, Any]] = Field(None, description="附加过滤")
    sort: Optional[Dict[str, Any]] = Field(None, description="排序")

    model_config = {"extra": "allow"}


class FunctionalCaseRunBody(BaseModel):
    """执行计划下功能用例。"""

    plan_id: Optional[str] = Field("", description="测试计划 ID")
    planId: Optional[str] = Field("", description="测试计划 ID（别名）")
    case_id: Optional[str] = Field("", description="用例 ID")
    caseId: Optional[str] = Field("", description="用例 ID（别名）")
    ids: Optional[List[str]] = Field([], description="用例 ID 列表")

    model_config = {"extra": "allow"}


# ── 报告 ─────────────────────────────────────────────────
class TestPlanReportGenerate(BaseModel):
    """测试计划报告生成。"""

    plan_id: Optional[str] = Field("", description="测试计划 ID")
    planId: Optional[str] = Field("", description="测试计划 ID（别名）")
    report_id: Optional[str] = Field("", description="报告 ID")
    reportId: Optional[str] = Field("", description="报告 ID（别名）")

    model_config = {"extra": "allow"}


class TestPlanReportRename(BaseModel):
    """测试计划报告重命名。"""

    id: str = Field("", description="报告 ID")
    name: str = Field("", description="新名称")
    reportName: str = Field("", description="新名称（前端别名）")

    def effective_name(self) -> str:
        return self.name or self.reportName

    model_config = {"extra": "allow"}


# ── 报告分页/明细（reportId + 分页）────────────────────
class ReportPageQuery(BaseModel):
    """测试计划报告分页（含项目过滤与集成筛选）。"""

    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, description="每页条数")
    keyword: str = Field("", description="搜索关键字")
    project_id: Optional[str] = Field("", description="所属项目 ID")
    projectId: Optional[str] = Field("", description="所属项目 ID（别名）")
    plan_id: Optional[str] = Field("", description="测试计划 ID")
    planId: Optional[str] = Field("", description="测试计划 ID（别名）")
    filter: Optional[Dict[str, Any]] = Field(None, description="报告筛选，如 integrated 列表")

    model_config = {"extra": "allow"}


class ReportDetailPageQuery(BaseModel):
    """报告/分享报告详情分页（reportId + keyword）。"""

    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, description="每页条数")
    keyword: str = Field("", description="搜索关键字")
    report_id: Optional[str] = Field("", description="报告 ID")
    reportId: Optional[str] = Field("", description="报告 ID（别名）")

    model_config = {"extra": "allow"}


class PlanResourcePageQuery(BaseModel):
    """计划下资源（接口用例/场景/缺陷）分页。"""

    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, description="每页条数")
    keyword: str = Field("", description="搜索关键字")
    plan_id: Optional[str] = Field("", description="测试计划 ID")
    planId: Optional[str] = Field("", description="测试计划 ID（别名）")
    module_id: Optional[str] = Field("", description="模块 ID 过滤")
    moduleIds: Optional[Any] = Field(None, description="模块 ID 列表（可为字符串或列表）")

    model_config = {"extra": "allow"}


# ── 计划关联用例 ────────────────────────────────────────
class PlanAssociationBody(BaseModel):
    """测试计划关联用例（association/add）。"""

    plan_id: Optional[str] = Field("", description="测试计划 ID")
    planId: Optional[str] = Field("", description="测试计划 ID（别名）")
    case_ids: Optional[List[str]] = Field([], description="用例 ID 列表")
    caseIds: Optional[List[str]] = Field([], description="用例 ID 列表（别名）")
    case_type: Optional[str] = Field("functional", description="用例类型")
    caseType: Optional[str] = Field("functional", description="用例类型（别名）")

    model_config = {"extra": "allow"}


class PlanRelStatusBody(BaseModel):
    """更新计划关联用例执行状态（association/update-status）。"""

    id: str = Field("", description="关联 ID")
    status: str = Field("pending", description="执行状态")

    model_config = {"extra": "allow"}


class FunctionalCaseDetailBody(BaseModel):
    """计划功能用例详情。"""

    case_id: Optional[str] = Field("", description="用例 ID")
    caseId: Optional[str] = Field("", description="用例 ID（别名）")

    model_config = {"extra": "allow"}


# ── 定时任务配置 ────────────────────────────────────────
class ScheduleConfigBody(BaseModel):
    """测试计划定时任务配置（schedule-config）。"""

    resourceId: str = Field("", description="测试计划 ID（resourceId）")
    cron: str = Field("", description="cron 表达式")
    enable: bool = Field(True, description="是否启用")
    runConfig: Optional[Dict[str, Any]] = Field(None, description="运行配置（runMode）")
    projectId: str = Field("", description="所属项目 ID")

    def effective_run_mode(self) -> str:
        cfg = self.runConfig or {}
        return str(cfg.get("runMode") or "SERIAL")

    model_config = {"extra": "allow"}


class BatchScheduleConfigBody(BaseModel):
    """批量配置测试计划定时任务（batch-schedule-config）。"""

    selectIds: Any = Field([], description="测试计划 ID 列表（兼容字符串或列表）")
    cron: str = Field("", description="cron 表达式")
    enable: bool = Field(True, description="是否启用")
    runConfig: Optional[Dict[str, Any]] = Field(None, description="运行配置（runMode）")
    projectId: str = Field("", description="所属项目 ID")

    def effective_ids(self) -> List[str]:
        ids = self.selectIds
        if isinstance(ids, str):
            ids = [ids]
        return ids

    def effective_run_mode(self) -> str:
        cfg = self.runConfig or {}
        return str(cfg.get("runMode") or "SERIAL")

    model_config = {"extra": "allow"}


# ── 报告批量/分享 ──────────────────────────────────────
class TestPlanBatchParamBody(BaseModel):
    """测试计划报告批量导出 ID 集合（report/batch-param）。"""

    selectAll: bool = Field(False, description="是否全选")
    selectIds: List[str] = Field([], description="勾选中的计划 ID")
    excludeIds: List[str] = Field([], description="需要排除的计划 ID")

    model_config = {"extra": "allow"}


class TestPlanShareGenBody(BaseModel):
    """测试计划报告生成分享链接（report/share/gen）。"""

    reportId: str = Field("", description="报告 ID")
    id: str = Field("", description="报告 ID（别名）")

    def effective_report_id(self) -> str:
        return self.reportId or self.id

    model_config = {"extra": "allow"}
