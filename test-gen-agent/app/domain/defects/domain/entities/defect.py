"""缺陷聚合根 Defect。

聚合边界内的组成：
  - Defect（聚合根）
  - 若干值对象：Severity / DefectStatus / tags

职责：守护缺陷的完整性与业务不变量（状态机迁移、严重程度合法、标题非空等）。
所有变更必须经由聚合根方法触发，业务命令在校验通过后记录领域事件，
供应用层落库 + 发布，从而与通知/审计等副作用解耦。
"""
from __future__ import annotations

import json
import time
from typing import List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.defects.domain.events import (
    DefectContentChanged,
    DefectRestored,
    DefectSeverityChanged,
    DefectSoftDeleted,
    DefectStatusChanged,
    DefectTitleChanged,
)
from app.domain.defects.domain.value_objects.severity import Severity, SeverityEnum
from app.domain.defects.domain.value_objects.status import DefectStatus, DefectStatusEnum


class Defect(AggregateRoot):
    """缺陷聚合根。"""

    def __init__(
        self,
        *,
        defect_id: str,
        title: str,
        description: str = "",
        severity: str = SeverityEnum.MAJOR.value,
        status: str = DefectStatusEnum.OPEN.value,
        file_path: str = "",
        test_case_id: str = "",
        error_snippet: str = "",
        assignee: str = "",
        tags: Optional[List[str]] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        deleted: bool = False,
    ):
        if not (title or "").strip():
            raise DomainValidationError("缺陷标题不能为空")
        self.id = Identifier.of(defect_id)
        self._title = (title or "").strip()
        self._description = description or ""
        self._severity = Severity(severity)
        self._status = DefectStatus(status)
        self._file_path = file_path or ""
        self._test_case_id = test_case_id or ""
        self._error_snippet = error_snippet or ""
        self._assignee = assignee or ""
        self._tags = list(tags or [])
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._deleted: bool = bool(deleted)
        self._domain_events = []
        self.version = 0

    # ── 只读属性 ─────────────────────────────────────
    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> str:
        return self._description

    @property
    def severity(self) -> Severity:
        return self._severity

    @property
    def status(self) -> DefectStatus:
        return self._status

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def test_case_id(self) -> str:
        return self._test_case_id

    @property
    def error_snippet(self) -> str:
        return self._error_snippet

    @property
    def assignee(self) -> str:
        return self._assignee

    @property
    def tags(self) -> List[str]:
        return list(self._tags)

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def deleted(self) -> bool:
        return self._deleted

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 业务命令（守护不变量）────────────────────────
    def rename(self, new_title: str, operator: str = "system") -> None:
        nt = (new_title or "").strip()
        if not nt:
            raise DomainValidationError("缺陷标题不能为空")
        if nt == self._title:
            return
        old = self._title
        self._title = nt
        self._touch()
        self.record_event(DefectTitleChanged(self.id.value, old, nt, operator))

    def change_description(self, text: str, operator: str = "system") -> None:
        self._description = text or ""
        self._touch()
        self.record_event(DefectContentChanged(self.id.value, "description", operator))

    def change_severity(self, severity: str, operator: str = "system") -> None:
        new_sev = Severity(severity)
        if new_sev.value == self._severity.value:
            return
        old = self._severity.value
        self._severity = new_sev
        self._touch()
        self.record_event(DefectSeverityChanged(self.id.value, old, new_sev.value, operator))

    def assign(self, assignee: str, operator: str = "system") -> None:
        if (assignee or "") == self._assignee:
            return
        self._assignee = assignee or ""
        self._touch()
        self.record_event(DefectContentChanged(self.id.value, "assignee", operator))

    def set_tags(self, tags: List[str], operator: str = "system") -> None:
        self._tags = list(tags or [])
        self._touch()
        self.record_event(DefectContentChanged(self.id.value, "tags", operator))

    def change_status(self, target: str, operator: str = "system") -> None:
        """受状态机约束的状态迁移（不含软删除）。"""
        target_status = DefectStatus(target)
        if target_status.is_trashed:
            raise DomainValidationError("请使用 delete() 软删除")
        from app.domain.defects.domain.services.defect_policy import DefectLifecyclePolicy
        DefectLifecyclePolicy().ensure_transition_allowed(self._status, target_status)
        if self._status.value is target_status.value:
            return
        old = self._status.value.value
        self._status = target_status
        self._touch()
        self.record_event(DefectStatusChanged(self.id.value, old, target_status.value.value, operator))

    def delete(self, operator: str = "system") -> None:
        """软删除移入回收站。"""
        if self._deleted:
            raise DomainValidationError("缺陷已在回收站，不可重复删除")
        self._deleted = True
        self._touch()
        self.record_event(DefectSoftDeleted(self.id.value, operator))

    def restore(self, operator: str = "system") -> None:
        """从回收站恢复。"""
        if not self._deleted:
            raise DomainValidationError("缺陷不在回收站，无需恢复")
        self._deleted = False
        self._touch()
        self.record_event(DefectRestored(self.id.value, operator))

    # ── 快照 / 持久化 ───────────────────────────────
    def to_dict(self) -> dict:
        """导出可落库 / 返回给上层视图层的字典。"""
        return {
            "id": self.id.value,
            "title": self._title,
            "description": self._description,
            "severity": self._severity.value,
            "status": self._status.value.value,
            "file_path": self._file_path,
            "test_case_id": self._test_case_id,
            "error_snippet": self._error_snippet,
            "assignee": self._assignee,
            "tags": list(self._tags),
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "deleted": 1 if self._deleted else 0,
        }

    @staticmethod
    def from_dict(data: dict) -> "Defect":
        """从持久化字典重建聚合。"""
        tags = data.get("tags") or []
        if isinstance(tags, str):
            try:
                tags = json.loads(tags or "[]")
            except Exception:
                tags = []
        deleted = bool(data.get("deleted"))
        if not deleted:
            # 兼容 status 列值；软删除记录 status 可能保留原状态
            status = data.get("status") or DefectStatusEnum.OPEN.value
        else:
            status = data.get("status") or DefectStatusEnum.OPEN.value
        return Defect(
            defect_id=str(data.get("id") or data.get("defect_id") or ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            severity=data.get("severity") or SeverityEnum.MAJOR.value,
            status=status,
            file_path=data.get("file_path", ""),
            test_case_id=data.get("test_case_id", ""),
            error_snippet=data.get("error_snippet", ""),
            assignee=data.get("assignee", ""),
            tags=tags,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            deleted=deleted,
        )
