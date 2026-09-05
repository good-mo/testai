"""
apitest 4 层重构：Repository 层 env_groups/global_params 去空壳对齐回归
======================================================================
目的：确保 app.repositories.apitest_repo.ApitestRepo 将环境组 / 全局参数
数据访问从「委托 app.apitest.store」下沉为仓库内**直连 SQL** 后，输出形态
与旧 store 在共享 apitest.db 上完全一致 —— 这是消除 Repository 空壳化
后仍零回归的依据。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.apitest import store as store  # noqa: E402
from app.repositories.apitest_repo import ApitestRepo as Repo  # noqa: E402


def _uniq(prefix="APT-EG-ALIGN"):
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


def _conn():
    return Repo._apitest_conn()


def _cleanup():
    c = _conn()
    c.execute("DELETE FROM env_groups")
    c.execute("DELETE FROM global_params")
    c.commit()


def setup_function():
    _cleanup()


def teardown_function():
    _cleanup()


def test_create_output_matches_old_store():
    proj = _uniq()
    r = Repo.create_env_group(name="rg", description="rd", project_id=proj,
                              env_group_project=[{"k": 1}], pos=1)
    s = store.create_env_group(name="sg", description="sd", project_id=proj,
                               env_group_project=[{"k": 2}], pos=2)
    try:
        assert r["name"] == "rg"
        assert r["description"] == "rd"
        assert r["env_group_project"] == [{"k": 1}]
        assert s["name"] == "sg"
        assert s["env_group_project"] == [{"k": 2}]
    finally:
        Repo.delete_env_group(r["id"])
        store.delete_env_group(s["id"])


def test_get_list_match_old_store_shared_db():
    proj = _uniq()
    r = Repo.create_env_group(name="rg", project_id=proj, pos=1)
    s = store.create_env_group(name="sg", project_id=proj, pos=2)
    try:
        # repo 与 store 共享同一 apitest.db，彼此可见
        assert Repo.get_env_group(r["id"])["name"] == "rg"
        assert store.get_env_group(s["id"])["name"] == "sg"
        r_names = sorted(x["name"] for x in Repo.list_env_groups(project_id=proj))
        assert r_names == ["rg", "sg"]
    finally:
        Repo.delete_env_group(r["id"])
        store.delete_env_group(s["id"])


def test_update_delete_match():
    r = Repo.create_env_group(name="rg", description="d1")
    s = store.create_env_group(name="sg", description="d1")
    try:
        # repo update 可被 store 读到（同一库）
        Repo.update_env_group(r["id"], description="repo-desc")
        assert store.get_env_group(r["id"])["description"] == "repo-desc"
        # store 更新 repo 也能读到
        store.update_env_group(s["id"], description="store-desc")
        assert Repo.get_env_group(s["id"])["description"] == "store-desc"
        # 删除
        assert Repo.delete_env_group(r["id"]) is True
        assert Repo.get_env_group(r["id"]) is None
    finally:
        Repo.delete_env_group(r["id"])
        store.delete_env_group(s["id"])


def test_global_params_align_and_mutual_readback():
    proj = _uniq()
    # repo 新建
    rgp = Repo.save_global_params(proj, headers=[{"h": 1}],
                                  common_variables=[{"v": 1}])
    try:
        assert rgp["headers"] == [{"h": 1}]
        assert rgp["common_variables"] == [{"v": 1}]
        # store 能读到 repo 写入的全局参数
        assert store.get_global_params(proj)["headers"] == [{"h": 1}]
        # store 更新后 repo 也能读到
        store.save_global_params(proj, headers=[{"h": 2}])
        assert Repo.get_global_params(proj)["headers"] == [{"h": 2}]
        # common_variables 在仅更新 headers 时保留
        assert Repo.get_global_params(proj)["common_variables"] == [{"v": 1}]
        # 删除
        assert Repo.delete_global_params(proj) is True
        assert Repo.get_global_params(proj) is None
    finally:
        Repo.delete_global_params(proj)


def test_delete_global_param_by_id():
    proj = _uniq()
    gp = Repo.save_global_params(proj, headers=[{"h": 1}])
    assert Repo.delete_global_param_by_id(gp["id"]) is True
    assert Repo.get_global_params(proj) is None
