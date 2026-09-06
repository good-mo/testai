# app/routers/project_compat_file.py
"""project_compat 拆分：项目文件管理 /project/file*（P4 超大文件拆分）。

自 app/routers/project_compat.py 按业务域搬移，纯路由搬移、行为不变，
响应沿用统一 ok()/fail()/_paginate() 与 read_body() 辅助函数。
"""

import uuid
from typing import Dict

from fastapi import APIRouter, Request

from app.core.response import ok
from app.logging_config import get_logger
from app.models.file import (
    FileBatchDeleteBody,
    FileBatchMoveBody,
    FileDownloadBody,
    FileModuleCountBody,
    FileModuleMoveBody,
    FileModuleUpdateBody,
)

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-project-file"])


"""project_compat 拆分：file 域路由（P4 超大文件拆分）。

自 app/routers/project_compat.py 按域搬移，纯搬移、行为不变。
"""


@router.get("/project/file/type")
def project_file_type_get():
    """项目文件类型（GET兼容）。"""
    return ok([
        "FILE", "IMAGE", "JAR", "XLS", "XLSX", "CSV",
        "DOC", "DOCX", "PDF", "TXT", "MD", "JSON", "YAML", "CONFIG",
    ])

@router.get("/project/file/repository/pull-file")
def project_file_repository_pull_file_get():
    """项目文件仓库拉取（GET兼容）。"""
    return ok()

@router.get("/project/file/association/list")
def project_file_association_list_get():
    """项目文件关联列表（GET兼容）。"""
    return ok([])

@router.post("/project/file/download")
async def project_file_download_post(body: FileDownloadBody):
    """项目文件下载（POST兼容）。"""
    file_id = body.id or body.fileId
    return ok({"fileId": file_id})

@router.post("/project/file/module/count")
async def project_file_module_count_post(body: FileModuleCountBody):
    """项目文件模块统计（POST）。

    返回各文件模块下的文件数量，以及 my/all 快捷入口的计数。
    结构：{"all": 总文件数, "my": 当前用户上传数, "<moduleId>": 各模块文件数}
    """
    combine = body.combine or {}
    create_user = combine.get("createUser", "")
    storage = combine.get("storage", "")

    # 复用统一文件服务扫描真实上传目录。此前这里手写 upload 路径时多算了一层
    # dirname（__file__ 位于 app/routers/ 下，比 app/services/ 更深一层），拼出了
    # 不存在的 /uploads，导致 root/all/my 恒为 0、界面看不到统计。
    try:
        from app.services.file_service import file_service

        files = file_service.list_project_files(
            storage=storage,
            create_user=create_user,
            combine=combine,
        )
    except Exception:
        files = []

    all_count = len(files)
    # my 语义：指定 createUser 时仅统计该用户上传的文件，否则退化为全部
    my_count = 0
    if create_user:
        for f in files:
            if (f.get("createUser") or "") == create_user:
                my_count += 1
    else:
        my_count = all_count

    # 文件归属模块聚合：未归属到任何模块的文件默认计入 root（root 语义 = 全部文件）
    direct: Dict[str, int] = {}
    for f in files:
        mid = f.get("moduleId") or "root"
        direct[mid] = direct.get(mid, 0) + 1

    counts: Dict[str, int] = {}
    try:
        from app.services.apitest_service import apitest_service

        file_modules = apitest_service.list_modules("file")

        def _file_total(mid: str) -> int:
            """模块自身文件 + 其全部子孙模块文件的递归总数。"""
            total = direct.get(mid, 0)
            for m in file_modules:
                if (m.get("parent_id") or "root") == mid:
                    total += _file_total(m.get("id", ""))
            return total

        for m in file_modules:
            mid = m.get("id", "")
            counts[mid] = _file_total(mid)
    except Exception:
        pass

    counts["root"] = all_count
    counts["my"] = my_count
    counts["all"] = all_count
    return ok(counts)


@router.get("/project/file-module/delete")
def project_file_module_delete(request: Request):
    """项目文件模块删除。"""
    try:
        # 尝试从查询参数读取 id
        from urllib.parse import parse_qs

        from app.services.apitest_service import apitest_service
        query = request.url.query
        params = parse_qs(query)
        mod_id = params.get("id", [""])[0]
        if mod_id:
            deleted = apitest_service.delete_module(mod_id)
            return ok({"deleted": deleted})
    except Exception:
        pass
    return ok({"deleted": False})

@router.post("/project/file/re-upload")
def project_file_re_upload():
    """重新上传项目文件。"""
    return ok({"id": str(uuid.uuid4())})

@router.post("/project/file/update")
def project_file_update():
    """更新项目文件。"""
    return ok()

@router.post("/project/file/batch-delete")
async def project_file_batch_delete(body: FileBatchDeleteBody):
    """批量删除项目文件。"""
    from app.services.file_service import file_service as _fs
    # 收集待删除文件 id
    file_ids = []
    select_ids = body.selectIds or []
    if isinstance(select_ids, list):
        file_ids = [str(i) for i in select_ids]
    # 若 selectAll 为 true，则结合条件过滤
    condition = body.condition or {}
    if body.selectAll:
        files = _fs.list_project_files(
            keyword=condition.get("keyword", ""),
            module_ids=body.moduleIds or [],
            file_type=body.fileType,
            storage=(condition.get("combine") or {}).get("storage", ""),
            create_user=(condition.get("combine") or {}).get("createUser", ""),
            project_id=body.projectId,
        )
        exclude = set(body.excludeIds)
        for f in files:
            if f["id"] not in exclude:
                file_ids.append(f["id"])
    if file_ids:
        _fs.delete_files_batch(file_ids)
    return ok({"deleted": len(file_ids)})

@router.get("/project/file/get")
def project_file_get(id: str = ""):
    """获取项目文件详情。"""
    from app.services.file_service import file_service as _fs
    meta = _fs.get_file_meta(id)
    if not meta:
        return ok({})
    # 合并 DB 元数据（经 Service 层，避免路由直连 Repo）
    db_meta = _fs.get_meta(id) or {}
    return ok({
        "id": id,
        "name": meta["name"],
        "originalName": meta["name"],
        "path": meta["path"],
        "size": meta["size"],
        "fileType": meta["fileType"],
        "type": meta["fileType"],
        "enable": bool(db_meta.get("enable", meta["fileType"] != "JAR")),
        "tags": [],
        "description": db_meta.get("description", ""),
        "updateUser": db_meta.get("update_user", ""),
        "createUser": db_meta.get("create_user", ""),
        "updateTime": int(db_meta.get("updated_at", 0) or 0),
        "createTime": int(db_meta.get("created_at", 0) or 0),
        "previewSrc": "",
        "storage": db_meta.get("storage", "minio"),
        "projectId": db_meta.get("project_id", ""),
        "moduleName": "",
        "moduleId": db_meta.get("module_id", "root"),
    })

@router.post("/project/file/batch-move")
async def project_file_batch_move(body: FileBatchMoveBody):
    """批量移动项目文件。"""
    from app.services.file_service import file_service as _fs
    file_ids = []
    select_ids = body.selectIds or []
    if isinstance(select_ids, list):
        file_ids = [str(i) for i in select_ids]
    move_module_id = body.moveModuleId
    if move_module_id and file_ids:
        for fid in file_ids:
            meta = _fs.get_meta(fid)
            if meta:
                _fs.update_meta(fid, {
                    "name": meta.get("name", ""),
                    "project_id": meta.get("project_id", ""),
                    "module_id": move_module_id,
                    "create_user": meta.get("create_user", ""),
                    "update_user": meta.get("update_user", ""),
                    "storage": meta.get("storage", "minio"),
                    "file_type": meta.get("file_type", "FILE"),
                    "enable": meta.get("enable", 1),
                    "size": meta.get("size", 0),
                })
    return ok({"moved": len(file_ids)})

@router.post("/project/file/batch-download")
def project_file_batch_download():
    """批量下载项目文件。"""
    return ok({"id": str(uuid.uuid4())})

@router.get("/project/file/download")
def project_file_download(file_id: str = ""):
    """下载项目文件。"""
    return ok({"fileId": file_id})

@router.post("/project/file/jar-file-status")
def project_file_jar_file_status():
    """JAR 文件状态。"""
    return ok([])

@router.post("/project/file-module/move")
async def project_file_module_move(body: FileModuleMoveBody):
    """移动文件模块。"""
    drag_node_id = body.dragNodeId
    drop_node_id = body.dropNodeId
    drop_position = body.dropPosition
    try:
        from app.services.apitest_service import apitest_service
        result = apitest_service.move_module(drag_node_id, drop_node_id, drop_position)
        return ok({"success": result})
    except Exception:
        pass
    return ok({"success": False})

@router.post("/project/file-module/update")
async def project_file_module_update(body: FileModuleUpdateBody):
    """更新文件模块。"""
    mod_id = body.id
    name = body.name
    try:
        from app.services.apitest_service import apitest_service
        updated = apitest_service.update_module(mod_id, name)
        return ok({"updated": updated})
    except Exception:
        pass
    return ok({"updated": False})

@router.post("/project/file/repository/add-repository")
def project_file_repository_add():
    """添加文件存储库。"""
    return ok({"id": str(uuid.uuid4())})

@router.post("/project/file/repository/update-repository")
def project_file_repository_update():
    """更新文件存储库。"""
    return ok()

@router.post("/project/file/repository/connect")
def project_file_repository_connect():
    """连接文件存储库。"""
    return ok()

@router.get("/project/file/repository/info")
def project_file_repository_info(id: str = ""):
    """存储库信息。"""
    return ok({})

@router.get("/project/file/repository/list")
def project_file_repository_list(project_id: str = ""):
    """存储库列表。"""
    return ok([])

@router.get("/project/file/repository/file-type")
def project_file_repository_file_type(project_id: str = ""):
    """存储库文件类型。"""
    return ok([])

@router.post("/project/file/repository/add-file")
def project_file_repository_add_file():
    """存储库添加文件。"""
    return ok({"id": str(uuid.uuid4())})

@router.post("/project/file/repository/pull-file")
def project_file_repository_pull_file():
    """拉取存储库文件。"""
    return ok()

@router.post("/project/file/association/list")
def project_file_association_list():
    """文件关联列表。"""
    return ok([])

@router.post("/project/file/association/delete")
def project_file_association_delete():
    """删除文件关联。"""
    return ok()

@router.post("/project/file/association/upgrade")
def project_file_association_upgrade():
    """升级文件关联。"""
    return ok()

@router.get("/project/file/file-version")
def project_file_file_version(file_id: str = ""):
    """文件历史版本。"""
    return ok([])

@router.get("/project/file/module/count")
def project_file_module_count(project_id: str = ""):
    """文件模块数量（GET 兼容）。"""
    from app.services.file_service import file_service as _fs
    counts: Dict[str, int] = _fs.count_files_by_module(project_id=project_id)
    return ok(counts)

@router.get("/project/file/association/upgrade/{file_id}")
@router.post("/project/file/association/upgrade/{file_id}")
def project_file_association_upgrade_path(file_id: str):
    """升级项目文件关联（带路径参数）。"""
    return ok({"id": file_id, "upgraded": True})

@router.get("/project/file/jar-file-status/{file_id}/{project_id}")
@router.post("/project/file/jar-file-status/{file_id}/{project_id}")
def project_file_jar_status_path(file_id: str, project_id: str):
    """获取项目 JAR 文件状态（带路径参数）。"""
    return ok({"file_id": file_id, "project_id": project_id})

@router.get("/project/file-module/delete/{id}")
@router.post("/project/file-module/delete/{id}")
def project_file_module_delete_path(id: str):
    """/project/file-module/delete 带路径参数（前端 RESTful 调用兼容）。"""
    from app.services.apitest_service import apitest_service
    try:
        apitest_service.delete_module(id)
    except Exception:
        pass
    return ok({"id": id, "deleted": True})
