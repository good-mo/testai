# app/domain/functional_export/interfaces/router.py
"""functional_export 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.functional_export.application.export_app_service import functional_export_app_service

router = APIRouter(tags=["functional_export"])


@router.post("/api/functional-export")
async def export_cases(request: Request):
    """Export Cases。"""
    try:
        body = await request.json()
        from app.domain.functional_export.application.dto import ExportCasesCommand
        cmd = ExportCasesCommand(**body)
        result = functional_export_app_service.export_cases(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/functional-export/status")
def task_status(request: Request):
    """Task Status。"""
    try:
        result = functional_export_app_service.task_status()
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/functional-export/download/{file_id}")
def download_path(file_id: str, request: Request):
    """Download Path。"""
    try:
        result = functional_export_app_service.download_path(file_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/functional-export/download/{file_id}/meta")
def download_task_meta(file_id: str, request: Request):
    """Download Task Meta。"""
    try:
        result = functional_export_app_service.download_task_meta(file_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))
