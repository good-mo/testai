# app/domain/display_config/interfaces/router.py
"""display_config 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.display_config.application.display_app_service import display_config_app_service

router = APIRouter(tags=["display_config"])


@router.get("/api/display-config")
def get_all(request: Request):
    """Get All。"""
    try:
        from app.domain.display_config.application.dto import GetDisplayConfigCommand
        cmd = GetDisplayConfigCommand(**dict(request.query_params))
        result = display_config_app_service.get_all(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/display-config")
async def save(request: Request):
    """Save。"""
    try:
        body = await request.json()
        from app.domain.display_config.application.dto import SaveDisplayConfigCommand
        cmd = SaveDisplayConfigCommand(**body)
        result = display_config_app_service.save(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/display-config/{key}")
def delete_by_key(key: str, request: Request):
    """Delete By Key。"""
    try:
        from app.domain.display_config.application.dto import DeleteByKeyCommand
        cmd = DeleteByKeyCommand("key": key)
        result = display_config_app_service.delete_by_key(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/display-config/file/{key}")
def get_file_url(key: str, request: Request):
    """Get File Url。"""
    try:
        result = display_config_app_service.get_file_url(key)
        return ok(result)
    except Exception as e:
        return fail(str(e))
