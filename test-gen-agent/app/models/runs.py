# app/models/runs.py
"""运行记录 Pydantic 模型。"""
from typing import Optional

from pydantic import BaseModel, Field


class RunQuery(BaseModel):
    """GET /api/runs 列表查询参数（含分页与过滤）。

    字段与 app.repositories.run_repo.RunRepo.list_records / count_records
    实际支持的过滤条件一一对应，未丢字段。
    """

    file_path: Optional[str] = Field(None, description="按文件路径模糊过滤")
    source: Optional[str] = Field(None, description="来源过滤: single/project/ws/task")
    passed: Optional[bool] = Field(None, description="按执行结果过滤: true/false")
    search: Optional[str] = Field(None, description="全文检索: 文件名或错误信息")
    limit: int = Field(50, ge=1, le=1000, description="每页条数")
    offset: int = Field(0, ge=0, description="偏移量")


class RunClearQuery(BaseModel):
    """DELETE /api/runs 清空运行记录的过滤参数。

    仅在显式指定 source 时按来源定向清理；缺省时清空全部记录。
    """

    source: Optional[str] = Field(None, description="来源过滤: single/project/ws/task")


__all__ = ["RunQuery", "RunClearQuery"]
