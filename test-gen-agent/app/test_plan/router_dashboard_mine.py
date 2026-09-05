# app/test_plan/router_dashboard_mine.py
"""工作台 Dashboard 我的列表 API（自 router_dashboard.py 拆分）。

包含工作台「我的列表」「待办列表」以及缺陷列表自定义字段/列选项端点。
"""


from fastapi import APIRouter, Request

from app.core.response import ok, read_body
from app.core.helpers import as_model
from app.models.test_plan import TestPlanIdsBody
from app.services.test_plan_service import test_plan_service
from app.test_plan.router_dashboard_common import _case_to_review_item, _parse_body

router = APIRouter(tags=["dashboard"])


# 用例内部 status → 前端 LastReviewResult 枚举值
_CASE_STATUS_TO_REVIEW = {
    "draft": "UN_REVIEWED",
    "approved": "PASS",
    "rejected": "UN_PASS",
    "review": "UNDER_REVIEWED",
    "pending": "UNDER_REVIEWED",
    "in_review": "UNDER_REVIEWED",
}


def _review_status(case_status: str) -> str:
    """将内部用例 status 映射为前端 LastReviewResult 枚举值。"""
    return _CASE_STATUS_TO_REVIEW.get(case_status or "draft", "UN_REVIEWED")


# ── 工作台-我的列表 ──────────────────────────────────────
@router.post("/dashboard/my/functional/page")
async def dashboard_my_functional_page(request: Request):
    """工作台-我的-功能用例列表。"""
    body = await _parse_body(request)
    page_size = body.get("pageSize", 10)
    current = body.get("current", 1)

    from app.services.case_service import case_service
    cases = case_service.list_cases(limit=page_size, offset=(current - 1) * page_size)

    items = []
    idx = (current - 1) * page_size
    for i, c in enumerate(cases, start=idx + 1):
        raw_status = c.get("status", "draft")
        items.append({
            "id": c.get("id", ""),
            "num": i,
            "name": c.get("title", ""),
            "priority": c.get("priority", "P2"),
            "status": raw_status,
            "testType": c.get("test_type", "functional"),
            "tags": c.get("tags", []) or [],
            "createTime": int((c.get("created_at", 0) or 0) * 1000),
            "updateTime": int((c.get("updated_at", 0) or 0) * 1000),
            "createUserName": c.get("created_by", "") or "admin",
            "reviewStatus": _review_status(raw_status),
            "lastExecuteResult": (c.get("last_result") or {}).get("status", "UN_EXECUTE")
            if isinstance(c.get("last_result"), dict) else "UN_EXECUTE",
            "customFields": [
                {
                    "internal": True,
                    "internalFieldKey": "functional_priority",
                    "fieldName": "用例等级",
                    "type": "SELECT",
                    "defaultValue": c.get("priority", "P2"),
                    "options": [
                        {"value": "P0", "text": "P0"},
                        {"value": "P1", "text": "P1"},
                        {"value": "P2", "text": "P2"},
                        {"value": "P3", "text": "P3"},
                    ],
                }
            ],
        })

    total = case_service.count_cases()
    return ok({
        "list": items,
        "total": total,
        "pageSize": page_size,
        "current": current,
    })


def _bug_to_item(d, idx):
    """将 defect dict 转成前端工作台缺陷列表项。

    缺陷数据表无 created_by / updated_by 字段，统一用 admin 作为创建/更新人。
    同时返回 *UserName 别名，前端 bugTable 的 dataTransform 从这些别名字段
    映射到 createUser / handleUser / updateUser。
    """
    creator = "admin"
    assignee = d.get("assignee", "") or "admin"
    updater = "admin"
    return {
        "id": d.get("id", ""),
        "num": idx,
        "name": d.get("title", ""),
        "title": d.get("title", ""),
        "status": d.get("status", "open"),
        "severity": d.get("severity", "major"),
        "handleUser": assignee,
        "handleUserName": assignee,
        "createUser": creator,
        "createUserName": creator,
        "updateUser": updater,
        "updateUserName": updater,
        "createTime": int((d.get("created_at", 0) or 0) * 1000),
        "updateTime": int((d.get("updated_at", 0) or 0) * 1000),
    }


@router.post("/dashboard/my/bug/page")
async def dashboard_my_bug_page(request: Request):
    """工作台-我的-缺陷列表。"""
    body = await _parse_body(request)
    page_size = body.get("pageSize", 10)
    current = body.get("current", 1)

    from app.services.defect_service import defect_service
    defects, total = defect_service.list(limit=page_size, offset=(current - 1) * page_size)

    items = []
    idx = (current - 1) * page_size
    for i, d in enumerate(defects, start=idx + 1):
        items.append(_bug_to_item(d, i))

    return ok({
        "list": items,
        "total": total,
        "pageSize": page_size,
        "current": current,
    })


@router.post("/dashboard/my/plan/page")
async def dashboard_my_plan_page(request: Request):
    """工作台-我的-测试计划列表。"""
    body = await _parse_body(request)
    page_size = body.get("pageSize", 10)
    current = body.get("current", 1)

    plans = test_plan_service.list_plans(limit=page_size, offset=(current - 1) * page_size)
    stats_map = test_plan_service.get_plans_statistics([p["id"] for p in plans])
    items = []
    idx = (current - 1) * page_size
    for i, p in enumerate(plans, start=idx + 1):
        stats = stats_map.get(p["id"], {"executionRate": 0, "passRate": 0, "total": 0})
        items.append({
            "id": p.get("id", ""),
            "num": i,
            "name": p.get("name", ""),
            "status": p.get("status", "prepared"),
            "priority": p.get("priority", "P2"),
            "executionRate": stats["executionRate"],
            "passRate": stats["passRate"],
            "caseCount": stats["total"],
            "functionalCaseCount": stats["total"],
            "createTime": int((p.get("created_at", 0) or 0) * 1000),
            "createUserName": p.get("created_by", "") or "admin",
        })

    return ok({
        "list": items,
        "total": test_plan_service.count_plans(),
        "pageSize": page_size,
        "current": current,
    })


@router.post("/dashboard/my/plan/statistics")
async def dashboard_my_plan_statistics(request: Request):
    """工作台-我的-测试计划统计。

    返回结构对齐前端 PassRateCountDetail：
    { id, name, passRate, executeRate, passThreshold, successCount,
      errorCount, fakeErrorCount, blockCount, pendingCount, caseTotal, status }
    """
    body = await read_body(request)
    plan_ids = as_model(body, TestPlanIdsBody).ids or []
    if not isinstance(plan_ids, list):
        plan_ids = []

    stats_map = test_plan_service.get_plans_statistics(plan_ids)
    items = []
    for pid in plan_ids:
        plan = test_plan_service.get_plan(pid)
        if not plan:
            continue
        stats = stats_map.get(pid, {})
        total = stats.get("total", 0)
        passed = stats.get("passed", 0)
        failed = stats.get("failed", 0)
        blocked = stats.get("blocked", 0)
        pending = stats.get("pending", 0)
        items.append({
            "id": pid,
            "name": plan.get("name", ""),
            "passRate": stats.get("passRate", 0),
            "executeRate": stats.get("executionRate", 0),
            "passThreshold": plan.get("pass_threshold", 100) or 100,
            "successCount": passed,
            "errorCount": failed,
            "fakeErrorCount": 0,
            "blockCount": blocked,
            "pendingCount": pending,
            "caseTotal": total,
            "functionalCaseCount": total,
            "apiCaseCount": 0,
            "apiScenarioCount": 0,
            "status": plan.get("status", "prepared"),
            "total": total,
            "passed": passed,
            "failed": failed,
            "pending": pending,
        })

    return ok(items)


@router.post("/dashboard/my/review/page")
async def dashboard_my_review_page(request: Request):
    """工作台-我的-用例评审列表。"""
    body = await _parse_body(request)
    page_size = body.get("pageSize", 10)
    current = body.get("current", 1)

    from app.services.case_service import case_service
    cases = case_service.list_cases(limit=999)
    review_cases = [c for c in cases if c.get("status") in ("review", "pending", "in_review")]
    paged = review_cases[(current - 1) * page_size: current * page_size]

    items = []
    idx = (current - 1) * page_size
    for i, c in enumerate(paged, start=idx + 1):
        c = dict(c)
        c["num"] = i
        items.append(_case_to_review_item(c))

    return ok({
        "list": items,
        "total": len(review_cases),
        "pageSize": page_size,
        "current": current,
    })


@router.post("/dashboard/my/api/page")
async def dashboard_my_api_page(request: Request):
    """工作台-我的-接口用例列表。"""
    body = await _parse_body(request)
    page_size = body.get("pageSize", 10)
    current = body.get("current", 1)

    from app.services.apitest_service import apitest_service
    cases = apitest_service.list_api_cases(limit=page_size, offset=(current - 1) * page_size)

    items = []
    idx = (current - 1) * page_size
    for i, c in enumerate(cases, start=idx + 1):
        items.append({
            "id": c.get("id", ""),
            "num": i,
            "name": c.get("name", ""),
            "description": c.get("description", ""),
            "priority": c.get("priority", "P2"),
            "status": c.get("status", "draft"),
            "lastReportStatus": "UN_EXECUTE",
            "lastReportId": "",
            "environmentName": "",
            "createName": "admin",
            "createTime": int((c.get("created_at", 0) or 0) * 1000),
            "updateTime": int((c.get("updated_at", 0) or 0) * 1000),
        })

    total = apitest_service.count_api_cases()
    return ok({
        "list": items,
        "total": total,
        "pageSize": page_size,
        "current": current,
    })


@router.post("/dashboard/my/scenario/page")
async def dashboard_my_scenario_page(request: Request):
    """工作台-我的-场景列表。"""
    body = await _parse_body(request)
    page_size = body.get("pageSize", 10)
    current = body.get("current", 1)

    from app.services.apitest_service import apitest_service
    scenarios = apitest_service.list_scenarios(limit=page_size, offset=(current - 1) * page_size)

    items = []
    idx = (current - 1) * page_size
    for i, s in enumerate(scenarios, start=idx + 1):
        items.append({
            "id": s.get("id", ""),
            "num": i,
            "name": s.get("name", ""),
            "description": s.get("description", ""),
            "priority": s.get("priority", "P2"),
            "status": s.get("status", "draft"),
            "lastReportStatus": "UN_EXECUTE",
            "lastReportId": "",
            "environmentName": "",
            "createUser": "admin",
            "createUserName": "admin",
            "requestPassRate": 0,
            "createTime": int((s.get("created_at", 0) or 0) * 1000),
            "updateTime": int((s.get("updated_at", 0) or 0) * 1000),
        })

    total = apitest_service.count_scenarios()
    return ok({
        "list": items,
        "total": total,
        "pageSize": page_size,
        "current": current,
    })


# ── 工作台-待办列表 ──────────────────────────────────────
@router.post("/dashboard/todo/plan/page")
async def dashboard_todo_plan_page(request: Request):
    """工作台-待办-测试计划列表。"""
    body = await _parse_body(request)
    page_size = body.get("pageSize", 10)
    current = body.get("current", 1)

    plans = test_plan_service.list_plans(limit=page_size, offset=(current - 1) * page_size)
    stats_map = test_plan_service.get_plans_statistics([p["id"] for p in plans])
    items = []
    idx = (current - 1) * page_size
    for i, p in enumerate(plans, start=idx + 1):
        stats = stats_map.get(p["id"], {"executionRate": 0, "passRate": 0, "total": 0})
        items.append({
            "id": p.get("id", ""),
            "num": i,
            "name": p.get("name", ""),
            "status": p.get("status", "prepared"),
            "priority": p.get("priority", "P2"),
            "executionRate": stats["executionRate"],
            "passRate": stats["passRate"],
            "caseCount": stats["total"],
            "functionalCaseCount": stats["total"],
            "createTime": int((p.get("created_at", 0) or 0) * 1000),
            "createUserName": p.get("created_by", "") or "admin",
        })

    return ok({
        "list": items,
        "total": test_plan_service.count_plans(),
        "pageSize": page_size,
        "current": current,
    })


@router.post("/dashboard/todo/review/page")
async def dashboard_todo_review_page(request: Request):
    """工作台-待办-用例评审列表。"""
    body = await _parse_body(request)
    page_size = body.get("pageSize", 10)
    current = body.get("current", 1)

    from app.services.case_service import case_service
    cases = case_service.list_cases(limit=999)
    review_cases = [c for c in cases if c.get("status") in ("review", "pending", "in_review")]
    paged = review_cases[(current - 1) * page_size: current * page_size]

    items = []
    idx = (current - 1) * page_size
    for i, c in enumerate(paged, start=idx + 1):
        c = dict(c)
        c["num"] = i
        items.append(_case_to_review_item(c))

    return ok({
        "list": items,
        "total": len(review_cases),
        "pageSize": page_size,
        "current": current,
    })


@router.post("/dashboard/todo/bug/page")
async def dashboard_todo_bug_page(request: Request):
    """工作台-待办-缺陷列表。"""
    body = await _parse_body(request)
    page_size = body.get("pageSize", 10)
    current = body.get("current", 1)

    from app.services.defect_service import defect_service
    defects, total = defect_service.list(limit=page_size, offset=(current - 1) * page_size)

    items = []
    idx = (current - 1) * page_size
    for i, d in enumerate(defects, start=idx + 1):
        items.append(_bug_to_item(d, i))

    return ok({
        "list": items,
        "total": total,
        "pageSize": page_size,
        "current": current,
    })


# ── 缺陷列表自定义字段 ───────────────────────────────────
@router.get("/dashboard/header/custom-field/{project_id}")
def dashboard_header_custom_field(project_id: str):
    """缺陷列表自定义字段。

    返回结构对齐前端 BugEditCustomField 模型：
    使用 fieldId / fieldName / fieldKey / type / options 等。
    """
    status_options = [
        {"value": "open", "text": "新建"},
        {"value": "in_progress", "text": "进行中"},
        {"value": "fixed", "text": "已修复"},
        {"value": "closed", "text": "已关闭"},
        {"value": "wont_fix", "text": "不修复"},
    ]
    severity_options = [
        {"value": "blocker", "text": "致命"},
        {"value": "critical", "text": "严重"},
        {"value": "major", "text": "一般"},
        {"value": "minor", "text": "轻微"},
        {"value": "trivial", "text": "提示"},
    ]
    return ok([
        {
            "fieldId": "title",
            "fieldKey": "title",
            "fieldName": "标题",
            "type": "TEXT",
            "value": "",
            "required": True,
            "show": True,
            "enable": True,
            "internal": True,
            "options": [],
            "defaultValue": "",
            "platformSystemField": True,
            "supportSearch": True,
        },
        {
            "fieldId": "status",
            "fieldKey": "status",
            "fieldName": "状态",
            "type": "SELECT",
            "value": "",
            "required": True,
            "show": True,
            "enable": True,
            "internal": True,
            "options": status_options,
            "defaultValue": "open",
            "platformSystemField": True,
            "supportSearch": True,
        },
        {
            "fieldId": "severity",
            "fieldKey": "severity",
            "fieldName": "严重程度",
            "type": "SELECT",
            "value": "",
            "required": True,
            "show": True,
            "enable": True,
            "internal": True,
            "options": severity_options,
            "defaultValue": "major",
            "platformSystemField": True,
            "supportSearch": True,
        },
        {
            "fieldId": "assignee",
            "fieldKey": "assignee",
            "fieldName": "处理人",
            "type": "MEMBER",
            "value": "",
            "required": False,
            "show": True,
            "enable": True,
            "internal": True,
            "options": [],
            "defaultValue": "",
            "platformSystemField": True,
            "supportSearch": True,
        },
    ])


@router.get("/dashboard/header/columns-option/{project_id}")
def dashboard_header_columns_option(project_id: str):
    """缺陷列表列选项。

    返回结构对齐前端 BugOptionListItem：
    { statusOption, handleUserOption, userOption }，每项为 { value, text }。
    """
    return ok({
        "statusOption": [
            {"value": "open", "text": "新建"},
            {"value": "in_progress", "text": "进行中"},
            {"value": "fixed", "text": "已修复"},
            {"value": "closed", "text": "已关闭"},
            {"value": "wont_fix", "text": "不修复"},
        ],
        "handleUserOption": [
            {"value": "admin", "text": "管理员"},
        ],
        "userOption": [
            {"value": "admin", "text": "管理员"},
        ],
    })
