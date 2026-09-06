"""Reports 域仓储实现。"""
import os
from typing import Optional, List, Dict, Any

class ReportsRepositoryImpl:
    """报告仓储实现。"""
    
    def __init__(self):
        self._output_dir = "reports"
        os.makedirs(self._output_dir, exist_ok=True)
    
    def generate_html_report(
        self,
        results: List[Dict[str, Any]],
        project_name: str = "Test Generation",
        title: str = "测试生成报告"
    ) -> str:
        from app.reports.generator import generate_html_report
        return generate_html_report(results, project_name, title)
    
    def generate_junit_report(
        self,
        results: List[Dict[str, Any]],
        project_name: str = "Test Generation"
    ) -> str:
        from app.reports.generator import generate_junit_report
        return generate_junit_report(results, project_name)
    
    def generate_markdown_report(
        self,
        results: List[Dict[str, Any]],
        project_name: str = "Test Generation",
        title: str = "测试生成报告"
    ) -> str:
        from app.reports.generator import generate_markdown_report
        return generate_markdown_report(results, project_name, title)
    
    def save_report(self, report_path: str, content: str) -> bool:
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False
    
    def list_reports(self, limit: int = 50) -> List[dict]:
        reports = []
        if os.path.isdir(self._output_dir):
            files = sorted(os.listdir(self._output_dir), reverse=True)
            for f in files[:limit]:
                path = os.path.join(self._output_dir, f)
                reports.append({
                    "id": f,
                    "name": f,
                    "path": path,
                })
        return reports
    
    def get_report(self, report_id: str) -> Optional[dict]:
        path = os.path.join(self._output_dir, report_id)
        if os.path.isfile(path):
            return {
                "id": report_id,
                "name": report_id,
                "path": path,
            }
        return None
    
    def delete_report(self, report_id: str) -> bool:
        path = os.path.join(self._output_dir, report_id)
        if os.path.isfile(path):
            os.remove(path)
            return True
        return False

reports_repository = ReportsRepositoryImpl()
__all__ = ["ReportsRepositoryImpl", "reports_repository"]
