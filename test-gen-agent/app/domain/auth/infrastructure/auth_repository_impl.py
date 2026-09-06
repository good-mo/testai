"""Auth 域仓储实现（委托给传统 auth_service）。"""
from typing import Optional

class AuthRepositoryImpl:
    """认证仓储实现。"""
    
    def __init__(self):
        from app.services.auth_service import auth_service
        self._service = auth_service
    
    def authenticate(self, username: str, password: str) -> Optional[dict]:
        return self._service.authenticate(username, password)
    
    def create_session(self, user_id: str, **kwargs) -> dict:
        return self._service.create_session(user_id, **kwargs)
    
    def get_session_user(self, token: str) -> Optional[dict]:
        return self._service.get_session_user(token)
    
    def delete_session(self, token: str) -> bool:
        return self._service.delete_session(token)
    
    def list_users(self, search: str = "", limit: int = 50) -> list:
        return self._service.list_users(search=search, limit=limit)
    
    def create_user(self, username: str, password: str, **kwargs) -> dict:
        return self._service.create_user(username, password, **kwargs)
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        return self._service.get_user_by_id(user_id)
    
    def update_user(self, user_id: str, **kwargs) -> Optional[dict]:
        return self._service.update_user(user_id, **kwargs)
    
    def delete_user(self, user_id: str) -> bool:
        return self._service.delete_user(user_id)
    
    def reset_password(self, user_id: str, new_password: str) -> bool:
        return self._service.reset_password(user_id, new_password)
    
    def set_user_enabled(self, user_id: str, enabled: bool) -> bool:
        return self._service.set_user_enabled(user_id, enabled)

auth_repository = AuthRepositoryImpl()
__all__ = ["AuthRepositoryImpl", "auth_repository"]
