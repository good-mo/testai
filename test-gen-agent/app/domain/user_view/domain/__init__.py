"""用户视图领域层。"""
from app.domain.user_view.domain.entities.user_view import UserView
from app.domain.user_view.domain.repository import UserViewRepository

__all__ = ["UserView", "UserViewRepository"]
