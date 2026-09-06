# app/routers/apitest_compat_base.py
"""apitest_compat 拆分共享层（Phase D 拆分超大文件）。

将 2712 行单文件的统一导入与模块级工具沉淀于此，
供 definition/scenario/case/mock 各分段模块复用。
"""

import json
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.response import read_body
from app.logging_config import get_logger
from app.services.apitest_service import apitest_service

__all__ = [
    "json",
    "uuid",
    "Any",
    "Dict",
    "List",
    "APIRouter",
    "Request",
    "JSONResponse",
    "read_body",
    "get_logger",
    "apitest_service",
    "_read_body",
    "_filter_module_tree",
    "_filter_module_tree_by_protocol",
    "_build_trash_count_map",
]


async def _read_body(request: Request) -> dict:
    """安全读取请求体。"""
    try:
        return await read_body(request)
    except Exception:
        return {}


def _filter_module_tree(tree, module_ids):
    """按模块 id 集合过滤模块树，仅保留指定模块（含子节点）。"""
    module_ids = set(module_ids)
    def _keep(nodes):
        kept = []
        for node in nodes:
            if node.get("type") == "API":
                continue
            if node.get("id") in module_ids:
                kept.append(node)
            else:
                children = _keep(node.get("children", []))
                if children:
                    node = dict(node)
                    node["children"] = children
                    kept.append(node)
        return kept
    return _keep(tree)


def _filter_module_tree_by_protocol(tree, protocols):
    """按协议过滤模块树中的 API 节点。"""
    protocols = set(protocols)
    def _apply(nodes):
        result = []
        for node in nodes:
            node = dict(node)
            if node.get("type") == "API":
                attach = node.get("attachInfo") or {}
                proto = attach.get("protocol", "HTTP")
                if proto in protocols:
                    result.append(node)
            else:
                children = _apply(node.get("children", []))
                node["children"] = children
                result.append(node)
        return result
    return _apply(tree)


def _build_trash_count_map():
    """构建回收站模块计数映射：{moduleId: count, all: total}。"""
    result = {"all": 0, "root": 0}
    try:
        # 用 DB COUNT 替代 len(全量拉取)，避免 limit 截断导致计数不准
        total = apitest_service.count_trash_definitions()
        result["all"] = total
        result["root"] = total
        for m in apitest_service.list_modules("definition"):
            result[m.get("id", "")] = 0
    except Exception:
        pass
    return result
