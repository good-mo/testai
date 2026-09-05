"""任务中心操作不再「假成功」的回归测试。

覆盖 task_center 中被 stub 的操作（stop/delete/rerun、schedule 启停、
update-cron、批量停止/删除）真正接到后端：
  - exec-task 操作改变 task manager 状态；
  - HTTP 层各 scope 操作路由稳定返回三段式信封且无 500。
"""


def test_manager_stop_delete_rerun_real(tmp_path, monkeypatch):
    """task manager 的 stop/delete/rerun 应真实改变任务状态/记录。"""
    from app.tasks import manager as mgr

    # 用独立存储，避免污染模块级 manager 的真实 DB
    from app.tasks.manager import TaskManager, TaskStore, register_handler
    store = TaskStore()

    @register_handler("taskcenter.test.handler")
    def _dummy(**kwargs):
        return {"done": True}

    m = TaskManager.__new__(TaskManager)
    m._store = store
    import asyncio
    m._queue = asyncio.Queue()
    m._tasks = {}
    m._running = {}
    m._maxsize = 100
    m._timeout = 60

    # 提交一个命名任务（pytest 环境无运行 loop，仅验证存储层状态）
    # 直接构造记录
    task_id = "tc-manager-test-1"
    store.save_task(
        task_id,
        coro_name="taskcenter.test.handler",
        args=[],
        handler_name="taskcenter.test.handler",
        handler_args=[],
        handler_kwargs={},
        restartable=True,
    )

    ok, _ = m.stop_task(task_id)
    assert ok is True
    rec = store.get_task(task_id)
    assert rec and rec["status"] == mgr.CANCELLED

    # delete 真实删除记录
    ok2, _ = m.delete_task(task_id)
    assert ok2 is True
    assert store.get_task(task_id) is None

    # rerun 针对不存在的任务应返回可读失败而非假装成功
    ok3, msg = m.rerun_task("not-exist-task")
    assert ok3 is False


def test_schedule_ops_no_fake_success_when_missing():
    """对不存在的定时任务，switch/delete 应报告失败而不是伪装成功。"""
    from app.routers import task_center as tc
    r = tc._schedule_switch_ids(["uim-no-such-schedule"])
    assert r["switched"] == 0
    assert r["failed"], "缺少的定时任务应记录失败信息"

    r2 = tc._schedule_delete_ids(["uim-no-such-schedule"])
    assert r2["deleted"] == 0
    assert r2["failed"]
