# app/domain/file/interfaces/router.py
"""file 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.file.application.file_app_service import file_app_service

router = APIRouter(tags=["file"])


@router.post("/api/file")
async def save_file(request: Request):
    """Save File。"""
    try:
        body = await request.json()
        from app.domain.file.application.dto import SaveFileCommand
        cmd = SaveFileCommand(**body)
        result = file_app_service.save_file(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/file")
def list_files(request: Request):
    """List Files。"""
    try:
        from app.domain.file.application.dto import FileQuery
        cmd = FileQuery(**dict(request.query_params))
        result = file_app_service.list_files(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/file/{file_id}")
def get_file(request: Request):
    """Get File。"""
    try:
        from app.domain.file.application.dto import GetFileCommand
        cmd = GetFileCommand(**dict(request.query_params))
        result = file_app_service.get_file(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/file/{file_id}/meta")
def get_file_meta(file_id: str, request: Request):
    """Get File Meta。"""
    try:
        result = file_app_service.get_file_meta(file_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/file/{file_id}")
def delete_file(file_id: str, request: Request):
    """Delete File。"""
    try:
        from app.domain.file.application.dto import DeleteFileCommand
        cmd = DeleteFileCommand(file_id=file_id)
        result = file_app_service.delete_file(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/file/delete-batch")
async def delete_batch(request: Request):
    """Delete Batch。"""
    try:
        body = await request.json()
        from app.domain.file.application.dto import DeleteBatchCommand
        cmd = DeleteBatchCommand(**body)
        result = file_app_service.delete_batch(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/file/count/{module}")
def count_by_module(request: Request):
    """Count By Module。"""
    try:
        from app.domain.file.application.dto import CountModuleQuery
        cmd = CountModuleQuery(**dict(request.query_params))
        result = file_app_service.count_by_module(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))
