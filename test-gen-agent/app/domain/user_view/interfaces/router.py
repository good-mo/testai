# app/domain/user_view/interfaces/router.py
"""user_view 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.user_view.application.user_view_app_service import user_view_app_service

router = APIRouter(tags=["user_view"])


@router.get("/api/user-view")
def list_custom_views(request: Request):
    """List Custom Views。"""
    try:
        from app.domain.user_view.application.dto import ListUserViewsCommand
        cmd = ListUserViewsCommand(**dict(request.query_params))
        result = user_view_app_service.list_custom_views(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/user-view/{view_id}")
def get(request: Request):
    """Get。"""
    try:
        from app.domain.user_view.application.dto import GetUserViewCommand
        cmd = GetUserViewCommand(**dict(request.query_params))
        result = user_view_app_service.get(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/user-view")
async def create(request: Request):
    """Create。"""
    try:
        body = await request.json()
        from app.domain.user_view.application.dto import CreateUserViewCommand
        cmd = CreateUserViewCommand(**body)
        result = user_view_app_service.create(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.put("/api/user-view/{view_id}")
async def update(view_id: str, request: Request):
    """Update。"""
    try:
        body = await request.json()
        body["view_id"] = view_id
        from app.domain.user_view.application.dto import UpdateUserViewCommand
        cmd = UpdateUserViewCommand(**body)
        result = user_view_app_service.update(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/user-view/{view_id}")
def delete(view_id: str, request: Request):
    """Delete。"""
    try:
        from app.domain.user_view.application.dto import DeleteUserViewCommand
        cmd = DeleteUserViewCommand(view_id=view_id)
        result = user_view_app_service.delete(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))
