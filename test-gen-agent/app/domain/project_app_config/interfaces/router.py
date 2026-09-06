# app/domain/project_app_config/interfaces/router.py
"""project_app_config 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.project_app_config.application.project_app_config_service import project_app_config_service

router = APIRouter(tags=["project_app_config"])


@router.get("/api/project-config/{project_id}/{module}")
def get_module_config(request: Request):
    """Get Module Config。"""
    try:
        from app.domain.project_app_config.application.dto import GetModuleConfigCommand
        cmd = GetModuleConfigCommand(**dict(request.query_params))
        result = project_app_config_service.get_module_config(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/project-config/{project_id}/{module}")
async def save_module_config(request: Request):
    """Save Module Config。"""
    try:
        body = await request.json()
        from app.domain.project_app_config.application.dto import SaveModuleConfigCommand
        cmd = SaveModuleConfigCommand(**body)
        result = project_app_config_service.save_module_config(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/project-config/{project_id}/{module}/{key}")
def get_config_value(request: Request):
    """Get Config Value。"""
    try:
        from app.domain.project_app_config.application.dto import GetConfigValueCommand
        cmd = GetConfigValueCommand(**dict(request.query_params))
        result = project_app_config_service.get_config_value(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/project-config/{project_id}/{module}/{key}")
async def set_config_value(request: Request):
    """Set Config Value。"""
    try:
        body = await request.json()
        from app.domain.project_app_config.application.dto import SetConfigValueCommand
        cmd = SetConfigValueCommand(**body)
        result = project_app_config_service.set_config_value(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/project-config/{project_id}/modules")
def list_all_modules(request: Request):
    """List All Modules。"""
    try:
        from app.domain.project_app_config.application.dto import ListAllModulesCommand
        cmd = ListAllModulesCommand(**dict(request.query_params))
        result = project_app_config_service.list_all_modules(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))
