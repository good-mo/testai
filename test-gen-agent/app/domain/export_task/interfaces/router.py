# app/domain/export_task/interfaces/router.py
"""export_task 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.export_task.application.export_task_app_service import export_task_app_service

router = APIRouter(tags=["export_task"])


@router.post("/api/export-task")
async def register(request: Request):
    """Register。"""
    try:
        body = await request.json()
        from app.domain.export_task.application.dto import RegisterTaskCommand
        cmd = RegisterTaskCommand(**body)
        result = export_task_app_service.register(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/export-task/{task_id}")
def get(request: Request):
    """Get。"""
    try:
        from app.domain.export_task.application.dto import GetTaskCommand
        cmd = GetTaskCommand(**dict(request.query_params))
        result = export_task_app_service.get(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/export-task/{task_id}")
def remove(task_id: str, request: Request):
    """Remove。"""
    try:
        from app.domain.export_task.application.dto import RemoveTaskCommand
        cmd = RemoveTaskCommand("task_id": task_id)
        result = export_task_app_service.remove(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/export-task/latest")
def latest(request: Request):
    """Latest。"""
    try:
        result = export_task_app_service.latest()
        return ok(result)
    except Exception as e:
        return fail(str(e))
