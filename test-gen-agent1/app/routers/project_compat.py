# app/routers/project_compat.py（自 app/adapters/domains/project.py 迁移）
"""业务域路由拆分：project（Phase 3 重构）。

原 app/adapters/domains/project.py 整体迁入 routers 层，P4 超大文件拆分后
本文件仅保留统一路由聚合入口（路由按业务域搬移至 project_compat_* 分段，
纯搬移、行为不变）。

保持 TestPilot 兼容路径与 {code,message,data} 响应格式不变。
"""

from fastapi import APIRouter

from app.routers.project_compat_application import router as project_compat_application_router
from app.routers.project_compat_environment import router as project_compat_environment_router
from app.routers.project_compat_extra import router as project_compat_extra_router
from app.routers.project_compat_extra2 import router as project_compat_extra2_router
from app.routers.project_compat_file import router as project_compat_file_router
from app.routers.project_compat_member import router as project_compat_member_router

router = APIRouter(tags=["adapter-project"])

# 聚合各分段路由：不同路径前缀间互不冲突，注册顺序不影响匹配
router.include_router(project_compat_member_router)
router.include_router(project_compat_file_router)
router.include_router(project_compat_environment_router)
router.include_router(project_compat_application_router)
router.include_router(project_compat_extra_router)
router.include_router(project_compat_extra2_router)
