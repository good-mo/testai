"""项目版本应用服务。"""
from __future__ import annotations

from typing import Optional

from app.domain.project_version.application.dto import (
    CreateVersionCommand,
    DeleteVersionCommand,
    GetVersionCommand,
    ListVersionsCommand,
    UpdateVersionCommand,
)
from app.domain.project_version.domain.entities.project_version import ProjectVersion
from app.domain.project_version.domain.exceptions import ProjectVersionNotFound
from app.domain.project_version.infrastructure.project_version_repo_impl import (
    ProjectVersionRepoAdapter,
)


class ProjectVersionAppService:
    """项目版本用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or ProjectVersionRepoAdapter()

    def list(self, cmd: ListVersionsCommand) -> list:
        versions = self._repo.list_by_project(cmd.project_id, cmd.keyword)
        return [v.to_dict() for v in versions]

    def get(self, cmd: GetVersionCommand) -> Optional[dict]:
        v = self._repo.get(cmd.version_id)
        return v.to_dict() if v else None

    def create(self, cmd: CreateVersionCommand) -> dict:
        version = ProjectVersion(
            version_id=self._repo.next_id(),
            project_id=cmd.project_id,
            name=cmd.name,
            description=cmd.description,
            status=cmd.status,
            latest=cmd.latest,
            publish_time=cmd.publish_time,
            create_user=cmd.create_user,
            _created=True,
        )
        # 如设为 latest，先清除同项目其他 latest
        if cmd.latest:
            self._repo.clear_project_latest(cmd.project_id)
        saved = self._repo.save(version)
        return saved.to_dict()

    def update(self, cmd: UpdateVersionCommand) -> Optional[dict]:
        version = self._repo.get(cmd.version_id)
        if not version:
            raise ProjectVersionNotFound(f"项目版本 {cmd.version_id} 不存在")
        if cmd.latest:
            self._repo.clear_project_latest(version.project_id, exclude_id=cmd.version_id)
        version.update_info(
            name=cmd.name, description=cmd.description,
            status=cmd.status, latest=cmd.latest, publish_time=cmd.publish_time,
        )
        saved = self._repo.save(version)
        return saved.to_dict()

    def delete(self, cmd: DeleteVersionCommand) -> bool:
        return self._repo.delete(cmd.version_id)

    def options(self, project_id: str) -> list:
        versions = self._repo.list_by_project(project_id)
        return [
            {"id": v.id.value, "name": v.name,
             "latest": v.latest, "enable": v.status}
            for v in versions
        ]

    def set_latest(self, version_id: str) -> Optional[dict]:
        """将指定版本置为最新，同时清除同项目其他版本的 latest 标记。

        版本不存在时抛 ProjectVersionNotFound（由门面收敛为 None 以兼容旧语义）。
        """
        version = self._repo.get(version_id)
        if not version:
            raise ProjectVersionNotFound(f"项目版本 {version_id} 不存在")
        self._repo.clear_project_latest(version.project_id, exclude_id=version_id)
        self._repo.set_latest(version_id)
        updated = self._repo.get(version_id)
        return updated.to_dict() if updated else None

    def toggle_status(self, version_id: str) -> Optional[dict]:
        """切换版本状态（取反）；版本不存在时抛 ProjectVersionNotFound。"""
        version = self._repo.get(version_id)
        if not version:
            raise ProjectVersionNotFound(f"项目版本 {version_id} 不存在")
        new_status = not version.status
        self._repo.set_status(version_id, new_status)
        updated = self._repo.get(version_id)
        return updated.to_dict() if updated else None


project_version_app_service = ProjectVersionAppService()
