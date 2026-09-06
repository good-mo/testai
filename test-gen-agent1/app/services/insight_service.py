# app/services/insight_service.py
"""测试洞察业务逻辑层（DDD 迁移 A→B→C 后的薄门面）。

test_insight 域已按 DDD 落地（app/domain/test_insight/），本 Service 演进为
**薄门面**，供 router / generation 等既有调用方继续以原签名访问：

  - 阶段 A：领域/应用层就绪（app/domain/test_insight/application/…）；
  - 阶段 B：Service 改为经应用服务 TestInsightAppService 统一编排访问；
  - 阶段 C：业务规则（执行结果/覆盖率/异常归因/风险/价值策略）下沉至领域层，
            本类不再承载任何业务规则，仅做参数到 DTO 的翻译与结果透传。

对外公共方法签名与返回结构保持不变，保证调用方零回归。
"""
from __future__ import annotations

from typing import Optional

from app.domain.test_insight.application.dto import RecordTraceCommand, TraceListQuery
from app.domain.test_insight.application.test_insight_app_service import (
    test_insight_app_service,
)


class InsightService:
    """测试洞察服务（对 test_insight 应用服务的薄门面）。"""

    def get_value(self) -> dict:
        """价值量化：缺陷价值 / 覆盖价值 / 避免事故估算。"""
        value = test_insight_app_service.get_value()
        incidents = test_insight_app_service.incident_avoidance()
        return {"value": value, "incident_avoidance": incidents}

    def list_trace(self, file_path: Optional[str] = None,
                   result: Optional[str] = None, limit: int = 50,
                   offset: int = 0) -> dict:
        """列出测试执行追溯记录。"""
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

    def record_trace(self, file_path: str = "", result: str = "unknown",
                     passed_count: int = 0, failed_count: int = 0,
                     error_count: int = 0, coverage: float = 0,
                     attribution: str = "", note: str = "",
                     created_by: str = "manual") -> dict:
        """记录一次执行追溯，形成可审计证据（业务规则由领域层守护）。"""
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

    def prove_coverage(self, file_path: str) -> dict:
        """自证清白：针对某文件调出历史执行记录。"""
        return test_insight_app_service.prove_coverage(file_path)

    def assess_risk(self, source_files: Optional[list] = None) -> dict:
        """高风险模块预警。"""
        return test_insight_app_service.assess_risk(source_files=source_files)

    def generate_from_description(self, description: str) -> dict:
        """低代码生成：用自然语言描述测试意图。"""
        return test_insight_app_service.generate_from_description(description)

    def get_skill_path(self) -> dict:
        """职业发展路径。"""
        return test_insight_app_service.skill_path()


# 单例门面（进程内复用，供 router / generation 引用）
insight_service = InsightService()
