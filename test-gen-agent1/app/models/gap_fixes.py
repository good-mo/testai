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
