# app/routers/attachment.py
"""业务域路由：attachment 兼容路由。迁移自 app/adapters/domains/attachment.py，占位 stub 原样保留。"""

import uuid

from fastapi import APIRouter, Request

from app.core.response import ok, read_body
from app.logging_config import get_logger
from app.models.file import FileDownloadBody

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-attachment"])


async def _read_body(request: Request) -> dict:
    """安全读取请求体。"""
    return await read_body(request)


@router.post("/attachment/check-update")
def attachment_check_update_post(request: Request):
    """附件更新检查（POST兼容）。"""
    return ok()


@router.post("/attachment/download/file")
async def attachment_download_file_post(body: FileDownloadBody):
    """附件下载（POST兼容，返回实际文件二进制）。"""
    file_id = body.id or body.fileId
    if not file_id:
        return ok({"fileId": ""})
    from app.domain.file.application.file_app_service import file_service
    fname = file_service.find_upload_file(file_id)
    if not fname:
        return ok({"fileId": file_id, "fileName": ""})
    from fastapi.responses import FileResponse
    return FileResponse(
        file_service.resolve_path(fname),
        filename=fname.split("_", 1)[1] if "_" in fname else fname,
    )


@router.post("/attachment/preview")
async def attachment_preview_post(request: Request):
    """附件预览（POST兼容）。

    前端 previewFile 以 blob 方式获取文件内容，直接返回文件。
    """
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    file_id = body.get("fileId") or body.get("id") or ""
    if not file_id:
        return ok()
    from app.domain.file.application.file_app_service import file_service
    fname = file_service.find_upload_file(file_id)
    if not fname:
        return ok()
    from fastapi.responses import FileResponse
    return FileResponse(file_service.resolve_path(fname))


@router.get("/attachment/options/{project_id}")
@router.post("/attachment/options/{project_id}")
def attachment_options_path(project_id: str):
    """获取附件选项（带路径参数）。"""
    return ok({"project_id": project_id})


@router.get("/attachment/update/{attachment_id}/{project_id}")
@router.post("/attachment/update/{attachment_id}/{project_id}")
def attachment_update_path(attachment_id: str, project_id: str):
    """更新附件（带路径参数）。"""
    return ok({"attachment_id": attachment_id, "project_id": project_id})


# ════════════════════════════════════════════════════════════
# 功能用例
# ════════════════════════════════════════════════════════════


@router.post("/attachment/download")
async def api_attachment_download_post(request: Request):
    """下载附件（POST 兼容前端调用）。

    前端 previewFile/downloadFileRequest 以 blob 方式请求；
    该路由返回文件内容。若未找到文件则返回 JSON 提示。
    """
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    file_id = body.get("fileId") or body.get("id") or ""
    if not file_id:
        return ok({"fileId": "", "fileName": ""})
    from app.domain.file.application.file_app_service import file_service
    fname = file_service.find_upload_file(file_id)
    if not fname:
        return ok({"fileId": file_id, "fileName": ""})
    from fastapi.responses import FileResponse
    return FileResponse(
        file_service.resolve_path(fname),
        filename=file_service._original_name(fname) if hasattr(file_service, '_original_name') else fname,
    )


@router.post("/attachment/upload/file")
def attachment_upload_file(request: Request):
    """上传文件并关联用例。"""
    return ok({
        "fileId": str(uuid.uuid4()),
        "fileName": "uploaded_file",
    })


@router.post("/attachment/transfer")
async def attachment_transfer(request: Request):
    """转存文件：将文件复制到指定项目/模块（真实更新 file_repo 归属元数据）。"""
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    file_id = body.get("fileId") or body.get("id") or ""
    target_project = body.get("projectId") or ""
    target_module = body.get("moduleId") or "root"
    if not file_id:
        return ok({"success": False, "msg": "缺少文件 ID"})
    from app.repositories.file_repo import file_repo
    from app.domain.file.application.file_app_service import file_service
    meta = file_service.get_file_meta(file_id)
    if not meta:
        return ok({"success": False, "msg": "文件不存在"})
    # 转存到目标项目/模块（复用物理文件，仅更新归属元数据）
    file_repo.upsert_meta(file_id, {
        "name": meta.get("name", ""),
        "project_id": target_project,
        "module_id": target_module or "root",
        "storage": "minio",
    })
    return ok({"success": True, "fileId": file_id, "moduleId": target_module})


@router.get("/attachment/preview")
def attachment_preview():
    """预览文件（需通过 id 或 fileId 参数定位）。"""
    return ok(None)


@router.get("/attachment/download")
def attachment_download(request: Request = None):
    """下载文件（从 query 参数中取 fileId，返回文件二进制）。"""
    if request is None:
        return ok(None)
    file_id = request.query_params.get("fileId", "") or request.query_params.get("id", "")
    if not file_id:
        return ok(None)
    from app.domain.file.application.file_app_service import file_service
    fname = file_service.find_upload_file(file_id)
    if not fname:
        return ok(None)
    from fastapi.responses import FileResponse
    return FileResponse(file_service.resolve_path(fname))


@router.post("/attachment/delete/file")
async def attachment_delete_file(request: Request):
    """删除文件或取消关联（真实删除物理文件与元数据）。"""
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    file_ids = body.get("ids") or body.get("selectIds") or []
    file_id = body.get("fileId") or body.get("id") or ""
    if isinstance(file_ids, str):
        file_ids = [file_ids]
    if file_id and not file_ids:
        file_ids = [file_id]
    from app.domain.file.application.file_app_service import file_service
    for fid in file_ids:
        file_service.delete_file(str(fid))
    return ok({"deleted": len(file_ids)})


@router.get("/attachment/options")
def attachment_options():
    """获取转存目录。"""
    return ok([])


@router.post("/attachment/update")
async def attachment_update(request: Request):
    """更新附件归属元数据。"""
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    file_id = body.get("fileId") or body.get("id") or ""
    project_id = body.get("projectId") or ""
    module_id = body.get("moduleId") or "root"
    if not file_id:
        return ok({"success": False})
    from app.repositories.file_repo import file_repo
    from app.domain.file.application.file_app_service import file_service
    meta = file_service.get_file_meta(file_id) or {}
    file_repo.upsert_meta(file_id, {
        "name": meta.get("name", ""),
        "project_id": project_id,
        "module_id": module_id,
    })
    return ok({"success": True, "fileId": file_id})


@router.get("/attachment/check-update")
def attachment_check_update():
    """检查附件是否更新。"""
    return ok({"hasUpdate": False})


@router.post("/attachment/upload/temp/file")
def attachment_upload_temp_file(request: Request):
    """富文本所需资源上传。"""
    return ok({
        "fileId": str(uuid.uuid4()),
    })


@router.get("/attachment/download/file")
def attachment_download_file(request: Request = None):
    """富文本资源详情预览压缩图。

    前端 PreviewEditorImageUrl = '/attachment/download/file' 用于回显富文本图片。
    从 query 参数中取 fileId，返回文件二进制内容。
    """
    if request is None:
        return ok(None)
    file_id = request.query_params.get("fileId", "") or request.query_params.get("id", "")
    if not file_id:
        return ok(None)
    from app.domain.file.application.file_app_service import file_service
    fname = file_service.find_upload_file(file_id)
    if not fname:
        return ok(None)
    from fastapi.responses import FileResponse
    return FileResponse(file_service.resolve_path(fname))


# ════════════════════════════════════════════════════════════
# 缺失接口补充 - 缺陷同步与导出
# ════════════════════════════════════════════════════════════

