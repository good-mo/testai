"""文件聚合根 FileItem（项目文件制品）。

聚合边界：
  - FileItem（聚合根）：上传文件元数据（id/name/归属/存储）
  - 文件名/类型为值对象，安全净化逻辑内聚
"""
from __future__ import annotations

import time
from typing import Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.file.domain.events import FileDeleted, FileMetaUpdated, FileUploaded
from app.domain.file.domain.value_objects.file_type import FileName, FileType


class FileItem(AggregateRoot):
    """文件制品聚合根（元数据视角）。"""

    def __init__(
        self,
        *,
        file_id: str,
        name: str,
        project_id: str = "",
        module_id: str = "root",
        create_user: str = "",
        update_user: str = "",
        storage: str = "minio",
        file_type: str = "",  # 留空则按文件名自动判定类型（见 _guess_type）
        description: str = "",
        enable: bool = True,
        size: int = 0,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        _uploaded: bool = False,
    ):
        if not file_id:
            raise DomainValidationError("文件 ID 不能为空")
        self.id = Identifier.of(file_id)
        self._name = FileName(name)
        self._project_id = project_id or ""
        self._module_id = module_id or "root"
        self._create_user = create_user or ""
        self._update_user = update_user or ""
        self._storage = storage or "minio"
        self._file_type = FileType(file_type or self._guess_type(self._name.value))
        self._description = description or ""
        self._enable = bool(enable)
        self._size = max(0, int(size or 0))
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._domain_events = []
        self.version = 0
        if _uploaded:
            self.record_event(FileUploaded(
                self.id.value, self._name.value, self._size,
                self._project_id, self._module_id))

    @staticmethod
    def _guess_type(filename: str) -> str:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext in {"png", "jpg", "jpeg", "gif", "bmp", "webp", "svg"}:
            return "IMAGE"
        if ext in {"doc", "docx", "pdf", "txt", "md"}:
            return "DOC"
        if ext in {"xls", "xlsx", "csv"}:
            return "XLS"
        if ext == "jar":
            return "JAR"
        if ext in {"json", "yaml", "yml"}:
            return "CONFIG"
        return "FILE"

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name.value

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def module_id(self) -> str:
        return self._module_id

    @property
    def create_user(self) -> str:
        return self._create_user

    @property
    def update_user(self) -> str:
        return self._update_user

    @property
    def storage(self) -> str:
        return self._storage

    @property
    def file_type(self) -> FileType:
        return self._file_type

    @property
    def description(self) -> str:
        return self._description

    @property
    def enable(self) -> bool:
        return self._enable

    @property
    def size(self) -> int:
        return self._size

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    # ── 业务命令 ─────────────────────────────────────
    def move_module(self, module_id: str) -> None:
        """移动到新的功能模块。"""
        if module_id:
            self._module_id = module_id
        self._touch()
        self.record_event(FileMetaUpdated(self.id.value, "move_module"))

    def update_meta(self, data: dict) -> None:
        """更新文件元数据。"""
        allowed = ("project_id", "module_id", "create_user", "update_user",
                   "storage", "file_type", "description", "enable")
        for k, v in data.items():
            if k in allowed:
                if k == "name":
                    self._name = FileName(v)
                elif k == "file_type":
                    self._file_type = FileType(v)
                elif k == "enable":
                    self._enable = bool(v)
                elif k == "description":
                    self._description = v or ""
                elif v is not None:
                    setattr(self, f"_{k}", v)
        self._touch()
        self.record_event(FileMetaUpdated(self.id.value, "meta"))

    def mark_deleted(self) -> None:
        self.record_event(FileDeleted(self.id.value, self._name.value))

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 序列化 ─────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "name": self._name.value,
            "project_id": self._project_id,
            "module_id": self._module_id,
            "create_user": self._create_user,
            "update_user": self._update_user,
            "storage": self._storage,
            "file_type": self._file_type.value,
            "description": self._description,
            "enable": self._enable,
            "size": self._size,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "FileItem":
        return FileItem(
            file_id=str(data.get("id") or ""),
            name=data.get("name", "unnamed"),
            project_id=data.get("project_id", data.get("projectId", "")),
            module_id=data.get("module_id", data.get("moduleId", "root")),
            create_user=data.get("create_user", data.get("createUser", "")),
            update_user=data.get("update_user", data.get("updateUser", "")),
            storage=data.get("storage", "minio"),
            file_type=data.get("file_type", data.get("fileType", "FILE")),
            description=data.get("description", ""),
            enable=bool(data.get("enable", 1)),
            size=data.get("size", 0),
            created_at=data.get("created_at", data.get("createTime")),
            updated_at=data.get("updated_at", data.get("updateTime")),
        )


__all__ = ["FileItem"]
