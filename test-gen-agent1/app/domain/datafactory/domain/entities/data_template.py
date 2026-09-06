"""数据模板聚合根 DataTemplate。

聚合边界内的组成：
  - DataTemplate（聚合根）
  - 值对象：Category / TemplateStatus / schema（字段→生成策略定义，此处以
    经过归一化校验的字典承载）

职责：守护数据模板的完整性与业务不变量（名称非空、类别合法、schema 为
字典）。所有变更必须经由聚合根方法触发，业务命令在校验通过后记录领域
事件，供应用层落库 + 发布。
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.datafactory.domain.events import (
    DataTemplateContentChanged,
    DataTemplateCreated,
    DataTemplateDeleted,
    DataTemplateStatusChanged,
)
from app.domain.datafactory.domain.value_objects.category import Category
from app.domain.datafactory.domain.value_objects.field_strategy import FieldStrategy
from app.domain.datafactory.domain.value_objects.template_status import (
    TemplateStatus,
    TemplateStatusEnum,
)


class DataTemplate(AggregateRoot):
    """数据模板聚合根。"""

    def __init__(
        self,
        *,
        template_id: str,
        name: str,
        description: str = "",
        category: str = "custom",
        schema: Optional[dict] = None,
        deps: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        status: str = TemplateStatusEnum.ACTIVE.value,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        _created: bool = False,
    ):
        if not (name or "").strip():
            raise DomainValidationError("数据模板名称不能为空")
        self.id = Identifier.of(template_id)
        self._name = (name or "").strip()
        self._description = description or ""
        self._category = Category(category)
        self._schema = self._normalize_schema(schema or {})
        self._deps = list(deps or [])
        self._tags = list(tags or [])
        self._status = TemplateStatus(status)
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(DataTemplateCreated(self.id.value, self._name))

    @staticmethod
    def _normalize_schema(schema: Any) -> Dict[str, Any]:
        """归一化校验字段定义：非字典抛错，非法策略码抛错。"""
        if schema is None:
            return {}
        if not isinstance(schema, dict):
            raise DomainValidationError("数据模板 schema 必须是字段定义字典")
        normalized: Dict[str, Any] = {}
        for field, spec in schema.items():
            if not isinstance(spec, dict):
                # 允许裸值（固定值简写），但统一归一为 fixed 策略
                normalized[str(field)] = {"strategy": "fixed", "value": spec}
                continue
            strat = spec.get("strategy", "fixed")
            FieldStrategy(strat)  # 校验合法
            normalized[str(field)] = dict(spec)
        return normalized

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def category(self) -> Category:
        return self._category

    @property
    def schema(self) -> Dict[str, Any]:
        return dict(self._schema)

    @property
    def deps(self) -> List[str]:
        return list(self._deps)

    @property
    def tags(self) -> List[str]:
        return list(self._tags)

    @property
    def status(self) -> TemplateStatus:
        return self._status

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def is_active(self) -> bool:
        return self._status.is_active

    def _touch(self, operator: str = "system") -> None:
        self._updated_at = time.time()

    # ── 业务命令（守护不变量）────────────────────────
    def rename(self, new_name: str, operator: str = "system") -> None:
        nn = (new_name or "").strip()
        if not nn:
            raise DomainValidationError("数据模板名称不能为空")
        if nn == self._name:
            return
        self._name = nn
        self._touch()
        self.record_event(DataTemplateContentChanged(self.id.value, "name", operator))

    def change_description(self, text: str, operator: str = "system") -> None:
        self._description = text or ""
        self._touch()
        self.record_event(DataTemplateContentChanged(self.id.value, "description", operator))

    def change_category(self, category: str, operator: str = "system") -> None:
        new_cat = Category(category)
        if new_cat.value == self._category.value:
            return
        self._category = new_cat
        self._touch()
        self.record_event(DataTemplateContentChanged(self.id.value, "category", operator))

    def set_schema(self, schema: Optional[dict], operator: str = "system") -> None:
        normalized = self._normalize_schema(schema or {})
        if normalized == self._schema:
            return
        self._schema = normalized
        self._touch()
        self.record_event(DataTemplateContentChanged(self.id.value, "schema", operator))

    def set_deps(self, deps: Optional[List[str]], operator: str = "system") -> None:
        self._deps = list(deps or [])
        self._touch()
        self.record_event(DataTemplateContentChanged(self.id.value, "deps", operator))

    def set_tags(self, tags: Optional[List[str]], operator: str = "system") -> None:
        self._tags = list(tags or [])
        self._touch()
        self.record_event(DataTemplateContentChanged(self.id.value, "tags", operator))

    def set_status(self, status: str, operator: str = "system") -> None:
        new_status = TemplateStatus(status)
        if new_status.value == self._status.value:
            return
        old = self._status.value
        self._status = new_status
        self._touch()
        self.record_event(DataTemplateStatusChanged(
            self.id.value, old, new_status.value, operator))

    def delete(self, operator: str = "system") -> None:
        """删除数据模板（由仓储置为非活跃/移除）。"""
        self._touch()
        self.record_event(DataTemplateDeleted(self.id.value, operator))

    # ── 快照 / 持久化 ───────────────────────────────
    def to_dict(self) -> dict:
        """导出可落库/可返回给上层视图层的字典。"""
        return {
            "id": self.id.value,
            "name": self._name,
            "description": self._description,
            "category": self._category.value,
            "schema": dict(self._schema),
            "deps": list(self._deps),
            "tags": list(self._tags),
            "status": self._status.value,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "DataTemplate":
        """从持久化字典/仓储返回行重建聚合。"""
        return DataTemplate(
            template_id=str(data.get("id") or data.get("template_id") or ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", "custom"),
            schema=data.get("schema") or {},
            deps=data.get("deps") or [],
            tags=data.get("tags") or [],
            status=data.get("status", "active"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


__all__ = ["DataTemplate"]
