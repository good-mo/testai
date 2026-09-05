"""展示配置应用层 DTO。

`SaveDisplayConfigCommand` 承载前端 `display/save` 的完整保存语义：
既包含文本/文件配置项条目（raw form items），也包含本次已落盘的上传文件
映射（key -> {url, originalName}）。对条目如何解释（文件项 fileName 与
paramValue 的互换、清空文件项的删除）由应用服务在领域层权威裁决，Service
门面仅做薄委托。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SaveDisplayConfigCommand:
    """保存界面配置命令。

    Args:
        items: 前端提交的原始配置项列表，形如
            [{paramKey, paramValue, type, fileName, original, hasFile}, ...]
        uploaded: 本次已由外层落盘的上传文件 key -> {url, originalName}
            （仅文件类 key；Service 门面负责实际落盘）。
    """
    items: List[Dict[str, Any]] = field(default_factory=list)
    uploaded: Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass
class GetDisplayConfigCommand:
    pass


@dataclass
class DeleteByKeyCommand:
    key: str = ""


__all__ = ["SaveDisplayConfigCommand", "GetDisplayConfigCommand", "DeleteByKeyCommand"]
