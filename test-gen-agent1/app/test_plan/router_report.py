# app/test_plan/router_report.py
"""测试计划-报告与分享明细 API 路由（自 router.py 拆分，控制文件行数 <800）。"""

from fastapi import APIRouter, Request

from app.core.response import ok
from app.models.test_plan import PlanResourcePageQuery, ReportDetailPageQuery
from app.services.test_plan_service import test_plan_service

report_router = APIRouter(tags=["test-plan-report"])


@report_router.get("/test-plan/report/get-task/{plan_id}")
def test_plan_report_get_task(plan_id: str):
    """测试计划执行结果。"""
    plan = test_plan_service.get_plan(plan_id)
    if not plan:
        return ok(None)
    stats = test_plan_service.get_plan_statistics(plan_id)
    return ok({
        "id": plan_id,
        "name": plan.get("name", ""),
        "status": "SUCCESS",
        "executionRate": stats["executionRate"],
        "passRate": stats["passRate"],
        "caseCount": stats["total"],
        "passedCount": stats["passed"],
        "failedCount": stats["failed"],
    })


@report_router.post("/test-plan/report/share/detail/bug/page")
def test_plan_report_share_detail_bug_page(body: ReportDetailPageQuery):
    """分享报告缺陷分页。

    入参：reportId / keyword。
    """
    report_id = body.reportId or ""
    keyword = body.keyword or ""
    page_size = body.pageSize
    current = body.current
    from app.services.defect_service import defect_service
    defects = defect_service.list(limit=page_size, offset=(current - 1) * page_size)[0]
    items = []
    for idx, d in enumerate(defects):
        if keyword and keyword.lower() not in d.get("title", "").lower() and keyword.lower() not in d.get("id", "").lower():
            continue
        items.append({
            "id": d.get("id", ""),
            "num": idx + 1,
            "title": d.get("title", ""),
            "status": d.get("status", "open"),
            "handleUserName": d.get("assignee", "admin"),
            "relationCaseCount": 0,
            "reportId": report_id,
        })
    total = len(items)
    paged = items[(current - 1) * page_size: current * page_size]
    return ok({
        "list": paged,
        "total": total,
        "pageSize": page_size,
        "current": current,
    })


@report_router.post("/test-plan/report/share/detail/functional/case/page")
def test_plan_report_share_detail_functional_case_page(body: ReportDetailPageQuery):
    """分享报告功能用例分页。

    入参：reportId / keyword。
    """
    report_id = body.reportId or ""
    keyword = body.keyword or ""
    page_size = body.pageSize
    current = body.current
    cases = test_plan_service.list_plan_cases(report_id) if report_id else []
    items = []
    for idx, rel in enumerate(cases):
        case_status = rel.get("status", "pending")
        case_name = f"用例 {rel.get('case_id', '')[:8]}"
        if keyword and keyword.lower() not in case_name.lower() and keyword.lower() not in rel.get('case_id', '').lower():
            continue
        execute_result = {
            "passed": "SUCCESS",
            "failed": "ERROR",
            "blocked": "BLOCKED",
            "pending": "PENDING",
        }.get(case_status, "PENDING")
        items.append({
            "id": rel.get("id", ""),
            "caseId": rel.get("case_id", ""),
            "num": idx + 1,
            "name": case_name,
            "moduleName": "全部用例",
            "priority": "P2",
            "executeResult": execute_result,
            "executeUser": "admin",
            "bugCount": 0,
            "reportId": report_id,
            "projectId": "",
        })
    total = len(items)
    paged = items[(current - 1) * page_size: current * page_size]
    return ok({
        "list": paged,
        "total": total,
        "pageSize": page_size,
        "current": current,
    })


@report_router.post("/test-plan/report/share/detail/api/case/page")
def test_plan_report_share_detail_api_case_page(body: ReportDetailPageQuery):
    """分享报告接口用例分页。

    入参：reportId / keyword。
    """
    report_id = body.reportId or ""
    keyword = body.keyword or ""
    page_size = body.pageSize
    current = body.current
    from app.services.apitest_service import apitest_service
    cases = apitest_service.list_api_cases(limit=page_size, offset=(current - 1) * page_size)
    items = []
    for idx, c in enumerate(cases):
        name = c.get("name", "")
        if keyword and keyword.lower() not in name.lower():
            continue
        items.append({
            "id": c.get("id", ""),
            "num": idx + 1,
            "name": name,
            "moduleName": "全部接口用例",
            "priority": "P2",
            "executeResult": "PENDING",
            "executeUser": "admin",
            "bugCount": 0,
            "reportId": report_id,
            "projectId": "",
        })
    total = len(items)
    paged = items[(current - 1) * page_size: current * page_size]
    return ok({
        "list": paged,
        "total": total,
        "pageSize": page_size,
        "current": current,
    })


@report_router.post("/test-plan/report/share/detail/scenario/case/page")
def test_plan_report_share_detail_scenario_case_page(body: ReportDetailPageQuery):
    """分享报告场景用例分页。

    入参：reportId / keyword。
    """
    report_id = body.reportId or ""
    keyword = body.keyword or ""
    page_size = body.pageSize
    current = body.current
    from app.services.apitest_service import apitest_service
    scenarios = apitest_service.list_scenarios(limit=page_size, offset=(current - 1) * page_size)
    items = []
    for idx, s in enumerate(scenarios):
        name = s.get("name", "")
        if keyword and keyword.lower() not in name.lower():
            continue
        items.append({
            "id": s.get("id", ""),
            "num": idx + 1,
            "name": name,
            "moduleName": "全部场景",
            "priority": "P2",
            "executeResult": "PENDING",
            "executeUser": "admin",
            "bugCount": 0,
            "reportId": report_id,
            "projectId": "",
        })
    total = len(items)
    paged = items[(current - 1) * page_size: current * page_size]
    return ok({
        "list": paged,
        "total": total,
        "pageSize": page_size,
        "current": current,
    })


@report_router.post("/test-plan/report/share/detail/plan/report/page")
def test_plan_report_share_detail_plan_report_page(body: PlanResourcePageQuery):
    """分享聚合报告明细。

    入参：reportId / keyword。
    """
    page_size = body.pageSize
    current = body.current
    keyword = body.keyword or ""
    plans = test_plan_service.list_plans(keyword=keyword, limit=100)
    stats_map = test_plan_service.get_plans_statistics([p["id"] for p in plans])
    items = []
    for p in plans:
        stats = stats_map.get(p["id"], {"passRate": 0, "executionRate": 0, "total": 0, "passed": 0, "failed": 0, "pending": 0, "blocked": 0})
        created_ts = int(p.get("created_at", 0) * 1000)
        items.append({
            "id": p["id"],
            "name": f"{p.get('name', '')} 报告",
            "testPlanName": p.get("name", ""),
            "planName": p.get("name", ""),
            "status": "COMPLETED" if p.get("status") == "completed" else "PREPARED",
            "resultStatus": "SUCCESS" if stats["passRate"] >= 80 else "ERROR",
            "createTime": created_ts,
            "startTime": created_ts,
            "endTime": created_ts,
            "createUser": p.get("created_by", "admin"),
            "createUserName": p.get("created_by", "admin"),
            "summary": "",
            "passThreshold": 80,
            "passRate": stats["passRate"],
            "executeRate": stats["executionRate"],
            "bugCount": 0,
            "caseTotal": stats["total"],
            "functionalTotal": stats["total"],
            "apiCaseTotal": 0,
            "apiScenarioTotal": 0,
            "executeCount": {
                "success": stats["passed"],
                "error": stats["failed"],
                "fakeError": 0,
                "block": stats["blocked"],
                "pending": stats["pending"],
            },
            "functionalCount": {
                "success": stats["passed"],
                "error": stats["failed"],
                "fakeError": 0,
                "block": stats["blocked"],
                "pending": stats["pending"],
            },
            "apiCaseCount": {
                "success": 0,
                "error": 0,
                "fakeError": 0,
                "block": 0,
                "pending": 0,
            },
            "apiScenarioCount": {
                "success": 0,
                "error": 0,
                "fakeError": 0,
                "block": 0,
                "pending": 0,
            },
            "planCount": 1,
            "passCountOfPlan": 1 if stats["passRate"] >= 80 else 0,
            "failCountOfPlan": 0 if stats["passRate"] >= 80 else 1,
            "functionalBugCount": 0,
            "apiBugCount": 0,
            "scenarioBugCount": 0,
            "defaultLayout": True,
            "triggerMode": "MANUAL",
            "integrated": False,
            "deleted": False,
        })
    paged = items[(current - 1) * page_size: current * page_size]
    return ok({
        "list": paged,
        "total": len(items),
        "pageSize": page_size,
        "current": current,
    })


@report_router.post("/test-plan/report/share/detail/functional/case/step")
@report_router.get("/test-plan/report/share/detail/functional/case/step/{share_id}/{report_id}")
def test_plan_report_share_detail_functional_case_step(request: Request = None, share_id: str = "", report_id: str = ""):
    """分享报告功能用例步骤。"""
    return ok([])


@report_router.get("/test-plan/report/share/detail/api-report")
@report_router.get("/test-plan/report/share/detail/api-report/{share_id}/{report_id}")
def test_plan_report_share_detail_api_report(share_id: str = "", report_id: str = ""):
    """分享接口报告。"""
    return ok(None)


@report_router.get("/test-plan/report/share/detail/api-report/get")
@report_router.get("/test-plan/report/share/detail/api-report/get/{share_id}/{report_id}/{step_id}")
def test_plan_report_share_detail_api_report_get(share_id: str = "", report_id: str = "", step_id: str = ""):
    """分享接口报告详情。"""
    return ok(None)


@report_router.get("/test-plan/report/share/detail/scenario-report")
@report_router.get("/test-plan/report/share/detail/scenario-report/{share_id}/{report_id}")
def test_plan_report_share_detail_scenario_report(share_id: str = "", report_id: str = ""):
    """分享场景报告。"""
    return ok(None)


@report_router.get("/test-plan/report/share/detail/scenario-report/get")
@report_router.get("/test-plan/report/share/detail/scenario-report/get/{share_id}/{report_id}/{step_id}")
def test_plan_report_share_detail_scenario_report_get(share_id: str = "", report_id: str = "", step_id: str = ""):
    """分享场景报告详情。"""
    return ok(None)


@report_router.post("/test-plan/api/case/report/get")
def test_plan_api_case_report_get_post(request: Request):
    """接口报告。"""
    return ok(None)


@report_router.post("/test-plan/api/case/report/get/detail")
def test_plan_api_case_report_get_detail_post(request: Request):
    """接口报告详情。"""
    return ok(None)


@report_router.post("/test-plan/api/scenario/report/get")
def test_plan_api_scenario_report_get_post(request: Request):
    """场景报告。"""
    return ok(None)


@report_router.post("/test-plan/api/scenario/report/get/detail")
def test_plan_api_scenario_report_get_detail_post(request: Request):
    """场景报告详情。"""
    return ok(None)


@report_router.post("/test-plan/report/detail/functional/collection/page")
def test_plan_report_detail_functional_collection_page(request: Request):
    """报告-功能用例测试点。"""
    return ok({
        "list": [], "total": 0,
    })


@report_router.post("/test-plan/report/detail/api/collection/page")
def test_plan_report_detail_api_collection_page(request: Request):
    """报告-接口用例测试点。"""
    return ok({
        "list": [], "total": 0,
    })


@report_router.post("/test-plan/report/detail/scenario/collection/page")
def test_plan_report_detail_scenario_collection_page(request: Request):
    """报告-场景用例测试点。"""
    return ok({
        "list": [], "total": 0,
    })


@report_router.post("/test-plan/report/share/detail/functional/collection/page")
def test_plan_report_share_detail_functional_collection_page(request: Request):
    """分享报告-功能用例测试点。"""
    return ok({
        "list": [], "total": 0,
    })


@report_router.post("/test-plan/report/share/detail/api/collection/page")
def test_plan_report_share_detail_api_collection_page(request: Request):
    """分享报告-接口用例测试点。"""
    return ok({
        "list": [], "total": 0,
    })


@report_router.post("/test-plan/report/share/detail/scenario/collection/page")
def test_plan_report_share_detail_scenario_collection_page(request: Request):
    """分享报告-场景用例测试点。"""
    return ok({
        "list": [], "total": 0,
    })
