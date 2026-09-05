"""接口场景聚合根 Scenario。

聚合边界内的组成：
  - Scenario（聚合根）
  - 值对象：ScenarioStatus / steps[]

职责：守护接口场景的完整性与业务不变量（名称非空、状态机迁移合法）。
所有变更必须经由聚合根方法触发，业务命令在校验通过后记录领域事件。

底层数据表：api_scenarios。
"""
from __future__ import annotations

import json
import time
from typing import List, Optional

from app.domain.apitest.domain.events import (
    ScenarioRenamed,
    ScenarioRestored,
    ScenarioSoftDeleted,
    ScenarioStatusChanged,
    ScenarioUpdated,
)
from app.domain.apitest.domain.services.apitest_policy import ApiStatePolicy
from app.domain.apitest.domain.value_objects.status import (
    ScenarioStatus,
    ScenarioStatusEnum,
)
from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError


class Scenario(AggregateRoot):
    """接口场景聚合根。"""

    def __init__(
        self,
        *,
        scenario_id: str,
        name: str,
        steps: Optional[List[dict]] = None,
        description: str = "",
        status: str = ScenarioStatusEnum.DRAFT.value,
        environment_id: str = "",
        project_id: str = "",
        metadata: Optional[dict] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        deleted: bool = False,
    ):
        if not (name or "").strip():
            raise DomainValidationError("接口场景名称不能为空")
        self.id = Identifier.of(scenario_id)
        self._name = (name or "").strip()
        self._steps = [dict(s) for s in (steps or [])]
        self._description = description or ""
        self._status = ScenarioStatus(status)
        self._environment_id = environment_id or ""
        self._project_id = project_id or ""
        self._metadata = dict(metadata or {})
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._deleted = bool(deleted)
        self._domain_events = []
        self.version = 0

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def steps(self) -> List[dict]:
        return [dict(s) for s in self._steps]

    @property
    def description(self) -> str:
        return self._description

    @property
    def status(self) -> ScenarioStatus:
        return self._status

    @property
    def environment_id(self) -> str:
        return self._environment_id

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def metadata(self) -> dict:
        return dict(self._metadata)

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def deleted(self) -> bool:
        return self._deleted or self._status.is_deprecated

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 业务命令（守护不变量）────────────────────────
    def rename(self, new_name: str, operator: str = "system") -> None:
        """修改接口场景名称。"""
        nn = (new_name or "").strip()
        if not nn:
            raise DomainValidationError("接口场景名称不能为空")
        if nn == self._name:
            return
        old = self._name
        self._name = nn
        self._touch()
        self.record_event(ScenarioRenamed(self.id.value, old, nn, operator))

    def change_description(self, text: str, operator: str = "system") -> None:
        self._description = text or ""
        self._touch()
        self.record_event(ScenarioUpdated(self.id.value, self._name, operator))

    def change_status(self, target: str, operator: str = "system") -> None:
        """受状态机约束的状态迁移（不含软删除）。"""
        target_status = ScenarioStatus(target)
        if target_status.is_deprecated:
            raise DomainValidationError("请使用 delete() 软删除")
        ApiStatePolicy().ensure_scenario_transition_allowed(self._status, target_status)
        if self._status.value is target_status.value:
            return
        old = self._status.value.value
        self._status = target_status
        self._touch()
        self.record_event(ScenarioStatusChanged(
            self.id.value, old, target_status.value.value, operator))

    def set_steps(self, steps: List[dict], operator: str = "system") -> None:
        """设置场景步骤列表。"""
        self._steps = [dict(s) for s in (steps or [])]
        self._touch()
        self.record_event(ScenarioUpdated(self.id.value, self._name, operator))

    def set_content(
        self,
        *,
        name: Optional[str] = None,
        steps: Optional[List[dict]] = None,
        description: Optional[str] = None,
        environment_id: Optional[str] = None,
        project_id: Optional[str] = None,
        operator: str = "system",
    ) -> None:
        """原子更新接口场景内容。"""
        if name is not None:
            self.rename(name, operator)
        if steps is not None:
            self._steps = [dict(s) for s in (steps or [])]
        if description is not None:
            self._description = description or ""
        if environment_id is not None:
            self._environment_id = environment_id or ""
        if project_id is not None:
            self._project_id = project_id or ""
        self._touch()
        self.record_event(ScenarioUpdated(self.id.value, self._name, operator))

    def delete(self, operator: str = "system", reason: str = "") -> None:
        """软删除进入回收站。"""
        if self._deleted:
            raise DomainValidationError("接口场景已在回收站，不可重复删除")
        self._deleted = True
        self._touch()
        self.record_event(ScenarioSoftDeleted(self.id.value, operator, reason))

    def restore(self, operator: str = "system") -> None:
        """从回收站恢复。"""
        if not self._deleted:
            raise DomainValidationError("接口场景不在回收站，无需恢复")
        self._deleted = False
        self._touch()
        self.record_event(ScenarioRestored(self.id.value, operator))

    # ── 持久化 ───────────────────────────────────────
    def to_dict(self) -> dict:
        """导出可落库/返回给上层视图层的字典。"""
        return {
            "id": self.id.value,
            "name": self._name,
            "steps": [dict(s) for s in self._steps],
            "description": self._description,
            "status": self._status.value.value,
            "environment_id": self._environment_id,
            "project_id": self._project_id,
            "metadata": dict(self._metadata),
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "deleted": 1 if self._deleted else 0,
        }

    @staticmethod
    def from_dict(data: dict) -> "Scenario":
        """从持久化字典/仓储返回行重建聚合。"""
        def _load_str(v, default=None):
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    return default
            return v or default

        def _load_list(v):
            r = _load_str(v, [])
            return r if isinstance(r, list) else []

        steps = _load_list(data.get("steps"))
        metadata = _load_str(data.get("metadata"), {})
        if not isinstance(metadata, dict):
            metadata = {}

        return Scenario(
            scenario_id=str(data.get("id") or data.get("scenario_id") or ""),
            name=data.get("name", ""),
            steps=steps,
            description=data.get("description", ""),
            status=data.get("status", ScenarioStatusEnum.DRAFT.value),
            environment_id=data.get("environment_id", ""),
            project_id=data.get("project_id", ""),
            metadata=metadata,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            deleted=bool(data.get("deleted", 0)),
        )
