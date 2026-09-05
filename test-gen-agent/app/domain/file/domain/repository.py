"""文件聚合仓储接口（Repository Port）。"""
from __future__ import annotations

from typing import List, Optional, Protocol

from app.domain.file.domain.entities.file_item import FileItem


class FileRepository(Protocol):
    """文件元数据仓储契约。"""
    def upsert_meta(self, file: FileItem) -> None: ...
    def get_meta(self, file_id: str) -> Optional[FileItem]: ...
    def list_by_ids(self, file_ids: List[str]) -> List[FileItem]: ...
    def delete_by_ids(self, file_ids: List[str]) -> int: ...
    def list_by_project(self, project_id: str = "") -> List[FileItem]: ...


__all__ = ["FileRepository"]
