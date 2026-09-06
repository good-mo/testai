"""接口测试应用层输入/输出 DTO。

面向聚合操作接收显式 DTO（而非裸 dict），与 Web 层 Pydantic 请求体解耦。
此处用 dataclass 表达简单命令，保持零框架依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ── ApiDefinition ────────────────────────────────────────
@dataclass
class CreateDefinitionCommand:
    """创建接口定义。"""

    name: str
    protocol: str = "HTTP"
    method: str = "GET"
    path: str = ""
    headers: Optional[dict] = None
    body: str = ""
    query: Optional[dict] = None
    params: Optional[dict] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)
    module_id: str = ""
    project_id: str = ""
    version: str = "v1"
    operator: str = "system"


@dataclass
class UpdateDefinitionCommand:
    """更新接口定义。"""

    definition_id: str
    name: Optional[str] = None
    protocol: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    headers: Optional[dict] = None
    body: Optional[str] = None
    query: Optional[dict] = None
    params: Optional[dict] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    module_id: Optional[str] = None
    operator: str = "system"


@dataclass
class DefinitionListQuery:
    """接口定义分页查询参数。"""

    keyword: str = ""
    project_id: str = ""
    limit: int = 100
    offset: int = 0
    include_latest_only: bool = True
    protocols: Optional[List[str]] = None
    module_ids: Optional[List[str]] = None


@dataclass
class DeleteDefinitionCommand:
    """删除接口定义。"""

    definition_id: str
    operator: str = "system"
    reason: str = ""


@dataclass
class RestoreDefinitionCommand:
    """恢复接口定义。"""

    definition_id: str
    operator: str = "system"


@dataclass
class CreateVersionCommand:
    """创建接口定义新版本。"""

    definition_id: str
    version: str = ""
    operator: str = "system"


# ── ApiCase ──────────────────────────────────────────────
@dataclass
class CreateApiCaseCommand:
    """创建接口用例。"""

    name: str
    api_definition_id: str = ""
    request: Optional[dict] = None
    asserts: Optional[List[dict]] = None
    pre_scripts: Optional[List[str]] = None
    post_scripts: Optional[List[str]] = None
    pre_sql: Optional[List[dict]] = None
    post_sql: Optional[List[dict]] = None
    variables: Optional[List[dict]] = None
    logic_controllers: Optional[List[dict]] = None
    environment_id: str = ""
    priority: str = "P2"
    description: str = ""
    project_id: str = ""
    operator: str = "system"


@dataclass
class UpdateApiCaseCommand:
    """更新接口用例。"""

    case_id: str
    name: Optional[str] = None
    api_definition_id: Optional[str] = None
    request: Optional[dict] = None
    asserts: Optional[List[dict]] = None
    pre_scripts: Optional[List[str]] = None
    post_scripts: Optional[List[str]] = None
    pre_sql: Optional[List[dict]] = None
    post_sql: Optional[List[dict]] = None
    variables: Optional[List[dict]] = None
    logic_controllers: Optional[List[dict]] = None
    environment_id: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[str] = None
    operator: str = "system"


@dataclass
class ChangeApiCaseStatusCommand:
    """变更接口用例状态。"""

    case_id: str
    target_status: str
    operator: str = "system"


@dataclass
class CaseListQuery:
    """接口用例分页查询参数。"""

    keyword: str = ""
    project_id: str = ""
    api_definition_id: str = ""
    limit: int = 100
    offset: int = 0


@dataclass
class DeleteCaseCommand:
    """删除接口用例。"""

    case_id: str
    operator: str = "system"
    reason: str = ""


@dataclass
class RestoreCaseCommand:
    """恢复接口用例。"""

    case_id: str
    operator: str = "system"


# ── Scenario ─────────────────────────────────────────────
@dataclass
class CreateScenarioCommand:
    """创建接口场景。"""

    name: str
    steps: Optional[List[dict]] = None
    description: str = ""
    environment_id: str = ""
    project_id: str = ""
    operator: str = "system"


@dataclass
class UpdateScenarioCommand:
    """更新接口场景。"""

    scenario_id: str
    name: Optional[str] = None
    steps: Optional[List[dict]] = None
    description: Optional[str] = None
    status: Optional[str] = None
    environment_id: Optional[str] = None
    project_id: Optional[str] = None
    operator: str = "system"


@dataclass
class ScenarioListQuery:
    """接口场景分页查询参数。"""

    keyword: str = ""
    project_id: str = ""
    limit: int = 100
    offset: int = 0


@dataclass
class DeleteScenarioCommand:
    """删除接口场景。"""

    scenario_id: str
    operator: str = "system"
    reason: str = ""


@dataclass
class RestoreScenarioCommand:
    """恢复接口场景。"""

    scenario_id: str
    operator: str = "system"


# ── Mock 服务 ───────────────────────────────────────────
@dataclass
class CreateMockCommand:
    """创建 Mock 服务。"""

    name: str = "未命名Mock服务"
    api_definition_id: str = ""
    method: str = "GET"
    path: str = ""
    status_code: int = 200
    response_body: str = ""
    response_headers: Optional[dict] = None
    delay_ms: int = 0
    active: int = 1
    description: str = ""
    project_id: str = ""
    match_type: str = "exact"
    match_script: str = ""
    operator: str = "system"


@dataclass
class UpdateMockCommand:
    """更新 Mock 服务。"""

    mock_id: str
    name: Optional[str] = None
    api_definition_id: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    response_headers: Optional[dict] = None
    delay_ms: Optional[int] = None
    active: Optional[int] = None
    description: Optional[str] = None
    project_id: Optional[str] = None
    match_type: Optional[str] = None
    match_script: Optional[str] = None
    operator: str = "system"


@dataclass
class MockListQuery:
    """Mock 服务分页查询参数。"""

    keyword: str = ""
    project_id: str = ""
    limit: int = 100
    offset: int = 0


@dataclass
class DeleteMockCommand:
    """删除 Mock 服务。"""

    mock_id: str
    operator: str = "system"
    reason: str = ""


@dataclass
class RestoreMockCommand:
    """恢复 Mock 服务。"""

    mock_id: str
    operator: str = "system"


@dataclass
class PurgeMockCommand:
    """彻底删除 Mock 服务。"""

    mock_id: str
    operator: str = "system"


@dataclass
class BatchDeleteMocksCommand:
    """批量软删除 Mock 服务。"""

    ids: List[str]
    operator: str = "system"


@dataclass
class BatchRestoreMocksCommand:
    """批量恢复 Mock 服务。"""

    ids: List[str]
    operator: str = "system"


@dataclass
class BatchPurgeMocksCommand:
    """批量彻底删除 Mock 服务。"""

    ids: List[str]
    operator: str = "system"


@dataclass
class RunMockRequestCommand:
    """Mock 请求匹配（running）。"""

    method: str = "GET"
    path: str = "/"
    base_path: str = ""
    query_params: Optional[dict] = None
    request_body: str = ""


# ==============================================================================
# 从 models/apitest.py 迁移
# ==============================================================================

# app/models/apitest.py
"""接口测试（apitest）域 Pydantic 请求体模型。

覆盖：接口定义/版本/用例/场景/Mock/环境 CRUD、调试、导入、
模块管理、批量操作、执行、关注。字段含 TestPilot 风格驼峰别名。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class _LenientRequest(BaseModel):
    """历史兼容：容忍前端经 axios 拦截器发送的裸标量请求体。

    迁移背景：旧路由用 read_body()/read_writable_body() 读取请求体时，
    会把裸字符串 `"x"` 归一化成 `{"id": "x"}`、数组归一化成
    `{"ids": [...]}`、空体归一化成 `{}`（见 app/core/response.py）。

    当这些路由改用 Pydantic 请求体模型后，若不加处理，FastAPI 会把上述
    裸标量判为 422。故在此把同一段归一化上移到模型层，保证旧前端
    （params 当 data 发的历史调用）不被类型校验打断。
    """

    @model_validator(mode="before")
    @classmethod
    def _lenient_coerce(cls, raw):
        if isinstance(raw, str):
            return {"id": raw}
        if isinstance(raw, list):
            return {"ids": raw}
        if raw is None:
            return {}
        return raw


# ── 接口定义 ─────────────────────────────────────────────
class ApiDefinitionCreate(_LenientRequest):
    """创建接口定义。"""

    id: Optional[str] = Field("", description="定义 ID（更新/迁移时）")
    name: str = Field("", description="接口名称")
    method: str = Field("GET", description="HTTP 方法")
    path: str = Field("", description="请求路径")
    protocol: str = Field("HTTP", description="协议: HTTP/HTTPS/TCP/SQL")
    description: str = Field("", description="描述")
    module_id: Optional[str] = Field("root", description="所属模块")
    moduleId: Optional[str] = Field("", description="所属模块（别名）")
    project_id: Optional[str] = Field("", description="所属项目")
    projectId: Optional[str] = Field("", description="所属项目（别名）")
    tags: Optional[List[str]] = Field([], description="标签")
    request: Optional[Dict[str, Any]] = Field(None, description="请求元信息")

    model_config = {"extra": "allow"}


class ApiDefinitionUpdate(_LenientRequest):
    """更新接口定义。"""

    id: Optional[str] = Field("", description="定义 ID")
    name: Optional[str] = Field(None, description="接口名称")
    method: Optional[str] = Field(None, description="HTTP 方法")
    path: Optional[str] = Field(None, description="请求路径")
    protocol: Optional[str] = Field(None, description="协议")
    description: Optional[str] = Field(None, description="描述")
    status: Optional[str] = Field(None, description="状态")
    tags: Optional[List[str]] = Field(None, description="标签")

    model_config = {"extra": "allow"}


class ApiDefinitionVersionCreate(_LenientRequest):
    """为接口定义创建新版本。"""

    version: str = Field("", description="版本号")

    model_config = {"extra": "allow"}


class ApiDefinitionRollback(_LenientRequest):
    """回滚接口定义到指定版本。"""

    version_id: str = Field("", description="目标版本 ID")

    model_config = {"extra": "allow"}


# ── 接口用例 ─────────────────────────────────────────────
class ApiCaseCreate(_LenientRequest):
    """创建接口用例。"""

    id: Optional[str] = Field("", description="用例 ID")
    name: str = Field("", description="用例名称")
    definition_id: Optional[str] = Field("", description="关联接口定义 ID")
    definitionId: Optional[str] = Field("", description="关联接口定义 ID（别名）")
    method: Optional[str] = Field("GET", description="HTTP 方法")
    path: Optional[str] = Field("", description="请求路径")
    protocol: Optional[str] = Field("HTTP", description="协议")
    module_id: Optional[str] = Field("", description="所属模块")
    moduleId: Optional[str] = Field("", description="所属模块（别名）")
    project_id: Optional[str] = Field("", description="所属项目")
    projectId: Optional[str] = Field("", description="所属项目（别名）")
    description: Optional[str] = Field("", description="描述")
    request: Optional[Dict[str, Any]] = Field(None, description="请求元信息")
    tags: Optional[List[str]] = Field([], description="标签")

    model_config = {"extra": "allow"}


class ApiCaseUpdate(_LenientRequest):
    """更新接口用例。"""

    id: Optional[str] = Field("", description="用例 ID")
    name: Optional[str] = Field(None, description="用例名称")
    description: Optional[str] = Field(None, description="描述")
    status: Optional[str] = Field(None, description="状态")
    priority: Optional[str] = Field(None, description="优先级")
    request: Optional[Dict[str, Any]] = Field(None, description="请求元信息")
    tags: Optional[List[str]] = Field(None, description="标签")

    model_config = {"extra": "allow"}


# ── 场景编排 ─────────────────────────────────────────────
class ScenarioCreate(_LenientRequest):
    """创建接口场景。"""

    id: Optional[str] = Field("", description="场景 ID")
    name: str = Field("", description="场景名称")
    description: Optional[str] = Field("", description="描述")
    module_id: Optional[str] = Field("", description="所属模块")
    moduleId: Optional[str] = Field("", description="所属模块（别名）")
    project_id: Optional[str] = Field("", description="所属项目")
    projectId: Optional[str] = Field("", description="所属项目（别名）")
    steps: Optional[List[Any]] = Field([], description="场景步骤")
    tags: Optional[List[str]] = Field([], description="标签")

    model_config = {"extra": "allow"}


class ScenarioUpdate(_LenientRequest):
    """更新接口场景。"""

    id: Optional[str] = Field("", description="场景 ID")
    name: Optional[str] = Field(None, description="场景名称")
    description: Optional[str] = Field(None, description="描述")
    steps: Optional[List[Any]] = Field(None, description="场景步骤")
    status: Optional[str] = Field(None, description="状态")
    tags: Optional[List[str]] = Field(None, description="标签")

    model_config = {"extra": "allow"}


# ── Mock 服务 ────────────────────────────────────────────
class MockCreate(_LenientRequest):
    """创建 Mock 服务。"""

    id: Optional[str] = Field("", description="Mock ID")
    name: str = Field("", description="Mock 名称")
    method: str = Field("GET", description="HTTP 方法")
    path: str = Field("", description="请求路径")
    project_id: Optional[str] = Field("", description="所属项目")
    projectId: Optional[str] = Field("", description="所属项目（别名）")
    response_code: Optional[int] = Field(200, description="响应状态码")
    response_code_type: Optional[str] = Field("", description="响应码类型")
    response_headers: Optional[Dict[str, Any]] = Field(None, description="响应头")
    response_body: Optional[str] = Field("", description="响应体")
    response_body_type: Optional[str] = Field("JSON", description="响应体类型")
    delay_ms: Optional[int] = Field(0, description="延迟毫秒数")

    model_config = {"extra": "allow"}


class MockUpdate(_LenientRequest):
    """更新 Mock 服务。"""

    id: Optional[str] = Field("", description="Mock ID")
    name: Optional[str] = Field(None, description="Mock 名称")
    method: Optional[str] = Field(None, description="HTTP 方法")
    path: Optional[str] = Field(None, description="请求路径")
    status: Optional[str] = Field(None, description="状态")

    model_config = {"extra": "allow"}


# ── 环境 / 调试 / 导入 ───────────────────────────────────
class ApiEnvironmentCreate(_LenientRequest):
    """创建接口测试环境。"""

    name: str = Field("", description="环境名称")
    description: Optional[str] = Field("", description="描述")
    base_url: Optional[str] = Field("", description="基础地址")
    baseUrl: Optional[str] = Field("", description="基础地址（别名）")
    project_id: Optional[str] = Field("", description="所属项目")
    projectId: Optional[str] = Field("", description="所属项目（别名）")
    headers: Optional[Dict[str, Any]] = Field(None, description="请求头")
    variables: Optional[Dict[str, Any]] = Field(None, description="环境变量")
    config: Optional[Dict[str, Any]] = Field(None, description="扩展配置")

    model_config = {"extra": "allow"}


class ApiEnvironmentUpdate(_LenientRequest):
    """更新接口测试环境。"""

    id: Optional[str] = Field("", description="环境 ID")
    name: Optional[str] = Field(None, description="环境名称")
    description: Optional[str] = Field(None, description="描述")
    base_url: Optional[str] = Field(None, description="基础地址")
    headers: Optional[Dict[str, Any]] = Field(None, description="请求头")
    variables: Optional[Dict[str, Any]] = Field(None, description="环境变量")

    model_config = {"extra": "allow"}


# ── 模块管理 ─────────────────────────────────────────────
class ModuleAddBody(_LenientRequest):
    """新增模块。"""

    name: str = Field("", description="模块名称")
    parent_id: str = Field("root", description="父模块 ID")
    project_id: str = Field("", description="所属项目")

    model_config = {"extra": "allow"}


class ModuleUpdateBody(_LenientRequest):
    """更新模块名称。"""

    id: str = Field("", description="模块 ID")
    name: str = Field("", description="模块名称")

    model_config = {"extra": "allow"}


class ModuleDeleteBody(_LenientRequest):
    """删除模块。"""

    id: str = Field("", description="模块 ID")

    model_config = {"extra": "allow"}


class ModuleMoveBody(_LenientRequest):
    """移动模块。"""

    id: str = Field("", description="模块 ID")
    parent_id: str = Field("", description="目标父模块 ID")
    parentId: str = Field("", description="目标父模块 ID（别名）")

    model_config = {"extra": "allow"}


# ── 批量操作 ─────────────────────────────────────────────
class BatchIdsBody(_LenientRequest):
    """通用批量 ID 操作。"""

    ids: List[str] = Field([], description="ID 列表")

    model_config = {"extra": "allow"}


class BatchUpdateBody(_LenientRequest):
    """批量更新（如批量改模块/项目）。"""

    ids: List[str] = Field([], description="ID 列表")
    module_id: Optional[str] = Field("", description="目标模块 ID")
    moduleId: Optional[str] = Field("", description="目标模块 ID（别名）")
    project_id: Optional[str] = Field("", description="目标项目 ID")
    projectId: Optional[str] = Field("", description="目标项目 ID（别名）")

    model_config = {"extra": "allow"}


# ── 执行 ─────────────────────────────────────────────────
class RunBody(_LenientRequest):
    """执行接口用例/场景。"""

    project_id: Optional[str] = Field("", description="所属项目")
    projectId: Optional[str] = Field("", description="所属项目（别名）")
    environment_id: Optional[str] = Field("", description="执行环境 ID")
    environmentId: Optional[str] = Field("", description="执行环境 ID（别名）")
    report_id: Optional[str] = Field("", description="报告 ID")

    model_config = {"extra": "allow"}


# ── apitest 路由服务下沉新增请求体（#282）─────────────────
class ScenarioRunRequest(BaseModel):
    """执行接口场景（运行参数）。"""
    environment_id: str = Field("", description="覆盖环境 ID，可为空使用场景自带环境")


class ImportApiRequest(BaseModel):
    """导入接口定义（JSON 内容）。"""
    content: str = Field(..., description="接口文档内容（JSON/YAML 等）")
    format: str = Field("auto", description="导入格式：auto/postman/swagger/har 等")
    project_id: str = Field("", description="归属项目 ID")


class ApiDebugRequest(BaseModel):
    """接口调试请求。"""
    method: str = Field("GET", description="请求方法")
    url: str = Field("", description="请求 URL")
    headers: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    body: Any = Field("", description="请求体")
    body_type: str = Field("json", description="请求体类型：json/form 等")
    timeout: int = Field(30, ge=1, le=300, description="超时秒数")


# ═══════════════════════════════════════════════════════════
# Compat（MeterSphere 兼容层）请求体建档
# 字段归纳自 app/routers/apitest_compat_*.py 中 read_body 实际读取的
# 前端格式字段（camelCase），经 model_validate 在路由层收敛归一。
# 保持 read_body 的宽容语义：extra: allow + 默认值对齐旧 body.get。
# ═══════════════════════════════════════════════════════════

# ── 通用列表/分页 ─────────────────────────────────────────
class DefinitionPageBody(_LenientRequest):
    """接口定义分页列表请求体（definition/page，含回收站）。"""

    keyword: str = ""
    pageSize: Any = 10
    current: Any = 1
    projectId: str = ""
    protocols: Optional[list] = None
    moduleIds: Optional[list] = None
    deleted: bool = False

    @property
    def limit(self) -> int:
        return int(self.pageSize or 10)

    @property
    def offset(self) -> int:
        return (int(self.current or 1) - 1) * self.limit

    model_config = {"extra": "allow"}


class DocPageBody(_LenientRequest):
    """接口文档分页列表请求体（definition/page-doc）。"""

    keyword: str = ""
    current: Any = 1
    pageSize: Any = 10

    @property
    def offset(self) -> int:
        return (int(self.current or 1) - 1) * int(self.pageSize or 10)

    model_config = {"extra": "allow"}


class DefinitionModuleQueryBody(_LenientRequest):
    """接口定义模块树请求体（definition/module/tree 及 only/env 变体）。"""

    keyword: str = ""
    protocols: Optional[list] = None
    projectId: str = ""
    moduleIds: Optional[list] = None
    selectedModules: Optional[list] = None

    @property
    def effective_protocols(self) -> list:
        return self.protocols or []

    @property
    def effective_module_ids(self) -> list:
        return self.moduleIds or []

    @property
    def effective_selected_modules(self) -> list:
        return self.selectedModules or []

    model_config = {"extra": "allow"}


# ── 接口定义写操作 ─────────────────────────────────────────
class DefinitionCompatCreateBody(_LenientRequest):
    """创建接口定义（definition/add，前端 camelCase 字段）。"""

    name: str = "未命名接口"
    method: str = "GET"
    path: str = "/"
    protocol: str = "HTTP"
    description: str = ""
    requestBody: Any = ""
    requestHeaders: Any = None
    headers: Any = None
    query: Any = None
    requestParams: Any = None
    params: Any = None
    tags: Any = None

    model_config = {"extra": "allow"}

    def service_kwargs(self) -> dict:
        """映射为 apitest_service.create_definition 期望的字段。"""
        return {
            "name": self.name or "未命名接口",
            "method": self.method or "GET",
            "path": self.path or "/",
            "protocol": self.protocol or "HTTP",
            "description": self.description or "",
            "body": self.requestBody or "",
            "headers": self.requestHeaders if self.requestHeaders is not None else (self.headers or {}),
            "query": self.query or {},
            "params": self.requestParams if self.requestParams is not None else (self.params or {}),
            "tags": self.tags or [],
        }


class DefinitionCompatUpdateBody(_LenientRequest):
    """更新接口定义（definition/update）。"""

    id: str = ""
    name: Any = None
    method: Any = None
    path: Any = None
    protocol: Any = None
    description: Any = None

    model_config = {"extra": "allow"}

    def service_kwargs(self) -> dict:
        """仅回传明确更新的字段（对齐旧循环 k/v 白名单语义）。"""
        updates = {}
        for k in ("name", "method", "path", "protocol", "description"):
            v = getattr(self, k)
            if k == "name" and v is not None:
                updates[k] = v
            elif k == "method" and v is not None:
                updates[k] = v
            elif k == "path" and v is not None:
                updates[k] = v
            elif k == "protocol" and v is not None:
                updates[k] = v
            elif k == "description" and v is not None:
                updates[k] = v
        return updates


# ── 模块操作 ───────────────────────────────────────────────
class CompatModuleAddBody(_LenientRequest):
    """新增接口定义模块（definition/module/add）。"""

    name: str = "新模块"
    parentId: str = "root"
    projectId: str = ""

    model_config = {"extra": "allow"}


class CompatModuleUpdateBody(_LenientRequest):
    """更新接口定义模块（definition/module/update）。"""

    id: str = ""
    name: str = ""

    model_config = {"extra": "allow"}


# ── 单 id / 批量选择 ───────────────────────────────────────


# ── 接口用例（compat） ────────────────────────────────────
class CaseCompatPageBody(_LenientRequest):
    """接口用例分页列表请求体（case/page）。"""

    keyword: str = ""
    pageSize: Any = 10
    current: Any = 1
    projectId: str = ""
    apiDefinitionId: Any = None
    definitionId: Any = None

    @property
    def effective_definition_id(self):
        v = self.apiDefinitionId if self.apiDefinitionId is not None else self.definitionId
        return v or None

    model_config = {"extra": "allow"}


class CaseCompatCreateBody(_LenientRequest):
    """创建接口用例（case/add，前端字段）。"""

    name: str = "未命名用例"
    apiDefinitionId: Any = None
    definitionId: Any = None
    description: str = ""
    assertions: Any = None
    asserts: Any = None
    preScripts: Any = None
    postScripts: Any = None

    @property
    def effective_api_definition_id(self):
        return self.apiDefinitionId if self.apiDefinitionId is not None else self.definitionId or ""

    model_config = {"extra": "allow"}

    def service_kwargs(self) -> dict:
        return {
            "name": self.name or "未命名用例",
            "api_definition_id": self.effective_api_definition_id,
            "description": self.description or "",
            "asserts": self.assertions if self.assertions is not None else (self.asserts or []),
            "pre_scripts": self.preScripts or [],
            "post_scripts": self.postScripts or [],
        }


class CaseCompatUpdateBody(_LenientRequest):
    """更新接口用例（case/update）。"""

    id: str = ""
    name: Any = None
    description: Any = None
    assertions: Any = None

    def service_kwargs(self) -> dict:
        updates = {}
        if self.name is not None:
            updates["name"] = self.name
        if self.description is not None:
            updates["description"] = self.description
        if self.assertions is not None:
            updates["asserts"] = self.assertions
        return updates

    model_config = {"extra": "allow"}


# ── 接口场景（compat） ────────────────────────────────────
class ScenarioCompatPageBody(_LenientRequest):
    """接口场景分页列表请求体（scenario/page）。"""

    keyword: str = ""
    pageSize: Any = 10
    current: Any = 1
    projectId: str = ""

    model_config = {"extra": "allow"}


class ScenarioCompatCreateBody(_LenientRequest):
    """创建接口场景（scenario/add）。"""

    name: str = "未命名场景"
    description: str = ""
    steps: Any = None

    model_config = {"extra": "allow"}

    def service_kwargs(self) -> dict:
        return {
            "name": self.name or "未命名场景",
            "description": self.description or "",
            "steps": self.steps or [],
        }


class ScenarioCompatUpdateBody(_LenientRequest):
    """更新接口场景（scenario/update）。"""

    id: str = ""
    name: Any = None
    description: Any = None
    steps: Any = None

    def service_kwargs(self) -> dict:
        updates = {}
        for k in ("name", "description", "steps"):
            v = getattr(self, k)
            if v is not None:
                updates[k] = v
        return updates

    model_config = {"extra": "allow"}


# ═══════════════════════════════════════════════════════════
# 接口场景 / 接口用例 / 接口定义（compat）通用请求体收敛
# 归纳自 apitest_compat_*.py 中 read_body 手写 .get() 解析的路由，
# 统一以模型收敛并保持 read_body 的宽容语义（extra: allow + 默认值对齐）。
# ═══════════════════════════════════════════════════════════

class CompatProjectQueryBody(_LenientRequest):
    """按 projectId 查询（*/module/tree、*/module/count、trash/count 等）。"""

    projectId: str = ""

    model_config = {"extra": "allow"}


class CompatModuleDeleteBody(_LenientRequest):
    """删除模块（*/module/delete）。"""

    id: str = ""

    model_config = {"extra": "allow"}


class CompatModuleMoveBody(_LenientRequest):
    """移动模块（*/module/move，仅消费请求体无需字段）。"""

    model_config = {"extra": "allow"}


class CompatIdBody(_LenientRequest):
    """通用单/多目标 id 请求体（兼容前端 id/scenarioId/caseId/case_id/ids 等别名）。"""

    id: Any = ""
    ids: Any = None
    scenarioId: Any = None
    scenario_id: Any = None
    caseId: Any = None
    case_id: Any = None
    definitionId: Any = None
    environmentId: Any = None
    environment_id: Any = None
    sourceId: Any = None
    stepId: Any = None
    step_id: Any = None

    @property
    def effective_id(self) -> str:
        """返回首个非空单 id（id→scenarioId→scenario_id→caseId→case_id→definitionId→sourceId）。"""
        for k in ("id", "scenarioId", "scenario_id", "caseId", "case_id", "definitionId", "sourceId"):
            v = getattr(self, k)
            if v:
                return v
        return self.id if self.id is not None else ""

    @property
    def id_or_ids(self) -> Any:
        """兼容 `body.get("id", body.get("ids", ""))`：id 非空用 id，否则用 ids。"""
        if self.id is not None and self.id != "":
            return self.id
        v = self.ids if self.ids is not None else self.caseId
        if v is None:
            v = self.case_id
        if v is None:
            v = self.scenarioId
        return v if v is not None else ""

    model_config = {"extra": "allow"}


class CompatBatchIdsBody(_LenientRequest):
    """批量选择请求体（ids / selectIds / selectAll）。

    兼容 `body.get("ids", body.get("selectIds", []))` 与 selectAll 全选语义。
    """

    ids: Any = None
    selectIds: Any = None
    caseIds: Any = None
    selectAll: Any = None

    @property
    def effective_ids(self) -> list:
        for k in ("ids", "selectIds", "caseIds"):
            v = getattr(self, k)
            if v:
                return v if isinstance(v, list) else [v]
        return []

    @property
    def select_all(self) -> bool:
        return bool(getattr(self, "selectAll", None))

    model_config = {"extra": "allow"}


class CompatExecutionPageBody(_LenientRequest):
    """执行历史 / 操作历史分页请求体（*/execute/page、*/operation-history/page）。"""

    current: Any = 1
    page: Any = None
    pageSize: Any = 10
    page_size: Any = None
    scenarioId: Any = None
    scenario_id: Any = None
    sourceId: Any = None
    id: Any = None
    caseId: Any = None
    case_id: Any = None
    definitionId: Any = None
    keyword: str = ""

    @property
    def effective_current(self) -> int:
        return int(self.current if self.current is not None else (self.page or 1)) or 1

    @property
    def effective_page_size(self) -> int:
        v = self.pageSize if self.pageSize is not None else self.page_size
        return int(v or 10) or 10

    @property
    def effective_target_id(self) -> str:
        for k in ("id", "scenarioId", "scenario_id", "caseId", "case_id", "sourceId", "definitionId"):
            v = getattr(self, k)
            if v:
                return v
        return ""

    @property
    def effective_keyword(self) -> str:
        return self.keyword or ""

    model_config = {"extra": "allow"}


class CompatBatchEditBody(_LenientRequest):
    """批量编辑请求体（ids/selectIds + 其余待更新字段）。

    旧逻辑 `fields = {k: v for k, v in body.items() if k not in ("ids","selectIds","selectAll")}`
    将所有非选择字段原样透传，故此处以 extra: allow 收集全量字段并按需剔除。
    """

    ids: Any = None
    selectIds: Any = None
    selectAll: Any = None

    @property
    def effective_ids(self) -> list:
        for k in ("ids", "selectIds"):
            v = getattr(self, k)
            if v:
                return v if isinstance(v, list) else [v]
        return []

    def update_fields(self) -> dict:
        """剔除选择字段后，其余 extra 字段视为待更新字段原样回传。"""
        data = dict(self.model_dump(exclude_none=False))
        for k in ("ids", "selectIds", "selectAll"):
            data.pop(k, None)
        return data

    model_config = {"extra": "allow"}


class CompatStatisticsBody(_LenientRequest):
    """执行统计请求体（*/statistics，ids 数组或整个请求体为 id 数组）。"""

    ids: Any = None

    @property
    def effective_ids(self) -> list:
        return self.ids if isinstance(self.ids, list) else []

    model_config = {"extra": "allow"}


class CompatFollowBody(_LenientRequest):
    """关注/取关请求体（*/follow）。"""

    id: Any = ""
    scenarioId: Any = None
    scenario_id: Any = None
    caseId: Any = None

    @property
    def effective_id(self) -> str:
        for k in ("id", "scenarioId", "scenario_id", "caseId"):
            v = getattr(self, k)
            if v:
                return v
        return self.id or ""

    model_config = {"extra": "allow"}


class CompatAssociationPageBody(_LenientRequest):
    """关联用例/引用分页请求体（scenario/association/page、scenario/get-reference）。"""

    scenarioId: Any = None
    scenario_id: Any = None
    current: Any = 1
    pageSize: Any = 10

    @property
    def effective_scenario_id(self) -> str:
        return (self.scenarioId if self.scenarioId is not None else self.scenario_id) or ""

    model_config = {"extra": "allow"}


class CompatStepUnSaveBody(_LenientRequest):
    """获取未保存步骤请求体（scenario/step/get/un-save）。"""

    stepId: Any = None
    step_id: Any = None

    @property
    def effective_step_id(self) -> str:
        return (self.stepId if self.stepId is not None else self.step_id) or ""

    model_config = {"extra": "allow"}


# ── 接口用例（compat）单值更新：priority / status ─────────
class CaseCompatPriorityBody(_LenientRequest):
    """更新用例优先级（case/update-priority）。"""

    id: Any = ""
    caseId: Any = None
    case_id: Any = None
    priority: Any = "P2"

    @property
    def effective_case_id(self) -> str:
        for k in ("id", "caseId", "case_id"):
            v = getattr(self, k)
            if v:
                return v
        return self.id or ""

    model_config = {"extra": "allow"}


class CaseCompatStatusBody(_LenientRequest):
    """更新用例状态（case/update-status）。"""

    id: Any = ""
    caseId: Any = None
    case_id: Any = None
    status: Any = "draft"

    @property
    def effective_case_id(self) -> str:
        for k in ("id", "caseId", "case_id"):
            v = getattr(self, k)
            if v:
                return v
        return self.id or ""

    model_config = {"extra": "allow"}


class CaseCompatTrashPageBody(_LenientRequest):
    """用例回收站分页（case/trash/page）。"""

    pageSize: Any = 100
    current: Any = 1

    @property
    def effective_page_size(self) -> int:
        return int(self.pageSize or 100) or 100

    @property
    def effective_current(self) -> int:
        return int(self.current or 1) or 1

    model_config = {"extra": "allow"}


class CaseCompatAiSaveConfigBody(_LenientRequest):
    """保存用例 AI 配置（case/ai/save/config）。

    兼容 `body.get("config") if "config" in body else body`：请求体既可能是
    {config: {...}, projectId}，也可能本身就是配置 dict。
    """

    config: Any = None
    projectId: Any = None

    @property
    def config_value(self) -> dict:
        if "config" in self.__dict__ and self.config is not None:
            raw = self.config
        else:
            raw = {k: v for k, v in self.model_dump().items() if k not in ("config", "projectId")}
            raw.update({k: v for k, v in (getattr(self, "__pydantic_extra__", {}) or {}).items()})
        return raw if isinstance(raw, dict) else {}

    @property
    def effective_project_id(self) -> str:
        return str(self.projectId or "")

    model_config = {"extra": "allow"}


class CaseCompatBatchEditBody(_LenientRequest):
    """批量编辑接口用例（case/batch/edit）。

    旧逻辑将 body 中除 (selectIds, selectAll, excludeIds, ids, condition) 外的
    全部字段作为更新字段透传 update_api_case，故此处以 extra: allow 收集并按白名单剔除。
    """

    selectIds: Any = None
    selectAll: Any = None
    excludeIds: Any = None
    ids: Any = None
    condition: Any = None

    @property
    def effective_case_ids(self) -> list:
        v = self.selectIds if self.selectIds is not None else self.ids
        if v is None:
            v = []
        return v if isinstance(v, list) else ([v] if v else [])

    @property
    def select_all(self) -> bool:
        return bool(self.selectAll)

    def update_fields(self) -> dict:
        data = dict(self.model_dump(exclude_none=False))
        for k in ("selectIds", "selectAll", "excludeIds", "ids", "condition"):
            data.pop(k, None)
        return data

    model_config = {"extra": "allow"}
# ── Mock compat（apitest_compat_mock.py）─────────────────
class MockCompatAddBody(_LenientRequest):
    """创建 Mock（mock/add，TestPilot 前端混合 camel/snake 命名）。"""

    name: str = Field("未命名Mock", description="Mock 名称")
    apiDefinitionId: str = Field("", description="所属接口定义 ID")
    method: str = Field("GET", description="HTTP 方法")
    path: str = Field("", description="请求路径")
    statusCode: Any = Field(200, description="响应状态码（前端驼峰）")
    response_body: str = Field("", description="响应体（后端蛇形）")
    response_headers: Any = Field(None, description="响应头")
    description: str = Field("", description="描述")
    projectId: str = Field("", description="所属项目 ID")

    model_config = {"extra": "allow"}

    def service_kwargs(self) -> dict:
        """映射为 apitest_service.create_mock 期望字段。"""
        return {
            "name": self.name or "未命名Mock",
            "api_definition_id": self.apiDefinitionId or "",
            "method": self.method or "GET",
            "path": self.path or "",
            "status_code": int(self.statusCode or 200),
            "response_body": self.response_body or "",
            "response_headers": self.response_headers,
            "description": self.description or "",
            "project_id": self.projectId or "",
        }


class MockCompatPageBody(_LenientRequest):
    """Mock 分页列表（mock/page）。"""

    keyword: str = Field("", description="搜索关键字")
    pageSize: Any = Field(10, description="每页条数")
    current: Any = Field(1, description="页码")
    projectId: str = Field("", description="所属项目 ID")

    model_config = {"extra": "allow"}


class MockCompatIdBody(_LenientRequest):
    """按 id 操作 Mock（delete/detail/copy/enable）。"""

    id: str = Field("", description="Mock ID")
    projectId: str = Field("", description="所属项目 ID（仅展示用）")
    active: Any = Field(1, description="启用标记（enable 用）")

    model_config = {"extra": "allow"}


class MockCompatBatchBody(_LenientRequest):
    """批量选择 Mock（batch/edit、batch/delete）。"""

    selectIds: Any = Field(None, description="已选用例 ID 列表")
    ids: Any = Field(None, description="ID 列表（别名）")
    selectAll: Any = Field(False, description="是否全选")
    excludeIds: Any = Field(None, description="排除 ID（selectAll 时）")

    model_config = {"extra": "allow"}

    @property
    def effective_ids(self) -> list:
        sel = self.selectIds if self.selectIds is not None else self.ids
        if sel is None:
            return []
        if isinstance(sel, str):
            sel = [sel]
        return list(sel)


class MockCompatHistoryPageBody(_LenientRequest):
    """Mock 操作历史分页（mock/operation-history/page）。"""

    current: Any = Field(None, description="页码")
    page: Any = Field(None, description="页码（别名）")
    pageSize: Any = Field(None, description="每页条数")
    page_size: Any = Field(None, description="每页条数（别名）")
    sourceId: str = Field("", description="资源 ID（操作对象）")
    id: str = Field("", description="Mock ID（别名）")
    mockId: str = Field("", description="Mock ID（别名）")

    model_config = {"extra": "allow"}

    @property
    def effective_page(self) -> int:
        return int(self.current if self.current is not None else (self.page or 1))

    @property
    def effective_page_size(self) -> int:
        return int(self.pageSize if self.pageSize is not None else (self.page_size or 10))

    @property
    def effective_mock_id(self) -> str:
        return self.sourceId or self.id or self.mockId or ""
