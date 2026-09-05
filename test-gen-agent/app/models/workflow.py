# app/models/workflow.py
"""工作流（状态流）域请求体模型。

字段自 `app/routers/project_compat_extra.py` / `app/routers/system_compat.py` /
`app/routers/system_compat_extra.py` 中状态流（status/flow/setting/*）各
handler 的 `read_body` 实际使用字段归纳。组织级与项目级状态流操作高度同构，
仅在 scope_type 与个别默认值上有别，故统一建档一套通用请求体模型。

兼容前端 TestPilot 驼峰字段与后端 snake_case 别名，散落的 `body.get("A",
body.get("B", ...))` 别名抽取统一收敛到各模型的 `effective_*` 归一属性。
所有模型默认 `extra: allow`，避免遗漏新增字段导致 400。
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field


def _first(*values: Any) -> Any:
    """取第一个非空值（None 与空串视为缺省，对齐旧 .get(key, default) 语义）。"""
    for v in values:
        if v is not None and v != "":
            return v
    return None


class WorkflowStatusAddBody(BaseModel):
    """新增工作流状态请求体（addWorkStatusModal）。

    兼容字段：scopeId/scope_id、scene、name、remark、allTransferTo/all_transfer_to。
    """

    scopeId: Optional[str] = Field(None, description="范围 ID（驼峰别名）")
    scope_id: Optional[str] = Field(None, description="范围 ID（蛇形别名）")
    scene: Optional[str] = Field("FUNCTIONAL", description="场景: FUNCTIONAL/API/UI/...")
    name: Optional[str] = Field("未命名状态", description="状态名称")
    remark: Optional[str] = Field("", description="备注")
    allTransferTo: Optional[Any] = Field(None, description="是否允许全部流转（项目级）")
    all_transfer_to: Optional[Any] = Field(None, description="是否允许全部流转（蛇形别名）")

    @property
    def effective_scope_id(self) -> str:
        return _first(self.scopeId, self.scope_id) or ""

    @property
    def effective_scene(self) -> str:
        return self.scene or "FUNCTIONAL"

    @property
    def effective_name(self) -> str:
        return self.name if self.name is not None else "未命名状态"

    @property
    def effective_remark(self) -> str:
        return self.remark or ""

    @property
    def effective_all_transfer_to(self) -> bool:
        return bool(_first(self.allTransferTo, self.all_transfer_to) or False)

    model_config = {"extra": "allow"}


class WorkflowStatusUpdateBody(BaseModel):
    """更新工作流状态请求体。

    兼容字段：id/statusId（状态 ID，id 优先）、name、remark、
    statusDefinitions/status_definitions。
    """

    id: Optional[Any] = Field(None, description="状态 ID（优先）")
    statusId: Optional[Any] = Field(None, description="状态 ID（别名）")
    name: Optional[str] = Field(None, description="状态名称")
    remark: Optional[str] = Field(None, description="备注")
    statusDefinitions: Optional[Any] = Field(None, description="初始/结束态标记列表")
    status_definitions: Optional[Any] = Field(None, description="标记列表（蛇形别名）")

    @property
    def effective_status_id(self) -> str:
        return _first(self.id, self.statusId) or ""

    @property
    def effective_name(self) -> str:
        return self.name or ""

    @property
    def effective_remark(self) -> str:
        return self.remark or ""

    @property
    def effective_status_definitions(self) -> Any:
        return _first(self.statusDefinitions, self.status_definitions)

    model_config = {"extra": "allow"}


class WorkflowStatusDeleteBody(BaseModel):
    """删除工作流状态请求体。兼容字段：id/statusId（id 优先）。"""

    id: Optional[Any] = Field(None, description="状态 ID（优先）")
    statusId: Optional[Any] = Field(None, description="状态 ID（别名）")

    @property
    def effective_status_id(self) -> str:
        return _first(self.id, self.statusId) or ""

    model_config = {"extra": "allow"}


class WorkflowStatusSortBody(BaseModel):
    """工作流状态排序请求体。

    兼容字段：data/ids/statusIds（列表形态）；read_body 会把前端裸数组归一为
    {"ids": [...]}，故裸数组形态也能命中 ids。
    """

    data: Optional[Any] = Field(None, description="排序后的状态 ID 数组")
    ids: Optional[Any] = Field(None, description="状态 ID 数组")
    statusIds: Optional[Any] = Field(None, description="状态 ID 数组（前端别名）")

    @property
    def effective_status_ids(self) -> List[str]:
        for key in ("data", "ids", "statusIds"):
            v = getattr(self, key)
            if isinstance(v, list) and v:
                return [str(d) for d in v]
        return []

    model_config = {"extra": "allow"}


class WorkflowFlowUpdateBody(BaseModel):
    """更新状态流转关系请求体。

    兼容字段：
      - source：sourceId/sourceStatusId/id（sourceId 优先）
      - targets：targetIds/statusFlowTargets/targetStatusIds（targetIds 优先，
        支持单值形态自动包裹为列表）
    """

    sourceId: Optional[Any] = Field(None, description="源状态 ID（优先）")
    sourceStatusId: Optional[Any] = Field(None, description="源状态 ID（别名）")
    id: Optional[Any] = Field(None, description="源状态 ID（别名）")
    targetIds: Optional[Any] = Field(None, description="目标状态 ID 列表（优先）")
    statusFlowTargets: Optional[Any] = Field(None, description="目标状态 ID 列表（别名）")
    targetStatusIds: Optional[Any] = Field(None, description="目标状态 ID 列表（别名）")

    @property
    def effective_source_id(self) -> str:
        return _first(self.sourceId, self.sourceStatusId, self.id) or ""

    @property
    def effective_target_ids(self) -> List[str]:
        targets = _first(self.targetIds, self.statusFlowTargets, self.targetStatusIds)
        if targets is None:
            return []
        if not isinstance(targets, list):
            targets = [targets] if targets else []
        return [str(t) for t in targets if t]

    model_config = {"extra": "allow"}


class WorkflowDefinitionUpdateBody(BaseModel):
    """设置状态为初始态/结束态请求体（setProjectWorkState）。

    兼容字段：statusId/id（statusId 优先）、definitionId/definition_id、
    enable/definition（enable 优先，缺省 True）。
    definitionId: "START" 设初始态, "END" 设结束态。
    """

    statusId: Optional[Any] = Field(None, description="状态 ID（优先）")
    id: Optional[Any] = Field(None, description="状态 ID（别名）")
    definitionId: Optional[Any] = Field(None, description="定义类型: START/END（优先）")
    definition_id: Optional[Any] = Field(None, description="定义类型（蛇形别名）")
    enable: Optional[Any] = Field(None, description="启用标记（缺省 True）")
    definition: Optional[Any] = Field(None, description="启用标记（前端别名）")

    @property
    def effective_status_id(self) -> str:
        return _first(self.statusId, self.id) or ""

    @property
    def effective_definition_id(self) -> str:
        return _first(self.definitionId, self.definition_id) or ""

    @property
    def effective_enable(self) -> bool:
        return bool(_first(self.enable, self.definition) if _first(self.enable, self.definition) is not None else True)

    model_config = {"extra": "allow"}


__all__ = [
    "WorkflowStatusAddBody",
    "WorkflowStatusUpdateBody",
    "WorkflowStatusDeleteBody",
    "WorkflowStatusSortBody",
    "WorkflowFlowUpdateBody",
    "WorkflowDefinitionUpdateBody",
]
