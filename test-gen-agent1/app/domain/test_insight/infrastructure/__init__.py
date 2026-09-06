"""TestInsight 上下文基础设施层：对接既有存储（InsightRepo / trace.db）。"""
from app.domain.test_insight.infrastructure.test_insight_repository_impl import (
    InsightRepoAdapter,
)

__all__ = ["InsightRepoAdapter"]
