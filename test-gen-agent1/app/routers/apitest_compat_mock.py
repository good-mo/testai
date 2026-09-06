import uuid

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from app.core.response import fail, ok
from app.models.apitest import (
    MockCompatAddBody,
    MockCompatBatchBody,
    MockCompatHistoryPageBody,
    MockCompatIdBody,
    MockCompatPageBody,
)

router = APIRouter(tags=["adapter-api_testing_mock"])

@router.get("/api/definition/mock/enable")
def api_definition_mock_enable_get(request: Request):
    """更新Mock状态（GET兼容，query 传 id/active）。接入真实 apitest_service.update_mock 落库。"""
    from app.services.apitest_service import apitest_service
    mock_id = request.query_params.get("id", "") if request else ""
    active = request.query_params.get("active", request.query_params.get("enable", "")) if request else ""
    if mock_id:
        try:
            if active != "":
                apitest_service.update_mock(mock_id, active=1 if str(active).lower() not in ("0", "false", "no") else 0)
            else:
                mock = apitest_service.get_mock(mock_id)
                if mock:
                    apitest_service.update_mock(mock_id, active=0 if bool(mock.get("active", 1)) else 1)
        except Exception:
            return ok({"id": mock_id, "success": False})
    return ok({"id": mock_id, "success": True})



@router.get("/api/definition/mock/transfer/options")
def api_definition_mock_transfer_options(project_id: str = ""):
    """Mock 文件转存目录。"""
    return ok([])



@router.get("/api/definition/mock/get-url")
def api_definition_mock_get_url(mock_id: str = ""):
    """获取 Mock URL。"""
    return ok("/mock/" + mock_id if mock_id else "/mock/")



@router.post("/api/definition/mock/add")
def api_mock_add(body: MockCompatAddBody = Body(default=None)):
    """添加 Mock。"""
    from app.services.apitest_service import apitest_service
    item = apitest_service.create_mock(**(body.service_kwargs() if body else {}))
    return ok(item)



@router.post("/api/definition/mock/page")
def api_mock_page(body: MockCompatPageBody = Body(default=None)):
    """Mock 分页列表。"""
    from app.services.apitest_service import apitest_service
    count_mocks = apitest_service.count_mocks
    list_mocks = apitest_service.list_mocks
    keyword = body.keyword if body else ""
    page_size = int(body.pageSize if body else 10)
    current = int(body.current if body else 1)
    offset = (current - 1) * page_size
    items = list_mocks(keyword=keyword, limit=page_size, offset=offset,
                       project_id=(body.projectId if body else ""))
    total = count_mocks(project_id=(body.projectId if body else ""))
    # 转为前端兼容格式
    result = []
    for m in items:
        result.append({
            "id": m.get("id", ""),
            "name": m.get("name", ""),
            "method": m.get("method", "GET"),
            "path": m.get("path", ""),
            "statusCode": m.get("status_code", 200),
            "responseBody": m.get("response_body", ""),
            "responseHeaders": m.get("response_headers", "{}"),
            "delay": m.get("delay_ms", 0),
            "active": m.get("active", 1),
            "description": m.get("description", ""),
            "projectId": m.get("project_id", ""),
            "createTime": int((m.get("created_at", 0) or 0) * 1000),
            "updateTime": int((m.get("updated_at", 0) or 0) * 1000),
            "createUser": "admin",
            "updateUser": "admin",
        })
    return ok({
        "list": result,
        "total": total,
    })



@router.post("/api/definition/mock/update")
def api_mock_update(body: MockCompatIdBody = Body(default=None)):
    """更新 Mock。"""
    mock_id = body.id if body else ""
    if not mock_id:
        return JSONResponse({"code": 400, "message": "缺少 id", "data": None})
    from app.services.apitest_service import apitest_service
    fields = body.model_dump(exclude_unset=True, exclude={"id"}) if body else {}
    item = apitest_service.update_mock(mock_id, **fields)
    return ok(item)



@router.post("/api/definition/mock/delete")
def api_mock_delete(body: MockCompatIdBody = Body(default=None)):
    """删除 Mock。"""
    mock_id = body.id if body else ""
    from app.services.apitest_service import apitest_service
    deleted = apitest_service.delete_mock(mock_id) if mock_id else False
    return ok(deleted)



@router.get("/api/definition/mock/detail/{mock_id}")
def api_mock_detail(mock_id: str):
    """获取 Mock 详情。"""
    from app.services.apitest_service import apitest_service
    get_mock = apitest_service.get_mock
    item = get_mock(mock_id)
    return ok(item)



@router.post("/api/definition/mock/enable")
def api_mock_enable(body: MockCompatIdBody = Body(default=None)):
    """启用/禁用 Mock。"""
    mock_id = body.id if body else ""
    active = body.active if body else 1
    from app.services.apitest_service import apitest_service
    item = apitest_service.update_mock(mock_id, active=int(active)) if mock_id else None
    return ok(item)


# ════════════════════════════════════════════════════════════
# 调试适配
# ════════════════════════════════════════════════════════════



@router.post("/api/definition/mock/detail")
def api_definition_mock_detail(body: MockCompatIdBody = Body(default=None)):
    """获取 Mock 详情（POST 方式，前端传 body）。"""
    mock_id = body.id if body else ""
    from app.services.apitest_service import apitest_service
    mock = apitest_service.get_mock(mock_id) if mock_id else None
    if not mock:
        return fail("Mock 不存在", code=404)
    return ok(mock)



@router.post("/api/definition/mock/copy")
def api_definition_mock_copy(body: MockCompatIdBody = Body(default=None)):
    """复制 Mock。"""
    mock_id = body.id if body else ""
    from app.services.apitest_service import apitest_service
    create_mock = apitest_service.create_mock
    mock = apitest_service.get_mock(mock_id)
    if not mock:
        return fail("Mock 不存在", code=404)
    new_mock = create_mock(
        name=f"{mock.get('name', '')} (副本)",
        api_definition_id=mock.get("api_definition_id", ""),
        method=mock.get("method", "GET"),
        path=mock.get("path", ""),
        status_code=mock.get("status_code", 200),
        response_body=mock.get("response_body", ""),
        response_headers=mock.get("response_headers", {}),
        delay_ms=mock.get("delay_ms", 0),
        active=mock.get("active", 1),
        description=mock.get("description", ""),
    )
    return ok(new_mock)



@router.post("/api/definition/mock/batch/edit")
def api_definition_mock_batch_edit(body: MockCompatBatchBody = Body(default=None)):
    """批量编辑 Mock。"""
    b = body if body is not None else MockCompatBatchBody()
    mock_ids = b.effective_ids
    if b.selectAll:
        from app.services.apitest_service import apitest_service
        mock_ids = [m["id"] for m in apitest_service.list_mocks(limit=999)]
    dump = b.model_dump(exclude_unset=True)
    update_fields = {k: v for k, v in dump.items() if k not in ("selectIds", "selectAll", "excludeIds", "ids", "condition")}
    if mock_ids and update_fields:
        from app.services.apitest_service import apitest_service
        for mid in mock_ids:
            apitest_service.update_mock(mid, **update_fields)
    return ok(None)



@router.post("/api/definition/mock/batch/delete")
def api_definition_mock_batch_delete(body: MockCompatBatchBody = Body(default=None)):
    """批量删除 Mock。"""
    b = body if body is not None else MockCompatBatchBody()
    mock_ids = b.effective_ids
    if b.selectAll:
        from app.services.apitest_service import apitest_service
        mock_ids = [m["id"] for m in apitest_service.list_mocks(limit=999)]
    from app.services.apitest_service import apitest_service
    for mid in mock_ids:
        apitest_service.delete_mock(mid)
    return ok(None)


# ════════════════════════════════════════════════════════════
# 缺失接口补充 - 缺陷高级功能
# ════════════════════════════════════════════════════════════

# 缺陷附件相关



@router.post("/api/definition/mock/upload/temp/file")
def api_definition_mock_upload_temp_file(request: Request):
    """Mock 临时文件上传。"""
    return ok({
        "fileId": str(uuid.uuid4()),
    })



@router.post("/api/definition/mock/transfer")
def api_definition_mock_transfer(request: Request):
    """Mock 文件转存。"""
    return ok(None)



@router.get("/api/definition/mock/transfer/options/{project_id}")
def api_definition_mock_transfer_options_path(project_id: str):
    """Mock 文件转存目录。"""
    return ok([])



@router.get("/api/definition/mock/get-url/{mock_id}")
def api_definition_mock_get_url_path(mock_id: str):
    """获取 Mock URL。"""
    return ok("/mock/" + mock_id)




# ════════════════════════════════════════════════════════════
# 核心模块缺失接口补充（TestPilot 对齐）
# ════════════════════════════════════════════════════════════



@router.post("/api/definition/mock/operation-history/page")
def api_definition_mock_operation_history_page(body: MockCompatHistoryPageBody = Body(default=None)):
    """Mock 操作历史分页。"""
    b = body if body is not None else MockCompatHistoryPageBody()
    current = b.effective_page
    page_size = b.effective_page_size
    mock_id = b.effective_mock_id
    from app.routers.apitest_compat_base import apitest_service as svc
    try:
        items = svc.list_operation_logs(
            resource_type="mock", resource_id=mock_id or None,
            limit=page_size, offset=(current - 1) * page_size,
        )
        total = svc.count_operation_logs(
            resource_type="mock", resource_id=mock_id or None,
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



@router.get("/api/definition/mock/enable/{id}")



@router.post("/api/definition/mock/enable/{id}")
def api_definition_mock_enable_path(id: str):
    """/api/definition/mock/enable 带路径参数（前端 RESTful 调用兼容）。"""
    from app.services.apitest_service import apitest_service
    update_mock = apitest_service.update_mock
    try:
        update_mock(id, active=1)
    except Exception:
        pass
    return ok({"id": id, "enabled": True})
