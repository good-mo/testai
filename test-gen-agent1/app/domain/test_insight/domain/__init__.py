"""TestInsight 领域层（domain layer）。

仅表达"测试洞察"业务概念与规则（执行追溯、异常归因、覆盖率、
风险分级、价值量化），不依赖 FastAPI / sqlite / 具体存储实现。
"""
from app.domain.test_insight.domain.entities.trace_run import TraceRun
from app.domain.test_insight.domain.repository import TestInsightRepository
from app.domain.test_insight.domain.value_objects.attribution import (
    Attribution,
    AttributionEnum,
)
from app.domain.test_insight.domain.value_objects.risk_level import RiskLevel, RiskLevelEnum
from app.domain.test_insight.domain.value_objects.test_result import (
    TestResult,
    TestResultEnum,
)

__all__ = [
    "TraceRun",
    "TestInsightRepository",
    "Attribution",
    "AttributionEnum",
    "RiskLevel",
    "RiskLevelEnum",
    "TestResult",
    "TestResultEnum",
]
