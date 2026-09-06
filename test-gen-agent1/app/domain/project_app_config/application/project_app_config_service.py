"""项目应用配置应用服务。"""
from __future__ import annotations

from typing import Any, Dict, List

from app.domain.project_app_config.application.dto import (
    GetConfigValueCommand,
    GetModuleConfigCommand,
    ListAllModulesCommand,
    SaveModuleConfigCommand,
    SetConfigValueCommand,
)
from app.domain.project_app_config.infrastructure.project_app_config_repo_impl import (
    ProjectAppConfigRepoAdapter,
)


class ProjectAppConfigAppService:
    """项目应用配置用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or ProjectAppConfigRepoAdapter()

    def get_module_config(self, cmd: GetModuleConfigCommand) -> Dict[str, Any]:
        return self._repo.get_module_config(cmd.project_id, cmd.module)

    def save_module_config(self, cmd: SaveModuleConfigCommand) -> Dict[str, Any]:
        return self._repo.save_module_config(cmd.project_id, cmd.module, cmd.config)

    def get_config_value(self, cmd: GetConfigValueCommand) -> str:
        return self._repo.get_config_value(
            cmd.project_id, cmd.module, cmd.config_key, cmd.default)

    def set_config_value(self, cmd: SetConfigValueCommand) -> None:
        self._repo.set_config_value(cmd.project_id, cmd.module, cmd.config_key, cmd.value)

    def list_all_modules(self, cmd: ListAllModulesCommand) -> List[Dict[str, Any]]:
        return self._repo.get_all_modules(cmd.project_id)

    def is_project_version_enabled(self, project_id: str) -> bool:
        raw = self._repo.get_config_value(project_id, "projectVersion", "enabled", default="")
        return raw.lower() in ("true", "1", "yes")

    def set_project_version_enabled(self, project_id: str, enabled: bool) -> None:
        self._repo.set_config_value(project_id, "projectVersion", "enabled", enabled)


project_app_config_app_service = ProjectAppConfigAppService()
