# app/models/method_compat.py
"""HTTP 方法兼容域（method_compat.py）请求体模型。

对应 app/routers/method_compat.py 中手写 read_body 解析的 POST 兼容端点。
该路由是跨域方法补齐（任务中心分页 / 组织/项目成员列表 / 插件表单选项 /
资源池容量 / 环境组删除 / 任务排队），各 body 独立建档，保持与旧 read_body
归一化一致的宽松语义（空体/裸标量/数组不抛 422），接入后行为零回归。
"""

from typing import Any

from pydantic import BaseModel, Field, model_validator


def _first_nonempty(*values: Any, default: Any = "") -> Any:
    """返回首个非空值，全部为空则取 default。"""
    for v in values:
        if v is not None and v != "":
            return v
    return default


class _LenientRequest(BaseModel):
    """历史兼容：容忍裸字符串/数组/空请求体，语义与旧 read_body 一致。"""

    model_config = {"extra": "allow", "populate_by_name": True}

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


def _int(val: Any, default: int) -> int:
    """宽松转 int，失败回落 default。"""
    try:
        return int(val) if val is not None and val != "" else default
    except (TypeError, ValueError):
        return default


class _LenientPageBody(_LenientRequest):
    """通用宽松分页基类：current/pageSize 兼容驼峰与整型字符串。"""

    current: Any = Field(None, description="当前页")
    pageSize: Any = Field(None, description="每页条数")

    @property
    def effective_current(self) -> int:
        return _int(self.current, 1)

    @property
    def effective_page_size(self) -> int:
        return _int(self.pageSize, 10)


class TaskCenterPageBody(_LenientPageBody):
    """任务中心分页（schedule/exec-task/item/batch 三级共用）。"""

    keyword: str = Field("", description="搜索关键字")


class TaskCenterOrderBody(_LenientRequest):
    """任务排队信息：前端传数组，read_body 归一化为 {"ids":[...]}。"""

    ids: Any = Field(None, description="任务 ID 列表（read_body 数组归一化产物）")

    @property
    def effective_ids(self) -> list:
        ids = self.ids if self.ids is not None else []
        if isinstance(ids, str):
            ids = [ids]
        return list(ids) if isinstance(ids, (list, tuple)) else []


class OrgMemberListBody(_LenientPageBody):
    """组织成员列表（organizationId 驼峰优先、orgId/organization_id 蛇形兜底）。"""

    organizationId: Any = Field(None, description="组织 ID（驼峰）")
    orgId: Any = Field(None, description="组织 ID（别名）")
    organization_id: Any = Field(None, description="组织 ID（蛇形）")
    keyword: Any = Field(None, description="搜索关键字")
    search: Any = Field(None, description="搜索关键字（别名）")

    @property
    def effective_org_id(self) -> str:
        return str(
            _first_nonempty(
                self.organizationId, self.orgId, self.organization_id, default="default-org"
            )
        )

    @property
    def effective_keyword(self) -> str:
        return str(_first_nonempty(self.keyword, self.search, default=""))


class ProjectMemberListBody(_LenientPageBody):
    """系统项目成员列表（projectId 驼峰优先、project_id 蛇形兜底）。"""

    projectId: Any = Field(None, description="项目 ID（驼峰）")
    project_id: Any = Field(None, description="项目 ID（蛇形）")
    keyword: Any = Field(None, description="搜索关键字")
    search: Any = Field(None, description="搜索关键字（别名）")

    @property
    def effective_project_id(self) -> str:
        return str(_first_nonempty(self.projectId, self.project_id, default=""))

    @property
    def effective_keyword(self) -> str:
        return str(_first_nonempty(self.keyword, self.search, default=""))


class PluginFormOptionBody(_LenientRequest):
    """插件表单选项（pluginId 为主、pluginFormOptionId 别名兜底）。"""

    pluginId: Any = Field(None, description="插件 ID")
    pluginFormOptionId: Any = Field(None, description="插件表单选项 ID（别名）")

    @property
    def effective_plugin_id(self) -> str:
        return str(_first_nonempty(self.pluginId, self.pluginFormOptionId, default=""))


class ResourcePoolCapacityListBody(_LenientPageBody):
    """资源池容量任务列表分页。"""


class EnvGroupDeleteBody(_LenientRequest):
    """删除环境组（取 id）。"""

    id: Any = Field(None, description="环境组 ID")

    @property
    def effective_id(self) -> str:
        return str(self.id or "")


__all__ = [
    "TaskCenterPageBody",
    "TaskCenterOrderBody",
    "OrgMemberListBody",
    "ProjectMemberListBody",
    "PluginFormOptionBody",
    "ResourcePoolCapacityListBody",
    "EnvGroupDeleteBody",
]
