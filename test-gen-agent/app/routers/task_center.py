# app/routers/task_center.py
"""横切模块：任务中心 task-center 兼容路由。

迁移自 app/adapters/domains/_task_center.py，保持原 TestPilot 兼容路径与占位 OK 实现不变。
"""

from fastapi import APIRouter, Request

from app.core.response import ok, page_result, read_body
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-task-center"])

from app.domain.task_center.application.dto import (
    DeleteSchedulesCommand,
    DeleteTasksCommand,
    EnableSchedulesCommand,
    RerunTaskCommand,
    StopTasksCommand,
    SwitchSchedulesCommand,
    UpdateCronCommand,
)
from app.domain.task_center.application.task_center_app_service import (
    task_center_app_service as _svc,
)
from app.models.task_center import TaskCenterIdsBody, TaskScheduleCronBody

# ═══════════════════════════════════════════════════════════════════════
# 任务中心操作的真实后端接线
#
# 此前的 stop/delete/rerun、schedule 启停/update-cron、批量停止/删除等大量
# 操作路由直接 ``return ok()`` 假成功 —— 前端点「停止/删除」提示成功但后端
# 毫无动作。下面统一接到平台真实数据源：
#   - exec-task（执行任务）→ app.tasks.manager（内存 + SQLite 持久化 tasks 表）
#   - schedule（定时任务） → test_plan_schedules（平台唯一的真实定时任务存储）
# 操作对象不存在时返回可读的失败信息，而非伪装成功。
#
# 业务编排已下沉至 task_center 域 DDD 应用服务 `task_center_app_service`；
# 路由层仅做参数归一（HTTP 关注点），下方 *_ids helper 保留为向后兼容薄壳，
# 一律委托 DDD 应用门面执行（阶段 B router 直连）。
# ───────────────────────────────────────────────────────────────────────


def _ids_from_body(body: dict) -> list:
    """从批量操作请求体归一提取 id 列表（selectIds/ids/taskIds/id 等）。

    字段语义统一收敛至 TaskCenterIdsBody（类型化请求体契约），
    逻辑与旧内联提取完全等价（含单值/多值/别名兼容）。
    """
    if not isinstance(body, dict):
        return []
    return TaskCenterIdsBody.model_validate(body).effective_ids


def _cron_from_body(body: dict) -> str:
    """从批量更新 cron 请求体归一提取 cron 表达式。"""
    if not isinstance(body, dict):
        return ""
    return TaskScheduleCronBody.model_validate(body).effective_cron


def _query_ids(request: Request) -> list:
    """从 GET 查询串读取逗号分隔的 id 列表。"""
    try:
        q = request.query_params
        raw = q.get("id") or q.get("taskId") or q.get("scheduleId") or ""
        return [x for x in str(raw).split(",") if x]
    except Exception:  # noqa: BLE001
        return []


def _query_one(request: Request) -> str:
    """从 GET 查询串读取单个 id。"""
    try:
        q = request.query_params
        return q.get("id") or q.get("taskId") or q.get("scheduleId") or ""
    except Exception:  # noqa: BLE001
        return ""


def _exec_stop_ids(ids: list) -> dict:
    """[compat 薄壳] 批量停止执行任务，委托 task_center_app_service。"""
    return _svc.stop_tasks(StopTasksCommand(ids=list(ids)))


def _exec_delete_ids(ids: list) -> dict:
    """[compat 薄壳] 批量删除执行任务，委托 task_center_app_service。"""
    return _svc.delete_tasks(DeleteTasksCommand(ids=list(ids)))


def _exec_rerun_id(tid: str) -> dict:
    """[compat 薄壳] 重跑单个任务，委托 task_center_app_service。"""
    return _svc.rerun_task(RerunTaskCommand(task_id=tid))


def _schedule_switch_ids(ids: list) -> dict:
    """[compat 薄壳] 切换定时任务启用状态，委托 task_center_app_service。"""
    return _svc.switch_schedules(SwitchSchedulesCommand(ids=list(ids)))


def _schedule_enable_ids(ids: list, enable: bool) -> dict:
    """[compat 薄壳] 启用/禁用定时任务，委托 task_center_app_service。"""
    return _svc.enable_schedules(EnableSchedulesCommand(ids=list(ids), enable=enable))


def _schedule_delete_ids(ids: list) -> dict:
    """[compat 薄壳] 批量删除定时任务，委托 task_center_app_service。"""
    return _svc.delete_schedules(DeleteSchedulesCommand(ids=list(ids)))


def _schedule_update_cron(ids: list, cron: str) -> dict:
    """[compat 薄壳] 批量更新定时 cron，委托 task_center_app_service。"""
    return _svc.update_cron(UpdateCronCommand(ids=list(ids), cron=cron))


@router.post("/project/task-center/exec-task/batch-delete")
async def proj_task_center_batch_delete_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_delete_ids(ids)
    return ok(result)

@router.post("/project/task-center/exec-task/batch-stop")
async def proj_task_center_batch_stop_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.post("/project/task-center/exec-task/item/batch-stop")
async def proj_task_center_item_batch_stop_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.post("/project/task-center/schedule/batch-disable")
async def proj_task_center_schedule_batch_disable_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _schedule_enable_ids(ids, False)
    return ok(result)

@router.post("/project/task-center/schedule/batch-enable")
async def proj_task_center_schedule_batch_enable_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _schedule_enable_ids(ids, True)
    return ok(result)

@router.post("/project/task-center/schedule/update-cron")
async def proj_task_center_schedule_update_cron_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    cron = _cron_from_body(body)
    result = _schedule_update_cron(ids, cron)
    return ok(result)

@router.post("/project/task-center/exec-task/statistics")
def proj_task_center_statistics_post(request: Request):
    """项目任务中心任务统计（POST兼容）。"""
    return ok([])

@router.get("/project/task-center/exec-task/page")
def project_task_center_exec_task_page():
    """项目任务中心-执行任务分页。"""
    return page_result([], len([]), current=1, page_size=10)

@router.get("/project/task-center/exec-task/item/page")
def project_task_center_exec_task_item_page():
    """项目任务中心-任务项分页。"""
    return page_result([], len([]), current=1, page_size=10)

@router.get("/project/task-center/exec-task/item/order")
def project_task_center_exec_task_item_order():
    """项目任务中心-任务项排序。"""
    return ok([])

@router.get("/project/task-center/exec-task/statistics")
def project_task_center_exec_task_statistics():
    """项目任务中心-任务统计。"""
    return ok([])

@router.get("/project/task-center/exec-task/item/stop")
async def project_task_center_exec_task_item_stop(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.get("/project/task-center/exec-task/stop")
async def project_task_center_exec_task_stop(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.get("/project/task-center/exec-task/rerun")
async def project_task_center_exec_task_rerun(request: Request):
    """操作接线到真实后端。"""
    tid = _query_one(request)
    result = _exec_rerun_id(tid)
    return ok(result)

@router.get("/project/task-center/exec-task/delete")
async def project_task_center_exec_task_delete(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _exec_delete_ids(ids)
    return ok(result)

@router.get("/project/task-center/exec-task/batch/page")
def project_task_center_exec_task_batch_page():
    """项目任务中心-批量分页。"""
    return page_result([], len([]), current=1, page_size=10)

@router.get("/project/task-center/exec-task/batch-stop")
async def project_task_center_exec_task_batch_stop(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.get("/project/task-center/exec-task/batch-delete")
async def project_task_center_exec_task_batch_delete(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_delete_ids(ids)
    return ok(result)

@router.get("/project/task-center/exec-task/item/batch-stop")
async def project_task_center_exec_task_item_batch_stop(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.get("/project/task-center/exec-task/item/batch-delete")
async def project_task_center_exec_task_item_batch_delete(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_delete_ids(ids)
    return ok(result)

@router.get("/project/task-center/schedule/page")
def project_task_center_schedule_page():
    """项目任务中心-定时任务分页。"""
    return page_result([], len([]), current=1, page_size=10)

@router.get("/project/task-center/schedule/delete")
async def project_task_center_schedule_delete(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _schedule_delete_ids(ids)
    return ok(result)

@router.get("/project/task-center/schedule/switch")
async def project_task_center_schedule_switch(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _schedule_switch_ids(ids)
    return ok(result)

@router.get("/project/task-center/schedule/batch-enable")
async def project_task_center_schedule_batch_enable(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _schedule_enable_ids(ids, True)
    return ok(result)

@router.get("/project/task-center/schedule/batch-disable")
async def project_task_center_schedule_batch_disable(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _schedule_enable_ids(ids, False)
    return ok(result)

@router.get("/project/task-center/schedule/update-cron")
async def project_task_center_schedule_update_cron(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    cron = _cron_from_body(body)
    result = _schedule_update_cron(ids, cron)
    return ok(result)

@router.get("/project/task-center/resource-pool/options")
def project_task_center_resource_pool_options():
    """项目任务中心-资源池选项。"""
    return ok([])

@router.get("/project/task-center/exec-task/delete/{task_id}")
@router.post("/project/task-center/exec-task/delete/{task_id}")
def project_task_center_exec_delete_path(task_id):
    """操作接线到真实后端。"""
    result = _exec_delete_ids([task_id])
    return ok(result)

@router.get("/project/task-center/exec-task/item/stop/{task_id}/{item_id}")
@router.post("/project/task-center/exec-task/item/stop/{task_id}/{item_id}")
def project_task_center_exec_item_stop_path(task_id, item_id):
    """操作接线到真实后端。"""
    result = _exec_stop_ids([task_id])
    return ok(result)

@router.get("/project/task-center/exec-task/rerun/{task_id}")
@router.post("/project/task-center/exec-task/rerun/{task_id}")
def project_task_center_exec_rerun_path(task_id):
    """操作接线到真实后端。"""
    result = _exec_rerun_id(task_id)
    return ok(result)

@router.get("/project/task-center/exec-task/stop/{task_id}")
@router.post("/project/task-center/exec-task/stop/{task_id}")
def project_task_center_exec_stop_path(task_id):
    """操作接线到真实后端。"""
    result = _exec_stop_ids([task_id])
    return ok(result)

@router.get("/project/task-center/schedule/delete/{schedule_id}")
@router.post("/project/task-center/schedule/delete/{schedule_id}")
def project_task_center_schedule_delete_path(schedule_id):
    """操作接线到真实后端。"""
    result = _schedule_delete_ids([schedule_id])
    return ok(result)

@router.get("/project/task-center/schedule/switch/{schedule_id}")
@router.post("/project/task-center/schedule/switch/{schedule_id}")
def project_task_center_schedule_switch_path(schedule_id):
    """操作接线到真实后端。"""
    result = _schedule_switch_ids([schedule_id])
    return ok(result)

@router.get("/project/task-center/exec-task/item/stop/{id}")
@router.post("/project/task-center/exec-task/item/stop/{id}")
def project_task_item_stop_single_path(id):
    """操作接线到真实后端。"""
    result = _exec_stop_ids([id])
    return ok(result)

@router.get("/project/task-center/page")
def project_task_center_page(request: Request):
    """项目任务中心分页列表。"""
    tasks = _svc.list_tasks()
    return ok({
        "list": tasks,
        "total": len(tasks),
    })

@router.get("/project/task-center/stop/{task_id}")
def project_task_center_stop(task_id):
    """操作接线到真实后端。"""
    result = _exec_stop_ids([task_id])
    return ok(result)

@router.post("/organization/task-center/exec-task/batch-delete")
async def org_task_center_batch_delete_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_delete_ids(ids)
    return ok(result)

@router.post("/organization/task-center/exec-task/batch-stop")
async def org_task_center_batch_stop_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.post("/organization/task-center/exec-task/item/batch-stop")
async def org_task_center_item_batch_stop_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.post("/organization/task-center/schedule/batch-disable")
async def org_task_center_schedule_batch_disable_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _schedule_enable_ids(ids, False)
    return ok(result)

@router.post("/organization/task-center/schedule/batch-enable")
async def org_task_center_schedule_batch_enable_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _schedule_enable_ids(ids, True)
    return ok(result)

@router.post("/organization/task-center/schedule/update-cron")
async def org_task_center_schedule_update_cron_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    cron = _cron_from_body(body)
    result = _schedule_update_cron(ids, cron)
    return ok(result)

@router.post("/system/task-center/exec-task/batch-delete")
async def sys_task_center_batch_delete_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_delete_ids(ids)
    return ok(result)

@router.post("/system/task-center/exec-task/batch-stop")
async def sys_task_center_batch_stop_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.post("/system/task-center/exec-task/item/batch-stop")
async def sys_task_center_item_batch_stop_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.post("/system/task-center/schedule/batch-disable")
async def sys_task_center_schedule_batch_disable_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _schedule_enable_ids(ids, False)
    return ok(result)

@router.post("/system/task-center/schedule/batch-enable")
async def sys_task_center_schedule_batch_enable_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _schedule_enable_ids(ids, True)
    return ok(result)

@router.post("/system/task-center/schedule/update-cron")
async def sys_task_center_schedule_update_cron_post(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    cron = _cron_from_body(body)
    result = _schedule_update_cron(ids, cron)
    return ok(result)

@router.post("/organization/task-center/exec-task/statistics")
def org_task_center_statistics_post(request: Request):
    """组织任务中心任务统计（POST兼容）。"""
    return ok([])

@router.post("/system/task-center/exec-task/statistics")
def sys_task_center_statistics_post(request: Request):
    """系统任务中心任务统计（POST兼容）。"""
    return ok([])

@router.post("/system/task-center/resource-pool/status")
def sys_task_center_resource_pool_status_post(request: Request):
    """系统任务中心资源池状态（POST兼容）。"""
    return ok([])

@router.get("/organization/task-center/exec-task/page")
def organization_task_center_exec_task_page():
    """组织任务中心-执行任务分页。"""
    return page_result([], len([]), current=1, page_size=10)

@router.get("/organization/task-center/exec-task/item/page")
def organization_task_center_exec_task_item_page():
    """组织任务中心-任务项分页。"""
    return page_result([], len([]), current=1, page_size=10)

@router.get("/organization/task-center/exec-task/item/order")
def organization_task_center_exec_task_item_order():
    """组织任务中心-任务项排序。"""
    return ok([])

@router.get("/organization/task-center/exec-task/statistics")
def organization_task_center_exec_task_statistics():
    """组织任务中心-任务统计。"""
    return ok([])

@router.get("/organization/task-center/exec-task/item/stop/{id}")
def organization_task_center_exec_task_item_stop(id):
    """操作接线到真实后端。"""
    result = _exec_stop_ids([id])
    return ok(result)

@router.get("/organization/task-center/exec-task/stop")
async def organization_task_center_exec_task_stop(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.get("/organization/task-center/exec-task/rerun")
async def organization_task_center_exec_task_rerun(request: Request):
    """操作接线到真实后端。"""
    tid = _query_one(request)
    result = _exec_rerun_id(tid)
    return ok(result)

@router.get("/organization/task-center/exec-task/delete")
async def organization_task_center_exec_task_delete(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _exec_delete_ids(ids)
    return ok(result)

@router.get("/organization/task-center/exec-task/batch/page")
def organization_task_center_exec_task_batch_page():
    """组织任务中心-批量分页。"""
    return page_result([], len([]), current=1, page_size=10)

@router.get("/organization/task-center/exec-task/batch-stop")
async def organization_task_center_exec_task_batch_stop(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.get("/organization/task-center/exec-task/batch-delete")
async def organization_task_center_exec_task_batch_delete(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_delete_ids(ids)
    return ok(result)

@router.get("/organization/task-center/exec-task/item/batch-stop")
async def organization_task_center_exec_task_item_batch_stop(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.get("/organization/task-center/exec-task/item/batch-delete")
async def organization_task_center_exec_task_item_batch_delete(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_delete_ids(ids)
    return ok(result)

@router.get("/organization/task-center/schedule/page")
def organization_task_center_schedule_page():
    """组织任务中心-定时任务分页。"""
    return page_result([], len([]), current=1, page_size=10)

@router.get("/organization/task-center/schedule/delete")
async def organization_task_center_schedule_delete(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _schedule_delete_ids(ids)
    return ok(result)

@router.get("/organization/task-center/schedule/switch")
async def organization_task_center_schedule_switch(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _schedule_switch_ids(ids)
    return ok(result)

@router.get("/organization/task-center/schedule/batch-enable")
async def organization_task_center_schedule_batch_enable(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _schedule_enable_ids(ids, True)
    return ok(result)

@router.get("/organization/task-center/schedule/batch-disable")
async def organization_task_center_schedule_batch_disable(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _schedule_enable_ids(ids, False)
    return ok(result)

@router.get("/organization/task-center/schedule/update-cron")
async def organization_task_center_schedule_update_cron(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    cron = _cron_from_body(body)
    result = _schedule_update_cron(ids, cron)
    return ok(result)

@router.get("/organization/task-center/project/options")
def organization_task_center_project_options():
    """组织任务中心-项目选项。"""
    return ok([])

@router.get("/organization/task-center/resource-pool/options")
def organization_task_center_resource_pool_options():
    """组织任务中心-资源池选项。"""
    return ok([])

@router.get("/system/task-center/exec-task/page")
def system_task_center_exec_task_page():
    """系统任务中心-执行任务分页。"""
    return page_result([], len([]), current=1, page_size=10)

@router.get("/system/task-center/exec-task/item/page")
def system_task_center_exec_task_item_page():
    """系统任务中心-任务项分页。"""
    return page_result([], len([]), current=1, page_size=10)

@router.get("/system/task-center/exec-task/item/order")
def system_task_center_exec_task_item_order():
    """系统任务中心-任务项排序。"""
    return ok([])

@router.get("/system/task-center/exec-task/statistics")
def system_task_center_exec_task_statistics():
    """系统任务中心-任务统计。"""
    return ok([])

@router.get("/system/task-center/exec-task/item/stop")
async def system_task_center_exec_task_item_stop(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.get("/system/task-center/exec-task/stop")
async def system_task_center_exec_task_stop(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.get("/system/task-center/exec-task/rerun")
async def system_task_center_exec_task_rerun(request: Request):
    """操作接线到真实后端。"""
    tid = _query_one(request)
    result = _exec_rerun_id(tid)
    return ok(result)

@router.get("/system/task-center/exec-task/delete")
async def system_task_center_exec_task_delete(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _exec_delete_ids(ids)
    return ok(result)

@router.get("/system/task-center/exec-task/batch/page")
def system_task_center_exec_task_batch_page():
    """系统任务中心-批量分页。"""
    return page_result([], len([]), current=1, page_size=10)

@router.get("/system/task-center/exec-task/batch-stop")
async def system_task_center_exec_task_batch_stop(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.get("/system/task-center/exec-task/batch-delete")
async def system_task_center_exec_task_batch_delete(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_delete_ids(ids)
    return ok(result)

@router.get("/system/task-center/exec-task/item/batch-stop")
async def system_task_center_exec_task_item_batch_stop(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_stop_ids(ids)
    return ok(result)

@router.get("/system/task-center/exec-task/item/batch-delete")
async def system_task_center_exec_task_item_batch_delete(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _exec_delete_ids(ids)
    return ok(result)

@router.get("/system/task-center/schedule/page")
def system_task_center_schedule_page():
    """系统任务中心-定时任务分页。"""
    return page_result([], len([]), current=1, page_size=10)

@router.get("/system/task-center/schedule/delete")
async def system_task_center_schedule_delete(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _schedule_delete_ids(ids)
    return ok(result)

@router.get("/system/task-center/schedule/switch")
async def system_task_center_schedule_switch(request: Request):
    """操作接线到真实后端。"""
    ids = _query_ids(request)
    result = _schedule_switch_ids(ids)
    return ok(result)

@router.get("/system/task-center/schedule/batch-enable")
async def system_task_center_schedule_batch_enable(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _schedule_enable_ids(ids, True)
    return ok(result)

@router.get("/system/task-center/schedule/batch-disable")
async def system_task_center_schedule_batch_disable(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    result = _schedule_enable_ids(ids, False)
    return ok(result)

@router.get("/system/task-center/schedule/update-cron")
async def system_task_center_schedule_update_cron(request: Request):
    """操作接线到真实后端。"""
    body = await read_body(request)
    ids = _ids_from_body(body)
    cron = _cron_from_body(body)
    result = _schedule_update_cron(ids, cron)
    return ok(result)

@router.get("/system/task-center/organization/options")
def system_task_center_organization_options():
    """系统任务中心-组织选项。"""
    return ok([])

@router.get("/system/task-center/project/options")
def system_task_center_project_options():
    """系统任务中心-项目选项。"""
    return ok([])

@router.get("/system/task-center/resource-pool/options")
def system_task_center_resource_pool_options():
    """系统任务中心-资源池选项。"""
    return ok([])

@router.get("/system/task-center/resource-pool/status")
def system_task_center_resource_pool_status():
    """系统任务中心-资源池状态。"""
    return ok([])

@router.get("/organization/task-center/exec-task/delete/{task_id}")
@router.post("/organization/task-center/exec-task/delete/{task_id}")
def org_task_center_exec_delete_path(task_id):
    """操作接线到真实后端。"""
    result = _exec_delete_ids([task_id])
    return ok(result)

@router.get("/organization/task-center/exec-task/item/stop/{id}/{item_id}")
@router.post("/organization/task-center/exec-task/item/stop/{id}/{item_id}")
def org_task_center_exec_item_stop_path(id, item_id):
    """操作接线到真实后端。"""
    result = _exec_stop_ids([id])
    return ok(result)

@router.get("/organization/task-center/exec-task/rerun/{task_id}")
@router.post("/organization/task-center/exec-task/rerun/{task_id}")
def org_task_center_exec_rerun_path(task_id):
    """操作接线到真实后端。"""
    result = _exec_rerun_id(task_id)
    return ok(result)

@router.get("/organization/task-center/exec-task/stop/{task_id}")
@router.post("/organization/task-center/exec-task/stop/{task_id}")
def org_task_center_exec_stop_path(task_id):
    """操作接线到真实后端。"""
    result = _exec_stop_ids([task_id])
    return ok(result)

@router.get("/organization/task-center/schedule/delete/{schedule_id}")
@router.post("/organization/task-center/schedule/delete/{schedule_id}")
def org_task_center_schedule_delete_path(schedule_id):
    """操作接线到真实后端。"""
    result = _schedule_delete_ids([schedule_id])
    return ok(result)

@router.get("/organization/task-center/schedule/switch/{schedule_id}")
@router.post("/organization/task-center/schedule/switch/{schedule_id}")
def org_task_center_schedule_switch_path(schedule_id):
    """操作接线到真实后端。"""
    result = _schedule_switch_ids([schedule_id])
    return ok(result)

@router.get("/system/task-center/exec-task/delete/{task_id}")
@router.post("/system/task-center/exec-task/delete/{task_id}")
def system_task_center_exec_delete_path(task_id):
    """操作接线到真实后端。"""
    result = _exec_delete_ids([task_id])
    return ok(result)

@router.get("/system/task-center/exec-task/item/stop/{task_id}/{item_id}")
@router.post("/system/task-center/exec-task/item/stop/{task_id}/{item_id}")
def system_task_center_exec_item_stop_path(task_id, item_id):
    """操作接线到真实后端。"""
    result = _exec_stop_ids([task_id])
    return ok(result)

@router.get("/system/task-center/exec-task/rerun/{task_id}")
@router.post("/system/task-center/exec-task/rerun/{task_id}")
def system_task_center_exec_rerun_path(task_id):
    """操作接线到真实后端。"""
    result = _exec_rerun_id(task_id)
    return ok(result)

@router.get("/system/task-center/exec-task/stop/{task_id}")
@router.post("/system/task-center/exec-task/stop/{task_id}")
def system_task_center_exec_stop_path(task_id):
    """操作接线到真实后端。"""
    result = _exec_stop_ids([task_id])
    return ok(result)

@router.get("/system/task-center/schedule/delete/{schedule_id}")
@router.post("/system/task-center/schedule/delete/{schedule_id}")
def system_task_center_schedule_delete_path(schedule_id):
    """操作接线到真实后端。"""
    result = _schedule_delete_ids([schedule_id])
    return ok(result)

@router.get("/system/task-center/schedule/switch/{schedule_id}")
@router.post("/system/task-center/schedule/switch/{schedule_id}")
def system_task_center_schedule_switch_path(schedule_id):
    """操作接线到真实后端。"""
    result = _schedule_switch_ids([schedule_id])
    return ok(result)

@router.get("/system/task-center/exec-task/item/stop/{id}")
@router.post("/system/task-center/exec-task/item/stop/{id}")
def system_task_item_stop_single_path(id):
    """操作接线到真实后端。"""
    result = _exec_stop_ids([id])
    return ok(result)
