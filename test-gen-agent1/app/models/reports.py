# app/models/reports.py
"""报告中心 Pydantic 请求体模型。

数据访问经 app.services.report_service 统一处理（复用 case/defect 数据源）。
字段自 `app/routers/reports_compat.py` 中 `read_body` 实际使用的请求体归纳，
前端 TestPilot 风格驼峰字段与后端 snake_case 别名并存。所有模型默认
`extra: allow`，避免遗漏新增字段导致 400。
"""

from typing import List

from pydantic import BaseModel, Field


class ReportIdBody(BaseModel):
    """报告详情/分享请求体（携带目标报告 id）。"""

    id: str = Field("", description="报告 ID（缺省时返回默认记录）")

    model_config = {"extra": "allow"}


class ReportPageQuery(BaseModel):
    """报告分页列表查询请求体。"""

    keyword: str = Field("", description="搜索关键字")
    pageSize: int = Field(10, description="每页条数")
    current: int = Field(1, description="页码")

    model_config = {"extra": "allow"}


class ReportBatchParamBody(BaseModel):
    """报告批量导出 ID 集合查询请求体。"""

    selectAll: bool = Field(False, description="是否全选（返回全部报告 ID）")
    selectIds: List[str] = Field([], description="勾选中的报告 ID")
    excludeIds: List[str] = Field([], description="需要排除的报告 ID")

    model_config = {"extra": "allow"}
