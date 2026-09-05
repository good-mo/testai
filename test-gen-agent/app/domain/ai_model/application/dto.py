"""AI 模型源应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ListModelsCommand:
    """模型列表查询。"""
    owner_type: str = "SYSTEM"
    owner: str = ""
    keyword: str = ""
    provider_name: str = ""


@dataclass
class GetModelCommand:
    """获取单个模型。"""
    model_id: str = ""


@dataclass
class CreateModelCommand:
    """新建模型源。"""
    name: str = ""
    model_type: str = "LLM"
    provider_name: str = ""
    permission_type: str = "PUBLIC"
    status: bool = True
    owner: str = ""
    owner_type: str = "SYSTEM"
    base_name: str = ""
    app_key: str = ""
    api_url: str = ""
    adv_settings: List[Dict[str, Any]] = field(default_factory=list)
    description: str = ""
    create_user: str = "admin"


@dataclass
class UpdateModelCommand:
    """更新模型源。"""
    model_id: str = ""
    name: Optional[str] = None
    provider_name: Optional[str] = None
    base_name: Optional[str] = None
    api_url: Optional[str] = None
    app_key: Optional[str] = None
    adv_settings: Optional[list] = None
    description: Optional[str] = None
    permission_type: Optional[str] = None
    status: Optional[bool] = None
    create_user: str = "admin"


@dataclass
class DeleteModelCommand:
    """删除模型源。"""
    model_id: str = ""


__all__ = ["ListModelsCommand", "GetModelCommand", "CreateModelCommand",
           "UpdateModelCommand", "DeleteModelCommand"]
