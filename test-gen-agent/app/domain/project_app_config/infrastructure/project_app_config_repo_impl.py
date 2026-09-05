"""项目应用配置聚合仓储实现。"""
from __future__ import annotations

from typing import Any, Dict, List

from app.repositories import project_app_config_repo


class ProjectAppConfigRepoAdapter:
    """将既有 project_app_config_repo 封装为面向配置的仓储。"""

    def get_module_config(self, project_id: str, module: str) -> Dict[str, Any]:
        return project_app_config_repo.get_module_config(project_id, module)

    def save_module_config(self, project_id: str, module: str, config: Dict[str, Any]) -> Dict[str, Any]:
        return project_app_config_repo.save_module_config(project_id, module, config)

    def get_config_value(self, project_id: str, module: str, config_key: str, default: str = "") -> str:
        return project_app_config_repo.get_config_value(project_id, module, config_key, default)

    def set_config_value(self, project_id: str, module: str, config_key: str, value: Any) -> None:
        project_app_config_repo.set_config_value(project_id, module, config_key, value)

    def get_all_modules(self, project_id: str = "") -> List[Dict[str, Any]]:
        return project_app_config_repo.get_all_modules(project_id)
