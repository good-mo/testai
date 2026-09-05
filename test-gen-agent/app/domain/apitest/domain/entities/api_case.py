"""接口用例聚合根 ApiCase。

聚合边界内的组成：
  - ApiCase（聚合根）
  - 值对象：Priority / ApiCaseStatus / request / asserts[] / variables[]

职责：守护接口用例完整性与业务不变量（名称非空、状态机迁移合法、优先级合法）。
所有变更必须经由聚合根方法触发，业务命令在校验通过后记录领域事件。

底层数据表：api_cases。
"""
from __future__ import annotations

import json
import time
from typing import List, Optional

from app.domain.apitest.domain.events import (
    ApiCasePriorityChanged,
    ApiCaseRenamed,
    ApiCaseRestored,
    ApiCaseSoftDeleted,
    ApiCaseStatusChanged,
    ApiCaseUpdated,
)
from app.domain.apitest.domain.services.apitest_policy import ApiStatePolicy
from app.domain.apitest.domain.value_objects.priority import Priority
from app.domain.apitest.domain.value_objects.status import (
    ApiCaseStatus,
    ApiCaseStatusEnum,
)
from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError


class ApiCase(AggregateRoot):
    """接口用例聚合根。"""

    def __init__(
        self,
        *,
        case_id: str,
        name: str,
        api_definition_id: str = "",
        request: Optional[dict] = None,
        asserts: Optional[List[dict]] = None,
        pre_scripts: Optional[List[str]] = None,
        post_scripts: Optional[List[str]] = None,
        pre_sql: Optional[List[dict]] = None,
        post_sql: Optional[List[dict]] = None,
        variables: Optional[List[dict]] = None,
        logic_controllers: Optional[List[dict]] = None,
        environment_id: str = "",
        status: str = ApiCaseStatusEnum.DRAFT.value,
        priority: str = "P2",
        description: str = "",
        project_id: str = "",
        metadata: Optional[dict] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        deleted: bool = False,
    ):
        if not (name or "").strip():
            raise DomainValidationError("接口用例名称不能为空")
        self.id = Identifier.of(case_id)
        self._name = (name or "").strip()
        self._api_definition_id = api_definition_id or ""
        self._request = dict(request or {})
        self._asserts = [dict(a) for a in (asserts or [])]
        self._pre_scripts = list(pre_scripts or [])
        self._post_scripts = list(post_scripts or [])
        self._pre_sql = [dict(s) for s in (pre_sql or [])]
        self._post_sql = [dict(s) for s in (post_sql or [])]
        self._variables = [dict(v) for v in (variables or [])]
        self._logic_controllers = [dict(c) for c in (logic_controllers or [])]
        self._environment_id = environment_id or ""
        self._status = ApiCaseStatus(status)
        self._priority = Priority(priority)
        self._description = description or ""
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
    def api_definition_id(self) -> str:
        return self._api_definition_id

    @property
    def request(self) -> dict:
        return dict(self._request)

    @property
    def asserts(self) -> List[dict]:
        return [dict(a) for a in self._asserts]

    @property
    def pre_scripts(self) -> List[str]:
        return list(self._pre_scripts)

    @property
    def post_scripts(self) -> List[str]:
        return list(self._post_scripts)

    @property
    def pre_sql(self) -> List[dict]:
        return [dict(s) for s in self._pre_sql]

    @property
    def post_sql(self) -> List[dict]:
        return [dict(s) for s in self._post_sql]

    @property
    def variables(self) -> List[dict]:
        return [dict(v) for v in self._variables]

    @property
    def logic_controllers(self) -> List[dict]:
        return [dict(c) for c in self._logic_controllers]

    @property
    def environment_id(self) -> str:
        return self._environment_id

    @property
    def status(self) -> ApiCaseStatus:
        return self._status

    @property
    def priority(self) -> Priority:
        return self._priority

    @property
    def description(self) -> str:
        return self._description

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
        """修改接口用例名称。"""
        nn = (new_name or "").strip()
        if not nn:
            raise DomainValidationError("接口用例名称不能为空")
        if nn == self._name:
            return
        old = self._name
        self._name = nn
        self._touch()
        self.record_event(ApiCaseRenamed(self.id.value, old, nn, operator))

    def change_description(self, text: str, operator: str = "system") -> None:
        self._description = text or ""
        self._touch()
        self.record_event(ApiCaseUpdated(self.id.value, self._name, operator))

    def change_priority(self, priority: str, operator: str = "system") -> None:
        new_p = Priority(priority)
        if new_p.value == self._priority.value:
            return
        old = self._priority.value
        self._priority = new_p
        self._touch()
        self.record_event(ApiCasePriorityChanged(
            self.id.value, old, new_p.value, operator))

    def change_status(self, target: str, operator: str = "system") -> None:
        """受状态机约束的状态迁移（不含软删除）。"""
        target_status = ApiCaseStatus(target)
        if target_status.is_deprecated:
            raise DomainValidationError("请使用 delete() 软删除")
        ApiStatePolicy().ensure_case_transition_allowed(self._status, target_status)
        if self._status.value is target_status.value:
            return
        old = self._status.value.value
        self._status = target_status
        self._touch()
        self.record_event(ApiCaseStatusChanged(
            self.id.value, old, target_status.value.value, operator))

    def set_request(self, request: dict, operator: str = "system") -> None:
        """设置用例请求内容。"""
        self._request = dict(request or {})
        self._touch()
        self.record_event(ApiCaseUpdated(self.id.value, self._name, operator))

    def set_asserts(self, asserts: List[dict], operator: str = "system") -> None:
        """设置断言规则列表。"""
        self._asserts = [dict(a) for a in (asserts or [])]
        self._touch()
        self.record_event(ApiCaseUpdated(self.id.value, self._name, operator))

    def set_content(
        self,
        *,
        name: Optional[str] = None,
        api_definition_id: Optional[str] = None,
        request: Optional[dict] = None,
        asserts: Optional[List[dict]] = None,
        pre_scripts: Optional[List[str]] = None,
        post_scripts: Optional[List[str]] = None,
        pre_sql: Optional[List[dict]] = None,
        post_sql: Optional[List[dict]] = None,
        variables: Optional[List[dict]] = None,
        logic_controllers: Optional[List[dict]] = None,
        environment_id: Optional[str] = None,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        operator: str = "system",
    ) -> None:
        """原子更新接口用例内容。"""
        if name is not None:
            self.rename(name, operator)
        if api_definition_id is not None:
            self._api_definition_id = api_definition_id or ""
        if request is not None:
            self._request = dict(request or {})
        if asserts is not None:
            self._asserts = [dict(a) for a in (asserts or [])]
        if pre_scripts is not None:
            self._pre_scripts = list(pre_scripts or [])
        if post_scripts is not None:
            self._post_scripts = list(post_scripts or [])
        if pre_sql is not None:
            self._pre_sql = [dict(s) for s in (pre_sql or [])]
        if post_sql is not None:
            self._post_sql = [dict(s) for s in (post_sql or [])]
        if variables is not None:
            self._variables = [dict(v) for v in (variables or [])]
        if logic_controllers is not None:
            self._logic_controllers = [dict(c) for c in (logic_controllers or [])]
        if environment_id is not None:
            self._environment_id = environment_id or ""
        if description is not None:
            self._description = description or ""
        if project_id is not None:
            self._project_id = project_id or ""
        self._touch()
        self.record_event(ApiCaseUpdated(self.id.value, self._name, operator))

    def delete(self, operator: str = "system", reason: str = "") -> None:
        """软删除进入回收站。"""
        if self._deleted:
            raise DomainValidationError("接口用例已在回收站，不可重复删除")
        if self._status.is_deprecated:
            raise DomainValidationError("接口用例已在回收站")
        self._deleted = True
        self._touch()
        self.record_event(ApiCaseSoftDeleted(self.id.value, operator, reason))

    def restore(self, operator: str = "system") -> None:
        """从回收站恢复。"""
        if not self._deleted:
            raise DomainValidationError("接口用例不在回收站，无需恢复")
        self._deleted = False
        self._touch()
        self.record_event(ApiCaseRestored(self.id.value, operator))

    # ── 持久化 ───────────────────────────────────────
    def to_dict(self) -> dict:
        """导出可落库/返回给上层视图层的字典。"""
        return {
            "id": self.id.value,
            "name": self._name,
            "api_definition_id": self._api_definition_id,
            "request": dict(self._request),
            "asserts": [dict(a) for a in self._asserts],
            "pre_scripts": list(self._pre_scripts),
            "post_scripts": list(self._post_scripts),
            "pre_sql": [dict(s) for s in self._pre_sql],
            "post_sql": [dict(s) for s in self._post_sql],
            "variables": [dict(v) for v in self._variables],
            "logic_controllers": [dict(c) for c in self._logic_controllers],
            "environment_id": self._environment_id,
            "status": self._status.value.value,
            "priority": self._priority.value,
            "description": self._description,
            "project_id": self._project_id,
            "metadata": dict(self._metadata),
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "deleted": 1 if self._deleted else 0,
        }

    @staticmethod
    def from_dict(data: dict) -> "ApiCase":
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

        def _load_dict(v):
            r = _load_str(v, {})
            return r if isinstance(r, dict) else {}

        request = _load_dict(data.get("request"))
        asserts = _load_list(data.get("asserts"))
        pre_scripts = _load_list(data.get("pre_scripts"))
        post_scripts = _load_list(data.get("post_scripts"))
        pre_sql = _load_list(data.get("pre_sql"))
        post_sql = _load_list(data.get("post_sql"))
        variables = _load_list(data.get("variables"))
        logic_controllers = _load_list(data.get("logic_controllers"))
        metadata = _load_dict(data.get("metadata"))

        deleted = bool(data.get("deleted", 0))
        return ApiCase(
            case_id=str(data.get("id") or data.get("case_id") or ""),
            name=data.get("name", ""),
            api_definition_id=data.get("api_definition_id", ""),
            request=request,
            asserts=asserts,
            pre_scripts=pre_scripts,
            post_scripts=post_scripts,
            pre_sql=pre_sql,
            post_sql=post_sql,
            variables=variables,
            logic_controllers=logic_controllers,
            environment_id=data.get("environment_id", ""),
            status=data.get("status", ApiCaseStatusEnum.DRAFT.value),
            priority=data.get("priority", "P2"),
            description=data.get("description", ""),
            project_id=data.get("project_id", ""),
            metadata=metadata,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            deleted=deleted,
        )
