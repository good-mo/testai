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


# ==============================================================================
# 从 models/file.py 迁移
# ==============================================================================

# app/models/file.py
"""文件管理 / 附件管理 Pydantic 请求体模型。"""
from typing import List

from pydantic import BaseModel, Field


class IdBody(BaseModel):
    """携带单个主键 id 的请求。"""

    id: str = Field("", description="主键 ID")

    model_config = {"extra": "allow"}


class FilePageBody(BaseModel):
    """项目文件分页查询。"""

    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, le=500, description="每页条数")
    keyword: str = Field("", description="搜索关键字")
    moduleIds: List[str] = Field([], description="模块 ID 列表")
    fileType: str = Field("", description="文件类型过滤")
    projectId: str = Field("", description="项目 ID")
    combine: dict = Field({}, description="附加过滤条件（keyword/storage/createUser）")
    model_config = {"extra": "allow"}


class FileModuleAddBody(BaseModel):
    """新增文件模块。"""

    name: str = Field("新模块", description="模块名称")
    parentId: str = Field("root", description="父模块 ID")
    projectId: str = Field("", description="项目 ID")


class AttachmentPageBody(BaseModel):
    """附件分页查询。"""

    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, le=500, description="每页条数")


# ════════════════════════════════════════════════════════════════
# 文件兼容路由（project_compat_file / attachment）请求体模型
# 字段自 app/routers/project_compat_file.py 与 app/routers/attachment.py
# 中 read_body 实际使用字段归纳，默认 extra: allow 避免遗漏新增字段。
# ════════════════════════════════════════════════════════════════


class FileDownloadBody(BaseModel):
    """项目文件 / 附件下载请求体（兼容 id 与 fileId 两种命名）。"""

    id: str = Field("", description="文件 ID")
    fileId: str = Field("", description="文件 ID（别名）")

    model_config = {"extra": "allow"}


class FileModuleCountBody(BaseModel):
    """文件模块计数请求体（携带附加过滤 combine）。"""

    combine: dict = Field({}, description="附加过滤条件（keyword/storage/createUser）")

    model_config = {"extra": "allow"}


class FileBatchDeleteBody(BaseModel):
    """项目文件批量删除请求体。"""

    selectAll: bool = Field(False, description="是否全选")
    selectIds: List[str] = Field([], description="勾选中的文件 ID")
    excludeIds: List[str] = Field([], description="需要排除的文件 ID")
    moduleIds: List[str] = Field([], description="模块 ID 过滤")
    fileType: str = Field("", description="文件类型过滤")
    projectId: str = Field("", description="项目 ID")
    condition: dict = Field({}, description="附加过滤条件（keyword/combine）")

    model_config = {"extra": "allow"}


class FileBatchMoveBody(BaseModel):
    """项目文件批量移动请求体。"""

    selectIds: List[str] = Field([], description="待移动的文件 ID")
    moveModuleId: str = Field("", description="目标模块 ID")

    model_config = {"extra": "allow"}


class FileModuleMoveBody(BaseModel):
    """文件模块移动（拖拽排序）请求体。"""

    dragNodeId: str = Field("", description="被拖动模块 ID")
    dropNodeId: str = Field("", description="放置目标模块 ID")
    dropPosition: int = Field(0, description="放置位置：-1 之上 / 0 之内 / 1 之下")

    model_config = {"extra": "allow"}


class FileModuleUpdateBody(BaseModel):
    """文件模块重命名请求体。"""

    id: str = Field("", description="模块 ID")
    name: str = Field("", description="模块新名称")

    model_config = {"extra": "allow"}
