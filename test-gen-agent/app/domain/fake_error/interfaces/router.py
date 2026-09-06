# app/domain/fake_error/interfaces/router.py
"""fake_error 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.fake_error.application.fake_error_app_service import fake_error_app_service

router = APIRouter(tags=["fake_error"])


@router.get("/api/fake-error")
def list(request: Request):
    """List。"""
    try:
        from app.domain.fake_error.application.dto import ListRulesCommand
        cmd = ListRulesCommand(**dict(request.query_params))
        result = fake_error_app_service.list(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/fake-error")
async def add_rules(request: Request):
    """Add Rules。"""
    try:
        body = await request.json()
        from app.domain.fake_error.application.dto import AddRulesCommand
        cmd = AddRulesCommand(**body)
        result = fake_error_app_service.add_rules(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/fake-error/{project_id}")
def delete(project_id: str, request: Request):
    """Delete。"""
    try:
        from app.domain.fake_error.application.dto import DeleteRulesCommand
        cmd = DeleteRulesCommand("project_id": project_id)
        result = fake_error_app_service.delete(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/fake-error/enable")
async def update_enable(request: Request):
    """Update Enable。"""
    try:
        body = await request.json()
        from app.domain.fake_error.application.dto import UpdateEnableCommand
        cmd = UpdateEnableCommand(**body)
        result = fake_error_app_service.update_enable(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/fake-error/count/{project_id}")
def get_enabled_count(project_id: str, request: Request):
    """Get Enabled Count。"""
    try:
        result = fake_error_app_service.get_enabled_count(project_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))
