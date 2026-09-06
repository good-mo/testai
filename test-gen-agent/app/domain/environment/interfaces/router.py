# app/routers/environments.py
"""环境管理路由（Phase 3 重构 · 4 层对齐）。

Router → Service → Repository → Database
"""
import asyncio

from fastapi import APIRouter

from app.core.response import fail, ok
from app.domain.environment.application.dto import EnvironmentCreate, EnvironmentUpdate
from app.domain.environment.application.environment_app_service import environment_service

router = APIRouter(tags=["environments"])


@router.get("/api/environments")
def api_list_environments(
    search: str = "",
    status: str = "",
    env_type: str = "",
):
    """列出环境。"""
    envs = environment_service.list(search=search, status=status, env_type=env_type)
    return ok({"environments": envs, "total": len(envs)})


@router.post("/api/environments")
def api_register_environment(body: EnvironmentCreate):
    """注册新环境。"""
    data = body.model_dump(exclude_unset=True)
    if not data.get("name"):
        data["name"] = "未命名环境"
    env = environment_service.create(data)
    return ok(env)


@router.get("/api/environments/{env_id}")
def api_get_environment(env_id: str):
    """获取环境详情。"""
    env = environment_service.get(env_id)
    if not env or env.get("deleted"):
        return fail("环境不存在", 404)
    return ok(env)


@router.put("/api/environments/{env_id}")
def api_update_environment(env_id: str, body: EnvironmentUpdate):
    """更新环境。"""
    updates = body.model_dump(exclude_unset=True)
    env = environment_service.update(env_id, updates)
    if not env:
        return fail("环境不存在", 404)
    return ok(env)


@router.delete("/api/environments/{env_id}")
def api_delete_environment(env_id: str):
    """删除环境。"""
    result = environment_service.delete(env_id)
    return ok({"success": result})


@router.post("/api/environments/{env_id}/launch")
async def api_launch_environment(env_id: str):
    """启动环境（Docker 容器）。"""
    env = environment_service.get(env_id)
    if not env or env.get("deleted"):
        return fail(f"环境 {env_id} 不存在", 404)
    result = await asyncio.to_thread(environment_service.launch, env_id)
    return ok(result)


@router.post("/api/environments/{env_id}/stop")
async def api_stop_environment(env_id: str):
    """停止环境。"""
    env = environment_service.get(env_id)
    if not env or env.get("deleted"):
        return fail(f"环境 {env_id} 不存在", 404)
    result = await asyncio.to_thread(environment_service.stop, env_id)
    return ok(result)


@router.post("/api/environments/{env_id}/health")
async def api_check_env_health(env_id: str):
    """检查环境健康状态。"""
    env = environment_service.get(env_id)
    if not env or env.get("deleted"):
        return fail(f"环境 {env_id} 不存在", 404)
    result = await asyncio.to_thread(environment_service.health_check, env_id)
    return ok(result)


@router.post("/api/environments/check-all")
async def api_check_all_envs():
    """检查所有环境健康状态。"""
    result = await asyncio.to_thread(environment_service.health_check_all)
    return ok(result)


@router.get("/api/environments/trash/list")
def api_list_env_trash():
    """列出回收站中的环境。"""
    items = environment_service.list_trash()
    return ok({"items": items, "total": len(items)})


@router.post("/api/environments/{env_id}/restore")
def api_restore_environment(env_id: str):
    """从回收站恢复环境。"""
    result = environment_service.restore(env_id)
    return ok({"success": result})
