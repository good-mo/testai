# app/test_plan/router_dashboard_home.py
"""工作台 Dashboard 首页 API（自 router_dashboard.py 拆分）。

包含首页数据/总览/执行趋势/最近活动等只读统计端点。
"""

from fastapi import APIRouter

from app.core.response import ok
from app.services.test_plan_service import test_plan_service

router = APIRouter(tags=["dashboard"])

# ── 工作台首页数据 ───────────────────────────────────────
@router.get("/dashboard/home")
def dashboard_home():
    """工作台首页数据。"""
    from app.services.apitest_service import apitest_service
    from app.services.case_service import case_service
    from app.services.defect_service import defect_service

    case_stats = case_service.get_stats()
    defect_stats = defect_service.get_stats()

    api_cases = apitest_service.list_api_cases(limit=999)
    scenarios = apitest_service.list_scenarios(limit=999)
    definitions = apitest_service.list_definitions(limit=999)
    plans = test_plan_service.list_plans(limit=999)

    return ok({
        "bugCount": defect_stats.get("total", 0),
        "caseCount": case_stats.get("total", 0),
        "apiCaseCount": len(api_cases),
        "scenarioCount": len(scenarios),
        "testPlanCount": len(plans),
        "definitionCount": len(definitions),
    })

@router.get("/dashboard/overview")
def dashboard_overview():
    """工作台总览。"""
    from app.services.case_service import case_service
    from app.services.defect_service import defect_service

    cases = case_service.list_cases(limit=999)
    defects = defect_service.list(limit=999)[0]
    plans = test_plan_service.list_plans(limit=999)

    case_status = {"draft": 0, "review": 0, "approved": 0, "rejected": 0, "deprecated": 0}
    for c in cases:
        s = c.get("status", "draft")
        case_status[s] = case_status.get(s, 0) + 1

    defect_severity = {"critical": 0, "major": 0, "minor": 0, "trivial": 0}
    for d in defects:
        sev = d.get("severity", "major")
        defect_severity[sev] = defect_severity.get(sev, 0) + 1

    plan_status = {"prepared": 0, "running": 0, "completed": 0, "archived": 0}
    for p in plans:
        s = p.get("status", "prepared")
        plan_status[s] = plan_status.get(s, 0) + 1

    return ok({
        "projectCount": 1,
        "caseCount": len(cases),
        "caseStatus": case_status,
        "defectCount": len(defects),
        "defectSeverity": defect_severity,
        "testPlanCount": len(plans),
        "planStatus": plan_status,
    })

@router.get("/dashboard/execution-trend")
def dashboard_execution_trend():
    """执行趋势数据。"""
    return ok({
        "dates": [],
        "executed": [],
        "passed": [],
        "failed": [],
    })

@router.get("/dashboard/recent-activity")
def dashboard_recent_activity():
    """最近活动。"""
    return ok([])
