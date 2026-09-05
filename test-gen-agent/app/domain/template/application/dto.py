"""模板应用层 DTO（命令/查询对象）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ListTemplatesCommand:
    """模板列表查询。"""
    scope_type: str = "PROJECT"
    scope_id: str = ""
    scene: str = ""


@dataclass
class GetTemplateCommand:
    """获取单个模板。"""
    scope_type: str = "PROJECT"
    template_id: str = ""


@dataclass
class SaveTemplateCommand:
    """保存（新增/更新）模板。"""
    scope_type: str = "PROJECT"
    template_id: Optional[str] = None
    name: str = ""
    remark: str = ""
    scene: str = "FUNCTIONAL"
    scope_id: str = ""
    internal: bool = False
    enable_default: bool = False
    enable_third_part: bool = False
    ref_id: str = ""
    platform_default: bool = False
    custom_fields: list = field(default_factory=list)
    system_fields: list = field(default_factory=list)
    upload_img_file_ids: list = field(default_factory=list)
    create_user: str = "admin"
    update_user: str = "admin"


@dataclass
class DeleteTemplateCommand:
    """删除模板。"""
    template_id: str = ""


@dataclass
class SetDefaultCommand:
    """设为默认模板。"""
    scope_type: str = "PROJECT"
    scope_id: str = ""
    scene: str = ""
    template_id: str = ""


__all__ = [
    "ListTemplatesCommand", "GetTemplateCommand", "SaveTemplateCommand",
    "DeleteTemplateCommand", "SetDefaultCommand",
]
