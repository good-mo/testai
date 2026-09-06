# app/routers/defects_compat_extra.py
"""缺陷兼容路由补充段（自 app/routers/defects_compat.py 按业务域拆分，P4 超大文件拆分）。

主文件保留缺陷列表 / 增删改查等核心路由；本文件承载回收站 / 自定义字段 /
模板 / 评论 / 附件 / 关联用例 / 变更历史 / 同步 / 关注等补充路由。

纯路由搬移，行为不变：响应沿用主文件的 ok()/fail() 与统一 ok() 辅助函数。
"""

import json
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import NotFoundError
from app.core.response import fail, ok, read_body
from app.models.defect import (
    BugBatchIdsBody,
    BugBatchUpdateBody,
    BugCommentAddBody,
    BugCommentUpdateBody,
    BugIdBody,
    BugPageQuery,
)
from app.routers.defects_compat import (
    _build_comment_tree,
    _comment_to_frontend,
    _match_filters,
    _read_body,
    _resolve_batch_ids,
    _sort_items,
    _to_bug_item,
    _to_severity,
)
from app.services.auth_service import auth_service
from app.services.defect_service import defect_service

router = APIRouter(tags=["adapter-defects-extra"])


# ── 缺陷回收站 & 自定义字段 ──────────────────────────────


@router.post("/bug/trash/page")
async def bug_trash_page(body: BugPageQuery):
    """缺陷回收站分页列表。"""
    keyword = (body.keyword or "").strip()
    page_size = body.effective_page_size
    current = body.effective_current
    # 筛选条件（condition.filter / filter）
    filter_cond = body.effective_filter
    sort = body.sort or {}
    defects = defect_service.list_trashed(limit=9999, offset=0)
    db_total = defect_service.count_trashed()
    items = []
    for d in defects:
        item = _to_bug_item(d, in_trash=True)
        # 关键词过滤（标题 / 编号 / 处理人 / 删除人）
        if keyword:
            hay = " ".join(str(item.get(k, "")) for k in ("title", "num", "handleUserName", "deleteUserName", "id")).lower()
            if keyword.lower() not in hay:
                continue
        # 简单筛选条件
        if filter_cond:
            if not _match_filters(item, filter_cond):
                continue
        items.append(item)
    # 排序：默认按删除时间倒序，支持 sort 指定字段
    items = _sort_items(items, sort)
    # 无过滤时用 DB 真实总数，有过滤时从过滤结果计算
    total = len(items) if (keyword or filter_cond) else db_total
    start = (current - 1) * page_size
    page_items = items[start:start + page_size]
    return ok({
            "list": page_items,
            "total": total,
            "pageSize": page_size,
            "current": current,
        })


@router.post("/bug/recover")
async def bug_recover(body: BugIdBody):
    """恢复缺陷。body: {id}"""
    bug_id = body.effective_id
    try:
        defect_service.restore(bug_id)
    except NotFoundError:
        return fail("缺陷不在回收站中", code=404)
    return ok(None)


@router.post("/bug/trash/recover/{bug_id}")
def bug_trash_recover_path(bug_id: str):
    """单个恢复缺陷。"""
    try:
        defect_service.restore(bug_id)
    except NotFoundError:
        pass
    return ok(None)


@router.get("/bug/trash/recover/{bug_id}")
def bug_trash_recover_get(bug_id: str):
    """单个恢复缺陷（GET）。"""
    try:
        defect_service.restore(bug_id)
    except NotFoundError:
        pass
    return ok(None)


@router.get("/bug/trash/delete/{bug_id}")
def bug_trash_delete_get(bug_id: str):
    """单个彻底删除缺陷（GET）。"""
    try:
        defect_service.purge(bug_id)
    except NotFoundError:
        pass
    return ok(None)


@router.post("/bug/trash/batch-recover")
async def bug_trash_batch_recover(body: BugBatchIdsBody):
    """批量恢复缺陷。body: {selectIds: [], selectAll, excludeIds} 或旧式 {ids: []}"""
    ids = _resolve_batch_ids({
        "selectAll": body.select_all,
        "selectIds": body.selected_ids,
        "excludeIds": body.excluded_ids,
        "ids": body.legacy_ids,
    })
    for bug_id in ids:
        try:
            defect_service.restore(bug_id)
        except Exception:
            pass
    return ok(None)


@router.post("/bug/delete")
async def bug_delete_standard(body: BugIdBody):
    """标准删除缺陷（移入回收站）。body: {id}"""
    bug_id = body.effective_id
    try:
        defect_service.trash(bug_id)
    except NotFoundError:
        pass
    return ok(None)


@router.post("/bug/trash/delete/{bug_id}")
def bug_trash_delete_path(bug_id: str):
    """单个彻底删除缺陷。"""
    try:
        defect_service.purge(bug_id)
    except NotFoundError:
        pass
    return ok(None)


@router.post("/bug/trash/batch-delete")
async def bug_trash_batch_delete(body: BugBatchIdsBody):
    """批量彻底删除缺陷。body: {selectIds: [], selectAll, excludeIds} 或旧式 {ids: []}"""
    ids = _resolve_batch_ids({
        "selectAll": body.select_all,
        "selectIds": body.selected_ids,
        "excludeIds": body.excluded_ids,
        "ids": body.legacy_ids,
    })
    for bug_id in ids:
        try:
            defect_service.purge(bug_id)
        except Exception:
            pass
    return ok(None)


def _member_options() -> List[Dict[str, str]]:
    """获取成员选项（处理人下拉）。"""
    try:
        users = auth_service.list_users()
        return [
            {"value": u.get("id", ""), "text": u.get("name") or u.get("username", "")}
            for u in users
        ]
    except Exception:
        return [{"value": "admin", "text": "admin"}]


def _bug_system_custom_fields() -> List[Dict[str, Any]]:
    """缺陷表头系统字段（含前端 BugEditCustomField 所需字段）。"""
    status_options = [
        {"value": "open", "text": "待处理"},
        {"value": "in_progress", "text": "处理中"},
        {"value": "fixed", "text": "已修复"},
        {"value": "closed", "text": "已关闭"},
        {"value": "wont_fix", "text": "不修复"},
    ]
    severity_options = [
        {"value": "blocker", "text": "阻断"},
        {"value": "critical", "text": "致命"},
        {"value": "major", "text": "严重"},
        {"value": "minor", "text": "一般"},
        {"value": "trivial", "text": "轻微"},
    ]
    return [
        {
            "fieldId": "status",
            "fieldKey": "status",
            "fieldName": "状态",
            "name": "状态",
            "id": "status",
            "key": "status",
            "type": "SELECT",
            "required": True,
            "show": True,
            "enable": True,
            "value": "",
            "internal": True,
            "supportSearch": True,
            "optionMethod": "",
            "apiFieldId": "",
            "defaultValue": "open",
            "options": status_options,
            "platformOptionJson": json.dumps(status_options, ensure_ascii=False),
            "platformSystemField": False,
        },
        {
            "fieldId": "severity",
            "fieldKey": "severity",
            "fieldName": "严重程度",
            "name": "严重程度",
            "id": "severity",
            "key": "severity",
            "type": "SELECT",
            "required": True,
            "show": True,
            "enable": True,
            "value": "",
            "internal": True,
            "supportSearch": True,
            "optionMethod": "",
            "apiFieldId": "",
            "defaultValue": "major",
            "options": severity_options,
            "platformOptionJson": json.dumps(severity_options, ensure_ascii=False),
            "platformSystemField": False,
        },
        {
            "fieldId": "assignee",
            "fieldKey": "assignee",
            "fieldName": "处理人",
            "name": "处理人",
            "id": "assignee",
            "key": "assignee",
            "type": "MEMBER",
            "required": False,
            "show": True,
            "enable": True,
            "value": "",
            "internal": True,
            "supportSearch": True,
            "optionMethod": "",
            "apiFieldId": "",
            "defaultValue": "",
            "options": _member_options(),
            "platformOptionJson": json.dumps(_member_options(), ensure_ascii=False),
            "platformSystemField": False,
        },
    ]


@router.get("/bug/header/custom-field/{project_id}")
def bug_header_custom_field_path(project_id: str):
    """获取缺陷表头自定义字段。"""
    return ok(_bug_system_custom_fields())


@router.get("/bug/columns-option/{project_id}")
def bug_columns_option(project_id: str):
    """获取缺陷列显示配置。"""
    return ok([
        {"key": "id", "label": "ID", "show": True, "order": 1},
        {"key": "title", "label": "标题", "show": True, "order": 2},
        {"key": "status", "label": "状态", "show": True, "order": 3},
        {"key": "severity", "label": "严重程度", "show": True, "order": 4},
        {"key": "assignee", "label": "处理人", "show": True, "order": 5},
        {"key": "createUser", "label": "创建人", "show": True, "order": 6},
        {"key": "createTime", "label": "创建时间", "show": True, "order": 7},
        {"key": "updateTime", "label": "更新时间", "show": True, "order": 8},
    ])


# ════════════════════════════════════════════════════════════
# 接口定义管理适配
# 前端: /api/definition/*  →  后端: /api/apitest/*
# ════════════════════════════════════════════════════════════


@router.get("/bug/current-platform")
def bug_current_platform():
    """获取当前缺陷平台。"""
    return ok("Local")


@router.get("/bug/check-exist/{bug_id}")
def bug_check_exist_path(bug_id: str):
    """检查缺陷是否存在。"""
    try:
        defect = defect_service.get(bug_id)
        return ok(defect is not None)
    except Exception:
        return ok(False)


@router.get("/bug/template/option")
def bug_template_option():
    """获取缺陷模板选项。"""
    return ok([])


@router.get("/bug/template/detail")
def bug_template_detail():
    """获取缺陷模板详情。返回结构化模板数据，避免前端读取 customFields 时崩溃。"""
    return ok({
        "id": "default-bug-template",
        "name": "默认缺陷模板",
        "description": "系统默认缺陷模板",
        "platform": "Local",
        "enable": True,
        "enableDefault": True,
        "scene": "BUG",
        "platformDefault": False,
        "systemFields": [],
        "customFields": _bug_system_custom_fields(),
    })


@router.post("/bug/comment/add")
async def bug_comment_add(request: Request, body: BugCommentAddBody):
    """添加缺陷评论。"""
    bug_id = body.effective_bug_id
    content = body.content
    if not bug_id or not content:
        return JSONResponse({"code": 400, "message": "缺陷ID和评论内容不能为空", "data": None})
    create_user = ""
    try:
        from app.auth.dependencies import get_current_user as _get_user
        user = _get_user(request)
        if user:
            create_user = user.get("id") or user.get("username") or ""
    except Exception:
        create_user = ""
    if not defect_service.get(bug_id):
        return fail("缺陷不存在", code=404)
    comment = defect_service.create_comment(
        bug_id=bug_id,
        content=content,
        parent_id=body.effective_parent_id,
        create_user=create_user,
        reply_user=body.replyUser,
        notifier=body.notifier,
    )
    return ok(_comment_to_frontend(comment, []))


@router.get("/bug/comment/get/{bug_id}")
def bug_comment_get(bug_id: str):
    """获取缺陷评论列表。"""
    comments = defect_service.list_comments(bug_id)
    return ok(_build_comment_tree(comments))


@router.post("/bug/export")
async def bug_export(request: Request):
    """导出缺陷。"""
    await read_body(request)
    return ok({
        "taskId": str(uuid.uuid4()),
    })


@router.post("/bug/batch-update")
async def bug_batch_update(body: BugBatchUpdateBody):
    """批量更新缺陷（消灭假成功）。

    前端批量编辑（batchEditModal）会提交：
      { selectIds/selectAll/excludeIds, projectId,
        [attribute]: value|inputValue, append, clear }
    其中 attribute 为 tags 或系统字段(severity/status/assignee)对应的
    自定义字段 fieldId。逐条真实落库更新，返回受影响数量。
    """
    # 解析目标缺陷（排除回收站的有效缺陷）
    select_all = body.select_all
    select_ids = body.selected_ids
    exclude_ids = body.excluded_ids
    ids = body.legacy_ids

    if select_all:
        all_defects, _ = defect_service.list(limit=9999, offset=0)
        target_ids = [
            d["id"] for d in all_defects
            if d.get("id") not in set(exclude_ids or [])
        ]
    else:
        target_ids = [i for i in (select_ids or ids) if i]

    # 提取要批量设置的字段
    attribute = body.effective_attribute or ""
    _extra = body.model_extra or {}
    value = body.effective_value
    if value is None and attribute in _extra:
        value = _extra[attribute]
    if attribute in ("tags",) and body.clear:
        value = []
    if attribute not in ("tags",) and isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    if value is None:
        value = ""
    if isinstance(value, list):
        value = [str(v) for v in value]

    # 系统字段 → 顶层列
    field_key = attribute
    if attribute in ("severity", "status", "assignee", "handleUser"):
        field_key = "assignee" if attribute == "handleUser" else attribute
    if field_key == "severity":
        value = _to_severity(str(value))

    updates: Dict[str, Any] = {}
    if field_key in ("tags", "severity", "status", "assignee"):
        updates[field_key] = value

    updated = 0
    for bug_id in target_ids:
        patch = dict(updates)
        if not patch:
            break
        # tags 追加/覆盖语义
        if "tags" in patch:
            try:
                defect = defect_service.get(bug_id)
            except Exception:
                defect = None
            if not defect:
                continue
            cur = defect.get("tags") or []
            if isinstance(cur, str):
                try:
                    cur = json.loads(cur)
                except Exception:
                    cur = []
            if body.append:
                merged = list(cur)
                for t in patch["tags"]:
                    if t not in merged:
                        merged.append(t)
                patch["tags"] = merged
            elif body.clear:
                patch["tags"] = []
        try:
            defect_service.update(bug_id, patch)
            updated += 1
        except Exception:
            continue
    return ok({"updated": updated})


# ════════════════════════════════════════════════════════════
# 用例评审适配
# 前端: /case/review/*  →  用例评审管理
# ════════════════════════════════════════════════════════════


@router.post("/bug/attachment/transfer")
def bug_attachment_transfer(request: Request):
    """转存缺陷附件。"""
    return ok(None)


@router.get("/bug/attachment/transfer/options/{project_id}")
def bug_attachment_transfer_options_path(project_id: str):
    """获取缺陷附件转存目录。"""
    return ok([])


@router.get("/bug/attachment/preview")
def bug_attachment_preview():
    """预览缺陷附件。"""
    return ok(None)


@router.get("/bug/attachment/download")
def bug_attachment_download():
    """下载缺陷附件。"""
    return ok(None)


@router.get("/bug/attachment/check-update")
def bug_attachment_check_update():
    """检查缺陷附件是否更新。"""
    return ok({"hasUpdate": False})


@router.post("/bug/attachment/update")
def bug_attachment_update(request: Request):
    """更新缺陷附件。"""
    return ok(None)


@router.post("/bug/attachment/file/page")
def bug_attachment_file_page(request: Request):
    """获取缺陷关联文件列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.get("/bug/attachment/preview/md")
def bug_editor_preview_file():
    """预览富文本图片。"""
    return ok(None)


# 缺陷关联用例


@router.get("/bug/case/page")
def bug_case_page():
    """获取缺陷关联的用例列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.post("/bug/case/page")
def bug_case_page_post(request: Request):
    """获取缺陷关联的用例列表（POST）。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.post("/bug/case/relate")
def bug_case_relate(request: Request):
    """批量添加缺陷关联用例。"""
    return ok(None)


@router.get("/bug/case/un-relate")
def bug_case_un_relate():
    """单个取消缺陷关联用例。"""
    return ok(None)


@router.post("/bug/case/un-relate/page")
def bug_case_un_relate_page(request: Request):
    """获取未关联的用例列表。"""
    return ok({
        "list": [],
        "total": 0,
    })


@router.get("/bug/case/un-relate/module/tree")
def bug_case_un_relate_module_tree():
    """获取未关联用例模块树。"""
    return ok([])


@router.get("/bug/case/un-relate/module/count")
def bug_case_un_relate_module_count():
    """获取未关联用例模块数量。"""
    return ok([])


@router.get("/bug/case/check-permission")
def bug_case_check_permission():
    """缺陷用例跳转权限检查。"""
    return ok(True)


# 缺陷变更历史


@router.post("/bug/history/page")
async def bug_history_page(request: Request):
    """获取缺陷变更历史。"""
    await read_body(request)
    return ok({
        "list": [],
        "total": 0,
    })


@router.get("/bug/history/page")
def bug_history_page_get():
    """获取缺陷变更历史（GET）。"""
    return ok({
        "list": [],
        "total": 0,
    })


# 缺陷回收站


@router.get("/bug/follow/{bug_id}")
def bug_follow_path(bug_id: str):
    """关注缺陷。

    消灭假成功：接入真实关注落库（api_follows, resource_type=bug）。
    """
    from app.services.apitest_service import apitest_service as _apitest
    try:
        ok_flag = bool(_apitest.follow_resource("bug", bug_id))
    except Exception:
        ok_flag = False
    return ok({"id": bug_id, "followed": ok_flag})


@router.get("/bug/unfollow/{bug_id}")
def bug_unfollow_path(bug_id: str):
    """取消关注缺陷。

    消灭假成功：接入真实取关落库（api_follows, resource_type=bug）。
    """
    from app.services.apitest_service import apitest_service as _apitest
    try:
        ok_flag = bool(_apitest.unfollow_resource("bug", bug_id))
    except Exception:
        ok_flag = False
    return ok({"id": bug_id, "unfollowed": ok_flag})


# 缺陷模板相关补充


@router.get("/bug/template/option/{project_id}")
def bug_template_option_project(project_id: str):
    """获取项目缺陷模板选项。前端期望 [TemplateOption] 结构。"""
    return ok([
        {
            "id": "default-bug-template",
            "name": "默认缺陷模板",
            "enableDefault": True,
            "platform": "Local",
        }
    ])


@router.post("/bug/template/detail")
async def bug_template_detail_post(request: Request):
    """获取缺陷模板详情（POST）。返回结构化模板数据，避免前端读取 customFields 时崩溃。"""
    try:
        await _read_body(request)
    except Exception:
        pass
    return ok({
        "id": "default-bug-template",
        "name": "默认缺陷模板",
        "description": "系统默认缺陷模板",
        "platform": "Local",
        "enable": True,
        "enableDefault": True,
        "scene": "BUG",
        "platformDefault": False,
        "systemFields": [],
        "customFields": _bug_system_custom_fields(),
    })


@router.get("/bug/export/columns/{project_id}")
def bug_export_columns_path(project_id: str):
    """获取缺陷导出字段配置。前端期望一组导出列定义。"""
    return ok([
        {"key": "num", "text": "ID"},
        {"key": "title", "text": "缺陷名称"},
        {"key": "statusName", "text": "状态"},
        {"key": "severity", "text": "严重程度"},
        {"key": "handleUser", "text": "处理人"},
        {"key": "platform", "text": "所属平台"},
        {"key": "tags", "text": "标签"},
        {"key": "createUserName", "text": "创建人"},
        {"key": "createTime", "text": "创建时间"},
        {"key": "updateUserName", "text": "更新人"},
        {"key": "updateTime", "text": "更新时间"},
        {"key": "description", "text": "描述"},
    ])


# 缺陷评论更新/删除


@router.post("/bug/comment/update")
async def bug_comment_update(body: BugCommentUpdateBody):
    """更新缺陷评论。"""
    comment_id = body.effective_comment_id
    content = body.content
    if not comment_id:
        return JSONResponse({"code": 400, "message": "评论ID不能为空", "data": None})
    comment = defect_service.update_comment(comment_id, content)
    if not comment:
        return fail("评论不存在", code=404)
    return ok(_comment_to_frontend(comment, []))


@router.get("/bug/comment/delete/{comment_id}")
def bug_comment_delete(comment_id: str):
    """删除缺陷评论。"""
    deleted = defect_service.delete_comment(comment_id)
    return ok({"deleted": deleted})


# 缺失接口补充 - 功能用例高级功能
# ════════════════════════════════════════════════════════════

# 脑图编辑


@router.get("/bug/sync/{project_id}")
def bug_sync_path(project_id: str):
    """同步缺陷（开源版）。"""
    return ok({
        "status": "COMPLETED",
        "count": 0,
    })


@router.post("/bug/sync/all")
def bug_sync_all(request: Request):
    """同步缺陷（企业版）。"""
    return ok(None)


@router.get("/bug/sync/check/{project_id}")
def bug_sync_check(project_id: str):
    """获取同步状态。前端期望 {complete: bool, msg: str}。"""
    return ok({
        "complete": True,
        "msg": "同步已完成",
    })


    """导出缺陷。"""
    return ok(None)


@router.get("/bug/current-platform/{project_id}")
def bug_current_platform_project(project_id: str):
    """获取项目缺陷平台。"""
    return ok("Local")


@router.get("/bug/header/columns-option/{project_id}")
def bug_header_columns_option_path(project_id: str):
    """获取表头字段选项。前端期望 {userOption, handleUserOption, statusOption}。"""
    user_option = []
    try:
        users = auth_service.list_users()
        user_option = [
            {"value": u.get("id", ""), "text": u.get("name") or u.get("username", "")}
            for u in users
        ]
    except Exception:
        user_option = [{"value": "admin", "text": "admin"}]

    handle_user_option = [
        {"value": item["value"], "text": item["text"]}
        for item in user_option
    ]
    status_option = [
        {"value": "open", "text": "待处理"},
        {"value": "in_progress", "text": "处理中"},
        {"value": "fixed", "text": "已修复"},
        {"value": "closed", "text": "已关闭"},
        {"value": "wont_fix", "text": "不修复"},
    ]
    return ok({
        "userOption": user_option,
        "handleUserOption": handle_user_option,
        "statusOption": status_option,
    })


# ════════════════════════════════════════════════════════════
# 缺失接口补充 - 功能用例 AI 功能
# ════════════════════════════════════════════════════════════



# ════════════════════════════════════════════════════════════
# 路径参数兼容路由（自 path_param_fixes.py 迁移）
# ════════════════════════════════════════════════════════════

@router.get("/dashboard/bug_handle_user/list/{projectId}")
@router.post("/dashboard/bug_handle_user/list/{projectId}")
def dashboard_bug_handle_user_list_path(projectId: str):
    """/dashboard/bug_handle_user/list 带路径参数（前端 RESTful 调用兼容）。"""
    return ok({"list": [], "total": 0})
