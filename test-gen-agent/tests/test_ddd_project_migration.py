"""项目域 DDD A→B→C 迁移回归测试。

覆盖目标：
  1. DTO 契约桥（web_contract）—— DDD 聚合导出 dict 归一为既有仓库行口径，
     保证阶段 B router 接入后对外 schema 零变化。
  2. 阶段 B router 接入回归 —— `routers/projects.py` 改调 `ProjectAppService`
     后，核心生命周期接口与既有契约逐字段一致（列表 / 创建 / 详情 / 更新 /
     删除 / 统计）。
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.domain.project.application.project_app_service import ProjectAppService
from app.domain.project.application.web_contract import to_row, to_row_page

TAG = "dddprjmig"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def client():
    """已登录的测试客户端。"""
    from app.main import app
    with TestClient(app) as c:
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        if r.status_code == 200:
            session = r.json()["data"]
            c.headers.update({
                "X-AUTH-TOKEN": session["sessionId"],
                "CSRF-TOKEN": session["csrfToken"],
            })
        yield c


def _data(resp):
    body = resp.json()
    return body.get("data") if isinstance(body, dict) else body


def _cleanup(pid):
    """软删除后物理删除，避免污染其他用例。"""
    from app.repositories.project_repo import ProjectRepo
    svc = ProjectAppService()
    try:
        svc.soft_delete(pid, "admin")
    except Exception:
        pass
    ProjectRepo.hard_delete(pid)


# ═══════════════════════════════════════════════════════════
# 一、DTO 契约桥单测（纯函数，无 DB）
# ═══════════════════════════════════════════════════════════
class TestWebContractBridge:
    def test_to_row_normalizes_ddd_output(self):
        """DDD 聚合导出 -> 既有仓库行口径：不内嵌 members、deleted 归一为 int。"""
        ddd = {
            "id": "p1", "name": "项目A", "description": "desc",
            "repo_url": "git://x", "language": "python", "path": "/x",
            "status": "active", "organization_id": "org1", "deleted": False,
            "created_at": 100.0, "updated_at": 200.0,
            "members": [{"user_id": "u1", "role": "member"}],
        }
        row = to_row(ddd)
        assert row["id"] == "p1"
        assert row["deleted"] == 0
        assert "members" not in row
        # 聚合不承载 deleted_at，兼容层给 None
        assert row["deleted_at"] is None
        assert row["created_at"] == 100.0

    def test_to_row_deleted_bool_to_int(self):
        assert to_row({"deleted": True})["deleted"] == 1
        assert to_row({"deleted": 0})["deleted"] == 0

    def test_to_row_missing_fields_defaulted(self):
        row = to_row({"id": "x", "name": "n"})
        assert row["language"] == "python"
        assert row["status"] == "active"
        assert row["deleted"] == 0

    def test_to_row_page_wraps_list(self):
        page = {"list": [{"id": "p1", "name": "n"}], "total": 1}
        assert set(to_row_page(page).keys()) == {"projects"}
        assert to_row_page(page)["projects"][0]["id"] == "p1"


# ═══════════════════════════════════════════════════════════
# 二、阶段 B：router 接入回归（对外契约零变化）
# ═══════════════════════════════════════════════════════════
class TestRouterPhaseBMigration:
    def _create(self, client):
        resp = client.post("/api/projects", json={
            "name": _mk(), "description": "迁移回归", "language": "python",
        })
        assert resp.status_code == 200
        data = _data(resp)
        self._pid = data["id"]
        return data

    def test_create_and_get_contract(self, client):
        p = self._create(client)
        for field in ("id", "name", "language", "status", "description"):
            assert field in p, f"创建返回缺 {field}"
        assert p["language"] == "python"
        assert p["status"] == "active"
        # 详情契约
        resp = client.get(f"/api/projects/{p['id']}")
        assert resp.status_code == 200
        detail = _data(resp)
        assert detail["id"] == p["id"]
        assert detail["name"] == p["name"]
        _cleanup(p["id"])

    def test_list_contract_has_projects(self, client):
        self._create(client)
        resp = client.get("/api/projects", params={"search": TAG})
        assert resp.status_code == 200
        data = _data(resp)
        assert "projects" in data
        _cleanup(self._pid)

    def test_update_contract(self, client):
        p = self._create(client)
        resp = client.put(f"/api/projects/{p['id']}", json={
            "description": "已更新", "language": "go",
        })
        assert resp.status_code == 200
        updated = _data(resp)
        assert updated["description"] == "已更新"
        assert updated["language"] == "go"
        _cleanup(p["id"])

    def test_delete_then_not_found(self, client):
        p = self._create(client)
        resp = client.delete(f"/api/projects/{p['id']}")
        assert resp.status_code == 200
        # 软删除后默认详情不可见（404）
        resp = client.get(f"/api/projects/{p['id']}")
        assert resp.status_code == 404
        from app.repositories.project_repo import ProjectRepo
        ProjectRepo.hard_delete(p["id"])

    def test_stats_endpoint_still_ok(self, client):
        p = self._create(client)
        resp = client.get(f"/api/projects/{p['id']}/stats")
        assert resp.status_code == 200
        assert _data(resp) is not None
        _cleanup(p["id"])


# ═══════════════════════════════════════════════════════════
# 三、阶段 C：project_service 薄门面委托 DDD（核心生命周期收敛）
# ═══════════════════════════════════════════════════════════
class TestServiceFacadeStageC:
    """project_service 核心生命周期收敛为 DDD 薄门面的回归测试。

    旁路/compat router 复用 `project_service` 走既有 4 层入口；阶段 C 使其
    create/get/list/update/delete 委托 `project_app_service`，输出经 DTO 契约桥
    归一为既有仓库行口径，对外 schema 与迁移前零变化，且 DDD 规则（状态机、
    软删除）在门面路径上生效。
    """
    def _mk(self) -> str:
        return f"{TAG}_facade_{uuid.uuid4().hex[:6]}"

    def test_create_get_route_ddd_and_shape(self, client):
        from app.repositories.project_repo import ProjectRepo
        from app.services.project_service import project_service
        name = self._mk()
        p = project_service.create({"name": name, "description": "阶段C", "language": "go"})
        pid = p["id"]
        # 返回为既有仓库行口径（无内嵌 members，deleted 为 int）
        assert "members" not in p
        assert p["deleted"] == 0
        assert p["language"] == "go"
        assert p["status"] == "active"
        # DDD 规则：名称非空
        with pytest.raises(ValueError):
            project_service.create({"name": "", "description": "x"})
        # get
        g = project_service.get(pid)
        assert g["id"] == pid and g["name"] == name
        # list 命中
        lst = project_service.list(search=name)
        assert any(x["id"] == pid for x in lst)
        ProjectRepo.hard_delete(pid)

    def test_update_status_goes_through_domain_and_idempotent(self, client):
        from app.repositories.project_repo import ProjectRepo
        from app.services.project_service import project_service
        p = project_service.create({"name": self._mk(), "description": "d"})
        pid = p["id"]
        # active -> archived（合法迁移，经领域状态机）
        u = project_service.update(pid, {"status": "archived"})
        assert u["status"] == "archived"
        # 幂等：archived -> archived 不抛异常、状态保持
        u2 = project_service.update(pid, {"status": "archived"})
        assert u2["status"] == "archived"
        # 字段更新
        u3 = project_service.update(pid, {"name": "阶段C改名"})
        assert u3["name"] == "阶段C改名"
        ProjectRepo.hard_delete(pid)

    def test_delete_soft_delete_and_idempotent(self, client):
        from app.repositories.project_repo import ProjectRepo
        from app.services.project_service import project_service
        p = project_service.create({"name": self._mk(), "description": "d"})
        pid = p["id"]
        assert project_service.delete(pid) is True
        assert ProjectRepo._get_project_row(pid, include_deleted=True)["deleted"] == 1
        # 二次删除返回 False（幂等，兼容既有 delete 语义）
        assert project_service.delete(pid) is False
        ProjectRepo.hard_delete(pid)

    def test_legacy_admin_status_still_written_to_repo(self, client):
        """遗留 deleted/disabled 状态位仍走 Repo 原样落库（不经聚合状态机改写）。"""
        from app.repositories.project_repo import ProjectRepo
        from app.services.project_service import project_service
        p = project_service.create({"name": self._mk(), "description": "d"})
        pid = p["id"]
        project_service.update(pid, {"status": "disabled"})
        assert ProjectRepo.get(pid)["status"] == "disabled"
        project_service.update(pid, {"status": "deleted"})
        assert ProjectRepo.get(pid)["status"] == "deleted"
        ProjectRepo.delete(pid)
        ProjectRepo.hard_delete(pid)
