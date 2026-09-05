# app/services/file_service.py
"""文件管理业务逻辑层（Phase 3 重构 · 四层对齐）。

将原 `app/file_mgmt/router.py` 内联的文件系统领域逻辑下沉到此服务层：
  - 上传目录定位、文件名净化（路径穿越防护）、安全落盘
  - 上传文件检索 / 删除 / 扫描分页
  - 文件模块树委托（复用 apitest 域模块能力）

Router 层只做 URL/参数/响应编排，不再直接触碰文件系统。
数据访问层：文件本体存储在文件系统 uploads 目录；模块树走 apitest 域。
"""
import os
import re
import time
import uuid
from typing import Dict, List, Optional

from app.repositories.file_repo import file_repo
from app.services.apitest_service import apitest_service
from app.domain.file.application.dto import (
    DeleteBatchCommand,
    DeleteFileCommand,
    SaveFileCommand,
    UpdateMetaCommand,
)
from app.domain.file.application.file_app_service import (
    file_app_service as _ddd_file,
)

# 上传文件存储目录
UPLOAD_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "uploads",
))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 文件名非法字符（含路径分隔符与控制字符）
_UNSAFE_CHARS = re.compile('[\\/:*?"<>|\x00-\x1f]')

# 文件类型扩展名 → 类型映射
_IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "bmp", "webp", "svg"}
_DOC_EXTS = {"doc", "docx", "pdf", "txt", "md"}


class FileService:
    """文件管理服务：封装上传文件在文件系统上的读写与检索。"""

    # ── 基础工具 ──────────────────────────────────────────
    @staticmethod
    def get_file_type(filename: str) -> str:
        """根据文件名判断文件类型。"""
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext in _IMAGE_EXTS:
            return "IMAGE"
        if ext in _DOC_EXTS:
            return "DOC"
        if ext in {"xls", "xlsx", "csv"}:
            return "XLS"
        if ext in {"jar"}:
            return "JAR"
        if ext in {"json", "yaml", "yml"}:
            return "CONFIG"
        return "FILE"

    @staticmethod
    def sanitize_filename(filename: str, default: str = "unnamed") -> str:
        """净化上传文件名，阻断路径穿越。

        客户端传入的 filename 完全不可信，若直接拼进 os.path.join，
        形如 ``../../app/main.py`` 的文件名会写到 uploads 目录之外；
        Windows 环境下盘符与保留名（CON/NUL 等）同样需要处理。

        处理策略：只取 basename → 去非法字符 → 去首尾空白与点 → 限长 → 兜底命名。
        """
        if not filename or not isinstance(filename, str):
            return default
        # 1) 只保留最后一段路径，吃掉 ../ 与绝对路径
        name = os.path.basename(filename.replace("\\", "/").strip())
        # 2) 去掉路径分隔符与控制字符
        name = _UNSAFE_CHARS.sub("_", name)
        # 3) Windows 保留设备名不可作为文件名
        if name.split(".")[0].upper() in {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }:
            name = f"_{name}"
        # 4) 去掉首尾空白与点，避免 ".." 与隐藏文件歧义
        name = name.strip(" .\u3000")[:200].strip(" .")
        return name or default

    @staticmethod
    def build_upload_path(file_id: str, filename: str) -> str:
        """拼接安全落盘路径，并二次校验未逃出 UPLOAD_DIR。"""
        safe_name = FileService.sanitize_filename(filename)
        path = os.path.abspath(os.path.join(UPLOAD_DIR, f"{file_id}_{safe_name}"))
        # 纵深防御：即便净化被绕过，也绝不允许写到上传目录之外
        if os.path.commonpath([path, UPLOAD_DIR]) != UPLOAD_DIR:
            path = os.path.abspath(os.path.join(UPLOAD_DIR, f"{file_id}_unnamed"))
        return path

    @staticmethod
    def find_upload_file(file_id: str) -> Optional[str]:
        """按 file_id 精确定位上传文件，返回文件名（找不到返回 None）。"""
        if not file_id or not isinstance(file_id, str):
            return None
        # 阻断路径穿越：id 中不允许出现分隔符
        if "/" in file_id or "\\" in file_id or file_id in (".", ".."):
            return None
        prefix = f"{file_id}_"
        for fname in os.listdir(UPLOAD_DIR):
            if fname.startswith(prefix):
                return fname
        return None

    @staticmethod
    def resolve_path(fname: str) -> str:
        """由上传文件名解析落盘绝对路径。"""
        return os.path.join(UPLOAD_DIR, fname)

    # ── 文件写入 ──────────────────────────────────────────
    def save_file(self, filename: str, content: bytes,
                  project_id: str = "", module_id: str = "root",
                  create_user: str = "", storage: str = "minio",
                  enable: bool = True) -> dict:
        """落盘上传文件，返回 {id, name, path, size, uploadTime}。

        委托 file 域 DDD 门面 `file_app_service.save_file`：安全落盘 + 同步
        元数据（含自动识别 file_type），返回形状与旧实现一致。
        """
        return _ddd_file.save_file(SaveFileCommand(
            filename=filename,
            content=content,
            project_id=project_id,
            module_id=module_id or "root",
            create_user=create_user,
            storage=storage or "minio",
            enable=enable,
        ))

    def delete_file(self, file_id: str) -> bool:
        """按 id 删除上传文件，返回是否命中（委托 DDD 门面）。"""
        return _ddd_file.delete_file(DeleteFileCommand(file_id=file_id))

    def delete_files_batch(self, file_ids: List[str]) -> int:
        """批量删除上传文件（委托 DDD 门面，返回删除数量）。"""
        return _ddd_file.delete_batch(DeleteBatchCommand(file_ids=file_ids))

    def _merge_meta(self, file_items: List[dict], project_id: str = "") -> List[dict]:
        """将磁盘扫描结果与元数据合并，补全 projectId/moduleId/createUser/storage。

        磁盘中已有 DB 元数据的文件按其记录归属；
        尚无元数据的旧文件 project_id 默认空串（表示未绑定项目），
        在「全部文件」视图中对任何项目均可见，在「我的文件」仅当
        create_user 匹配时才显示。
        """
        if not file_items:
            return []
        ids = [f["id"] for f in file_items]
        metas = file_repo.list_by_ids(ids)
        meta_map = {m["id"]: m for m in metas}
        merged = []
        for f in file_items:
            m = meta_map.get(f["id"], {})
            # 文件无 DB 元数据时标记为空项目（供全项目视图显示）
            f["projectId"] = m.get("project_id", "")
            f["moduleId"] = m.get("module_id", "root")
            f["createUser"] = m.get("create_user", "")
            f["updateUser"] = m.get("update_user", "")
            f["storage"] = m.get("storage", "minio")
            f["enable"] = bool(m.get("enable", 1))
            f["description"] = m.get("description", "")
            merged.append(f)
        return merged

    # ── 项目文件扫描（完整元数据，供分页/详情）──────────────
    def _scan_project_files(self) -> List[dict]:
        """扫描上传目录，返回完整项目文件元数据列表。"""
        files = []
        try:
            for fname in os.listdir(UPLOAD_DIR):
                fpath = os.path.join(UPLOAD_DIR, fname)
                if not os.path.isfile(fpath):
                    continue
                stat = os.stat(fpath)
                orig_name = fname.split("_", 1)[1] if "_" in fname else fname
                ftype = self.get_file_type(orig_name)
                files.append({
                    "id": fname.split("_", 1)[0] if "_" in fname else fname,
                    "name": orig_name,
                    "originalName": orig_name,
                    "path": fpath,
                    "size": stat.st_size,
                    "uploadTime": stat.st_mtime,
                    "updateTime": int(stat.st_mtime * 1000),
                    "createTime": int(stat.st_mtime * 1000),
                    "type": ftype,
                    "fileType": ftype,
                    "enable": ftype != "JAR",
                    "tags": [],
                    "description": "",
                    "updateUser": "",
                    "createUser": "",
                    "previewSrc": "",
                    "storage": "minio",
                })
        except Exception:
            pass
        return files

    def list_project_files(
        self, keyword: str = "", module_ids: Optional[List[str]] = None,
        file_type: str = "", storage: str = "", create_user: str = "",
        project_id: str = "", combine: Optional[dict] = None,
    ) -> List[dict]:
        """项目文件列表（含过滤），供 router 分页。

        先扫磁盘 → 再合并 DB 元数据 → 按 projectId/moduleId/createUser/storage 精确过滤。
        文件首次上传时若元数据尚未写入（旧文件/直接拷入 uploads 目录的文件），
        默认视为归属于当前 projectId 与 root 模块。
        """
        files = self._scan_project_files()
        files = self._merge_meta(files, project_id=project_id)
        combine = combine or {}
        combine_keyword = combine.get("keyword", keyword)
        storage = combine.get("storage", storage)
        create_user = combine.get("createUser", create_user)
        module_ids = module_ids or []

        kw = combine_keyword or keyword
        if kw:
            files = [f for f in files if kw.lower() in f["name"].lower()]
        if file_type:
            files = [f for f in files if (f.get("fileType") or "").lower() == file_type.lower()]
        # 项目过滤：显式指定 projectId 时仅返回该项目下的文件
        # 未绑定项目的旧文件（projectId 为空）对所有项目均可见
        if project_id:
            files = [f for f in files
                     if f.get("projectId") == project_id or not f.get("projectId")]
        if module_ids and "root" not in module_ids:
            files = [f for f in files if f.get("moduleId") in module_ids]
        if storage:
            files = [f for f in files if (f.get("storage") or "").lower() == storage.lower()]
        if create_user:
            files = [f for f in files if f.get("createUser") == create_user]
        return files

    def count_files_by_module(self, project_id: str = "", storage: str = "",
                               create_user: str = "") -> dict:
        """统计项目文件各模块数量。返回 {root, my, all, <moduleId>: count}。"""
        disk_files = self._scan_project_files()
        # 合并 DB 元数据，记录每个文件的 module_id
        metas = file_repo.list_by_ids([f["id"] for f in disk_files])
        meta_map = {m["id"]: m for m in metas}
        # 先初始化所有文件模块的计数为 0（含空模块）
        counts: Dict[str, int] = {}
        try:
            file_modules = apitest_service.list_modules("file", project_id=project_id)
            for m in file_modules:
                counts[m.get("id", "")] = 0
        except Exception:
            pass
        counts.setdefault("root", 0)
        # 统一按模块汇总
        for f in disk_files:
            m = meta_map.get(f["id"], {})
            # storage 过滤
            f_storage = (m.get("storage") or "minio").lower()
            if storage and f_storage != storage.lower():
                continue
            # project 过滤（未绑定项目的文件对所有项目可见）
            f_project = m.get("project_id", "")
            if project_id and f_project != project_id and f_project:
                continue
            f_module = m.get("module_id", "root")
            counts["root"] = counts.get("root", 0) + 1
            if f_module != "root":
                counts[f_module] = counts.get(f_module, 0) + 1
        counts["all"] = counts.get("root", 0)
        # my 计数（当前用户上传的）
        if create_user:
            my_count = 0
            for f in disk_files:
                m = meta_map.get(f["id"], {})
                if m.get("create_user", "") != create_user:
                    continue
                f_storage = (m.get("storage") or "minio").lower()
                if storage and f_storage != storage.lower():
                    continue
                f_project = m.get("project_id", "")
                if project_id and f_project != project_id and f_project:
                    continue
                my_count += 1
            counts["my"] = my_count
        else:
            counts["my"] = counts.get("root", 0)
        return counts

    # ── 附件扫描 ──────────────────────────────────────────
    def _scan_attachments(self) -> List[dict]:
        """扫描上传目录，返回附件页元数据（精简，不含 project 专属字段）。"""
        files = []
        try:
            for fname in os.listdir(UPLOAD_DIR):
                fpath = os.path.join(UPLOAD_DIR, fname)
                if not os.path.isfile(fpath):
                    continue
                stat = os.stat(fpath)
                orig_name = fname.split("_", 1)[1] if "_" in fname else fname
                ftype = self.get_file_type(orig_name)
                files.append({
                    "id": fname.split("_", 1)[0] if "_" in fname else fname,
                    "name": orig_name,
                    "originalName": orig_name,
                    "path": fpath,
                    "size": stat.st_size,
                    "uploadTime": stat.st_mtime,
                    "updateTime": int(stat.st_mtime * 1000),
                    "type": ftype,
                    "fileType": ftype,
                    "enable": ftype != "JAR",
                    "tags": [],
                    "description": "",
                    "updateUser": "admin",
                })
        except Exception:
            pass
        return files

    def list_attachment_meta(self) -> List[dict]:
        """附件资源列表（仅 {id, name, size}，供资源附件列表接口）。"""
        files = []
        try:
            for fname in os.listdir(UPLOAD_DIR):
                fpath = os.path.join(UPLOAD_DIR, fname)
                if not os.path.isfile(fpath):
                    continue
                stat = os.stat(fpath)
                orig_name = fname.split("_", 1)[1] if "_" in fname else fname
                files.append({
                    "id": fname.split("_", 1)[0] if "_" in fname else fname,
                    "name": orig_name,
                    "size": stat.st_size,
                })
        except Exception:
            pass
        return files

    def get_file_meta(self, file_id: str) -> Optional[Dict]:
        """按 id 返回文件详情元数据，找不到返回 None。"""
        fname = self.find_upload_file(file_id)
        if not fname:
            return None
        fpath = self.resolve_path(fname)
        stat = os.stat(fpath)
        orig_name = fname.split("_", 1)[1] if "_" in fname else fname
        ftype = self.get_file_type(orig_name)
        return {
            "id": file_id,
            "name": orig_name,
            "path": fpath,
            "size": stat.st_size,
            "type": ftype,
            "fileType": ftype,
            "fname": fname,
        }

    # ── 元数据访问（经 Repository 层，供 router 无需直连 file_repo）──
    def get_meta(self, file_id: str) -> Optional[dict]:
        """按文件 id 查询 DB 元数据（project/module/createUser/storage 等）。"""
        return file_repo.get_meta(file_id)

    def update_meta(self, file_id: str, data: dict) -> None:
        """写入/更新文件 DB 元数据（委托 DDD 门面）。"""
        return _ddd_file.update_meta(UpdateMetaCommand(file_id=file_id, data=data))

    # ── 文件模块（委托 apitest 域能力）────────────────────
    def build_module_tree(self, project_id: str = ""):
        return apitest_service.build_module_tree("file", project_id=project_id)

    def add_module(self, name: str, parent_id: str = "root",
                   project_id: str = ""):
        return apitest_service.add_module(
            scope="file", name=name, parent_id=parent_id, project_id=project_id,
        )

    def delete_module(self, mod_id: str) -> bool:
        return apitest_service.delete_module(mod_id) if mod_id else False


file_service = FileService()

__all__ = ["file_service", "FileService", "UPLOAD_DIR"]
