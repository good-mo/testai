"""AI 模型源聚合根 AiModelSource。

聚合边界：
  - AiModelSource（聚合根）：模型源配置（LLM/VISION/AUDIO）
  - 高级配置项（adv_settings）为聚合内嵌 JSON 结构
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.domain.ai_model.domain.events import (
    AiModelCreated,
    AiModelUpdated,
)
from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.time_utils import time_from_row

# 模型类型 / 权限 / 所有者类型
MODEL_TYPE_LLM = "LLM"
MODEL_TYPE_VISION = "VISION"
MODEL_TYPE_AUDIO = "AUDIO"
PERMISSION_PUBLIC = "PUBLIC"
PERMISSION_PRIVATE = "PRIVATE"
OWNER_TYPE_SYSTEM = "SYSTEM"
OWNER_TYPE_PERSONAL = "PERSONAL"


class AiModelSource(AggregateRoot):
    """AI 模型源聚合根。"""

    def __init__(
        self,
        *,
        model_id: str,
        name: str = "",
        model_type: str = MODEL_TYPE_LLM,
        provider_name: str = "",
        permission_type: str = PERMISSION_PUBLIC,
        status: bool = True,
        owner: str = "",
        owner_type: str = OWNER_TYPE_SYSTEM,
        base_name: str = "",
        app_key: str = "",
        api_url: str = "",
        adv_settings: Optional[list] = None,
        description: str = "",
        create_user: str = "admin",
        create_time: Optional[float] = None,
        update_time: Optional[float] = None,
        _created: bool = False,
    ):
        if not model_id:
            raise DomainValidationError("模型 ID 不能为空")
        if not (name or "").strip():
            raise DomainValidationError("模型名称不能为空")
        if owner_type not in (OWNER_TYPE_SYSTEM, OWNER_TYPE_PERSONAL):
            raise DomainValidationError(f"非法 owner_type: {owner_type}")
        self.id = Identifier.of(model_id)
        self._name = (name or "").strip()
        self._model_type = model_type or MODEL_TYPE_LLM
        self._provider_name = provider_name or ""
        self._permission_type = permission_type or PERMISSION_PUBLIC
        self._status = bool(status)
        self._owner = owner or ""
        self._owner_type = owner_type or OWNER_TYPE_SYSTEM
        self._base_name = base_name or ""
        self._app_key = app_key or ""
        self._api_url = api_url or ""
        self._adv_settings = list(adv_settings or [])
        self._description = description or ""
        self._create_user = create_user or "admin"
        now = time.time()
        self._create_time = create_time if create_time is not None else now
        self._update_time = update_time if update_time is not None else now
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(AiModelCreated(self.id.value, self._name, self._provider_name))

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def model_type(self) -> str:
        return self._model_type

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def permission_type(self) -> str:
        return self._permission_type

    @property
    def status(self) -> bool:
        return self._status

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def owner_type(self) -> str:
        return self._owner_type

    @property
    def base_name(self) -> str:
        return self._base_name

    @property
    def app_key(self) -> str:
        return self._app_key

    @property
    def api_url(self) -> str:
        return self._api_url

    @property
    def adv_settings(self) -> List[Dict[str, Any]]:
        return [dict(x) for x in self._adv_settings]

    @property
    def description(self) -> str:
        return self._description

    # ── 业务命令 ─────────────────────────────────────
    def rename(self, name: str) -> None:
        """重命名。"""
        if not (name or "").strip():
            raise DomainValidationError("模型名称不能为空")
        self._name = (name or "").strip()
        self._touch()

    def enable(self) -> None:
        """启用。"""
        self._status = True
        self._touch()

    def disable(self) -> None:
        """停用。"""
        self._status = False
        self._touch()

    def update_settings(self, *, name: Optional[str] = None,
                        provider_name: Optional[str] = None,
                        base_name: Optional[str] = None,
                        api_url: Optional[str] = None,
                        app_key: Optional[str] = None,
                        adv_settings: Optional[list] = None,
                        description: Optional[str] = None,
                        permission_type: Optional[str] = None,
                        status: Optional[bool] = None) -> None:
        """批量更新模型源配置。"""
        if name is not None:
            if not (name or "").strip():
                raise DomainValidationError("模型名称不能为空")
            self._name = (name or "").strip()
        if provider_name is not None:
            self._provider_name = provider_name
        if base_name is not None:
            self._base_name = base_name
        if api_url is not None:
            self._api_url = api_url
        if app_key is not None:
            self._app_key = app_key
        if adv_settings is not None:
            self._adv_settings = list(adv_settings)
        if description is not None:
            self._description = description
        if permission_type is not None:
            self._permission_type = permission_type
        if status is not None:
            self._status = bool(status)
        self.record_event(AiModelUpdated(self.id.value))
        self._touch()

    def _touch(self) -> None:
        self._update_time = time.time()

    # ── 持久化 ───────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "name": self._name,
            "type": self._model_type,
            "providerName": self._provider_name,
            "permissionType": self._permission_type,
            "status": self._status,
            "owner": self._owner,
            "ownerType": self._owner_type,
            "baseName": self._base_name,
            "appKey": self._app_key,
            "apiUrl": self._api_url,
            "advSettingDTOList": self._adv_settings,
            "description": self._description,
            "createUser": self._create_user,
            "createTime": int(self._create_time * 1000) if self._create_time else 0,
            "updateTime": int(self._update_time * 1000) if self._update_time else 0,
        }

    @staticmethod
    def from_dict(data: dict) -> "AiModelSource":
        return AiModelSource(
            model_id=str(data.get("id") or data.get("model_id") or ""),
            name=data.get("name", ""),
            model_type=data.get("type", MODEL_TYPE_LLM),
            provider_name=data.get("providerName", "") or data.get("provider_name", ""),
            permission_type=data.get("permissionType", PERMISSION_PUBLIC),
            status=bool(data.get("status", True)),
            owner=data.get("owner", ""),
            owner_type=data.get("ownerType", OWNER_TYPE_SYSTEM) or data.get("owner_type", OWNER_TYPE_SYSTEM),
            base_name=data.get("baseName", "") or data.get("base_name", ""),
            app_key=data.get("appKey", "") or data.get("app_key", ""),
            api_url=data.get("apiUrl", "") or data.get("api_url", ""),
            adv_settings=data.get("advSettingDTOList") or data.get("adv_settings") or [],
            description=data.get("description", ""),
            create_user=data.get("createUser", "admin"),
            create_time=time_from_row(data, "create_time", "createTime"),
            update_time=time_from_row(data, "update_time", "updateTime"),
        )
