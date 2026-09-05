"""
邀请注册 (/invite) 与无项目页 (/no-project) 全流程集成测试。

覆盖前端真实调用链路：
  - /invite  邀请注册页：管理员发邀请 -> 新用户(免登录)校验邀请 -> 注册 -> 登录
  - /no-project 无项目页：项目下拉列表 + 切换项目
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, username: str, password: str):
    r = client.post("/login", json={
        "username": username, "password": password, "authenticate": "LOCAL",
    })
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    return {
        "X-Auth-Token": d["sessionId"],
        "CSRF-Token": d["csrfToken"],
    }, d


# ═══════════════════════════════════════════════════════════
# /invite 邀请注册页
# ═══════════════════════════════════════════════════════════
class TestInvitePage:
    """/invite 邀请注册页全流程。"""

    def test_system_invite_create(self, client):
        """管理员通过 /system/user/invite 创建邀请，返回 inviteId 与链接。"""
        h, _ = _login(client, "admin", "admin123")
        r = client.post("/system/user/invite", json={
            "inviteEmails": ["invite_a@example.com"],
            "userRoleIds": ["member"],
        }, headers=h)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["inviteId"]
        assert "inviteId=" in data["invitationUrl"]

    def test_check_invite_public_no_auth(self, client):
        """新用户（未登录）校验邀请链接有效性，不应 401。"""
        h, _ = _login(client, "admin", "admin123")
        r = client.post("/system/user/invite", json={
            "inviteEmails": ["invite_b@example.com"], "userRoleIds": ["member"],
        }, headers=h)
        inv_id = r.json()["data"]["inviteId"]
        # 未携带任何鉴权头
        resp = client.get(f"/system/user/check-invite/{inv_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["invited"] is True

    def test_check_invite_invalid_returns_400(self, client):
        """无效邀请链接返回 400（前端据此展示“已过期”）。"""
        resp = client.get("/system/user/check-invite/not-exist-invite-id")
        assert resp.status_code == 400
        assert resp.json()["code"] == 400

    def test_register_by_invite_creates_user_and_login(self, client):
        """新用户免登录注册后，可用注册的用户名密码登录。"""
        h, _ = _login(client, "admin", "admin123")
        r = client.post("/system/user/invite", json={
            "inviteEmails": ["invite_c@example.com"], "userRoleIds": ["member"],
        }, headers=h)
        inv_id = r.json()["data"]["inviteId"]

        # 注册（免登录，密码直接传明文，后端 rsa_decrypt 解密失败会原样返回）
        reg = client.post("/system/user/register-by-invite", json={
            "inviteId": inv_id, "name": "invite_user_c",
            "password": "invitepass123", "phone": "",
        })
        assert reg.status_code == 200, reg.text
        assert reg.json()["data"]["success"] is True

        # 登录验证注册真实生效
        h2, d2 = _login(client, "invite_user_c", "invitepass123")
        assert d2["username"] == "invite_user_c"

    def test_invite_single_use(self, client):
        """邀请被使用后再次校验返回 400（一次性邀请）。"""
        h, _ = _login(client, "admin", "admin123")
        r = client.post("/system/user/invite", json={
            "inviteEmails": ["invite_d@example.com"], "userRoleIds": ["member"],
        }, headers=h)
        inv_id = r.json()["data"]["inviteId"]
        reg = client.post("/system/user/register-by-invite", json={
            "inviteId": inv_id, "name": "invite_user_d",
            "password": "invitepass123", "phone": "",
        })
        assert reg.status_code == 200, reg.text
        resp = client.get(f"/system/user/check-invite/{inv_id}")
        assert resp.status_code == 400

    def test_duplicate_username_rejected(self, client):
        """重复用户名注册被拒绝。"""
        h, _ = _login(client, "admin", "admin123")
        r = client.post("/system/user/invite", json={
            "inviteEmails": ["invite_e@example.com"], "userRoleIds": ["member"],
        }, headers=h)
        inv_id = r.json()["data"]["inviteId"]
        client.post("/system/user/register-by-invite", json={
            "inviteId": inv_id, "name": "admin", "password": "x12345678", "phone": "",
        })
        resp = client.post("/system/user/register-by-invite", json={
            "inviteId": inv_id, "name": "admin", "password": "x12345678", "phone": "",
        })
        # 用户名已存在应报错
        assert resp.json()["code"] == 400

    def test_org_invite_creates_record(self, client):
        """组织邀请也生成可用的邀请链接。"""
        h, _ = _login(client, "admin", "admin123")
        r = client.post("/organization/user/invite", json={
            "inviteEmails": ["invite_f@example.com"],
            "userRoleIds": ["member"],
            "organizationId": "default-org",
        }, headers=h)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["inviteId"]
        assert data["organizationId"] == "default-org"
        assert "inviteId=" in data["invitationUrl"]


# ═══════════════════════════════════════════════════════════
# /no-project 无项目页
# ═══════════════════════════════════════════════════════════
class TestNoProjectPage:
    """/no-project 页面前端调用：项目下拉 + 切换项目。"""

    def test_project_list_options_by_org(self, client):
        """getProjectList(orgId) -> GET /project/list/options/{orgId} 返回真实项目。"""
        h, _ = _login(client, "admin", "admin123")
        r = client.get("/project/list/options/default-org", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert isinstance(data, list)
        if data:
            item = data[0]
            assert item["id"]
            assert item["name"]
            assert "organizationId" in item

    def test_switch_project(self, client):
        """switchProject({projectId,userId}) 落库并返回组织。"""
        h, d = _login(client, "admin", "admin123")
        projects = client.get("/project/list/options/default-org", headers=h).json()["data"]
        if not projects:
            pytest.skip("default-org 下无项目")
        pid = projects[0]["id"]
        r = client.post("/project/switch", json={
            "projectId": pid, "userId": d["id"],
        }, headers=h)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["projectId"] == pid
        assert data["organizationId"] == "default-org"
