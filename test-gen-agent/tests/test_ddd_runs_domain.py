"""DDD 任务运行（TaskCenter / Infrastructure 共享内核）试点域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：任务状态机非法流转、终态守卫、失败重跑。
  2. 应用服务全链路（对接真实 task_repo 存储）。
"""
import uuid

import pytest

from app.domain.common.exceptions import DomainValidationError, InvariantViolation
from app.domain.runs.application.dto import (
    CompleteTaskCommand,
    EnqueueTaskCommand,
    StartTaskCommand,
)
from app.domain.runs.application.run_app_service import RunAppService, run_app_service
from app.domain.runs.domain.entities.task import Task
from app.domain.runs.domain.value_objects.task_status import (
    TaskStatus,
    TaskStatusEnum,
)

TAG = "dddrun"


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:6]}"


def _task(**kw):
    kw.setdefault("task_id", _mk())
    return Task(**kw)


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需数据库）
# ═══════════════════════════════════════════════════════════
class TestTaskStatus:
    def test_normalize(self):
        assert str(TaskStatus("RUNNING")) == "running"
        with pytest.raises(DomainValidationError):
            TaskStatus("does_not_exist")

    def test_terminal(self):
        assert TaskStatus(TaskStatusEnum.SUCCESS.value).terminal
        assert TaskStatus(TaskStatusEnum.CANCELLED.value).terminal
        assert not TaskStatus(TaskStatusEnum.PENDING.value).terminal


class TestTaskAggregate:
    def test_full_lifecycle(self):
        t = _task()
        t.start("worker")
        assert str(t.status) == "running"
        t.succeed({"ok": True})
        assert str(t.status) == "success" and t.terminal

    def test_terminal_guard(self):
        t = _task()
        t.start("worker")
        t.succeed()
        with pytest.raises(InvariantViolation):
            t.start("w2")

    def test_illegal_transition(self):
        t = _task()
        with pytest.raises(InvariantViolation):
            t.fail("from pending directly not allowed unless status==pending allowed")  # pending->failed 不允许
        # pending 直接 fail 应被守卫（仅 running 可 fail，pending 仅本实现特例）
        # 实际: pending -> fail 走 _transit(failed)，检查矩阵，pending 不允许 -> failed
        assert str(t.status) == "pending"

    def test_requeue_after_failure(self):
        t = _task()
        t.start("worker")
        t.fail("boom")
        assert str(t.status) == "failed"
        t.requeue()
        assert str(t.status) == "pending"

    def test_cancel(self):
        t = _task()
        t.cancel()  # pending -> cancelled
        assert str(t.status) == "cancelled"


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（对接真实 task_repo）
# ═══════════════════════════════════════════════════════════
class TestRunAppService:
    def test_enqueue_start_success(self):
        d = run_app_service.enqueue(EnqueueTaskCommand(coro_name="gen_case"))
        assert d["status"] == "pending"
        run_app_service.start(StartTaskCommand(task_id=d["task_id"], worker="w"))
        assert run_app_service.get(d["task_id"])["status"] == "running"
        run_app_service.complete(CompleteTaskCommand(
            task_id=d["task_id"], status="success", result={"ok": 1}))
        assert run_app_service.get(d["task_id"])["status"] == "success"

    def test_failed_requeue(self):
        svc = RunAppService()
        d = svc.enqueue(EnqueueTaskCommand(coro_name="gen_case"))
        svc.start(StartTaskCommand(task_id=d["task_id"], worker="w"))
        svc.complete(CompleteTaskCommand(task_id=d["task_id"], status="failed", error="e"))
        assert svc.get(d["task_id"])["status"] == "failed"
        svc.requeue(d["task_id"])
        assert svc.get(d["task_id"])["status"] == "pending"
