"""项目应用配置应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class GetModuleConfigCommand:
    project_id: str = ""
    module: str = ""

@dataclass
class SaveModuleConfigCommand:
    project_id: str = ""
    module: str = ""
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SetConfigValueCommand:
    project_id: str = ""
    module: str = ""
    config_key: str = ""
    value: Any = ""

@dataclass
class GetConfigValueCommand:
    project_id: str = ""
    module: str = ""
    config_key: str = ""
    default: str = ""

@dataclass
class ListAllModulesCommand:
    project_id: str = ""

__all__ = ["GetModuleConfigCommand", "SaveModuleConfigCommand", "SetConfigValueCommand",
           "GetConfigValueCommand", "ListAllModulesCommand"]


# ==============================================================================
# 从 models/app_config.py 迁移
# ==============================================================================

# app/models/app_config.py
"""项目应用配置 Pydantic 请求体模型（project_app_config 域）。

承接 app/routers/extra_router.py 中 `/project/application/*` 泛化兜底路由
（前端 menuManagement / menuSetting 缺失接口补充）所消费的 JSON 请求体。

字段同时收录驼峰与蛇形两种命名（前端与历史后端调用均可能携带），默认值
与旧 `read_body(...).get(key, default)` 语义保持一致，保证接入后行为零回归。
"""

from pydantic import BaseModel, Field


class ProjectAppConfigGetBody(BaseModel):
    """查询某项目某模块的应用配置（POST /project/application/{suffix}）。

    前端展开某模块菜单时调用，携带目标 projectId；其余配置项以服务端
    project_app_configs 存储为准，请求体无需再携带。
    """

    project_id: str = Field("", description="项目 ID（蛇形）")
    projectId: str = Field("", description="项目 ID（前端驼峰）")

    @property
    def effective_project_id(self) -> str:
        """驼峰优先、蛇形兜底。"""
        return self.projectId or self.project_id

    model_config = {"extra": "allow"}


class ProjectAppConfigUpdateBody(BaseModel):
    """更新某项目某模块的应用配置（POST /project/application/update/{suffix}）。

    注意：路径参数实为菜单类型后缀，projectId 经请求体传递。type/typeValue
    表示单条配置项的键与值（type 缺省时视为占位、不落库，与旧行为一致）。
    """

    project_id: str = Field("", description="项目 ID（蛇形）")
    projectId: str = Field("", description="项目 ID（前端驼峰）")
    type: str = Field("", description="配置项键（config_key）")
    typeValue: str = Field("", description="配置项值")

    @property
    def effective_project_id(self) -> str:
        """驼峰优先、蛇形兜底。"""
        return self.projectId or self.project_id

    model_config = {"extra": "allow"}


class ProjectAppPlatformSyncBody(BaseModel):
    """平台同步配置请求体（缺陷/用例 平台联调保存）。

    承接 project_compat_application 中
    `/project/application/update/bug/sync` 与
    `/project/application/update/case/related` 的请求体。
    前端以驼峰键上传平台 KEY 与配置 JSON 串；extra allow 保留未声明的
    额外字段以便 `model_dump()` 原样回传。
    """

    PLATFORM_KEY: str = Field("", description="平台 KEY（jira/tapd/zentao 等）")
    BUG_PLATFORM_CONFIG: str = Field("", description="缺陷平台配置 JSON 串")
    CASE_PLATFORM_CONFIG: str = Field("", description="用例平台配置 JSON 串")
    bugPlatformConfig: str = Field("", description="缺陷平台配置（前端驼峰）")
    casePlatformConfig: str = Field("", description="用例平台配置（前端驼峰）")

    model_config = {"extra": "allow"}
