# app/services/project_app_config_service.py
"""项目应用配置业务逻辑层（project_app_config 域 DDD 接入 · 阶段 C 薄门面）。

业务数据访问已收敛到 project_app_config 域 DDD 应用服务
`project_app_config_app_service`（见 `app/domain/project_app_config/`）。
本 Service 收敛为对 DDD 应用门面的**薄委托门面**，仅保留既有方法签名以兼容
`auth/router_system`、`extra_router`、`project_compat_application` 等调用方，
返回结构与重构前一致（DDD 门面底层复用既有 `project_app_config_repo`，默认合并/
upsert/单值读写语义零变化），对外 API 零回归、可回滚。

> 推荐调用方直接使用 `project_app_config_app_service`；本类仅作过渡兼容层保留。
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.domain.project_app_config.application.dto import (
    GetConfigValueCommand,
    GetModuleConfigCommand,
    ListAllModulesCommand,
    SaveModuleConfigCommand,
    SetConfigValueCommand,
)
from app.domain.project_app_config.application.project_app_config_service import (
    project_app_config_app_service as _ddd,
)


class ProjectAppConfigService:
    """项目应用配置服务：router 层唯一业务入口（DDD 薄门面）。"""

    # ── 模块配置（菜单管理） ──────────────────────────
    def get_module_config(self, project_id: str, module: str) -> Dict[str, Any]:
        """获取某模块的配置（合并默认值）。"""
        return _ddd.get_module_config(GetModuleConfigCommand(
            project_id=project_id, module=module,
        ))

    def save_module_config(self, project_id: str, module: str,
                           config: Dict[str, Any]) -> Dict[str, Any]:
        """保存某模块的配置并返回更新后的完整配置。"""
        return _ddd.save_module_config(SaveModuleConfigCommand(
            project_id=project_id, module=module, config=config,
        ))

    def get_all_modules(self, project_id: str = "") -> List[Dict[str, Any]]:
        """返回菜单管理列表（顶层模块）。"""
        return _ddd.list_all_modules(ListAllModulesCommand(project_id=project_id))

    # ── projectVersion 模块启用开关 ────────────────────
    def is_project_version_enabled(self, project_id: str) -> bool:
        """项目版本功能是否启用。"""
        return _ddd.is_project_version_enabled(project_id)

    def set_project_version_enabled(self, project_id: str, enabled: bool) -> None:
        """设置项目版本功能启用状态。"""
        _ddd.set_project_version_enabled(project_id, enabled)

    # ── 通用单值读写（供同表扩展使用）─────────────────
    def get_config_value(self, project_id: str, module: str, config_key: str,
                         default: str = "") -> str:
        """读取单条原始配置值。"""
        return _ddd.get_config_value(GetConfigValueCommand(
            project_id=project_id, module=module, config_key=config_key,
            default=default,
        ))

    def set_config_value(self, project_id: str, module: str, config_key: str,
                         value: Any) -> None:
        """写入单条配置。"""
        _ddd.set_config_value(SetConfigValueCommand(
            project_id=project_id, module=module, config_key=config_key, value=value,
        ))


project_app_config_service = ProjectAppConfigService()


__all__ = ["project_app_config_service", "ProjectAppConfigService"]
