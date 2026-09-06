# app/routers/insights.py
"""测试洞察路由（Phase 3 重构 · DDD 迁移阶段 B）。

阶段 B：路由不再直接调用四层 Service / Repository，改为经由 test_insight 域
应用层的 DTO 桥（web_bridge）访问 DDD 应用服务，业务规则由领域层守护。

保留点：
- /api/insights/risk 仍需跨 project_service / case_service 收集被测源码，
  该「编排」留在路由内，实际风险计算走 DDD 应用服务；
- 对外 API 路径与返回结构保持既有一致。
"""
import asyncio
from typing import Optional

from fastapi import APIRouter

from app.core.response import fail, ok
from app.domain.test_insight.application import web_bridge as insight_bridge
from app.domain.test_insight.application.dto import LowcodeRequest, TraceRecord

router = APIRouter(tags=["insights"])


@router.get("/api/insights/value")
def api_insights_value():
    """价值量化：缺陷价值 / 覆盖价值 / 避免事故估算。"""
    return ok(insight_bridge.get_value())


@router.get("/api/insights/trace")
def api_list_trace(
    file_path: Optional[str] = None,
    result: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """列出测试执行追溯记录。"""
    data = insight_bridge.list_trace(
        file_path=file_path, result=result, limit=limit, offset=offset,
    )
    return ok(data)


@router.post("/api/insights/trace")
def api_record_trace(body: TraceRecord):
    """手动记录一次执行追溯。"""
    rec = insight_bridge.record_trace(
        file_path=body.file_path, result=body.result,
        passed_count=body.passed_count, failed_count=body.failed_count,
        error_count=body.error_count, coverage=body.coverage,
        attribution=body.attribution, note=body.note, created_by=body.created_by,
    )
    return ok(rec)


@router.get("/api/insights/trace/prove")
def api_prove_coverage(file_path: str):
    """自证清白：针对某文件调出历史执行记录。"""
    return ok(insight_bridge.prove_coverage(file_path))


@router.get("/api/insights/risk")
async def api_risk(project_path: str = ""):
    """高风险模块预警。"""
    if project_path:
        from app.domain.project.application.project_app_service import project_service
        scan = await asyncio.to_thread(project_service.scan_project, project_path)
        result = await asyncio.to_thread(
            insight_bridge.assess_risk, source_files=scan["files"],
        )
    else:
        from app.domain.cases.application.case_app_service import case_service
        cases = await asyncio.to_thread(case_service.list_cases, limit=200)
        files = []
        for c in cases:
            fp = c.get("file_path", "")
            if fp:
                files.append({"relative_path": fp, "source_code": c.get("source_code", "")})
        result = await asyncio.to_thread(insight_bridge.assess_risk, source_files=files)
    return ok(result)


@router.post("/api/insights/lowcode")
def api_lowcode(body: LowcodeRequest):
    """低代码生成：用自然语言描述测试意图。"""
    description = (body.description or "").strip()
    if not description:
        return fail("请描述你想测试什么", 400)
    result = insight_bridge.generate_from_description(description)
    return ok(result)


@router.get("/api/insights/skill-path")
def api_skill_path():
    """职业发展路径。"""
    return ok(insight_bridge.get_skill_path())
