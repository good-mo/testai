# app/domain/common/interfaces/router.py
"""common 域路由适配器。"""
from fastapi import APIRouter

router = APIRouter(tags=["common"])

# common 域是共享基础层，不直接暴露路由
# 提供 entities, value_objects, exceptions 等共享组件
