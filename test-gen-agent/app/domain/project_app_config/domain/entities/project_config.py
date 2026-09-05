"""项目应用配置聚合根 ProjectAppConfig。"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.project_app_config.domain.events import ProjectConfigSaved

# 常用模块
MODULE_WORKSTATION = "workstation"
MODULE_TEST_PLAN = "testPlan"
MODULE_BUG_MANAGEMENT = "bugManagement"
MODULE_CASE_MANAGEMENT = "caseManagement"
MODULE_PROJECT_VERSION = "projectVersion"

# 每个模块的默认配置
DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
    "workstation": {"WORKSTATION_SYNC_RULE": True},
    "testPlan": {"TEST_PLAN_CLEAN_REPORT": "3M", "TEST_PLAN_SHARE_REPORT": "1D"},
    "bugManagement": {"BUG_SYNC_SYNC_ENABLE": False},
    "caseManagement": {},
    "apiTesting": {},
    "performanceTesting": {},
}


class ProjectAppConfig(AggregateRoot):
    """项目应用配置聚合根（项目 + 模块 + 配置键 → 配置值）。"""

    def __init__(
        self,
        *,
        project_id: str,
        module: str,
        config_key: str,
        config_value: Any = "",
        updated_at: Optional[float] = None,
    ):
        if not project_id:
            raise DomainValidationError("项目 ID 不能为空")
        if not module:
            raise DomainValidationError("模块名不能为空")
        if not config_key:
            raise DomainValidationError("配置键不能为空")
        self.id = Identifier.of(f"{project_id}:{module}:{config_key}")
        self._project_id = project_id
        self._module = module
        self._config_key = config_key
        self._config_value = config_value
        self._updated_at = updated_at if updated_at is not None else time.time()
        self._domain_events = []
        self.version = 0

    @property
    def project_id(self) -> str:
        return self._project_id
    @property
    def module(self) -> str:
        return self._module
    @property
    def config_key(self) -> str:
        return self._config_key
    @property
    def config_value(self) -> Any:
        return self._config_value

    def set_value(self, value: Any) -> None:
        """更新配置值。"""
        self._config_value = value
        self._updated_at = time.time()
        self.record_event(ProjectConfigSaved(self._project_id, self._module, self._config_key))

    def to_dict(self) -> dict:
        return {
            "project_id": self._project_id,
            "module": self._module,
            "config_key": self._config_key,
            "config_value": self._config_value,
            "updated_at": self._updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "ProjectAppConfig":
        return ProjectAppConfig(
            project_id=data.get("project_id") or data.get("projectId") or "",
            module=data.get("module", ""),
            config_key=data.get("config_key") or data.get("configKey") or "",
            config_value=(
                data.get("config_value")
                if "config_value" in data
                else data.get("configValue")
            ),
            updated_at=(
                data.get("updated_at")
                if data.get("updated_at") is not None
                else data.get("updatedAt")
            ),
        )
