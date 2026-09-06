"""Auth 域路由适配器。"""
from fastapi import APIRouter, Request
from app.core.response import ok, fail
from app.domain.auth.application.auth_app_service import auth_app_service

router = APIRouter(tags=["auth"])

@router.post("/api/auth/login")
async def login(request: Request):
    """用户登录。"""
    try:
        body = await request.json()
        from app.domain.auth.application.dto import AuthenticateCommand
        cmd = AuthenticateCommand(username=body.get("username", ""), password=body.get("password", ""))
        result = auth_app_service.authenticate(cmd)
        return ok(result) if result else fail("Invalid credentials", code=401)
    except Exception as e:
        return fail(str(e))

@router.post("/api/auth/logout")
async def logout(request: Request):
    """用户登出。"""
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        from app.domain.auth.application.dto import DeleteSessionCommand
        cmd = DeleteSessionCommand(token=token)
        result = auth_app_service.delete_session(cmd)
        return ok({"logged_out": result})
    except Exception as e:
        return fail(str(e))

@router.get("/api/auth/users")
def list_users(request: Request):
    """列出用户。"""
    try:
        from app.domain.auth.application.dto import ListUsersQuery
        query = ListUsersQuery(
            search=request.query_params.get("search", ""),
            limit=int(request.query_params.get("limit", "50"))
        )
        result = auth_app_service.list_users(query)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/auth/users")
async def create_user(request: Request):
    """创建用户。"""
    try:
        body = await request.json()
        from app.domain.auth.application.dto import CreateUserCommand
        cmd = CreateUserCommand(
            username=body.get("username", ""),
            password=body.get("password", ""),
            kwargs=body
        )
        result = auth_app_service.create_user(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/auth/users/{user_id}")
def get_user(user_id: str, request: Request):
    """获取用户详情。"""
    try:
        from app.domain.auth.application.dto import GetUserQuery
        query = GetUserQuery(user_id=user_id)
        result = auth_app_service.get_user(query)
        return ok(result) if result else fail("User not found", code=404)
    except Exception as e:
        return fail(str(e))

@router.put("/api/auth/users/{user_id}")
async def update_user(user_id: str, request: Request):
    """更新用户。"""
    try:
        body = await request.json()
        from app.domain.auth.application.dto import UpdateUserCommand
        cmd = UpdateUserCommand(user_id=user_id, kwargs=body)
        result = auth_app_service.update_user(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/auth/users/{user_id}")
def delete_user(user_id: str, request: Request):
    """删除用户。"""
    try:
        from app.domain.auth.application.dto import DeleteUserCommand
        cmd = DeleteUserCommand(user_id=user_id)
        result = auth_app_service.delete_user(cmd)
        return ok({"deleted": result})
    except Exception as e:
        return fail(str(e))

@router.post("/api/auth/users/{user_id}/reset-password")
async def reset_password(user_id: str, request: Request):
    """重置密码。"""
    try:
        body = await request.json()
        from app.domain.auth.application.dto import ResetPasswordCommand
        cmd = ResetPasswordCommand(user_id=user_id, new_password=body.get("new_password", ""))
        result = auth_app_service.reset_password(cmd)
        return ok({"success": result})
    except Exception as e:
        return fail(str(e))

@router.post("/api/auth/users/{user_id}/enable")
async def set_user_enabled(user_id: str, request: Request):
    """设置用户启用状态。"""
    try:
        body = await request.json()
        from app.domain.auth.application.dto import SetUserEnabledCommand
        cmd = SetUserEnabledCommand(user_id=user_id, enabled=body.get("enabled", True))
        result = auth_app_service.set_user_enabled(cmd)
        return ok({"success": result})
    except Exception as e:
        return fail(str(e))
