"""DDD 支撑域（environment/file/message/script/template）· 阶段 C 迁移回归测试。

背景
----
`app/domain/{environment,file,message,script,template}/` DDD 层就绪后，
本测试锁定「阶段 C」Service 委托契约：既有四层 Service 收敛为**薄门面**，
核心生命周期经 DDD 应用服务 / 聚合根守护不变量（名称非空、状态机等），
同时保持旧 Service 方法签名与返回 schema 向后兼容。

覆盖目标：
  1. script_service —— register/get/update/delete 经 DDD 委托；
  2. template_service —— list/add/get/update/delete/set_default 经 DDD；
  3. environment_service —— create/get/update/delete 经 DDD；
  4. message_service —— robot CRUD + 通知已读 经 DDD；
  5. file_service —— save_file/delete_file 经 DDD（补全 schema）。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import pytest

from app.core.database import Database  # noqa: E402

TAG = "migsvc"


def _mk(prefix="MIG") -> str:
    return f"{TAG}-{prefix}-{uuid.uuid4().hex[:8]}"


def _cleanup(table, db, _id):
    """通用清理：按 id 删除测试记录。"""
    try:
        conn = Database.get_conn(db)
        conn.execute(f"DELETE FROM {table} WHERE id=?", (_id,))
        conn.commit()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 一、Script 脚本域 Service 委托
# ═══════════════════════════════════════════════════════════
class TestScriptServiceDelegation:
    def test_register_get_update_delete(self):
        """script_service 委托 DDD：生命周期 CRUD + 名称守卫。"""
        from app.services.script_service import script_service

        s = script_service.register(
            name=_mk("script"), file_path="/tmp/test_ui.py",
            framework="pytest", description="迁移回归",
        )
        assert s and s["id"]
        sid = s["id"]
        try:
            got = script_service.get(sid)
            assert got and got["id"] == sid
            assert got["framework"] == "pytest"
            # 更新（经 DDD 聚合守护）
            upd = script_service.update(sid, description="已更新")
            assert upd and upd["description"] == "已更新"
        finally:
            script_service.delete(sid)

    def test_get_not_found_returns_none(self):
        """缺失返回 None（维持旧契约）。"""
        from app.services.script_service import script_service
        assert script_service.get("nonexistent") is None

    def test_register_empty_name_rejected(self):
        """空名由聚合根拒绝。"""
        from app.services.script_service import script_service
        with pytest.raises(Exception):
            script_service.register(name="")

    def test_evaluate_selector_and_stats(self):
        """纯计算委托保持可用。"""
        from app.services.script_service import script_service
        r = script_service.evaluate_selector("css", "#submit-btn")
        assert r and "score" in r
        assert script_service.get_stats() is not None


# ═══════════════════════════════════════════════════════════
# 二、Template 模板域 Service 委托
# ═══════════════════════════════════════════════════════════
class TestTemplateServiceDelegation:
    def _create(self):
        from app.services.template_service import template_service
        pid = _mk("proj")
        t = template_service.add_template("PROJECT", {
            "name": _mk("tpl"), "remark": "mig", "scene": "FUNCTIONAL",
            "scopeId": pid, "customFields": [], "systemFields": [],
        })
        assert t and t["id"]
        return t, pid

    def test_add_get_update_delete(self):
        """template_service 委托 DDD：生命周期 CRUD。"""
        from app.services.template_service import template_service
        t, pid = self._create()
        tid = t["id"]
        try:
            got = template_service.get_template("PROJECT", tid)
            assert got and got["id"] == tid
            # 列表应含该模板（或自动播种默认）
            lst = template_service.list_templates("PROJECT", pid, "FUNCTIONAL")
            assert any(x["id"] == tid for x in lst)
            # 更新
            upd = template_service.update_template("PROJECT", tid, {
                "id": tid, "name": "迁移改名", "scene": "FUNCTIONAL",
                "scopeId": pid, "customFields": [], "systemFields": [],
            })
            assert upd and upd["name"] == "迁移改名"
            assert template_service.get_template("PROJECT", tid)["name"] == "迁移改名"
        finally:
            template_service.delete_template(tid)

    def test_get_not_found_returns_none(self):
        """缺失返回 None。"""
        from app.services.template_service import template_service
        assert template_service.get_template("PROJECT", "nope") is None


# ═══════════════════════════════════════════════════════════
# 三、Environment 环境域 Service 委托
# ═══════════════════════════════════════════════════════════
class TestEnvironmentServiceDelegation:
    def _create(self):
        from app.services.environment_service import environment_service
        env = environment_service.create({
            "name": _mk("env"), "description": "mig", "env_type": "docker",
        })
        assert env and env.get("id")
        return env

    def test_create_get_update_delete(self):
        """environment_service 委托 DDD：生命周期 CRUD。"""
        from app.services.environment_service import environment_service
        env = self._create()
        eid = env["id"]
        try:
            got = environment_service.get(eid)
            assert got and got["id"] == eid
            assert got["name"] == env["name"]
            # 更新
            upd = environment_service.update(eid, {"description": "更新描述"})
            assert upd and upd["description"] == "更新描述"
            # 删除
            assert environment_service.delete(eid) is True
            assert environment_service.get(eid) is None
        finally:
            environment_service.delete(eid)

    def test_list_and_trash(self):
        """回收站操作经 DDD 委托。"""
        from app.services.environment_service import environment_service
        env = self._create()
        eid = env["id"]
        try:
            assert environment_service.list() is not None
            assert environment_service.trash(eid) is True
            assert environment_service.restore(eid) is True
        finally:
            environment_service.delete(eid)

    def test_get_not_found_returns_none(self):
        """缺失返回 None。"""
        from app.services.environment_service import environment_service
        assert environment_service.get("nope") is None


# ═══════════════════════════════════════════════════════════
# 四、Message 消息域 Service 委托
# ═══════════════════════════════════════════════════════════
class TestMessageServiceDelegation:
    def test_robot_crud_via_ddd(self):
        """message_service 机器人 CRUD 经 DDD 委托。"""
        from app.services.message_service import message_service

        # 内置机器人可见
        robots = message_service.list_robots()
        platforms = [r["platform"] for r in robots]
        assert "IN_SITE" in platforms
        assert "MAIL" in platforms

        # 创建自定义机器人
        r = message_service.create_robot({
            "name": _mk("robot"), "platform": "CUSTOM",
            "webhook": "https://example.com/hook",
        })
        assert r and r["id"]
        rid = r["id"]
        try:
            got = message_service.get_robot(rid)
            assert got and got["id"] == rid
            assert got["name"] == r["name"]
            # 更新 / 启停
            message_service.update_robot(rid, {"name": "改名机器人"})
            assert message_service.get_robot(rid)["name"] == "改名机器人"
            message_service.set_robot_enable(rid, False)
            assert message_service.get_robot(rid)["enable"] is False
        finally:
            message_service.delete_robot(rid)

    def test_builtin_robot_cannot_create(self):
        """站内信/邮件为内置，不允许创建。"""
        from app.services.message_service import message_service
        with pytest.raises(ValueError):
            message_service.create_robot({"name": "x", "platform": "IN_SITE"})


# ═══════════════════════════════════════════════════════════
# 五、File 文件域 Service 委托
# ═══════════════════════════════════════════════════════════
class TestFileServiceDelegation:
    def test_save_find_delete(self):
        """file_service 保存/检索/删除经 DDD。"""
        from app.services.file_service import file_service
        content = b"Hello DDD migration"
        d = file_service.save_file("migration.txt", content)
        assert d and d["id"]
        fid = d["id"]
        try:
            # 通过磁盘扫描可见
            assert file_service.find_upload_file(fid) is not None
            # 文件可下载（resolve path）
            fname = file_service.find_upload_file(fid)
            assert fname and os.path.exists(file_service.resolve_path(fname))
            # 详情元数据
            meta = file_service.get_file_meta(fid)
            assert meta and "type" in meta and "fileType" in meta
        finally:
            assert file_service.delete_file(fid) is True
            assert file_service.find_upload_file(fid) is None
