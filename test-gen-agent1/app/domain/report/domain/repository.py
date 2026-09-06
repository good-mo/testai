"""报告聚合仓储接口（Repository Port）。

仅在 domain 层定义、由 infrastructure 实现。应用层依赖此接口而非具体
实现，便于测试替换（内存/文件仓储）与多存储切换。

报告产物为文件制品（报告中心 reports 目录），仓储以"聚合 Report"为粒度，
把 生成 / 列表 / 下载路径 / 移入回收站 / 恢复 / 彻底删除 等文件语义
封装为聚合读写，保证生命周期一致。
"""
from __future__ import annotations

from typing import List, Optional, Protocol, Tuple

from app.domain.report.domain.entities.report import Report


class ReportRepository(Protocol):
    """报告聚合仓储契约。"""

    def next_name(self, report_format: str = "html") -> str: ...

    def list_case_snapshots(self, limit: int = 50) -> list:
        """读取参与报告汇总的用例快照（报告数据来源）。"""
        ...

    def generate(self, report: Report, results: list) -> str:
        """把结果行导出为指定格式报告文件，返回报告文件完整路径。"""
        ...

    def list_reports(self) -> List[dict]: ...

    def find_report(self, report_name: str) -> Optional[Report]: ...

    def download_path(self, report_name: str) -> Optional[str]: ...

    def trash_report(self, report: Report) -> bool: ...

    def list_trash(self) -> Tuple[List[Report], int]: ...

    def restore_report(self, report: Report) -> bool: ...

    def purge_report(self, report: Report) -> bool: ...


__all__ = ["ReportRepository"]
