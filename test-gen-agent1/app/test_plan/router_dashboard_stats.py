# app/test_plan/router_dashboard_stats.py
"""工作台 Dashboard 统计卡片 API（自 router_dashboard.py 拆分）。

包含工作台各统计卡片、数量统计、接口覆盖率与测试计划数量统计端点
及其数据组装辅助函数。
"""

import time
from typing import Any, Dict, List

from fastapi import APIRouter, Request

from app.core.response import ok
from app.services.test_plan_service import test_plan_service
from app.test_plan.router_dashboard_common import _case_to_review_item, _parse_body

router = APIRouter(tags=["dashboard"])

# ── 工作台统计卡片 ───────────────────────────────────────

def _overview_payload(body):
    """构造项目概览响应：caseCountMap 按前端模块键返回总数，projectCountList 为时间序列。

    前端 overview.vue 模块摘要依赖 caseCountMap 键为
    FUNCTIONAL / CASE_REVIEW / API / API_CASE / API_SCENARIO / TEST_PLAN / BUG_COUNT。
    """
    day_number = body.get("dayNumber", 3)
    start_time = body.get("startTime", 0)
    end_time = body.get("endTime", 0)

    from app.services.apitest_service import apitest_service
    from app.services.case_service import case_service
    from app.services.defect_service import defect_service

    cases = case_service.list_cases(limit=999)
    defects = defect_service.list(limit=999)[0]
    api_cases = apitest_service.list_api_cases(limit=999)
    scenarios = apitest_service.list_scenarios(limit=999)
    definitions = apitest_service.list_definitions(limit=999)
    plans = test_plan_service.list_plans(limit=999)

    now = time.time()
    if start_time and end_time:
        start_ts, end_ts = start_time / 1000, end_time / 1000
    else:
        start_ts = now - int(day_number or 3) * 86400
        end_ts = now

    days = int((end_ts - start_ts) / 86400) + 1
    days = max(1, min(days, 31))

    def _in_window(obj):
        ts = obj.get("created_at", 0) or 0
        return start_ts <= ts < end_ts

    case_window = [c for c in cases if _in_window(c)]
    defect_window = [d for d in defects if _in_window(d)]
    review_window = [c for c in case_window if c.get("status") in ("review", "pending", "in_review")]
    api_case_window = [a for a in api_cases if _in_window(a)]
    scenario_window = [s for s in scenarios if _in_window(s)]
    definition_window = [d for d in definitions if _in_window(d)]
    plan_window = [p for p in plans if _in_window(p)]

    case_count_map = {
        "FUNCTIONAL": len(case_window),
        "CASE_REVIEW": len(review_window),
        "API": len(definition_window),
        "API_CASE": len(api_case_window),
        "API_SCENARIO": len(scenario_window),
        "TEST_PLAN": len(plan_window),
        "BUG_COUNT": len(defect_window),
    }

    xaxis = []
    case_counts = []
    defect_counts = []
    api_counts = []
    for i in range(days - 1, -1, -1):
        day_start = end_ts - i * 86400
        day_end = day_start + 86400
        xaxis.append(time.strftime("%m-%d", time.localtime(day_start)))
        case_counts.append(sum(1 for c in cases if day_start <= c.get("created_at", 0) < day_end))
        defect_counts.append(sum(1 for d in defects if day_start <= d.get("created_at", 0) < day_end))
        api_counts.append(sum(1 for a in api_cases if day_start <= a.get("created_at", 0) < day_end))

    return {
        "caseCountMap": case_count_map,
        "projectCountList": [
            {"id": "default", "name": "默认项目", "count": case_counts},
        ],
        "xaxis": xaxis,
        "errorCode": 0,
    }


@router.post("/dashboard/project_view")
async def dashboard_project_view(request: Request):
    """项目概览：按时间统计用例/缺陷/接口创建量。"""
    body = await _parse_body(request)
    return ok(_overview_payload(body))


@router.post("/dashboard/create_by_me")
async def dashboard_create_by_me(request: Request):
    """我创建的数据统计。"""
    body = await _parse_body(request)
    return ok(_overview_payload(body))


@router.post("/dashboard/project_member_view")
def dashboard_project_member_view(request: Request):
    """项目成员概览（多项目成员视图）：返回空序列占位，图表按模块键渲染。"""
    return ok({
        "caseCountMap": {
            "FUNCTIONAL": 0,
            "CASE_REVIEW": 0,
            "API": 0,
            "API_CASE": 0,
            "API_SCENARIO": 0,
            "TEST_PLAN": 0,
            "BUG_COUNT": 0,
        },
        "projectCountList": [],
        "xaxis": [],
        "errorCode": 0,
    })


# ── 数量统计卡片 ─────────────────────────────────────────
def _pct(num: int, den: int) -> int:
    """计算百分比（取整）。"""
    return round(num / den * 100) if den else 0

def _build_percent_list(status_map: Dict[str, int]) -> List[Dict[str, Any]]:
    """由 {status: count} 构造 statusPercentList。"""
    total = sum(status_map.values())
    return [
        {"status": s, "count": cnt, "percentValue": f"{round(cnt / total * 100, 1) if total else 0}%"}
        for s, cnt in status_map.items()
    ]

def _case_stats_map(cases: List[Dict]) -> Dict[str, Any]:
    """用例数量卡片：review / pass 为数组。"""
    status_map: Dict[str, int] = {}
    for c in cases:
        s = c.get("status", "draft")
        status_map[s] = status_map.get(s, 0) + 1
    total = len(cases)
    approved = status_map.get("approved", 0)
    reviewed = approved
    unreviewed = total - approved
    return {
        "review": [
            {"name": "评审率", "count": _pct(reviewed, total)},
            {"name": "已评审", "count": reviewed},
            {"name": "未评审", "count": unreviewed},
        ],
        "pass": [
            {"name": "通过率", "count": _pct(approved, total)},
            {"name": "已通过", "count": approved},
            {"name": "未通过", "count": total - approved},
        ],
    }

def _cover_stats_map(cases: List[Dict]) -> Dict[str, Any]:
    """关联用例 / 用例评审卡片：cover 为数组。"""
    total = len(cases)
    covered = sum(
        1
        for c in cases
        if c.get("related_ids") or c.get("relations") or c.get("status") in ("approved", "review")
    )
    return {
        "cover": [
            {"name": "覆盖率", "count": _pct(covered, total)},
            {"name": "已覆盖", "count": covered},
            {"name": "未覆盖", "count": total - covered},
        ],
    }

def _bug_stats_map(defects: List[Dict]) -> Dict[str, Any]:
    """缺陷/遗留缺陷卡片：retentionRate 为数组 [rate, totalBug, legacy]。"""
    total = len(defects)
    legacy = sum(
        1
        for d in defects
        if d.get("status", "open") in ("open", "in_progress", "reopened", "new", "reopen")
    )
    return {
        "retentionRate": [
            {"name": "遗留率", "count": _pct(legacy, total)},
            {"name": "缺陷总数", "count": total},
            {"name": "遗留缺陷", "count": legacy},
        ],
    }

def _api_count_stats_map(definitions: List[Dict]) -> Dict[str, Any]:
    """接口数量卡片：completionRate 为数组。"""
    total = len(definitions)
    done = sum(
        1
        for d in definitions
        if str(d.get("status", "draft")).lower() in ("done", "completed", "close", "closed")
    )
    in_progress = sum(
        1
        for d in definitions
        if str(d.get("status", "draft")).lower() in ("processing", "debugging", "in_progress")
    )
    unfinished = total - done - in_progress
    return {
        "completionRate": [
            {"name": "完成率", "count": _pct(done, total)},
            {"name": "已完成", "count": done},
            {"name": "进行中", "count": in_progress},
            {"name": "未完成", "count": unfinished},
        ],
        "cover": [
            {"name": "覆盖率", "count": _pct(done, total)},
            {"name": "已覆盖", "count": done},
            {"name": "未覆盖", "count": unfinished},
        ],
    }

def _make_pass_rate_data(
    status_map: Dict[str, int], stats_map: Dict[str, Any]
) -> Dict[str, Any]:
    """构造 PassRateDataType 响应：statusStatisticsMap 键均为数组。"""
    return {
        "statusStatisticsMap": stats_map,
        "statusPercentList": _build_percent_list(status_map),
        "errorCode": 0,
    }

@router.post("/dashboard/case_count")
def dashboard_case_count(request: Request):
    """用例数量统计。"""
    from app.services.case_service import case_service
    cases = case_service.list_cases(limit=999)
    status_map: Dict[str, int] = {}
    for c in cases:
        s = c.get("status", "draft")
        status_map[s] = status_map.get(s, 0) + 1
    return ok(_make_pass_rate_data(status_map, _case_stats_map(cases)))

@router.post("/dashboard/associate_case_count")
def dashboard_associate_case_count(request: Request):
    """关联用例数量统计。"""
    from app.services.case_service import case_service
    cases = case_service.list_cases(limit=999)
    associated = [c for c in cases if c.get("related_ids") or c.get("relations")]
    status_map: Dict[str, int] = {}
    for c in associated:
        s = c.get("status", "draft")
        status_map[s] = status_map.get(s, 0) + 1
    return ok(_make_pass_rate_data(status_map, _cover_stats_map(associated)))

@router.post("/dashboard/review_case_count")
def dashboard_review_case_count(request: Request):
    """用例评审数量统计。"""
    from app.services.case_service import case_service
    cases = case_service.list_cases(limit=999)
    in_review = [c for c in cases if c.get("status") in ("review", "pending", "in_review")]
    status_map: Dict[str, int] = {}
    for c in in_review:
        s = c.get("status", "draft")
        status_map[s] = status_map.get(s, 0) + 1
    return ok(_make_pass_rate_data(status_map, _cover_stats_map(in_review)))

@router.post("/dashboard/reviewing_by_me")
def dashboard_reviewing_by_me(request: Request):
    """待我评审列表。"""
    from app.services.case_service import case_service
    cases = case_service.list_cases(limit=999)
    reviews = [c for c in cases if c.get("status") in ("review", "pending", "in_review")]
    return ok({
        "list": [_case_to_review_item(c) for c in reviews[:20]],
        "total": len(reviews),
    })

@router.post("/dashboard/api_count")
def dashboard_api_count(request: Request):
    """接口数量统计。"""
    from app.services.apitest_service import apitest_service
    definitions = apitest_service.list_definitions(limit=999)
    status_map: Dict[str, int] = {}
    for d in definitions:
        s = str(d.get("status", "draft"))
        status_map[s] = status_map.get(s, 0) + 1
    return ok(_make_pass_rate_data(status_map, _api_count_stats_map(definitions)))

@router.post("/dashboard/api_case_count")
def dashboard_api_case_count(request: Request):
    """接口用例数量统计。"""
    from app.services.apitest_service import apitest_service
    cases = apitest_service.list_api_cases(limit=999)
    status_map: Dict[str, int] = {}
    for c in cases:
        s = str(c.get("status", "draft"))
        status_map[s] = status_map.get(s, 0) + 1
    stats_map: Dict[str, Any] = {
        "execRate": [
            {"name": "执行率", "count": _pct(len(cases), len(cases))},
            {"name": "已执行", "count": len(cases)},
            {"name": "未执行", "count": 0},
        ],
        "passRate": [
            {"name": "通过率", "count": _pct(0, len(cases))},
            {"name": "已通过", "count": 0},
            {"name": "未通过", "count": len(cases)},
        ],
        "execCount": [{"name": "执行次数", "count": len(cases)}],
        "apiCaseCount": [{"name": "接口用例数", "count": len(cases)}],
    }
    return ok(_make_pass_rate_data(status_map, stats_map))

@router.post("/dashboard/scenario_count")
def dashboard_scenario_count(request: Request):
    """场景用例数量统计。"""
    from app.services.apitest_service import apitest_service
    scenarios = apitest_service.list_scenarios(limit=999)
    status_map: Dict[str, int] = {}
    for s in scenarios:
        st = str(s.get("status", "draft"))
        status_map[st] = status_map.get(st, 0) + 1
    stats_map: Dict[str, Any] = {
        "execRate": [
            {"name": "执行率", "count": _pct(len(scenarios), len(scenarios))},
            {"name": "已执行", "count": len(scenarios)},
            {"name": "未执行", "count": 0},
        ],
        "passRate": [
            {"name": "通过率", "count": _pct(0, len(scenarios))},
            {"name": "已通过", "count": 0},
            {"name": "未通过", "count": len(scenarios)},
        ],
        "execCount": [{"name": "执行次数", "count": len(scenarios)}],
        "apiScenarioCount": [{"name": "场景用例数", "count": len(scenarios)}],
    }
    return ok(_make_pass_rate_data(status_map, stats_map))

@router.post("/dashboard/bug_count")
def dashboard_bug_count(request: Request):
    """缺陷数量统计。"""
    from app.services.defect_service import defect_service
    defects = defect_service.list(limit=999)[0]
    status_map: Dict[str, int] = {}
    for d in defects:
        s = d.get("status", "open")
        status_map[s] = status_map.get(s, 0) + 1
    return ok(_make_pass_rate_data(status_map, _bug_stats_map(defects)))

@router.post("/dashboard/create_bug_by_me")
def dashboard_create_bug_by_me(request: Request):
    """我创建的缺陷统计。"""
    from app.services.defect_service import defect_service
    defects = defect_service.list(limit=999)[0]
    status_map: Dict[str, int] = {}
    for d in defects:
        s = d.get("status", "open")
        status_map[s] = status_map.get(s, 0) + 1
    return ok(_make_pass_rate_data(status_map, _bug_stats_map(defects)))

@router.post("/dashboard/handle_bug_by_me")
def dashboard_handle_bug_by_me(request: Request):
    """待我处理的缺陷统计。"""
    from app.services.defect_service import defect_service
    defects = defect_service.list(limit=999)[0]
    open_defects = [d for d in defects if d.get("status") in ("open", "in_progress", "reopened", "new")]
    status_map: Dict[str, int] = {}
    for d in open_defects:
        s = d.get("status", "open")
        status_map[s] = status_map.get(s, 0) + 1
    return ok(_make_pass_rate_data(status_map, _bug_stats_map(open_defects)))

@router.post("/dashboard/plan_legacy_bug")
def dashboard_plan_legacy_bug(request: Request):
    """测试计划遗留缺陷。"""
    from app.services.defect_service import defect_service
    defects = defect_service.list(limit=999)[0]
    status_map: Dict[str, int] = {}
    for d in defects:
        s = d.get("status", "open")
        status_map[s] = status_map.get(s, 0) + 1
    return ok(_make_pass_rate_data(status_map, _bug_stats_map(defects)))

# ── 缺陷处理人 ───────────────────────────────────────────
@router.post("/dashboard/bug_handle_user")
def dashboard_bug_handle_user(request: Request):
    """缺陷处理人概览。"""
    return ok({
        "caseCountMap": {},
        "projectCountList": [],
        "xaxis": [],
        "errorCode": 0,
    })

@router.get("/dashboard/bug_handle_user/list")
def dashboard_bug_handle_user_list():
    """缺陷处理人列表。"""
    return ok([
        {"id": "admin", "name": "admin"},
    ])

# ── 接口变更 ─────────────────────────────────────────────
@router.post("/dashboard/api_change")
def dashboard_api_change(request: Request):
    """接口变更列表。

    返回结构对齐前端 apiChangeList 表格需要：
    { id, num, name, method, path, protocol, status, caseTotal,
      scenarioTotal, createTime, updateTime }
    """
    from app.services.apitest_service import apitest_service
    definitions = apitest_service.list_definitions(limit=50)
    items = []
    for i, d in enumerate(definitions, start=1):
        case_total = 0
        try:
            case_total = apitest_service.count_cases_for_definition(d.get("id", ""))
        except Exception:
            case_total = 0
        items.append({
            "id": d.get("id", ""),
            "num": i,
            "name": d.get("name", ""),
            "method": d.get("method", "GET"),
            "path": d.get("path", ""),
            "protocol": d.get("protocol", "HTTP"),
            "status": d.get("status", "open"),
            "caseTotal": case_total,
            "scenarioTotal": 0,
            "createTime": int((d.get("created_at", 0) or 0) * 1000),
            "updateTime": int((d.get("updated_at", 0) or 0) * 1000),
        })
    return ok({
        "list": items,
        "total": len(items),
    })

# ── 项目成员选项 ─────────────────────────────────────────
@router.get("/dashboard/member/get-project-member/option/{project_id}")
def dashboard_member_option(project_id: str, keyword: str = ""):
    """获取项目成员下拉选项。"""
    return ok([
        {"id": "admin", "name": "admin"},
    ])

@router.get("/dashboard/plan/option/{project_id}")
def dashboard_plan_option(project_id: str):
    """获取测试计划下拉选项。"""
    plans = test_plan_service.list_plans(limit=100)
    items = [{"id": p["id"], "name": p["name"]} for p in plans]
    return ok(items)

@router.post("/dashboard/plan_view")
async def dashboard_plan_view(request: Request):
    """测试计划概览。"""
    body = await _parse_body(request)
    plan_id = body.get("planId", "")

    if plan_id:
        plan = test_plan_service.get_plan(plan_id)
        if not plan:
            return ok({
                "caseCountMap": {}, "projectCountList": [], "xaxis": [], "errorCode": 0,
            })
        stats = test_plan_service.get_plan_statistics(plan_id)
        xaxis = [plan.get("name", "")]
        return ok({
            "caseCountMap": {"passed": stats["passed"], "failed": stats["failed"], "pending": stats["pending"]},
            "projectCountList": [{"id": plan_id, "name": plan.get("name", ""), "count": [stats["total"]]}],
            "xaxis": xaxis,
            "errorCode": 0,
        })

    # 没有指定计划则返回所有计划的统计
    plans = test_plan_service.list_plans(limit=50)
    xaxis = [p.get("name", "") for p in plans[:10]]
    stats_map = test_plan_service.get_plans_statistics([p["id"] for p in plans[:10]])
    counts = [stats_map.get(p["id"], {}).get("total", 0) for p in plans[:10]]

    return ok({
        "caseCountMap": {},
        "projectCountList": [{"id": "all", "name": "全部计划", "count": counts}],
        "xaxis": xaxis,
        "errorCode": 0,
    })

# ── 接口覆盖率 ───────────────────────────────────────────
@router.get("/api/definition/rage")
def dashboard_api_coverage():
    """接口覆盖率统计。"""
    from app.services.apitest_service import apitest_service

    definitions = apitest_service.list_definitions(limit=999)
    api_cases = apitest_service.list_api_cases(limit=999)
    scenarios = apitest_service.list_scenarios(limit=999)

    total_api = len(definitions)
    covered_api = min(total_api, len(api_cases))

    return ok({
        "allApiCount": total_api,
        "unCoverWithApiDefinition": max(0, total_api - covered_api),
        "coverWithApiDefinition": covered_api,
        "apiCoverage": f"{round(covered_api / total_api * 100, 1) if total_api else 0}%",
        "unCoverWithApiCase": 0,
        "coverWithApiCase": len(api_cases),
        "apiCaseCoverage": "0%",
        "unCoverWithApiScenario": 0,
        "coverWithApiScenario": len(scenarios),
        "scenarioCoverage": "0%",
    })

# ── 测试计划数量统计 ─────────────────────────────────────
@router.post("/test-plan/rage")
def dashboard_test_plan_rage(request: Request):
    """测试计划数量统计。"""
    plans = test_plan_service.list_plans(limit=999)

    status_map = {"prepared": 0, "running": 0, "completed": 0, "archived": 0}
    for p in plans:
        s = p.get("status", "prepared")
        status_map[s] = status_map.get(s, 0) + 1

    total = len(plans)
    executed = total - status_map.get("prepared", 0)
    passed = 0
    completed_ids = [p["id"] for p in plans if p.get("status") == "completed"]
    if completed_ids:
        stats_map = test_plan_service.get_plans_statistics(completed_ids)
        for pid in completed_ids:
            stats = stats_map.get(pid, {})
            passed += stats.get("passed", 0)

    return ok({
        "unExecute": status_map.get("prepared", 0),
        "executed": executed,
        "passed": passed,
        "notPassed": max(0, executed - passed),
        "finished": status_map.get("completed", 0),
        "running": status_map.get("running", 0),
        "prepared": status_map.get("prepared", 0),
        "archived": status_map.get("archived", 0),
        "errorCode": 0,
        "passedArchived": 0,
        "notPassedArchived": 0,
    })
