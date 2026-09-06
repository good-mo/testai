# app/services/resource_pool_service.py
"""资源池业务逻辑层（resource_pool 域 DDD 接入 · 阶段 C 薄门面）。

资源池业务数据访问已收敛到 resource_pool 域 DDD 应用服务
`resource_pool_app_service`（见 `app/domain/resource_pool/`）。本 Service
收敛为对 DDD 应用门面的**薄委托门面**，仅保留既有方法签名以兼容
`app/routers/test_resources.py` / `method_compat.py` 等调用方。

DDD 聚合 `to_dict` 输出 camelCase（`createdAt`/`updatedAt` 毫秒），而既有
router 消费 snake_case DB 行（`created_at`/`updated_at` 秒），故在门面处做
**契约桥**（camel → snake），保证对外方法签名与返回结构不变、调用方零改动、可回滚。

> 推荐调用方直接使用 `resource_pool_app_service`；本类仅作过渡兼容层保留。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.domain.resource_pool.application.dto import (
    CreatePoolCommand,
    DeletePoolCommand,
    GetPoolCommand,
    ListPoolsCommand,
    SetEnableCommand,
    UpdatePoolCommand,
)
from app.domain.resource_pool.application.resource_pool_app_service import (
    resource_pool_app_service as _ddd,
)
from app.domain.resource_pool.domain.exceptions import ResourcePoolNotFound


def _to_row(ddd_dict: Optional[dict]) -> Optional[dict]:
    """把 DDD to_dict 的 camelCase 毫秒输出桥接为 router 消费的 snake_case 秒行。

    与既有 `ResourcePoolRepo.get_all/get_by_id` 的 DB 行 schema 完全一致
    （enable 归一为 0/1，created_at/updated_at 为秒浮点），router 零改动。
    """
    if not ddd_dict:
        return None
    return {
        "id": ddd_dict.get("id"),
        "name": ddd_dict.get("name"),
        "description": ddd_dict.get("description", ""),
        "enable": 1 if ddd_dict.get("enable") else 0,
        "created_at": (ddd_dict.get("createdAt") or 0) / 1000.0 if ddd_dict.get("createdAt") else 0,
        "updated_at": (ddd_dict.get("updatedAt") or 0) / 1000.0 if ddd_dict.get("updatedAt") else 0,
    }


class ResourcePoolService:
    """资源池服务（resource_pool 域 DDD 薄门面）。"""

    def create(self, name: str = "未命名资源池", description: str = "",
               enable: bool = True) -> dict:
        created = _ddd.create(CreatePoolCommand(
            name=name, description=description, enable=enable,
        ))
        # 保持既有 create 返回 {id} 的契约（id 为真实落库 id）
        return {"id": created.get("id")}

    def list(self, keyword: str = "") -> List[Dict]:
        return [_to_row(p) for p in _ddd.list(ListPoolsCommand(keyword=keyword))]

    def get(self, pool_id: str) -> Optional[dict]:
        return _to_row(_ddd.get(GetPoolCommand(pool_id=pool_id)))

    def update(self, pool_id: str, data: dict) -> bool:
        data = data or {}
        # 兼容既有 ResourcePoolRepo.update 白名单：enable 变更随 update 一起提交
        if "enable" in data:
            try:
                self.set_enable(pool_id, bool(data.get("enable")))
            except ResourcePoolNotFound:
                return False
        try:
            _ddd.update(UpdatePoolCommand(
                pool_id=pool_id,
                name=data.get("name"),
                description=data.get("description"),
            ))
            return True
        except ResourcePoolNotFound:
            return False

    def delete(self, pool_id: str) -> bool:
        return _ddd.delete(DeletePoolCommand(pool_id=pool_id))

    def set_enable(self, pool_id: str, enable: bool) -> bool:
        return _ddd.set_enable(SetEnableCommand(pool_id=pool_id, enable=bool(enable)))


resource_pool_service = ResourcePoolService()


__all__ = ["resource_pool_service", "ResourcePoolService"]
