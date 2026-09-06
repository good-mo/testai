"""调试应用服务（Application Service / Use Case 门面）。

修复说明：
  - 修改 import：从 DebugRepoAdapter 改为 DebugRepositoryImpl
  - 使用模块级单例 debug_repository
  - 把 debug_service 的内存缓存逻辑移入此处（has/next_num/all_items）
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.domain.debug.application.dto import (
    DeleteDebugItemCommand,
    GetDebugItemCommand,
    SaveDebugItemCommand,
)
from app.domain.debug.domain.entities.debug_item import DebugItem

# ── 修复：改 import ──────────────────────────────────────────
from app.domain.debug.infrastructure.debug_repository_impl import (
    DebugRepositoryImpl,
    debug_repository,
)


class DebugAppService:
    """调试用例编排服务（含内存缓存）。"""

    def __init__(self, repo=None):
        # ── 修复：使用新的 Repository 单例 ──────────────────
        self._repo = repo or debug_repository
        # 内存缓存（从 debug_service 移入）
        self._store: Dict[str, Dict[str, Any]] = {}
        self._initialize_cache()

    def _initialize_cache(self) -> None:
        """从 DB 加载全部数据到内存缓存。"""
        try:
            items = self._repo.list_all()
            self._store.clear()
            for item in items:
                self._store[item.id.value] = item.to_dict()
            if items:
                from app.logging_config import get_logger
                logger = get_logger(__name__)
                logger.info("从数据库加载 %d 条调试数据", len(items))
        except Exception as e:
            from app.logging_config import get_logger
            logger = get_logger(__name__)
            logger.warning("加载调试数据失败: %s", e)

    # ── 缓存相关方法（从 debug_service 移入）──────────────
    def has(self, debug_id: str) -> bool:
        """调试项是否存在。"""
        if debug_id in self._store:
            return True
        return self._repo.get(debug_id) is not None

    def next_num(self) -> int:
        """计算下一个可用的 num 序号。"""
        return len(self._store) + 1

    def all_items(self) -> List[Dict[str, Any]]:
        """返回全部调试项（值列表）。"""
        return list(self._store.values())

    # ── 标准 CRUD ─────────────────────────────────────────
    def get(self, cmd: GetDebugItemCommand) -> Optional[dict]:
        # 先查缓存
        cached = self._store.get(cmd.debug_id)
        if cached is not None:
            return cached
        # 再查 DB
        item = self._repo.get(cmd.debug_id)
        if item:
            result = item.to_dict()
            self._store[cmd.debug_id] = result
            return result
        return None

    def save(self, cmd: SaveDebugItemCommand) -> dict:
        debug_id = cmd.debug_id or str(uuid.uuid4().hex[:12])
        item = DebugItem(
            debug_id=debug_id,
            name=cmd.name, protocol=cmd.protocol, method=cmd.method,
            path=cmd.path, url=cmd.url,
            project_id=cmd.project_id, module_id=cmd.module_id,
            request_data=cmd.request_data, response_data=cmd.response_data,
            create_user=cmd.create_user, update_user=cmd.update_user,
            num=cmd.num,
        )
        saved = self._repo.save(item)
        result = saved.to_dict()
        # 同步缓存
        self._store[debug_id] = result
        return result

    def delete(self, cmd: DeleteDebugItemCommand) -> bool:
        existed = self._repo.delete(cmd.debug_id)
        # 同步缓存
        self._store.pop(cmd.debug_id, None)
        return existed

    def list_all(self) -> list:
        items = self._repo.list_all()
        return [i.to_dict() for i in items]


debug_app_service = DebugAppService()
