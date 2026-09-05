# app/routers/reports_compat.py（自 app/adapters/domains/reports.py 迁移）
"""业务域路由拆分：reports（Phase 3 重构）。"""

import time
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Request

from app.core.response import ok, read_body
from app.core.task_enums import (
    normalize_exec_result,
    normalize_report_step_status,
    normalize_report_step_type,
    normalize_status,
)
from app.logging_config import get_logger
from app.models.reports import (
    ReportBatchParamBody,
    ReportIdBody,
    ReportPageQuery,
)
from app.services.run_service import run_service

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-reports"])


@router.post("/api/report/case/export/{report_id}")
def api_report_case_export_by_id(report_id: str, request: Request):
    """接口用例报告导出（带报告ID路径参数）。"""
    return ok()


@router.post("/api/report/case/get/")
def api_report_case_get_trailing():
    """接口用例报告详情（尾斜杠）。"""
    return ok({"id": "", "name": "接口用例报告", "status": "SUCCESS"})


@router.post("/api/report/case/get/detail/")
def api_report_case_get_detail_trailing():
    """接口用例报告详情步骤（尾斜杠）。"""
    return ok({"steps": []})


@router.post("/api/report/case/share/detail")
def api_report_case_share_detail():
    """接口用例报告分享详情。"""
    return ok({"steps": []})


@router.post("/api/report/scenario/share/detail")
def api_report_scenario_share_detail():
    """场景报告分享详情。"""
    return ok({"steps": []})


@router.post("/api/report/share/get")
def api_report_share_get_post():
    """获取分享信息。"""
    return ok({})


@router.post("/api/report/case/task-report")
def api_report_case_task_report():
    """接口用例任务报告。"""
    return ok([])


@router.post("/api/report/scenario/task-report")
def api_report_scenario_task_report():
    """场景任务报告。"""
    return ok([])


@router.post("/api/report/scenario/task-step")
def api_report_scenario_task_step():
    """场景任务报告步骤。"""
    return ok([])


@router.post("/api/report/case/export")
def api_report_case_export():
    """接口用例报告导出。"""
    return ok({"id": str(uuid.uuid4()), "fileName": "report.zip"})


@router.post("/api/report/case/batch-export")
def api_report_case_batch_export():
    """接口用例报告批量导出。"""
    return ok({"id": str(uuid.uuid4())})


@router.post("/api/report/case/batch-param")
async def api_report_case_batch_param(body: ReportBatchParamBody):
    """接口用例批量导出报告 ID 集合。"""
    records = run_service.list(limit=200)
    # selectAll 表示全选，返回全部报告 ID；否则用 selectIds
    if body.selectAll:
        return ok([r.get("id", "") for r in records if r.get("id")])
    result = [sid for sid in body.selectIds if sid not in body.excludeIds]
    return ok(result)


@router.post("/api/report/scenario/export")
def api_report_scenario_export():
    """场景报告导出。"""
    return ok({"id": str(uuid.uuid4())})


@router.post("/api/report/scenario/batch-export")
def api_report_scenario_batch_export():
    """场景报告批量导出。"""
    return ok({"id": str(uuid.uuid4())})


@router.post("/api/report/scenario/batch-param")
async def api_report_scenario_batch_param(body: ReportBatchParamBody):
    """场景报告批量导出报告 ID 集合。"""
    records = run_service.list(limit=200)
    if body.selectAll:
        return ok([r.get("id", "") for r in records if r.get("id")])
    result = [sid for sid in body.selectIds if sid not in body.excludeIds]
    return ok(result)


@router.get("/api/report/scenario/export/{report_id}")
@router.post("/api/report/scenario/export/{report_id}")
def report_scenario_export_path(report_id: str):
    """导出场景报告（带路径参数）。"""
    return ok({"id": report_id, "exported": True})


# ════════════════════════════════════════════════════════════
# 场景
# ════════════════════════════════════════════════════════════


@router.post("/api/report/case/rename/{report_id}")
async def api_report_case_rename_path(request: Request, report_id: str = ""):
    """接口用例报告重命名（带路径参数）。"""
    body = await read_body(request)
    new_name = ""
    if isinstance(body, dict):
        new_name = body.get("name") or body.get("reportName") or ""
    if not new_name:
        # 兼容裸字符串 body
        raw = await request.body()
        try:
            raw_text = raw.decode("utf-8").strip().strip('"')
            if raw_text and raw_text != "{}":
                new_name = raw_text
        except Exception:
            pass
    rid = report_id or (body.get("id") if isinstance(body, dict) else "")
    if rid and new_name:
        run_service.rename_report(rid, new_name)
        return ok({"id": rid, "renamed": True})
    return ok({"id": rid or "", "renamed": False})


@router.post("/api/report/scenario/rename/{report_id}")
async def api_report_scenario_rename_path(request: Request, report_id: str = ""):
    """接口场景报告重命名（带路径参数）。"""
    body = await read_body(request)
    new_name = ""
    if isinstance(body, dict):
        new_name = body.get("name") or body.get("reportName") or ""
    if not new_name:
        raw = await request.body()
        try:
            raw_text = raw.decode("utf-8").strip().strip('"')
            if raw_text and raw_text != "{}":
                new_name = raw_text
        except Exception:
            pass
    rid = report_id or (body.get("id") if isinstance(body, dict) else "")
    if rid and new_name:
        run_service.rename_report(rid, new_name)
        return ok({"id": rid, "renamed": True})
    return ok({"id": rid or "", "renamed": False})


def _build_share_report_detail(share_id: str, report_id: str, report_type: str = "SCENARIO") -> Dict[str, Any]:
    """构建供分享页展示的 ReportDetail mock 数据（与前端 models/apiTest/report.ts ReportDetail 对齐）。"""
    now_ms = int(time.time() * 1000)
    detail = {
        "id": report_id,
        "name": f"接口{'场景' if report_type == 'SCENARIO' else '用例'}报告 {report_id}",
        "testPlanId": "",
        "createUser": "admin",
        "createTime": now_ms,
        "deleteTime": 0,
        "deleteUser": "",
        "deleted": False,
        "updateUser": "admin",
        "updateTime": now_ms,
        "startTime": now_ms - 60000,
        "endTime": now_ms,
        "requestDuration": 1200,
        "status": "COMPLETED",
        "execStatus": "COMPLETED",
        "triggerMode": "MANUAL",
        "result": "SUCCESS",
        "runMode": "SERIAL",
        "poolId": "pool-1",
        "poolName": "默认资源池",
        "versionId": "",
        "integrated": False,
        "projectId": "",
        "environmentId": "env-1",
        "environmentName": "默认环境",
        "errorCount": 0,
        "fakeErrorCount": 0,
        "pendingCount": 0,
        "successCount": 2,
        "assertionCount": 4,
        "assertionSuccessCount": 4,
        "requestErrorRate": "0.00",
        "requestPendingRate": "0.00",
        "requestFakeErrorRate": "0.00",
        "requestPassRate": "100.00",
        "assertionPassRate": "100.00",
        "scriptIdentifier": "",
        "children": [
            {
                "stepId": f"step-1-{report_id}",
                "sort": 1,
                "name": "请求步骤1",
                "type": "HTTP",
                "stepType": "API",
                "status": "SUCCESS",
                "requestName": "GET /api/example",
                "children": [],
                "index": 1,
            },
            {
                "stepId": f"step-2-{report_id}",
                "sort": 2,
                "name": "请求步骤2",
                "type": "HTTP",
                "stepType": "API",
                "status": "SUCCESS",
                "requestName": "POST /api/create",
                "children": [],
                "index": 2,
            },
        ],
        "stepTotal": 2,
        "stepSuccessCount": 2,
        "stepErrorCount": 0,
        "stepFakeErrorCount": 0,
        "stepPendingCount": 0,
        "console": "",
        "waitingTime": 0,
        "creatUserName": "admin",
    }
    return _normalize_report_steps(detail)


@router.get("/api/report/case/share/{share_id}/{report_id}")
def api_report_case_share_path(share_id: str, report_id: str):
    """接口用例报告分享详情（带路径参数）。

    返回与前端 ReportDetail 结构一致的数据，供 shareReportCase 页面展示。
    """
    detail = _build_share_report_detail(share_id, report_id, "CASE")
    records = _list_report_records()
    rec = next((r for r in records if r.get("id") == report_id), None)
    if rec:
        detail["name"] = rec.get("file_path", detail["name"]) or detail["name"]
        # status/execStatus 为执行状态（已完成=COMPLETED），成败由 result 表达
        detail["status"] = "COMPLETED"
        detail["execStatus"] = "COMPLETED"
        detail["result"] = "SUCCESS" if rec.get("passed") else "ERROR"
        if rec.get("passed"):
            detail["requestPassRate"] = "100.00"
        else:
            detail["errorCount"] = 1
            detail["successCount"] = 0
            detail["requestPassRate"] = "0.00"
    return ok(detail)


@router.get("/api/report/scenario/share/{share_id}/{report_id}")
def api_report_scenario_share_path(share_id: str, report_id: str):
    """接口场景报告分享详情（带路径参数）。

    返回与前端 ReportDetail 结构一致的数据，供 shareReportScenario 页面展示。
    """
    detail = _build_share_report_detail(share_id, report_id, "SCENARIO")
    records = _list_report_records()
    rec = next((r for r in records if r.get("id") == report_id), None)
    if rec:
        detail["name"] = rec.get("file_path", detail["name"]) or detail["name"]
        # status/execStatus 为执行状态（已完成=COMPLETED），成败由 result 表达
        detail["status"] = "COMPLETED"
        detail["execStatus"] = "COMPLETED"
        detail["result"] = "SUCCESS" if rec.get("passed") else "ERROR"
        if rec.get("passed"):
            detail["requestPassRate"] = "100.00"
        else:
            detail["errorCount"] = 1
            detail["successCount"] = 0
            detail["requestPassRate"] = "0.00"
    return ok(detail)


def _build_share_step_detail(share_id: str, report_id: str, step_id: str) -> Dict[str, Any]:
    """构建供分享页步骤详情展示的 mock 数据（与前端 ReportStepDetailItem 结构对齐）。"""
    return {
        "id": step_id,
        "reportId": report_id,
        "stepId": step_id,
        "status": "SUCCESS",
        "fakeCode": "",
        "requestName": "GET /api/example",
        "requestTime": 200,
        "code": "200",
        "responseSize": 1024,
        "scriptIdentifier": "",
        "content": {
            "responseResult": {
                "responseCode": "200",
                "responseMessage": "OK",
                "responseSize": 1024,
                "headers": [{"name": "Content-Type", "value": "application/json"}],
                "body": "{\"code\": 200, \"data\": \"success\"}",
                "latency": 120,
                "dnsLookupTime": 5,
                "tcpHandshakeTime": 10,
                "sslHandshakeTime": 0,
                "socketInitTime": 3,
                "downloadTime": 5,
                "transferStartTime": 20,
                "responseTime": 200,
            },
            "subRequestResults": [],
            "assertionResults": [],
            "console": "",
            "request": {
                "method": "GET",
                "url": "https://api.example.com/test",
                "headers": [],
                "body": {},
            },
        },
        "isSuccessful": True,
    }


@router.get("/api/report/case/share/detail/{share_id}/{report_id}/{step_id}")
def api_report_case_share_detail_path(share_id: str, report_id: str, step_id: str):
    """接口用例报告分享步骤详情（带路径参数）。"""
    return ok([_build_share_step_detail(share_id, report_id, step_id)])


@router.get("/api/report/scenario/share/detail/{share_id}/{report_id}/{step_id}")
def api_report_scenario_share_detail_path(share_id: str, report_id: str, step_id: str):
    """接口场景报告分享步骤详情（带路径参数）。"""
    return ok([_build_share_step_detail(share_id, report_id, step_id)])


@router.get("/api/report/case/task-report/{task_id}")
def api_report_case_task_report_path(task_id: str):
    """接口用例任务报告（带路径参数）。

    status 归一为执行状态枚举（已生成完成的报告为 COMPLETED），
    result 用执行结果枚举承载成败 —— 不再把 SUCCESS/ERROR 塞给前端
    executeStatusMap 导致「未知状态」TypeError。
    """
    return ok({
        "task_id": task_id,
        "status": normalize_status("COMPLETED"),
        "execStatus": normalize_status("COMPLETED"),
        "result": normalize_exec_result("SUCCESS"),
    })


@router.get("/api/report/scenario/task-step/{task_id}")
def api_report_scenario_task_step_path(task_id: str):
    """接口场景任务步骤（带路径参数）。"""
    return ok({
        "task_id": task_id,
        "status": normalize_status("COMPLETED"),
        "execStatus": normalize_status("COMPLETED"),
        "result": normalize_exec_result("SUCCESS"),
    })


@router.get("/api/report/scenario/task-report/{task_id}/{step_id}")
def api_report_scenario_task_report_step_path(task_id: str, step_id: str):
    """接口场景任务报告步骤（带路径参数）。"""
    return ok({
        "task_id": task_id,
        "step_id": step_id,
        "status": normalize_status("COMPLETED"),
        "execStatus": normalize_status("COMPLETED"),
        "result": normalize_exec_result("SUCCESS"),
    })


# ════════════════════════════════════════════════════════════
# 任务中心模块（修复 1 参数版本 item/stop）
# ════════════════════════════════════════════════════════════


@router.post("/api/report/case/page")
async def api_report_case_page(body: ReportPageQuery):
    """接口用例报告分页列表。"""
    keyword = body.keyword
    page_size = body.pageSize
    current = body.current
    offset = (current - 1) * page_size
    search = keyword or None
    records = run_service.list(limit=page_size, offset=offset, search=search)
    items = []
    for r in records:
        item = _build_report_item(r)
        item["reportType"] = "CASE"
        items.append(item)
    # total: DB 侧真实计数（与 list 同 search 条件）
    total = run_service.count(search=search)
    return ok({
            "list": items,
            "total": total,
            "pageSize": page_size,
            "current": current,
        })


@router.post("/api/report/scenario/page")
async def api_report_scenario_page(body: ReportPageQuery):
    """接口场景报告分页列表。"""
    page_size = body.pageSize
    current = body.current
    offset = (current - 1) * page_size
    records = run_service.list(limit=page_size, offset=offset)
    items = []
    for r in records:
        item = _build_report_item(r)
        item["reportType"] = "SCENARIO"
        items.append(item)
    # total: DB 真实总数（无关键词过滤时）
    total = run_service.count()
    return ok({
            "list": items,
            "total": total,
            "pageSize": page_size,
            "current": current,
        })


@router.post("/api/report/case/rename")
async def api_report_case_rename(request: Request):
    """重命名用例报告（真实落库：更新 run_records.file_path）。"""
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    rid = body.get("id") or body.get("reportId") or ""
    new_name = body.get("name") or body.get("reportName") or ""
    if rid and new_name:
        ok_res = run_service.rename_report(rid, new_name)
        return ok({"id": rid, "renamed": bool(ok_res)})
    return ok({"renamed": False})


@router.post("/api/report/scenario/rename")
async def api_report_scenario_rename(request: Request):
    """重命名场景报告（真实落库：更新 run_records.file_path）。"""
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    rid = body.get("id") or body.get("reportId") or ""
    new_name = body.get("name") or body.get("reportName") or ""
    if rid and new_name:
        ok_res = run_service.rename_report(rid, new_name)
        return ok({"id": rid, "renamed": bool(ok_res)})
    return ok({"renamed": False})


@router.post("/api/report/case/delete")
async def api_report_case_delete(request: Request):
    """删除用例报告（真实落库：删除对应运行记录）。"""
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    rid = body.get("id") or body.get("reportId") or ""
    if rid:
        run_service.delete_report(rid)
    return ok({"deleted": bool(rid)})


@router.post("/api/report/case/batch/delete")
async def api_report_case_batch_delete(request: Request):
    """批量删除用例报告（真实落库：批量删除运行记录）。"""
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    ids = body.get("ids") or body.get("selectIds") or []
    if body.get("selectAll") and body.get("excludeIds"):
        all_records = run_service.list(limit=1000)
        ids = [r["id"] for r in all_records if r.get("id") not in body.get("excludeIds", [])]
    if isinstance(ids, str):
        ids = [ids]
    cnt = run_service.delete_reports(ids) if ids else 0
    return ok({"deleted": cnt})


@router.post("/api/report/scenario/delete")
async def api_report_scenario_delete(request: Request):
    """删除场景报告（真实落库：删除对应运行记录）。"""
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    rid = body.get("id") or body.get("reportId") or ""
    if rid:
        run_service.delete_report(rid)
    return ok({"deleted": bool(rid)})


@router.post("/api/report/scenario/batch/delete")
async def api_report_scenario_batch_delete(request: Request):
    """批量删除场景报告（真实落库：批量删除运行记录）。"""
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    ids = body.get("ids") or body.get("selectIds") or []
    if body.get("selectAll") and body.get("excludeIds"):
        all_records = run_service.list(limit=1000)
        ids = [r["id"] for r in all_records if r.get("id") not in body.get("excludeIds", [])]
    if isinstance(ids, str):
        ids = [ids]
    cnt = run_service.delete_reports(ids) if ids else 0
    return ok({"deleted": cnt})


def _normalize_report_steps(node: Any) -> Any:
    """递归归一报告步骤树，使 step 级 status/stepType 落在前端可识别值域内。

    兼容场景/用例报告里的 children / steps 嵌套结构。未知的 stepType 统一回退
    为 API、未知 step status 回退为 PENDING，避免前端 statusMap/scenarioStepMap
    查不到 key 而 undefined.label 崩溃。
    """
    if isinstance(node, dict):
        # 步骤节点（含 stepId/status/stepType 字段）在返回前归一化值域
        if "stepType" in node and node.get("stepType") is not None:
            node["stepType"] = normalize_report_step_type(node.get("stepType"))
        if "status" in node and isinstance(node.get("status"), str):
            node["status"] = normalize_report_step_status(node.get("status"))
        if "execStatus" in node and isinstance(node.get("execStatus"), str):
            node["execStatus"] = normalize_report_step_status(node.get("execStatus"))
        for key, value in node.items():
            if isinstance(value, list):
                node[key] = [_normalize_report_steps(item) for item in value]
            elif isinstance(value, dict):
                node[key] = _normalize_report_steps(value)
    elif isinstance(node, list):
        return [_normalize_report_steps(item) for item in node]
    return node


def _build_steps(report_type: str, file_name: str, passed: bool) -> List[Dict[str, Any]]:
    """构建场景/用例报告步骤树 children 数据。"""
    if report_type == "CASE":
        # 用例报告：单一请求步骤
        return [{
            "stepId": "step-1",
            "reportId": "",
            "name": f"请求 {file_name or 'API用例'}",
            "sort": 1,
            "index": 1,
            "stepType": "API",
            "parentId": "",
            "status": "SUCCESS" if passed else "ERROR",
            "fakeCode": "",
            "requestName": "API请求",
            "requestTime": 120 if passed else 200,
            "code": "200" if passed else "500",
            "responseSize": 1024 if passed else 0,
            "scriptIdentifier": "",
            "fold": True,
            "expanded": False,
            "children": [],
        }]

    # 场景报告：构建带层级的步骤树
    base_name = file_name or "接口场景"
    return [
        {
            "stepId": "step-scenario-1",
            "reportId": "",
            "name": f"请求 {base_name}-登录",
            "sort": 1,
            "index": 1,
            "stepType": "API",
            "parentId": "",
            "status": "SUCCESS" if passed else "ERROR",
            "fakeCode": "",
            "requestName": "登录请求",
            "requestTime": 80 if passed else 120,
            "code": "200" if passed else "500",
            "responseSize": 512 if passed else 0,
            "scriptIdentifier": "",
            "fold": True,
            "expanded": False,
            "children": [
                {
                    "stepId": "step-scenario-1-1",
                    "reportId": "",
                    "name": "提取 Token",
                    "sort": 1,
                    "index": 1,
                    "stepType": "SCRIPT",
                    "parentId": "step-scenario-1",
                    "status": "SUCCESS" if passed else "PENDING",
                    "fakeCode": "",
                    "requestName": "",
                    "requestTime": 10,
                    "code": "",
                    "responseSize": 0,
                    "scriptIdentifier": "var token = response.data.token;",
                    "fold": True,
                    "expanded": False,
                    "children": [],
                }
            ],
        },
        {
            "stepId": "step-scenario-2",
            "reportId": "",
            "name": f"请求 {base_name}-查询列表",
            "sort": 2,
            "index": 2,
            "stepType": "API",
            "parentId": "",
            "status": "SUCCESS" if passed else "PENDING",
            "fakeCode": "",
            "requestName": "查询列表",
            "requestTime": 60 if passed else 0,
            "code": "200" if passed else "",
            "responseSize": 2048 if passed else 0,
            "scriptIdentifier": "",
            "fold": True,
            "expanded": False,
            "children": [
                {
                    "stepId": "step-scenario-2-1",
                    "reportId": "",
                    "name": "校验响应状态",
                    "sort": 1,
                    "index": 1,
                    "stepType": "SCRIPT",
                    "parentId": "step-scenario-2",
                    "status": "SUCCESS" if passed else "PENDING",
                    "fakeCode": "",
                    "requestName": "",
                    "requestTime": 5,
                    "code": "",
                    "responseSize": 0,
                    "scriptIdentifier": "assert(response.status === 200);",
                    "fold": True,
                    "expanded": False,
                    "children": [],
                }
            ],
        },
        {
            "stepId": "step-scenario-3",
            "reportId": "",
            "name": f"请求 {base_name}-创建数据",
            "sort": 3,
            "index": 3,
            "stepType": "API",
            "parentId": "",
            "status": "SUCCESS" if passed else "PENDING",
            "fakeCode": "",
            "requestName": "创建数据",
            "requestTime": 100 if passed else 0,
            "code": "201" if passed else "",
            "responseSize": 256 if passed else 0,
            "scriptIdentifier": "",
            "fold": True,
            "expanded": False,
            "children": [],
        },
        {
            "stepId": "step-scenario-4",
            "reportId": "",
            "name": f"请求 {base_name}-执行断言",
            "sort": 4,
            "index": 4,
            "stepType": "API_CASE",
            "parentId": "",
            "status": "SUCCESS" if passed else "PENDING",
            "fakeCode": "",
            "requestName": "断言检查",
            "requestTime": 50 if passed else 0,
            "code": "200" if passed else "",
            "responseSize": 128 if passed else 0,
            "scriptIdentifier": "",
            "fold": True,
            "expanded": False,
            "children": [],
        },
    ]


def _report_detail(rec: Dict[str, Any], report_type: str = "CASE") -> Dict[str, Any]:
    """构建完整报告详情，供前端全屏导出 PDF / 报告详情渲染使用。

    返回值按 frontend ReportDetail / PlanReportDetail 模型对齐。
    """
    passed = bool(rec.get("passed"))
    created_ts = int(rec.get("created_at", 0) * 1000)
    end_ts = created_ts + (int((rec.get("performance_report") or {}).get("duration", 1) * 1000)
                           if isinstance(rec.get("performance_report"), dict) else 1200)

    total_steps = 4 if report_type == "SCENARIO" else 1
    success_steps = total_steps if passed else max(0, total_steps - 1)
    error_steps = 0 if passed else 1
    fake_error_steps = 0
    pending_steps = 0 if passed else (total_steps - success_steps - error_steps)
    if pending_steps < 0:
        pending_steps = 0

    success_count = 1 if passed else 0
    error_count = 0 if passed else 1
    fake_error_count = 0
    pending_count = 0 if passed else 0

    assertion_count = 2
    assertion_success = 2 if passed else 0
    request_total = success_count + error_count + fake_error_count + pending_count

    # 基础 ReportDetail 结构（对齐 frontend models/apiTest/report.ts）
    detail = {
        "id": rec.get("id", ""),
        "name": rec.get("file_path", "接口测试") or "接口测试",
        "testPlanId": rec.get("metadata", {}).get("testPlanId", "") if isinstance(rec.get("metadata"), dict) else "",
        "createUser": "admin",
        "createTime": created_ts,
        "deleteTime": 0,
        "deleteUser": "",
        "deleted": False,
        "updateUser": "admin",
        "updateTime": created_ts,
        "startTime": created_ts,
        "endTime": end_ts,
        "requestDuration": end_ts - created_ts,
        # ReportDetail.status/execStatus 为执行状态枚举（已完成=COMPLETED），
        # 成败由 result 承载 —— 对齐 frontend ReportDetail.status: ExecuteStatusEnum。
        "status": "COMPLETED",
        "execStatus": "COMPLETED",
        "triggerMode": "MANUAL",
        "result": "SUCCESS" if passed else "ERROR",
        "runMode": "SERIAL",
        "poolId": "",
        "poolName": "LOCAL",
        "versionId": "",
        "integrated": False,
        "projectId": rec.get("metadata", {}).get("projectId", "") if isinstance(rec.get("metadata"), dict) else "",
        "environmentId": "",
        "environmentName": "默认环境",
        "successCount": success_count,
        "errorCount": error_count,
        "fakeErrorCount": fake_error_count,
        "pendingCount": pending_count,
        "assertionCount": assertion_count,
        "assertionSuccessCount": assertion_success,
        "requestPassRate": "100.00" if passed else "0.00",
        "requestErrorRate": "0.00" if passed else "100.00",
        "requestFakeErrorRate": "0.00",
        "requestPendingRate": "0.00",
        "assertionPassRate": "100.00" if passed else "0.00",
        "scriptIdentifier": "",
        "children": _build_steps(report_type, rec.get("file_path", ""), passed),
        "stepTotal": total_steps,
        "stepSuccessCount": success_steps,
        "stepErrorCount": error_steps,
        "stepFakeErrorCount": fake_error_steps,
        "stepPendingCount": pending_steps,
        "requestTotal": request_total,
        "console": "",
        "waitingTime": 100,
        "creatUserName": "admin",
        "total": request_total,
        "responseTime": 120,
        "reportType": "SCENARIO" if report_type == "SCENARIO" else "CASE",
        "passRate": 1.0 if passed else 0.0,
        "requestCount": 1,
    }
    return _normalize_report_steps(detail)


@router.post("/api/report/case/get")
async def api_report_case_get(body: ReportIdBody):
    """获取用例报告详情。"""
    report_id = body.id
    records = _list_report_records()
    rec = next((r for r in records if r.get("id") == report_id), None)
    if not rec:
        rec = records[0] if records else {}
    return ok(_report_detail(rec, "CASE"))


@router.post("/api/report/scenario/get")
async def api_report_scenario_get(body: ReportIdBody):
    """获取场景报告详情。"""
    report_id = body.id
    records = _list_report_records()
    rec = next((r for r in records if r.get("id") == report_id), None)
    if not rec:
        rec = records[0] if records else {}
    detail = _report_detail(rec, "SCENARIO")
    return ok(detail)


@router.post("/api/report/case/get/detail")
async def api_report_case_get_detail(body: ReportIdBody):
    """获取用例报告步骤详情。"""
    report_id = body.id
    records = _list_report_records()
    rec = next((r for r in records if r.get("id") == report_id), None)
    if not rec:
        rec = records[0] if records else {}
    detail = _report_detail(rec, "CASE")
    detail["steps"] = detail.get("children", [])
    return ok(detail)


@router.post("/api/report/scenario/get/detail")
async def api_report_scenario_get_detail(body: ReportIdBody):
    """获取场景报告步骤详情。"""
    report_id = body.id
    records = _list_report_records()
    rec = next((r for r in records if r.get("id") == report_id), None)
    if not rec:
        rec = records[0] if records else {}
    detail = _report_detail(rec, "SCENARIO")
    detail["steps"] = detail.get("children", [])
    return ok(detail)


@router.get("/api/report/case/get/{report_id}")
def api_report_case_get_get(report_id: str):
    """获取用例报告详情（GET）。"""
    records = _list_report_records()
    rec = next((r for r in records if r.get("id") == report_id), None)
    if not rec:
        rec = records[0] if records else {}
    return ok(_report_detail(rec, "CASE"))


@router.get("/api/report/scenario/get/{report_id}")
def api_report_scenario_get_get(report_id: str):
    """获取场景报告详情（GET）。"""
    records = _list_report_records()
    rec = next((r for r in records if r.get("id") == report_id), None)
    if not rec:
        rec = records[0] if records else {}
    detail = _report_detail(rec, "SCENARIO")
    return ok(detail)


@router.get("/api/report/case/get/detail/{report_id}")
def api_report_case_get_detail_get(report_id: str):
    """获取用例报告步骤详情（GET）。"""
    records = _list_report_records()
    rec = next((r for r in records if r.get("id") == report_id), None)
    if not rec:
        rec = records[0] if records else {}
    detail = _report_detail(rec, "CASE")
    detail["steps"] = detail.get("children", [])
    return ok(detail)


@router.get("/api/report/scenario/get/detail/{report_id}")
def api_report_scenario_get_detail_get(report_id: str):
    """获取场景报告步骤详情（GET）。"""
    records = _list_report_records()
    rec = next((r for r in records if r.get("id") == report_id), None)
    if not rec:
        rec = records[0] if records else {}
    detail = _report_detail(rec, "SCENARIO")
    detail["steps"] = detail.get("children", [])
    return ok(detail)


@router.post("/api/report/case/share")
async def api_report_case_share(body: ReportIdBody):
    """用例报告分享。"""
    report_id = body.id
    share_id = report_id or "share_" + str(uuid.uuid4())[:8]
    return ok({
        "shareId": share_id,
        "shareUrl": f"?shareId={share_id}",
    })


@router.post("/api/report/scenario/share")
async def api_report_scenario_share(body: ReportIdBody):
    """场景报告分享。"""
    report_id = body.id
    share_id = report_id or "share_" + str(uuid.uuid4())[:8]
    return ok({
        "shareId": share_id,
        "shareUrl": f"?shareId={share_id}",
    })


@router.post("/api/report/share/gen")
async def api_report_share_gen(body: ReportIdBody):
    """生成分享链接。"""
    report_id = body.id
    share_id = report_id or "share_" + str(uuid.uuid4())[:8]
    return ok({
        "shareId": share_id,
        "shareUrl": f"?shareId={share_id}",
    })


@router.get("/api/report/share/get")
def api_report_share_get(request: Request, id: str = "", shareId: str = ""):
    """获取分享信息。"""
    share = shareId or id or ""
    records = _list_report_records()
    rec = records[0] if records else None
    report_id = rec.get("id", "") if rec else share
    return ok({
        "shareId": share,
        "reportId": report_id,
        "deleted": False,
        "expired": False,
        "shareTime": 0,
    })


@router.post("/api/report/share/get-share-time")
def api_report_share_get_time(request: Request):
    """获取分享时间。"""
    return ok(0)


@router.get("/api/report/case/delete/{report_id}")
def api_report_case_delete_get(report_id: str):
    """删除用例报告（GET 路径参数，真实落库）。"""
    if report_id:
        run_service.delete_report(report_id)
    return ok({"deleted": bool(report_id)})


@router.get("/api/report/scenario/delete/{report_id}")
def api_report_scenario_delete_get(report_id: str):
    """删除场景报告（GET 路径参数，真实落库）。"""
    if report_id:
        run_service.delete_report(report_id)
    return ok({"deleted": bool(report_id)})


@router.get("/api/report/share/get/{share_id}")
def api_report_share_get_path(share_id: str):
    """获取分享信息（GET path）。

    前端 getShareReportInfo(shareId) 期望返回：
      { reportId, deleted, expired }
    reportId 用于后续获取报告详情；deleted/expired 标记资源失效状态。
    """
    records = _list_report_records()
    rec = next((r for r in records if r.get("id", "").replace("share_", "") in share_id
                or share_id in r.get("id", "")), None)
    if not rec:
        # 尝试用首条记录（兼容 mock 数据）
        rec = records[0] if records else None
    report_id = rec.get("id", "") if rec else (share_id.replace("share_", "") if share_id.startswith("share_") else share_id)
    return ok({
        "shareId": share_id,
        "reportId": report_id,
        "deleted": False,
        "expired": False,
        "shareTime": 0,
    })


@router.get("/api/report/share/get-share-time/{project_id}")
def api_report_share_get_time_path(project_id: str):
    """获取分享时间（GET path）。"""
    return ok(0)


@router.get("/api/report/scenario/get/detail/{report_id}/{step_id}")
def api_report_scenario_get_detail_path(report_id: str, step_id: str):
    """场景报告步骤详情（GET path）。"""
    records = _list_report_records()
    rec = next((r for r in records if r.get("id") == report_id), None)
    if not rec:
        rec = records[0] if records else {}
    detail = _report_detail(rec, "SCENARIO")
    detail["steps"] = [{"id": step_id, "name": "步骤" + step_id, "status": "SUCCESS" if rec.get("passed") else "ERROR"}]
    return ok(detail)


@router.get("/api/report/case/get/detail/{report_id}/{step_id}")
def api_report_case_get_detail_path(report_id: str, step_id: str):
    """用例报告步骤详情（GET path）。"""
    records = _list_report_records()
    rec = next((r for r in records if r.get("id") == report_id), None)
    if not rec:
        rec = records[0] if records else {}
    detail = _report_detail(rec, "CASE")
    detail["steps"] = [{"id": step_id, "name": "请求" + step_id, "status": "SUCCESS" if rec.get("passed") else "ERROR"}]
    return ok(detail)


# 缺失接口补充 - 接口定义模块管理
# ════════════════════════════════════════════════════════════


def _build_report_item(rec: Dict[str, Any]) -> Dict[str, Any]:
    """将运行记录转为报告条目。"""
    return {
        "id": rec.get("id", ""),
        "name": rec.get("file_path", "接口测试") or "接口测试",
        "status": "SUCCESS" if rec.get("passed") else "ERROR",
        "passRate": 1.0 if rec.get("passed") else 0.0,
        "requestCount": 1,
        "errorCount": 0 if rec.get("passed") else 1,
        "createTime": int(rec.get("created_at", 0) * 1000),
        "createUser": "admin",
        "projectId": "",
        "triggerMode": "MANUAL",
        "type": "API",
    }


def _list_report_records():
    try:
        return run_service.list(limit=200)
    except Exception:
        return []


