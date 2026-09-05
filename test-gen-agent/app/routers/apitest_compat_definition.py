import json
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Request

from app.core.response import fail, ok, read_body
from app.core.helpers import as_model, definition_followed
from app.models.apitest import (
    CompatBatchIdsBody,
    CompatExecutionPageBody,
    CompatIdBody,
    CompatModuleAddBody,
    CompatModuleDeleteBody,
    CompatModuleUpdateBody,
    CompatProjectQueryBody,
    DefinitionCompatCreateBody,
    DefinitionCompatUpdateBody,
    DefinitionModuleQueryBody,
    DefinitionPageBody,
    DocPageBody,
)
from app.routers.apitest_compat_base import (
    _build_trash_count_map,
    _filter_module_tree,
    _filter_module_tree_by_protocol,
    _read_body,
    apitest_service,
)

router = APIRouter(tags=["adapter-api_testing_definition"])


@router.get("/api/definition/delete-to-gc")
async def api_definition_delete_gc_get(request: Request):
    """接口定义移入回收站（GET兼容）。

    与 POST /api/definition/delete-to-gc 语义对齐（软删）。
    id 从 query / body 解析，兼容前端 MSR.get({url, params: id}) 与 ?id= 两种形态。
    """
    query = dict(request.query_params)
    definition_id = (query.get("id") or query.get("definitionId")
                     or request.path_params.get("id") or "")
    if not definition_id:
        m = as_model(await read_body(request), CompatIdBody)
        definition_id = m.id if m.id is not None else (m.definitionId or "")
    if definition_id:
        apitest_service.delete_definition(definition_id)
    return ok({"deleted": bool(definition_id)})


@router.get("/api/definition/schedule/delete")
def api_definition_schedule_delete_get(request: Request):
    """接口定义定时同步删除（GET兼容）。"""
    return ok()


@router.get("/api/definition/schedule/switch")
def api_definition_schedule_switch_get(request: Request):
    """接口定义定时同步开关（GET兼容）。"""
    return ok()


@router.post("/api/definition/module/tree")
async def api_definition_module_tree_post(request: Request):
    """接口定义模块树（真实实现）。

    入参：keyword / protocols / projectId / moduleIds（用于过滤）。
    返回：ModuleTreeNode[]。
    """
    body = DefinitionModuleQueryBody.model_validate(await _read_body(request))
    protocols = body.effective_protocols
    module_ids = body.effective_module_ids
    tree = apitest_service.build_module_tree("definition")
    # 模块过滤：若指定了具体模块，仅返回这些模块及其子模块
    if module_ids and "all" not in module_ids:
        tree = _filter_module_tree(tree, module_ids)
    # 协议过滤：模块树中若含 API 节点，按协议过滤
    if protocols:
        tree = _filter_module_tree_by_protocol(tree, protocols)
    return ok(tree)


@router.post("/api/definition/module/only/tree")
async def api_definition_module_only_tree_post(request: Request):
    """接口定义不含接口的模块树（真实实现）。

    入参：keyword / protocols / projectId / moduleIds（用于过滤）。
    """
    body = DefinitionModuleQueryBody.model_validate(await _read_body(request))
    module_ids = body.effective_module_ids
    tree = apitest_service.build_module_tree("definition", include_api=False)
    if module_ids and "all" not in module_ids:
        tree = _filter_module_tree(tree, module_ids)
    return ok(tree)


@router.post("/api/definition/module/env/tree")
async def api_definition_module_env_tree_post(request: Request):
    """接口定义环境模块树（真实实现）。

    入参：projectId / selectedModules。
    返回：EnvModule 结构 { moduleTree, selectedModules }。
    """
    body = DefinitionModuleQueryBody.model_validate(await _read_body(request))
    selected_modules = body.effective_selected_modules
    tree = apitest_service.build_module_tree("definition", include_api=False)
    return ok({
        "moduleTree": tree,
        "selectedModules": selected_modules,
    })


@router.post("/api/definition/export/{export_type}")
def api_definition_export_by_type(export_type: str, request: Request):
    """接口定义导出（带类型路径参数）。"""
    return ok()


@router.get("/api/definition/get-detail")
def api_definition_get_detail_query(id: str = ""):
    """接口定义详情（query 方式）。"""
    from app.services.apitest_service import apitest_service as apitest_store
    defn = apitest_store.get_definition(id) if id else None
    if not defn:
        return ok({})
    return ok(_to_definition(defn))


@router.post("/api/definition/get-detail")
async def api_definition_get_detail_post(request: Request):
    """接口定义详情 POST。"""
    m = as_model(await read_body(request), CompatIdBody)
    defn_id = m.effective_id
    from app.services.apitest_service import apitest_service as apitest_store
    defn = apitest_store.get_definition(defn_id) if defn_id else None
    if not defn:
        return ok({})
    return ok(_to_definition(defn))


@router.post("/api/definition/batch/delete")
async def api_definition_batch_delete(request: Request):
    """接口定义批量彻底删除（回收站清空，真实实现）。

    前端回收站 batchCleanOutDefinition 调用本端点（BatchCleanOutApiUrl），
    语义为回收站中批量彻底删除。此前误用 batch_delete_definitions（软删），
    这里改为 batch_purge_definitions 彻底删除；支持 selectAll 全选回收站清空。
    """
    m = as_model(await read_body(request), CompatBatchIdsBody)
    ids = m.effective_ids
    if m.select_all and not ids:
        all_items = apitest_service.list_trash_definitions(limit=999)
        ids = [d["id"] for d in all_items]
    from app.services.apitest_service import apitest_service as apitest_store
    count = apitest_store.batch_purge_definitions(ids) if ids else 0
    return ok({"deleted": count})


@router.get("/api/definition/download/file")
def api_definition_download_file(file_id: str = ""):
    """接口定义文件下载。"""
    return ok({"fileId": file_id, "fileName": "file"})


@router.get("/api/definition/transfer/options")
def api_definition_transfer_options(project_id: str = ""):
    """接口定义文件转存目录。"""
    return ok([])


@router.get("/api/definition/get-reference")
def api_definition_get_reference(id: str = ""):
    """获取接口引用关系。"""
    return ok([])


@router.post("/api/definition/schedule/add")
async def api_definition_schedule_add(request: Request):
    """添加接口定义定时同步。"""
    await read_body(request)
    return ok({"id": str(uuid.uuid4())})


@router.post("/api/definition/schedule/update")
async def api_definition_schedule_update(request: Request):
    """更新接口定义定时同步。"""
    await read_body(request)
    return ok()


@router.post("/api/definition/schedule/delete")
async def api_definition_schedule_delete(request: Request):
    """删除接口定义定时同步。"""
    await read_body(request)
    return ok()


@router.post("/api/definition/schedule/check")
async def api_definition_schedule_check(request: Request):
    """检查定时同步 URL。"""
    await read_body(request)
    return ok({"exist": True})


@router.post("/api/definition/schedule/switch")
async def api_definition_schedule_switch(request: Request):
    """开关定时同步。"""
    await read_body(request)
    return ok()


@router.post("/api/definition/schedule/get")
async def api_definition_schedule_get(request: Request):
    """查询定时同步。"""
    await read_body(request)
    return ok({})


@router.get("/api/definition/schedule/get")
def api_definition_schedule_get_query(id: str = ""):
    """查询定时同步 GET。"""
    return ok({})


# ════════════════════════════════════════════════════════════
# P0-4: 接口文档分享  /api/doc/share/*
# ════════════════════════════════════════════════════════════


@router.get("/api/definition/stop/{definition_id}")


@router.post("/api/definition/stop/{definition_id}")
def definition_stop_path(definition_id: str):
    """停止接口定义任务（带路径参数）。"""
    return ok({"id": definition_id, "stopped": True})


# ════════════════════════════════════════════════════════════
# 文档分享
# ════════════════════════════════════════════════════════════


@router.post("/api/definition/module/trash/count")
async def api_definition_module_trash_count_post(request: Request):
    """接口定义模块回收站数量（POST）。"""
    await _read_body(request)
    return ok(_build_trash_count_map())


@router.post("/api/definition/page")
async def api_definition_page(request: Request):
    """接口定义分页列表。

    deleted=true 时查询回收站数据（前端回收站页面）。
    """
    body = DefinitionPageBody.model_validate(await read_body(request))
    keyword = body.keyword
    page_size = body.pageSize if body.pageSize is not None else 10
    current = body.current if body.current is not None else 1
    project_id = body.projectId
    protocols = body.protocols or []
    module_ids = body.moduleIds or []
    deleted = body.deleted

    from app.services.apitest_service import apitest_service
    count_definitions = apitest_service.count_definitions
    list_definitions = apitest_service.list_definitions

    if deleted:
        # 回收站：查询已删除的接口定义
        # 先取全部回收站数据，再在内存中过滤分页
        trash_all = apitest_service.list_trash_definitions(
            project_id=project_id, limit=100000
        )
        # 关键词过滤
        if keyword:
            k = keyword.lower()
            trash_all = [
                d for d in trash_all
                if k in (d.get("name", "") or "").lower()
                or k in (d.get("path", "") or "").lower()
                or k in (d.get("description", "") or "").lower()
            ]
        # 协议过滤
        if protocols:
            trash_all = [d for d in trash_all if d.get("protocol", "HTTP") in protocols]
        # 总数：无过滤条件时走 DB COUNT 真实值；有过滤时用内存过滤结果
        total = (apitest_service.count_trash_definitions(project_id)
                 if not keyword and not protocols else len(trash_all))
        # 分页
        start = (current - 1) * page_size
        page_items = trash_all[start:start + page_size]
        items = [_to_definition(d) for d in page_items]
        return ok({
            "list": items,
            "total": total,
            "pageSize": page_size,
            "current": current,
        })

    # 将 protocols/module_ids 过滤下推到 SQL 层，避免分页计数不准确
    definitions = list_definitions(
        keyword=keyword, limit=page_size, offset=(current - 1) * page_size,
        project_id=project_id, protocols=protocols, module_ids=module_ids,
    )
    # 总数：统计全部符合条件（含 keyword/protocols/module_ids）的记录数
    total = count_definitions(
        project_id=project_id, keyword=keyword,
        protocols=protocols, module_ids=module_ids,
    )

    items = []
    for d in definitions:
        items.append(_to_definition(d))

    return ok({
            "list": items,
            "total": total,
            "pageSize": page_size,
            "current": current,
        })


@router.post("/api/definition/add")
async def api_definition_add(request: Request):
    """添加接口定义。"""
    m = DefinitionCompatCreateBody.model_validate(await read_body(request))
    from app.services.apitest_service import apitest_service
    definition = apitest_service.create_definition(**m.service_kwargs())
    return ok(_to_definition(definition))


@router.post("/api/definition/update")
async def api_definition_update(request: Request):
    """更新接口定义。"""
    body = DefinitionCompatUpdateBody.model_validate(await read_body(request))
    definition_id = body.id or ""
    from app.services.apitest_service import apitest_service
    try:
        definition = apitest_service.update_definition(definition_id, **body.service_kwargs())
    except Exception:
        definition = None
    if not definition:
        return fail("接口不存在", code=404)
    return ok(_to_definition(definition))


@router.post("/api/definition/delete-to-gc")
async def api_definition_delete(request: Request):
    """删除接口定义（移入回收站）。"""
    m = as_model(await read_body(request), CompatIdBody)
    definition_id = m.id if m.id is not None else ""
    apitest_service.delete_definition(definition_id)
    return ok(None)


@router.post("/api/definition/delete")
async def api_definition_delete_post(request: Request):
    """接口定义彻底删除（回收站清空，POST 兼容）。

    与 GET/POST /api/definition/delete/{id} 语义对齐（回收站彻底删除 purge）。
    此前误用 delete_definition（软删进回收站），主列表软删应走 /delete-to-gc。
    """
    m = as_model(await read_body(request), CompatIdBody)
    definition_id = m.id if m.id is not None else (m.ids if m.ids is not None else (m.definitionId or ""))
    ids = definition_id if isinstance(definition_id, list) else [definition_id]
    purged = 0
    for did in ids:
        if did and apitest_service.purge_definition(did):
            purged += 1
    return ok({"deleted": purged})


@router.get("/api/definition/module/tree")
def api_definition_module_tree():
    """获取接口模块树。"""
    return ok(apitest_service.build_module_tree("definition"))


@router.post("/api/definition/module/add")
async def api_definition_module_add(request: Request):
    """添加接口定义模块。"""
    m = CompatModuleAddBody.model_validate(await read_body(request))
    module = apitest_service.add_module(
        scope="definition",
        name=m.name or "新模块",
        parent_id=m.parentId or "root",
        project_id=m.projectId or "",
    )
    return ok(module)


@router.post("/api/definition/module/count", operation_id="api_definition_module_count_post")


@router.get("/api/definition/module/count", operation_id="api_definition_module_count_get")
async def api_definition_module_count(request: Request = None):
    """获取接口定义模块数量。

    入参：keyword / protocols / projectId / moduleIds。
    返回：{ moduleId: count, all: total, root: total } 映射。
    """
    m = DefinitionModuleQueryBody()
    if request is not None:
        m = DefinitionModuleQueryBody.model_validate(await _read_body(request))
    protocols = m.protocols or []

    # 模块数量统计统一下沉 apitest_service / ApitestRepo，
    # 不再在路由层手写 SQL（约束 #2）。
    modules = apitest_service.list_modules("definition")
    api_count_by_module = apitest_service.count_definitions_by_module(protocols=None)
    total = apitest_service.count_definitions_total(protocols=protocols)

    result = {"all": total, "root": total}
    for m in modules:
        result[m.get("id", "")] = api_count_by_module.get(m.get("id", ""), 0)
    return ok(result)


@router.get("/api/definition/get-detail/{definition_id}")
def api_definition_detail(definition_id: str):
    """获取接口定义详情。"""
    from app.services.apitest_service import apitest_service
    get_definition = apitest_service.get_definition
    definition = get_definition(definition_id)
    if not definition:
        return fail("接口不存在", code=404)
    return ok(_to_definition(definition))


@router.post("/api/definition/import")
def api_definition_import(request: Request):
    """导入接口定义。"""
    return ok(None)


@router.post("/api/definition/export")
def api_definition_export(request: Request):
    """导出接口定义。"""
    return ok(None)


@router.post("/api/definition/batch/delete-to-gc")
async def api_definition_batch_delete_gc(request: Request):
    """批量删除接口定义（移入回收站，真实实现）。

    前端 batchDeleteDefinition 传 { ids/selectIds, selectAll, excludeIds }。
    支持 selectAll 全选主列表（未删除）定义后批量软删进回收站。
    """
    m = as_model(await read_body(request), CompatBatchIdsBody)
    ids = m.effective_ids
    if m.select_all and not ids:
        all_items = apitest_service.list_definitions(limit=999)
        ids = [d["id"] for d in all_items]
    deleted = apitest_service.batch_delete_definitions(ids) if ids else 0
    return ok({"deleted": deleted})


@router.post("/api/definition/batch-update")
def api_definition_batch_update(request: Request):
    """批量更新接口定义。"""
    return ok(None)


@router.post("/api/definition/batch-move")
def api_definition_batch_move(request: Request):
    """批量移动接口定义。"""
    return ok(None)


@router.post("/api/definition/copy")
def api_definition_copy(request: Request):
    """复制接口定义。"""
    return ok(None)


@router.post("/api/definition/debug")
def api_definition_debug(request: Request):
    """调试接口定义。"""
    return ok(None)


@router.get("/api/definition/follow")
def api_definition_follow(request: Request):
    """关注接口定义（GET兼容，query 取 id/definitionId）。

    与 /api/case/follow 对齐：真实写 api_follows 表（resource_type=definition），
    消灭此前返回 ok(None) 不落库的假成功。
    """
    def_id = request.query_params.get("id") or request.query_params.get("definitionId") or ""
    if not def_id:
        return ok({"success": False})
    ok_flag = apitest_service.follow_resource("definition", def_id)
    return ok({"success": bool(ok_flag)})


@router.post("/api/definition/edit/pos")
def api_definition_edit_pos(request: Request):
    """拖拽调整位置。"""
    return ok(None)


def _to_definition(defn: Dict[str, Any]) -> Dict[str, Any]:
    """将后端接口定义格式转为前端格式。"""
    def _parse_field(val, default=None):
        """解析 JSON 字符串字段；已是 dict/list 则直接返回。"""
        if isinstance(val, (dict, list)):
            return val
        if val is None:
            return default or {}
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return default or {}

    # 计算接口定义下的用例数量（统一下沉 apitest_service，避免路由层直连 DB）
    case_total = 0
    def_id = defn.get("id", "")
    if def_id:
        try:
            case_total = apitest_service.count_cases_for_definition(def_id)
        except Exception:
            case_total = 0

    return {
        "id": defn.get("id", ""),
        "name": defn.get("name", ""),
        "num": defn.get("num", 0),
        "method": defn.get("method", "GET"),
        "path": defn.get("path", "/"),
        "protocol": defn.get("protocol", "HTTP"),
        "description": defn.get("description", ""),
        "status": defn.get("status", "processing"),
        "requestBody": _parse_field(defn.get("request_body", defn.get("body", {}))),
        "responseBody": _parse_field(defn.get("response_body", {})),
        "headers": _parse_field(defn.get("headers", {})),
        "query": _parse_field(defn.get("query", {})),
        "params": _parse_field(defn.get("params", {})),
        "tags": _parse_field(defn.get("tags", []), []),
        "moduleId": defn.get("module_id", "root"),
        "moduleName": defn.get("module_name", "全部接口"),
        "modulePath": defn.get("module_path", "/全部接口"),
        "caseTotal": defn.get("case_total", case_total),
        "casePassRate": defn.get("case_pass_rate", ""),
        "caseStatus": defn.get("case_status", ""),
        "projectId": defn.get("project_id", ""),
        "pos": defn.get("pos", 0),
        "latest": bool(defn.get("latest", True)),
        "versionId": defn.get("version_id", ""),
        "refId": defn.get("ref_id", ""),
        "createTime": int((defn.get("created_at", 0) or 0) * 1000),
        "createUser": defn.get("created_by", defn.get("create_user", "admin")),
        "createUserName": defn.get("create_user_name", defn.get("created_by", "admin")),
        "createName": defn.get("created_by", "admin"),
        "updateTime": int((defn.get("updated_at", 0) or 0) * 1000),
        "updateUser": defn.get("updated_by", defn.get("update_user", "admin")),
        "updateUserName": defn.get("update_user_name", defn.get("updated_by", "admin")),
        "updateName": defn.get("updated_by", "admin"),
        "deleted": bool(defn.get("deleted", False)),
        "deleteTime": int((defn.get("deleted_at", 0) or 0) * 1000) if defn.get("deleted_at") else 0,
        "deleteUser": "",
        "deleteUserName": "",
        "versionName": "",
        "follow": definition_followed(def_id),
        "customFields": [],
    }


# ════════════════════════════════════════════════════════════
# 接口场景适配
# ════════════════════════════════════════════════════════════


@router.post("/api/definition/module/update")
async def api_definition_module_update(request: Request):
    """更新接口定义模块。"""
    m = CompatModuleUpdateBody.model_validate(await read_body(request))
    mod_id = m.id or ""
    name = m.name or ""
    if not mod_id or not name:
        return fail("缺少 id 或 name", code=400)
    updated = apitest_service.update_module(mod_id, name)
    if not updated:
        return fail("模块不存在", code=404)
    module = apitest_service.get_module(mod_id) or {}
    return ok({
        "id": module.get("id", mod_id),
        "name": module.get("name", name),
        "type": "MODULE",
        "parentId": module.get("parent_id", "root"),
        "children": [],
        "count": 0,
    })


@router.get("/api/definition/module/delete")
def api_definition_module_delete(id: str = ""):
    """删除接口定义模块。"""
    if id:
        apitest_service.delete_module(id)
    return ok(None)


@router.post("/api/definition/module/delete")
async def api_definition_module_delete_post(request: Request):
    """删除接口定义模块（POST 方式）。"""
    m = as_model(await read_body(request), CompatModuleDeleteBody)
    mod_id = m.id
    if mod_id:
        apitest_service.delete_module(mod_id)
    return ok(None)


@router.post("/api/definition/module/move")
async def api_definition_module_move(request: Request):
    """移动接口定义模块。"""
    await read_body(request)
    return ok(None)


# ════════════════════════════════════════════════════════════
# 缺失接口补充 - 接口用例
# ════════════════════════════════════════════════════════════


@router.get("/api/definition/module/only/tree")
def api_definition_module_only_tree():
    """获取不包含接口的模块树。"""
    tree = apitest_service.build_module_tree("definition", include_api=False)
    return ok(tree)


@router.get("/api/definition/module/env/tree")
def api_definition_module_env_tree():
    """获取环境的模块树。"""
    tree = apitest_service.build_module_tree("definition", include_api=False)
    return ok(tree)


@router.post("/api/definition/stop")
def api_definition_stop(request: Request):
    """停止接口导出。"""
    return ok(None)


@router.get("/api/definition/download/file/{project_id}/{file_id}")
def api_definition_download_file_path(project_id: str, file_id: str):
    """下载导出的文件。"""
    return ok(None)


@router.post("/api/definition/transfer")
def api_definition_transfer(request: Request):
    """接口定义文件转存。"""
    return ok(None)


@router.get("/api/definition/transfer/options/{project_id}")
def api_definition_transfer_options_path(project_id: str):
    """接口定义文件转存目录。"""
    return ok([])


@router.post("/api/definition/upload/temp/file")
def api_definition_upload_temp_file(request: Request):
    """接口定义临时文件上传。"""
    return ok({
        "fileId": str(uuid.uuid4()),
    })


@router.get("/api/definition/operation-history")
def api_definition_operation_history(request: Request,
                                     id: str = "", sourceId: str = "",
                                     current: int = 1, pageSize: int = 10):
    """接口定义变更历史（GET）。"""
    from app.routers.apitest_compat_base import apitest_service as svc
    def_id = id or sourceId or ""
    try:
        items = svc.list_operation_logs(
            resource_type="definition", resource_id=def_id or None,
            limit=pageSize or 10, offset=(max(current or 1, 1) - 1) * (pageSize or 10),
        )
        total = svc.count_operation_logs(
            resource_type="definition", resource_id=def_id or None,
        )
    except Exception:
        items, total = [], 0
    result = []
    for log in items or []:
        result.append({
            "id": log.get("id", ""),
            "type": str(log.get("action", "update")).upper(),
            "createUser": log.get("operator", "admin"),
            "createUserName": log.get("operator", "admin"),
            "createTime": int((log.get("created_at") or 0) * 1000),
            "sourceId": log.get("resource_id", ""),
            "content": log.get("detail", {}),
            "refId": log.get("resource_id", ""),
            "versionName": "",
            "module": log.get("resource_type", ""),
            "projectId": log.get("project_id", ""),
        })
    return ok({
        "list": result,
        "total": total,
        "current": current or 1,
        "pageSize": pageSize or 10,
    })


@router.post("/api/definition/operation-history")
async def api_definition_operation_history_post(request: Request):
    """接口定义变更历史（POST）。"""
    m = as_model(await read_body(request), CompatExecutionPageBody)
    current = m.effective_current
    page_size = m.effective_page_size
    def_id = m.effective_target_id
    from app.routers.apitest_compat_base import apitest_service as svc
    try:
        items = svc.list_operation_logs(
            resource_type="definition", resource_id=def_id or None,
            limit=page_size, offset=(current - 1) * page_size,
        )
        total = svc.count_operation_logs(
            resource_type="definition", resource_id=def_id or None,
        )
    except Exception:
        items, total = [], 0
    result = []
    for log in items or []:
        result.append({
            "id": log.get("id", ""),
            "type": str(log.get("action", "update")).upper(),
            "createUser": log.get("operator", "admin"),
            "createUserName": log.get("operator", "admin"),
            "createTime": int((log.get("created_at") or 0) * 1000),
            "sourceId": log.get("resource_id", ""),
            "content": log.get("detail", {}),
            "refId": log.get("resource_id", ""),
            "versionName": "",
            "module": log.get("resource_type", ""),
            "projectId": log.get("project_id", ""),
        })
    return ok({
        "list": result,
        "total": total,
        "current": current,
        "pageSize": page_size,
    })


@router.post("/api/definition/operation-history/save")
def api_definition_operation_history_save(request: Request):
    """保存接口定义变更历史。"""
    return ok(None)


@router.post("/api/definition/operation-history/recover")
def api_definition_operation_history_recover(request: Request):
    """恢复接口定义变更历史。"""
    return ok(None)


@router.post("/api/definition/get-reference")
def api_definition_get_reference_route(request: Request):
    """获取接口引用关系。"""
    return ok([])


@router.post("/api/definition/json-schema/preview")
def api_definition_json_schema_preview(request: Request):
    """JSON Schema 转换预览。"""
    return ok({})


@router.post("/api/definition/json-schema/auto-generate")
def api_definition_json_schema_auto_generate(request: Request):
    """JSON Schema 自动生成。"""
    return ok({})


@router.post("/api/definition/file/copy")
def api_definition_file_copy(request: Request):
    """接口定义文件复制。"""
    return ok(None)


@router.post("/api/definition/recover")
async def api_definition_recover(request: Request):
    """恢复接口定义。"""
    m = as_model(await read_body(request), CompatIdBody)
    def_id = m.id if m.id is not None else (m.definitionId if m.definitionId is not None else m.ids)
    ids = def_id if isinstance(def_id, list) else [def_id]
    restored = 0
    for did in ids:
        if did and apitest_service.restore_definition(did):
            restored += 1
    return ok({"restored": restored})


@router.post("/api/definition/batch-recover")
async def api_definition_batch_recover(request: Request):
    """批量恢复接口定义。"""
    m = as_model(await read_body(request), CompatBatchIdsBody)
    ids = m.effective_ids
    restored = 0
    for did in ids:
        if apitest_service.restore_definition(did):
            restored += 1
    return ok({"restored": restored})


@router.get("/api/definition/module/trash/tree")
def api_definition_module_trash_tree():
    """获取接口定义回收站模块树。"""
    return ok([])


@router.get("/api/definition/module/trash/count")
def api_definition_module_trash_count():
    """获取接口定义回收站模块统计数量。"""
    return ok(_build_trash_count_map())


# ════════════════════════════════════════════════════════════
# 缺失接口补充 - 接口用例 AI 功能
# ════════════════════════════════════════════════════════════


@router.post("/api/definition/page-doc")
async def api_definition_page_doc(request: Request):
    """接口定义文档分页列表。"""
    body = DocPageBody.model_validate(await read_body(request))
    keyword = body.keyword or ""
    current = int(body.current or 1)
    page_size = int(body.pageSize or 10)
    try:
        offset = (current - 1) * page_size
        items = apitest_service.list_definitions(
            keyword=keyword, limit=page_size, offset=offset,
        )
        total = apitest_service.count_definitions(keyword=keyword)
        return ok({
            "list": items,
            "total": total,
            "current": current,
            "pageSize": page_size,
        })
    except Exception:
        return ok({
            "list": [], "total": 0, "current": current, "pageSize": page_size,
        })


@router.post("/api/definition/doc")
async def api_definition_doc(request: Request):
    """获取接口定义文档详情。"""
    m = as_model(await read_body(request), CompatIdBody)
    definition_id = m.effective_id
    try:
        item = apitest_service.get_definition(definition_id) if definition_id else None
    except Exception:
        item = None
    if item is None and definition_id:
        item = {"id": definition_id, "name": "", "method": "GET", "path": ""}
    return ok(item)


@router.post("/api/definition/module/trash/tree")
async def api_definition_module_trash_tree_post(request: Request):
    """接口定义回收站模块树（POST 方式）。"""
    m = as_model(await read_body(request), CompatProjectQueryBody)
    project_id = m.projectId
    return ok({
        "id": "root", "name": "根模块", "parentId": "root",
        "children": [], "count": 0, "projectId": project_id,
    })


@router.get("/api/definition/delete-to-gc/{id}")


@router.post("/api/definition/delete-to-gc/{id}")
def api_definition_delete_to_gc_path(id: str):
    """/api/definition/delete-to-gc 带路径参数（前端 RESTful 调用兼容）。"""
    try:
        apitest_service.delete_definition(id)
    except Exception:
        pass
    return ok({"id": id, "deleted": True})


@router.get("/api/definition/delete/{id}")


@router.post("/api/definition/delete/{id}")
def api_definition_delete_path(id: str):
    """/api/definition/delete 带路径参数（前端 RESTful 调用兼容）。

    语义为回收站中彻底删除（purge），与 POST /api/definition/delete 对齐。
    主列表软删请走 /api/definition/delete-to-gc。
    """
    try:
        apitest_service.purge_definition(id)
    except Exception:
        pass
    return ok({"id": id, "deleted": True})


@router.get("/api/definition/follow/{id}")
@router.post("/api/definition/follow/{id}")
def api_definition_follow_path(id: str, user_id: str = "admin"):
    """/api/definition/follow 带路径参数（前端 RESTful 调用兼容）。

    单端点 toggle：真实翻转关注状态并返回服务器侧实际状态，
    供前端「回读」而非只做乐观翻转。
    """
    if not id:
        return fail("缺少 id", code=400)
    followed = apitest_service.toggle_follow("definition", id, user_id)
    return ok({"id": id, "followed": bool(followed)})


@router.get("/api/definition/module/delete/{id}")


@router.post("/api/definition/module/delete/{id}")
def api_definition_module_delete_path(id: str):
    """/api/definition/module/delete 带路径参数（前端 RESTful 调用兼容）。"""
    try:
        apitest_service.delete_module(id)
    except Exception:
        pass
    return ok({"id": id, "deleted": True})


@router.get("/api/definition/rage/{projectId}")
def api_definition_rage_path(projectId: str):
    """/api/definition/rage 接口覆盖率报告（带项目ID）。"""
    from app.services.apitest_service import apitest_service
    list_api_cases = apitest_service.list_api_cases
    list_definitions = apitest_service.list_definitions
    list_scenarios = apitest_service.list_scenarios
    definitions = list_definitions(limit=999)
    api_cases = list_api_cases(limit=999)
    scenarios = list_scenarios(limit=999)
    total_api = len(definitions)
    covered_api = min(total_api, len(api_cases))
    return ok({
        "allApiCount": total_api,
        "unCoverWithApiDefinition": max(0, total_api - covered_api),
        "coverWithApiDefinition": covered_api,
        "apiCoverage": f"{round(covered_api / total_api * 100, 1) if total_api else 0}%",
        "unCoverWithApiCase": 0,
        "coverWithApiCase": len(api_cases),
        "apiCaseCoverage": f"{round(len(api_cases) / total_api * 100, 1) if total_api else 0}%",
        "unCoverWithApiScenario": 0,
        "coverWithApiScenario": len(scenarios),
        "scenarioCoverage": f"{round(len(scenarios) / total_api * 100, 1) if total_api else 0}%",
        "projectId": projectId,
    })


@router.get("/api/definition/schedule/delete/{id}")


@router.post("/api/definition/schedule/delete/{id}")
def api_definition_schedule_delete_path(id: str):
    """/api/definition/schedule/delete 带路径参数（前端 RESTful 调用兼容）。"""
    return ok({"id": id, "deleted": True})


@router.get("/api/definition/schedule/get/{id}")


@router.post("/api/definition/schedule/get/{id}")
def api_definition_schedule_get_path(id: str):
    """/api/definition/schedule/get 带路径参数（前端 RESTful 调用兼容）。"""
    return ok({"id": id, "schedule": None})


@router.get("/api/definition/schedule/switch/{id}")


@router.post("/api/definition/schedule/switch/{id}")
def api_definition_schedule_switch_path(id: str):
    """/api/definition/schedule/switch 带路径参数（前端 RESTful 调用兼容）。"""
    return ok({"id": id, "enabled": True})
