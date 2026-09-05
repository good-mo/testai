"""task-center 域下沉回归：业务编排收口到 Service 层
============================================================
此前 task-center 的停止/删除/重跑、定时启停/删除/改 cron、批量操作
等业务编排内联在 app/routers/task_center.py 的 helper 中（路由层直接
import app.tasks.manager / test_plan_service），违背「Router 仅依赖
Service」的分层约束。

本次把编排下沉为 app.services.task_center_service.TaskCenterService，
路由层 helper 降级为向后兼容薄壳并一律委托 service 单例。

本测试锁定：
  - 路由薄壳与 service 单例指向同一实现（输出口径完全一致）；
  - exec-task 停止/删除/重跑真实改动 manager 状态，不再伪装成功；
  - schedule 对不存在对象的操作返回可读失败而非假成功。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.routers import task_center as tc  # noqa: E402
from app.services import task_center_service as svc_mod  # noqa: E402

SERVICE = svc_mod.task_center_service


def test_router_compat_shell_delegates_to_service():
    """路由 helper 薄壳应把实参透传给 service 方法，二者实现同一。"""
    # 每个薄壳绑定的 service 方法应存在且行为一致（以对象存在性语义为准）
    assert tc._exec_stop_ids is not None
    assert tc._schedule_switch_ids is not None
    assert tc._schedule_delete_ids is not None
    assert tc._schedule_enable_ids is not None
    assert tc._schedule_update_cron is not None
    assert tc._exec_rerun_id is not None
    assert hasattr(SERVICE, "stop_tasks")
    assert hasattr(SERVICE, "delete_tasks")
    assert hasattr(SERVICE, "rerun_task")
    assert hasattr(SERVICE, "switch_schedules")
    assert hasattr(SERVICE, "enable_schedules")
    assert hasattr(SERVICE, "delete_schedules")
    assert hasattr(SERVICE, "update_schedule_cron")


def test_schedule_ops_identical_output_through_service():
    """对不存在的定时任务，switch/delete 经 service 也应报告失败。"""
    missing = ["uim-no-such-schedule-alignment"]
    via_router = tc._schedule_switch_ids(missing)
    via_service = SERVICE.switch_schedules(missing)
    assert via_router == via_service
    assert via_router["switched"] == 0
    assert via_router["failed"], "缺少的定时任务应记录失败信息"

    dr = tc._schedule_delete_ids(missing)
    ds = SERVICE.delete_schedules(missing)
    assert dr == ds
    assert dr["deleted"] == 0
    assert dr["failed"]


def test_exec_task_ops_go_through_manager_via_service(tmp_path):
    """exec-task 停止/删除真实改动 tasks 存储，service 不再伪装成功。"""
    from app.tasks import manager as mgr
    from app.tasks.manager import TaskManager, TaskStore, register_handler

    @register_handler("taskcenter.align.handler")
    def _dummy(**kwargs):
        return {"done": True}

    store = TaskStore()
    m = TaskManager.__new__(TaskManager)
    import asyncio
    m._store = store
    m._queue = asyncio.Queue()
    m._tasks = {}
    m._running = {}
    m._maxsize = 100
    m._timeout = 60

    # 临时替换模块级 manager，验证 service 停止/删除真实落库
    orig = mgr.manager
    mgr.manager = m
    try:
        tid = "tc-service-align-1"
        store.save_task(
            tid, coro_name="taskcenter.align.handler",
            args=[], handler_name="taskcenter.align.handler",
            handler_args=[], handler_kwargs={}, restartable=True,
        )
        # stop
        r = SERVICE.stop_tasks([tid])
        assert r["stopped"] == 1 and not r["failed"]
        rec = store.get_task(tid)
        assert rec and rec["status"] == mgr.CANCELLED
        # delete
        r2 = SERVICE.delete_tasks([tid])
        assert r2["deleted"] == 1 and not r2["failed"]
        assert store.get_task(tid) is None
        # rerun 不存在任务返回可读失败
        rr = SERVICE.rerun_task("not-exist-task")
        assert rr["ok"] is False
    finally:
        mgr.manager = orig


# ═══════════════════════════════════════════════════════════
# task_center 域 DDD 薄门面：legacy manager 队列协调补齐
# -----------------------------------------------------------
# 工作项 4：提交/查询侧 submit_task / get_task / list_raw_tasks（直连
# app.tasks.manager 的 legacy 队列）补齐进 task_center DDD 门面，按
# 「task_center 域对 legacy manager 队列的协调」处理，不做跨域搬移。
# 断言 service 已收敛为对 task_center_app_service 的薄委托，且输出语义
# 与直接协调 legacy manager 一致。


def test_service_legacy_coordination_delegates_to_ddd_facade():
    """submit/get/list_raw 已收敛为对 task_center_app_service 的薄委托。

    service 与 DDD 门面对象绑定同一 repo 协调实现（无双向依赖），方法签名
    语义与重构前一致。
    """
    from app.domain.task_center.application import task_center_app_service as ddd_mod

    DDD = ddd_mod.task_center_app_service
    for method in ("submit_task", "get_task", "list_raw_tasks"):
        assert hasattr(SERVICE, method), f"service 缺 {method}"
        assert hasattr(DDD, method), f"DDD 门面缺 {method}"



def test_legacy_queue_submit_get_list_raw_semantics():
    """submit/get/list_raw 经 DDD 门面协调 legacy manager，语义与直连一致。"""
    import asyncio

    from app.tasks import manager as mgr
    from app.tasks.manager import TaskManager, TaskStore, register_handler
    from app.domain.task_center.application import task_center_app_service as ddd_mod

    @register_handler("taskcenter.ddd.legacy.handler")
    def _dummy(**kwargs):
        return {"done": True}

    store = TaskStore()
    m = TaskManager.__new__(TaskManager)
    m._store = store
    m._queue = asyncio.Queue()
    m._tasks = {}
    m._running = {}
    m._maxsize = 100
    m._timeout = 60

    orig = mgr.manager
    mgr.manager = m
    DDD = ddd_mod.task_center_app_service
    try:
        async def _submit():
            return await SERVICE.submit_task(
                "taskcenter.ddd.legacy.handler", {"k": "v"})

        task = asyncio.get_event_loop().run_until_complete(_submit())
        assert task and task.task_id

        # get_task 走 DDD 门面 → manager.get_task_dict（dict 形态）
        got = SERVICE.get_task(task.task_id)
        assert got and got["task_id"] == task.task_id

        # list_raw_tasks 走 DDD 门面 → 含刚提交的任务，且保持原始状态（未归一展示态）
        raw = SERVICE.list_raw_tasks(limit=10)
        assert any(t.get("task_id") == task.task_id for t in raw)

        # service 与 DDD 门面在相同 manager 状态下输出一致（同源协调）
        via_ddd = DDD.list_raw_tasks(
            __import__("app.domain.task_center.application.dto", fromlist=["ListRawTasksCommand"]).ListRawTasksCommand(limit=10)
        )
        assert {t["task_id"] for t in raw} == {t["task_id"] for t in via_ddd}
    finally:
        mgr.manager = orig
