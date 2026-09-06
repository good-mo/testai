"""调试应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class GetDebugItemCommand:
    debug_id: str = ""

@dataclass
class SaveDebugItemCommand:
    debug_id: str = ""
    name: str = "未命名调试"
    protocol: str = "HTTP"
    method: str = "GET"
    path: str = "/"
    url: str = "/"
    project_id: str = ""
    module_id: str = "root"
    request_data: Dict[str, Any] = field(default_factory=dict)
    response_data: Dict[str, Any] = field(default_factory=dict)
    create_user: str = "admin"
    update_user: str = "admin"
    num: int = 0

@dataclass
class DeleteDebugItemCommand:
    debug_id: str = ""

__all__ = ["GetDebugItemCommand", "SaveDebugItemCommand", "DeleteDebugItemCommand"]


# ==============================================================================
# 从 models/debug.py 迁移
# ==============================================================================

# app/models/debug.py
"""接口调试（debug）域 Pydantic 请求体模型。

字段归纳自 `app/routers/debug_compat.py` 中各 POST 端点经 `read_body()`
实际读取的请求体。前端 TestPilot 风格驼峰字段与后端别名并存；所有模型
默认 `extra: allow` 并保留 read_body 的空体/裸标量归一化语义，避免遗漏
新增字段导致 400。

调试对象结构说明：
- add / update 的请求体既可能把请求子字段（authConfig/body/headers/query/
  rest/otherConfig/polymorphicName/uploadFileIds/linkFileIds）放在顶层，
  也可能整体嵌套在 `request` 中，本域模型两种形态均兼容（见
  DebugSaveBody.effective_request()）。
- debug / debug/debug 发送的是 ExecuteRequestParams（回显/执行入参），
  属整包透传结构，见 DebugEchoBody / DebugExecuteBody。
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, model_validator


class _LenientRequest(BaseModel):
    """历史兼容：容忍前端经 axios 拦截器发送的裸标量/数组/空请求体。

    与旧 `read_body()` 的归一化语义一致：裸字符串 `"x"` → `{"id": "x"}`、
    数组 → `{"ids": [...]}`、空体 → `{}`，保证类型化模型不打断既有前端契约。
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


def _get(d: Dict[str, Any], *keys: str, default: Any = "") -> Any:
    """按优先级取多个别名键中的首个存在值。"""
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


class DebugIdBody(_LenientRequest):
    """按 ID 读取 / 删除调试项（get / delete 共用）。

    前端既有 `{"id": "..."}` 形态，历史调用亦可能发 `debugId` 别名。
    """

    id: str = Field("", description="调试 ID")
    debugId: str = Field("", description="调试 ID（别名）")
    debug_id: str = Field("", description="调试 ID（蛇形别名）")

    @property
    def effective_id(self) -> str:
        return _get(self.model_dump(exclude_unset=True), "id", "debugId", "debug_id", default="")

    model_config = {"extra": "allow"}


class DebugEditPosBody(_LenientRequest):
    """拖拽调试节点（edit/pos）。

    前端 dragDebug 发送 { projectId, moveMode, moveId, targetId, moduleId }。
    """

    moveId: str = Field("", description="被拖拽调试项 ID")
    move_id: str = Field("", description="被拖拽调试项 ID（蛇形别名）")
    moduleId: str = Field("", description="目标模块 ID")
    module_id: str = Field("", description="目标模块 ID（蛇形别名）")

    @property
    def effective_move_id(self) -> str:
        return _get(self.model_dump(exclude_unset=True), "moveId", "move_id", default="")

    @property
    def effective_module_id(self) -> str:
        return _get(self.model_dump(exclude_unset=True), "moduleId", "module_id", default="")

    model_config = {"extra": "allow"}


class DebugImportCurlBody(_LenientRequest):
    """导入 Curl 命令（import-curl）。前端 importByCurl 只发送 { curl }。"""

    curl: str = Field("", description="Curl 命令")
    data: str = Field("", description="Curl 命令（data 别名）")

    @property
    def effective_curl(self) -> str:
        return _get(self.model_dump(exclude_unset=True), "curl", "data", default="")

    model_config = {"extra": "allow"}


class DebugEchoBody(_LenientRequest):
    """本地执行回显（POST /api/debug）。

    本端点回传原始 ExecuteRequestParams 供本地执行服务消费，属整包透传，
    无固定字段约束。保留原始请求体供路由原样回传。
    """

    model_config = {"extra": "allow"}


class DebugExecuteBody(_LenientRequest):
    """执行调试请求（debug/debug）。发送 ExecuteRequestParams。"""

    id: Optional[str] = Field(None, description="调试 ID")
    name: Optional[str] = Field(None, description="名称")
    moduleId: Optional[str] = Field(None, description="模块 ID")
    projectId: Optional[str] = Field(None, description="项目 ID")
    environmentId: Optional[str] = Field(None, description="环境 ID")
    protocol: Optional[str] = Field(None, description="协议")
    method: Optional[str] = Field(None, description="HTTP 方法")
    path: Optional[str] = Field(None, description="请求路径")
    url: Optional[str] = Field(None, description="请求地址")
    frontendDebug: Optional[bool] = Field(None, description="是否本地执行模式")
    request: Optional[Dict[str, Any]] = Field(None, description="嵌套请求对象")

    model_config = {"extra": "allow"}


class DebugSaveBody(_LenientRequest):
    """保存调试项（add / update）。

    同时兼容“请求子字段在顶层”与“整体嵌套在 request”两种前端形态。
    """

    id: str = Field("", description="调试 ID（update 时必传）")
    name: str = Field("未命名调试", description="名称")
    protocol: str = Field("HTTP", description="协议")
    method: str = Field("GET", description="HTTP 方法")
    path: str = Field("", description="请求路径")
    url: str = Field("", description="请求地址")
    projectId: str = Field("", description="项目 ID")
    project_id: str = Field("", description="项目 ID（蛇形别名）")
    moduleId: str = Field("root", description="模块 ID")
    module_id: str = Field("", description="模块 ID（蛇形别名）")
    request: Optional[Dict[str, Any]] = Field(None, description="嵌套请求对象")
    response: Any = Field({}, description="响应数据")
    authConfig: Any = Field(None, description="鉴权配置")
    body: Any = Field(None, description="请求体")
    headers: Any = Field(None, description="请求头")
    query: Any = Field(None, description="查询参数")
    rest: Any = Field(None, description="REST 参数")
    otherConfig: Any = Field(None, description="其他配置")
    polymorphicName: str = Field("MsCommonElement", description="协议多态名")
    uploadFileIds: Optional[list] = Field(None, description="上传文件 ID")
    linkFileIds: Optional[list] = Field(None, description="关联文件 ID")

    def effective_request(self) -> Dict[str, Any]:
        """取得有效的请求子对象。

        若请求子字段在顶层，则从顶层拼装为 request；否则返回嵌套的 request。
        """
        data = self.model_dump(exclude_unset=True)
        request_data = self.request or {}
        if request_data and isinstance(request_data, dict):
            return request_data
        return {
            "authConfig": _get(data, "authConfig", default={}),
            "body": _get(data, "body", default={}),
            "headers": _get(data, "headers", default=[]),
            "query": _get(data, "query", default=[]),
            "rest": _get(data, "rest", default=[]),
            "otherConfig": _get(data, "otherConfig", default={}),
            "polymorphicName": _get(data, "polymorphicName", default="MsCommonElement"),
            "uploadFileIds": _get(data, "uploadFileIds", default=[]),
            "linkFileIds": _get(data, "linkFileIds", default=[]),
        }

    model_config = {"extra": "allow"}


class DebugModuleAddBody(_LenientRequest):
    """添加调试模块（module/add）。"""

    name: str = Field("新模块", description="模块名")
    parentId: str = Field("root", description="父模块 ID")
    parent_id: str = Field("", description="父模块 ID（蛇形别名）")
    projectId: str = Field("", description="项目 ID")
    project_id: str = Field("", description="项目 ID（蛇形别名）")

    @property
    def effective_name(self) -> str:
        return _get(self.model_dump(exclude_unset=True), "name", default="新模块")

    @property
    def effective_parent_id(self) -> str:
        return _get(self.model_dump(exclude_unset=True), "parentId", "parent_id", default="root")

    @property
    def effective_project_id(self) -> str:
        return _get(self.model_dump(exclude_unset=True), "projectId", "project_id", default="")

    model_config = {"extra": "allow"}


class DebugModuleUpdateBody(_LenientRequest):
    """更新调试模块（module/update）。"""

    id: str = Field("", description="模块 ID")
    moduleId: str = Field("", description="模块 ID（别名）")
    name: str = Field("", description="模块名")
    parentId: str = Field("root", description="父模块 ID")
    parent_id: str = Field("", description="父模块 ID（蛇形别名）")

    @property
    def effective_id(self) -> str:
        return _get(self.model_dump(exclude_unset=True), "id", "moduleId", default="")

    @property
    def effective_parent_id(self) -> str:
        return _get(self.model_dump(exclude_unset=True), "parentId", "parent_id", default="root")

    model_config = {"extra": "allow"}


class DebugModuleMoveBody(_LenientRequest):
    """移动调试模块（module/move）。前端 moveDebugModule 发送该结构。"""

    dragNodeId: str = Field("", description="被拖拽模块 ID")
    drag_node_id: str = Field("", description="被拖拽模块 ID（蛇形别名）")
    dropNodeId: str = Field("", description="目标模块 ID")
    drop_node_id: str = Field("", description="目标模块 ID（蛇形别名）")
    dropPosition: int = Field(0, description="落点位置 0/1/2")

    @property
    def effective_drag_id(self) -> str:
        return _get(self.model_dump(exclude_unset=True), "dragNodeId", "drag_node_id", default="")

    @property
    def effective_drop_id(self) -> str:
        return _get(self.model_dump(exclude_unset=True), "dropNodeId", "drop_node_id", default="")

    model_config = {"extra": "allow"}


# ==============================================================================
# 从 models/gap_fixes.py 迁移
# ==============================================================================

# app/models/gap_fixes.py
"""补齐差异兼容接口 Pydantic 模型。

对应 app/routers/gap_fixes.py 中手写 read_body 解析的请求体端点：
- /api/execute/resourcescript            资源脚本执行
- /task/center/api/{scope}/real-time/page 任务中心实时分页（project/org/system 三级同构）
"""

from typing import Optional

from pydantic import BaseModel, Field


class ResourceScriptExecBody(BaseModel):
    """执行资源脚本请求体。

    scriptId 为前端别名，resourceId 优先；缺省为空串。
    """

    resource_id: Optional[str] = Field(None, alias="resourceId", description="资源 ID")
    script_id: Optional[str] = Field(None, alias="scriptId", description="脚本 ID")

    model_config = {"extra": "allow", "populate_by_name": True}

    def effective_script_id(self) -> str:
        """resourceId 优先、scriptId 兜底。"""
        return self.resource_id or self.script_id or ""


class TaskCenterRealTimePageBody(BaseModel):
    """任务中心实时任务分页请求体（project/org/system 共用）。"""

    current: int = Field(1, ge=1, description="当前页")
    page_size: int = Field(10, alias="pageSize", ge=1, description="每页条数")

    model_config = {"extra": "allow", "populate_by_name": True}


__all__ = ["ResourceScriptExecBody", "TaskCenterRealTimePageBody"]
