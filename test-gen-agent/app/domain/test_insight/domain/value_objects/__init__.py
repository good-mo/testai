"""TestInsight 上下文值对象集。"""
from app.domain.test_insight.domain.value_objects.attribution import (
    ATTRIBUTION_LABELS,
    Attribution,
    AttributionEnum,
)
from app.domain.test_insight.domain.value_objects.coverage import (
    COVERAGE_GOOD_THRESHOLD,
    COVERAGE_ZERO,
    Coverage,
)
from app.domain.test_insight.domain.value_objects.risk_level import (
    RiskLevel,
    RiskLevelEnum,
)
from app.domain.test_insight.domain.value_objects.test_result import (
    TEST_RESULT_ERROR,
    TEST_RESULT_FAILED,
    TEST_RESULT_PASSED,
    TEST_RESULT_UNKNOWN,
    TestResult,
    TestResultEnum,
)

__all__ = [
    "Attribution",
    "AttributionEnum",
    "ATTRIBUTION_LABELS",
    "Coverage",
    "COVERAGE_ZERO",
    "COVERAGE_GOOD_THRESHOLD",
    "RiskLevel",
    "RiskLevelEnum",
    "TestResult",
    "TestResultEnum",
    "TEST_RESULT_UNKNOWN",
    "TEST_RESULT_PASSED",
    "TEST_RESULT_FAILED",
    "TEST_RESULT_ERROR",
]
