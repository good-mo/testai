"""模板聚合根 Template。

模板：项目/组织通用的字段配置模板，管理字段布局（custom_fields /
system_fields）在不同业务场景（功能用例/API/UI/测试计划/缺陷）下的
展示结构。

聚合边界：
  - Template（聚合根）：模板基本信息 + 场景 + 作用域
  - 自定义字段/系统字段/上传图片 为聚合内值对象（以 JSON 结构承载）
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.time_utils import time_from_row
from app.domain.template.domain.events import (
    TemplateCreated,
    TemplateDeleted,
    TemplateUpdated,
)
from app.domain.template.domain.value_objects.template_scene import ScopeType, TemplateScene


class Template(AggregateRoot):
    """模板聚合根。"""

    def __init__(
        self,
        *,
        template_id: str,
        name: str = "",
        remark: str = "",
        scene: str = "FUNCTIONAL",
        scope_type: str = "PROJECT",
        scope_id: str = "",
        internal: bool = False,
        enable_default: bool = False,
        enable_third_part: bool = False,
        ref_id: str = "",
        platform_default: bool = False,
        custom_fields: Optional[list] = None,
        system_fields: Optional[list] = None,
        upload_img_file_ids: Optional[list] = None,
        create_time: Optional[float] = None,
        update_time: Optional[float] = None,
        create_user: str = "admin",
        update_user: str = "admin",
        _created: bool = False,
    ):
        if not template_id:
            raise DomainValidationError("模板 ID 不能为空")
        if not (name or "").strip():
            raise DomainValidationError("模板名称不能为空")
        self.id = Identifier.of(template_id)
        self._name = (name or "").strip()
        self._remark = remark or ""
        self._scene = TemplateScene(scene)
        self._scope_type = ScopeType(scope_type)
        self._scope_id = scope_id or ""
        self._internal = bool(internal)
        self._enable_default = bool(enable_default)
        self._enable_third_part = bool(enable_third_part)
        self._ref_id = ref_id or ""
        self._platform_default = bool(platform_default)
        self._custom_fields = [dict(f) for f in (custom_fields or [])]
        self._system_fields = [dict(f) for f in (system_fields or [])]
        self._upload_img_file_ids = list(upload_img_file_ids or [])
        self._create_time = create_time if create_time is not None else time.time()
        self._update_time = update_time if update_time is not None else self._create_time
        self._create_user = create_user or "admin"
        self._update_user = update_user or "admin"
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(TemplateCreated(
                self.id.value, self._scene.value, self._scope_type.value, self._scope_id))

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def remark(self) -> str:
        return self._remark

    @property
    def scene(self) -> TemplateScene:
        return self._scene

    @property
    def scope_type(self) -> ScopeType:
        return self._scope_type

    @property
    def scope_id(self) -> str:
        return self._scope_id

    @property
    def is_internal(self) -> bool:
        return self._internal

    @property
    def is_default(self) -> bool:
        return self._enable_default

    @property
    def is_third_part(self) -> bool:
        return self._enable_third_part

    @property
    def ref_id(self) -> str:
        return self._ref_id

    @property
    def is_platform_default(self) -> bool:
        return self._platform_default

    @property
    def custom_fields(self) -> List[dict]:
        return [dict(f) for f in self._custom_fields]

    @property
    def system_fields(self) -> List[dict]:
        return [dict(f) for f in self._system_fields]

    @property
    def upload_img_file_ids(self) -> List[str]:
        return list(self._upload_img_file_ids)

    @property
    def create_time(self) -> float:
        return self._create_time

    @property
    def update_time(self) -> float:
        return self._update_time

    @property
    def create_user(self) -> str:
        return self._create_user

    @property
    def update_user(self) -> str:
        return self._update_user

    # ── 业务命令 ─────────────────────────────────────
    def rename(self, name: str, operator: str = "system") -> None:
        if not (name or "").strip():
            raise DomainValidationError("模板名称不能为空")
        old = self._name
        self._name = name.strip()
        self._update_user = operator
        self._touch()
        if old != self._name:
            self.record_event(TemplateUpdated(self.id.value, "rename"))

    def update_meta(self, data: dict, operator: str = "system") -> None:
        """更新模板元数据（名称/备注/自定义字段等）。"""
        if "name" in data:
            if not (data.get("name") or "").strip():
                raise DomainValidationError("模板名称不能为空")
            self._name = data["name"].strip()
        if "remark" in data:
            self._remark = data.get("remark") or ""
        if "scene" in data:
            self._scene = TemplateScene(data["scene"])
        if "custom_fields" in data:
            self._custom_fields = [dict(f) for f in (data["custom_fields"] or [])]
        if "system_fields" in data:
            self._system_fields = [dict(f) for f in (data["system_fields"] or [])]
        if "upload_img_file_ids" in data:
            self._upload_img_file_ids = list(data["upload_img_file_ids"] or [])
        if "internal" in data:
            self._internal = bool(data["internal"])
        if "enable_third_part" in data or "enableThirdPart" in data:
            self._enable_third_part = bool(data.get("enable_third_part", data.get("enableThirdPart", False)))
        if "enable_default" in data or "enableDefault" in data:
            self._enable_default = bool(data.get("enable_default", data.get("enableDefault", False)))
        if "ref_id" in data:
            self._ref_id = data.get("ref_id") or ""
        self._update_user = operator
        self._touch()
        self.record_event(TemplateUpdated(self.id.value, "meta"))

    def set_default(self) -> None:
        """标记为默认模板。"""
        self._enable_default = True
        self.record_event(TemplateUpdated(self.id.value, "set_default"))

    def clear_default(self) -> None:
        """清除默认标记。"""
        self._enable_default = False
        self.record_event(TemplateUpdated(self.id.value, "clear_default"))

    def mark_deleted(self, operator: str = "system") -> None:
        """物理删除由仓储完成，此处标记并记录事件。"""
        self.record_event(TemplateDeleted(self.id.value, operator))

    def _touch(self) -> None:
        self._update_time = time.time()

    # ── 序列化 ─────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "name": self._name,
            "remark": self._remark,
            "scene": self._scene.value,
            "scopeId": self._scope_id,
            "scopeType": self._scope_type.value,
            "internal": self._internal,
            "enableDefault": self._enable_default,
            "enableThirdPart": self._enable_third_part,
            "platformDefault": self._platform_default,
            "refId": self._ref_id,
            "customFields": self._custom_fields,
            "systemFields": self._system_fields,
            "uploadImgFileIds": self._upload_img_file_ids,
            "createTime": int(self._create_time * 1000),
            "updateTime": int(self._update_time * 1000),
            "createUser": self._create_user,
            "updateUser": self._update_user,
        }

    @staticmethod
    def from_dict(data: dict) -> "Template":
        return Template(
            template_id=str(data.get("id") or data.get("template_id") or ""),
            name=data.get("name", ""),
            remark=data.get("remark", ""),
            scene=data.get("scene", "FUNCTIONAL"),
            scope_type=data.get("scope_type", data.get("scopeType", "PROJECT")),
            scope_id=data.get("scope_id", data.get("scopeId", "")),
            internal=bool(data.get("internal", 0)),
            enable_default=bool(data.get("enable_default", data.get("enableDefault", 0))),
            enable_third_part=bool(data.get("enable_third_part", data.get("enableThirdPart", 0))),
            ref_id=data.get("ref_id", data.get("refId", "")),
            platform_default=bool(data.get("platform_default", data.get("platformDefault", 0))),
            custom_fields=data.get("custom_fields", data.get("customFields")),
            system_fields=data.get("system_fields", data.get("systemFields")),
            upload_img_file_ids=data.get("upload_img_file_ids", data.get("uploadImgFileIds")),
            create_time=time_from_row(data, "create_time", "createTime"),
            update_time=time_from_row(data, "update_time", "updateTime"),
            create_user=data.get("create_user", data.get("createUser", "admin")),
            update_user=data.get("update_user", data.get("updateUser", "admin")),
        )


__all__ = ["Template"]
