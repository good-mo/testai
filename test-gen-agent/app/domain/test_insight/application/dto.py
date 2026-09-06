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


# ==============================================================================
# 从 models/insights.py 迁移
# ==============================================================================

# app/models/insights.py
"""测试洞察 Pydantic 模型。"""
from pydantic import BaseModel, Field


class TraceRecord(BaseModel):
    file_path: str = Field("")
    result: str = Field("unknown")
    passed_count: int = Field(0)
    failed_count: int = Field(0)
    error_count: int = Field(0)
    coverage: float = Field(0)
    attribution: str = Field("")
    note: str = Field("")
    created_by: str = Field("manual")


class LowcodeRequest(BaseModel):
    description: str = Field(..., description="用自然语言描述测试意图")
