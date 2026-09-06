# app/routers/projects.py
"""项目管理路由（Phase 3 重构 · 4 层对齐 / DDD 迁移 · 阶段 B）。

阶段 B（项目域 A→B→C 渐进迁移）：
  本路由的核心生命周期接口（列表 / 创建 / 详情 / 更新 / 删除）改调
  DDD 应用门面 `ProjectAppService`，参数经 DTO（`dto.py`）翻译，
  返回经 DTO 契约桥（`web_contract.py`）归一为既有仓库行口径，
  保证对外 API / 前端契约零变化。

Router → ProjectAppService → ProjectRepoAdapter(防腐层) → ProjectRepo

统计等 Project 聚合未承载的读口径仍走 `project_service`（双轨过渡）。
"""
from fastapi import APIRouter

from app.core.response import fail, ok
from app.domain.common.exceptions import AggregateNotFound, DomainValidationError
from app.domain.project.application.dto import (
    ChangeStatusCommand,
    CreateProjectCommand,
    ListQuery,
    UpdateProjectCommand,
)
from app.domain.project.application.project_app_service import ProjectAppService
from app.domain.project.application.web_contract import to_row, to_row_page
from app.models.project import ProjectCreate, ProjectUpdate
from app.domain.project.application.project_app_service import project_service

router = APIRouter(tags=["projects"])

# 项目应用门面（进程内单例）
_project_app = ProjectAppService()

# 状态机可合法迁移的项目状态（active/archived）
_MANAGEABLE_STATUSES = ("active", "archived")


@router.get("/api/projects")
def front_api_list_projects(search: str = "", status: str = "", limit: int = 100):
    """前端项目列表。"""
    result = _project_app.list(ListQuery(
        search=search or "", status=status or "", limit=int(limit or 100),
    ))
    return ok(to_row_page(result))


@router.post("/api/projects")
def front_api_create_project(body: ProjectCreate):
    """前端创建项目。"""
    item = _project_app.create(CreateProjectCommand(
        name=body.name,
        description=body.description,
        repo_url=body.repo_url,
        language=body.language,
        path=body.path,
    ))
    return ok(to_row(item))


@router.get("/api/projects/{project_id}")
def front_api_get_project(project_id: str):
    """前端获取项目详情。"""
    try:
        item = _project_app.get_or_raise(project_id)
    except AggregateNotFound:
        return fail("项目不存在", 404)
    return ok(to_row(item))


@router.put("/api/projects/{project_id}")
def front_api_update_project(project_id: str, body: ProjectUpdate):
    """前端更新项目。

    `status`（active/archived）属聚合生命周期状态，经 `change_status` 走
    领域状态机；其余普通字段走 `update`。保证对外 schema 不变。
    """
    updates = body.model_dump(exclude_unset=True)
    status = updates.pop("status", None)

    # 1) 先更新普通字段（若有）
    if updates:
        try:
            _project_app.update(UpdateProjectCommand(
                project_id=project_id,
                name=updates.get("name"),
                description=updates.get("description"),
                repo_url=updates.get("repo_url"),
                language=updates.get("language"),
                path=updates.get("path"),
            ))
        except AggregateNotFound:
            return fail("项目不存在", 404)
        except DomainValidationError as e:
            return fail(str(e), 400)

    # 2) 状态迁移（active/archived）经领域状态机
    if status is not None:
        if str(status) not in _MANAGEABLE_STATUSES:
            return fail(f"非法项目状态: {status}", 400)
        try:
            _project_app.change_status(ChangeStatusCommand(
                project_id=project_id, target_status=str(status),
            ))
        except AggregateNotFound:
            return fail("项目不存在", 404)
        except DomainValidationError as e:
            return fail(str(e), 400)

    item = _project_app.get(project_id)
    if item is None:
        return fail("项目不存在", 404)
    return ok(to_row(item))


@router.delete("/api/projects/{project_id}")
def front_api_delete_project(project_id: str):
    """前端删除项目（软删除，进入回收站）。"""
    try:
        _project_app.soft_delete(project_id)
    except (AggregateNotFound, DomainValidationError):
        # 项目已删除/不存在时保持原语义：返回成功（幂等）
        pass
    return ok({"success": True})


@router.get("/api/projects/{project_id}/stats")
def front_api_project_stats(project_id: str):
    """前端获取项目统计（聚合未承载，走既有读口径）。"""
    return ok(project_service.get_stats(project_id))
