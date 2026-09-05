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
