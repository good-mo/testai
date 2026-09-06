"""文件聚合仓储实现（Adapter / Anti-Corruption Layer）。"""
from __future__ import annotations

from typing import List, Optional

from app.domain.file.domain.entities.file_item import FileItem
from app.repositories.file_repo import FileRepo


class FileRepoAdapter:
    """将既有 FileRepo 封装为面向聚合 FileItem 的仓储。"""

    def upsert_meta(self, file: FileItem) -> None:
        data = file.to_dict()
        FileRepo.upsert_meta(file.id.value, data)

    def get_meta(self, file_id: str) -> Optional[FileItem]:
        row = FileRepo.get_meta(file_id)
        return FileItem.from_dict(row) if row else None

    def list_by_ids(self, file_ids: List[str]) -> List[FileItem]:
        rows = FileRepo.list_by_ids(file_ids)
        return [FileItem.from_dict(r) for r in rows]

    def delete_by_ids(self, file_ids: List[str]) -> int:
        return FileRepo.delete_by_ids(file_ids)

    def list_by_project(self, project_id: str = "") -> List[FileItem]:
        rows = FileRepo.list_by_project(project_id)
        return [FileItem.from_dict(r) for r in rows]

    def count_by_module(self, project_id: str = "", storage: str = "") -> dict:
        return FileRepo.count_by_module(project_id, storage)


__all__ = ["FileRepoAdapter"]
