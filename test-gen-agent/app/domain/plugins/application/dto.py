"""plugins 域 DTO (Data Transfer Objects).

从 models/plugins.py 迁移而来。
"""
# app/models/plugins.py
"""插件管理 Pydantic 模型。

对应 app/routers/plugins.py（插件管理兼容路由）。
该域为占位兼容实现（stub），无落地 store/repo，前端仍会向
/plugin/add、/plugin/update、/plugin/delete 提交请求体。此处按前端
实际发送载荷建档请求体模型，供路由以类型化 body 收口、不再手写
read_body 逐 key 解析。
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class PluginUpsertBody(BaseModel):
    """新增 / 更新插件请求体。

    新增走前端 multipart 上传（文件内容不经 JSON 请求体），更新走
    JSON，载荷字段以更新分支为准：id / name / organizationIds /
    global / description / enable。stub 不消费字段，做宽容解析。
    """

    id: Optional[str] = Field(None, description="插件 ID（更新时必填）")
    name: str = Field("", description="插件名称")
    plugin_id: Optional[str] = Field(None, alias="pluginId", description="插件标识")
    file_name: Optional[str] = Field(None, alias="fileName", description="文件名")
    description: str = Field("", description="插件描述")
    enable: Optional[bool] = Field(None, description="是否启用")
    global_: Optional[bool] = Field(None, alias="global", description="是否全局启用")
    organization_ids: Optional[List[str]] = Field(None, alias="organizationIds", description="指定组织 ID")

    model_config = {"extra": "allow", "populate_by_name": True}


class PluginIdBody(BaseModel):
    """按插件 ID 操作（删除）。前端经 GET 路径参数或 POST body 提交。"""

    id: str = Field("", description="插件 ID")

    model_config = {"extra": "allow"}


__all__ = ["PluginUpsertBody", "PluginIdBody"]
