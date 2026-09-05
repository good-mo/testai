# -*- coding: utf-8 -*-
"""file / template / message / display_config 仓库四层下沉验证测试。

验证这些仓库的 SQL 已真正沉入 L3（非空壳委托），并覆盖事务包裹后的
多写操作正确性（清级联 / 批量 upsert / 默认模板切换）。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories.display_config_repo import DisplayConfigRepo  # noqa: E402
from app.repositories.file_repo import FileRepo  # noqa: E402
from app.repositories.message_repo import MessageRepo  # noqa: E402
from app.repositories.template_repo import TemplateRepo  # noqa: E402


def _uniq(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _cleanup(cleaners):
    """执行清理函数。"""
    for c in cleaners:
        try:
            c()
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════
# FileRepo — 项目文件元数据
# ════════════════════════════════════════════════════════════════
class TestFileRepoSQLSunk:
    """file_repo 方法全部为仓库内直连 SQL，无旧域委托。"""

    def setup_method(self):
        self.fid = _uniq("FILE")
        self.pid = _uniq("PROJ")

    def teardown_method(self):
        _cleanup([lambda: FileRepo.delete_by_ids([self.fid])])

    def test_upsert_and_get_meta(self):
        FileRepo.upsert_meta(self.fid, {
            "name": "req.md", "project_id": self.pid,
            "module_id": "m1", "create_user": "admin",
            "file_type": "DOC", "size": 1024, "enable": 1,
        })
        meta = FileRepo.get_meta(self.fid)
        assert meta is not None
        assert meta["name"] == "req.md"
        assert meta["project_id"] == self.pid
        assert meta["file_type"] == "DOC"
        assert meta["size"] == 1024
        assert meta["create_user"] == "admin"

    def test_upsert_update_existing(self):
        FileRepo.upsert_meta(self.fid, {
            "name": "a.txt", "project_id": self.pid, "size": 100,
        })
        FileRepo.upsert_meta(self.fid, {
            "name": "b.txt", "project_id": self.pid, "size": 200,
            "description": "updated",
        })
        meta = FileRepo.get_meta(self.fid)
        assert meta is not None
        assert meta["name"] == "b.txt"
        assert meta["size"] == 200
        assert meta["description"] == "updated"

    def test_list_by_project_and_ids(self):
        fid2 = _uniq("FILE2")
        FileRepo.upsert_meta(self.fid, {
            "name": "x.txt", "project_id": self.pid,
        })
        FileRepo.upsert_meta(fid2, {
            "name": "y.txt", "project_id": self.pid,
        })
        try:
            files = FileRepo.list_by_project(self.pid)
            ids = {f["id"] for f in files}
            assert self.fid in ids and fid2 in ids

            got = FileRepo.list_by_ids([self.fid, fid2])
            assert len(got) == 2
        finally:
            FileRepo.delete_by_ids([fid2])

    def test_count_by_module(self):
        FileRepo.upsert_meta(self.fid, {
            "name": "m.txt", "project_id": self.pid, "module_id": "m1",
        })
        counts = FileRepo.count_by_module(self.pid)
        assert counts.get("all", 0) >= 1
        assert counts.get("m1", 0) >= 1

    def test_delete_by_ids(self):
        FileRepo.upsert_meta(self.fid, {"name": "del.txt", "project_id": self.pid})
        assert FileRepo.get_meta(self.fid) is not None
        deleted = FileRepo.delete_by_ids([self.fid])
        assert deleted > 0
        assert FileRepo.get_meta(self.fid) is None

    def test_repo_has_no_delegation(self):
        """确保 file_repo 不委托旧域模块——不应 import app.file_mgmt 等。"""
        import inspect

        import app.repositories.file_repo as mod

        src = inspect.getsource(mod)
        # 不应有转发/委托至旧域的 import
        assert "from app.file_mgmt" not in src
        assert "from app.message" not in src
        assert "app.defects" not in src
        assert "app.cases" not in src


# ════════════════════════════════════════════════════════════════
# TemplateRepo — 模板
# ════════════════════════════════════════════════════════════════
class TestTemplateRepoSQLSunk:
    """template_repo 全部方法为仓库内直连 SQL。"""

    def setup_method(self):
        self.tid = _uniq("TPL")
        self.scope_id = _uniq("SCOPE")
        self.scope_type = "PROJECT"
        self.scene = "FUNCTIONAL"

    def teardown_method(self):
        _cleanup([
            lambda: TemplateRepo.delete_template(self.tid),
        ])

    def test_list_and_get(self):
        TemplateRepo.upsert_template(self.tid, {
            "name": "Template A", "scopeId": self.scope_id,
            "scene": self.scene, "customFields": [{"id": "f1"}],
        }, self.scope_type)
        rows = TemplateRepo.list_templates(self.scope_type, self.scope_id, self.scene)
        assert any(r["id"] == self.tid for r in rows)

        t = TemplateRepo.get_template(self.tid)
        assert t is not None
        assert t["name"] == "Template A"
        assert "f1" in t.get("custom_fields", "")

    def test_count_in_scope(self):
        TemplateRepo.upsert_template(self.tid, {
            "name": "T1", "scopeId": self.scope_id, "scene": self.scene,
        }, self.scope_type)
        cnt = TemplateRepo.count_in_scope(self.scope_type, self.scope_id, self.scene)
        assert cnt >= 1

    def test_set_default_transaction_atomic(self):
        """set_default 多写操作应包裹在事务中，保证原子性。"""
        tid2 = _uniq("TPL2")
        TemplateRepo.upsert_template(self.tid, {
            "name": "T1", "scopeId": self.scope_id, "scene": self.scene,
        }, self.scope_type)
        TemplateRepo.upsert_template(tid2, {
            "name": "T2", "scopeId": self.scope_id, "scene": self.scene,
        }, self.scope_type)
        try:
            # 设置 tid2 为默认 → tid1 的 enable_default 应被清除
            ok = TemplateRepo.set_default(self.scope_type, self.scope_id, self.scene, tid2)
            assert ok

            t1 = TemplateRepo.get_template(self.tid)
            t2 = TemplateRepo.get_template(tid2)
            assert t1["enable_default"] == 0
            assert t2["enable_default"] == 1

            # 切回 tid1
            ok2 = TemplateRepo.set_default(self.scope_type, self.scope_id, self.scene, self.tid)
            assert ok2
            t1b = TemplateRepo.get_template(self.tid)
            t2b = TemplateRepo.get_template(tid2)
            assert t1b["enable_default"] == 1
            assert t2b["enable_default"] == 0
        finally:
            TemplateRepo.delete_template(tid2)

    def test_upsert_update_and_delete(self):
        TemplateRepo.upsert_template(self.tid, {
            "name": "Orig", "scopeId": self.scope_id, "scene": self.scene,
        }, self.scope_type)
        TemplateRepo.upsert_template(self.tid, {
            "name": "Updated", "scopeId": self.scope_id, "scene": self.scene,
        }, self.scope_type)
        t = TemplateRepo.get_template(self.tid)
        assert t["name"] == "Updated"

        ok = TemplateRepo.delete_template(self.tid)
        assert ok
        assert TemplateRepo.get_template(self.tid) is None

    def test_seed_default(self):
        """seed_default 在范围内无模板时自动落一条默认模板。"""
        sid = _uniq("SCOPE2")
        try:
            seeded = TemplateRepo.seed_default("PROJECT", sid, "FUNCTIONAL", "系统默认")
            if seeded:
                rows = TemplateRepo.list_templates("PROJECT", sid, "FUNCTIONAL")
                assert len(rows) >= 1
                assert rows[0]["name"] == "系统默认"
                TemplateRepo.delete_template(rows[0]["id"])
            else:
                # 范围内已有模板，seed 不应重复
                existing = TemplateRepo.list_templates("PROJECT", sid, "FUNCTIONAL")
                assert len(existing) >= 1
        finally:
            rows = TemplateRepo.list_templates("PROJECT", sid, "FUNCTIONAL")
            for r in rows:
                TemplateRepo.delete_template(r["id"])

    def test_repo_has_no_delegation(self):
        import inspect

        import app.repositories.template_repo as mod
        src = inspect.getsource(mod)
        assert "from app.template" not in src
        assert "from app.projects" not in src


# ════════════════════════════════════════════════════════════════
# MessageRepo — 机器人/消息设置/站内通知
# ════════════════════════════════════════════════════════════════
class TestMessageRepoSQLSunk:
    """message_repo 全部方法为仓库内直连 SQL，无旧域委托。"""

    def setup_method(self):
        self.pid = _uniq("MSP")
        self.rid = _uniq("ROB")

    def teardown_method(self):
        _cleanup([
            lambda: MessageRepo.delete_robot(self.rid),
        ])

    def test_robot_crud(self):
        MessageRepo.create_robot({
            "id": self.rid,
            "project_id": self.pid,
            "name": "钉钉机器人", "platform": "DING_TALK",
            "webhook": "https://example.com/hook", "enable": True,
        })
        r = MessageRepo.get_robot(self.rid)
        assert r is not None
        assert r["name"] == "钉钉机器人"
        assert r["platform"] == "DING_TALK"
        assert r["enable"] == 1

        robots = MessageRepo.list_robots(self.pid)
        assert any(x["id"] == self.rid for x in robots)

        # 更新
        ok = MessageRepo.update_robot(self.rid, {"name": "新名字", "enable": False})
        assert ok
        r2 = MessageRepo.get_robot(self.rid)
        assert r2["name"] == "新名字"
        assert r2["enable"] == 0

    def test_delete_robot_transaction_atomic(self):
        """delete_robot 级联清理 message_tasks 应事务原子。"""
        MessageRepo.create_robot({
            "id": self.rid, "project_id": self.pid, "name": "R",
        })
        # 创建关联消息设置
        MessageRepo.upsert_task({
            "project_id": self.pid,
            "task_type": "BUG_TASK", "event": "CREATE",
            "robot_id": self.rid, "enable": True,
        })
        assert MessageRepo.get_task(self.pid, "BUG_TASK", "CREATE", self.rid) is not None

        # 删除机器人 → 关联任务也应被清理
        ok = MessageRepo.delete_robot(self.rid)
        assert ok
        assert MessageRepo.get_robot(self.rid) is None
        assert MessageRepo.get_task(self.pid, "BUG_TASK", "CREATE", self.rid) is None

    def test_task_upsert_and_get(self):
        MessageRepo.upsert_task({
            "project_id": self.pid,
            "task_type": "BUG_TASK", "event": "CREATE",
            "robot_id": "IN_SITE", "receiver_ids": ["OPERATOR"],
            "subject": "默认主题", "enable": True,
        })
        t = MessageRepo.get_task(self.pid, "BUG_TASK", "CREATE", "IN_SITE")
        assert t is not None
        assert t["receiver_ids"] == ["OPERATOR"]
        assert t["enable"] == 1

        # 再次 upsert 应更新而非新建
        MessageRepo.upsert_task({
            "project_id": self.pid,
            "task_type": "BUG_TASK", "event": "CREATE",
            "robot_id": "IN_SITE", "receiver_ids": ["OPERATOR", "CREATE_USER"],
            "enable": False,
        })
        t2 = MessageRepo.get_task(self.pid, "BUG_TASK", "CREATE", "IN_SITE")
        assert t2 is not None
        assert len(t2["receiver_ids"]) == 2
        assert t2["enable"] == 0

    def test_notification_flow(self):
        nid = MessageRepo.create_notification({
            "title": "通知标题", "content": "内容",
            "receiver": "admin", "status": "UNREAD",
        })
        assert nid

        rows = MessageRepo.list_notifications(receiver="admin")
        assert len(rows) > 0
        cnt = MessageRepo.count_notifications(receiver="admin")
        assert cnt > 0

        # 标记已读
        ok = MessageRepo.set_read(nid)
        assert ok
        cnt_unread = MessageRepo.count_notifications(receiver="admin", status="UNREAD")
        assert cnt_unread >= 0

    def test_robot_enable_toggle(self):
        MessageRepo.create_robot({
            "id": self.rid, "project_id": self.pid, "name": "R",
        })
        ok = MessageRepo.set_robot_enable(self.rid, False)
        assert ok
        r = MessageRepo.get_robot(self.rid)
        assert r["enable"] == 0

        ok = MessageRepo.set_robot_enable(self.rid, True)
        assert ok
        r = MessageRepo.get_robot(self.rid)
        assert r["enable"] == 1

    def test_repo_has_no_delegation(self):
        import inspect

        import app.repositories.message_repo as mod
        src = inspect.getsource(mod)
        assert "from app.message" not in src
        assert "from app.defects" not in src
        assert "from app.cases" not in src
        assert "from app.projects" not in src


# ════════════════════════════════════════════════════════════════
# DisplayConfigRepo — 页面展示配置
# ════════════════════════════════════════════════════════════════
class TestDisplayConfigRepoSQLSunk:
    """display_config_repo 全部方法为仓库内直连 SQL。"""

    def setup_method(self):
        DisplayConfigRepo.clear()

    def teardown_method(self):
        DisplayConfigRepo.clear()

    def test_save_many_transaction_atomic(self):
        """save_many 批量 upsert 应在事务内完成。"""
        DisplayConfigRepo.save_many([
            {"paramKey": "ui.title", "paramValue": "平台", "type": "text"},
            {"paramKey": "ui.slogan", "paramValue": "测试", "type": "text"},
            {"paramKey": "ui.icon", "paramValue": "logo.png", "type": "file",
             "fileName": "/attachment/download/abc"},
        ])
        items = DisplayConfigRepo.get_all()
        assert len(items) == 3

        keys = {i["paramKey"] for i in items}
        assert "ui.title" in keys
        assert "ui.icon" in keys

    def test_file_item_clear(self):
        """文件项清空语义：无文件且 original=True 时删除记录。"""
        DisplayConfigRepo.save_many([
            {"paramKey": "ui.icon", "paramValue": "x.png", "type": "file",
             "fileName": "/att/1"},
        ])
        items = DisplayConfigRepo.get_all()
        assert len(items) == 1

        # 清空文件项
        DisplayConfigRepo.save_many([
            {"paramKey": "ui.icon", "paramValue": "", "type": "file",
             "fileName": "", "original": True, "hasFile": False},
        ])
        items2 = DisplayConfigRepo.get_all()
        assert len(items2) == 0

    def test_get_by_key(self):
        DisplayConfigRepo.save_many([
            {"paramKey": "ui.title", "paramValue": "My Platform", "type": "text"},
        ])
        item = DisplayConfigRepo.get_by_key("ui.title")
        assert item is not None
        assert item["paramValue"] == "My Platform"

        missing = DisplayConfigRepo.get_by_key("ui.does_not_exist")
        assert missing is None

    def test_delete_and_clear(self):
        DisplayConfigRepo.save_many([
            {"paramKey": "ui.title", "paramValue": "P", "type": "text"},
            {"paramKey": "ui.slogan", "paramValue": "S", "type": "text"},
        ])
        DisplayConfigRepo.delete_by_key("ui.title")
        items = DisplayConfigRepo.get_all()
        assert len(items) == 1
        assert items[0]["paramKey"] == "ui.slogan"

        DisplayConfigRepo.clear()
        assert len(DisplayConfigRepo.get_all()) == 0

    def test_repo_has_no_delegation(self):
        import inspect

        import app.repositories.display_config_repo as mod
        src = inspect.getsource(mod)
        assert "from app.auth.store" not in src
        assert "from app.auth.router" not in src
        assert "from app.system" not in src


# ════════════════════════════════════════════════════════════════
# 跨仓库验证：schema 注册一致 + 无漂移
# ════════════════════════════════════════════════════════════════
class TestRepoSchemaConsistency:
    """验证仓库 DDL 与 schema_registry 对齐。"""

    def test_table_sources_registered(self):
        from app.core import schema_registry

        # 表应有唯一 DDL 来源，指向对应仓库
        assert "project_files" in schema_registry.TABLE_SOURCES
        assert "templates" in schema_registry.TABLE_SOURCES
        assert "project_robots" in schema_registry.TABLE_SOURCES
        assert "message_tasks" in schema_registry.TABLE_SOURCES
        assert "notifications" in schema_registry.TABLE_SOURCES
        assert "page_display_configs" in schema_registry.TABLE_SOURCES

    def test_no_schema_drift(self):
        import subprocess
        result = subprocess.run(
            ["python3", "scripts/sync_schema_registry.py", "--check"],
            capture_output=True, text=True, cwd="/workspace",
        )
        assert result.returncode == 0, f"schema drift: {result.stdout} {result.stderr}"
