# app/routers/frontend.py
"""前端 API 测试页面路由（Phase 3 重构：从 main.py 拆分）。"""
import asyncio
import json

from fastapi import APIRouter, Request

from app.core.helpers import definition_followed
from app.core.response import fail, ok, read_body, read_writable_body
from app.services.apitest_service import apitest_service
from app.services.frontend_api_service import frontend_api_service

router = APIRouter(tags=["frontend"])


def _parse_json_field(val, default=None):
    """解析 JSON 字符串字段；已是 dict/list 则直接返回。"""
    if isinstance(val, (dict, list)):
        return val
    if val is None:
        return default if default is not None else {}
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


def _scenario_to_frontend(s: dict) -> dict:
    """将回收站场景原始数据转换为前端 camelCase 格式。"""
    steps = s.get("steps", [])
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except (json.JSONDecodeError, TypeError):
            steps = []
    del_ts = s.get("deleted_at")
    return {
        "id": s.get("id", ""),
        "name": s.get("name", ""),
        "num": s.get("num", 0),
        "description": s.get("description", ""),
        "steps": steps,
        "moduleId": s.get("module_id", "root"),
        "modulePath": s.get("module_path", "/全部场景"),
        "priority": s.get("priority", "P2"),
        "status": s.get("status", "draft"),
        "createTime": int((s.get("created_at", 0) or 0) * 1000),
        "updateTime": int((s.get("updated_at", 0) or 0) * 1000),
        "createUser": s.get("created_by", s.get("create_user", "admin")),
        "createUserName": s.get("create_user_name", s.get("created_by", "admin")),
        "createName": s.get("created_by", "admin"),
        "updateUser": s.get("updated_by", s.get("update_user", "admin")),
        "updateUserName": s.get("update_user_name", s.get("updated_by", "admin")),
        "updateName": s.get("updated_by", "admin"),
        "deleted": True,
        "deleteTime": int((del_ts or 0) * 1000) if del_ts else 0,
        "deleteUser": s.get("delete_user", s.get("deleted_by", "")),
        "deleteUserName": s.get("delete_user_name", s.get("deleted_by", "")),
        "lastReportStatus": "",
        "lastReportId": "",
        "tags": [],
        "environmentName": "",
        "stepTotal": len(steps) if isinstance(steps, list) else 0,
        "requestPassRate": "",
    }


@router.post("/api/api-definitions/import")
async def front_api_import_definitions(req: Request):
    """前端导入接口定义 Postman/Swagger。"""
    body = await read_body(req)
    fmt = body.get("format", "auto")
    data = body.get("data", body)
    if fmt in ("postman", "auto"):
        result = await asyncio.to_thread(frontend_api_service.import_from_postman, data)
        if result.get("imported", 0) > 0:
            return ok(result)
    if fmt in ("swagger", "auto"):
        result = await asyncio.to_thread(frontend_api_service.import_from_swagger, data)
        return ok(result)
    return ok({"imported": 0, "errors": ["无法识别导入格式"]})


@router.get("/api/api-definitions")
def front_api_list_definitions(
    search: str = "", method: str = "", protocol: str = "", limit: int = 100,
):
    """前端接口定义列表。"""
    defs = frontend_api_service.list_api_definitions(search=search, method=method, protocol=protocol, limit=limit)
    return ok({"definitions": defs})


@router.post("/api/api-definitions")
async def front_api_create_definition(req: Request):
    """前端创建接口定义。"""
    body = await read_body(req)
    item = frontend_api_service.create_api_definition(
        name=body.get("name", "未命名接口定义"), method=body.get("method", "GET"),
        path=body.get("path", ""), protocol=body.get("protocol", "HTTP"),
        description=body.get("description", ""),
        request_headers=body.get("request_headers"),
        request_params=body.get("request_params"),
        request_body=body.get("request_body", ""),
        request_body_type=body.get("request_body_type", "json"),
        response_code=body.get("response_code", "200"),
        response_headers=body.get("response_headers"),
        response_body=body.get("response_body", ""),
        response_body_type=body.get("response_body_type", "json"),
        tags=body.get("tags"),
    )
    return ok(item)


@router.get("/api/api-definitions/{definition_id}")
def front_api_get_definition(definition_id: str):
    """前端获取接口定义详情。"""
    item = frontend_api_service.get_api_definition(definition_id)
    if not item:
        return fail("接口定义不存在", 404)
    return ok(item)


@router.put("/api/api-definitions/{definition_id}")
async def front_api_update_definition(definition_id: str, req: Request):
    """前端更新接口定义。"""
    body = await read_writable_body(req)
    item = frontend_api_service.update_api_definition(definition_id, **body)
    if not item:
        return fail("接口定义不存在", 404)
    return ok(item)


@router.delete("/api/api-definitions/{definition_id}")
def front_api_delete_definition(definition_id: str):
    """前端删除接口定义。"""
    result = frontend_api_service.delete_api_definition(definition_id)
    if not result:
        return fail("接口定义不存在", 404)
    return ok({"success": True})


# ── 接口用例管理（前端）───────────────────────────────────
@router.get("/api/api-test-cases")
def front_api_list_test_cases(search: str = "", limit: int = 100):
    """前端接口用例列表。"""
    cases = frontend_api_service.list_api_test_cases(search=search, limit=limit)
    return ok({"cases": cases})


@router.post("/api/api-test-cases")
async def front_api_create_test_case(req: Request):
    """前端创建接口用例。"""
    body = await read_body(req)
    item = frontend_api_service.create_api_test_case(
        name=body.get("name", "未命名接口用例"),
        definition_id=body.get("definition_id", ""),
        method=body.get("method", "GET"),
        path=body.get("path", ""),
        request_headers=body.get("request_headers"),
        request_params=body.get("request_params"),
        request_body=body.get("request_body", ""),
        request_body_type=body.get("request_body_type", "json"),
        assertions=body.get("assertions", []),
        pre_scripts=body.get("pre_scripts", []),
        post_scripts=body.get("post_scripts", []),
        pre_sql=body.get("pre_sql", ""),
        post_sql=body.get("post_sql", ""),
        variables=body.get("variables"),
        environment_id=body.get("environment_id"),
        timeout=body.get("timeout", 30),
        retry_count=body.get("retry_count", 0),
    )
    return ok(item)


@router.get("/api/api-test-cases/{case_id}")
def front_api_get_test_case(case_id: str):
    """前端获取接口用例。"""
    item = frontend_api_service.get_api_test_case(case_id)
    if not item:
        return fail("接口用例不存在", 404)
    return ok(item)


@router.put("/api/api-test-cases/{case_id}")
async def front_api_update_test_case(case_id: str, req: Request):
    """前端更新接口用例。"""
    body = await read_writable_body(req)
    item = frontend_api_service.update_api_test_case(case_id, **body)
    if not item:
        return fail("接口用例不存在", 404)
    return ok(item)


@router.delete("/api/api-test-cases/{case_id}")
def front_api_delete_test_case(case_id: str):
    """前端删除接口用例。"""
    result = frontend_api_service.delete_api_test_case(case_id)
    if not result:
        return fail("接口用例不存在", 404)
    return ok({"success": True})


# ── 场景管理（前端）───────────────────────────────────────
@router.get("/api/scenarios")
def front_api_list_scenarios(limit: int = 100):
    """前端场景列表。"""
    scenarios = frontend_api_service.list_scenarios(limit=limit)
    return ok({"scenarios": scenarios})


@router.post("/api/scenarios")
async def front_api_create_scenario(req: Request):
    """前端创建场景。"""
    body = await read_body(req)
    item = frontend_api_service.create_scenario(
        name=body.get("name", "未命名场景"),
        steps=body.get("steps", []),
        description=body.get("description", ""),
        environment_id=body.get("environment_id"),
    )
    return ok(item)


@router.post("/api/scenarios/{scenario_id}/execute")
def front_api_execute_scenario(scenario_id: str):
    """前端执行场景。"""
    result = frontend_api_service.execute_scenario(scenario_id)
    return ok(result)


@router.get("/api/scenarios/{scenario_id}")
def front_api_get_scenario(scenario_id: str):
    """前端获取场景。"""
    item = frontend_api_service.get_scenario(scenario_id)
    if not item:
        return fail("场景不存在", 404)
    return ok(item)


@router.put("/api/scenarios/{scenario_id}")
async def front_api_update_scenario(scenario_id: str, req: Request):
    """前端更新场景。"""
    body = await read_writable_body(req)
    item = frontend_api_service.update_scenario(scenario_id, **body)
    if not item:
        return fail("场景不存在", 404)
    return ok(item)


@router.delete("/api/scenarios/{scenario_id}")
def front_api_delete_scenario(scenario_id: str):
    """前端删除场景。"""
    result = frontend_api_service.delete_scenario(scenario_id)
    if not result:
        return fail("场景不存在", 404)
    return ok({"success": True})


# ── Mock 服务管理（前端）──────────────────────────────────
@router.get("/api/mock-services")
def front_api_list_mock_services(limit: int = 100):
    """前端 Mock 服务列表。"""
    mocks = frontend_api_service.list_mock_services(limit=limit)
    return ok({"mocks": mocks})


@router.post("/api/mock-services")
async def front_api_create_mock_service(req: Request):
    """前端创建 Mock 服务。"""
    body = await read_body(req)
    item = frontend_api_service.create_mock_service(
        name=body.get("name", "未命名Mock服务"),
        method=body.get("method", "GET"),
        path=body.get("path", ""),
        response_code=body.get("response_code", 200),
        response_headers=body.get("response_headers"),
        response_body=body.get("response_body", ""),
        delay_ms=body.get("delay_ms", 0),
    )
    return ok(item)


@router.get("/api/mock-services/{mock_id}")
def front_api_get_mock_service(mock_id: str):
    """前端获取 Mock 服务。"""
    item = frontend_api_service.get_mock_service(mock_id)
    if not item:
        return fail("Mock 服务不存在", 404)
    return ok(item)


@router.put("/api/mock-services/{mock_id}")
async def front_api_update_mock_service(mock_id: str, req: Request):
    """前端更新 Mock 服务。"""
    body = await read_writable_body(req)
    item = frontend_api_service.update_mock_service(mock_id, **body)
    if not item:
        return fail("Mock 服务不存在", 404)
    return ok(item)


@router.delete("/api/mock-services/{mock_id}")
def front_api_delete_mock_service(mock_id: str):
    """前端删除 Mock 服务。"""
    result = frontend_api_service.delete_mock_service(mock_id)
    if not result:
        return fail("Mock 服务不存在", 404)
    return ok({"success": True})


# ── 定义/用例回收站（前端）────────────────────────────────
@router.get("/api/definition/trash/page")
def front_api_definition_trash_page(
    keyword: str = "",
    pageSize: int = 10,
    current: int = 1,
):
    """接口定义回收站分页。"""
    # 取全部回收站数据再分页，保证 total 正确
    all_trash = frontend_api_service.list_trash_definitions(limit=100000)
    # 关键词过滤
    if keyword:
        k = keyword.lower()
        all_trash = [
            d for d in all_trash
            if k in (d.get("name", "") or "").lower()
            or k in (d.get("path", "") or "").lower()
        ]
    # 无关键词过滤时用 DB 真实总数；有关键词时用内存过滤结果
    total = len(all_trash) if keyword else apitest_service.count_trash_definitions()
    start = (current - 1) * pageSize
    page_items = all_trash[start:start + pageSize]
    # 转换为前端 camelCase 格式（与 _to_definition 输出一致）
    converted = []
    for d in page_items:
        del_ts = d.get("deleted_at")
        converted.append({
            "id": d.get("id", ""),
            "name": d.get("name", ""),
            "num": d.get("num", 0),
            "method": d.get("method", "GET"),
            "path": d.get("path", "/"),
            "protocol": d.get("protocol", "HTTP"),
            "description": d.get("description", ""),
            "status": d.get("status", "processing"),
            "requestBody": _parse_json_field(d.get("request_body", d.get("body", {}))),
            "responseBody": _parse_json_field(d.get("response_body", {})),
            "headers": _parse_json_field(d.get("request_headers", d.get("headers", {}))),
            "query": _parse_json_field(d.get("query", {})),
            "params": _parse_json_field(d.get("request_params", d.get("params", {}))),
            "tags": _parse_json_field(d.get("tags", []), []),
            "moduleId": d.get("module_id", "root"),
            "moduleName": d.get("module_name", "全部接口"),
            "modulePath": d.get("module_path", "/全部接口"),
            "caseTotal": d.get("case_total", 0),
            "casePassRate": "",
            "caseStatus": "",
            "projectId": d.get("project_id", ""),
            "pos": d.get("pos", 0),
            "latest": bool(d.get("latest", True)),
            "versionId": d.get("version_id", ""),
            "refId": d.get("ref_id", ""),
            "createTime": int((d.get("created_at", 0) or 0) * 1000),
            "createUser": d.get("created_by", d.get("create_user", "admin")),
            "createUserName": d.get("create_user_name", d.get("created_by", "admin")),
            "createName": d.get("created_by", "admin"),
            "updateTime": int((d.get("updated_at", 0) or 0) * 1000),
            "updateUser": d.get("updated_by", d.get("update_user", "admin")),
            "updateUserName": d.get("update_user_name", d.get("updated_by", "admin")),
            "updateName": d.get("updated_by", "admin"),
            "deleted": True,
            "deleteTime": int((del_ts or 0) * 1000) if del_ts else 0,
            "deleteUser": d.get("deleted_by", d.get("delete_user", "")),
            "deleteUserName": d.get("delete_user_name", d.get("deleted_by", "")),
            "versionName": "",
            "follow": definition_followed(d.get("id", "")),
            "customFields": [],
        })
    return ok({
        "list": converted,
        "total": total,
        "pageSize": pageSize,
        "current": current,
    })


@router.get("/api/definition/delete")
def front_api_definition_delete(id: str = ""):
    """接口定义彻底删除（回收站清空，GET 兼容）。

    前端 DeleteRecycleApiUrl=/api/definition/delete 语义为回收站中彻底删除。
    主列表软删请走 /api/definition/delete-to-gc。
    """
    result = frontend_api_service.delete_api_definition(id, permanent=True)
    return ok({"deleted": result})


@router.post("/api/definition/batch-delete")
async def front_api_definition_batch_delete(req: Request):
    """批量删除接口定义。"""
    body = await read_body(req)
    ids = body.get("ids", [])
    deleted = 0
    for iid in ids:
        if frontend_api_service.delete_api_definition(iid):
            deleted += 1
    return ok({"deleted": deleted})


@router.post("/api/case/recover")
async def front_api_case_recover(req: Request):
    """恢复接口用例。"""
    body = await read_body(req)
    case_id = body.get("id", "")
    # 先从 management 恢复（api_test_cases 表）
    result = frontend_api_service.restore_case(case_id)
    if not result:
        # 再从 store 恢复（api_cases 表）
        try:
            result = apitest_service.restore_case(case_id)
        except Exception:
            pass
    return ok({"restored": result})


@router.post("/api/scenario/trash/page")
async def front_api_scenario_trash_page(req: Request):
    """场景回收站分页。"""
    body = await read_body(req)
    page_size = body.get("pageSize", 10)
    current = body.get("current", 1)
    # 获取全部回收站数据（先不限制条数），再在内存中分页
    items = frontend_api_service.list_trash_scenarios(limit=100000)
    # 总数使用 DB 真实总数
    total = apitest_service.count_trash_scenarios()
    start = (current - 1) * page_size
    page_items = items[start:start + page_size]

    # 转换为前端 camelCase 格式（与 /api/scenario/page 输出一致）
    converted = []
    for s in page_items:
        converted.append(_scenario_to_frontend(s))
    return ok({
        "list": converted,
        "total": total,
        "pageSize": page_size,
        "current": current,
    })


@router.post("/api/scenario/recover")
async def front_api_scenario_recover(req: Request):
    """恢复场景。"""
    body = await read_body(req)
    scenario_id = body.get("id", "")
    result = frontend_api_service.restore_scenario(scenario_id)
    return ok({"restored": result})


@router.post("/api/scenario/batch-operation/recover-gc")
async def front_api_scenario_batch_recover_gc(req: Request):
    """回收站-批量恢复场景（真实实现）。

    前端 batchRecoverScenario 传 { selectIds, selectAll, excludeIds }，
    selectAll 全选时拉取全部回收站条目再排除 excludeIds。
    """
    body = await read_body(req)
    ids = body.get("ids", body.get("selectIds", []))
    exclude = set(body.get("excludeIds", []) or [])
    if body.get("selectAll"):
        trash = frontend_api_service.list_trash_scenarios(limit=100000)
        ids = [s["id"] for s in trash if s.get("id") not in exclude]
    recovered = 0
    for sid in ids:
        if sid and frontend_api_service.restore_scenario(sid):
            recovered += 1
    return ok({"recovered": recovered})


@router.post("/api/scenario/batch-operation/delete")
async def front_api_scenario_batch_delete(req: Request):
    """回收站-批量彻底删除场景（真实实现）。

    前端 batchDeleteScenario 传 { selectIds, selectAll, excludeIds }，
    selectAll 全选时拉取全部回收站条目再排除 excludeIds。
    回收站中的"删除"语义为彻底清空（permanent=True）。
    """
    body = await read_body(req)
    ids = body.get("ids", body.get("selectIds", []))
    exclude = set(body.get("excludeIds", []) or [])
    if body.get("selectAll"):
        trash = frontend_api_service.list_trash_scenarios(limit=100000)
        ids = [s["id"] for s in trash if s.get("id") not in exclude]
    deleted = 0
    for sid in ids:
        if sid and frontend_api_service.delete_scenario(sid, permanent=True):
            deleted += 1
    return ok({"deleted": deleted})


@router.get("/mock/{path:path}", operation_id="mock_call_get_front")
@router.post("/mock/{path:path}", operation_id="mock_call_post_front")
@router.put("/mock/{path:path}", operation_id="mock_call_put_front")
@router.delete("/mock/{path:path}", operation_id="mock_call_delete_front")
@router.patch("/mock/{path:path}", operation_id="mock_call_patch_front")
def mock_call_front(path: str, request: Request):
    """Mock 服务调用。"""
    result = apitest_service.run_mock_request(request.method, "/" + path.lstrip("/"))
    if result:
        return ok(result)
    return fail(f"未找到匹配的 Mock: {path}", 404)
