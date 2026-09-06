"""
test_tenant_info.py — 完整的租户测试信息

覆盖租户（组织）管理的完整流程：
  1. 租户（组织）CRUD：创建、查询、更新、启用/禁用、删除/恢复
  2. 组织成员管理：添加、列出、移除、更新角色
  3. 组织-项目管理：创建、绑定、列出、更新、删除
  4. 完整租户数据初始化：组织 + 用户 + 项目联动
  5. 前端契约：系统组织管理、组织项目管理接口

运行：
  pytest tests/test_tenant_info.py -v
"""

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """测试客户端，自动登录。"""
    from app.main import app
    with TestClient(app) as c:
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, f"登录失败: {r.text}"
        session = r.json()["data"]
        c.headers.update({
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        })
        yield c


@pytest.fixture(scope="module")
def org_svc():
    """组织业务服务（取代已删除的旧 app.organizations.store 兼容层）。"""
    from app.services.organization_service import organization_service
    return organization_service


# ════════════════════════════════════════════════════════════
# 第 1 层：租户（组织）CRUD
# ════════════════════════════════════════════════════════════

class TestTenantOrgCRUD:
    """租户（组织）完整 CRUD 流程。"""

    def test_create_organization(self, client, org_svc):
        """创建组织。"""
        name = f"测试租户-{uuid.uuid4().hex[:6]}"
        org = org_svc.create(name=name, description="完整租户测试组织")
        assert org is not None
        assert org["name"] == name
        assert org["status"] == "active"
        assert org["memberCount"] == 0
        return org

    def test_get_organization(self, client, org_svc):
        """获取组织详情。"""
        org = self.test_create_organization(client, org_svc)
        fetched = org_svc.get(org["id"])
        assert fetched is not None
        assert fetched["id"] == org["id"]
        assert fetched["name"] == org["name"]

    def test_list_organizations(self, client, org_svc):
        """列出所有组织。"""
        orgs = org_svc.list()
        assert len(orgs) >= 1
        # 默认组织应存在
        names = [o["name"] for o in orgs]
        assert any("默认组织" in n for n in names)

    def test_update_organization(self, client, org_svc):
        """更新组织信息。"""
        org = self.test_create_organization(client, org_svc)
        new_name = f"更新后-{org['name']}"
        updated = org_svc.update(org["id"], name=new_name, description="已更新描述")
        assert updated is not None
        assert updated["name"] == new_name
        assert updated["description"] == "已更新描述"

    def test_rename_organization(self, client, org_svc):
        """重命名组织。"""
        org = self.test_create_organization(client, org_svc)
        new_name = f"重命名-{org['name']}"
        renamed = org_svc.rename(org["id"], new_name)
        assert renamed is not None
        assert renamed["name"] == new_name

    def test_enable_disable_organization(self, client, org_svc):
        """启用/禁用组织。"""
        org = self.test_create_organization(client, org_svc)
        # 禁用
        assert org_svc.disable(org["id"])
        fetched = org_svc.get(org["id"])
        assert fetched["status"] == "disabled"
        # 启用
        assert org_svc.enable(org["id"])
        fetched = org_svc.get(org["id"])
        assert fetched["status"] == "active"

    def test_delete_recover_organization(self, client, org_svc):
        """删除/恢复组织。"""
        org = self.test_create_organization(client, org_svc)
        # 软删除
        assert org_svc.delete(org["id"])
        fetched = org_svc.get(org["id"])
        assert fetched is None  # 软删除后不可查询
        # 恢复
        assert org_svc.recover(org["id"])
        fetched = org_svc.get(org["id"])
        assert fetched is not None


# ════════════════════════════════════════════════════════════
# 第 2 层：组织成员管理
# ════════════════════════════════════════════════════════════

class TestTenantMembers:
    """组织成员管理。"""

    def test_add_org_member(self, client, org_svc):
        """添加组织成员。"""
        from app.auth.store import auth_store
        user = auth_store.get_user_by_username("admin")
        assert user is not None

        member = org_svc.add_member("default-org", user["id"], role="admin")
        assert member is not None
        assert member["organization_id"] == "default-org"
        assert member["user_id"] == user["id"]
        assert member["role"] == "admin"

    def test_list_org_members(self, client, org_svc):
        """列出组织成员。"""
        members = org_svc.list_members("default-org")
        assert len(members) >= 1

    def test_count_org_members(self, client, org_svc):
        """统计组织成员数量。"""
        count = org_svc.count_members("default-org")
        assert count >= 1

    def test_update_org_member_role(self, client, org_svc):
        """更新组织成员角色。"""
        from app.auth.store import auth_store
        user = auth_store.get_user_by_username("admin")
        member = org_svc.update_member("default-org", user["id"], role="member")
        assert member is not None
        assert member["role"] == "member"

    def test_remove_org_member(self, client, org_svc):
        """移除组织成员。"""
        from app.auth.store import auth_store
        # 先创建测试用户
        username = f"tenant_test_{uuid.uuid4().hex[:6]}"
        user = auth_store.create_user(username=username, password="test123", name="测试用户")
        assert user is not None

        # 添加成员
        member = org_svc.add_member("default-org", user["id"], role="member")
        assert member is not None

        # 移除成员
        assert org_svc.remove_member("default-org", user["id"])
        members = org_svc.list_members("default-org")
        assert all(m["user_id"] != user["id"] for m in members)


# ════════════════════════════════════════════════════════════
# 第 3 层：组织-项目管理
# ════════════════════════════════════════════════════════════

class TestTenantProject:
    """组织-项目管理。"""

    def test_list_org_projects(self, client, org_svc):
        """列出组织下的项目。"""
        projects = org_svc.list_projects("default-org")
        assert isinstance(projects, list)

    def test_bind_project_to_org(self, client, org_svc):
        """将项目绑定到组织。"""
        from app.services.project_service import project_service
        proj = project_service.create({"name": f"绑定项目-{uuid.uuid4().hex[:6]}"})
        assert org_svc.bind_project(proj["id"], "default-org")
        projects = org_svc.list_projects("default-org")
        assert any(p["id"] == proj["id"] for p in projects)


# ════════════════════════════════════════════════════════════
# 第 4 层：完整租户数据初始化
# ════════════════════════════════════════════════════════════

class TestTenantDataSeed:
    """完整租户数据初始化。"""

    def test_seed_tenant_data(self, client, org_svc):
        """初始化完整租户测试数据。"""
        result = org_svc.seed_tenant_data()
        assert "organizations" in result
        assert "members" in result
        assert "projects" in result
        assert len(result["organizations"]) >= 1

    def test_get_tenant_summary(self, client, org_svc):
        """获取租户数据摘要。"""
        summary = org_svc.get_tenant_summary()
        assert "orgCount" in summary
        assert "memberCount" in summary
        assert "projectCount" in summary
        assert "organizations" in summary


# ════════════════════════════════════════════════════════════
# 第 5 层：前端 API 契约
# ════════════════════════════════════════════════════════════

class TestTenantApiContract:
    """前端组织管理 API 契约。"""

    def test_system_org_option_all(self, client):
        """系统组织下拉选项。"""
        r = client.get("/system/organization/option/all")
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list)
        # 默认组织应该存在
        assert any(o.get("name") == "默认组织" for o in data)

    def test_system_org_list(self, client):
        """系统组织列表（POST）。"""
        r = client.post("/system/organization/list", json={"current": 1, "pageSize": 10})
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, dict)
        assert "list" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_system_org_total(self, client):
        """系统组织总数。"""
        r = client.get("/system/organization/total")
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, dict)
        assert "total" in data

    def test_org_project_add(self, client):
        """组织添加项目。"""
        r = client.post("/organization/project/add", json={
            "name": f"API项目-{uuid.uuid4().hex[:6]}",
            "description": "组织添加项目测试",
            "organizationId": "default-org",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data is not None
        assert "id" in data

    def test_org_project_page(self, client):
        """组织项目分页。"""
        r = client.post("/organization/project/page", json={
            "current": 1, "pageSize": 10,
            "organizationId": "default-org",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, dict)
        assert "list" in data
        assert "total" in data

    def test_org_member_list(self, client):
        """组织成员列表。"""
        r = client.get("/organization/member/list", params={"org_id": "default-org"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
