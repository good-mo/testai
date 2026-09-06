"""展示配置应用服务。

承接 `display/save` / `display/info` 的完整保存与读取语义，是
display_config 域生产读写的**唯一权威入口**。Service 门面收敛为对本
应用服务的薄委托，业务规则（文件类 key 的 fileName/paramValue 互换、
清空文件项的删除、文本/文件默认值）在此统一裁决，消灭 service→repo
的双写旁路。
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.domain.display_config.application.dto import (
    DeleteByKeyCommand,
    GetDisplayConfigCommand,
    SaveDisplayConfigCommand,
)
from app.domain.display_config.domain.entities.display_item import DisplayConfigItem
from app.domain.display_config.infrastructure.display_repository_impl import (
    DisplayRepoAdapter,
)

# 前端页面配置的四个文件类 key（对应 FileParamItem.type=file）。
# 领域权威声明：这些 key 的 fileName 存可访问 URL、paramValue 存原始文件名。
_FILE_KEYS = {"ui.icon", "ui.loginLogo", "ui.loginImage", "ui.logoPlatform"}


class DisplayAppService:
    """展示配置用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or DisplayRepoAdapter()

    def save(self, cmd: SaveDisplayConfigCommand) -> list:
        """按前端 display/save 语义解释并持久化配置项，返回保存后全部配置。

        Args:
            cmd: 原始提交条目 + 本次已落盘的上传文件映射。
        Returns:
            保存后的完整配置项列表（供响应 /display/save）。
        """
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
                    # 本次换了新图：fileName 存可访问 URL、paramValue 存原始文件名
                    # （前端 initPageConfig 取 url: e.fileName / name: e.paramValue）
                    up = uploaded[key]
                    entry["fileName"] = up.get("url", "")
                    entry["paramValue"] = up.get("originalName", "")
                elif item.get("original") and not item.get("hasFile") and not item.get("paramValue"):
                    # 标记清空（删除存量记录）
                    entry["clear"] = True
                elif item.get("paramValue"):
                    # 未换图但带旧值（JSON 直接提交场景）：URL 在 paramValue 则搬入 fileName
                    pv = str(item.get("paramValue") or "")
                    if pv.startswith(("/attachment/", "http")):
                        entry["fileName"] = pv
                        entry["paramValue"] = item.get("fileName") or ""
                    # 否则 fileName 已是 URL（幂等重存）：保持默认
            normalized.append(entry)

        # 先处理显式清空的文件项（删除存量记录）
        for entry in normalized:
            if entry.pop("clear", False):
                self._repo.delete_by_key(entry["paramKey"])

        # 与既有 /display/save 语义一致：清空项删除后仍以空值重入（幂等），
        # 非清空项正常 upsert。
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
        # 返回保存后的完整配置（与既有 /display/save 响应一致）
        return [i.to_dict() for i in self._repo.get_all()]

    def get_all(self, cmd: GetDisplayConfigCommand = None) -> list:
        items = self._repo.get_all()
        return [i.to_dict() for i in items]

    def delete_by_key(self, cmd: DeleteByKeyCommand) -> None:
        self._repo.delete_by_key(cmd.key)

    def get_file_url(self, key: str) -> str:
        """读取某文件类 key 的可访问 URL（无则空串）。"""
        item = self._repo.get_by_key(key)
        if item and item.param_type == "file":
            return item.param_value or ""
        return ""


display_app_service = DisplayAppService()
