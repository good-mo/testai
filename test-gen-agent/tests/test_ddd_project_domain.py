"""DDD 项目管理试点域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：状态机（active/archived）、软删除/恢复、成员管理。
  2. 应用服务全链路（对接真实 ProjectRepo 存储）。
"""
import uuid

import pytest

from app.domain.common.exceptions import AggregateNotFound, DomainValidationError
from app.domain.project.application.dto import (
    AddMemberCommand,
    ChangeStatusCommand,
    CreateProjectCommand,
    ListQuery,
    RemoveMemberCommand,
    UpdateProjectCommand,
)
from app.domain.project.application.project_app_service import ProjectAppService
from app.domain.project.domain.value_objects.language import ProjectLanguage, ProjectLanguageEnum
from app.domain.project.domain.value_objects.member_role import MemberRole
from app.domain.project.domain.value_objects.project_status import ProjectStatus, ProjectStatusEnum

TAG = "dddprj"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _project(**kw):
    from app.domain.project.domain.entities.project import Project
    kw.setdefault("project_id", _mk())
    kw.setdefault("name", "项目")
    return Project(**kw)


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需数据库）
# ═══════════════════════════════════════════════════════════
class TestValueObjects:
    def test_status_normalize(self):
        assert str(ProjectStatus("Active")) == "active"
        assert str(ProjectStatus("ARCHIVED")) == "archived"
        assert str(ProjectStatus("")) == "active"
        # DB 软删除存储值 'deleted' -> 内部 DELETED
        assert ProjectStatus("deleted").is_deleted

    def test_status_illegal_rejected(self):
        with pytest.raises(DomainValidationError):
            ProjectStatus("bogus")

    def test_language_default(self):
        assert str(ProjectLanguage("")) == "python"
        assert str(ProjectLanguage(ProjectLanguageEnum.GO.value)) == "go"
        # 未知语言收敛为 other
        assert str(ProjectLanguage("cobol")) == "other"

    def test_member_role_normalize(self):
        assert str(MemberRole("ADMIN")) == "admin"
        assert str(MemberRole("")) == "member"
        with pytest.raises(DomainValidationError):
            MemberRole("owner")

    def test_name_required(self):
        with pytest.raises(DomainValidationError):
            _project(name="")


class TestAggregate:
    def test_rename(self):
        p = _project()
        p.rename("新项目", "u")
        assert p.name == "新项目"

    def test_rename_empty_rejected(self):
        p = _project()
        with pytest.raises(DomainValidationError):
            p.rename("", "u")

    def test_archive_activate(self):
        p = _project()
        assert str(p.status) == "active"
        p.archive("u")
        assert str(p.status) == "archived"
        p.activate("u")
        assert str(p.status) == "active"

    def test_illegal_transition_rejected(self):
        p = _project(status="active")
        with pytest.raises(DomainValidationError):
            p.change_status(ProjectStatusEnum.DELETED.value, "u")  # 不可直接软删
        # archived 状态回到 active 是合法的
        p2 = _project(status="archived")
        p2.change_status("active", "u")
        assert str(p2.status) == "active"

    def test_soft_delete_restore(self):
        p = _project()
        p.delete("u")
        assert p.deleted
        with pytest.raises(DomainValidationError):
            p.delete("u")  # 重复删除
        p.restore("u")
        assert not p.deleted
        with pytest.raises(DomainValidationError):
            p.restore("u")  # 不在回收站

    def test_recycled_project_forbids_mutation(self):
        p = _project()
        p.delete("u")
        with pytest.raises(DomainValidationError):
            p.rename("改名", "u")  # 回收站不可改名

    def test_member_add_remove(self):
        p = _project()
        p.add_member(user_id="u1", username="alice", role="admin")
        assert len(p.members) == 1
        assert p.members[0].role == "admin"
        # 重复加入幂等去重
        p.add_member(user_id="u1", username="alice", role="member")
        assert len(p.members) == 1
        removed = p.remove_member(user_id="u1")
        assert removed and len(p.members) == 0

    def test_member_without_identity_rejected(self):
        p = _project()
        with pytest.raises(DomainValidationError):
            p.add_member(user_id="", username="")

    def test_events_collected(self):
        p = _project()
        p.rename("abc", "u")
        p.archive("u")
        p.add_member(user_id="u9", username="x", role="member")
        names = [type(e).__name__ for e in p.pull_domain_events()]
        assert "ProjectRenamed" in names
        assert "ProjectArchived" in names
        assert "ProjectMemberAdded" in names


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（真实存储）
# ═══════════════════════════════════════════════════════════
@pytest.fixture
def fresh_project_id():
    svc = ProjectAppService()
    proj = svc.create(CreateProjectCommand(
        name=_mk(), language="python", operator="admin",
    ))
    pid = proj["id"]
    yield pid
    # 清理（软删除后物理删除）
    from app.repositories.project_repo import ProjectRepo
    svc.soft_delete(pid, "admin")
    ProjectRepo.hard_delete(pid)


def test_create_and_get(fresh_project_id):
    svc = ProjectAppService()
    assert svc.get(fresh_project_id) is not None
    assert svc.get(fresh_project_id)["deleted"] is False


def test_update_rename(fresh_project_id):
    svc = ProjectAppService()
    r = svc.update(UpdateProjectCommand(
        project_id=fresh_project_id, name=_mk(), language="go", operator="admin"))
    assert r is not None
    assert r["language"] == "go"


def test_lifecycle_roundtrip(fresh_project_id):
    svc = ProjectAppService()
    svc.archive(fresh_project_id)
    assert svc.get(fresh_project_id)["status"] == "archived"
    svc.activate(fresh_project_id)
    assert svc.get(fresh_project_id)["status"] == "active"


def test_change_status(fresh_project_id):
    svc = ProjectAppService()
    r = svc.change_status(ChangeStatusCommand(
        project_id=fresh_project_id, target_status="archived", operator="admin"))
    assert r["status"] == "archived"


def test_delete_restore_roundtrip(fresh_project_id):
    svc = ProjectAppService()
    assert svc.soft_delete(fresh_project_id, "admin")
    # 默认不可见
    assert svc.get(fresh_project_id) is None
    # include_deleted 可见且标记 deleted
    g = svc.get(fresh_project_id, include_deleted=True)
    assert g is not None and g["deleted"] is True
    assert svc.restore(fresh_project_id, "admin")
    assert svc.get(fresh_project_id)["status"] == "active"


def test_member_flow(fresh_project_id):
    svc = ProjectAppService()
    svc.add_member(AddMemberCommand(
        project_id=fresh_project_id, user_id="u100", username="bob",
        role="admin", operator="admin"))
    members = svc.list_members(fresh_project_id)
    assert len(members) == 1
    assert members[0]["role"] == "admin"
    assert svc.remove_member(RemoveMemberCommand(
        project_id=fresh_project_id, user_id="u100", operator="admin"))
    assert len(svc.list_members(fresh_project_id)) == 0


def test_list_and_get_or_raise(fresh_project_id):
    svc = ProjectAppService()
    result = svc.list(ListQuery(search=TAG, limit=50))
    assert "list" in result and "total" in result
    assert result["total"] >= 1
    assert svc.get_or_raise(fresh_project_id) is not None
    with pytest.raises(AggregateNotFound):
        svc.get_or_raise("__no_such_project__")
