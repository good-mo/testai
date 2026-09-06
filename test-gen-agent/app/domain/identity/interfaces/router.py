# app/domain/identity/interfaces/router.py
"""identity 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.identity.application.identity_app_service import identity_app_service

router = APIRouter(tags=["identity"])


@router.post("/api/identity/user")
async def create_user(request: Request):
    """Create User。"""
    try:
        body = await request.json()
        from app.domain.identity.application.dto import CreateUserCommand
        cmd = CreateUserCommand(**body)
        result = identity_app_service.create_user(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/identity/user/{user_id}")
def get_user(user_id: str, request: Request):
    """Get User。"""
    try:
        result = identity_app_service.get_user(user_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.put("/api/identity/user/{user_id}")
async def update_user(user_id: str, request: Request):
    """Update User。"""
    try:
        body = await request.json()
        body["user_id"] = user_id
        from app.domain.identity.application.dto import UpdateUserCommand
        cmd = UpdateUserCommand(**body)
        result = identity_app_service.update_user(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/identity/user/{user_id}/enable")
async def set_user_enabled(request: Request):
    """Set User Enabled。"""
    try:
        body = await request.json()
        from app.domain.identity.application.dto import SetUserEnabledCommand
        cmd = SetUserEnabledCommand(**body)
        result = identity_app_service.set_user_enabled(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/identity/user/{user_id}/password")
async def change_password(request: Request):
    """Change Password。"""
    try:
        body = await request.json()
        from app.domain.identity.application.dto import ChangePasswordCommand
        cmd = ChangePasswordCommand(**body)
        result = identity_app_service.change_password(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/identity/users")
def list_users(request: Request):
    """List Users。"""
    try:
        from app.domain.identity.application.dto import UserListQuery
        cmd = UserListQuery(**dict(request.query_params))
        result = identity_app_service.list_users(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/identity/organization")
async def create_organization(request: Request):
    """Create Organization。"""
    try:
        body = await request.json()
        from app.domain.identity.application.dto import CreateOrganizationCommand
        cmd = CreateOrganizationCommand(**body)
        result = identity_app_service.create_organization(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))
