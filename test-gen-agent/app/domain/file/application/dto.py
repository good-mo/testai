"""文件应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class SaveFileCommand:
    """保存上传文件。"""
    filename: str
    content: bytes = b""
    project_id: str = ""
    module_id: str = "root"
    create_user: str = ""
    storage: str = "minio"
    enable: bool = True


@dataclass
class FileQuery:
    """文件列表查询。"""
    keyword: str = ""
    module_ids: List[str] = field(default_factory=list)
    file_type: str = ""
    storage: str = ""
    create_user: str = ""
    project_id: str = ""


@dataclass
class DeleteFileCommand:
    """删除文件。"""
    file_id: str


@dataclass
class DeleteBatchCommand:
    """批量删除。"""
    file_ids: List[str] = field(default_factory=list)


@dataclass
class GetFileCommand:
    """获取文件。"""
    file_id: str


@dataclass
class UpdateMetaCommand:
    """更新元数据。"""
    file_id: str
    data: dict = field(default_factory=dict)


@dataclass
class CountModuleQuery:
    """按模块统计。"""
    project_id: str = ""
    storage: str = ""
    create_user: str = ""


__all__ = [
    "SaveFileCommand", "FileQuery", "DeleteFileCommand", "DeleteBatchCommand",
    "GetFileCommand", "UpdateMetaCommand", "CountModuleQuery",
]
