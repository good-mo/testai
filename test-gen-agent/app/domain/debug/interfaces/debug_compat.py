"""Debug 域路由适配器

聚合所有 debug 相关的兼容路由。
"""
from fastapi import APIRouter

# from app.routers.debug_compat import router as debug_router

# TODO: 实现具体路由
router = APIRouter(tags=["adapter-debug"])
