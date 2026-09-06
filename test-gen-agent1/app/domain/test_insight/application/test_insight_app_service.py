"""TestInsight 应用服务（Application Service / Use Case 门面）。

职责：
  1. 作为 Web 层与领域层之间的用例编排入口；
  2. 承载"执行追溯"用例的事务边界：加载聚合 → 执行领域命令 →
     保存聚合 → 发布领域事件；
  3. 承载"自证清白 / 价值量化 / 风险预警 / 低代码生成"等读取与分析
     用例（跨 defects / cases 等其它限界上下文），经由仓储防腐层代理。

保持瘦：只做编排，不写业务规则（业务规则在领域层聚合内）。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.domain.common.domain_events import event_bus
from app.domain.test_insight.application.dto import RecordTraceCommand, TraceListQuery
from app.domain.test_insight.domain.entities.trace_run import TraceRun
from app.domain.test_insight.domain.repository import TestInsightRepository
from app.domain.test_insight.domain.value_objects.attribution import (
    ATTRIBUTION_LABELS,
)
from app.domain.test_insight.infrastructure.test_insight_repository_impl import (
    InsightRepoAdapter,
)

logger = logging.getLogger(__name__)


class TestInsightAppService:
    """测试洞察用例编排服务。"""

    def __init__(self, repo: TestInsightRepository = None):
        self._repo: TestInsightRepository = repo or InsightRepoAdapter()

    # ── 执行追溯：记录入账 ─────────────────────────
    def record_trace(self, cmd: RecordTraceCommand) -> dict:
        run = TraceRun(
            trace_id=self._repo.next_id(),
            file_path=cmd.file_path,
            result=cmd.result,
            passed_count=cmd.passed_count,
            failed_count=cmd.failed_count,
            error_count=cmd.error_count,
            coverage=cmd.coverage,
            attribution=cmd.attribution,
            note=cmd.note,
            created_by=cmd.created_by,
        )
        run.record(cmd.operator)
        self._repo.save(run)
        self._publish(run)
        return run.to_dict()

    # ── 执行追溯：读取 / 自证清白 ──────────────────
    def get(self, trace_id: str) -> Optional[dict]:
        run = self._repo.find_by_id(trace_id)
        return run.to_dict() if run else None

    def list(self, query: TraceListQuery) -> dict:
        items, total = self._repo.list(
            file_path=query.file_path, result=query.result,
            limit=query.limit, offset=query.offset,
        )
        return {
            "runs": [r.to_dict() for r in items],
            "stats": self._repo.stats(),
            "total": total,
            "attributions": dict(ATTRIBUTION_LABELS),
        }

    def prove_coverage(self, file_path: str) -> dict:
        """自证清白：调出某文件全部历史执行记录。"""
        runs = self._repo.list_by_file(file_path, limit=100)
        serialized = [r.to_dict() for r in runs]
        last_run = serialized[0] if serialized else None
        has_passed_evidence = any(r.is_passed for r in runs)
        return {
            "file_path": file_path,
            "total_runs": len(runs),
            "last_run": last_run,
            "has_passed_evidence": has_passed_evidence,
            "coverage_snapshot": last_run["coverage"] if last_run else 0,
            "runs": serialized,
        }

    def stats(self) -> dict:
        return self._repo.stats()

    # ── 跨域分析 / 纯业务规则用例（代理到防腐层）────
    def get_value(self) -> dict:
        return self._repo.value()

    def incident_avoidance(self) -> dict:
        return self._repo.incident_avoidance()

    def assess_risk(self, source_files: Optional[list] = None) -> dict:
        return self._repo.assess_risk(source_files=source_files)

    def generate_from_description(self, description: str) -> dict:
        return self._repo.generate_from_description(description)

    def skill_path(self) -> dict:
        return self._repo.skill_path()

    # ── 内部助手 ───────────────────────────────────
    def _publish(self, run: TraceRun) -> None:
        for ev in run.pull_domain_events():
            event_bus.dispatch(ev)


# 单例门面（进程内复用）
test_insight_app_service = TestInsightAppService()
