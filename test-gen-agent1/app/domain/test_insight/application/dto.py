"""TestInsight 应用层输入/输出 DTO。

应用层面向"测试洞察"操作接收显式 DTO（而非裸 dict），与 Web 层
Pydantic 请求体解耦。此处用 dataclass 表达简单命令，保持零框架依赖。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RecordTraceCommand:
    """记录一次测试执行（写入审计证据）。"""

    file_path: str
    result: str = "unknown"
    passed_count: int = 0
    failed_count: int = 0
    error_count: int = 0
    coverage: float = 0.0
    attribution: str = ""
    note: str = ""
    created_by: str = "manual"
    operator: str = "system"


@dataclass
class TraceListQuery:
    file_path: str = ""
    result: str = ""
    limit: int = 50
    offset: int = 0
