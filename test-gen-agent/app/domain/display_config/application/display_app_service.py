"""展示配置应用服务。

修复说明：
  - 修改 import：从 DisplayRepoAdapter 改为 DisplayConfigRepositoryImpl
  - 使用模块级单例 display_config_repository，避免每次实例化都重新建表
  - 其他代码完全不变（方法签名和业务逻辑保持一致）

修复前：self._repo = repo or DisplayRepoAdapter()
修复后：self._repo = repo or display_config_repository
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.domain.display_config.application.dto import (
    DeleteByKeyCommand,
    GetDisplayConfigCommand,
    SaveDisplayConfigCommand,
)
from app.domain.display_config.domain.entities.display_item import DisplayConfigItem

# ── 修复：改 import ──────────────────────────────────────────
# 之前：from app.domain.display_config.infrastructure.display_repository_impl import DisplayRepoAdapter
# 之后：直接导入新的 Repository 实现和单例
from app.domain.display_config.infrastructure.display_repository_impl import (
    DisplayConfigRepositoryImpl,
    display_config_repository,
)

# 前端页面配置的四个文件类 key
_FILE_KEYS = {"ui.icon", "ui.loginLogo", "ui.loginImage", "ui.logoPlatform"}


class DisplayAppService:
    """展示配置用例编排服务。"""

    def __init__(self, repo=None):
        # ── 修复：使用新的 Repository 单例 ──────────────────
        # 之前：self._repo = repo or DisplayRepoAdapter()
        # 之后：self._repo = repo or display_config_repository
        self._repo = repo or display_config_repository

    def save(self, cmd: SaveDisplayConfigCommand) -> list:
        """按前端 display/save 语义解释并持久化配置项。"""
        request_items = cmd.items if isinstance(cmd.items, list) else []
        uploaded = cmd.uploaded or {}

        normalized: List[Dict[str, Any]] = []
        for item in request_items:
            if not isinstance(item, dict):
                continue
            key = item.get("paramKey")
            if not key:
                continue
            ptype = item.get("type") or "text"
            entry: Dict[str, Any] = {
                "paramKey": key,
                "paramValue": item.get("paramValue") or "",
                "type": ptype,
                "fileName": item.get("fileName") or "",
            }
            if key in _FILE_KEYS:
                if key in uploaded:
                    up = uploaded[key]
                    entry["fileName"] = up.get("url", "")
                    entry["paramValue"] = up.get("originalName", "")
                elif item.get("original") and not item.get("hasFile") and not item.get("paramValue"):
                    entry["clear"] = True
                elif item.get("paramValue"):
                    pv = str(item.get("paramValue") or "")
                    if pv.startswith(("/attachment/", "http")):
                        entry["fileName"] = pv
                        entry["paramValue"] = item.get("fileName") or ""
            normalized.append(entry)

        # 处理清空的文件项
        for entry in normalized:
            if entry.pop("clear", False):
                self._repo.delete_by_key(entry["paramKey"])

        # 保存配置项
        self._repo.save_many(
            [
                DisplayConfigItem(
                    param_key=e["paramKey"],
                    param_value=e["paramValue"],
                    param_type=e["type"],
                    file_name=e["fileName"],
                )
                for e in normalized
                if e.get("paramKey")
            ]
        )
        return [i.to_dict() for i in self._repo.get_all()]

    def get_all(self, cmd: GetDisplayConfigCommand = None) -> list:
        items = self._repo.get_all()
        return [i.to_dict() for i in items]

    def delete_by_key(self, cmd: DeleteByKeyCommand) -> None:
        self._repo.delete_by_key(cmd.key)

    def get_file_url(self, key: str) -> str:
        """读取某文件类 key 的可访问 URL。"""
        item = self._repo.get_by_key(key)
        if item and item.param_type == "file":
            return item.param_value or ""
        return ""


# 模块级单例
display_app_service = DisplayAppService()