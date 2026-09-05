"""
用户组 Repository 层行为回归测试
==================================
目的：`app.repositories.user_group_repo.UserGroupRepo` 是用户组表唯一 DB 访问入口。
原兼容门面 `app.auth.user_groups` 已删除，本测试只验证 UserGroupRepo 自身
CRUD / 成员 / 权限的输出形态与软删除语义，守住「下沉四层化」后的行为基线。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories.user_group_repo import UserGroupRepo  # noqa: E402


def test_group_crud_output_shape():
    ng = UserGroupRepo.create_group(
        "对齐组", "描述", "SYSTEM", "scopeX", create_user="admin", pos=5)
    try:
        for f in ["name", "description", "internal", "type", "scopeId",
                  "createUser", "pos"]:
            assert f in ng, f"create 输出缺少字段 {f}"
        assert ng["name"] == "对齐组"
        assert ng["type"] == "SYSTEM"
        assert ng["pos"] == 5
    finally:
        UserGroupRepo.delete_group(ng["id"])


def test_list_groups_scope_filter():
    n = UserGroupRepo.list_groups("SYSTEM", "global")
    assert isinstance(n, list)
    assert all(g["scopeId"] in ("global", "") for g in n)
    # 组织/项目作用域
    for gtype in ("ORGANIZATION", "PROJECT"):
        assert isinstance(UserGroupRepo.list_groups(gtype, ""), list)
    # 自定义作用域
    gid = UserGroupRepo.create_group("scope组", "", "SYSTEM", "custom-scope-x")["id"]
    try:
        scope_ids = [g["id"] for g in UserGroupRepo.list_groups("SYSTEM", "custom-scope-x")]
        assert gid in scope_ids
    finally:
        UserGroupRepo.delete_group(gid)


def test_member_crud_roundtrip():
    gid = UserGroupRepo.create_group("成员组", "", "SYSTEM", "sx-m")["id"]
    try:
        nm = UserGroupRepo.add_group_member(
            gid, "u-align-1", username="alice", name="爱丽丝", email="a@x.com")
        assert nm is not None
        m = UserGroupRepo.get_group_member(gid, "u-align-1")
        assert m is not None and m["userId"] == "u-align-1"
        assert len(UserGroupRepo.list_group_members(gid)) == 1
        # 更新名称
        nu = UserGroupRepo.update_group(gid, name="改名")
        assert nu["name"] == "改名"
        # 删除成员
        UserGroupRepo.add_group_member(gid, "u-remove-new", username="n")
        assert UserGroupRepo.remove_group_member(gid, "u-remove-new") is True
        assert UserGroupRepo.get_group_member(gid, "u-remove-new") is None
    finally:
        UserGroupRepo.delete_group(gid)


def test_permissions_roundtrip():
    gid = UserGroupRepo.create_group("权限组", "", "SYSTEM", "sx-p")["id"]
    try:
        assert UserGroupRepo.update_group_permissions(gid, ["p1", "p2"]) == \
            UserGroupRepo.get_group_permissions(gid) == ["p1", "p2"]
    finally:
        UserGroupRepo.delete_group(gid)


def test_delete_builtin_protection():
    # 内置组不可删
    assert UserGroupRepo.delete_group("admin") is False


def test_remove_user_org_memberships_clears_org_type_only():
    """remove_user_org_memberships 只清 ORGANIZATION 类型，保留其它作用域关系。"""
    uid = "u-org-mem-2"
    UserGroupRepo.remove_user_org_memberships(uid)
    org_g = UserGroupRepo.create_group("Org清理组", "", "ORGANIZATION", "orgX", pos=1)
    sys_g = UserGroupRepo.create_group("Sys清理组", "", "SYSTEM", "", pos=2)
    try:
        UserGroupRepo.add_group_member(org_g["id"], uid, username="um2",
                                       group_type="ORGANIZATION", scope_id="orgX")
        UserGroupRepo.add_group_member(sys_g["id"], uid, username="um2",
                                       group_type="SYSTEM", scope_id="")
        removed = UserGroupRepo.remove_user_org_memberships(uid)
        assert removed >= 1
        # ORGANIZATION 关系已清，SYSTEM 关系保留
        assert UserGroupRepo.get_group_member(org_g["id"], uid) is None
        assert UserGroupRepo.get_group_member(sys_g["id"], uid) is not None
    finally:
        UserGroupRepo.remove_group_member(sys_g["id"], uid)
        UserGroupRepo.delete_group(org_g["id"])
        UserGroupRepo.delete_group(sys_g["id"])
