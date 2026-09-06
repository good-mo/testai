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
