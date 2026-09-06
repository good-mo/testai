# app/repositories/report_repo.py
"""报告中心数据访问层（Phase 3 重构 · 4 层对齐）。

本层是 reports 域报告产物访问入口：
  - 封装旧 app.reports.generator 的报告生成能力
  - 收敛报告文件/回收站的文件系统操作
供 report_service 消费，Service 不再直接回调旧域模块。
"""
import os
from typing import List, Optional

from app.repositories.case_repo import CaseRepo

REPORT_DIR = "reports"
TRASH_DIR = os.path.join(REPORT_DIR, ".trash")


class ReportRepo:
    """报告中心数据访问层（门面）。"""

    # ── 内部依赖 ─────────────────────────────────────────
    @staticmethod
    def _generator():
        from app.reports import generator
        return generator

    # ══════════════════════════════════════════════════════
    # 用例快照（报告数据来源）
    # ══════════════════════════════════════════════════════
    @classmethod
    def list_case_snapshots(cls, limit: int = 50) -> list:
        """读取最近用例作为报告数据源（复用 CaseRepo）。"""
        return CaseRepo.list_cases(limit=limit)

    # ══════════════════════════════════════════════════════
    # 生成报告
    # ══════════════════════════════════════════════════════
    @classmethod
    def generate_html(cls, results: list, project_name: str = "Test Generation",
                      title: str = "测试生成报告") -> str:
        return cls._generator().generate_html_report(results, project_name, title)

    @classmethod
    def generate_junit(cls, results: list) -> str:
        return cls._generator().generate_junit_report(results)

    @classmethod
    def generate_markdown(cls, results: list) -> str:
        return cls._generator().generate_markdown_report(results)

    # ══════════════════════════════════════════════════════
    # 报告文件管理
    # ══════════════════════════════════════════════════════
    @classmethod
    def list_reports(cls) -> List[dict]:
        if not os.path.isdir(REPORT_DIR):
            return []
        files = sorted(os.listdir(REPORT_DIR), reverse=True)
        return [{"name": f, "path": f"/api/reports/download/{f}"} for f in files]

    @classmethod
    def download_path(cls, filename: str) -> Optional[str]:
        report_path = os.path.join(REPORT_DIR, filename)
        return report_path if os.path.isfile(report_path) else None

    @classmethod
    def trash_report(cls, filename: str) -> bool:
        report_path = os.path.join(REPORT_DIR, filename)
        if not os.path.isfile(report_path):
            return False
        os.makedirs(TRASH_DIR, exist_ok=True)
        os.rename(report_path, os.path.join(TRASH_DIR, filename))
        return True

    @classmethod
    def list_trash(cls) -> list:
        if not os.path.isdir(TRASH_DIR):
            return []
        return sorted(os.listdir(TRASH_DIR), reverse=True)

    @classmethod
    def restore_report(cls, filename: str) -> bool:
        src = os.path.join(TRASH_DIR, filename)
        if not os.path.isfile(src):
            return False
        os.rename(src, os.path.join(REPORT_DIR, filename))
        return True

    @classmethod
    def purge_report(cls, filename: str) -> bool:
        path = os.path.join(TRASH_DIR, filename)
        if not os.path.isfile(path):
            return False
        os.remove(path)
        return True


report_repo = ReportRepo
