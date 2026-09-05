# app/services/display_config_service.py
"""界面配置业务逻辑层（display_config 域 DDD 接入 · 阶段 C 薄门面）。

界面配置（display/save + display/info 的读写与文件落盘）已收敛到
display_config 域 DDD 应用服务 `display_app_service`
（见 `app/domain/display_config/`）。本 Service 收敛为对 DDD 应用门面的
**薄委托门面**：仅保留既有方法签名以兼容 `auth/router_system` 等调用方，
`save/get_all/get_file_url` 全部委托 DDD，仅 `save_uploaded_file`（物理文件
落盘、属 file 限界上下文）保留在本层。方法签名/返回结构与重构前一致、
调用方零改动、可回滚。

> 推荐调用方直接使用 `display_app_service`；本类仅作过渡兼容层保留。
"""
from typing import Any, Dict, List

from app.domain.display_config.application.display_app_service import (
    display_app_service as _ddd,
)
from app.domain.display_config.application.dto import (
    GetDisplayConfigCommand,
    SaveDisplayConfigCommand,
)


class DisplayConfigService:
    """界面配置服务：router 层唯一业务入口（display_config 域 DDD 薄门面）。"""

    # ── 文件落盘（供 router 调用；物理文件持久化，不在 DDD 域内）──
    @staticmethod
    def save_uploaded_file(filename: str, content: bytes) -> Dict[str, str]:
        """保存上传的展示文件，返回 {url, originalName}。"""
        from app.services.file_service import file_service
        data = file_service.save_file(filename, content)
        file_id = data["id"]
        # 附件下载接口可直接返回图片字节，作为前端 <img src> 的可访问 URL
        return {
            "url": f"/attachment/download/{file_id}",
            "originalName": data["name"],
        }

    # ── 保存 ──────────────────────────────────────────────
    def save(self, request_items: List[Dict[str, Any]],
             uploaded: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
        """保存界面配置（委托 display_config 域 DDD 应用服务裁决语义）。

        Args:
            request_items: multipart 中 request 字段解析出的
                [{paramKey,paramValue,type,fileName,original,hasFile}, ...]
            uploaded: 已落盘的上传文件 key -> {url, originalName}
        Returns:
            保存后的完整配置项列表（供响应）。
        """
        return _ddd.save(SaveDisplayConfigCommand(
            items=request_items, uploaded=uploaded,
        ))

    # ── 读取 ──────────────────────────────────────────────
    def get_all(self) -> List[Dict[str, Any]]:
        return _ddd.get_all(GetDisplayConfigCommand())

    def get_file_url(self, key: str) -> str:
        """读取某文件类 key 的可访问 URL（无则空串）。"""
        return _ddd.get_file_url(key)


display_config_service = DisplayConfigService()


__all__ = ["display_config_service", "DisplayConfigService"]
