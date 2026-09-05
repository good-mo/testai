"""调试业务逻辑层（debug 域 DDD 接入 · 阶段 C 薄门面）。

`app/domain/debug/` DDD 层就绪后，数据访问已收敛到 debug 域 DDD 应用服务
`debug_app_service`（见 `app/domain/debug/`）。本 Service 收敛为对 DDD 应用
门面的**薄委托门面**，仅保留既有方法签名以兼容 `debug_compat` / `gap_fixes`
等调用方；对外返回结构（camelCase）与重构前一致，router 零改动、可回滚。

仍保留进程内 `_store` 仅作读缓存，用于 `has` / `next_num` 的即时一致与减少
全表扫描，持久化一律经 DDD 门面落到 `DebugRepo`（debug_items 表唯一入口）。
"""
from typing import Any, Dict, List, Optional

from app.domain.debug.application.debug_app_service import debug_app_service as _ddd
from app.domain.debug.application.dto import (
    DeleteDebugItemCommand,
    GetDebugItemCommand,
    SaveDebugItemCommand,
)
from app.logging_config import get_logger
from app.repositories.debug_repo import DebugRepo

logger = get_logger(__name__)


def _to_save_cmd(item: Dict[str, Any]) -> SaveDebugItemCommand:
    """把调用方传入的 camelCase 调试项映射为 DDD 保存命令。"""
    return SaveDebugItemCommand(
        debug_id=item.get("id", ""),
        name=item.get("name", "未命名调试"),
        protocol=item.get("protocol", "HTTP"),
        method=item.get("method", "GET"),
        path=item.get("path", "/"),
        url=item.get("url", item.get("path", "/")),
        project_id=item.get("projectId", "") or item.get("project_id", ""),
        module_id=item.get("moduleId", "root") or item.get("module_id", "root"),
        request_data=item.get("request") or item.get("request_data") or {},
        response_data=item.get("response") or item.get("response_data") or {},
        create_user=item.get("createUser", "admin"),
        update_user=item.get("updateUser", "admin"),
        num=item.get("num", 0),
    )


class DebugService:
    """调试数据服务：对外薄门面，持久化经 DDD 应用服务。"""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    # ── 初始化 / 生命周期 ─────────────────────────────────
    def initialize(self) -> None:
        """建表并从 DB 加载全部数据到内存缓存。"""
        try:
            DebugRepo.ensure_table()
        except Exception as e:
            logger.warning("初始化 debug_items 表失败: %s", e)
        try:
            items = _ddd.list_all()
            self._store.clear()
            for item in items:
                self._store[item["id"]] = item
            if items:
                logger.info("从数据库加载 %d 条调试数据", len(items))
        except Exception as e:
            logger.warning("加载调试数据失败: %s", e)

    # ── 读取 ─────────────────────────────────────────────
    def get(self, debug_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 获取调试项（不存在返回 None）。"""
        cached = self._store.get(debug_id)
        if cached is not None:
            return cached
        item = _ddd.get(GetDebugItemCommand(debug_id=debug_id))
        if item:
            self._store[debug_id] = item
        return item

    def has(self, debug_id: str) -> bool:
        """调试项是否存在。"""
        if debug_id in self._store:
            return True
        return _ddd.get(GetDebugItemCommand(debug_id=debug_id)) is not None

    def all_items(self) -> List[Dict[str, Any]]:
        """返回全部调试项（值列表）。"""
        return list(self._store.values())

    def next_num(self) -> int:
        """计算下一个可用的 num 序号。"""
        return len(self._store) + 1

    # ── 写入 ─────────────────────────────────────────────
    def save(self, item: Dict[str, Any]) -> None:
        """保存调试项：经 DDD 落库 + 同步内存缓存。

        item 必须包含 id；若已存在则覆盖更新，否则新增。
        """
        debug_id = item.get("id", "")
        if not debug_id:
            return
        try:
            saved = _ddd.save(_to_save_cmd(item))
        except Exception as e:
            logger.warning("保存调试数据失败: %s", e)
            return
        if saved:
            self._store[debug_id] = saved

    def delete(self, debug_id: str) -> bool:
        """删除调试项：从内存 + DB 中移除。返回是否存在。"""
        existed = self.has(debug_id)
        if existed:
            del self._store[debug_id]
        try:
            _ddd.delete(DeleteDebugItemCommand(debug_id=debug_id))
        except Exception as e:
            logger.warning("删除调试数据失败: %s", e)
        return existed


# 模块级单例
debug_service = DebugService()
debug_service.initialize()


__all__ = ["debug_service", "DebugService"]
