"""工作流状态聚合根 WorkflowStatus。"""
from __future__ import annotations

import json
import time
from typing import List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.time_utils import MS_PER_SECOND, seconds_to_ms, time_from_row
from app.domain.workflow.domain.events import (
    WorkflowStatusCreated,
    WorkflowStatusUpdated,
)

# 状态定义类型
DEF_START = "START"
DEF_END = "END"


class WorkflowStatus(AggregateRoot):
    """工作流状态聚合根。

    时间约定（与共享内核一致）：聚合内部与 DB 列存 **秒**，``to_dict()`` 对外视图
    输出 **毫秒**（camelCase createTime/updateTime），``from_dict()`` 经
    ``time_from_row`` 兼容 DB 秒行与 camel 毫秒行，杜绝「读→改→存」时间放大 1000 倍。
    """

    def __init__(
        self,
        *,
        status_id: str,
        scope_type: str = "PROJECT",
        scope_id: str = "",
        scene: str = "FUNCTIONAL",
        name: str = "",
        remark: str = "",
        pos: int = 0,
        status_definitions: Optional[list] = None,
        internal: bool = False,
        create_user: str = "admin",
        create_time: Optional[float] = None,
        update_time: Optional[float] = None,
        status_flow_targets: Optional[list] = None,
        _created: bool = False,
    ):
        if not status_id:
            raise DomainValidationError("状态 ID 不能为空")
        if not (name or "").strip():
            raise DomainValidationError("状态名称不能为空")
        self.id = Identifier.of(status_id)
        self._scope_type = scope_type or "PROJECT"
        self._scope_id = scope_id or ""
        self._scene = scene or "FUNCTIONAL"
        self._name = (name or "").strip()
        self._remark = remark or ""
        self._pos = int(pos or 0)
        self._status_definitions = list(status_definitions or [])
        self._internal = bool(internal)
        self._create_user = create_user or "admin"
        # 只读的流转关系（read-model，来源 workflow_flows 表，不入聚合状态）
        self._status_flow_targets = list(status_flow_targets or [])
        now = time.time()
        self._create_time = create_time if create_time is not None else now
        self._update_time = update_time if update_time is not None else now
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(WorkflowStatusCreated(self.id.value, self._name))

    @property
    def scope_type(self) -> str:
        return self._scope_type
    @property
    def scope_id(self) -> str:
        return self._scope_id
    @property
    def scene(self) -> str:
        return self._scene
    @property
    def name(self) -> str:
        return self._name
    @property
    def remark(self) -> str:
        return self._remark
    @property
    def status_definitions(self) -> list:
        return list(self._status_definitions)
    @property
    def internal(self) -> bool:
        return self._internal
    @property
    def status_flow_targets(self) -> List[str]:
        """只读：本状态可流转到的目标状态 id 列表。"""
        return list(self._status_flow_targets)

    def update_info(self, *, name: Optional[str] = None,
                    remark: Optional[str] = None,
                    all_transfer_to: Optional[bool] = None,
                    status_definitions: Optional[list] = None) -> None:
        if name is not None:
            if not (name or "").strip():
                raise DomainValidationError("状态名称不能为空")
            self._name = (name or "").strip()
        if remark is not None:
            self._remark = remark
        if status_definitions is not None:
            self._status_definitions = list(status_definitions)
        self._update_time = time.time()
        self.record_event(WorkflowStatusUpdated(self.id.value))

    def is_start(self) -> bool:
        """是否为初始态。"""
        return DEF_START in self._status_definitions

    def is_end(self) -> bool:
        """是否为结束态。"""
        return DEF_END in self._status_definitions

    def set_definition(self, definition_id: str, enable: bool) -> None:
        """设置初始态/结束态标记。"""
        if definition_id not in (DEF_START, DEF_END):
            raise DomainValidationError(f"非法 definition_id: {definition_id}")
        if enable:
            if definition_id not in self._status_definitions:
                self._status_definitions.append(definition_id)
        else:
            self._status_definitions = [
                d for d in self._status_definitions if d != definition_id]
        self._update_time = time.time()

    def to_dict(self) -> dict:
        """对外视图（camelCase，createTime/updateTime 毫秒，含流转目标）。"""
        return {
            "id": self.id.value,
            "scopeType": self._scope_type,
            "scopeId": self._scope_id,
            "scene": self._scene,
            "name": self._name,
            "remark": self._remark,
            "pos": self._pos,
            "statusDefinitions": list(self._status_definitions),
            "internal": self._internal,
            "createUser": self._create_user,
            "statusFlowTargets": list(self._status_flow_targets),
            "createTime": seconds_to_ms(self._create_time) if self._create_time else 0,
            "updateTime": seconds_to_ms(self._update_time) if self._update_time else 0,
        }

    @staticmethod
    def from_dict(data: dict) -> "WorkflowStatus":
        defs = data.get("status_definitions") or data.get("statusDefinitions") or []
        if isinstance(defs, str):
            try:
                defs = json.loads(defs)
            except Exception:
                defs = []
        flows = data.get("status_flow_targets") or data.get("statusFlowTargets") or []
        if isinstance(flows, str):
            try:
                flows = json.loads(flows)
            except Exception:
                flows = []
        return WorkflowStatus(
            status_id=str(data.get("id") or ""),
            scope_type=data.get("scope_type") or data.get("scopeType") or "PROJECT",
            scope_id=data.get("scope_id") or data.get("scopeId") or "",
            scene=data.get("scene") or "FUNCTIONAL",
            name=data.get("name", ""),
            remark=data.get("remark", ""),
            pos=data.get("pos", 0),
            status_definitions=defs,
            internal=bool(data.get("internal", False)),
            create_user=data.get("create_user") or data.get("createUser") or "admin",
            create_time=time_from_row(data, "create_time", "createTime"),
            update_time=time_from_row(data, "update_time", "updateTime"),
            status_flow_targets=flows,
        )
