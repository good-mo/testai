"""数据工厂应用层 → Web 层契约映射（DTO 桥 / Anti-Corruption 翻译）。

数据工厂域完成 **阶段 A（DDD 领域/应用层就绪）** 后，进入 **阶段 B**
（router 改调 `datafactory_app_service`）时，需保证对外 API schema 与
既有 `DatafactoryService` 时代逐字段一致，避免破坏前端与既有契约测试。

经核对，DDD 聚合 `to_dict()` 与既有 DatafactoryRepo 输出在模板/批次字段
上已完全对齐（id/name/description/category/schema/deps/tags/status/
created_at/updated_at），唯二差异点由本映射层补齐：

1. **造数生成**：既有 `generate_data` 返回含 `batch_id` 的产物；
   DDD `DataBatch.to_dict()` 以 `id` 表达批次主键。这里补 `batch_id`
   别名，保证既有消费方读到 `batch_id` 不被破坏（新增字段、零移除）。
2. **模板列表**：DDD `list_templates` 返回 `{list, total}`，既有
   `GET /api/data/templates` 返回 `{templates, total}`，此处归一化。
"""
from __future__ import annotations

from typing import Any, Dict


def template_list_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """DDD list_templates 输出 {list,total} → Web {templates,total}。"""
    return {
        "templates": payload.get("list", []),
        "total": payload.get("total", 0),
    }


def batch_generate_payload(batch: Dict[str, Any]) -> Dict[str, Any]:
    """DDD generate 输出（id 为主键）→ 兼容既有 batch_id 契约。

    保持原字段不动，仅补 `batch_id` 别名（若 DDD 输出恰好没有该键）。
    """
    out = dict(batch)
    if "batch_id" not in out and "id" in out:
        out["batch_id"] = out["id"]
    return out


__all__ = ["template_list_payload", "batch_generate_payload"]
