# app/routers/apitest_compat.py（自 app/adapters/domains/api_testing.py 迁移）
"""业务域路由拆分：api_testing（Phase 3 重构）。

原 2712 行单文件已按 definition / scenario / case / mock 拆分为四个分段模块，
本文件仅保留统一路由聚合入口（路由纯搬移、行为不变）。
"""

from fastapi import APIRouter

from app.routers.apitest_compat_case import router as apitest_case_router
from app.routers.apitest_compat_definition import router as apitest_definition_router
from app.routers.apitest_compat_mock import router as apitest_mock_router
from app.routers.apitest_compat_scenario import router as apitest_scenario_router

router = APIRouter(tags=["adapter-api_testing"])

# 聚合各分段路由：不同路径前缀间互不冲突，注册顺序不影响匹配
router.include_router(apitest_definition_router)
router.include_router(apitest_scenario_router)
router.include_router(apitest_case_router)
router.include_router(apitest_mock_router)
