"""报告应用服务（Application Service / Use Case 门面）。

职责：
  1. 作为路由器与领域层之间的用例编排入口；
  2. 承载"报告"用例的事务边界：加载聚合 → 执行领域命令 → 保存聚合 →
     发布领域事件；
  3. 把报告生成（汇总口径）作为编排逻辑，领域规则留在领域层策略内。

保持瘦：只做编排，不写业务规则（汇总口径、状态机在领域层策略/聚合内）。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.domain.common.domain_events import event_bus
from app.domain.report.application.dto import (
    DownloadCommand,
    GenerateCommand,
    PurgeCommand,
    RestoreCommand,
    TrashCommand,
    TrashListQuery,
)
from app.domain.report.domain.entities.report import Report
from app.domain.report.domain.exceptions import ReportNotFound
from app.domain.report.domain.services.report_policy import (
    build_result_rows,
    compute_summary,
)
from app.domain.report.infrastructure.report_repository_impl import ReportRepoAdapter

logger = logging.getLogger(__name__)


class ReportAppService:
    """报告用例编排服务。"""

    def __init__(self, repo=None):
        # 允许依赖注入（便于测试替身）；默认使用既有文件仓储适配器
        self._repo = repo or ReportRepoAdapter()

    # ── 生成报告 ─────────────────────────────────────
    def generate(self, cmd: GenerateCommand) -> Optional[dict]:
        """汇总用例快照并导出指定格式报告。

        Returns:
            报告聚合 dict（含 report_path 完整文件路径）；无用例数据返回 None。
        """
        case_limit = max(1, int(cmd.case_limit or 50))
        snapshots = self._repo.list_case_snapshots(limit=case_limit)
        if not snapshots:
            return None
        rows = build_result_rows(snapshots)
        summary = compute_summary(rows)

        report = Report(
            report_name=self._repo.next_name(cmd.format_type),
            report_format=cmd.format_type,
            title=cmd.title,
            project_name=cmd.project_name,
            summary=summary,
        )
        # 领域校验格式（非法格式抛 DomainValidationError）
        _ = report.report_format

        report_path = self._repo.generate(report, rows)
        report.set_summary(summary)
        result = report.to_dict()
        result["report_path"] = report_path
        self._publish(report)
        return result

    # ── 列表 / 下载 ─────────────────────────────────
    def list_reports(self) -> list:
        """列出活跃报告。"""
        return self._repo.list_reports()

    def download(self, cmd: DownloadCommand) -> Optional[str]:
        """返回报告文件下载绝对路径（不存在返回 None）。"""
        return self._repo.download_path(cmd.report_name)

    # ── 回收站 ──────────────────────────────────────
    def trash(self, cmd: TrashCommand) -> bool:
        report = self._find_active_or_raise(cmd.report_name)
        report.trash(cmd.operator)
        if not self._repo.trash_report(report):
            raise ReportNotFound(f"报告 {cmd.report_name} 不存在")
        self._publish(report)
        return True

    def list_trash(self, query: TrashListQuery) -> dict:
        items, total = self._repo.list_trash(limit=query.limit, offset=query.offset)
        return {"list": [r.to_dict() for r in items], "total": total}

    def restore(self, cmd: RestoreCommand) -> bool:
        report = self._find_trashed_or_raise(cmd.report_name)
        report.restore(cmd.operator)
        if not self._repo.restore_report(report):
            raise ReportNotFound(f"报告 {cmd.report_name} 不在回收站")
        self._publish(report)
        return True

    def purge(self, cmd: PurgeCommand) -> bool:
        report = self._find_trashed_or_raise(cmd.report_name)
        report.mark_purged(cmd.operator)
        if not self._repo.purge_report(report):
            raise ReportNotFound(f"报告 {cmd.report_name} 不存在")
        self._publish(report)
        return True

    # ── 内部助手 ───────────────────────────────────
    def _find_active_or_raise(self, report_name: str) -> Report:
        report = self._repo.find_report(report_name)
        if report is None or report.is_trashed:
            raise ReportNotFound(f"报告 {report_name} 不存在")
        return report

    def _find_trashed_or_raise(self, report_name: str) -> Report:
        report = self._repo.find_report(report_name)
        if report is None or not report.is_trashed:
            raise ReportNotFound(f"回收站中不存在该报告: {report_name}")
        return report

    @staticmethod
    def _publish(report: Report) -> None:
        events = report.pull_domain_events()
        for ev in events:
            event_bus.dispatch(ev)


# 单例门面（进程内复用）
report_app_service = ReportAppService()

__all__ = ["ReportAppService", "report_app_service"]
