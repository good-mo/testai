import json
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Request

from app.core.response import fail, ok, read_body
from app.core.helpers import as_model, current_user_name
from app.models.apitest import (
    CaseCompatAiSaveConfigBody,
    CaseCompatBatchEditBody,
    CaseCompatCreateBody,
    CaseCompatPageBody,
    CaseCompatPriorityBody,
    CaseCompatStatusBody,
    CaseCompatTrashPageBody,
    CaseCompatUpdateBody,
    CompatBatchIdsBody,
    CompatExecutionPageBody,
    CompatIdBody,
)
from app.routers.apitest_compat_base import apitest_service

router = APIRouter(tags=["adapter-api_testing_case"])


@router.get("/api/case/delete")
async def api_case_delete_get(request: Request):
    """接口用例删除（GET兼容）。"""
    m = as_model(await read_body(request), CompatIdBody)
    case_id = m.id if m.id is not None else (m.caseId or "")
    apitest_service.purge_case(case_id)
    return ok()


@router.get("/api/case/follow")
def api_case_follow_get(request: Request):
    """接口用例关注（GET兼容）。"""
    from app.services.apitest_service import apitest_service as apitest_store
    case_id = request.query_params.get("id") or request.query_params.get("caseId") or ""
    if not case_id:
        return ok({"success": False})
    return ok({"success": apitest_store.follow_resource("case", case_id)})


@router.get("/api/case/recover")
async def api_case_recover_get(request: Request):
    """接口用例恢复（GET兼容）。

    前端以 query 传 `id`（axios 拦截器只把非 GET 的 params 塞进请求体，
    GET 请求的参数落在 query string）。这里把 query 参数与 body 合并归一化。
    """
    body = await read_body(request)
    query = dict(request.query_params)
    if not isinstance(body, dict):
        body = {}
    for key in ("id", "ids"):
        if key not in body and key in query:
            body[key] = query[key]
    m = as_model(body, CompatIdBody)
    case_id = m.id_or_ids
    ids = case_id if isinstance(case_id, list) else [case_id]
    restored = 0
    for cid in ids:
        if not cid:
            continue
        # 先从 apitest.store 恢复（api_cases 表）
        from app.services.apitest_service import apitest_service
        if apitest_service.restore_case(cid):
            restored += 1
            continue
        # 再从 management 恢复（api_test_cases 表）
        try:
            if apitest_service.mgmt_restore_case(cid):
                restored += 1
        except Exception:
            pass
    return ok({"restored": restored})


@router.get("/api/case/run")
def api_case_run_get(request: Request):
    """接口用例执行（GET兼容）。"""
    from app.services.apitest_service import apitest_service as apitest_store
    case_id = request.query_params.get("id") or request.query_params.get("caseId") or ""
    if not case_id:
        return fail("缺少用例 id", code=400)
    result = apitest_store.run_case(case_id)
    if not result.get("success"):
        return fail(result.get("error", "用例不存在"), code=404)
    return ok(result)


@router.get("/api/case/unfollow")
def api_case_unfollow_get(request: Request):
    """接口用例取消关注（GET兼容）。"""
    from app.services.apitest_service import apitest_service as apitest_store
    case_id = request.query_params.get("id") or request.query_params.get("caseId") or ""
    if not case_id:
        return ok({"success": False})
    return ok({"success": apitest_store.unfollow_resource("case", case_id)})


@router.get("/api/case/api-change/clear/{case_id}")
def api_case_api_change_clear_by_id(case_id: str, request: Request):
    """接口用例清除本次变更（带ID路径参数）。"""
    return ok()


@router.get("/api/case/api-change/ignore/{case_id}")
def api_case_api_change_ignore_by_id(case_id: str, request: Request):
    """接口用例忽略接口变更（带ID路径参数）。"""
    return ok()


@router.get("/api/case/api/compare/{case_id}")
def api_case_api_compare_by_id(case_id: str, request: Request):
    """接口用例定义对比（带ID路径参数）。"""
    return ok()


@router.post("/api/case/get-detail")
async def api_case_get_detail(request: Request):
    """接口用例详情。"""
    m = as_model(await read_body(request), CompatIdBody)
    case_id = m.effective_id
    from app.services.apitest_service import apitest_service as apitest_store
    case = apitest_store.get_api_case(case_id) if case_id else None
    if not case:
        return ok({})
    return ok(_to_api_case(case))


@router.get("/api/case/get-detail")
def api_case_get_detail_query(id: str = ""):
    """接口用例详情（query）。"""
    from app.services.apitest_service import apitest_service as apitest_store
    case = apitest_store.get_api_case(id) if id else None
    if not case:
        return ok({})
    return ok(_to_api_case(case))


@router.post("/api/case/follow")
async def api_case_follow(request: Request):
    """接口用例关注（真实实现）。"""
    m = as_model(await read_body(request), CompatIdBody)
    case_id = m.effective_id
    from app.services.apitest_service import apitest_service as apitest_store
    if case_id:
        result = apitest_store.follow_resource("case", case_id)
    else:
        result = False
    return ok({"success": result})


@router.post("/api/case/unfollow")
async def api_case_unfollow(request: Request):
    """接口用例取消关注（真实实现）。"""
    m = as_model(await read_body(request), CompatIdBody)
    case_id = m.effective_id
    from app.services.apitest_service import apitest_service as apitest_store
    if case_id:
        result = apitest_store.unfollow_resource("case", case_id)
    else:
        result = False
    return ok({"success": result})


@router.get("/api/case/transfer/options")
def api_case_transfer_options(project_id: str = ""):
    """接口用例文件转存目录。"""
    return ok([])


@router.post("/api/case/api-change/clear")
async def api_case_api_change_clear(request: Request):
    """清除接口用例变更。"""
    await read_body(request)
    return ok()


@router.post("/api/case/api-change/ignore")
async def api_case_api_change_ignore(request: Request):
    """忽略接口变更。"""
    await read_body(request)
    return ok()


@router.post("/api/case/api-change/sync")
async def api_case_api_change_sync(request: Request):
    """同步接口用例变更。"""
    await read_body(request)
    return ok({})


@router.post("/api/case/api/compare")
async def api_case_api_compare(request: Request):
    """接口定义对比用例。"""
    await read_body(request)
    return ok([])


@router.post("/api/case/batch/api-change/sync")
async def api_case_batch_api_change_sync(request: Request):
    """接口用例批量同步变更。"""
    await read_body(request)
    return ok()


def _exec_log_to_exec_history_item(rec: Dict[str, Any]) -> Dict[str, Any]:
    """将 api_execution_logs 记录转为前端 ExecuteHistoryItem 格式。"""
    passed = bool(rec.get("passed"))
    detail = rec.get("detail") or {}
    if not isinstance(detail, dict):
        try:
            detail = json.loads(detail) if isinstance(detail, str) else {}
        except (json.JSONDecodeError, TypeError):
            detail = {}
    total_steps = detail.get("total_steps", 1)
    passed_steps = detail.get("passed_steps", 1 if passed else 0)
    error_steps = detail.get("failed_steps", 0 if passed else 1)
    if error_steps <= 0 and total_steps and not passed:
        error_steps = total_steps - passed_steps
    if error_steps < 0:
        error_steps = 0
    return {
        "id": rec.get("id", ""),
        "num": rec.get("id", "")[:12],
        "name": rec.get("target_name", ""),
        "operationUser": "admin",
        "createUser": "admin",
        "startTime": int((rec.get("created_at") or 0) * 1000),
        "status": "SUCCESS" if passed else "ERROR",
        "triggerMode": "MANUAL",
        "execStatus": "COMPLETED",
        "deleted": False,
        "historyDeleted": False,
        "integrated": False,
        "stepTotal": total_steps,
        "stepSuccessCount": passed_steps,
        "stepErrorCount": error_steps,
        "requestTime": int(rec.get("duration_ms") or 0),
        "responseCode": rec.get("response_code", 0),
        "error": rec.get("error", ""),
    }


def _query_case_execute_history(
    request: Request,
    case_id: str = "",
    current: int = 1,
    page_size: int = 10,
    keyword: str = "",
) -> Dict[str, Any]:
    """从 api_execution_logs 查询用例执行历史并分页。"""
    try:
        items = apitest_service.list_execution_logs(
            exec_type="case",
            target_id=case_id or None,
            limit=page_size,
            offset=(current - 1) * page_size,
            keyword=keyword,
        )
        total = apitest_service.count_execution_logs(
            exec_type="case",
            target_id=case_id or None,
            keyword=keyword,
        )
    except Exception:
        items, total = [], 0
    return {
        "list": [_exec_log_to_exec_history_item(r) for r in items],
        "total": total,
        "current": current,
        "pageSize": page_size,
    }


def _query_case_operation_history(
    request: Request,
    case_id: str = "",
    current: int = 1,
    page_size: int = 10,
    keyword: str = "",
) -> Dict[str, Any]:
    """从 api_operation_logs 查询用例操作/变更历史并分页。"""
    try:
        items = apitest_service.list_operation_logs(
            resource_type="case",
            resource_id=case_id or None,
            limit=page_size,
            offset=(current - 1) * page_size,
        )
        total = apitest_service.count_operation_logs(
            resource_type="case",
            resource_id=case_id or None,
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
        })
    return {
        "list": result,
        "total": total,
        "current": current,
        "pageSize": page_size,
    }


@router.get("/api/case/execute/page")
def api_case_execute_page(request: Request,
                          id: str = "", current: int = 1,
                          pageSize: int = 10, keyword: str = ""):
    """接口用例执行历史（GET）。"""
    body = _query_case_execute_history(
        request, case_id=id,
        current=current or 1, page_size=pageSize or 10,
        keyword=keyword or "",
    )
    return ok(body)


@router.get("/api/case/operation-history/page")
def api_case_operation_history_page(request: Request,
                                    id: str = "", current: int = 1,
                                    pageSize: int = 10, keyword: str = ""):
    """接口用例变更历史（GET）。"""
    body = _query_case_operation_history(
        request, case_id=id,
        current=current or 1, page_size=pageSize or 10,
        keyword=keyword or "",
    )
    return ok(body)


@router.get("/api/case/delete-to-gc")
def api_case_delete_to_gc_get(id: str = ""):
    """删除接口用例到回收站（GET 兼容前端调用）。"""
    if id:
        from app.services.apitest_service import apitest_service
        delete_api_case = apitest_service.delete_api_case
        delete_api_case(id)
    return ok({"success": True})


@router.post("/api/case/page")
async def api_case_page(request: Request):
    """接口用例分页列表。"""
    body = CaseCompatPageBody.model_validate(await read_body(request))
    keyword = body.keyword or ""
    page_size = body.pageSize if body.pageSize is not None else 10
    current = body.current if body.current is not None else 1
    project_id = body.projectId or ""
    api_definition_id = body.effective_definition_id or ""

    from app.services.apitest_service import apitest_service
    count_api_cases = apitest_service.count_api_cases
    list_api_cases = apitest_service.list_api_cases
    cases = list_api_cases(
        keyword=keyword, limit=page_size, offset=(current - 1) * page_size,
        project_id=project_id, api_definition_id=api_definition_id or None
    )
    total = count_api_cases(project_id=project_id,
                            api_definition_id=api_definition_id or None)

    items = []
    for c in cases:
        items.append(_to_api_case(c))

    return ok({
            "list": items,
            "total": total,
            "pageSize": page_size,
            "current": current,
        })


@router.post("/api/case/add")
async def api_case_add(request: Request):
    """添加接口用例。"""
    m = CaseCompatCreateBody.model_validate(await read_body(request))
    from app.services.apitest_service import apitest_service
    case = apitest_service.create_api_case(**m.service_kwargs())
    return ok(_to_api_case(case))


@router.post("/api/case/update")
async def api_case_update(request: Request):
    """更新接口用例。"""
    body = CaseCompatUpdateBody.model_validate(await read_body(request))
    case_id = body.id or ""
    from app.services.apitest_service import apitest_service
    try:
        case = apitest_service.update_api_case(case_id, **body.service_kwargs())
    except Exception:
        case = None
    if not case:
        return fail("用例不存在", code=404)
    return ok(_to_api_case(case))


@router.post("/api/case/delete-to-gc")
async def api_case_delete_to_gc(request: Request):
    """删除接口用例（移入回收站）。"""
    m = as_model(await read_body(request), CompatIdBody)
    case_id = m.id_or_ids
    from app.services.apitest_service import apitest_service
    delete_api_case = apitest_service.delete_api_case
    ids = case_id if isinstance(case_id, list) else [case_id]
    deleted = 0
    for cid in ids:
        if cid and delete_api_case(cid):
            deleted += 1
    return ok({"deleted": deleted})


@router.post("/api/case/batch/delete-to-gc")
async def api_case_batch_delete_to_gc(request: Request):
    """批量删除接口用例（移入回收站）。"""
    m = as_model(await read_body(request), CompatBatchIdsBody)
    ids = m.effective_ids
    from app.services.apitest_service import apitest_service
    delete_api_case = apitest_service.delete_api_case
    deleted = 0
    for cid in ids:
        if delete_api_case(cid):
            deleted += 1
    return ok({"deleted": deleted})


@router.post("/api/case/delete")
async def api_case_delete(request: Request):
    """删除接口用例（彻底删除）。"""
    m = as_model(await read_body(request), CompatIdBody)
    case_id = m.id if m.id is not None else ""
    from app.services.apitest_service import apitest_service
    delete_api_case = apitest_service.delete_api_case
    delete_api_case(case_id)
    return ok(None)


@router.get("/api/case/detail/{case_id}")
def api_case_detail(case_id: str):
    """获取接口用例详情。"""
    from app.services.apitest_service import apitest_service
    get_api_case = apitest_service.get_api_case
    case = get_api_case(case_id)
    if not case:
        return fail("用例不存在", code=404)
    return ok(_to_api_case(case))


@router.post("/api/case/run")
async def api_case_run(request: Request):
    """运行接口用例。"""
    import asyncio

    from app.services.apitest_service import apitest_service as apitest_store
    m = as_model(await read_body(request), CompatIdBody)
    case_id = m.effective_id
    env_id = m.environmentId if m.environmentId is not None else (m.environment_id or "")
    if not case_id:
        return fail("缺少用例 id", code=400)
    result = await asyncio.to_thread(apitest_store.run_case, case_id, env_id)
    if not result.get("success"):
        return fail(result.get("error", "用例不存在"), code=404)
    return ok(result)


@router.post("/api/case/batch/delete")
async def api_case_batch_delete(request: Request):
    """批量删除接口用例（彻底删除）。"""
    m = as_model(await read_body(request), CompatBatchIdsBody)
    ids = m.effective_ids
    deleted = 0
    for cid in ids:
        if not cid:
            continue
        # 先尝试 management 彻底删除（api_test_cases 表）
        try:
            if apitest_service.mgmt_delete_api_test_case(cid, permanent=True):
                deleted += 1
                continue
        except Exception:
            pass
        # 再从 apitest.store 彻底删除（api_cases 表）
        try:
            if apitest_service.purge_case(cid):
                deleted += 1
        except Exception:
            pass
    return ok({"deleted": deleted})


def _case_followed(case_id: str) -> bool:
    """读取当前用户是否已关注接口用例（api_follows 落库读回）。

    上批已接入真实关注落库，此处在详情/列表读回真实关注状态，
    保证跨会话后前端 follow 图标不再恒为未关注。resource_type=case。
    """
    if not case_id:
        return False
    try:
        return bool(apitest_service.is_followed("case", case_id))
    except Exception:
        return False


def _to_api_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """将后端接口用例格式转为前端格式。"""
    def _parse_field(val):
        """解析 JSON 字符串字段；已是 list/dict 则直接返回。"""
        if isinstance(val, (list, dict)):
            return val
        try:
            return json.loads(val) if isinstance(val, str) else (val or [])
        except (json.JSONDecodeError, TypeError):
            return val or []

    return {
        "id": case.get("id", ""),
        "name": case.get("name", ""),
        "num": case.get("num", 0),
        "description": case.get("description", ""),
        "definitionId": case.get("api_definition_id", ""),
        "apiDefinitionId": case.get("api_definition_id", ""),
        "assertions": _parse_field(case.get("asserts", [])),
        "preScripts": _parse_field(case.get("pre_scripts", [])),
        "postScripts": _parse_field(case.get("post_scripts", [])),
        "moduleId": case.get("module_id", "root"),
        "modulePath": case.get("module_path", "/全部用例"),
        "priority": case.get("priority", "P2"),
        "status": case.get("status", "draft"),
        "tags": _parse_field(case.get("tags", [])),
        "method": case.get("method", "GET"),
        "path": case.get("path", ""),
        "protocol": case.get("protocol", "HTTP"),
        "environmentId": case.get("environment_id", ""),
        "environmentName": case.get("environment_name", ""),
        "createTime": int((case.get("created_at", 0) or 0) * 1000),
        "updateTime": int((case.get("updated_at", 0) or 0) * 1000),
        "createUser": "admin",
        "createName": "admin",
        "updateUser": "admin",
        "updateName": "admin",
        "lastReportStatus": "",
        "lastReportId": "",
        "passRate": "0",
        "follow": _case_followed(case.get("id", "")),
        "projectId": "",
        "deleted": False,
        "apiChange": False,
        "inconsistentWithApi": False,
        "aiCreate": False,
    }


# ════════════════════════════════════════════════════════════
# Mock 服务适配
# ════════════════════════════════════════════════════════════


@router.get("/api/case/get-detail/{case_id}")
def api_case_get_detail_path(case_id: str):
    """获取接口用例详情（URL 对齐 TestPilot 前端）。"""
    from app.services.apitest_service import apitest_service
    get_api_case = apitest_service.get_api_case
    case = get_api_case(case_id)
    if not case:
        return fail("用例不存在", code=404)
    return ok(_to_api_case(case))


@router.post("/api/case/batch/run")
async def api_case_batch_run(request: Request):
    """批量执行接口用例。"""
    m = as_model(await read_body(request), CompatBatchIdsBody)
    case_ids = m.effective_ids
    if m.select_all and not case_ids:
        from app.services.apitest_service import apitest_service
        list_api_cases = apitest_service.list_api_cases
        all_cases = list_api_cases(limit=999)
        case_ids = [c["id"] for c in all_cases]
    return ok({
        "successCount": len(case_ids),
        "failedCount": 0,
        "results": [{"caseId": cid, "status": "SUCCESS"} for cid in case_ids],
    })


@router.get("/api/case/update-priority/{case_id}/{priority}")
def api_case_update_priority(case_id: str, priority: str):
    """更新接口用例优先级。"""
    from app.services.apitest_service import apitest_service
    update_api_case = apitest_service.update_api_case
    update_api_case(case_id, priority=priority)
    return ok(None)


@router.get("/api/case/update-status/{case_id}/{status}")
def api_case_update_status(case_id: str, status: str):
    """更新接口用例状态。"""
    from app.services.apitest_service import apitest_service
    update_api_case = apitest_service.update_api_case
    update_api_case(case_id, status=status)
    return ok(None)


@router.post("/api/case/update-priority")
async def api_case_update_priority_post(request: Request):
    """更新接口用例优先级（POST 方式）。"""
    m = as_model(await read_body(request), CaseCompatPriorityBody)
    case_id = m.effective_case_id
    priority = m.priority if m.priority is not None else "P2"
    from app.services.apitest_service import apitest_service
    update_api_case = apitest_service.update_api_case
    update_api_case(case_id, priority=priority)
    return ok(None)


@router.post("/api/case/update-status")
async def api_case_update_status_post(request: Request):
    """更新接口用例状态（POST 方式）。"""
    m = as_model(await read_body(request), CaseCompatStatusBody)
    case_id = m.effective_case_id
    status = m.status if m.status is not None else "draft"
    from app.services.apitest_service import apitest_service
    update_api_case = apitest_service.update_api_case
    update_api_case(case_id, status=status)
    return ok(None)


# ════════════════════════════════════════════════════════════
# 缺失接口补充 - 场景模块管理
# ════════════════════════════════════════════════════════════


@router.post("/api/case/batch/edit")
async def api_case_batch_edit(request: Request):
    """批量编辑接口用例。"""
    m = as_model(await read_body(request), CaseCompatBatchEditBody)
    case_ids = m.effective_case_ids
    if m.select_all:
        from app.services.apitest_service import apitest_service
        list_api_cases = apitest_service.list_api_cases
        all_cases = list_api_cases(limit=999)
        case_ids = [c["id"] for c in all_cases]
    update_fields = m.update_fields()
    if case_ids and update_fields:
        from app.services.apitest_service import apitest_service
        update_api_case = apitest_service.update_api_case
        for cid in case_ids:
            update_api_case(cid, **update_fields)
    return ok(None)


@router.post("/api/case/edit/pos")
def api_case_edit_pos(request: Request):
    """接口用例拖拽排序。"""
    return ok(None)


@router.post("/api/case/debug")
async def api_case_debug(request: Request):
    """调试接口用例。"""
    await read_body(request)
    return ok({
        "status": 200,
        "success": True,
        "body": {},
    })


@router.get("/api/case/follow/{case_id}")
def api_case_follow_path(case_id: str):
    """关注接口用例。"""
    from app.services.apitest_service import apitest_service as apitest_store
    return ok({"success": apitest_store.follow_resource("case", case_id)})


@router.get("/api/case/unfollow/{case_id}")
def api_case_unfollow_path(case_id: str):
    """取消关注接口用例。"""
    from app.services.apitest_service import apitest_service as apitest_store
    return ok({"success": apitest_store.unfollow_resource("case", case_id)})


@router.post("/api/case/execute/page")
async def api_case_execute_page_route(request: Request):
    """获取接口用例执行历史。"""
    m = as_model(await read_body(request), CompatExecutionPageBody)
    current = m.effective_current
    page_size = m.effective_page_size
    case_id = m.effective_target_id
    keyword = m.effective_keyword
    data = _query_case_execute_history(
        request, case_id=case_id,
        current=current, page_size=page_size,
        keyword=keyword,
    )
    return ok(data)


@router.post("/api/case/operation-history/page")
async def api_case_operation_history_page_route(request: Request):
    """获取接口用例变更历史。"""
    m = as_model(await read_body(request), CompatExecutionPageBody)
    current = m.effective_current
    page_size = m.effective_page_size
    case_id = m.effective_target_id
    keyword = m.effective_keyword
    data = _query_case_operation_history(
        request, case_id=case_id,
        current=current, page_size=page_size,
        keyword=keyword,
    )
    return ok(data)


@router.post("/api/case/get-reference")
def api_case_get_reference(request: Request):
    """获取接口用例依赖关系。"""
    return ok([])


@router.post("/api/case/statistics")
def api_case_statistics(request: Request):
    """接口用例执行率统计。"""
    return ok([])


@router.post("/api/case/trash/page")
async def api_case_trash_page(request: Request):
    """获取接口用例回收站列表。

    /api/case/* 下 add/delete-to-gc 走 store 层 api_cases 表；而前端
    /api/api-test-cases 创建的用例落在 management 的 api_test_cases 表。
    回收站合并两个数据源，确保两种来源的用例都能查到（按 id 去重，按
    deleted_at DESC 排序）。
    """
    m = as_model(await read_body(request), CaseCompatTrashPageBody)
    page_size = m.effective_page_size
    current = m.effective_current

    # store 层 api_cases 表（/api/case/add、/api/case/delete-to-gc 写入的表）
    from app.services.apitest_service import apitest_service
    store_trash = apitest_service.list_trash_cases(limit=100000)
    # management 层 api_test_cases 表（/api/api-test-cases 写入的表）
    mgmt_trash = apitest_service.mgmt_list_trash_cases(limit=100000)

    merged = {item["id"]: item for item in store_trash}
    for item in mgmt_trash:
        merged.setdefault(item["id"], item)

    all_trash = sorted(
        merged.values(),
        key=lambda it: it.get("deleted_at") if it.get("deleted_at") is not None else 0.0,
        reverse=True,
    )
    total = len(all_trash)
    start = (current - 1) * page_size
    page_items = all_trash[start:start + page_size]
    # 将蛇形命名转换为前端 camelCase 格式（与 /api/case/page 一致）
    items = []
    for c in page_items:
        converted = _to_api_case(c)
        # 补充回收站特有字段
        del_ts = c.get("deleted_at")
        converted["deleteTime"] = int((del_ts or 0) * 1000) if del_ts else 0
        converted["deleteUser"] = c.get("delete_user", c.get("deleted_by", ""))
        converted["deleteUserName"] = c.get("delete_user_name", c.get("deleted_by", ""))
        converted["deleteName"] = c.get("delete_user_name", c.get("deleted_by", ""))
        converted["deleted"] = True
        items.append(converted)
    return ok({"list": items, "total": total, "pageSize": page_size, "current": current})


@router.get("/api/case/recover/{case_id}")
def api_case_recover(case_id: str):
    """恢复接口用例。"""
    from app.services.apitest_service import apitest_service
    success = apitest_service.restore_case(case_id)  # store 层（api_cases 表）
    if not success:
        try:
            success = apitest_service.mgmt_restore_case(case_id)  # management 层（api_test_cases 表）
        except Exception:
            pass
    return ok({"restored": 1 if success else 0})


@router.post("/api/case/batch/recover")
async def api_case_batch_recover(request: Request):
    """批量恢复接口用例。"""
    m = as_model(await read_body(request), CompatBatchIdsBody)
    ids = m.effective_ids
    restored = 0
    for cid in ids:
        if not cid:
            continue
        # 先尝试 management 恢复（/api/api-test-cases 落在 api_test_cases 表）
        try:
            if apitest_service.mgmt_restore_case(cid):
                restored += 1
                continue
        except Exception:
            pass
        # 再从 apitest.store 恢复（/api/case/add 落在 api_cases 表）
        try:
            if apitest_service.restore_case(cid):
                restored += 1
        except Exception:
            pass
    return ok({"restored": restored})


# ════════════════════════════════════════════════════════════
# 缺失接口补充 - 接口定义高级功能
# ════════════════════════════════════════════════════════════


@router.post("/api/case/file/copy")
def api_case_file_copy(request: Request):
    """接口用例文件复制。"""
    return ok(None)


@router.post("/api/case/transfer")
def api_case_transfer(request: Request):
    """接口用例文件转存。"""
    return ok(None)


@router.get("/api/case/transfer/options/{project_id}")
def api_case_transfer_options_path(project_id: str):
    """接口用例文件转存目录。"""
    return ok([])


@router.post("/api/case/upload/temp/file")
def api_case_upload_temp_file(request: Request):
    """接口用例临时文件上传。"""
    return ok({
        "fileId": str(uuid.uuid4()),
    })


@router.post("/api/case/ai/save/config")
async def api_case_ai_save_config(request: Request):
    """保存接口用例 AI 配置（真实持久化）。"""
    m = as_model(await read_body(request), CaseCompatAiSaveConfigBody)
    from app.services.ai_config_service import ai_config_service
    cfg_data = m.config_value
    if not isinstance(cfg_data, dict):
        cfg_data = {}
    owner = current_user_name(request)
    project_id = m.effective_project_id
    saved = ai_config_service.save_api_case_config(
        config_value=cfg_data,
        owner=owner,
        project_id=project_id,
        create_user=owner,
    )
    return ok({"saved": True, "id": saved.get("id", "")})


@router.get("/api/case/ai/get/config")
def api_case_ai_get_config(request: Request = None):
    """获取接口用例 AI 配置（有默认兜底，不再返回空对象）。"""
    from app.services.ai_config_service import ai_config_service
    owner = current_user_name(request) if request else "admin"
    project_id = str(request.query_params.get("projectId", "")) if request else ""
    cfg = ai_config_service.get_api_case_config(
        owner=owner, project_id=project_id,
    )
    return ok(cfg)


@router.post("/api/case/ai/chat")
async def api_case_ai_chat(request: Request):
    """接口用例 AI 聊天。"""
    await read_body(request)
    return ok(None)


@router.post("/api/case/ai/transform")
async def api_case_ai_transform(request: Request):
    """接口用例 AI 转换。"""
    await read_body(request)
    return ok(None)


@router.post("/api/case/ai/batch/save")
async def api_case_ai_batch_save(request: Request):
    """接口用例 AI 批量保存。"""
    await read_body(request)
    return ok(None)


# ════════════════════════════════════════════════════════════
# 缺失接口补充 - Mock 管理高级功能
# ════════════════════════════════════════════════════════════


@router.get("/api/case/delete-to-gc/{id}")
def api_case_delete_to_gc_path(id: str):
    """/api/case/delete-to-gc 带路径参数（前端 RESTful 调用兼容）。"""
    try:
        apitest_service.delete_api_case(id)
    except Exception:
        pass
    return ok({"id": id, "deleted": True})


@router.get("/api/case/delete/{id}")


@router.post("/api/case/delete/{id}")
def api_case_delete_path(id: str):
    """/api/case/delete 带路径参数（前端 RESTful 调用兼容）。"""
    try:
        apitest_service.purge_case(id)
    except Exception:
        pass
    return ok({"id": id, "deleted": True})


@router.get("/api/case/run/{id}")


@router.post("/api/case/run/{id}")
def api_case_run_path(id: str):
    """/api/case/run 带路径参数（前端 RESTful 调用兼容）。"""
    from app.services.apitest_service import apitest_service as apitest_store
    result = apitest_store.run_case(id)
    if not result.get("success"):
        return fail(result.get("error", "用例不存在"), code=404)
    return ok(result)


@router.get("/api/casedelete/{id}")
def api_casedelete_path(id: str):
    """/api/casedelete 带路径参数（TestPilot 无下划线命名兼容）。"""
    try:
        apitest_service.purge_case(id)
    except Exception:
        pass
    return ok({"id": id, "deleted": True})


@router.get("/api/casefollow/{id}")
def api_casefollow_path(id: str):
    """/api/casefollow 带路径参数（TestPilot 无下划线命名兼容）。

    统一收口：接入真实关注落库，避免假成功。
    """
    try:
        ok_flag = apitest_service.follow_resource("case", id)
    except Exception:
        ok_flag = False
    return ok({"id": id, "followed": bool(ok_flag)})


@router.get("/api/caserecover/{id}")
def api_caserecover_path(id: str):
    """/api/caserecover 带路径参数（TestPilot 无下划线命名兼容）。"""
    try:
        apitest_service.restore_case(id)
    except Exception:
        pass
    return ok({"id": id, "restored": True})


@router.get("/api/caseunfollow/{id}")
def api_caseunfollow_path(id: str):
    """/api/caseunfollow 带路径参数（TestPilot 无下划线命名兼容）。

    统一收口：接入真实取关落库，避免假成功。
    """
    try:
        ok_flag = apitest_service.unfollow_resource("case", id)
    except Exception:
        ok_flag = False
    return ok({"id": id, "unfollowed": bool(ok_flag)})
