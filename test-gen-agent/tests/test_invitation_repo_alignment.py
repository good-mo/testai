"""邀请域去空壳化：InvitationRepo 直连 SQL 行为回归测试
================================================================
目的：邀请注册为独立小域，`InvitationRepo` 是 invitations 表唯一数据
访问入口（system_compat / project_compat 等路由经 invitation_repo 真实落库）。
本测试锁定邀请的创建 / 按 invite_id 查询 / 有效性（有效期 / 未使用）/
标记已用 的真实 DB 语义，确保「邀请链接一旦生成便持久、可用可校验、
用完即失效」的流程不被破坏。
"""
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories.invitation_repo import invitation_repo  # noqa: E402


def _uniq_email():
    return "align-%s@example.com" % uuid.uuid4().hex[:8]


def _cleanup(invite_id):
    try:
        conn = invitation_repo.get_by_invite_id(invite_id)
        if conn:
            c = invitation_repo.get_conn()
            c.execute("DELETE FROM invitations WHERE invite_id = ?", (invite_id,))
            c.commit()
    except Exception:
        pass


def test_create_returns_invite_and_persists():
    email = _uniq_email()
    inv = invitation_repo.create_invite(
        [email], scope="ORGANIZATION", organization_id="org-a",
        project_id="proj-a", role_ids=["g1", "g2"], create_user="admin",
    )
    assert inv and inv.get("invite_id"), "create_invite 应返回含 invite_id 的记录"
    try:
        got = invitation_repo.get_by_invite_id(inv["invite_id"])
        assert got is not None, "创建后应能从 DB 按 invite_id 读回"
        assert got["scope"] == "ORGANIZATION"
        assert got["organization_id"] == "org-a"
        assert got["project_id"] == "proj-a"
        assert got["email"] == email
        assert got["used"] == 0
        import json
        assert json.loads(got["role_ids"]) == ["g1", "g2"]
    finally:
        _cleanup(inv["invite_id"])


def test_default_scope_is_system_when_empty():
    inv = invitation_repo.create_invite([_uniq_email()])
    assert inv and inv.get("invite_id")
    try:
        got = invitation_repo.get_by_invite_id(inv["invite_id"])
        assert got["scope"] == "SYSTEM"
    finally:
        _cleanup(inv["invite_id"])


def test_is_valid_before_and_invalid_after_use():
    inv = invitation_repo.create_invite([_uniq_email()])
    iid = inv["invite_id"]
    try:
        assert invitation_repo.is_valid(iid) is True
        assert invitation_repo.mark_used(iid) is True
        assert invitation_repo.is_valid(iid) is False, "已使用邀请应失效"
    finally:
        _cleanup(iid)


def test_expired_invite_is_invalid():
    email = _uniq_email()
    # 过期邀请：直接插入一条 expire_time 已过去的记录
    now = time.time()
    conn = invitation_repo.get_conn()
    conn.execute(
        "INSERT INTO invitations (id, invite_id, email, scope, expire_time, used) "
        "VALUES (?, ?, ?, 'SYSTEM', ?, 0)",
        (str(uuid.uuid4()), "expired-%s" % uuid.uuid4().hex[:8], email, now - 10),
    )
    conn.commit()
    iid = conn.execute(
        "SELECT invite_id FROM invitations WHERE email = ?", (email,)
    ).fetchone()["invite_id"]
    try:
        assert invitation_repo.is_valid(iid) is False, "过期邀请应失效"
    finally:
        _cleanup(iid)


def test_unknown_invite_invalid():
    assert invitation_repo.is_valid("no-such-invite-" + uuid.uuid4().hex[:8]) is False


def test_multiple_emails_returns_first():
    """为多邮箱创建，应返回首邮箱的记录并带可用的 invite_id。"""
    inv = invitation_repo.create_invite(
        [_uniq_email(), _uniq_email()], scope="PROJECT",
        organization_id="", project_id="pj-multi",
    )
    assert inv and inv.get("invite_id")
    try:
        assert invitation_repo.is_valid(inv["invite_id"]) is True
    finally:
        _cleanup(inv["invite_id"])
