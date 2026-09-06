"""接口测试 Web 输入归一化。"""

from __future__ import annotations

import json
from typing import Any


_STRUCT_FIELDS = {
    "definition": {"headers", "query", "params", "tags"},
    "api_case": {"request", "asserts", "pre_scripts", "post_scripts", "pre_sql", "post_sql", "variables", "logic_controllers", "tags"},
    "scenario": {"steps", "tags"},
    "mock": {"response_headers"},
    "environment": {"variables"},
}


def normalize_payload(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    """将 Web 层结构字段转换为稳定的 JSON 文本，供仓储持久化。"""
    result = dict(payload)
    for field in _STRUCT_FIELDS.get(kind, set()):
        value = result.get(field)
        if isinstance(value, (dict, list)):
            result[field] = json.dumps(value, ensure_ascii=False)
    return result


__all__ = ["normalize_payload"]
