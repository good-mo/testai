# app/routers/plugins.py
"""业务域路由：plugins 兼容路由。迁移自 app/adapters/domains/plugins.py，占位 stub 原样保留。"""

import uuid

from fastapi import APIRouter, Body, Request

from app.core.response import ok
from app.logging_config import get_logger
from app.domain.plugins.application.dto import PluginIdBody, PluginUpsertBody

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-plugins"])


@router.get("/plugin/delete")
def plugin_delete_get(request: Request):
    """插件删除（GET兼容）。"""
    return ok()


@router.post("/plugin/options")
def plugin_options_post(request: Request):
    """插件选项（POST兼容）。"""
    return ok([])


@router.get("/plugin/list")
def plugin_list():
    """插件列表。"""
    return ok([])


@router.post("/plugin/add")
def plugin_add(body: PluginUpsertBody = Body(default=None)):
    """添加插件。multipart 上传兼容，JSON 载荷经 PluginUpsertBody 收口。"""
    return ok({"id": str(uuid.uuid4())})


@router.post("/plugin/update")
def plugin_update(body: PluginUpsertBody = Body(default=None)):
    """更新插件。"""
    return ok()


@router.post("/plugin/delete")
def plugin_delete(body: PluginIdBody = Body(default=None)):
    """删除插件。"""
    return ok()


@router.get("/plugin/options")
def plugin_options():
    """插件选项。"""
    return ok([])


@router.get("/plugin/script/get")
def plugin_script_get(id: str = ""):
    """获取插件脚本。"""
    return ok({})


@router.get("/plugin/image/")
def plugin_image(id: str = ""):
    """插件图片。"""
    return ok({})


# ════════════════════════════════════════════════════════════
# P2-2: 服务集成  /service/integration/*
# ════════════════════════════════════════════════════════════


@router.get("/plugin/image/{plugin_id}")
def plugin_image_path(plugin_id: str):
    """获取插件图片（带路径参数）。"""
    return ok({"id": plugin_id})


# ════════════════════════════════════════════════════════════
# 项目
# ════════════════════════════════════════════════════════════

