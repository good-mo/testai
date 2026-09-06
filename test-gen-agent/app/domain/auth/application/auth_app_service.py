"""Auth 域应用服务。"""
from typing import Optional
from app.domain.auth.application.dto import (
    AuthenticateCommand, CreateSessionCommand, GetSessionUserQuery,
    DeleteSessionCommand, ListUsersQuery, CreateUserCommand,
    GetUserQuery, UpdateUserCommand, DeleteUserCommand,
    ResetPasswordCommand, SetUserEnabledCommand,
)

class AuthAppService:
    """认证应用服务（委托给传统 auth_service）。"""
    
    def __init__(self):
        from app.services.auth_service import auth_service
        self._service = auth_service
    
    def authenticate(self, cmd: AuthenticateCommand) -> Optional[dict]:
        return self._service.authenticate(cmd.username, cmd.password)
    
    def create_session(self, cmd: CreateSessionCommand) -> dict:
        return self._service.create_session(cmd.user_id, **cmd.kwargs)
    
    def get_session_user(self, query: GetSessionUserQuery) -> Optional[dict]:
        return self._service.get_session_user(query.token)
    
    def delete_session(self, cmd: DeleteSessionCommand) -> bool:
        return self._service.delete_session(cmd.token)
    
    def list_users(self, query: ListUsersQuery) -> list:
        return self._service.list_users(search=query.search, limit=query.limit)
    
    def create_user(self, cmd: CreateUserCommand) -> dict:
        return self._service.create_user(cmd.username, cmd.password, **cmd.kwargs)
    
    def get_user(self, query: GetUserQuery) -> Optional[dict]:
        return self._service.get_user_by_id(query.user_id)
    
    def update_user(self, cmd: UpdateUserCommand) -> Optional[dict]:
        return self._service.update_user(cmd.user_id, **cmd.kwargs)
    
    def delete_user(self, cmd: DeleteUserCommand) -> bool:
        return self._service.delete_user(cmd.user_id)
    
    def reset_password(self, cmd: ResetPasswordCommand) -> bool:
        return self._service.reset_password(cmd.user_id, cmd.new_password)
    
    def set_user_enabled(self, cmd: SetUserEnabledCommand) -> bool:
        return self._service.set_user_enabled(cmd.user_id, cmd.enabled)

auth_app_service = AuthAppService()
__all__ = ["AuthAppService", "auth_app_service"]
