# app/models/scripts.py
"""脚本健康度 Pydantic 模型。"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ScriptCreate(BaseModel):
    name: str = Field(..., min_length=1)
    file_path: str = Field("")
    framework: str = Field("")
    description: str = Field("")
    locators: Optional[List[Dict]] = Field(None)


class ScriptUpdate(BaseModel):
    name: Optional[str] = None
    file_path: Optional[str] = None
    framework: Optional[str] = None
    description: Optional[str] = None
    locators: Optional[List[Dict]] = None
    status: Optional[str] = None


class ExecutionRecordCreate(BaseModel):
    success: bool = Field(True)
    duration: float = Field(0.0)
    error_type: str = Field("")
    error_message: str = Field("")
    locator_failures: Optional[List[Dict]] = None


class LocatorEvalRequest(BaseModel):
    strategy: str = Field("")
    selector: str = Field("")


class ScriptListQuery(BaseModel):
    """脚本列表查询参数（分页 + 过滤）。

    收敛 GET /api/scripts 的散落 query 参数，对齐 runs 域 RunQuery 用法。
    原签名：status / framework / search / limit=100 / offset=0。
    """
    status: Optional[str] = None
    framework: Optional[str] = None
    search: Optional[str] = None
    limit: int = Field(100)
    offset: int = Field(0)


class ScriptExecutionsQuery(BaseModel):
    """脚本执行历史查询参数。

    收敛 GET /api/scripts/{id}/executions 的散落 query 参数 limit。
    """
    limit: int = Field(20)
