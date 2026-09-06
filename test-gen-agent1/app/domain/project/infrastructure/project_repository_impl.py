"""Project 聚合仓储实现（Adapter 防腐层）。

将"面向聚合的仓储接口"翻译为既有 ProjectRepo（四层 Repository）的命令，
实现防腐层（Anti-Corruption Layer），复用已验证的存储逻辑，同时让领域层
获得聚合级读写语义；后续如需换存储仅替换本文件。
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from app.domain.common.entities import Identifier
from app.domain.project.domain.entities.project import Project
from app.domain.project.domain.value_objects.member import ProjectMember
from app.repositories.project_repo import ProjectRepo


class ProjectRepoAdapter:
    """将既有 ProjectRepo 封装为面向聚合的仓储。"""

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    # ── 读：聚合重建 ────────────────────────────────
    def _attach_members(self, project: Project) -> Project:
        """加载项目成员到聚合，保持聚合级内聚读取语义。"""
        try:
            for mr in ProjectRepo.list_members(project.id.value):
                project._members.append(ProjectMember.from_dict(mr))
        except Exception:
            # 读取成员失败不阻断聚合重建（保持对既有主表读的兼容）
            pass
        return project

    def find_by_id(self, project_id: str, include_deleted: bool = False) -> Optional[Project]:
        row = ProjectRepo.get(project_id, include_deleted=include_deleted)
        if not row:
            return None
        project = Project.from_dict(dict(row))
        return self._attach_members(project)

    def list_projects(self, *, search: str = "", status: str = "", limit: int = 100,
                      include_deleted: bool = False) -> Tuple[List[Project], int]:
        rows = ProjectRepo.list(search=search, status=status, limit=limit,
                                include_deleted=include_deleted)
        return [Project.from_dict(dict(r)) for r in rows], len(rows)

    # ── 写：以聚合为粒度落库 ────────────────────────
    def save(self, project: Project) -> Project:
        """新增项目：落库并把仓储生成的真实主键回填到聚合。

        底层 ProjectRepo.create 自行生成 uuid，故在此回填聚合 id，
        保证后续 update / 事件订阅都以真实主键为准。
        """
        d = project.snapshot()
        row = ProjectRepo.create(
            name=d["name"], description=d["description"], repo_url=d["repo_url"],
            language=d["language"], path=d["path"],
        )
        if not row:
            raise RuntimeError(f"项目创建失败: {project.name}")
        project.id = Identifier.of(row["id"])
        if project._organization_id:
            ProjectRepo.update(project.id.value, {"organization_id": project._organization_id})
        return project

    def update(self, project: Project) -> Optional[Project]:
        d = project.snapshot()
        persist = {k: v for k, v in d.items() if k != "organization_id"}
        result = ProjectRepo.update(project.id.value, persist)
        if result is None:
            return None
        if project._organization_id:
            ProjectRepo.update(project.id.value, {"organization_id": project._organization_id})
        return self.find_by_id(project.id.value)

    def soft_delete(self, project_id: str) -> bool:
        return ProjectRepo.delete(project_id)

    def restore(self, project_id: str) -> bool:
        return ProjectRepo.recover(project_id)

    # ── 成员关联 ────────────────────────────────────
    def add_member(self, project_id: str, member: dict) -> Optional[dict]:
        return ProjectRepo.add_member(
            project_id=project_id,
            user_id=member.get("user_id", ""),
            username=member.get("username", ""),
            name=member.get("name", ""),
            email=member.get("email", ""),
            role=member.get("role", "member"),
            user_group=member.get("user_group", ""),
        )

    def get_member(self, member_id: str) -> Optional[dict]:
        return ProjectRepo.get_member(member_id)

    def list_members(self, project_id: str, keyword: str = "") -> List[dict]:
        return ProjectRepo.list_members(project_id, keyword=keyword)

    def update_member(self, member_id: str, data: dict) -> Optional[dict]:
        return ProjectRepo.update_member(member_id, data)

    def remove_member(self, project_id: str, user_id: str) -> bool:
        return ProjectRepo.remove_member(project_id, user_id)

    def batch_remove_members(self, project_id: str, user_ids: list) -> int:
        return ProjectRepo.batch_remove_members(project_id, user_ids)

    # ── 自定义函数（custom_funcs）旁路覆盖 ────────────────
    def list_custom_funcs(self, project_id: str = "", keyword: str = "") -> List[dict]:
        """转发既有 ProjectRepo 自定义函数列表。"""
        return ProjectRepo.list_custom_funcs(project_id=project_id, keyword=keyword)

    def get_custom_func_row(self, func_id: str) -> Optional[dict]:
        return ProjectRepo.get_custom_func_row(func_id)

    def create_custom_func(self, func_id: str, name: str = "", script: str = "",
                           func_type: str = "HTTP", description: str = "",
                           status: str = "DRAFT", project_id: str = "",
                           tags: Optional[list] = None, params: str = "[]",
                           result: str = "", create_user: str = "admin") -> bool:
        return ProjectRepo.create_custom_func(
            func_id=func_id, name=name, script=script, func_type=func_type,
            description=description, status=status, project_id=project_id,
            tags=tags, params=params, result=result, create_user=create_user,
        )

    def update_custom_func(self, func_id: str, updates: dict,
                           update_user: str = "admin") -> bool:
        return ProjectRepo.update_custom_func(func_id, updates, update_user=update_user)

    def update_custom_func_status(self, func_id: str, status: str) -> bool:
        return ProjectRepo.update_custom_func_status(func_id, status)

    def delete_custom_func(self, func_id: str) -> bool:
        return ProjectRepo.delete_custom_func(func_id)

    def list_custom_func_status(self, project_id: str = "") -> List[dict]:
        return ProjectRepo.list_custom_func_status(project_id=project_id)

    # ── 自定义字段（project_custom_fields）旁路覆盖 ────────
    def list_custom_fields(self, scope_id: str, scene: str = "") -> List[dict]:
        return ProjectRepo.list_custom_fields(scope_id, scene=scene)

    def get_custom_field(self, field_id: str) -> Optional[dict]:
        return ProjectRepo.get_custom_field(field_id)

    def upsert_custom_field(self, field_id: str, body: dict) -> Optional[dict]:
        return ProjectRepo.upsert_custom_field(field_id, body)

    def delete_custom_field(self, field_id: str) -> bool:
        return ProjectRepo.delete_custom_field(field_id)
