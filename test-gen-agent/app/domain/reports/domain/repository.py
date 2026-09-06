"""Reports 域仓储接口。"""
from typing import Optional, Protocol, List, Dict, Any

class ReportRepository(Protocol):
    """报告仓储接口。"""
    
    def generate_html_report(
        self,
        results: List[Dict[str, Any]],
        project_name: str = "Test Generation",
        title: str = "测试生成报告"
    ) -> str:
        """生成 HTML 格式报告。"""
        ...
    
    def generate_junit_report(
        self,
        results: List[Dict[str, Any]],
        project_name: str = "Test Generation"
    ) -> str:
        """生成 JUnit XML 格式报告。"""
        ...
    
    def generate_markdown_report(
        self,
        results: List[Dict[str, Any]],
        project_name: str = "Test Generation",
        title: str = "测试生成报告"
    ) -> str:
        """生成 Markdown 格式报告。"""
        ...
    
    def save_report(self, report_path: str, content: str) -> bool:
        """保存报告到文件。"""
        ...
    
    def list_reports(self, limit: int = 50) -> List[dict]:
        """列出报告。"""
        ...
    
    def get_report(self, report_id: str) -> Optional[dict]:
        """获取报告。"""
        ...
    
    def delete_report(self, report_id: str) -> bool:
        """删除报告。"""
        ...

__all__ = ["ReportRepository"]
