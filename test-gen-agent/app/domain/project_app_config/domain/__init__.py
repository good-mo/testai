"""项目应用配置领域层。"""
from app.domain.project_app_config.domain.entities.project_config import ProjectAppConfig
from app.domain.project_app_config.domain.repository import ProjectAppConfigRepository

__all__ = ["ProjectAppConfig", "ProjectAppConfigRepository"]
