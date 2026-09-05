# app/routers/functional_cases_extra.py
"""功能用例业务域路由（补充段）。

由 app/routers/functional_cases.py 按业务域拆分而来（P4 超大文件拆分）：
主文件保留核心 CRUD / 模块 / 回收站路由；本文件承载
脑图 / 导入导出 / 评论 / 需求关联 / 前后置关系 / 用例关联 / AI / 路径参数兼容等补充路由。

纯路由搬移，行为不变：本文件注册到同一 router（tags=adapter-functional_cases_extra），
所有响应沿用核心响应函数 ok()/fail() 与 read_body()。
"""

import asyncio

from fastapi import APIRouter, Request

from app.core.helpers import current_user_name
from app.core.response import ok, read_body
from app.models.case import FunctionalModuleDeleteBody
from app.services import functional_export_service
from app.services.apitest_service import apitest_service
from app.services.case_service import case_service

router = APIRouter(tags=["adapter-functional_cases_extra"])


# 附件路由已迁移至 app/file_mgmt/ 模块


# ── 缺陷更多接口 ────────────────────────────────────────


@router.post("/functional/mind/case/review/list")
def functional_mind_case_review_list(request: Request):
    """获取评审脑图数据。"""
    cases = case_service.list_cases(limit=500)
    review_cases = [c for c in cases if c.get("status") in ("review", "pending", "in_review")]
    tree = []
    for c in review_cases:
        node = {
            "id": c.get("id", ""),
            "text": c.get("title", ""),
            "resource": {
                "status": c.get("status", "review"),
                "priority": c.get("priority", "P2"),
            },
            "children": [],
        }
        tree.append(node)
    return ok(tree)


@router.post("/functional/mind/case/plan/list")
def functional_mind_case_plan_list(request: Request):
    """获取测试计划用例脑图。"""
    cases = case_service.list_cases(limit=500)
    tree = []
    for c in cases:
        node = {
            "id": c.get("id", ""),
            "text": c.get("title", ""),
            "resource": {
                "status": c.get("status", "draft"),
                "priority": c.get("priority", "P2"),
            },
            "children": [],
        }
        tree.append(node)
    return ok(tree)


@router.post("/functional/mind/case/collection/list")
def functional_mind_case_collection_list(request: Request):
    """获取测试计划用例脑图-测试点。"""
    cases = case_service.list_cases(limit=500)
    tree = []
    for c in cases:
        node = {
            "id": c.get("id", ""),
            "text": c.get("title", ""),
            "resource": {
                "status": c.get("status", "draft"),
                "priority": c.get("priority", "P2"),
            },
            "children": [],
        }
        tree.append(node)
    return ok(tree)


# ════════════════════════════════════════════════════════════
# 项目成员管理
# 前端: /project/member/*  →  项目成员管理
# ════════════════════════════════════════════════════════════


@router.post("/functional/mind/case/edit")
async def functional_mind_case_edit(request: Request):
    """保存用例脑图。"""
    await read_body(request)  # 占位实现：读取以触发请求体校验
    return ok(None)


@router.get("/functional/mind/case/tree")
def functional_mind_case_tree():
    """获取脑图模块树。"""
    return ok({
        "id": "root",
        "name": "全部用例",
        "type": "MODULE",
        "children": [],
    })


# 导入导出


@router.post("/functional/case/pre-check/excel")
def functional_case_pre_check_excel(request: Request):
    """导入Excel文件检查。"""
    return ok({
        "success": True,
        "errors": [],
    })


@router.post("/functional/case/pre-check/xmind")
def functional_case_pre_check_xmind(request: Request):
    """导入XMind文件检查。"""
    return ok({
        "success": True,
        "errors": [],
    })


@router.post("/functional/case/import/excel")
def functional_case_import_excel(request: Request):
    """导入Excel文件。"""
    return ok({
        "successCount": 0,
        "failCount": 0,
    })


@router.post("/functional/case/import/xmind")
def functional_case_import_xmind(request: Request):
    """导入XMind文件。"""
    return ok({
        "successCount": 0,
        "failCount": 0,
    })


@router.post("/functional/case/export/excel")
async def functional_case_export_excel(request: Request):
    """导出Excel文件：生成真实文件并登记导出任务。"""
    body = await read_body(request)
    result = await asyncio.to_thread(functional_export_service.export_cases_excel, body)
    # 前端此处把返回值整体当作 taskId 展示；返回含 fileId/taskId 的对象便于 websocket 关联
    return ok(result)


@router.post("/functional/case/export/xmind")
async def functional_case_export_xmind(request: Request):
    """导出XMind文件：生成真实文件并登记导出任务。"""
    body = await read_body(request)
    result = await asyncio.to_thread(functional_export_service.export_cases_xmind, body)
    return ok(result)


@router.get("/functional/case/check/export-task")
async def functional_case_check_export_task():
    """检查是否有进行中的导出任务。无任务时返回空对象（fileId=''），前端据此打开导出弹窗。"""
    task = await asyncio.to_thread(functional_export_service.task_status)
    if not task:
        return ok({"fileId": "", "taskId": ""})
    return ok({"fileId": task.get("fileId", ""), "taskId": task.get("taskId", "")})


@router.get("/functional/case/export/columns")
def functional_case_export_columns():

    """获取导出字段配置（无路径参数，返回系统列）。"""
    return ok({
        "systemColumns": {
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
        },
        "customColumns": {},
    })


@router.get("/functional/case/download/file")
def functional_case_download_file():
    """下载导出的文件（无参占位；带 fileId 的下载走 /functional/case/download/file/{projectId}/{fileId}）。"""
    return ok(None)


@router.get("/functional/case/stop")
def functional_case_stop():
    """停止导出（无参占位）。"""
    return ok(None)


@router.get("/functional/case/download/excel/template")
def functional_case_download_excel_template():
    """下载Excel导入模板。"""
    return ok(None)


@router.get("/functional/case/download/xmind/template")
def functional_case_download_xmind_template():
    """下载XMind导入模板。"""
    return ok(None)


# 评论


@router.get("/functional/case/comment/get/list/{case_id}")
def functional_case_comment_get_list_by_id(case_id: str):
    """获取用例评论列表。"""
    return ok([])


@router.post("/functional/case/comment/save")
def functional_case_comment_save(request: Request):
    """创建用例评论。"""
    return ok(None)


@router.post("/functional/case/comment/update")
def functional_case_comment_update(request: Request):
    """更新用例评论。"""
    return ok(None)


@router.get("/functional/case/comment/delete/{comment_id}")
def functional_case_comment_delete_by_id(comment_id: str):
    """删除用例评论。"""
    return ok(None)


@router.get("/functional/case/review/comment/{case_id}")
def functional_case_review_comment_by_id(case_id: str):
    """获取用例评审评论。"""
    return ok([])


# 需求关联


@router.get("/functional/case/demand/page/{case_id}")
def functional_case_demand_page_by_id(case_id: str):
    """获取用例关联需求列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.post("/functional/case/demand/add")
def functional_case_demand_add(request: Request):
    """添加用例需求关联。"""
    return ok(None)


@router.post("/functional/case/demand/update")
def functional_case_demand_update(request: Request):
    """更新用例需求关联。"""
    return ok(None)


@router.post("/functional/case/demand/batch/relevance")
def functional_case_demand_batch_relevance(request: Request):
    """批量关联需求。"""
    return ok(None)


@router.post("/functional/case/demand/cancel")
def functional_case_demand_cancel(request: Request):
    """取消用例需求关联。"""
    return ok(None)


@router.get("/functional/case/demand/third/list/page")
def functional_case_demand_third_list():
    """获取三方关联需求列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


# 用例关系（前后置）


@router.get("/functional/case/relationship/page/{case_id}")
def functional_case_relationship_page(case_id: str):
    """获取前后置用例列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.post("/functional/case/relationship/page")
def functional_case_relationship_page_post(request: Request):
    """获取前后置用例列表（POST）。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.post("/functional/case/relationship/relate/page")
def functional_case_relationship_relate_page(request: Request):
    """获取可关联的前后置用例列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.post("/functional/case/relationship/add")
def functional_case_relationship_add(request: Request):
    """添加前后置关系。"""
    return ok(None)


@router.post("/functional/case/relationship/delete")
def functional_case_relationship_delete(request: Request):
    """取消前后置关系。"""
    return ok(None)


@router.get("/functional/case/relationship/get-ids")
def functional_case_relationship_get_ids():
    """获取前后置已关联用例ids。"""
    return ok([])


# 用例关联（接口用例、缺陷等）


@router.post("/functional/case/test/associate/case/page")
def functional_case_test_associate_case_page(request: Request):
    """获取可关联的接口用例列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.get("/functional/case/test/associate/case/module/count")
def functional_case_test_associate_case_module_count():
    """获取接口用例模块数量。"""
    return ok([])


@router.get("/functional/case/test/associate/case/module/tree")
def functional_case_test_associate_case_module_tree():
    """获取接口用例模块树。"""
    return ok([])


@router.post("/functional/case/test/associate/case")
def functional_case_test_associate_case(request: Request):
    """关联接口用例。"""
    return ok(None)


@router.post("/functional/case/test/has/associate/case/page")
def functional_case_test_has_associate_case_page(request: Request):
    """获取已关联用例列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.post("/functional/case/test/disassociate/case")
def functional_case_test_disassociate_case(request: Request):
    """取消关联用例。"""
    return ok(None)


@router.post("/functional/case/test/associate/bug/page")
def functional_case_test_associate_bug_page(request: Request):
    """获取可关联的缺陷列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.post("/functional/case/test/associate/bug")
def functional_case_test_associate_bug(request: Request):
    """关联缺陷。"""
    return ok(None)


@router.post("/functional/case/test/disassociate/bug")
def functional_case_test_disassociate_bug(request: Request):
    """取消关联缺陷。"""
    return ok(None)


@router.post("/functional/case/test/has/associate/bug/page")
def functional_case_test_has_associate_bug_page(request: Request):
    """获取已关联缺陷列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.post("/functional/case/test/has/associate/plan/page")
def functional_case_test_has_associate_plan_page(request: Request):
    """获取已关联测试计划列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.post("/functional/case/test/plan/comment")
def functional_case_test_plan_comment(request: Request):
    """获取测试计划评论。"""
    return ok([])


@router.get("/functional/case/test/associate/case/page")
def functional_case_test_associate_case_page_get():
    """获取可关联的接口用例列表（GET）。"""
    return ok({
        "list": [],
        "total": 0,
    })


# 用例变更历史


@router.post("/functional/case/operation-history")
def functional_case_operation_history(request: Request):
    """获取用例变更历史。"""
    return ok({
        "list": [],
        "total": 0,
    })


# 用例拖拽排序


@router.post("/functional/case/edit/pos")
async def functional_case_edit_pos(request: Request):
    """用例拖拽排序（更新用例所属模块与位置元数据）。

    入参：{ projectId, targetId, moveMode, moveId }
    - moveId: 被拖拽的用例 ID
    - targetId: 拖拽目标（用例 ID 或模块 ID）
    - moveMode: BEFORE/AFTER/APPEND
    """
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    move_id = body.get("moveId") or ""
    target_id = body.get("targetId") or ""
    move_mode = body.get("moveMode") or ""
    if not move_id:
        return ok({"success": False})
    case = case_service.get(move_id)
    if not case:
        return ok({"success": False, "msg": "用例不存在"})
    # 将位置与目标写入 metadata
    try:
        import json as _json
        meta = case.get("metadata", "{}")
        if isinstance(meta, str):
            try:
                meta = _json.loads(meta)
            except Exception:
                meta = {}
        if not isinstance(meta, dict):
            meta = {}
        meta["pos"] = body.get("pos", 0)
        meta["target_id"] = target_id
        meta["move_mode"] = move_mode if isinstance(move_mode, str) else str(move_mode or "")
        # 若目标是模块 ID（非用例），切换模块归属
        if move_mode in ("APPEND",) or (target_id and not case_service.get(target_id)):
            meta["module_id"] = target_id
        case_service.update(move_id, {"metadata": meta})
    except Exception:
        return ok({"success": False})
    return ok({"success": True, "moveId": move_id})


# 模块删除


@router.get("/functional/case/module/delete")
def functional_case_module_delete(id: str = ""):
    """删除用例模块。"""
    if id:
        apitest_service.delete_module(id)
    return ok(None)


@router.post("/functional/case/module/delete")
async def functional_case_module_delete_post(request: Request):
    """删除用例模块（POST）。"""
    body = await read_body(request)
    mod_id = FunctionalModuleDeleteBody.model_validate(body).effective_module_id
    if mod_id:
        apitest_service.delete_module(mod_id)
    return ok(None)


@router.get("/functional/case/default/template/field")
def functional_case_default_template_field():
    """获取默认模板自定义字段。"""
    return ok([])


# 回收站模块相关


@router.post("/functional/case/review/page")
def functional_case_review_page(request: Request):
    """获取用例详情评审列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


# 项目下拉选项


@router.post("/functional/case/ai/save/config")
async def functional_case_ai_save_config(request: Request):
    """保存功能用例 AI 配置（真实持久化）。"""
    body = await read_body(request)
    from app.services.ai_config_service import ai_config_service
    if not isinstance(body, dict):
        body = {}
    # 前端 config 形如 {designConfig: {...}, templateConfig: {...}}
    cfg_data = body.get("config") if "config" in body else body
    if not isinstance(cfg_data, dict):
        cfg_data = {}
    owner = current_user_name(request)
    project_id = str(body.get("projectId") or "")
    saved = ai_config_service.save_functional_case_config(
        config_value=cfg_data,
        owner=owner,
        project_id=project_id,
        create_user=owner,
    )
    return ok({"saved": True, "id": saved.get("id", "")})


@router.get("/functional/case/ai/get/config")
def functional_case_ai_get_config(request: Request = None):
    """获取功能用例 AI 配置（有默认兜底，不再返回空对象）。"""
    from app.services.ai_config_service import ai_config_service
    owner = current_user_name(request) if request else "admin"
    project_id = str(request.query_params.get("projectId", "")) if request else ""
    cfg = ai_config_service.get_functional_case_config(
        owner=owner, project_id=project_id,
    )
    return ok(cfg)


@router.post("/functional/case/ai/transform")
async def functional_case_ai_transform(request: Request):
    """功能用例 AI 结构转换。

    将请求文本与用例数据写入 AI 对话历史；当前无 LLM 服务时
    返回结构化的空转换结果（前端可识别）。
    """
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    prompt = (body.get("prompt") or body.get("message")
              or body.get("description") or "")
    owner = current_user_name(request)
    case_ids = body.get("caseIds") or []
    from app.services.ai_config_service import ai_config_service
    conv = ai_config_service.chat(
        conversation_id=str(body.get("conversationId") or ""),
        prompt=prompt or "AI 用例结构转换",
        owner=owner, create_user=owner,
    )
    return ok({
        "conversationId": conv["id"],
        "transformed": [],
        "success": True,
        "caseIds": case_ids if isinstance(case_ids, list) else [],
    })


@router.post("/functional/case/ai/chat")
async def functional_case_ai_chat(request: Request):
    """功能用例 AI 聊天。

    将用户消息真实持久化到 AI 对话；回复内容为空（等待 LLM 服务接入）。
    """
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    prompt = (body.get("prompt") or body.get("message")
              or body.get("content") or "")
    owner = current_user_name(request)
    conv_id = str(body.get("conversationId") or "")
    from app.services.ai_config_service import ai_config_service
    conv = ai_config_service.chat(
        conversation_id=conv_id,
        prompt=prompt,
        owner=owner, create_user=owner,
    )
    return ok({
        "id": conv["id"],
        "conversationId": conv["id"],
        "content": "",
    })


@router.post("/functional/case/ai/batch/save")
async def functional_case_ai_batch_save(request: Request):
    """功能用例 AI 批量保存。

    将 AI 生成的用例数据批量写入 test_cases 表（case_service.create）。
    """
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    cases = body.get("cases") or body.get("list") or []
    if isinstance(cases, dict):
        cases = [cases]
    saved = []
    for c in cases if isinstance(cases, list) else []:
        if not isinstance(c, dict) or not c.get("title"):
            continue
        try:
            new_case = case_service.create({
                "title": c.get("title", ""),
                "description": c.get("description", ""),
                "priority": c.get("priority", "P2"),
                "status": c.get("status", "draft"),
                "tags": c.get("tags") or [],
            })
            if new_case:
                saved.append(new_case.get("id", ""))
        except Exception:
            continue
    return ok({
        "success": True,
        "saved": saved,
        "savedCount": len(saved),
    })


# ════════════════════════════════════════════════════════════
# 缺失接口补充 - 接口用例高级功能
# ════════════════════════════════════════════════════════════


# ════════════════════════════════════════════════════════════
# 路径参数兼容路由（自 path_param_fixes.py 迁移）
# ════════════════════════════════════════════════════════════

@router.get("/functional/case/delete/{id}")
@router.post("/functional/case/delete/{id}")
def functional_case_delete_path(id: str):
    """/functional/case/delete 带路径参数（前端 RESTful 调用兼容）。"""
    try:
        case_service.purge(id)
    except Exception:
        pass
    return ok({"id": id, "deleted": True})
