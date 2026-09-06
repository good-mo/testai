# app/routers/method_compat.py（自 app/adapters/domains/method_compat.py 迁移）
"""HTTP 方法兼容与业务逻辑补齐。

修复以下问题：
  1. P1 方法不匹配：前端 POST 而后端仅有 GET（反之亦然），导致 405。
  2. 关键业务接口补齐：环境、文件仓库、成员管理、资源池等。
"""

import time
import uuid
from typing import Dict, List

from fastapi import APIRouter, Request

from app.core.response import fail, ok, page_result, read_body
from app.core.task_enums import normalize_exec_result, normalize_status, normalize_trigger_mode
from app.core.helpers import as_model
from app.logging_config import get_logger
from app.models.method_compat import (
    EnvGroupDeleteBody,
    OrgMemberListBody,
    PluginFormOptionBody,
    ProjectMemberListBody,
    ResourcePoolCapacityListBody,
    TaskCenterOrderBody,
    TaskCenterPageBody,
)
from app.services.apitest_service import apitest_service
from app.services.case_service import case_service
from app.services.organization_service import organization_service
from app.services.project_service import project_service
from app.services.resource_pool_service import resource_pool_service
from app.services.task_center_service import task_center_service

logger = get_logger(__name__)
router = APIRouter(tags=["method-compat"])


def _task_center_item(item_id: str, name: str = "", status: str = "COMPLETED",
                      type: str = "API", create_time: float = 0,
                      trigger_mode: str = "MANUAL", result: str = "SUCCESS",
                      **extra) -> dict:
    """构造任务中心条目。

    状态输出边界归一化：
      - ``status`` 统一为权威执行状态枚举（PENDING/RUNNING/COMPLETED/RERUNNING/STOPPED），
        不再把内部小写生命周期（pending/running/success/...）或执行结果（SUCCESS/ERROR）
        原样塞给前端 executeStatusMap；
      - ``triggerMode`` 补权威触发方式枚举，避免前端取到 undefined；
      - ``result`` 补权威执行结果枚举，供前端 executeResultMap 展示。
    """
    return {
        "id": item_id,
        "name": name or f"任务-{item_id[:8]}",
        "type": type,
        "status": normalize_status(status),
        "triggerMode": normalize_trigger_mode(trigger_mode),
        "result": normalize_exec_result(result),
        "createTime": int(create_time or time.time() * 1000),
        "startTime": int(create_time or time.time() * 1000),
        "endTime": 0,
        "executor": "admin",
        **extra,
    }


def _list_schedules(keyword: str = "") -> List[Dict]:
    """查询真实调度任务列表。

    数据访问统一下沉 apitest_service（Router → Service → Repo → Database），
    路由层不再手写 SQL（约束 #2）。
    """
    try:
        return apitest_service.list_schedules(keyword=keyword)
    except Exception:
        return []


def _list_tasks() -> List[Dict]:
    """从任务管理器查询真实任务。"""
    items = []
    try:
        tasks = task_center_service.list_raw_tasks(limit=500)
        for t in tasks:
            raw_status = t.get("status") or "COMPLETED"
            # manager 内部小写生命周期 → 权威大写执行状态；执行结果由其判定
            if raw_status in ("success", "failed", "error", "cancelled", "stopped"):
                result = normalize_exec_result(raw_status)
            else:
                result = "SUCCESS"
            items.append(_task_center_item(
                t.get("task_id") or t.get("id") or str(uuid.uuid4()),
                t.get("name", ""),
                raw_status,
                t.get("type", "API"),
                t.get("created_at", time.time()),
                trigger_mode="MANUAL",
                result=result,
            ))
    except Exception:
        pass
    return items


# ════════════════════════════════════════════════════════════
# P1-1: 功能用例-脑图方法兼容 (POST)
# ════════════════════════════════════════════════════════════

@router.post("/functional/mind/case/list")
async def functional_mind_case_list_post(request: Request):
    """获取脑图数据（POST兼容）。"""
    cases = case_service.list_cases(limit=500)
    tree = []
    for c in cases:
        node = {
            "id": c.get("id", ""),
            "text": c.get("title", ""),
            "resource": {
                "status": c.get("status", "draft"),
                "priority": c.get("priority", "P2"),
            },
            "children": [],
        }
        tree.append(node)
    return ok(tree)


@router.post("/functional/mind/case/tree")
async def functional_mind_case_tree_post(request: Request):
    """获取脑图模块树（POST兼容）。"""
    return ok({
        "id": "root",
        "name": "全部用例",
        "type": "MODULE",
        "children": [],
    })


# ════════════════════════════════════════════════════════════
# P1-2: 系统-组织/项目成员列表 (POST兼容)
# ════════════════════════════════════════════════════════════

@router.post("/system/organization/list-member")
async def system_organization_list_member_post(request: Request):
    """组织成员列表（POST兼容）。"""
    body = await read_body(request)
    mb = as_model(body, OrgMemberListBody)
    org_id = mb.effective_org_id
    keyword = mb.effective_keyword
    page_size = mb.effective_page_size
    current = mb.effective_current

    members = organization_service.list_members(org_id, search=keyword, limit=999)
    items = []
    for m in members:
        items.append({
            "id": m.get("user_id", ""),
            "name": m.get("name", m.get("username", "")),
            "email": m.get("email", ""),
            "phone": "",
            "role": m.get("role", "member"),
            "createTime": int((m.get("create_time", 0) or 0) * 1000),
        })
    return page_result(items, len(items), current=current, page_size=page_size)


@router.post("/system/project/member-list")
async def system_project_member_list_post(request: Request):
    """系统项目成员列表（POST兼容）。"""
    body = await read_body(request)
    mb = as_model(body, ProjectMemberListBody)
    project_id = mb.effective_project_id
    keyword = mb.effective_keyword
    page_size = mb.effective_page_size
    current = mb.effective_current

    if not project_id:
        return page_result([], len([]), current=current, page_size=page_size)

    members = project_service.list_members(project_id, keyword=keyword)
    items = []
    for m in members:
        items.append({
            "id": m.get("user_id", ""),
            "name": m.get("name", m.get("username", "")),
            "email": m.get("email", ""),
            "phone": "",
            "role": m.get("role", "member"),
            "createTime": int((m.get("created_at", 0) or 0) * 1000),
        })
    return page_result(items, len(items), current=current, page_size=page_size)


# ════════════════════════════════════════════════════════════
# P1-3: 任务中心方法兼容 (POST)
# ════════════════════════════════════════════════════════════

# ── 项目任务中心 POST ───────────────────────────────────

@router.post("/project/task-center/schedule/page")
async def project_schedule_page_post(request: Request):
    """项目定时任务分页（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    keyword = page.keyword or ""
    items = _list_schedules(keyword)
    return page_result(items, len(items), current=current, page_size=page_size)


@router.post("/project/task-center/exec-task/page")
async def project_exec_task_page_post(request: Request):
    """项目执行任务分页（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    items = _list_tasks()
    return page_result(items, len(items), current=current, page_size=page_size)


@router.post("/project/task-center/exec-task/item/page")
async def project_exec_task_item_page_post(request: Request):
    """项目任务详情分页（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    return page_result([], len([]), current=current, page_size=page_size)


@router.post("/project/task-center/exec-task/item/order")
async def project_exec_task_item_order_post(request: Request):
    """项目任务排队信息（POST兼容）。"""
    body = await read_body(request)
    task_ids = TaskCenterOrderBody.model_validate(body).effective_ids
    result = {}
    for tid in task_ids:
        result[tid] = {"order": 1, "inQueue": False}
    return ok(result)


@router.post("/project/task-center/exec-task/batch/page")
async def project_exec_task_batch_page_post(request: Request):
    """项目批量任务报告列表（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    return page_result([], len([]), current=current, page_size=page_size)


# ── 系统任务中心 POST ───────────────────────────────────

@router.post("/system/task-center/schedule/page")
async def system_schedule_page_post(request: Request):
    """系统定时任务分页（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    keyword = page.keyword or ""
    items = _list_schedules(keyword)
    return page_result(items, len(items), current=current, page_size=page_size)


@router.post("/system/task-center/exec-task/page")
async def system_exec_task_page_post(request: Request):
    """系统执行任务分页（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    items = _list_tasks()
    return page_result(items, len(items), current=current, page_size=page_size)


@router.post("/system/task-center/exec-task/item/page")
async def system_exec_task_item_page_post(request: Request):
    """系统任务详情分页（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    return page_result([], len([]), current=current, page_size=page_size)


@router.post("/system/task-center/exec-task/item/order")
async def system_exec_task_item_order_post(request: Request):
    """系统任务排队信息（POST兼容）。"""
    body = await read_body(request)
    task_ids = TaskCenterOrderBody.model_validate(body).effective_ids
    result = {}
    for tid in task_ids:
        result[tid] = {"order": 1, "inQueue": False}
    return ok(result)


@router.post("/system/task-center/exec-task/batch/page")
async def system_exec_task_batch_page_post(request: Request):
    """系统批量任务报告列表（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    return page_result([], len([]), current=current, page_size=page_size)


# ── 组织任务中心 POST ───────────────────────────────────

@router.post("/organization/task-center/schedule/page")
async def org_schedule_page_post(request: Request):
    """组织定时任务分页（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    keyword = page.keyword or ""
    items = _list_schedules(keyword)
    return page_result(items, len(items), current=current, page_size=page_size)


@router.post("/organization/task-center/exec-task/page")
async def org_exec_task_page_post(request: Request):
    """组织执行任务分页（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    items = _list_tasks()
    return page_result(items, len(items), current=current, page_size=page_size)


@router.post("/organization/task-center/exec-task/item/page")
async def org_exec_task_item_page_post(request: Request):
    """组织任务详情分页（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    return page_result([], len([]), current=current, page_size=page_size)


@router.post("/organization/task-center/exec-task/item/order")
async def org_exec_task_item_order_post(request: Request):
    """组织任务排队信息（POST兼容）。"""
    body = await read_body(request)
    task_ids = TaskCenterOrderBody.model_validate(body).effective_ids
    result = {}
    for tid in task_ids:
        result[tid] = {"order": 1, "inQueue": False}
    return ok(result)


@router.post("/organization/task-center/exec-task/batch/page")
async def org_exec_task_batch_page_post(request: Request):
    """组织批量任务报告列表（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    return page_result([], len([]), current=current, page_size=page_size)


# ── 其他任务中心 POST 兼容 ──────────────────────────────

@router.post("/task/center/project/schedule/page")
async def task_center_project_schedule_page_post(request: Request):
    """项目-任务中心-定时任务列表（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, TaskCenterPageBody)
    current = page.effective_current
    page_size = page.effective_page_size
    keyword = page.keyword or ""
    items = _list_schedules(keyword)
    return page_result(items, len(items), current=current, page_size=page_size)


@router.post("/task/center/api/project/stop")
async def task_center_api_project_stop_post(request: Request):
    """停止项目 API 任务（POST兼容）。"""
    return ok()


# ════════════════════════════════════════════════════════════
# P1-4: 接口测试方法兼容
# ════════════════════════════════════════════════════════════

@router.get("/api/scenario/step/get")
def api_scenario_step_get_get(request: Request):
    """获取场景步骤详情（GET兼容，前端用 query 传 stepId）。"""
    return ok(None)


@router.get("/api/definition/mock/page")
def api_definition_mock_page_get(request: Request):
    """Mock 分页列表（GET兼容）。"""
    params = dict(request.query_params)
    keyword = params.get("keyword", "")
    page_size = int(params.get("pageSize", 10))
    current = int(params.get("current", 1))
    offset = (current - 1) * page_size
    items = apitest_service.list_mocks(keyword=keyword, limit=page_size, offset=offset,
                                       project_id=params.get("projectId", ""))
    result = []
    for m in items:
        result.append({
            "id": m.get("id", ""),
            "name": m.get("name", ""),
            "method": m.get("method", "GET"),
            "path": m.get("path", ""),
            "statusCode": m.get("status_code", 200),
            "responseBody": m.get("response_body", ""),
            "responseHeaders": m.get("response_headers", "{}"),
            "delay": m.get("delay_ms", 0),
            "active": bool(m.get("active", 1)),
            "description": m.get("description", ""),
            "createTime": int((m.get("created_at", 0) or 0) * 1000),
        })
    return page_result(result, len(result), current=current, page_size=page_size)


# ════════════════════════════════════════════════════════════
# P1-4b: 插件表单选项方法兼容 (POST)
# ════════════════════════════════════════════════════════════

@router.post("/api/test/plugin/form/option")
async def api_test_plugin_form_option_post(request: Request):
    """插件表单选项（POST兼容）。

    前端 `getPluginOptions` 用 POST 提交 {pluginId, ...} 拉取级联选项，
    而后端历史实现只注册了 GET，点击插件配置下拉会直接 405。
    """
    body = await read_body(request)
    plugin_id = as_model(body, PluginFormOptionBody).effective_plugin_id
    logger.debug("插件表单选项查询 pluginId=%s", plugin_id)
    return ok([])


# ════════════════════════════════════════════════════════════
# P1-5: 资源池容量方法兼容 (POST)
# ════════════════════════════════════════════════════════════

@router.post("/test/resource/pool/capacity/task/list")
async def test_resource_pool_capacity_task_list_post(request: Request):
    """资源池容量任务列表（POST兼容）。"""
    body = await read_body(request)
    page = as_model(body, ResourcePoolCapacityListBody)
    current = page.effective_current
    page_size = page.effective_page_size
    return page_result([], len([]), current=current, page_size=page_size)


# ════════════════════════════════════════════════════════════
# P1-6: 项目管理-环境管理补充
# ════════════════════════════════════════════════════════════

@router.post("/project/environment/group/delete")
async def project_environment_group_delete_post(request: Request):
    """删除环境组（POST兼容）。"""
    body = await read_body(request)
    group_id = as_model(body, EnvGroupDeleteBody).effective_id
    if not group_id:
        return fail("缺少环境组 ID")
    apitest_service.delete_env_group(group_id)
    return ok()


# ════════════════════════════════════════════════════════════
# P1-7: 项目管理-文件管理补充
# ════════════════════════════════════════════════════════════

@router.get("/project/file/list")
def project_file_list(project_id: str = "", keyword: str = ""):
    """项目文件列表。"""
    return page_result([], len([]), current=1, page_size=10)


# ════════════════════════════════════════════════════════════
# P2-1: 资源池补充
# ════════════════════════════════════════════════════════════

@router.get("/test/resource/pool/page")
def test_resource_pool_page_get(project_id: str = "", keyword: str = ""):
    """资源池分页（GET兼容）。"""
    items = resource_pool_service.list(keyword=keyword)
    # 转换为前端期望格式
    result = []
    for p in items:
        result.append({
            "id": p.get("id", ""),
            "name": p.get("name", ""),
            "description": p.get("description", ""),
            "enable": bool(p.get("enable", 1)),
            "createTime": int((p.get("created_at", 0) or 0) * 1000),
            "updateTime": int((p.get("updated_at", 0) or 0) * 1000),
        })
    return page_result(result, len(result), current=1, page_size=100)
