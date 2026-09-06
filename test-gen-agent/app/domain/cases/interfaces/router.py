# app/routers/cases.py
"""用例管理路由（Phase 3 重构：从 main.py 拆分）。"""
import asyncio
import json
import tempfile
import time
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from app.core.response import fail, ok, read_body
from app.models.case import (
    CaseCreate,
    CaseDependencyAdd,
    CaseFunctionalIdBody,
    CaseFunctionalIdsBody,
    CaseFunctionalPageBody,
    CaseImportBody,
    CaseRelationAdd,
    CaseRequirementAdd,
    CaseRestoreBody,
    CaseReviewSubmit,
    CaseRollback,
    CaseTrashBody,
    CaseUpdate,
)
from app.domain.cases.application.case_app_service import case_service

router = APIRouter(tags=["cases"])


# ════════════════════════════════════════════════════════════
# 用例库管理 API
# ════════════════════════════════════════════════════════════

@router.get("/api/cases")
async def api_list_cases(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    test_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """列出测试用例，支持按状态/优先级/标签/关键词/测试类型过滤。"""
    cases = await asyncio.to_thread(
        case_service.list_cases,
        status=status, priority=priority, tag=tag,
        search=search, test_type=test_type, limit=limit, offset=offset,
    )
    total = await asyncio.to_thread(
        case_service.count_cases,
        status=status, priority=priority, tag=tag,
        search=search, test_type=test_type,
    )
    return ok({"cases": cases, "total": total})


@router.get("/api/cases/stats")
async def api_case_stats():
    """获取用例库统计。"""
    return ok(await asyncio.to_thread(case_service.get_stats))


@router.post("/api/cases")
async def api_create_case(payload: CaseCreate):
    """创建新用例。"""
    case = await asyncio.to_thread(case_service.create, payload.model_dump())
    return ok(case)


@router.get("/api/cases/mindmap")
async def api_get_case_mindmap_early(project_filter: str = ""):
    """获取用例脑图树形结构（优先路由）。"""
    tree = await asyncio.to_thread(case_service.get_mindmap, project_filter)
    return ok(tree)


@router.get("/api/cases/export")
async def api_export_cases_early(format: str = "excel"):
    """导出用例（优先路由）。format: excel/mindmap"""
    cases = await asyncio.to_thread(case_service.list_cases, limit=1000)
    if format == "excel":
        content = await asyncio.to_thread(case_service.export_excel, cases)
        filename = f"test_cases_export_{int(time.time())}.csv"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f:
            f.write(content)
            tmp_path = f.name
        return FileResponse(tmp_path, filename=filename,
                            media_type="text/csv; charset=utf-8")
    elif format == "mindmap":
        content = await asyncio.to_thread(case_service.export_mindmap, cases)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            f.write(content.encode("utf-8"))
            tmp_path = f.name
        return FileResponse(tmp_path, filename="test_cases_mindmap.json",
                            media_type="application/json")
    return fail("不支持的导出格式", 400)


@router.get("/api/cases/trash")
async def api_list_trash_cases_early():
    """列出回收站中的用例（优先路由）。"""
    trashes = await asyncio.to_thread(case_service.list_trash)
    return ok({"trash": trashes, "total": len(trashes)})


@router.get("/api/cases/{case_id}")
async def api_get_case(case_id: str):
    """获取单个用例。"""
    case = await asyncio.to_thread(case_service.get, case_id)
    if not case:
        return fail(f"case {case_id} 不存在", 404)
    return ok(case)


@router.put("/api/cases/{case_id}")
async def api_update_case(case_id: str, payload: CaseUpdate):
    """更新用例。"""
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "test_type" in updates:
        existing = await asyncio.to_thread(case_service.get, case_id)
        if existing:
            meta = existing.get("metadata", {}) or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except json.JSONDecodeError:
                    meta = {}
            meta["test_type"] = updates.pop("test_type")
            updates["metadata"] = json.dumps(meta, ensure_ascii=False)
    if "structured_cases" in updates and not isinstance(updates["structured_cases"], list):
        del updates["structured_cases"]
    try:
        case = case_service.update(case_id, **updates)
    except ValueError as e:
        return fail(str(e), 400)
    if not case:
        return fail(f"case {case_id} 不存在", 404)
    return ok(case)


@router.delete("/api/cases/{case_id}")
async def api_delete_case(case_id: str):
    """删除用例（软删除到回收站）。"""
    deleted = await asyncio.to_thread(case_service.soft_delete, case_id)
    if not deleted:
        return fail(f"case {case_id} 不存在", 404)
    return ok({"deleted": True, "trashed": True})


# ════════════════════════════════════════════════════════════
# 用例高级管理 API
# ════════════════════════════════════════════════════════════

@router.get("/api/cases/{case_id}/full")
async def api_get_case_full(case_id: str):
    """获取用例完整信息（含关联/依赖/评审/版本/变更/需求）。"""
    case = await asyncio.to_thread(case_service.get_full_info, case_id)
    if not case:
        return fail(f"case {case_id} 不存在", 404)
    return ok(case)


@router.post("/api/cases/{case_id}/relations")
async def api_add_case_relation(case_id: str, payload: CaseRelationAdd):
    """添加用例关联。"""
    try:
        rel = await asyncio.to_thread(
            case_service.add_relation,
            case_id,
            payload.related_case_id,
            payload.relation_type,
        )
        return ok(rel)
    except ValueError as e:
        return fail(str(e), 400)


@router.delete("/api/cases/{case_id}/relations/{related_id}")
async def api_remove_case_relation(case_id: str, related_id: str):
    """移除用例关联。"""
    removed = await asyncio.to_thread(case_service.remove_relation, case_id, related_id)
    if not removed:
        return fail("关联不存在", 404)
    return ok({"removed": True})


@router.get("/api/cases/{case_id}/relations")
async def api_list_case_relations(case_id: str):
    """列出用例的所有关联。"""
    relations = await asyncio.to_thread(case_service.list_relations, case_id)
    return ok({"relations": relations})


@router.post("/api/cases/import")
async def api_import_cases(payload: CaseImportBody):
    """导入用例。"""
    fmt = payload.format
    if fmt == "excel":
        result = await asyncio.to_thread(case_service.import_excel, payload.content, payload.operator)
    elif fmt == "mindmap":
        result = await asyncio.to_thread(case_service.import_mindmap, payload.content, payload.operator)
    else:
        return fail("不支持的导入格式", 400)
    return ok(result)


# 用例评审流程
@router.post("/api/cases/{case_id}/reviews/submit")
async def api_submit_case_review(case_id: str, payload: CaseReviewSubmit):
    """提交用例评审。"""
    try:
        result = await asyncio.to_thread(
            case_service.submit_review,
            case_id,
            reviewer=payload.reviewer,
            comment=payload.comment,
        )
        return ok(result)
    except ValueError as e:
        return fail(str(e), 400)


@router.post("/api/cases/{case_id}/reviews/approve")
async def api_approve_case_review(case_id: str, payload: CaseReviewSubmit):
    """通过用例评审。"""
    result = await asyncio.to_thread(
        case_service.approve_review,
        case_id,
        reviewer=payload.reviewer,
        comment=payload.comment,
    )
    return ok(result)


@router.post("/api/cases/{case_id}/reviews/reject")
async def api_reject_case_review(case_id: str, payload: CaseReviewSubmit):
    """驳回用例评审。"""
    result = await asyncio.to_thread(
        case_service.reject_review,
        case_id,
        reviewer=payload.reviewer,
        comment=payload.comment,
    )
    return ok(result)


@router.get("/api/cases/{case_id}/reviews")
async def api_get_case_reviews(case_id: str):
    """获取用例评审记录。"""
    reviews = await asyncio.to_thread(case_service.get_reviews, case_id)
    return ok({"reviews": reviews})


# 用例依赖关系
@router.post("/api/cases/{case_id}/dependencies")
async def api_add_case_dependency(case_id: str, payload: CaseDependencyAdd):
    """添加用例依赖。"""
    try:
        dep = await asyncio.to_thread(
            case_service.add_dependency,
            case_id,
            payload.depends_on,
            payload.dep_type,
            payload.description,
        )
        return ok(dep)
    except ValueError as e:
        return fail(str(e), 400)


@router.delete("/api/cases/{case_id}/dependencies/{depends_on}")
async def api_remove_case_dependency(case_id: str, depends_on: str):
    """移除用例依赖。"""
    removed = await asyncio.to_thread(case_service.remove_dependency, case_id, depends_on)
    if not removed:
        return fail("依赖不存在", 404)
    return ok({"removed": True})


@router.get("/api/cases/{case_id}/dependencies")
async def api_list_case_dependencies(case_id: str):
    """列出用例的所有依赖。"""
    deps = await asyncio.to_thread(case_service.list_dependencies, case_id)
    return ok({"dependencies": deps})


# 用例回收站
@router.post("/api/cases/{case_id}/trash")
async def api_soft_delete_case(case_id: str, payload: CaseTrashBody | None = None):
    """软删除用例到回收站。"""
    deleted = await asyncio.to_thread(
        case_service.soft_delete,
        case_id,
        deleted_by=(payload.deleted_by if payload else ""),
        reason=(payload.reason if payload else ""),
    )
    if not deleted:
        return fail(f"case {case_id} 不存在", 404)
    return ok({"deleted": True, "trashed": True})


@router.post("/api/cases/{case_id}/restore")
async def api_restore_case(case_id: str, payload: CaseRestoreBody | None = None):
    """从回收站恢复用例。"""
    restored = await asyncio.to_thread(case_service.restore, case_id, operator=(payload.operator if payload else ""))
    if not restored:
        return fail(f"case {case_id} 不在回收站中", 404)
    return ok({"restored": True})


@router.delete("/api/cases/{case_id}/purge")
async def api_purge_case(case_id: str):
    """从回收站彻底删除用例。"""
    purged = await asyncio.to_thread(case_service.purge, case_id)
    if not purged:
        return fail(f"case {case_id} 不存在", 404)
    return ok({"purged": True})


# 用例版本管理
@router.get("/api/cases/{case_id}/versions")
async def api_list_case_versions(case_id: str):
    """列出用例的所有版本。"""
    versions = await asyncio.to_thread(case_service.list_versions, case_id)
    return ok({"versions": versions})


@router.get("/api/cases/{case_id}/versions/{version}")
async def api_get_case_version(case_id: str, version: int):
    """获取指定版本快照。"""
    version_data = await asyncio.to_thread(case_service.get_version, case_id, version)
    if not version_data:
        return fail(f"版本 {version} 不存在", 404)
    return ok(version_data)


@router.post("/api/cases/{case_id}/rollback")
async def api_rollback_case(case_id: str, payload: CaseRollback):
    """回滚用例到指定版本。"""
    version = payload.version
    rolled_back = await asyncio.to_thread(
        case_service.rollback,
        case_id,
        version,
        operator=payload.operator,
    )
    if not rolled_back:
        return fail(f"版本 {version} 不存在", 404)
    return ok({"rolled_back": True, "version": version})


# 用例变更记录
@router.get("/api/cases/{case_id}/changes")
async def api_list_case_changes(case_id: str, limit: int = 50):
    """列出用例的变更记录。"""
    changes = await asyncio.to_thread(case_service.list_changes, case_id, limit=limit)
    total = await asyncio.to_thread(case_service.count_changes, case_id)
    return ok({"changes": changes, "total": total})


# 用例关联需求
@router.post("/api/cases/{case_id}/requirements")
async def api_add_case_requirement(case_id: str, payload: CaseRequirementAdd):
    """关联需求到用例。"""
    try:
        result = await asyncio.to_thread(
            case_service.add_requirement,
            case_id,
            requirement_id=payload.requirement_id,
            requirement_type=payload.requirement_type,
            requirement_title=payload.requirement_title,
            requirement_url=payload.requirement_url,
        )
        return ok(result)
    except ValueError as e:
        return fail(str(e), 400)


@router.delete("/api/cases/{case_id}/requirements/{requirement_id}")
async def api_remove_case_requirement(case_id: str, requirement_id: str):
    """移除需求关联。"""
    removed = await asyncio.to_thread(case_service.remove_requirement, case_id, requirement_id)
    if not removed:
        return fail("需求关联不存在", 404)
    return ok({"removed": True})


@router.get("/api/cases/{case_id}/requirements")
async def api_list_case_requirements(case_id: str):
    """列出用例关联的所有需求。"""
    requirements = await asyncio.to_thread(case_service.list_requirements, case_id)
    return ok({"requirements": requirements})


# ════════════════════════════════════════════════════════════
# 功能用例前端契约路由
# ------------------------------------------------------------
# 收敛迁移样板：原 app/adapters/domains/functional_cases.py 承载的
# TestPilot 前端路径（/functional/case/*）逐步迁移到业务域路由层。
#
# 迁移约定（对应 docs/refactoring-guide.md）：
#   - 业务逻辑一律落在 app/routers/cases.py（用例域），而非适配补丁文件
#   - handler 保持前端 {code, message, data, success} 契约与入参形态不变
#   - 迁移后从 adapters/domains/functional_cases.py 删除同名 handler，
#     保证"前端契约"与"后端路由"都在 routers/ 一处可溯源
#   - 验收：python3 scripts/route_conflict_check.py --check 与
#     python3 scripts/frontend_contract_check.py --check 均保持绿色
# ════════════════════════════════════════════════════════════

def _parse_case_request_body(body: dict) -> dict:
    """归一化前端用例请求字段（steps 可能是 JSON 字符串）。"""
    steps_val = body.get("steps", body.get("structured_cases"))
    if isinstance(steps_val, str):
        try:
            body["structured_cases"] = json.loads(steps_val)
        except (json.JSONDecodeError, TypeError):
            body["structured_cases"] = []
    elif steps_val is None:
        body["structured_cases"] = []
    elif isinstance(steps_val, list):
        body["structured_cases"] = steps_val
    return body


async def _read_case_body(request: Request) -> dict:
    """安全读取用例请求体，兼容 multipart/form-data 与 application/json。"""
    content_type = request.headers.get("content-type", "").lower()
    if "multipart/form-data" in content_type:
        form = await request.form()
        request_field = form.get("request")
        if request_field is None:
            return {}
        if hasattr(request_field, "read"):
            try:
                raw = await request_field.read()
                body = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
            except (json.JSONDecodeError, TypeError, AttributeError):
                body = {}
        else:
            try:
                body = json.loads(request_field)
            except (json.JSONDecodeError, TypeError):
                body = {}
    else:
        body = await read_body(request)
    return _parse_case_request_body(body)


@router.post("/functional/case/page")
async def functional_case_page(payload: CaseFunctionalPageBody):
    """功能用例分页列表（前端契约）。支持按 moduleIds 过滤。"""
    keyword = payload.keyword or ""
    page_size = payload.get_page_size()
    current = payload.get_page()
    module_ids = payload.effective_module_ids()

    # 收集所有用例以便按 metadata.module_id 过滤
    all_cases = await asyncio.to_thread(case_service.list_cases, limit=100000)

    # 按模块过滤: 需读取每个 case 的 metadata.module_id
    def _case_module_id(c: dict) -> str:
        meta = c.get("metadata", {}) or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                meta = {}
        return meta.get("module_id", "") or c.get("module_id", "") or "root"

    if module_ids and "root" not in module_ids:
        all_cases = [c for c in all_cases if _case_module_id(c) in module_ids]

    # 关键词过滤
    if keyword:
        kw = keyword.lower()
        all_cases = [
            c for c in all_cases
            if kw in (c.get("title", "") or "").lower()
            or kw in (c.get("description", "") or "").lower()
            or kw in (c.get("id", "") or "").lower()
        ]

    # 总数：从全量过滤后计算，确保与列表同口径
    total = len(all_cases)
    start = (current - 1) * page_size
    page_cases = all_cases[start:start + page_size]
    items = [case_service.to_functional_case(c) for c in page_cases]
    return ok({"list": items, "total": total, "pageSize": page_size, "current": current})


@router.post("/functional/case/add")
async def functional_case_add(request: Request):
    """添加功能用例（前端契约）。兼容 JSON 与 multipart/form-data。"""
    body = await _read_case_body(request)
    steps = body.get("structured_cases") or body.get("steps") or []
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except (json.JSONDecodeError, TypeError):
            steps = []
    meta = {}
    _mid = body.get("moduleId")
    if _mid is not None:
        meta["module_id"] = _mid
    if body.get("prerequisite") is not None:
        meta["prerequisite"] = body.get("prerequisite")
    if body.get("projectId"):
        meta["project_id"] = body.get("projectId")
    try:
        case = await asyncio.to_thread(
            case_service.create,
            {
                "title": body.get("name") or body.get("title", "未命名用例"),
                "description": body.get("description", ""),
                "source_code": body.get("sourceCode", body.get("source_code", "")),
                "file_path": body.get("filePath", body.get("file_path", "")),
                "status": body.get("status", "draft"),
                "priority": body.get("priority", "P2"),
                "test_type": body.get("testType", body.get("test_type", "functional")),
                "tags": body.get("tags", []),
                "metadata": meta,
                "structured_cases": steps,
            },
        )
    except Exception as e:
        return fail(f"创建失败: {str(e)[:100]}", 400)
    if not case:
        return fail("创建失败", 500)
    return ok(case_service.to_functional_case(case))


@router.post("/functional/case/update")
async def functional_case_update(request: Request):
    """更新功能用例（前端契约）。

    除名称/描述/优先级等基础字段外，同时持久化功能用例在“编辑”抽屉中
    可修改的模块（moduleId）、标签（tags）与前置条件（prerequisite）。
    这些字段之前会被静默丢弃，导致编辑后保存不生效（模块/标签/前置条件
    一刷新就被还原）。
    """
    body = await _read_case_body(request)
    case_id = body.get("id", "")
    if not case_id:
        return fail("缺少用例 id", 400)
    updates = {}
    # name 与 title 是同一字段的别名。前端展开 detail 时两个 key 同时存在，
    # 且编辑名称只覆盖 name 不覆盖 title；循环中两个 key 都会命中同一分支导致
    # 后者覆盖前者。故在循环前统一处理：name 存在时以 name 为准，否则用 title。
    _name_val = body.get("name")
    _title_val = body.get("title")
    if _name_val is not None:
        updates["title"] = _name_val
    elif _title_val is not None:
        updates["title"] = _title_val
    for k, v in body.items():
        if k in ("name", "title"):
            continue  # 已在上方统一处理
        elif k == "description":
            updates["description"] = v
        elif k == "status":
            updates["status"] = v
        elif k == "priority":
            updates["priority"] = v
        elif k == "testType":
            updates["test_type"] = v
        elif k == "sourceCode":
            updates["source_code"] = v
        elif k == "filePath":
            updates["file_path"] = v
        elif k == "tags":
            if v is not None:
                updates["tags"] = v if isinstance(v, list) else [v]
    steps_val = body.get("structured_cases") or body.get("steps")
    if steps_val is not None:
        if isinstance(steps_val, str):
            try:
                steps_val = json.loads(steps_val)
            except (json.JSONDecodeError, TypeError):
                steps_val = []
        updates["structured_cases"] = steps_val
    # 处理 customFields 中的 functional_priority -> 同步更新 priority
    if body.get("customFields") is not None:
        try:
            custom_fields = body.get("customFields") or []
            for cf in custom_fields:
                if isinstance(cf, dict):
                    fid = cf.get("fieldId", "")
                    if fid == "functional_priority" and cf.get("value"):
                        updates["priority"] = cf["value"]
        except Exception:
            pass
    # 模块 / 前置条件等无独立列字段收敛进 metadata，与“全部用例”根节点以外的
    # 模块归属、用例前置条件保持一致，避免编辑后被还原。
    existing = await asyncio.to_thread(case_service.get, case_id)
    if existing:
        try:
            meta = json.loads(existing.get("metadata") or "{}") \
                if isinstance(existing.get("metadata"), str) \
                else dict(existing.get("metadata") or {})
        except (json.JSONDecodeError, TypeError):
            meta = {}
        if body.get("moduleId") is not None:
            meta["module_id"] = body.get("moduleId")
        if body.get("prerequisite") is not None:
            meta["prerequisite"] = body.get("prerequisite")
        if meta:
            updates["metadata"] = meta
    try:
        case = await asyncio.to_thread(case_service.update, case_id, **updates)
    except ValueError as e:
        return fail(str(e), 400)
    except Exception:
        case = None
    if not case:
        return fail("用例不存在", 404)
    return ok(case_service.to_functional_case(case))


@router.post("/functional/case/delete")
async def functional_case_delete(payload: CaseFunctionalIdBody):
    """删除功能用例（前端契约，软删除进入回收站）。"""
    await asyncio.to_thread(case_service.soft_delete, payload.id, deleted_by="admin")
    return ok()


def _enrich_detail_counts(case_data: dict) -> dict:
    """为功能用例详情补充关联数量字段（前端详情抽屉需要）。"""
    enriched = dict(case_data)
    case_id = case_data.get("id", "")
    enriched["bugCount"] = 0
    enriched["caseCount"] = 0
    enriched["caseReviewCount"] = 0
    enriched["demandCount"] = 0
    enriched["relateEdgeCount"] = 0
    enriched["testPlanCount"] = 0
    enriched["commentCount"] = 0
    enriched["historyCount"] = 0
    # 从变更记录/版本表查询真实存在的数量（经 Service 层，避免路由直连 Repo）
    if case_id:
        try:
            enriched["historyCount"] = case_service.count_changes(case_id)
        except Exception:
            pass
    return enriched


@router.get("/functional/case/detail/{case_id}")
async def functional_case_detail(case_id: str):
    """获取功能用例详情（前端契约）。"""
    case = await asyncio.to_thread(case_service.get, case_id)
    if not case:
        return fail("用例不存在", 404)
    return ok(_enrich_detail_counts(case_service.to_functional_case(case)))


@router.post("/functional/case/detail")
async def functional_case_detail_post(payload: CaseFunctionalIdBody):
    """获取功能用例详情（POST 前端契约）。"""
    case = await asyncio.to_thread(case_service.get, payload.id) if payload.id else None
    if not case:
        return fail("用例不存在", 404)
    return ok(_enrich_detail_counts(case_service.to_functional_case(case)))


@router.post("/functional/case/batch/delete-to-gc")
async def functional_case_batch_delete(payload: CaseFunctionalIdsBody):
    """批量删除功能用例（前端契约）。"""
    ids = payload.effective_ids()
    if payload.selectAll and not ids:
        all_cases = await asyncio.to_thread(case_service.list_cases, limit=999)
        ids = [c["id"] for c in all_cases]
    deleted = 0
    for cid in ids:
        if await asyncio.to_thread(case_service.soft_delete, cid, deleted_by="admin"):
            deleted += 1
    return ok({"deleted": deleted})


@router.post("/functional/case/batch/copy")
async def functional_case_batch_copy(payload: CaseFunctionalIdsBody):
    """批量复制功能用例（前端契约）。"""
    ids = payload.effective_ids()
    copied = []
    for cid in ids:
        case = await asyncio.to_thread(case_service.get, cid)
        if not case:
            continue
        new_case = await asyncio.to_thread(
            case_service.create,
            {
                "title": f"{case.get('title', '')} (副本)",
                "description": case.get("description", ""),
                "priority": case.get("priority", "P2"),
                "test_type": case.get("test_type", "functional"),
                "structured_cases": case.get("structured_cases", []),
            },
        )
        if new_case:
            copied.append(new_case)
    return ok(copied)


@router.get("/functional/mind/case/list")
async def functional_mind_case_list():
    """获取功能用例脑图数据（前端契约）。"""
    cases = await asyncio.to_thread(case_service.list_cases, limit=500)
    tree = [{
        "id": c.get("id", ""),
        "text": c.get("title", ""),
        "resource": {"status": c.get("status", "draft"), "priority": c.get("priority", "P2")},
        "children": [],
    } for c in cases]
    return ok(tree)


@router.get("/functional/case/module/tree")
def functional_case_module_tree():
    """获取功能用例模块树（前端契约，真实实现）。"""
    return ok(case_service.build_functional_module_tree())

