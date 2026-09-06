# app/test_plan/router_dashboard_common.py
"""工作台 Dashboard 公共辅助函数（自 router_dashboard.py 拆分）。

供各 Dashboard 分段路由共用：请求体解析与评审列表项格式转换。
"""

from typing import Any, Dict

from fastapi import Request

from app.core.response import read_body


# 用例内部 status → 前端 ReviewStatus ('PREPARED'/'UNDERWAY'/'COMPLETED')
_CASE_STATUS_TO_REVIEW_STATUS = {
    "draft": "PREPARED",
    "approved": "COMPLETED",
    "rejected": "COMPLETED",
    "deprecated": "COMPLETED",
    "review": "UNDERWAY",
    "pending": "UNDERWAY",
    "in_review": "UNDERWAY",
}


def _review_status(status: str) -> str:
    """将内部用例状态映射为前端 ReviewStatus。"""
    return _CASE_STATUS_TO_REVIEW_STATUS.get(status or "draft", "PREPARED")


def _case_to_review_item(case: Dict[str, Any]) -> Dict[str, Any]:
    """将用例转为评审列表项格式。"""
    status = case.get("status", "draft")
    return {
        "id": case.get("id", ""),
        "num": case.get("num", 0),
        "name": case.get("title", ""),
        "title": case.get("title", ""),
        "priority": case.get("priority", "P2"),
        "status": _review_status(status),
        "testType": case.get("test_type", "functional"),
        "passRate": 0,
        "caseCount": 1,
        "reviewPassRule": "SINGLE",
        "createTime": int((case.get("created_at", 0) or 0) * 1000),
        "updateTime": int((case.get("updated_at", 0) or 0) * 1000),
        "createUser": "admin",
        "createUserName": "admin",
    }

async def _parse_body(request: Request) -> Dict[str, Any]:
    """安全解析请求体（委托 app.core.response.read_body）。"""
    return await read_body(request)
