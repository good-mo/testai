"""资源池限界上下文。

聚合根：`ResourcePool`（资源池）
对应现有：`services/resource_pool_service.py` `repositories/resource_pool_repo.py`
"""
from app.domain.resource_pool.application.resource_pool_app_service import (
    ResourcePoolAppService,
    resource_pool_app_service,
)
from app.domain.resource_pool.domain.entities.resource_pool import ResourcePool

__all__ = ["ResourcePoolAppService", "resource_pool_app_service", "ResourcePool"]
