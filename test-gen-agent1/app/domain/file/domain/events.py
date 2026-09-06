"""文件领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class FileUploaded(DomainEvent):
    """文件已上传落盘。"""

    def __init__(self, file_id: str, name: str, size: int = 0,
                 project_id: str = "", module_id: str = "root"):
        super().__init__(aggregate_id=file_id)
        self.name = name
        self.size = size
        self.project_id = project_id
        self.module_id = module_id


class FileDeleted(DomainEvent):
    """文件已删除。"""

    def __init__(self, file_id: str, name: str = ""):
        super().__init__(aggregate_id=file_id)
        self.name = name


class FileMetaUpdated(DomainEvent):
    """文件元数据已更新。"""

    def __init__(self, file_id: str, action: str = "meta"):
        super().__init__(aggregate_id=file_id)
        self.action = action


__all__ = ["FileUploaded", "FileDeleted", "FileMetaUpdated"]
