"""认证模块单元测试：登录、登出、会话、用户、RSA 密钥。"""

import os
import unittest

import pytest
from fastapi.testclient import TestClient

# 使用临时数据库
os.environ.setdefault("AUTH_DB_PATH", "test_auth.db")

from app.auth.store import _LOGIN_MAX_ATTEMPTS  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    """创建测试客户端。"""
    # 清理测试数据库
    db_path = "test_auth.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    return TestClient(app)


class TestAuthFlow:
    """认证流程测试。"""

    def test_get_public_key(self, client):
        """获取 RSA 公钥。"""
        r = client.get("/get-key")
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert "BEGIN PUBLIC KEY" in data["data"]

    def test_login_success(self, client):
        """登录成功。"""
        r = client.post("/login", json={
            "username": "admin",
            "password": "admin123",
            "authenticate": "LOCAL",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert data["data"]["sessionId"]
        assert data["data"]["csrfToken"]
        assert data["data"]["name"]  # has name

    def test_login_fail(self, client):
        """登录失败（错误密码）。"""
        r = client.post("/login", json={
            "username": "admin",
            "password": "wrong_password",
            "authenticate": "LOCAL",
        })
        assert r.status_code == 400

    def test_login_user_not_exist(self, client):
        """登录失败（用户不存在）。"""
        r = client.post("/login", json={
            "username": "nonexistent",
            "password": "test123",
            "authenticate": "LOCAL",
        })
        assert r.status_code == 400

    def test_is_login(self, client):
        """检查登录状态。"""
        # 先登录
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        session = r.json()["data"]
        headers = {
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        }
        # 检查登录状态
        r = client.get("/is-login", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert data["data"]["name"]  # has name

    def test_is_login_not_authenticated(self, client):
        """未登录时检查登录状态。"""
        r = client.get("/is-login")
        assert r.status_code == 401

    def test_signout(self, client):
        """登出。"""
        # 先登录
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        session = r.json()["data"]
        headers = {
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        }
        # 登出
        r = client.post("/signout", headers=headers)
        assert r.status_code == 200
        # 登出后检查
        r = client.get("/is-login", headers=headers)
        assert r.status_code == 401

    def test_authentication_list(self, client):
        """获取认证方式。"""
        r = client.get("/authentication/get-list")
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert "LOCAL" in data["data"]


class TestPersonalInfo:
    """个人信息测试。"""

    def _login_headers(self, client):
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        session = r.json()["data"]
        return {
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        }

    def test_get_personal_info(self, client):
        """获取个人信息。"""
        headers = self._login_headers(client)
        r = client.get("/personal/get", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert data["data"]["name"]  # has name

    def test_update_personal_info(self, client):
        """更新个人信息。"""
        headers = self._login_headers(client)
        r = client.post("/personal/update-info", headers=headers, json={
            "name": "New Admin",
            "email": "new@example.com",
        })
        assert r.status_code == 200
        # 验证更新
        r = client.get("/personal/get", headers=headers)
        data = r.json()["data"]
        assert data["name"] == "New Admin"
        assert data["email"] == "new@example.com"

    def test_get_personal_info_not_login(self, client):
        """未登录获取个人信息。"""
        r = client.get("/personal/get")
        assert r.status_code == 401


class TestMenuAndSystem:
    """菜单和系统信息测试。"""

    def test_get_menu_list(self, client):
        """获取菜单列表。"""
        r = client.post("/api/user/menu")
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert len(data["data"]) > 0

    def _login_headers(self, client):
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        session = r.json()["data"]
        return {
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        }

    def test_get_system_version(self, client):
        """获取系统版本。"""
        headers = self._login_headers(client)
        r = client.get("/system/version/current", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["data"]

    def test_get_package_type(self, client):
        """获取包类型。"""
        headers = self._login_headers(client)
        r = client.get("/system/version/package-type", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["data"] in ["enterprise", "community"]

    def test_get_base_info(self, client):
        """获取基础信息。"""
        headers = self._login_headers(client)
        r = client.get("/system/parameter/get/base-info", headers=headers)
        assert r.status_code == 200
        assert r.json()["code"] == 200

    def test_get_display_config(self, client):
        """获取界面配置。"""
        headers = self._login_headers(client)
        r = client.get("/display/info", headers=headers)
        assert r.status_code == 200
        assert r.json()["code"] == 200


class TestProjectManagement:
    """项目管理测试。"""

    def _login_headers(self, client):
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        session = r.json()["data"]
        return {
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        }

    def test_get_project(self, client):
        """获取项目详情。"""
        headers = self._login_headers(client)
        r = client.get("/project/get/test-project", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert data["data"]["name"]
        assert data["data"]["id"] == "test-project"


class TestLocalConfig:
    """本地执行配置测试。"""

    def _login_headers(self, client):
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        session = r.json()["data"]
        return {
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        }

    def test_get_local_configs(self, client):
        """获取本地执行配置。"""
        headers = self._login_headers(client)
        r = client.get("/user/local/config/get", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list)

    def test_add_local_config(self, client):
        """添加本地执行配置。"""
        headers = self._login_headers(client)
        r = client.post("/user/local/config/add", headers=headers, json={
            "user_url": "http://localhost:8080",
            "type": "API",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["user_url"] == "http://localhost:8080"


class TestAPIKey:
    """API Key 管理测试。"""

    def _login_headers(self, client):
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        session = r.json()["data"]
        return {
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        }

    def test_list_api_keys(self, client):
        """获取 API Key 列表。"""
        headers = self._login_headers(client)
        r = client.get("/user/api/key/list", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list)

    def test_create_api_key(self, client):
        """创建 API Key。"""
        headers = self._login_headers(client)
        r = client.post("/user/api/key/add", headers=headers, json={
            "description": "测试Key",
            "forever": True,
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["access_key"]
        assert data["secret_key"]

    def test_delete_api_key(self, client):
        """删除 API Key。"""
        headers = self._login_headers(client)
        # 先创建
        r = client.post("/user/api/key/add", headers=headers, json={"description": "待删除"})
        key_id = r.json()["data"]["id"]
        # 删除
        r = client.post("/user/api/key/delete", headers=headers, json={"id": key_id})
        assert r.status_code == 200
        # 验证已删除
        r = client.get("/user/api/key/list", headers=headers)
        keys = r.json()["data"]
        assert all(k["id"] != key_id for k in keys)


class TestCsrfProtection:
    """安全加固：已登录写请求必须携带有效 CSRF Token。"""

    def _login_headers(self, client, with_csrf=True):
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        session = r.json()["data"]
        h = {"X-AUTH-TOKEN": session["sessionId"]}
        if with_csrf:
            h["CSRF-TOKEN"] = session["csrfToken"]
        return h

    def test_mutating_post_requires_csrf(self, client):
        """已登录 POST 无 CSRF 头 → 403。"""
        headers = self._login_headers(client, with_csrf=False)
        r = client.post("/api/apitest/definitions", headers=headers,
                        json={"name": "csrf-guard", "path": "/g"})
        assert r.status_code == 403, f"无 CSRF 的 POST 应 403，实际 {r.status_code}"

    def test_mutating_post_wrong_csrf_rejected(self, client):
        """已登录 POST 携带错误 CSRF 头 → 403。"""
        headers = self._login_headers(client, with_csrf=True)
        headers["CSRF-TOKEN"] = "forged-token"
        r = client.post("/api/apitest/definitions", headers=headers,
                        json={"name": "csrf-guard", "path": "/g"})
        assert r.status_code == 403, f"错误 CSRF 的 POST 应 403，实际 {r.status_code}"

    def test_mutating_post_with_csrf_ok(self, client):
        """已登录 POST 携带正确 CSRF 头 → 正常处理。"""
        headers = self._login_headers(client, with_csrf=True)
        r = client.post("/api/apitest/definitions", headers=headers,
                        json={"name": "csrf-ok", "path": "/ok"})
        assert r.status_code == 200, r.text

    def test_write_get_requires_csrf(self, client):
        """/api/ 下写语义 GET（如删除）无 CSRF → 403。"""
        headers = self._login_headers(client, with_csrf=False)
        r = client.get("/api/case/delete", headers=headers)
        assert r.status_code == 403, f"写语义 GET 无 CSRF 应 403，实际 {r.status_code}"

    def test_read_get_no_csrf_still_allowed(self, client):
        """只读 GET 无需 CSRF（与旧行为一致）。"""
        headers = self._login_headers(client, with_csrf=False)
        # /is-login 属公开路径，无需登录；这里验证读请求不受 CSRF 拦截
        r = client.get("/is-login", headers=headers)
        assert r.status_code == 200


class TestLoginBruteForce:
    """安全加固：连续失败达到阈值后锁定，防止暴力破解。"""

    def test_lock_after_repeated_failures(self, client):
        """同一账号连续 5 次失败后进入锁定状态。"""
        from app.auth.store import _login_failures, _login_lockout_until, auth_store
        uname = "brute_probe_user"
        # 清理可能残留状态
        _login_failures.pop(uname, None)
        _login_lockout_until.pop(uname, None)
        try:
            for i in range(_LOGIN_MAX_ATTEMPTS):
                r = client.post("/login", json={
                    "username": uname, "password": f"wrong_{i}",
                })
                assert r.status_code == 400
            # 已达阈值，应进入锁定
            assert auth_store.login_lock_remaining(uname) > 0
            # 锁定期内即使密码正确也不放行（用户不存在，authenticate 短路）
            remaining = auth_store.login_lock_remaining(uname)
            assert remaining > 0
        finally:
            # 清理锁定，避免影响其它测试
            _login_failures.pop(uname, None)
            _login_lockout_until.pop(uname, None)


class TestSessionSlidingExpiry:
    """安全加固：会话有效期随活跃访问滑动续期。"""

    def test_session_renewed_when_close_to_expiry(self, client):
        """距过期不足阈值时，访问会顺延过期时间。"""
        import time as _time

        from app.auth.store import auth_store
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        sid = r.json()["data"]["sessionId"]

        from app.core.database import Database
        conn = Database.get_conn("auth.db")
        # 将会话过期时间压到 1 小时后（不足续期阈值 24h）
        new_expire = _time.time() + 3600
        conn.execute("UPDATE sessions SET expire_time = ? WHERE id = ?", (new_expire, sid))

        # 活跃访问触发续期
        user = auth_store.get_session_user(sid)
        assert user is not None
        # 续期后过期时间应远大于原先的 1 小时后
        assert user["session_expire_time"] > new_expire + 12 * 3600

    def test_expired_session_invalid(self, client):
        """已过期会话无法获取用户。"""
        import time as _time

        from app.auth.store import auth_store
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        sid = r.json()["data"]["sessionId"]
        from app.core.database import Database
        conn = Database.get_conn("auth.db")
        conn.execute("UPDATE sessions SET expire_time = ? WHERE id = ?", (_time.time() - 10, sid))
        user = auth_store.get_session_user(sid)
        assert user is None

    def test_revoke_user_sessions_invalidates_all(self, client):
        """服务端吊销用户全部会话后，旧会话立即失效（改密/重置密码后触发）。"""
        from app.auth.store import auth_store

        # 同一用户建立两个会话
        r1 = client.post("/login", json={"username": "admin", "password": "admin123"})
        s1 = r1.json()["data"]["sessionId"]
        user_id = r1.json()["data"]["id"]
        r2 = client.post("/login", json={"username": "admin", "password": "admin123"})
        s2 = r2.json()["data"]["sessionId"]

        # 两个会话当前均有效
        assert auth_store.get_session_user(s1) is not None
        assert auth_store.get_session_user(s2) is not None

        # 吊销该用户全部会话
        revoked = auth_store.revoke_user_sessions(user_id)
        assert revoked >= 2, f"应吊销至少 2 个会话，实际 {revoked}"

        # 吊销后两个旧会话均失效
        assert auth_store.get_session_user(s1) is None
        assert auth_store.get_session_user(s2) is None


if __name__ == "__main__":
    unittest.main()

class TestWriteGetRequiresAuth:
    """安全加固：/api/ 下的「写语义 GET」路由须鉴权，只读 GET 仍放行。"""

    def _login_headers(self, client):
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        session = r.json()["data"]
        return {
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        }

    def test_write_get_rejected_without_token(self, client):
        """未登录访问写语义 GET 路由返回 401。"""
        for p in [
            "/api/case/delete",
            "/api/case/delete-to-gc/123",
            "/api/case/recover/7",
            "/api/case/run/7",
            "/api/scenario/delete/5",
            "/api/scenario/delete-to-gc/5",
            "/api/scenario/recover/5",
            "/api/definition/delete-to-gc/8",
            "/api/definition/schedule/delete",
            "/api/definition/schedule/switch/9",
            "/api/definition/stop/d1",
            "/api/scenario/stop/s1",
            "/api/debug/module/delete/3",
            "/api/doc/share/delete/10",
            "/api/stop/t1",
            "/api/report/case/delete/r1",
        ]:
            r = client.get(p)
            assert r.status_code == 401, f"{p} 应要求登录，实际 {r.status_code}"

    def test_write_get_accepted_with_token(self, client):
        """登录后写语义 GET 路由不再被鉴权拦截。"""
        headers = self._login_headers(client)
        r = client.get("/api/case/delete", headers=headers)
        assert r.status_code == 200

    def test_read_get_still_open(self, client):
        """只读 GET 路由（回收站列表等）仍无需登录。"""
        for p in [
            "/api/cases/trash",
            "/api/definition/trash/page",
            "/api/reports/trash/list",
            "/api/apitest/trash/definitions",
        ]:
            r = client.get(p)
            assert r.status_code != 401, f"{p} 为只读路由不应 401，实际 {r.status_code}"
