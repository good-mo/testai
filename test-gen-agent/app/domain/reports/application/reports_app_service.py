"""Reports 域应用服务。"""
from typing import Optional, List
from app.domain.reports.application.dto import (
    GenerateReportCommand,
    SaveReportCommand,
    ListReportsQuery,
    GetReportQuery,
    DeleteReportCommand,
)

class ReportsAppService:
    """报告应用服务。"""
    
    def __init__(self, repo=None):
        # 委托给传统 reports/generator.py
        from app.reports.generator import (
            generate_html_report,
            generate_junit_report,
            generate_markdown_report,
        )
        self._generate_html = generate_html_report
        self._generate_junit = generate_junit_report
        self._generate_markdown = generate_markdown_report
        self._reports = []  # 内存存储，实际应该用数据库
    
    def generate_report(self, cmd: GenerateReportCommand) -> str:
        """生成报告。"""
        if cmd.format == "html":
            return self._generate_html(cmd.results, cmd.project_name, cmd.title)
        elif cmd.format == "junit":
            return self._generate_junit(cmd.results, cmd.project_name)
        elif cmd.format == "markdown":
            return self._generate_markdown(cmd.results, cmd.project_name, cmd.title)
        else:
            raise ValueError(f"Unsupported format: {cmd.format}")
    
    def save_report(self, cmd: SaveReportCommand) -> bool:
        """保存报告。"""
        self._reports.append({
            "path": cmd.report_path,
            "content": cmd.content,
        })
        return True
    
    def list_reports(self, query: ListReportsQuery) -> List[dict]:
        """列出报告。"""
        return self._reports[:query.limit]
    
    def get_report(self, query: GetReportQuery) -> Optional[dict]:
        """获取报告。"""
        for report in self._reports:
            if report.get("id") == query.report_id:
                return report
        return None
    
    def delete_report(self, cmd: DeleteReportCommand) -> bool:
        """删除报告。"""
        self._reports = [r for r in self._reports if r.get("id") != cmd.report_id]
        return True

reports_app_service = ReportsAppService()
__all__ = ["ReportsAppService", "reports_app_service"]
