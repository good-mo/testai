# app/models/task_center.py
"""任务中心（task_center）域 Pydantic 请求体模型。

字段自 `app/routers/task_center.py` 中 `_ids_from_body` / read_body
实际使用的请求体归纳。task-center 为横切操作域：既承载「执行任务
exec-task」（停止/删除/重跑）也承载「定时任务 schedule」（启停/删除/
批量切换/批量更新 cron），请求体统一为「ID 列表 + 可选 cron」形态。

兼容前端多种传参别名（selectIds/ids/taskIds/scheduleIds/id/taskId/
scheduleId），统一经 `effective_ids` 归一提取；默认 `extra: allow`
避免遗漏新增字段导致 400。
"""

from typing import Any, List

from pydantic import BaseModel, Field

# 批量 ID 的前端别名（按优先级匹配）
_ID_KEYS = ("selectIds", "ids", "taskIds", "scheduleIds", "excludeIds")
_ID_SINGLE_KEYS = ("id", "taskId", "scheduleId")


class TaskCenterIdsBody(BaseModel):
    """任务中心通用批量操作请求体（exec-task/schedule 停止删除切换等）。

    兼容字段：
      - 列表形态：selectIds / ids / taskIds / scheduleIds / excludeIds
      - 单值形态：id / taskId / scheduleId（含裸字符串/单元素列表）
    """

    selectIds: Any = Field(None, description="待选 ID 列表（列表或单值）")
    ids: Any = Field(None, description="ID 列表")
    taskIds: Any = Field(None, description="执行任务 ID 列表")
    scheduleIds: Any = Field(None, description="定时任务 ID 列表")
    excludeIds: Any = Field(None, description="需排除的 ID 列表")
    id: Any = Field(None, description="单个任务/定时任务 ID")
    taskId: Any = Field(None, description="单个执行任务 ID（别名）")
    scheduleId: Any = Field(None, description="单个定时任务 ID（别名）")

    @property
    def effective_ids(self) -> List[str]:
        """按优先级归一提取 ID 列表（对齐旧 `_ids_from_body` 逻辑）。"""
        for key in _ID_KEYS:
            v = getattr(self, key)
            if isinstance(v, list):
                return [str(x) for x in v if x]
            if v:
                return [str(v)]
        for key in _ID_SINGLE_KEYS:
            v = getattr(self, key)
            if v:
                if isinstance(v, list):
                    return [str(x) for x in v if x]
                return [str(v)]
        return []

    model_config = {"extra": "allow"}


class TaskScheduleCronBody(TaskCenterIdsBody):
    """批量更新定时任务 cron 的请求体（含 cron 表达式）。"""

    cron: str = Field("", description="cron 表达式（5 段或 6 段）")

    @property
    def effective_cron(self) -> str:
        return (self.cron or "").strip()

    model_config = {"extra": "allow"}


__all__ = [
    "TaskCenterIdsBody",
    "TaskScheduleCronBody",
]
