"""
认证域 4 层重构：repository 层与旧 app.auth.store.AuthStore 对齐回归测试
=========================================================================
目的：确保下沉后的 app.repositories.auth_repo.AuthRepo（auth.db → tga.db
直连 SQL）在相同数据库上，用户 / 会话 / API Key / 本地配置的数据访问输出
形态与旧 app.auth.store.AuthStore 完全一致 —— 这是把 Repository 从
「委托空壳」下沉为直连 SQL 后仍零回归的依据。

由于两条路径读写同一张物理表（users / sessions / api_keys /
user_local_configs），测试对新增数据使用唯一用户名，验证后清理。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.auth.store import AuthStore  # noqa: E402
from app.repositories.auth_repo import AuthRepo  # noqa: E402

old = AuthStore()
repo = AuthRepo()


def _uniq(prefix="AUTH-ALIGN"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_create_user_output_matches_old_store():
    # repo 与旧 store 各自创建，字段口径应一致
    uname_r = _uniq()
    uname_o = _uniq()
    ru = repo.create_user(uname_r, "pass1234", name="Repo 用户", email="r@x.com")
    ou = old.create_user(uname_o, "pass1234", name="Old 用户", email="o@x.com")
    try:
        assert ru["username"] == uname_r
        assert ou["username"] == uname_o
        # 字段口径一致：入参字段按预期写入，默认字段两端一致
        assert ru.get("name") == "Repo 用户"
        assert ou.get("name") == "Old 用户"
        assert ru.get("email") == "r@x.com"
        assert ou.get("email") == "o@x.com"
        for f in ("role", "enable"):
            assert ru.get(f) == ou.get(f), f"字段 {f} 不一致 new={ru.get(f)} old={ou.get(f)}"
        # 都不含明文密码哈希
        assert "password_hash" not in ru
        assert "password_hash" not in ou
        # 密码登录两端一致（同一套 PBKDF2 校验）
        assert repo.authenticate(uname_r, "pass1234") is not None
        assert old.authenticate(uname_o, "pass1234") is not None
    finally:
        repo.delete_user(ru["id"])
        old.delete_user(ou["id"])


def test_get_by_id_and_username_match():
    uname = _uniq()
    ru = repo.create_user(uname, "pass1234", name="对齐", role="user")
    try:
        got = repo.get_user_by_id(ru["id"])
        old_got = old.get_user_by_id(ru["id"])
        assert got is not None and old_got is not None
        assert got["username"] == old_got["username"] == uname
        by_name = repo.get_user_by_username(uname)
        assert by_name is not None and by_name["id"] == ru["id"]
    finally:
        repo.delete_user(ru["id"])


def test_update_delete_and_enable_consistent():
    uname = _uniq()
    ru = repo.create_user(uname, "pass1234")
    try:
        upd = repo.update_user(ru["id"], name="改名", email="new@x.com")
        assert upd["name"] == "改名"
        assert upd["email"] == "new@x.com"
        # 旧 store 视角读取到同一行（同表）
        assert old.get_user_by_id(ru["id"])["email"] == "new@x.com"
        # 禁用后 authenticate 失败
        repo.set_user_enabled(ru["id"], False)
        assert repo.authenticate(uname, "pass1234") is None
        repo.set_user_enabled(ru["id"], True)
        assert repo.authenticate(uname, "pass1234") is not None
    finally:
        repo.delete_user(ru["id"])


def test_session_crud_and_readback_consistent():
    uname = _uniq()
    ru = repo.create_user(uname, "pass1234")
    try:
        sess = repo.create_session(ru["id"], ip="127.0.0.1")
        assert set(sess) == {"sessionId", "csrfToken"}
        # repo 视角读回
        u = repo.get_session_user(sess["sessionId"])
        assert u is not None and u["id"] == ru["id"]
        assert u.get("_csrf_token") == sess["csrfToken"]
        # 旧 store 视角读回同一条会话
        u2 = old.get_session_user(sess["sessionId"])
        assert u2 is not None and u2["id"] == ru["id"]
        # 登出删除后两端都不可见
        assert repo.delete_session(sess["sessionId"]) is True
        assert repo.get_session_user(sess["sessionId"]) is None
        assert old.get_session_user(sess["sessionId"]) is None
    finally:
        repo.delete_user(ru["id"])


def test_local_config_crud_consistent():
    uname = _uniq()
    ru = repo.create_user(uname, "pass1234")
    try:
        cfg = repo.add_local_config(ru["id"], "http://local.run", cfg_type="API")
        assert cfg.get("id")
        # 两端都能读到同一条配置
        got_repo = repo.get_local_configs(ru["id"])
        got_old = old.get_local_configs(ru["id"])
        assert any(c["id"] == cfg["id"] for c in got_repo)
        assert any(c["id"] == cfg["id"] for c in got_old)
        # 更新 + 启停
        assert repo.update_local_config(cfg["id"], "http://new.run") is True
        assert repo.toggle_local_config(cfg["id"], True) is True
    finally:
        # 清理配置 + 用户
        for c in repo.get_local_configs(ru["id"]):
            try:
                repo._conn().execute(
                    "DELETE FROM user_local_configs WHERE id = ?", (c["id"],)
                )
                repo._conn().commit()
            except Exception:
                pass
        repo.delete_user(ru["id"])


def test_api_key_crud_consistent():
    uname = _uniq()
    ru = repo.create_user(uname, "pass1234")
    try:
        key = repo.create_api_key(ru["id"], description="对齐", forever=True)
        assert key.get("access_key", "").startswith("ak_")
        # 两端读回
        got_repo = repo.list_api_keys(ru["id"])
        got_old = old.list_api_keys(ru["id"])
        assert any(k["id"] == key["id"] for k in got_repo)
        assert any(k["id"] == key["id"] for k in got_old)
        # 不返回 secret
        for k in got_repo:
            assert "secret_key" not in k
        # 启停 + 删除
        assert repo.toggle_api_key(key["id"], False) is True
        assert repo.delete_api_key(key["id"]) is True
        assert not any(k["id"] == key["id"] for k in repo.list_api_keys(ru["id"]))
    finally:
        repo.delete_user(ru["id"])


def test_rsa_and_login_guard_shared():
    # RSA 公钥可读取（repo 与 store 同源，store 为模块级函数）
    from app.auth.store import get_rsa_public_key as old_pk_fn
    pk_repo = repo.get_rsa_public_key()
    pk_old = old_pk_fn()
    assert pk_repo and pk_repo == pk_old
    # 防爆破计数共享：repo 侧失败会反映到 store 侧锁定口径
    from app.auth.store import _login_failures, _login_lockout_until
    uname = _uniq()
    _login_failures.pop(uname, None)
    _login_lockout_until.pop(uname, None)
    try:
        for i in range(5):
            repo.authenticate(uname, f"wrong_{i}")
        assert repo.login_lock_remaining(uname) > 0
        assert old.login_lock_remaining(uname) > 0
    finally:
        _login_failures.pop(uname, None)
        _login_lockout_until.pop(uname, None)
