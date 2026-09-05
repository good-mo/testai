"""文件应用服务（Application Service / Use Case 门面）。

负责文件上传落盘/扫描/删除等用例编排。文件系统副作用保持在应用层。
"""
from __future__ import annotations

import os
import uuid
from typing import Dict, List, Optional

from app.domain.common.domain_events import event_bus
from app.domain.file.application.dto import (
    CountModuleQuery,
    DeleteBatchCommand,
    DeleteFileCommand,
    FileQuery,
    GetFileCommand,
    SaveFileCommand,
    UpdateMetaCommand,
)
from app.domain.file.domain.entities.file_item import FileItem
from app.domain.file.infrastructure.file_repository_impl import FileRepoAdapter

# 上传目录
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_WORKSPACE = os.path.abspath(os.path.join(_FILE_DIR, "..", "..", "..", ".."))
UPLOAD_DIR = os.path.join(_WORKSPACE, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class FileAppService:
    """文件用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or FileRepoAdapter()

    # ── 文件保存 ──────────────────────────────────────────
    def save_file(self, cmd: SaveFileCommand) -> dict:
        """落盘上传文件，返回 {id, name, path, size, uploadTime}。"""
        file = FileItem(
            file_id=str(uuid.uuid4()),
            name=cmd.filename,
            project_id=cmd.project_id,
            module_id=cmd.module_id,
            create_user=cmd.create_user,
            update_user=cmd.create_user,
            storage=cmd.storage,
            enable=cmd.enable,
            size=len(cmd.content),
            _uploaded=True,
        )
        # 安全落盘
        file_path = self._build_upload_path(file.id.value, file.name)
        with open(file_path, "wb") as f:
            f.write(cmd.content)
        # 同步元数据
        self._repo.upsert_meta(file)
        self._publish(file)
        return {
            "id": file.id.value,
            "name": file.name,
            "path": file_path,
            "size": len(cmd.content),
            "uploadTime": file.updated_at,
        }

    # ── 文件扫描 / 查询 ──────────────────────────────────
    def list_files(self, query: FileQuery) -> List[dict]:
        """扫描上传目录 + 合并元数据 + 过滤。"""
        disk_files = self._scan_files()
        disk_files = self._merge_meta(disk_files, query.project_id)

        # 过滤
        if query.keyword:
            disk_files = [f for f in disk_files
                          if query.keyword.lower() in f["name"].lower()]
        if query.file_type:
            disk_files = [f for f in disk_files
                          if f.get("fileType", "").lower() == query.file_type.lower()]
        if query.project_id:
            disk_files = [f for f in disk_files
                          if f.get("projectId") == query.project_id
                          or not f.get("projectId")]
        if query.module_ids and "root" not in query.module_ids:
            disk_files = [f for f in disk_files
                          if f.get("moduleId") in query.module_ids]
        if query.storage:
            disk_files = [f for f in disk_files
                          if (f.get("storage") or "").lower() == query.storage.lower()]
        if query.create_user:
            disk_files = [f for f in disk_files if f.get("createUser") == query.create_user]
        return disk_files

    def get_file(self, cmd: GetFileCommand) -> Optional[dict]:
        """按 id 返回文件详情。"""
        fname = self._find_upload_file(cmd.file_id)
        if not fname:
            return None
        fpath = os.path.join(UPLOAD_DIR, fname)
        stat = os.stat(fpath)
        orig_name = fname.split("_", 1)[1] if "_" in fname else fname
        return {
            "id": cmd.file_id,
            "name": orig_name,
            "path": fpath,
            "size": stat.st_size,
            "fname": fname,
        }

    def get_file_meta(self, file_id: str) -> Optional[dict]:
        meta = self._repo.get_meta(file_id)
        return meta.to_dict() if meta else None

    # ── 文件删除 ──────────────────────────────────────────
    def delete_file(self, cmd: DeleteFileCommand) -> bool:
        fname = self._find_upload_file(cmd.file_id)
        if fname:
            path = os.path.join(UPLOAD_DIR, fname)
            os.remove(path)
            file_item = self._repo.get_meta(cmd.file_id)
            if file_item:
                file_item.mark_deleted()
                self._publish(file_item)
            self._repo.delete_by_ids([cmd.file_id])
            return True
        return False

    def delete_batch(self, cmd: DeleteBatchCommand) -> int:
        removed = 0
        for fid in cmd.file_ids:
            if self.delete_file(DeleteFileCommand(file_id=fid)):
                removed += 1
        return removed

    # ── 模块统计 ──────────────────────────────────────────
    def count_by_module(self, cmd: CountModuleQuery) -> dict:
        """按模块统计文件数量。"""
        disk_files = self._scan_files()
        metas = self._repo.list_by_ids([f["id"] for f in disk_files])
        meta_map = {m.id.value: m for m in metas}
        counts: Dict[str, int] = {}
        counts.setdefault("root", 0)
        for f in disk_files:
            m = meta_map.get(f["id"])
            f_storage = (m.storage if m else "minio").lower() if m else "minio"
            if cmd.storage and f_storage != cmd.storage.lower():
                continue
            f_project = m.project_id if m else ""
            if cmd.project_id and f_project != cmd.project_id and f_project:
                continue
            f_module = m.module_id if m else "root"
            counts["root"] = counts.get("root", 0) + 1
            if f_module != "root":
                counts[f_module] = counts.get(f_module, 0) + 1
        counts["all"] = counts.get("root", 0)
        counts["my"] = counts.get("root", 0)
        return counts

    # ── 元数据操作 ────────────────────────────────────────
    def update_meta(self, cmd: UpdateMetaCommand) -> None:
        item = self._repo.get_meta(cmd.file_id)
        if item:
            item.update_meta(cmd.data)
            self._repo.upsert_meta(item)
            self._publish(item)
        else:
            # 磁盘文件可能还没有元数据
            item = FileItem(file_id=cmd.file_id, name=cmd.file_id, _uploaded=False)
            item.update_meta(cmd.data)
            self._repo.upsert_meta(item)

    # ── 内部工具 ──────────────────────────────────────────
    @staticmethod
    def _find_upload_file(file_id: str) -> Optional[str]:
        if not file_id or "/" in file_id or "\\" in file_id:
            return None
        prefix = f"{file_id}_"
        for fname in os.listdir(UPLOAD_DIR):
            if fname.startswith(prefix):
                return fname
        return None

    @staticmethod
    def _build_upload_path(file_id: str, filename: str) -> str:
        """拼接安全落盘路径。"""
        safe = filename.replace("\\", "/").split("/")[-1]
        import re
        safe = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", safe)
        path = os.path.abspath(os.path.join(UPLOAD_DIR, f"{file_id}_{safe}"))
        if os.path.commonpath([path, UPLOAD_DIR]) != UPLOAD_DIR:
            path = os.path.abspath(os.path.join(UPLOAD_DIR, f"{file_id}_unnamed"))
        return path

    @staticmethod
    def _scan_files() -> List[dict]:
        """扫描上传目录。"""
        files = []
        for fname in os.listdir(UPLOAD_DIR):
            fpath = os.path.join(UPLOAD_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            stat = os.stat(fpath)
            orig_name = fname.split("_", 1)[1] if "_" in fname else fname
            files.append({
                "id": fname.split("_", 1)[0] if "_" in fname else fname,
                "name": orig_name,
                "originalName": orig_name,
                "path": fpath,
                "size": stat.st_size,
                "uploadTime": stat.st_mtime,
                "updateTime": int(stat.st_mtime * 1000),
                "createTime": int(stat.st_mtime * 1000),
                "type": FileItem._guess_type(orig_name),
                "fileType": FileItem._guess_type(orig_name),
                "tags": [],
            })
        return files

    @staticmethod
    def _merge_meta(disk_files: List[dict], project_id: str = "") -> List[dict]:
        """将磁盘扫描结果与元数据合并。"""
        if not disk_files:
            return []
        ids = [f["id"] for f in disk_files]
        repo = FileRepoAdapter()
        metas = repo.list_by_ids(ids)
        meta_map = {m.id.value: m for m in metas}
        for f in disk_files:
            m = meta_map.get(f["id"])
            if m:
                f["projectId"] = m.project_id
                f["moduleId"] = m.module_id
                f["createUser"] = m.create_user
                f["updateUser"] = m.update_user
                f["storage"] = m.storage
                f["enable"] = m.enable
                f["description"] = m.description
            else:
                f["projectId"] = ""
                f["moduleId"] = "root"
                f["createUser"] = ""
                f["storage"] = "minio"
                f["enable"] = f.get("fileType") != "JAR"
        return disk_files

    @staticmethod
    def _publish(entity) -> None:
        for ev in entity.pull_domain_events():
            event_bus.dispatch(ev)


# 单例门面
file_app_service = FileAppService()

__all__ = ["FileAppService", "file_app_service"]
