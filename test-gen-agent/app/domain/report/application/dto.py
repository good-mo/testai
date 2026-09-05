"""报告应用层输入/输出 DTO。

面向聚合操作接收显式 DTO（而非裸 dict），与 Web 层 Pydantic 请求体
解耦。此处用 dataclass 表达简单命令，保持零框架依赖。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GenerateCommand:
    """生成测试报告命令。

    format_type: html / junit / markdown（默认 html）
    title / project_name: 仅对 html 生效，可覆盖默认标题。
    case_limit: 参与汇总的用例快照数量上限。
    """
    format_type: str = "html"
    title: str = "测试生成报告"
    project_name: str = "Test Generation"
    case_limit: int = 50


@dataclass
class ReportQuery:
    """报告列表查询（活跃报告）。"""


@dataclass
class DownloadCommand:
    """下载 / 校验报告命令。"""
    report_name: str


@dataclass
class TrashCommand:
    """移入回收站命令。"""
    report_name: str
    operator: str = "system"


@dataclass
class RestoreCommand:
    """从回收站恢复命令。"""
    report_name: str
    operator: str = "system"


@dataclass
class PurgeCommand:
    """彻底删除命令。"""
    report_name: str
    operator: str = "system"


@dataclass
class TrashListQuery:
    """回收站列表查询。"""
    limit: int = 100
    offset: int = 0


__all__ = [
    "GenerateCommand",
    "ReportQuery",
    "DownloadCommand",
    "TrashCommand",
    "RestoreCommand",
    "PurgeCommand",
    "TrashListQuery",
]
