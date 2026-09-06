"""Apitest 域路由适配器

聚合所有 API 测试相关的兼容路由。
"""
from fastapi import APIRouter

# 导入各个子模块的路由
from app.routers.apitest_compat_base import router as base_router
from app.routers.apitest_compat_case import router as case_router
from app.routers.apitest_compat_definition import router as definition_router
from app.routers.apitest_compat_mock import router as mock_router
from app.routers.apitest_compat_scenario import router as scenario_router

router = APIRouter(tags=["adapter-apitest"])

# 聚合所有子路由
router.include_router(base_router)
router.include_router(definition_router)
router.include_router(scenario_router)
router.include_router(case_router)
router.include_router(mock_router)
