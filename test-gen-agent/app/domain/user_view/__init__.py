"""用户视图限界上下文。

聚合根：`UserView`（用户自定义视图）
对应现有：`services/user_view_service.py` `repositories/user_view_repo.py`
"""
from app.domain.user_view.application.user_view_app_service import (
    UserViewAppService,
    user_view_app_service,
)
from app.domain.user_view.domain.entities.user_view import UserView

__all__ = ["UserViewAppService", "user_view_app_service", "UserView"]
