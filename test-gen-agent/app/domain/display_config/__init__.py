"""展示配置（页面/登录页/平台主页 UI 配置）限界上下文。

聚合根：`DisplayConfig`（页面展示配置项）
对应现有：`services/display_config_service.py` `repositories/display_config_repo.py`
"""
from app.domain.display_config.application.display_app_service import (
    DisplayAppService,
    display_app_service,
)
from app.domain.display_config.domain.entities.display_item import DisplayConfigItem

__all__ = ["DisplayAppService", "display_app_service", "DisplayConfigItem"]
