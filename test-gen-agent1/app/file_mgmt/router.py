# app/file_mgmt/router.py
"""文件管理 API 路由：上传、下载、预览、附件管理。

四层重构：URL/参数/响应编排保留在本层，文件系统领域逻辑已下沉到
`app.services.file_service.FileService`（service 层）。
"""
import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from app.core.response import fail, ok, read_body
from app.models.file import (
    AttachmentPageBody,
    FileModuleAddBody,
    FilePageBody,
    IdBody,
)
from app.services.file_service import file_service

router = APIRouter(tags=["file-management"])


def _original_name(fname: str) -> str:
    """从上传文件名还原原始文件名（去掉 UUID 前缀）。"""
    return fname.split("_", 1)[1] if "_" in fname else fname


# ── 项目文件管理 ───────────────────────────────────────
@router.post("/project/file/upload")
async def project_file_upload(request: Request):
    """上传项目文件。

    从 multipart 的 ``request`` 字段中读取 projectId/moduleId/enable 等
    元信息并随文件一起落库，供后续按项目 / 模块 / 用户过滤查询。
    """
    # 支持 multipart/form-data 和 JSON 两种方式
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        # 解析 request 元数据字段（JSON 字符串）
        project_id = ""
        module_id = "root"
        enable = True
        try:
            request_field = form.get("request")
            if request_field is not None:
                if hasattr(request_field, "read"):
                    raw = await request_field.read()
                    req_data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
                else:
                    req_data = json.loads(request_field)
                project_id = req_data.get("projectId", "")
                module_id = req_data.get("moduleId", "root")
                enable = bool(req_data.get("enable", True))
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
        if file and hasattr(file, "filename"):
            content = await file.read()
            # 从会话中取当前用户，作为 create_user
            current_user = getattr(request.state, "user", None) or {}
            create_user = str(current_user.get("id", "") or current_user.get("user_id", "") or "")
            data = file_service.save_file(
                getattr(file, "filename", ""), content,
                project_id=project_id, module_id=module_id,
                create_user=create_user,
                enable=enable,
            )
            return ok(data)
        return fail("未找到文件", code=400)
    else:
        body = await read_body(request)
        return ok({
            "id": str(uuid.uuid4()),
            "name": body.get("name", ""),
            "size": 0,
        })


@router.post("/project/file/page")
def project_file_page(payload: FilePageBody):
    """分页查询项目文件列表。"""
    files = file_service.list_project_files(
        keyword=payload.keyword,
        module_ids=payload.moduleIds,
        file_type=payload.fileType,
        storage=payload.combine.get("storage", ""),
        create_user=payload.combine.get("createUser", ""),
        project_id=payload.projectId,
        combine=payload.combine,
    )
    page_size = payload.pageSize
    current = payload.current
    start = (current - 1) * page_size
    page_items = files[start:start + page_size]
    return ok({
        "list": page_items,
        "total": len(files),
        "pageSize": page_size,
        "current": current,
    })


@router.post("/project/file/delete")
def project_file_delete(payload: IdBody):
    """删除项目文件（兼容单删与批量删除结构）。"""
    # 兼容批量结构: { selectIds: [...], selectAll, excludeIds, ... }
    if hasattr(payload, "selectIds") and payload.selectIds:
        ids = [str(i) for i in payload.selectIds]
        file_service.delete_files_batch(ids)
        return ok({"deleted": len(ids)})
    file_service.delete_file(payload.id)
    return ok()


@router.get("/project/file/download/{file_id}")
def project_file_download(file_id: str):
    """下载项目文件。"""
    fname = file_service.find_upload_file(file_id)
    if fname:
        return FileResponse(
            file_service.resolve_path(fname), filename=_original_name(fname),
        )
    return fail("文件不存在", code=404)


@router.get("/project/file/get/{file_id}")
def project_file_get(file_id: str):
    """获取文件详情（含项目/模块归属元数据）。"""
    meta = file_service.get_file_meta(file_id)
    if meta:
        db_meta = file_service.get_meta(file_id) or {}
        return ok({
            "id": meta["id"],
            "name": meta["name"],
            "originalName": meta["name"],
            "path": meta["path"],
            "size": meta["size"],
            "type": meta["type"],
            "fileType": meta["fileType"],
            "projectId": db_meta.get("project_id", ""),
            "moduleId": db_meta.get("module_id", "root"),
            "createUser": db_meta.get("create_user", ""),
            "updateUser": db_meta.get("update_user", ""),
            "storage": db_meta.get("storage", "minio"),
            "enable": bool(db_meta.get("enable", meta["fileType"] != "JAR")),
            "description": db_meta.get("description", ""),
        })
    return fail("文件不存在", code=404)


@router.post("/project/file/type")
def project_file_type():
    """获取文件类型集合。"""
    return ok([
        "FILE", "IMAGE", "JAR", "XLS", "XLSX", "CSV",
        "DOC", "DOCX", "PDF", "TXT", "MD", "JSON", "YAML",
    ])


@router.get("/project/file-module/tree")
def project_file_module_tree(request: Request):
    """获取文件模块树。"""
    # 支持查询参数 ?projectId=xxx 过滤
    project_id = request.query_params.get("projectId", "")
    return ok(file_service.build_module_tree(project_id=project_id))


@router.post("/project/file-module/add")
def project_file_module_add(payload: FileModuleAddBody):
    """添加文件模块。"""
    module = file_service.add_module(
        name=payload.name,
        parent_id=payload.parentId,
        project_id=payload.projectId,
    )
    return ok(module)


@router.post("/project/file-module/delete")
def project_file_module_delete(payload: IdBody):
    """删除文件模块。"""
    deleted = file_service.delete_module(payload.id)
    return ok(deleted)


# ── 文件预览 ─────────────────────────────────────────
@router.get("/file/preview/original")
def file_preview_original(request: Request = None):
    """预览原图（从 query 参数中取 fileId，返回文件二进制内容）。"""
    if request is None:
        return ok(None)
    file_id = request.query_params.get("fileId", "") or request.query_params.get("id", "")
    if not file_id:
        return ok(None)
    from app.services.file_service import file_service
    fname = file_service.find_upload_file(file_id)
    if not fname:
        return ok(None)
    from fastapi.responses import FileResponse
    return FileResponse(file_service.resolve_path(fname))


@router.get("/file/preview/compressed")
def file_preview_compressed(request: Request = None):
    """预览压缩图（从 query 参数中取 fileId，返回文件二进制内容）。"""
    if request is None:
        return ok(None)
    file_id = request.query_params.get("fileId", "") or request.query_params.get("id", "")
    if not file_id:
        return ok(None)
    from app.services.file_service import file_service
    fname = file_service.find_upload_file(file_id)
    if not fname:
        return ok(None)
    from fastapi.responses import FileResponse
    return FileResponse(file_service.resolve_path(fname))


# ── 附件管理 ─────────────────────────────────────────
@router.post("/attachment/upload")
async def attachment_upload(request: Request):
    """上传附件。"""
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if file and hasattr(file, "filename"):
            content = await file.read()
            data = file_service.save_file(getattr(file, "filename", ""), content)
            return ok({
                "id": data["id"],
                "name": data["name"],
                "size": data["size"],
            })
    return fail("未找到文件", code=400)


@router.post("/attachment/page")
def attachment_page(payload: AttachmentPageBody):
    """附件分页列表。"""
    files = file_service._scan_attachments()
    page_size = payload.pageSize
    current = payload.current
    start = (current - 1) * page_size
    return ok({
        "list": files[start:start + page_size],
        "total": len(files),
    })


@router.post("/attachment/delete")
def attachment_delete(payload: IdBody):
    """删除附件。"""
    file_service.delete_file(payload.id)
    return ok()


@router.get("/attachment/download/{file_id}")
def attachment_download(file_id: str):
    """下载附件。"""
    fname = file_service.find_upload_file(file_id)
    if fname:
        return FileResponse(
            file_service.resolve_path(fname), filename=_original_name(fname),
        )
    return fail("文件不存在", code=404)


@router.get("/attachment/list/{resource_id}")
def attachment_list(resource_id: str):
    """获取资源附件列表。"""
    return ok(file_service.list_attachment_meta())


# ── 缺陷附件 ─────────────────────────────────────────
@router.post("/bug/attachment/upload")
async def bug_attachment_upload(request: Request):
    """上传缺陷附件。"""
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if file and hasattr(file, "filename"):
            filename = file.filename
            content = await file.read()
            data = file_service.save_file(filename, content)
            return ok({
                "id": data["id"],
                "name": data["name"],
                "size": data["size"],
            })
    return fail("未找到文件", code=400)


@router.get("/bug/attachment/list/{bug_id}")
def bug_attachment_list(bug_id: str):
    """获取缺陷附件列表。"""
    return ok([])


@router.post("/bug/attachment/delete")
def bug_attachment_delete(request: Request):
    """删除缺陷附件。"""
    return ok(None)


@router.get("/bug/attachment/download/{file_id}")
def bug_attachment_download(file_id: str):
    """下载缺陷附件。"""
    fname = file_service.find_upload_file(file_id)
    if fname:
        return FileResponse(
            file_service.resolve_path(fname), filename=_original_name(fname),
        )
    return fail("文件不存在", code=404)


@router.post("/bug/attachment/upload/md/file")
async def bug_attachment_upload_md(request: Request):
    """富文本编辑器上传图片。"""
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if file and hasattr(file, "filename"):
            filename = file.filename
            content = await file.read()
            data = file_service.save_file(filename, content)
            return ok({
                "id": data["id"],
                "name": data["name"],
                "url": f"/attachment/download/{data['id']}",
            })
    return fail("未找到文件", code=400)


# ── 文件历史版本 ─────────────────────────────────────
@router.get("/project/file/file-version/{file_id}")
def project_file_version(file_id: str):
    """获取文件历史版本列表。"""
    return ok([])
