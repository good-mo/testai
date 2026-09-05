"""前端兼容 API 测试限界上下文。

前端兼容页面接口（接口定义/用例/场景/Mock）的适配层。
本域为轻域：数据访问委托 `apitest` 上下文的仓储。

对应现有：`services/frontend_api_service.py`
"""
from app.domain.frontend_api.application.frontend_api_app_service import (
    FrontendApiAppService,
    frontend_api_app_service,
)
from app.domain.frontend_api.domain.entities.api_import import ApiImport

__all__ = ["FrontendApiAppService", "frontend_api_app_service", "ApiImport"]
