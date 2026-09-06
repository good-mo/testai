"""项目版本域下沉对齐测试（ProjectVersionRepo / ProjectVersionService）。

目的：project_versions 域下沉为 Router → ProjectVersionService →
ProjectVersionRepo 直连 SQL 后，锁定 repo 的建表 / CRUD / 开关读写，
以及 service 的 snake_case → camelCase 归一化语义，保证「下沉前路由内联
SQL 的行为」在下沉后保持一致（零回归由本对齐用例保证）。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories.project_version_repo import ProjectVersionRepo  # noqa: E402
from app.repositories.project_version_repo import project_version_repo  # noqa: E402
from app.services.project_version_service import project_version_service  # noqa: E402


def test_repo_crud_and_service_camelcase_roundtrip():
    """repo CRUD + service camelCase 归一化往返。"""
    pid = "proj-ver-%s" % uuid.uuid4().hex[:8]

    # service.add 应返回 camelCase 版本对象
    v = project_version_service.add(pid, "v1.0", "desc", status=False, latest=False,
                                    publish_time=1700000000000)
    assert v is not None
    vid = v["id"]
    assert v["projectId"] == pid
    assert v["status"] is False and v["latest"] is False
    assert v["publishTime"] == 1700000000000

    # repo 层应能直接读回（snake_case 行）
    row = ProjectVersionRepo.get_version(vid)
    assert row is not None
    assert row["project_id"] == pid and row["name"] == "v1.0"

    try:
        # service.list_items（camelCase）
        items = project_version_service.list_items(pid)
        assert len(items) == 1
        for key in ("id", "name", "status", "latest", "publishTime",
                    "createTime", "createUser", "projectId"):
            assert key in items[0], f"版本项缺字段 {key}"

        # service.options
        opts = project_version_service.options(pid)
        assert opts and "id" in opts[0] and "enable" in opts[0]

        # update
        up = project_version_service.update(vid, {"name": "v1.0-up", "status": True})
        assert up["name"] == "v1.0-up" and up["status"] is True

        # 重复 name 查询（keyword 过滤）
        items_kw = project_version_service.list_items(pid, keyword="up")
        assert len(items_kw) == 1

        # latest 置顶（需先有两版本）
        v2 = project_version_service.add(pid, "v2.0")
        v2id = v2["id"]
        project_version_service.set_latest(v2id)
        assert project_version_repo.get_version(v2id)["latest"] == 1
        assert project_version_repo.get_version(vid)["latest"] == 0

        # 删除
        assert project_version_service.delete(vid) is True
        assert project_version_service.delete(v2id) is True
        assert project_version_service.list_items(pid) == []
    finally:
        try:
            ProjectVersionRepo.delete_version(vid)
        except Exception:
            pass


def test_feature_enabled_toggle_roundtrip():
    """版本功能开关读写（project_app_configs 模块配置）。"""
    pid = "proj-ver-fea-%s" % uuid.uuid4().hex[:8]
    # 若 project_app_configs 表不存在则先补建，保证开关落库可读回
    conn = ProjectVersionRepo._conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_app_configs (
                project_id TEXT NOT NULL,
                module TEXT NOT NULL,
                config_key TEXT NOT NULL,
                config_value TEXT DEFAULT '',
                updated_at REAL,
                PRIMARY KEY (project_id, module, config_key)
            )
        """)
        conn.commit()
    except Exception:
        pass

    assert project_version_service.is_feature_enabled(pid) is False
    project_version_service.set_feature_enabled(pid, True)
    assert project_version_service.is_feature_enabled(pid) is True
    new_state = project_version_service.toggle_feature_enabled(pid)
    assert new_state is False
    assert project_version_service.is_feature_enabled(pid) is False
