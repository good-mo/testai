"""Issue #10 / #480: Task Manager SQLite 共享队列 + 可恢复任务注册的回归测试。

覆盖：
  1. 可恢复任务（named handler）跨进程认领
  2. 进程重启后可恢复任务自动重新入队执行
  3. 匿名协程任务重启后被正确标记 failed
  4. 原子认领（并发安全）
  5. 旧版 API 向后兼容

说明：
  DB 访问统一经 Database 连接池（tasks.db 路由到共享 tga.db，见 app.db 的
  _LEGACY_DB_MAP / app.core.database）。每个用例运行前清空 tasks 表，
  保证用例间互不干扰（不依赖 tmp_path 的独立库隔离）。
"""
import asyncio
import json
import sqlite3
import time

import pytest

from app.tasks import manager as m


@pytest.fixture(autouse=True)
def _clean_tasks_table():
    """每个用例运行前后清空共享 tga.db 的 tasks 表，避免状态残留。"""
    conn = m.TaskStore()._get_conn()
    conn.execute("DELETE FROM tasks")
    conn.commit()
    yield
    try:
        conn.execute("DELETE FROM tasks")
        conn.commit()
    except Exception:
        pass


def _make_store():
    """创建一个 TaskStore 实例（连接由 Database 统一管理）。"""
    return m.TaskStore()


# ════════════════════════════════════════════════════════════
# 1. TaskStore schema 迁移
# ════════════════════════════════════════════════════════════

class TestSchemaMigration:
    """新列应从旧表结构自动补齐。"""

    def test_new_columns_added_to_old_table(self):
        conn = m.TaskStore()._get_conn()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        for col in ("handler_name", "handler_args", "handler_kwargs",
                    "restartable", "claimed_by"):
            assert col in cols, f"列 {col} 应被自动补齐"

    def test_restartable_task_persisted(self):
        store = _make_store()
        store.save_task(
            "rest_task", "my_handler", [],
            handler_name="my_handler",
            handler_args=[{"key": "value"}],
            handler_kwargs={"extra": True},
            restartable=True,
        )
        rec = store.get_task("rest_task")
        assert rec["restartable"] == 1
        assert rec["handler_name"] == "my_handler"
        assert json.loads(rec["handler_args"]) == [{"key": "value"}]
        assert json.loads(rec["handler_kwargs"]) == {"extra": True}
        store.close()


# ════════════════════════════════════════════════════════════
# 2. Handler 注册与提交
# ════════════════════════════════════════════════════════════

class TestHandlerRegistry:

    def test_register_and_get_handler(self):
        @m.register_handler("test.handler")
        async def my_handler(data):
            return {"echo": data}

        handler = m.get_handler("test.handler")
        assert handler is not None
        assert handler is my_handler

    def test_duplicate_register_overwrites(self):
        @m.register_handler("test.dup")
        async def h1():
            return 1

        @m.register_handler("test.dup")
        async def h2():
            return 2

        handler = m.get_handler("test.dup")
        assert handler is h2

    def test_get_unregistered_returns_none(self):
        assert m.get_handler("does.not.exist") is None

    def test_list_handlers_sorted(self):
        @m.register_handler("test.b")
        def _hb():
            pass

        @m.register_handler("test.a")
        def _ha():
            pass

        handlers = m.list_handlers()
        assert "test.a" in handlers
        assert "test.b" in handlers
        assert handlers.index("test.a") < handlers.index("test.b")


class TestSubmitNamed:
    """submit_named 应支持可恢复任务提交。"""

    def test_submit_named_success(self):
        async def scenario():
            @m.register_handler("test.echo")
            async def echo(data):
                return {"echo": data}

            tm = m.TaskManager(maxsize=10, timeout=5)
            tm._store = _make_store()

            task = await tm.submit_named("test.echo", {"msg": "hi"})
            assert task.task_id
            assert task.restartable is True
            assert task.handler_name == "test.echo"

            # 验证持久化
            stored = tm._store.get_task(task.task_id)
            assert stored["restartable"] == 1
            assert stored["handler_name"] == "test.echo"

            tm.start(num_workers=1)
            await asyncio.sleep(0.5)
            t = tm.get_task(task.task_id)
            assert t.status == m.SUCCESS
            assert t.result == {"echo": {"msg": "hi"}}
            await tm.stop()

        asyncio.run(scenario())

    def test_submit_named_unregistered_raises(self):
        async def scenario():
            tm = m.TaskManager(maxsize=10, timeout=5)
            tm._store = _make_store()

            with pytest.raises(ValueError, match="未注册"):
                await tm.submit_named("not.registered", "data")

        asyncio.run(scenario())

    def test_submit_named_sync_handler(self):
        """sync handler 也应能通过 submit_named 执行。"""
        async def scenario():
            @m.register_handler("test.sync")
            def add(a, b):
                return a + b

            tm = m.TaskManager(maxsize=10, timeout=5)
            tm._store = _make_store()

            task = await tm.submit_named("test.sync", 3, 4)
            tm.start(num_workers=1)
            await asyncio.sleep(0.5)
            t = tm.get_task(task.task_id)
            assert t.status == m.SUCCESS
            assert t.result == 7
            await tm.stop()

        asyncio.run(scenario())


# ════════════════════════════════════════════════════════════
# 3. 跨进程认领与重启恢复
# ════════════════════════════════════════════════════════════

class TestRestartRecovery:
    """进程重启后的任务恢复行为。"""

    def test_restartable_task_survives_restart(self):
        """可恢复任务在重启后应被新 worker 重新执行。"""
        async def scenario():
            @m.register_handler("test.slow")
            async def slow(data):
                await asyncio.sleep(0.3)
                return {"slow": data}

            # 进程 A 提交任务但未执行
            tm_a = m.TaskManager(maxsize=10, timeout=5)
            tm_a._store = _make_store()
            task = await tm_a.submit_named("test.slow", "payload")
            task_id = task.task_id

            # 进程 B 启动，应能恢复并执行 pending 的可恢复任务
            tm_b = m.TaskManager(maxsize=10, timeout=5)
            tm_b._store = _make_store()
            tm_b.start(num_workers=1)

            await asyncio.sleep(1.0)
            t = tm_b.get_task(task_id)
            assert t.status == m.SUCCESS
            assert t.result == {"slow": "payload"}
            await tm_b.stop()

        asyncio.run(scenario())

    def test_anonymous_task_marked_failed_on_restart(self):
        """匿名协程任务（非 restartable）重启后应被标记为 failed。"""
        async def scenario():
            async def anonymous():
                return "never runs"

            tm_a = m.TaskManager(maxsize=10, timeout=5)
            tm_a._store = _make_store()
            task = await tm_a.submit(anonymous)
            task_id = task.task_id
            assert task.restartable is False

            # 模拟进程重启
            tm_b = m.TaskManager(maxsize=10, timeout=5)
            tm_b._store = _make_store()
            tm_b.start(num_workers=1)
            await asyncio.sleep(0.3)

            t = tm_b.get_task(task_id)
            assert t.status == m.FAILED
            assert t.error
            await tm_b.stop()

        asyncio.run(scenario())

    def test_running_task_marked_failed_on_restart(self):
        """running 状态任务（无论是否可恢复）重启后应标记 failed。"""
        async def scenario():
            @m.register_handler("test.hang")
            async def hang(data):
                await asyncio.sleep(10)
                return data

            tm_a = m.TaskManager(maxsize=10, timeout=5)
            tm_a._store = _make_store()
            task = await tm_a.submit_named("test.hang", "x")
            task_id = task.task_id

            # 标记为 running 状态（模拟任务正在执行时进程崩溃）
            tm_a._store.update_status(task_id, m.RUNNING, started_at=time.time())

            # 新进程启动
            tm_b = m.TaskManager(maxsize=10, timeout=5)
            tm_b._store = _make_store()
            tm_b.start(num_workers=1)
            await asyncio.sleep(0.3)

            t = tm_b.get_task(task_id)
            assert t.status == m.FAILED
            assert "中断" in (t.error or "")
            await tm_b.stop()

        asyncio.run(scenario())


class TestCrossProcessClaim:
    """多个 worker 进程应能认领同一个 SQLite 队列中的 pending 任务。"""

    def test_second_process_can_execute_task(self):
        """进程 A 提交任务，进程 B 应能执行。"""
        async def scenario():
            @m.register_handler("test.echo2")
            async def echo2(data):
                return {"ok": data}

            # 进程 A 只提交，不启动 worker
            tm_a = m.TaskManager(maxsize=10, timeout=5)
            tm_a._store = _make_store()
            task = await tm_a.submit_named("test.echo2", "from-A")
            task_id = task.task_id

            # 进程 B 启动 worker，应从 SQLite 中认领并执行
            tm_b = m.TaskManager(maxsize=10, timeout=5)
            tm_b._store = _make_store()
            tm_b.start(num_workers=1)
            await asyncio.sleep(0.8)

            t = tm_b.get_task(task_id)
            assert t.status == m.SUCCESS
            assert t.result == {"ok": "from-A"}
            await tm_b.stop()

        asyncio.run(scenario())

    def test_atomic_claim_no_double_execution(self):
        """多个 worker 同时认领不应导致同一任务被执行两次。"""
        store = _make_store()
        m.register_handler("test.atomic")
        store.save_task(
            "task1", "test.atomic", [],
            handler_name="test.atomic", restartable=True,
        )

        # 两个 store 同时认领，应只有一个成功
        store2 = _make_store()
        rec1 = store.claim_next_pending(worker_id="w1")
        rec2 = store2.claim_next_pending(worker_id="w2")

        assert rec1 is not None, "第一个 worker 应能认领任务"
        assert rec2 is None, "第二个 worker 不应再认领已被认领的任务"
        assert rec1["task_id"] == "task1"
        assert rec1["claimed_by"] == "w1"

        store.close()
        store2.close()


# ════════════════════════════════════════════════════════════
# 4. 向后兼容
# ════════════════════════════════════════════════════════════

class TestBackwardCompat:
    """旧版 API 应保持可用。"""

    def test_mark_abandoned_returns_failed_tasks(self):
        """mark_abandoned 应返回被标记为 failed 的任务。"""
        store = _make_store()
        store.save_task("anon1", "coro", [])
        store.save_task("done1", "coro", [])
        store.update_status("done1", m.SUCCESS)

        swept = store.mark_abandoned()
        ids = {r["task_id"] for r in swept}
        assert ids == {"anon1"}
        assert store.get_task("anon1")["status"] == m.FAILED
        assert store.get_task("done1")["status"] == m.SUCCESS
        store.close()

    def test_anonymous_submit_still_works(self):
        """旧版 submit(coro, *args) 仍应正常工作。"""
        async def scenario():
            async def double(x):
                return x * 2

            tm = m.TaskManager(maxsize=10, timeout=5)
            tm._store = _make_store()
            task = await tm.submit(double, 21)
            assert task.restartable is False

            tm.start(num_workers=1)
            await asyncio.sleep(0.5)
            t = tm.get_task(task.task_id)
            assert t.status == m.SUCCESS
            assert t.result == 42
            await tm.stop()

        asyncio.run(scenario())

    def test_recover_pending_deprecated_alias(self):
        """recover_pending 旧方法应仍可用。"""
        store = _make_store()
        store.save_task("p1", "coro", [])
        store.save_task("s1", "coro", [])
        store.update_status("s1", m.SUCCESS)

        pending = store.recover_pending()
        assert len(pending) == 1
        assert pending[0]["task_id"] == "p1"
        store.close()


# ════════════════════════════════════════════════════════════
# 5. 应用上下文
# ════════════════════════════════════════════════════════════

class TestAppContext:
    """set_app_context / get_app_context 全局上下文。"""

    def test_set_and_get(self):
        m.set_app_context("test_key", {"val": 42})
        assert m.get_app_context("test_key") == {"val": 42}

    def test_get_default(self):
        assert m.get_app_context("nonexistent", "default") == "default"
        assert m.get_app_context("nonexistent") is None
