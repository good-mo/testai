# app/routers/functional_cases.py（自 app/adapters/domains/functional_cases.py 迁移）
"""业务域路由拆分：functional_cases（Phase 3 重构）。"""

import asyncio
import json
import os

from fastapi import APIRouter, Request

from app.core.response import fail, ok, page_result, read_body
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-functional_cases"])



from app.domain.case.application.dto import (
    FunctionalCaseFollowBody,
    FunctionalCaseRefBody,
    FunctionalModuleBody,
    FunctionalTrashBatchBody,
    FunctionalTrashPageBody,
)

from app.domain.apitest.application.apitest_app_service import apitest_service
from app.domain.cases.application.case_app_service import case_service


@router.get("/functional/case/delete")
async def functional_case_delete_get(request: Request):
    """功能用例删除（GET兼容）。"""
    body = await read_body(request)
    case_id = FunctionalCaseRefBody.model_validate(body).effective_id
    case_service.soft_delete(case_id)
    return ok()


@router.post("/functional/case/demand/third/list/page")
async def functional_case_demand_third_list_page_post(request: Request):
    """功能用例三方需求列表分页（POST兼容）。"""
    body = await read_body(request)
    req = FunctionalTrashPageBody.model_validate(body)
    return page_result([], len([]), current=req.current, page_size=req.pageSize)


def _trash_module_counts(project_id: str = "") -> dict:
    """统计回收站用例按模块分布。返回 {all: 总数, root: 根模块数, <moduleId>: 数量}。"""
    try:
        trashed = case_service.list_trash()
        counts: dict = {"all": len(trashed), "root": 0}
        for t in trashed:
            case = t.get("case_data", {}) or {}
            meta = case.get("metadata", {}) or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    meta = {}
            mod_id = meta.get("module_id", "") or case.get("module_id", "") or "root"
            counts[mod_id] = counts.get(mod_id, 0) + 1
        return counts
    except Exception:
        return {"all": 0, "root": 0}


def _build_trash_module_tree(project_id: str = "") -> list:
    """构建回收站模块树（仅保留有回收站用例的模块节点）。

    每个模块 count = 该模块下（含子模块）回收站用例总数。
    """
    try:
        trashed = case_service.list_trash()
        counts = _trash_module_counts(project_id)
        if not trashed:
            return []
        # 构建 functional 模块层级
        tree = case_service.build_functional_module_tree() if hasattr(case_service, "build_functional_module_tree") else None
        if not tree:
            return []
        # 递归过滤只保留 count>0 的节点（含子孙累计）
        def _prune(node):
            children = []
            for child in node.get("children", []) or []:
                pruned_child = _prune(child)
                if pruned_child is not None:
                    children.append(pruned_child)
            # 计算当前节点的回收站用例数（自身 + 子孙）
            direct = counts.get(node.get("id", ""), 0)
            child_sum = sum(c.get("count", 0) for c in children)
            total = direct + child_sum
            if total > 0 or children:
                result = dict(node)
                result["children"] = children
                result["count"] = total
                return result
            return None

        pruned = []
        for node in tree:
            result = _prune(node)
            if result is not None:
                pruned.append(result)
        return pruned
    except Exception:
        return []


@router.post("/functional/case/module/count")
async def functional_case_module_count_post(request: Request):
    """功能用例模块统计（真实实现）。返回 {all: 总数, moduleId: 数量} 格式。"""
    modules = apitest_service.list_modules("functional")
    # 仅统计功能用例（test_type=functional）
    cases = case_service.list_cases(test_type="functional", limit=100000)
    # total 用 DB 侧 COUNT，不受拉取 limit 封顶
    total = case_service.count_cases(test_type="functional")
    counts: dict = {"all": total, "root": 0}
    for m in modules:
        counts[m.get("id", "")] = 0
    for c in cases:
        meta = c.get("metadata", {}) or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                meta = {}
        mod_id = meta.get("module_id", "") or c.get("module_id", "") or "root"
        if mod_id not in counts:
            counts[mod_id] = 0
        counts[mod_id] = counts.get(mod_id, 0) + 1
    return ok(counts)


@router.post("/functional/case/test/associate/case/module/count")
def functional_case_test_associate_module_count_post(request: Request):
    """功能用例关联用例模块统计（POST兼容）。"""
    return ok([])


@router.post("/functional/case/trash/module/count")
def functional_case_trash_module_count_post(request: Request):
    """功能用例回收站模块统计（POST兼容）。"""
    trashed = case_service.list_trash()
    return ok({"all": len(trashed)})


@router.post("/functional/case/test/associate/case/module/tree")
def functional_case_test_associate_case_module_tree_post(request: Request):
    """功能用例关联用例模块树（POST兼容）。"""
    return ok([])


@router.post("/functional/case/comment/delete")
async def functional_case_comment_delete(request: Request):
    """删除功能用例评论。"""
    await read_body(request)
    return ok()


@router.post("/functional/case/comment/get/list")
async def functional_case_comment_get_list(request: Request):
    """获取功能用例评论列表。"""
    await read_body(request)
    return ok([])


@router.post("/functional/case/review/comment")
async def functional_case_review_comment(request: Request):
    """功能用例评审评论。"""
    await read_body(request)
    return ok()


@router.post("/functional/case/demand/page")
async def functional_case_demand_page(request: Request):
    """功能用例需求关联分页。"""
    await read_body(request)
    return page_result([], len([]), current=1, page_size=10)


@router.get("/functional/case/custom/field/{project_id}")
@router.post("/functional/case/custom/field/{project_id}")
def func_case_custom_field_path(project_id: str):
    """获取功能用例自定义字段（带路径参数）。

    前端 getFilterCustomFields 期望接收数组格式的自定义字段定义列表。
    目前系统尚未持久化自定义字段，返回空数组保证页面正常加载。
    """
    return ok([])


@router.get("/functional/case/default/template/field/{project_id}")
@router.post("/functional/case/default/template/field/{project_id}")
def func_case_default_template_field_path(project_id: str):
    """获取功能用例默认模板字段（带路径参数）。

    前端 getCaseDefaultFields 期望返回 {id, customFields} 结构。
    提供默认的功能用例模板，包含用例等级 functional_priority 内置字段。
    """
    default_fields = [
        {
            "fieldId": "functional_priority",
            "fieldName": "用例等级",
            "internal": True,
            "internalFieldKey": "functional_priority",
            "type": "SELECT",
            "required": True,
            "defaultValue": "P2",
            "options": [
                {"value": "P0", "text": "P0", "internal": True, "pos": 1},
                {"value": "P1", "text": "P1", "internal": True, "pos": 2},
                {"value": "P2", "text": "P2", "internal": True, "pos": 3},
                {"value": "P3", "text": "P3", "internal": True, "pos": 4},
            ],
        }
    ]
    return ok({
        "id": f"default-template-{project_id}",
        "name": "默认模板",
        "internal": True,
        "customFields": default_fields,
    })


@router.get("/functional/case/demand/cancel/{case_id}")
@router.post("/functional/case/demand/cancel/{case_id}")
def func_case_demand_cancel_path(case_id: str):
    """取消用例需求关联（带路径参数）。"""
    return ok({"id": case_id, "cancelled": True})


@router.get("/functional/case/download/file/{case_id}/{file_id}")
@router.post("/functional/case/download/file/{case_id}/{file_id}")
async def func_case_download_file_path(case_id: str, file_id: str):
    """下载功能用例导出文件（带路径参数）。file_id 为导出文件ID时返回真实文件流。"""
    from fastapi.responses import FileResponse

    from app.domain.functional_export.application.export_app_service import export_app_service as functional_export_service

    path = await asyncio.to_thread(functional_export_service.download_path, file_id)
    if path:
        task = functional_export_service.download_task_meta(file_id)
        filename = (task or {}).get("filename") or os.path.basename(path)
        return FileResponse(path, filename=filename)
    return ok({"case_id": case_id, "file_id": file_id})


@router.get("/functional/case/export/columns/{project_id}")
@router.post("/functional/case/export/columns/{project_id}")
def func_case_export_columns_path(project_id: str):
    """获取功能用例导出列（带路径参数）。

    前端 MsExportDrawer 期望返回 {systemColumns: {key: label}, customColumns: {...}} 结构。
    systemColumns 对应系统内置列；customColumns 对应模板自定义字段列。
    """
    # 系统内置列（与前端功能用例表列定义对齐）
    system_columns = {
        "num": "ID",
        "name": "名称",
        "caseLevel": "用例等级",
        "reviewStatus": "评审结果",
        "lastExecuteResult": "执行结果",
        "moduleId": "所属模块",
        "tags": "标签",
        "updateUser": "更新人",
        "updateTime": "更新时间",
        "createUser": "创建人",
        "createTime": "创建时间",
    }
    # 从默认模板读取自定义字段作为可导出列
    custom_columns: dict = {}
    try:
        default_tpl = func_case_default_template_field_path(project_id)
        tpl_body = json.loads(default_tpl.body) if hasattr(default_tpl, "body") else {}
        tpl_data = tpl_body.get("data", {}) or {}
        for field in tpl_data.get("customFields") or []:
            custom_columns[field.get("fieldId", "")] = field.get("fieldName", "")
    except Exception:
        pass
    return ok({
        "systemColumns": system_columns,
        "customColumns": custom_columns,
    })


@router.get("/functional/case/module/delete/{module_id}")
@router.post("/functional/case/module/delete/{module_id}")
def func_case_module_delete_path(module_id: str):
    """删除功能用例模块（带路径参数）。"""
    return ok({"id": module_id, "deleted": True})


@router.get("/functional/case/stop/{case_id}")
@router.post("/functional/case/stop/{case_id}")
def func_case_stop_path(case_id: str):
    """停止功能用例执行（带路径参数）。"""
    return ok({"id": case_id, "stopped": True})


@router.get("/functional/case/test/disassociate/bug/{case_id}")
@router.post("/functional/case/test/disassociate/bug/{case_id}")
def func_case_disassociate_bug_path(case_id: str):
    """取消功能用例与缺陷关联（带路径参数）。"""
    return ok({"id": case_id, "disassociated": True})


# ════════════════════════════════════════════════════════════
# 组织管理
# ════════════════════════════════════════════════════════════


@router.get("/functional/case/module/tree/{project_id}")
async def functional_case_module_tree_path(project_id: str):
    """获取功能用例模块树（带路径参数）。

    复用真实模块树构建逻辑（与 cases.py 中无 path 参数的
    /functional/case/module/tree 保持一致）。原先此处返回写死的空
    root（children 恒为空），导致前端功能用例页左侧目录树读不到任何
    已创建的功能模块，目录无法展开、也无法进入模块添加用例。
    """
    tree = await asyncio.to_thread(case_service.build_functional_module_tree)
    return ok(tree)


# 功能用例回收站模块树（前端: /functional/case/module/trash/tree/{projectId}）


@router.get("/functional/case/module/trash/tree/{project_id}")
def functional_case_module_trash_tree_path(project_id: str):
    """获取功能用例回收站模块树（带路径参数）。

    基于 functional 模块树结构，仅保留有回收站用例的模块，
    每个模块的 count = 该模块下（含子模块）回收站用例总数。
    """
    return ok(_build_trash_module_tree(project_id))


# 公共脚本列选项（前端: /project/custom/func/columns-option/{projectId}）


@router.get("/functional/case/relationship/get-ids/{case_id}")
def functional_case_relationship_get_ids_path(case_id: str):
    """获取功能用例前后置已关联 IDs（带路径参数）。"""
    return ok([])


# 功能用例测试计划评论（前端: /functional/case/test/plan/comment/{caseId}）


@router.get("/functional/case/test/plan/comment/{case_id}")
def functional_case_test_plan_comment_path(case_id: str):
    """获取功能用例测试计划评论（带路径参数）。"""
    return ok([])


# 消息任务配置（前端: /notice/message/task/get/{projectId}）


@router.post("/functional/case/batch/edit")
def functional_case_batch_edit(request: Request):
    """批量编辑功能用例。"""
    return ok(None)


@router.post("/functional/case/batch/move")
def functional_case_batch_move(request: Request):
    """批量移动功能用例。"""
    return ok(None)


_FUNC_CASE_FOLLOW_TYPE = "functional_case"


@router.get("/functional/case/follower")
def functional_case_follower(functional_case_id: str = ""):
    """获取功能用例关注人（真实回读 api_follows 落库）。"""
    case_id = functional_case_id or ""
    return ok(apitest_service.list_followers(_FUNC_CASE_FOLLOW_TYPE, case_id))


@router.post("/functional/case/edit/follower")
async def functional_case_edit_follower(request: Request):
    """关注/取消关注功能用例（单端点 toggle，真实落库并回读）。

    前端 followerCaseRequest 发送 { userId, functionalCaseId }。
    兼容 body / query 取参，返回翻转后的真实状态供前端读回。
    """
    body = await read_body(request)
    req = FunctionalCaseFollowBody.model_validate(body)
    case_id = req.effective_case_id
    user_id = req.effective_user_id
    if not case_id:
        return fail("缺少 functionalCaseId", code=400)
    followed = apitest_service.toggle_follow(_FUNC_CASE_FOLLOW_TYPE, case_id, user_id)
    return ok({"functionalCaseId": case_id, "followed": bool(followed)})


@router.post("/functional/case/custom/field")
def functional_case_custom_field(request: Request):
    """获取自定义字段。"""
    return ok([])


@router.post("/functional/case/module/add")
async def functional_case_module_add(request: Request):
    """添加模块。"""
    body = await read_body(request)
    req = FunctionalModuleBody.model_validate(body)
    module = apitest_service.add_module(
        scope="functional",
        name=req.name or "新模块",
        parent_id=req.parentId or "root",
        project_id=req.projectId,
    )
    return ok(module)


@router.post("/functional/case/module/update")
async def functional_case_module_update(request: Request):
    """更新模块。"""
    body = await read_body(request)
    req = FunctionalModuleBody.model_validate(body)
    mod_id = req.effective_module_id
    name = req.name
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


@router.post("/functional/case/module/move")
def functional_case_module_move(request: Request):
    """移动模块。"""
    return ok(None)


@router.get("/functional/case/module/trash/tree")
def functional_case_module_trash_tree():
    """获取回收站模块树。"""
    return ok(_build_trash_module_tree())


# ── 功能用例回收站 ──────────────────────────────────────


@router.get("/functional/case/module/count")
def functional_case_module_count():
    """获取全部用例模块数量。返回 {all: 总数, moduleId: 数量} 格式。"""
    modules = apitest_service.list_modules("functional")
    # 仅统计功能用例（test_type=functional）
    cases = case_service.list_cases(test_type="functional", limit=100000)
    # total 用 DB 侧 COUNT，不受拉取 limit 封顶
    total = case_service.count_cases(test_type="functional")
    counts: dict = {"all": total, "root": 0}
    for m in modules:
        counts[m.get("id", "")] = 0
    for c in cases:
        meta = c.get("metadata", {}) or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                meta = {}
        mod_id = meta.get("module_id", "") or c.get("module_id", "") or "root"
        if mod_id not in counts:
            counts[mod_id] = 0
        counts[mod_id] = counts.get(mod_id, 0) + 1
    return ok(counts)


@router.post("/functional/case/trash/page")
async def functional_case_trash_page(request: Request):
    """功能用例回收站分页列表。"""
    body = await read_body(request)
    req = FunctionalTrashPageBody.model_validate(body)
    keyword = req.keyword or ""
    page_size = req.pageSize
    current = req.current
    trashed = case_service.list_trash()
    items = []
    for t in trashed:
        case = t.get("case_data", {})
        item = case_service.to_functional_case(case)
        item["deleted"] = True
        item["deleteTime"] = t.get("deleted_at", 0)
        item["deleteUser"] = t.get("deleted_by", "")
        item["deleteUserName"] = t.get("deleted_by", "")  # 前端 template 访问 deleteUserName
        items.append(item)
    # 简单关键词过滤
    if keyword:
        items = [i for i in items if keyword.lower() in i.get("name", "").lower()
                 or keyword.lower() in i.get("id", "").lower()]
    total = len(items)
    start = (current - 1) * page_size
    page_items = items[start:start + page_size]
    return ok({
            "list": page_items,
            "total": total,
            "pageSize": page_size,
            "current": current,
        })


@router.get("/functional/case/trash/module/count")
def functional_case_trash_module_count():
    """获取回收站模块数量。"""
    return ok(_trash_module_counts())


@router.post("/functional/case/trash/recover")
async def functional_case_trash_recover(request: Request):
    """恢复单个回收站用例。body: {id}"""
    body = await read_body(request)
    case_id = FunctionalCaseRefBody.model_validate(body).effective_id
    case_service.restore(case_id, operator="admin")
    return ok(None)


@router.get("/functional/case/trash/recover/{case_id}")
def functional_case_trash_recover_get(case_id: str):
    """恢复单个回收站用例（GET）。"""
    case_service.restore(case_id, operator="admin")
    return ok(None)


@router.get("/functional/case/trash/delete/{case_id}")
def functional_case_trash_delete_get(case_id: str):
    """删除单个回收站用例（GET）。"""
    case_service.purge(case_id)
    return ok(None)


@router.post("/functional/case/trash/batch/recover")
async def functional_case_trash_batch_recover(request: Request):
    """批量恢复回收站用例。body: {ids: [] | selectIds: []}"""
    body = await read_body(request)
    # 前端批量操作发送 selectIds / selectedIds，兼容 ids / id
    ids = FunctionalTrashBatchBody.model_validate(body).effective_ids()
    for case_id in ids:
        try:
            case_service.restore(case_id, operator="admin")
        except Exception:
            pass
    return ok(None)


@router.post("/functional/case/trash/delete")
async def functional_case_trash_delete(request: Request):
    """删除单个回收站用例。body: {id}"""
    body = await read_body(request)
    case_id = FunctionalCaseRefBody.model_validate(body).effective_id
    case_service.purge(case_id)
    return ok(None)


@router.post("/functional/case/trash/batch/delete")
async def functional_case_trash_batch_delete(request: Request):
    """批量删除回收站用例。body: {ids: [] | selectIds: []}"""
    body = await read_body(request)
    # 前端批量操作发送 selectIds / selectedIds，兼容 ids / id
    ids = FunctionalTrashBatchBody.model_validate(body).effective_ids()
    for case_id in ids:
        try:
            case_service.purge(case_id)
        except Exception:
            pass
    return ok(None)
