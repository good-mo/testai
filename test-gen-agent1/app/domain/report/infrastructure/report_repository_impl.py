"""报告聚合仓储实现（Adapter）。

把"面向聚合 Report 的仓储接口"翻译为既有 ReportRepo（四层 Repository）
的文件语义命令，实现防腐层（Anti-Corruption Layer）。复用已验证的
生成 / 文件管理逻辑，同时让领域层获得聚合级读写语义；后续如需换存储
仅替换本文件。
"""
from __future__ import annotations

import time
import uuid
from typing import List, Optional, Tuple

from app.domain.report.domain.entities.report import Report
from app.repositories.report_repo import ReportRepo


class ReportRepoAdapter:
    """将既有 ReportRepo 封装为面向聚合 Report 的仓储。"""

    def next_name(self, report_format: str = "html") -> str:
        """生成一个带格式后缀的报告文件名。"""
        ts = time.strftime("%Y%m%d_%H%M%S")
        return f"report_{ts}_{uuid.uuid4().hex[:4]}.{report_format}"

    def list_case_snapshots(self, limit: int = 50) -> list:
        """读取参与报告汇总的用例快照（复用 ReportRepo 数据源门面）。"""
        return ReportRepo.list_case_snapshots(limit=limit)

    # ── 生成报告 ─────────────────────────────────────
    def generate(self, report: Report, results: list) -> str:
        """把结果行导出为指定格式报告文件，返回完整文件路径。"""
        fmt = report.report_format.value
        if fmt == "junit":
            return ReportRepo.generate_junit(results)
        if fmt == "markdown":
            return ReportRepo.generate_markdown(results)
        return ReportRepo.generate_html(results, report.project_name, report.title)

    # ── 读：聚合重建 ─────────────────────────────────
    def find_report(self, report_name: str) -> Optional[Report]:
        """在活跃报告/回收站中查找报告产物。"""
        for f in self.list_reports():
            if str(f.get("name")) == report_name:
                return Report(report_name=report_name,
                              report_format=_guess_format(report_name))
        reports, _ = self.list_trash()
        for row in reports:
            if row.name == report_name:
                return row
        return None

    def list_reports(self) -> List[dict]:
        """列出活跃报告（维持既有 {name, path} 结构）。"""
        return ReportRepo.list_reports()

    def list_trash(self, limit: int = 100, offset: int = 0) -> Tuple[List[Report], int]:
        rows = ReportRepo.list_trash()
        items = rows[offset:offset + limit]
        reports = [
            Report(report_name=name, report_format=_guess_format(name),
                   state="trash")
            for name in items
        ]
        return reports, len(rows)

    def download_path(self, report_name: str) -> Optional[str]:
        """返回活跃报告的文件下载绝对路径（不存在返回 None）。"""
        return ReportRepo.download_path(report_name)

    # ── 写：文件生命周期 ─────────────────────────────
    def trash_report(self, report: Report) -> bool:
        return ReportRepo.trash_report(report.name)

    def restore_report(self, report: Report) -> bool:
        return ReportRepo.restore_report(report.name)

    def purge_report(self, report: Report) -> bool:
        return ReportRepo.purge_report(report.name)


def _guess_format(filename: str) -> str:
    """由报告文件名后缀推断格式。"""
    suffix = str(filename).rsplit(".", 1)[-1].lower() if "." in str(filename) else "html"
    return suffix if suffix in ("html", "junit", "markdown") else "html"


__all__ = ["ReportRepoAdapter"]
