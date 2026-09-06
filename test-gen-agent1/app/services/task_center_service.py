# app/services/task_center_service.py
"""任务中心 task-center 业务逻辑层（阶段 C 薄门面接线 · task_center DDD 接入）。

task-center 是横切展示/协调域：既协调 legacy 执行任务队列（来源：
app/tasks.manager 管理的 tasks 队列）也承载「定时任务 schedule」（来源：
test_plan_schedules）。此前编排散落在路由内联 helper 中，后收口为
TaskCenterService 直连 app.tasks.manager / test_plan_repo。

现在 task_center 域的 DDD 门面（`task_center_app_service`）已覆盖对 legacy
队列的协调能力（提交 submit_task / 查询 get_task / 原始列表 list_raw_tasks /
停止/删除/重跑/list_tasks）与定时启停/删除/改 cron。本 Service 收敛为对 DDD
应用门面的**薄委托门面**，仅保留既有方法签名以兼容 app/routers/* 等调用方，
返回结构与重构前一致、对外 API 零回归、可回滚。

> 推荐调用方直接使用 `task_center_app_service`；本类仅作过渡兼容层保留。
"""

from typing import Optional

from app.domain.task_center.application.dto import (
    DeleteSchedulesCommand,
    DeleteTasksCommand,
    EnableSchedulesCommand,
    GetTaskCommand,
    ListRawTasksCommand,
    RerunTaskCommand,
    StopTasksCommand,
    SubmitTaskCommand,
    SwitchSchedulesCommand,
    UpdateCronCommand,
)
from app.domain.task_center.application.task_center_app_service import (
    task_center_app_service as _ddd,
)
from app.logging_config import get_logger

logger = get_logger(__name__)


class TaskCenterService:
    """任务中心服务（DDD 薄门面）。"""

    # ── exec-task（执行任务）── ────────────────────────────

    def stop_tasks(self, ids: list) -> dict:
        """批量停止执行任务。返回 {stopped, failed} 口径。"""
        return _ddd.stop_tasks(StopTasksCommand(ids=list(ids)))

    def delete_tasks(self, ids: list) -> dict:
        """批量删除执行任务。返回 {deleted, failed} 口径。"""
        return _ddd.delete_tasks(DeleteTasksCommand(ids=list(ids)))

    def rerun_task(self, task_id: str) -> dict:
        """重跑单个执行任务。返回 {ok, message, taskId} 口径。"""
        return _ddd.rerun_task(RerunTaskCommand(task_id=task_id))

    async def submit_task(self, name: str, payload: dict):
        """提交命名执行任务（generation.run 等）到后台 legacy 队列。"""
        return await _ddd.submit_task(SubmitTaskCommand(name=name, payload=payload))

    def get_task(self, task_id: str) -> Optional[dict]:
        """按 id 查询执行任务详情（dict 形态）。"""
        return _ddd.get_task(GetTaskCommand(task_id=task_id))

    def list_raw_tasks(self, limit: int = 50) -> list:
        """列出最近执行任务（原始摘要，不做展示态归一）。"""
        return _ddd.list_raw_tasks(ListRawTasksCommand(limit=limit))

    def list_tasks(self) -> list:
        """列出执行任务，并把内部生命周期状态归一为权威大写执行状态。"""
        return _ddd.list_tasks()

    # ── schedule（定时任务）── ─────────────────────────────

    def switch_schedules(self, ids: list) -> dict:
        """切换定时任务启用状态。返回 {switched, failed} 口径。"""
        return _ddd.switch_schedules(SwitchSchedulesCommand(ids=list(ids)))

    def enable_schedules(self, ids: list, enable: bool) -> dict:
        """启用/禁用定时任务。返回 {done, failed} 口径。"""
        return _ddd.enable_schedules(EnableSchedulesCommand(ids=list(ids), enable=enable))

    def delete_schedules(self, ids: list) -> dict:
        """批量删除定时任务。返回 {deleted, failed} 口径。"""
        return _ddd.delete_schedules(DeleteSchedulesCommand(ids=list(ids)))

    def update_schedule_cron(self, ids: list, cron: str) -> dict:
        """批量更新定时任务 cron 表达式。返回 {updated, failed} 口径。"""
        return _ddd.update_cron(UpdateCronCommand(ids=list(ids), cron=cron))


# 模块级单例：router 统一经此访问
task_center_service = TaskCenterService()
