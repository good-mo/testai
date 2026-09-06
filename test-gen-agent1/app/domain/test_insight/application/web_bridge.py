"""TestInsight 应用层 → Web 适配（DTO 桥，阶段 B）。

职责：把 router 收到的 Web 请求体/查询参数翻译为 DDD 应用服务输入 DTO，
并把 DDD 应用服务返回的聚合结果规整为与既有 Web 契约一致的 dict。

- 归因字典：沿用领域层 ATTRIBUTION_LABELS（与既有 ATTRIBUTIONS 内容一致）；
- 列表 total 语义：保持既有 Web 端「当前页条数」口径，避免对外行为漂移；
- value 端点：把 DDD 拆分的 get_value / incident_avoidance 聚合为既有
  {"value":…, "incident_avoidance":…} 单接口输出。
"""
from __future__ import annotations

from typing import Optional

from app.domain.test_insight.application.dto import RecordTraceCommand, TraceListQuery
from app.domain.test_insight.application.test_insight_app_service import (
    test_insight_app_service,
)


def record_trace(file_path: str = "", result: str = "unknown",
                 passed_count: int = 0, failed_count: int = 0,
                 error_count: int = 0, coverage: float = 0,
                 attribution: str = "", note: str = "",
                 created_by: str = "manual") -> dict:
    """记录一次执行追溯（Web POST /api/insights/trace）。"""
    return test_insight_app_service.record_trace(RecordTraceCommand(
        file_path=file_path or "",
        result=result or "unknown",
        passed_count=passed_count or 0,
        failed_count=failed_count or 0,
        error_count=error_count or 0,
        coverage=coverage or 0.0,
        attribution=attribution or "",
        note=note or "",
        created_by=created_by or "manual",
        operator="manual",
    ))


def list_trace(file_path: Optional[str] = None, result: Optional[str] = None,
               limit: int = 50, offset: int = 0) -> dict:
    """列出测试执行追溯（Web GET /api/insights/trace）。"""
    res = test_insight_app_service.list(TraceListQuery(
        file_path=file_path or "",
        result=result or "",
        limit=limit or 50,
        offset=offset or 0,
    ))
    return {
        "runs": res["runs"],
        "stats": res["stats"],
        "total": len(res["runs"]),
        "attributions": res["attributions"],
    }


def prove_coverage(file_path: str) -> dict:
    """自证清白：调出某文件历史执行记录（Web GET /api/insights/trace/prove）。"""
    return test_insight_app_service.prove_coverage(file_path)


def get_value() -> dict:
    """价值量化（Web GET /api/insights/value）。"""
    value = test_insight_app_service.get_value()
    incidents = test_insight_app_service.incident_avoidance()
    return {"value": value, "incident_avoidance": incidents}


def assess_risk(source_files: Optional[list] = None) -> dict:
    """高风险模块预警（Web GET /api/insights/risk 底层计算）。"""
    return test_insight_app_service.assess_risk(source_files=source_files)


def generate_from_description(description: str) -> dict:
    """低代码生成（Web POST /api/insights/lowcode）。"""
    return test_insight_app_service.generate_from_description(description)


def get_skill_path() -> dict:
    """职业发展路径（Web GET /api/insights/skill-path）。"""
    return test_insight_app_service.skill_path()
