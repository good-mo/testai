"""项目应用配置限界上下文。

聚合根：`ProjectAppConfig`（项目模块配置项）
对应现有：`services/project_app_config_service.py` `repositories/project_app_config_repo.py`
"""
from app.domain.project_app_config.application.project_app_config_service import (
    ProjectAppConfigAppService,
    project_app_config_app_service,
)
from app.domain.project_app_config.domain.entities.project_config import ProjectAppConfig

__all__ = ["ProjectAppConfigAppService", "project_app_config_app_service", "ProjectAppConfig"]
