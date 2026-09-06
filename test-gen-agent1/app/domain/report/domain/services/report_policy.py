"""报告领域服务：报告产物生命周期与统计策略。

将"状态迁移合法性""是否可下载/可恢复""汇总统计口径"抽成无状态纯策略，
供聚合与应用层复用，规则单一出处，杜绝散落各处导致的判空/口径不一致。
"""
from __future__ import annotations

from app.domain.common.exceptions import DomainValidationError
from app.domain.report.domain.value_objects.report_state import (
    ReportState,
    ReportStateEnum,
)


class ReportLifecyclePolicy:
    """报告产物生命周期策略（无状态领域服务）。"""

    def ensure_transition_allowed(self, current: ReportState, target: ReportState) -> None:
        if target.is_purged:
            # 彻底清除是物理删除的终态，由仓储 purge 直接落地，不走状态机
            return
        if not current.can_transition_to(target):
            raise DomainValidationError(
                f"不允许从报告状态 '{current}' 迁移到 '{target}'"
            )

    def ensure_purgeable(self, current: ReportState) -> None:
        """只有回收站中的产物才可被彻底清除。"""
        if not current.is_trashed:
            raise DomainValidationError(
                f"报告产物状态为 '{current}'，只有回收站产物可被彻底删除"
            )

    def ensure_active(self, current: ReportState) -> None:
        """只有可用（未删除）的产物才可下载/进入活跃报告列表。"""
        if not current.is_active:
            raise DomainValidationError(
                f"报告产物处于 '{current}'，不可作为活跃报告访问"
            )


def compute_summary(results: list) -> dict:
    """由报告结果行统计整体汇总。

    Args:
        results: 每个文件的结果行（含 test_result.passed 与
                 coverage_report.line_coverage_pct）。

    Returns:
        {total, passed, failed, coverage}
    """
    results = results or []
    total = len(results)
    passed = sum(1 for r in results
                 if (r.get("test_result") or {}).get("passed"))
    failed = max(total - passed, 0)
    cov_values = [
        (r.get("coverage_report") or {}).get("line_coverage_pct")
        for r in results
        if (r.get("coverage_report") or {}).get("line_coverage_pct") is not None
    ]
    coverage = round(sum(cov_values) / len(cov_values), 2) if cov_values else 0
    return {"total": total, "passed": passed, "failed": failed, "coverage": coverage}


def build_result_rows(case_snapshots: list) -> list:
    """把用例快照归一化为报告结果行（业务口径单一出处）。

    对应当前 report_service.generate 中的逐用例快照解析逻辑，
    内聚在此，应用层与 Web 层不必再复制判空 / JSON 解析分支。
    """
    import json

    rows = []
    for c in case_snapshots or []:
        last_result = c.get("last_result", "")
        try:
            last_result_data = json.loads(last_result) if last_result else {}
        except (json.JSONDecodeError, TypeError):
            last_result_data = {}
        rows.append({
            "file_path": c.get("file_path", "unknown"),
            "generated_tests": c.get("test_code", ""),
            "test_result": last_result_data,
            "coverage_report": {},
            "retry_count": 0,
        })
    return rows


__all__ = [
    "ReportLifecyclePolicy",
    "ReportStateEnum",
    "compute_summary",
    "build_result_rows",
]
