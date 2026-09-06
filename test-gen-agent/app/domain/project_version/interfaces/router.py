# app/domain/project_version/interfaces/router.py
"""project_version 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.project_version.application.project_version_app_service import project_version_app_service

router = APIRouter(tags=["project_version"])


@router.get("/api/project-version")
def list(request: Request):
    """List。"""
    try:
        from app.domain.project_version.application.dto import ListVersionsCommand
        cmd = ListVersionsCommand(**dict(request.query_params))
        result = project_version_app_service.list(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/project-version/{version_id}")
def get(request: Request):
    """Get。"""
    try:
        from app.domain.project_version.application.dto import GetVersionCommand
        cmd = GetVersionCommand(**dict(request.query_params))
        result = project_version_app_service.get(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/project-version")
async def create(request: Request):
    """Create。"""
    try:
        body = await request.json()
        from app.domain.project_version.application.dto import CreateVersionCommand
        cmd = CreateVersionCommand(**body)
        result = project_version_app_service.create(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.put("/api/project-version/{version_id}")
async def update(version_id: str, request: Request):
    """Update。"""
    try:
        body = await request.json()
        body["version_id"] = version_id
        from app.domain.project_version.application.dto import UpdateVersionCommand
        cmd = UpdateVersionCommand(**body)
        result = project_version_app_service.update(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/project-version/{version_id}")
def delete(version_id: str, request: Request):
    """Delete。"""
    try:
        from app.domain.project_version.application.dto import DeleteVersionCommand
        cmd = DeleteVersionCommand("version_id": version_id)
        result = project_version_app_service.delete(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/project-version/options/{project_id}")
def options(project_id: str, request: Request):
    """Options。"""
    try:
        result = project_version_app_service.options(project_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/project-version/{version_id}/latest")
async def set_latest(version_id: str, request: Request):
    """Set Latest。"""
    try:
        result = project_version_app_service.set_latest(version_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))
