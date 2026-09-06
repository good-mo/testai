# app/models/integration.py
"""服务集成 / SSO 平台配置 Pydantic 请求体模型。

对应 `app/routers/integrations.py`（工作流 C-3 兼容路由）。

该路由长期是「占位 stub」：POST 处理器此前仅 `await read_body(req)`
消费请求体后返回空 `ok()`，未落库、未取任何字段。为收敛「手写
read_body 解析」并便于后续真实实现时直接取用配置字段，这里据前端
（serviceIntegration / qrCode 配置页）实际下发的字段建档请求体模型。

字段同时收录驼峰与下划线两种命名（前端与历史后端调用均可能携带），
全部默认 `extra: allow`，避免遗漏新增字段导致 400；并对空体 / 裸标量
做归一，保持旧 `read_body()` 的空体返回 200 语义。
"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, model_validator


class _LenientRequest(BaseModel):
    """历史兼容：容忍前端经 axios 拦截器发送的裸标量请求体。

    旧路由用 read_body() 会把裸字符串 `"x"` 归一化成 `{"id": "x"}`、
    数组归一化成 `{"ids": [...]}`、空体归一化成 `{}`。改用 Pydantic
    请求体模型后若不处理，FastAPI 会对裸标量判 422，故把同一段
    归一化上移到模型层（等价空体/无效体返回 200 的既有契约）。
    """

    @model_validator(mode="before")
    @classmethod
    def _lenient_coerce(cls, raw):
        if raw is None or isinstance(raw, (str, list)):
            return {}
        return raw


# ── 服务集成 /service/integration/* ─────────────────────────
class ServiceIntegrationBody(_LenientRequest):
    """添加/更新服务集成。

    对应前端 `AddOrUpdateServiceModel`：主键、插件 id、是否启用、
    组织 id，以及随插件而异的动态 `configuration` 配置字典。
    """

    id: Optional[str] = Field(None, description="集成记录 ID（更新时必填）")
    pluginId: Optional[str] = Field(None, description="插件 ID（前端驼峰）")
    plugin_id: Optional[str] = Field(None, description="插件 ID（下划线兜底）")
    enable: Optional[bool] = Field(False, description="是否启用")
    organizationId: Optional[str] = Field(None, description="组织 ID（前端驼峰）")
    organization_id: Optional[str] = Field(None, description="组织 ID（下划线兜底）")
    configuration: Optional[Dict[str, Any]] = Field(None, description="插件配置项（随插件而异）")

    model_config = {"extra": "allow"}


class ServiceIntegrationDeleteBody(_LenientRequest):
    """删除服务集成（按 ID）。"""

    id: Optional[str] = Field(None, description="集成记录 ID")

    model_config = {"extra": "allow"}


class ServiceIntegrationValidateBody(_LenientRequest):
    """校验服务集成（测试连接）。

    前端 `/service/integration/validate/{plugin_id}/{org_id}` 携带
    pluginId / organizationId；body 内还可能有随插件而异的连接参数。
    """

    pluginId: Optional[str] = Field(None, description="插件 ID（前端驼峰）")
    plugin_id: Optional[str] = Field(None, description="插件 ID（下划线兜底）")
    organizationId: Optional[str] = Field(None, description="组织 ID（前端驼峰）")
    organization_id: Optional[str] = Field(None, description="组织 ID（下划线兜底）")
    configuration: Optional[Dict[str, Any]] = Field(None, description="插件配置项（随插件而异）")

    model_config = {"extra": "allow"}


# ── SSO 平台配置 save / validate / enable / change-validate ──
# 各平台 save 与 validate 均携带完整配置对象（含 valid 回显位）：
#   企微 WeCom   : corpId / agentId / appSecret / callBack / enable / valid
#   钉钉 DingTalk: agentId / appKey / appSecret / callBack / enable / valid
#   飞书 Lark    : agentId / appSecret / callBack / enable / valid（LarkSuite 同构）
class _PlatformConfigBase(_LenientRequest):
    """平台 SSO 配置共字段（agentId / callBack / enable / valid）。"""

    agentId: Optional[str] = Field(None, description="应用 agentId（前端驼峰）")
    agent_id: Optional[str] = Field(None, description="应用 agentId（下划线兜底）")
    callBack: Optional[str] = Field(None, description="回调地址 callBack（前端驼峰）")
    call_back: Optional[str] = Field(None, description="回调地址（下划线兜底）")
    enable: Optional[bool] = Field(False, description="是否启用")
    valid: Optional[bool] = Field(False, description="是否已校验通过")

    model_config = {"extra": "allow"}


class WeComConfigBody(_PlatformConfigBase):
    """企业微信 SSO 配置（save / validate）。"""

    corpId: Optional[str] = Field(None, description="企业 corpId（前端驼峰）")
    corp_id: Optional[str] = Field(None, description="企业 corpId（下划线兜底）")
    appSecret: Optional[str] = Field(None, description="应用 appSecret（前端驼峰）")
    app_secret: Optional[str] = Field(None, description="应用 appSecret（下划线兜底）")


class DingTalkConfigBody(_PlatformConfigBase):
    """钉钉 SSO 配置（save / validate）。"""

    appKey: Optional[str] = Field(None, description="应用 appKey（前端驼峰）")
    app_key: Optional[str] = Field(None, description="应用 appKey（下划线兜底）")
    appSecret: Optional[str] = Field(None, description="应用 appSecret（前端驼峰）")
    app_secret: Optional[str] = Field(None, description="应用 appSecret（下划线兜底）")


class LarkConfigBody(_PlatformConfigBase):
    """飞书 SSO 配置（save / validate）。"""

    appSecret: Optional[str] = Field(None, description="应用 appSecret（前端驼峰）")
    app_secret: Optional[str] = Field(None, description="应用 appSecret（下划线兜底）")


class LarkSuiteConfigBody(LarkConfigBody):
    """国际飞书 SSO 配置（save / validate），字段与 Lark 同构。"""


class PlatformEnableBody(_LenientRequest):
    """启用/禁用某平台 SSO（enable 切换）。"""

    enable: Optional[bool] = Field(False, description="是否启用")
    platform: Optional[str] = Field(None, description="平台名（可选）")

    model_config = {"extra": "allow"}
