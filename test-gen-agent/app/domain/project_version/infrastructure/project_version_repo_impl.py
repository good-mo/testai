"""项目版本聚合仓储实现。"""
from __future__ import annotations

import uuid
from typing import List, Optional

from app.domain.project_version.domain.entities.project_version import ProjectVersion
from app.repositories.project_version_repo import project_version_repo


class ProjectVersionRepoAdapter:
    """将既有 project_version_repo 封装为面向 ProjectVersion 的仓储。"""

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def save(self, version: ProjectVersion) -> ProjectVersion:
        existing = self.get(version.id.value)
        updates = {
            "name": version.name,
            "description": version.description,
            "status": int(version.status),
            "latest": int(version.latest),
        }
        if version.publish_time is not None:
            updates["publish_time"] = version.publish_time
        if version.update_time is not None:
            updates["update_time"] = version.update_time
        if existing:
            project_version_repo.update_version(version.id.value, updates)
        else:
            # 新建以聚合根的 id 落库，保证返回 id == 落库 id（修复双 id 漂移缺陷）
            project_version_repo.add_version(
                version.project_id, version.name, version.description,
                status=version.status, latest=version.latest,
                publish_time=version.publish_time,
                create_user=version.create_user,
                version_id=version.id.value,
            )
        return version

    def get(self, version_id: str) -> Optional[ProjectVersion]:
        row = project_version_repo.get_version(version_id)
        return ProjectVersion.from_dict(row) if row else None

    def list_by_project(self, project_id: str, keyword: str = "") -> List[ProjectVersion]:
        rows = project_version_repo.list_versions(project_id, keyword=keyword)
        return [ProjectVersion.from_dict(r) for r in rows]

    def delete(self, version_id: str) -> bool:
        return project_version_repo.delete_version(version_id)

    def clear_project_latest(self, project_id: str, exclude_id: str = "") -> None:
        project_version_repo.clear_project_latest(project_id, exclude_id)

    def set_latest(self, version_id: str) -> None:
        project_version_repo.set_latest(version_id)

    def set_status(self, version_id: str, status: bool) -> None:
        project_version_repo.set_status(version_id, status)
