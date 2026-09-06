"""任务中心应用服务（协调 runs + test_plan）。

task-center 是横切展示/协调域：既协调 legacy 执行任务队列（`app.tasks.manager`
的提交/查询/停止/删除/重跑/列表），也协调定时任务（test_plan_schedules）。
这些能力均收口在 task_center 域门面内作为「对 legacy 队列的协调」处理，不做
跨域搬移。
"""
from __future__ import annotations

from app.domain.task_center.application.dto import (
    DeleteSchedulesCommand,
    DeleteTasksCommand,
    EnableSchedulesCommand,
    GetTaskCommand,
    ListRawTasksCommand,
    ListTasksCommand,
    RerunTaskCommand,
    StopTasksCommand,
    SubmitTaskCommand,
    SwitchSchedulesCommand,
    UpdateCronCommand,
)
from app.domain.task_center.infrastructure.task_center_repository_impl import (
    TaskCenterRepoAdapter,
)


class TaskCenterAppService:
    """任务中心用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or TaskCenterRepoAdapter()

    # ── exec-task（执行任务 · legacy 队列协调）── ──────────
    def stop_tasks(self, cmd: StopTasksCommand) -> dict:
        return self._repo.stop_tasks(cmd.ids)

    def delete_tasks(self, cmd: DeleteTasksCommand) -> dict:
        return self._repo.delete_tasks(cmd.ids)

    def rerun_task(self, cmd: RerunTaskCommand) -> dict:
        return self._repo.rerun_task(cmd.task_id)

    async def submit_task(self, cmd: SubmitTaskCommand):
        """提交命名执行任务到后台 legacy 队列（返回 manager.Task）。"""
        return await self._repo.submit_task(cmd.name, cmd.payload)

    def get_task(self, cmd: GetTaskCommand):
        """按 id 查询执行任务详情（dict 形态）。"""
        return self._repo.get_task(cmd.task_id)

    def list_raw_tasks(self, cmd: ListRawTasksCommand) -> list:
        """列出最近执行任务（原始摘要，不做展示态归一）。"""
        return self._repo.list_raw_tasks(cmd.limit)

    def list_tasks(self, cmd: ListTasksCommand = None) -> list:
        return self._repo.list_tasks()

    # ── schedule（定时任务）── ─────────────────────────────
    def switch_schedules(self, cmd: SwitchSchedulesCommand) -> dict:
        return self._repo.switch_schedules(cmd.ids)

    def enable_schedules(self, cmd: EnableSchedulesCommand) -> dict:
        return self._repo.enable_schedules(cmd.ids, cmd.enable)

    def delete_schedules(self, cmd: DeleteSchedulesCommand) -> dict:
        return self._repo.delete_schedules(cmd.ids)

    def update_cron(self, cmd: UpdateCronCommand) -> dict:
        return self._repo.update_schedule_cron(cmd.ids, cmd.cron)


task_center_app_service = TaskCenterAppService()
task_center_service = task_center_app_service
