# app/routers/datafactory.py
"""数据工厂路由（Phase 4 · DDD A→B→C 渐进式迁移 — 阶段 B 接入）。

- **阶段 A（已完成）**：`app/domain/datafactory/` DDD 领域/应用层就绪，
  `datafactory_app_service` 可用、有单测。
- **阶段 B（本次）**：核心生命周期接口改调 `datafactory_app_service`，
  输出经 `application/web_mapper.py` DTO 桥翻译，保持对外 API schema
  与既有 `DatafactoryService` 时代逐字段一致（零破坏、可回滚）。
- **阶段 C**：`datafactory_service` 瘦身为薄门面委托 DDD（见该文件）。
"""
import asyncio
from typing import Optional

from fastapi import APIRouter

from app.core.response import fail, ok
from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainException,
    DomainValidationError,
)
from app.domain.datafactory.application.datafactory_app_service import (
    datafactory_app_service,
)
from app.domain.datafactory.application.dto import (
    CleanupCommand,
    CreateTemplateCommand,
    GenerateCommand,
    TemplateListQuery,
    UpdateTemplateCommand,
)
from app.domain.datafactory.application.web_mapper import (
    batch_generate_payload,
    template_list_payload,
)
from app.domain.datafactory.application.dto import (
    DataGenerateRequest,
    DataTemplateCreate,
    DataTemplateUpdate,
)

router = APIRouter(tags=["data-factory"])

_SVC = datafactory_app_service


def _translate_domain_error(exc: DomainException):
    """把领域异常翻译为统一 {code,message,data} 响应（保持四层时代语义）。"""
    code = exc.status_code if exc.status_code >= 400 else 400
    return fail(exc.message or "操作失败", code)


@router.get("/api/data/templates")
def api_list_data_templates(
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """列出数据模板。"""
    payload = _SVC.list_templates(TemplateListQuery(
        category=category or "", search=search or "",
        limit=limit, offset=offset,
    ))
    return ok(template_list_payload(payload))


@router.post("/api/data/templates")
def api_create_data_template(req: DataTemplateCreate):
    """创建数据模板。"""
    try:
        template = _SVC.create_template(CreateTemplateCommand(
            name=req.name, description=req.description,
            category=req.category, schema_def=req.schema_def,
            deps=req.deps, tags=req.tags,
        ))
    except DomainException as exc:
        return _translate_domain_error(exc)
    return ok(template)


@router.get("/api/data/templates/{template_id}")
def api_get_data_template(template_id: str):
    """获取数据模板详情。"""
    template = _SVC.get_template(template_id)
    if not template:
        return fail(f"模板 {template_id} 不存在", 404)
    return ok(template)


@router.put("/api/data/templates/{template_id}")
def api_update_data_template(template_id: str, req: DataTemplateUpdate):
    """更新数据模板。"""
    body = req.model_dump(exclude_none=True)
    body.pop("schema_def", None)  # 避免混入非命令字段
    try:
        template = _SVC.update_template(UpdateTemplateCommand(
            template_id=template_id,
            name=body.get("name"),
            description=body.get("description"),
            category=body.get("category"),
            schema_def=req.schema_def,
            deps=body.get("deps"),
            tags=body.get("tags"),
            status=body.get("status"),
        ))
    except AggregateNotFound:
        return fail(f"模板 {template_id} 不存在", 404)
    except DomainValidationError as exc:
        return _translate_domain_error(exc)
    if not template:
        return fail(f"模板 {template_id} 不存在", 404)
    return ok(template)


@router.delete("/api/data/templates/{template_id}")
def api_delete_data_template(template_id: str):
    """删除数据模板。"""
    try:
        deleted = _SVC.delete_template(template_id)
    except AggregateNotFound:
        deleted = False
    if not deleted:
        return fail(f"模板 {template_id} 不存在", 404)
    return ok({"deleted": True, "template_id": template_id})


@router.post("/api/data/generate")
async def api_generate_data(req: DataGenerateRequest):
    """按模板批量生成数据。"""
    if not req.template_id:
        return fail("缺少 template_id 参数", 400)
    if not _SVC.get_template(req.template_id):
        return fail(f"数据模板 {req.template_id} 不存在", 404)
    result = await asyncio.to_thread(
        _SVC.generate,
        GenerateCommand(
            template_id=req.template_id, batch_size=req.batch_size,
            env_key=req.env_key,
        ),
    )
    return ok(batch_generate_payload(result))


@router.get("/api/data/batches")
def api_list_data_batches(limit: int = 50):
    """列出生成批次。"""
    return ok(_SVC.list_batches(limit=limit))


@router.post("/api/data/cleanup/batch/{batch_id}")
async def api_cleanup_batch(batch_id: str):
    """清理指定批次的数据（幂等：未知批次亦返回成功，沿用既有语义）。"""
    try:
        result = await asyncio.to_thread(
            _SVC.cleanup_batch,
            CleanupCommand(batch_id=batch_id),
        )
    except AggregateNotFound:
        # 沿用四层时代"未知批次清理返回 False 而非 4xx"的幂等语义
        result = False
    return ok(result)


@router.post("/api/data/cleanup/template/{template_id}")
async def api_cleanup_template(template_id: str):
    """清理指定模板的数据。"""
    result = await asyncio.to_thread(
        _SVC.cleanup_by_template, template_id,
    )
    return ok(result)


@router.post("/api/data/cleanup/env/{env_key}")
async def api_cleanup_env(env_key: str):
    """清理指定环境的数据。"""
    result = await asyncio.to_thread(
        _SVC.cleanup_by_env, env_key,
    )
    return ok(result)


@router.get("/api/data/stats")
async def api_data_stats():
    """数据工厂统计。"""
    return ok(await asyncio.to_thread(_SVC.stats))
