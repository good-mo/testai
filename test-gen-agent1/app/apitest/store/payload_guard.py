# -*- coding: utf-8 -*-
"""apitest 请求体字段守卫。

为什么需要它
------------
接口测试域的路由（`app/routers/apitest.py`）普遍采用「原样透传」写法：

    body = await req.json()
    item = apitest_service.create_definition(**body)

而 store 层的 `create_xxx(**kwargs)` / `update_xxx(**fields)` 签名是封闭的。
一旦前端多传一个字段（TestPilot 前端普遍发 camelCase，如 `projectId`），
就会出现两类 500：

  1. create：`TypeError: create_definition() got an unexpected keyword argument 'projectId'`
  2. update：`sqlite3.OperationalError: no such column: projectId`
     （因为 `_update()` 用 `data.keys()` 直接拼 SQL SET 子句）

这些本应是 400（参数错误），却被打成 500，前端只能看到「服务器内部错误」，
定位成本极高。

本模块提供三个纯函数，在路由把 body 交给 service 之前做一次收口：
  - 过滤掉 store 层签名不接受的键（避免 TypeError / SQL 注入式列名拼错）
  - 把 camelCase 别名归一化为 store 层认识的 snake_case
  - 顺手把 dict/list 字段序列化为 JSON 字符串（store 层用 TEXT 列存储）
"""

import json
from typing import Any, Dict, Set

# camelCase（前端）→ snake_case（store 层签名）
_CAMEL_ALIASES: Dict[str, str] = {
    "projectId": "project_id",
    "apiDefinitionId": "api_definition_id",
    "environmentId": "environment_id",
    "baseUrl": "base_url",
    "statusCode": "status_code",
    "responseCode": "response_code",
    "responseBody": "response_body",
    "responseHeaders": "response_headers",
    "databaseConfig": "database_config",
    "versionId": "version_id",
    "refId": "ref_id",
    "moduleId": "module_id",
    "scenarioId": "scenario_id",
}


# 各资源的 store 层签名白名单。
# 说明：这里显式列出而不做自动 introspect，是因为 store 函数是模块级函数、
# 每次 import 都要遍历会有额外开销；且白名单本身即是「接口契约文档」，
# 新增字段时必须显式登记，避免误放行。
_ALLOWED_FIELDS: Dict[str, Set[str]] = {
    "definition": {
        "name", "protocol", "method", "path", "headers", "body", "query",
        "params", "description", "tags", "project_id", "module_id", "version",
    },
    "api_case": {
        "name", "api_definition_id", "request", "asserts", "pre_scripts",
        "post_scripts", "pre_sql", "post_sql", "variables",
        "logic_controllers", "environment_id", "status", "priority",
        "description", "project_id", "tags",
    },
    "scenario": {
        "name", "steps", "description", "status", "environment_id",
        "project_id", "tags",
    },
    "mock": {
        "name", "api_definition_id", "method", "path", "status_code",
        "response_body", "response_headers", "delay_ms", "enabled",
        "description", "project_id",
    },
    "environment": {
        "name", "base_url", "headers", "variables", "description",
        "project_id", "script", "database_config", "config",
    },
}


# 需要 JSON 序列化的字段（store 层以 TEXT 列存储 + json.loads 读回）
_JSON_FIELDS: Dict[str, Set[str]] = {
    "definition": {"headers", "query", "params", "tags"},
    "api_case": {"request", "asserts", "pre_scripts", "post_scripts",
                 "pre_sql", "post_sql", "variables", "logic_controllers", "tags"},
    "scenario": {"steps", "tags"},
    "mock": {"response_headers"},
    "environment": {"headers", "variables", "database_config", "config"},
}


def normalize_payload(resource: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """把前端请求体归一化为 store 层可安全消费的字典。

    处理顺序：camelCase 别名 → 白名单过滤 → JSON 序列化。
    未知资源类型（resource 未在 _ALLOWED_FIELDS 中）原样返回，
    避免误伤尚未登记的调用点。

    Args:
        resource: 资源类型，取值见 _ALLOWED_FIELDS 的键。
        body:     路由从 request.json() 拿到的原始请求体。

    Returns:
        归一化后的新字典（不修改入参）。
    """
    if not isinstance(body, dict):
        return {}
    allowed = _ALLOWED_FIELDS.get(resource)
    if allowed is None:
        return dict(body)

    result: Dict[str, Any] = {}
    for key, value in body.items():
        field = _CAMEL_ALIASES.get(key, key)
        if field not in allowed:
            # 前端多传的字段：静默丢弃。
            # 与其让 store 层抛 TypeError/OperationalError 打 500，
            # 不如按「忽略未知字段」处理，兼容前端版本差异。
            continue
        if field in _JSON_FIELDS.get(resource, set()):
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            elif value is None:
                value = ""
        result[field] = value
    return result


def unknown_fields(resource: str, body: Dict[str, Any]) -> list:
    """返回 body 中该资源不认识的字段名（已排除 camelCase 别名）。

    供路由在需要严格校验时返回 400 使用；当前默认策略是忽略，
    保留此函数便于将来切换成严格模式。
    """
    allowed = _ALLOWED_FIELDS.get(resource)
    if allowed is None or not isinstance(body, dict):
        return []
    return [
        key for key in body
        if _CAMEL_ALIASES.get(key, key) not in allowed
    ]


def allowed_fields(resource: str) -> Set[str]:
    """返回某资源允许写入的字段集合（测试与文档用）。"""
    return set(_ALLOWED_FIELDS.get(resource, ()))
