"""项目版本聚合根 ProjectVersion。"""
from __future__ import annotations

import time
from typing import Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.time_utils import time_from_row
from app.domain.project_version.domain.events import (
    ProjectVersionCreated,
    ProjectVersionStatusChanged,
    ProjectVersionUpdated,
)


class ProjectVersion(AggregateRoot):
    """项目版本聚合根。"""

    def __init__(
        self,
        *,
        version_id: str,
        project_id: str = "",
        name: str = "",
        description: str = "",
        status: bool = False,
        latest: bool = False,
        publish_time: Optional[float] = None,
        create_user: str = "admin",
        create_time: Optional[float] = None,
        update_time: Optional[float] = None,
        _created: bool = False,
    ):
        if not version_id:
            raise DomainValidationError("版本 ID 不能为空")
        if not (name or "").strip():
            raise DomainValidationError("版本名称不能为空")
        self.id = Identifier.of(version_id)
        self._project_id = project_id or ""
        self._name = (name or "").strip()
        self._description = description or ""
        self._status = bool(status)
        self._latest = bool(latest)
        self._publish_time = publish_time
        self._create_user = create_user or "admin"
        now = time.time()
        self._create_time = create_time if create_time is not None else now
        self._update_time = update_time if update_time is not None else now
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(ProjectVersionCreated(self.id.value, self._name, self._project_id))

    @property
    def project_id(self) -> str:
        return self._project_id
    @property
    def name(self) -> str:
        return self._name
    @property
    def description(self) -> str:
        return self._description
    @property
    def status(self) -> bool:
        return self._status
    @property
    def latest(self) -> bool:
        return self._latest
    @property
    def publish_time(self) -> Optional[float]:
        return self._publish_time

    @property
    def create_user(self) -> str:
        return self._create_user

    @property
    def update_time(self) -> Optional[float]:
        return self._update_time

    def update_info(self, *, name: Optional[str] = None,
                    description: Optional[str] = None,
                    status: Optional[bool] = None,
                    latest: Optional[bool] = None,
                    publish_time: Optional[float] = None) -> None:
        if name is not None:
            if not (name or "").strip():
                raise DomainValidationError("版本名称不能为空")
            self._name = (name or "").strip()
        if description is not None:
            self._description = description
        if status is not None:
            self._status = bool(status)
            if self._status:
                self.record_event(ProjectVersionStatusChanged(self.id.value, True))
        if latest is not None:
            self._latest = bool(latest)
        if publish_time is not None:
            self._publish_time = publish_time
        self._update_time = time.time()
        self.record_event(ProjectVersionUpdated(self.id.value))

    def set_latest(self) -> None:
        """设为最新版本。"""
        self._latest = True
        self._update_time = time.time()

    def clear_latest(self) -> None:
        """取消最新标记。"""
        self._latest = False
        self._update_time = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "name": self._name,
            "description": self._description,
            "status": self._status,
            "latest": self._latest,
            "publishTime": int(self._publish_time) if self._publish_time else 0,
            "createTime": int(self._create_time * 1000) if self._create_time else 0,
            "createUser": self._create_user,
            "projectId": self._project_id,
        }

    @staticmethod
    def from_dict(data: dict) -> "ProjectVersion":
        return ProjectVersion(
            version_id=str(data.get("id") or data.get("version_id") or ""),
            project_id=data.get("projectId", "") or data.get("project_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            status=bool(data.get("status", False)),
            latest=bool(data.get("latest", False)),
            publish_time=data.get("publish_time") or data.get("publishTime"),
            create_user=data.get("create_user", "admin"),
            create_time=time_from_row(data, "create_time", "createTime"),
            update_time=time_from_row(data, "update_time", "updateTime"),
        )
