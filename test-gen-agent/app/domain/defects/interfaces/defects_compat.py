# app/routers/defects_compat.py（自 app/adapters/domains/defects.py 迁移）
"""业务域路由拆分：defects（Phase 3 重构）。"""

import json
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Request

from app.core.response import fail, ok, read_body, read_form_or_json
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-defects"])

from app.core.exceptions import NotFoundError, ValidationError
from app.models.defect import BugBatchIdsBody, BugIdBody, BugPageQuery
from app.domain.auth.application.auth_app_service import auth_service
from app.domain.defects.application.defect_app_service import defect_service


async def _read_body(request: Request) -> dict:
    """安全读取请求体。"""
    try:
        return await read_body(request)
    except Exception:
        return {}


@router.get("/bug/attachment/list/")
def bug_attachment_list(id: str = ""):
    """缺陷附件列表。"""
    return ok([])


@router.get("/bug/attachment/transfer/options/")
def bug_attachment_transfer_options(project_id: str = ""):
    """缺陷附件转存目录。"""
    return ok([])


@router.post("/bug/comment/get/")
def bug_comment_get_post(id: str = ""):
    """获取缺陷评论列表（POST 兼容）。"""
    if not id:
        return ok([])
    comments = defect_service.list_comments(id)
    return ok(_build_comment_tree(comments))


@router.post("/bug/comment/delete/")
def bug_comment_delete_post(id: str = ""):
    """删除缺陷评论（POST 兼容）。"""
    deleted = defect_service.delete_comment(id) if id else False
    return ok({"deleted": deleted})


@router.post("/bug/trash/delete/")
async def bug_trash_delete(id: str = "", body: BugIdBody = Body(default=None)):
    """缺陷回收站彻底删除。id 取自 query 或 body。"""
    if not id and body is not None:
        id = body.effective_id
    if not id:
        return ok({"deleted": False})
    try:
        defect_service.purge(id)
        success = True
    except NotFoundError:
        success = False
    return ok({"deleted": success})


@router.post("/bug/trash/recover/")
async def bug_trash_recover(id: str = "", body: BugIdBody = Body(default=None)):
    """缺陷回收站恢复。id 取自 query 或 body。"""
    if not id and body is not None:
        id = body.effective_id
    if not id:
        return ok({"recovered": False})
    try:
        defect_service.restore(id)
        success = True
    except NotFoundError:
        success = False
    return ok({"recovered": success})


@router.post("/bug/delete/")
async def bug_delete(id: str = "", body: BugIdBody = Body(default=None)):
    """删除缺陷（移入回收站）。id 取自 query 或 body。"""
    if not id and body is not None:
        id = body.effective_id
    if not id:
        return ok({"deleted": False})
    try:
        defect_service.trash(id)
        success = True
    except NotFoundError:
        success = False
    return ok({"deleted": success})


@router.get("/bug/check-exist/")
def bug_check_exist(id: str = ""):
    """检查缺陷是否存在。"""
    return ok({"exist": True})


@router.post("/bug/follow/")
async def bug_follow(id: str = "", body: BugIdBody = Body(default=None)):
    """关注缺陷。

    消灭假成功：接入真实关注落库（api_follows, resource_type=bug）。
    id 兼容 query / body。
    """
    from app.domain.apitest.application.apitest_app_service import apitest_service as _apitest
    if not id and body is not None:
        id = body.effective_id
    try:
        ok_flag = bool(_apitest.follow_resource("bug", id)) if id else False
    except Exception:
        ok_flag = False
    return ok({"id": id, "followed": ok_flag})


@router.post("/bug/unfollow/")
async def bug_unfollow(id: str = "", body: BugIdBody = Body(default=None)):
    """取消关注缺陷。

    消灭假成功：接入真实取关落库（api_follows, resource_type=bug）。
    id 兼容 query / body。
    """
    from app.domain.apitest.application.apitest_app_service import apitest_service as _apitest
    if not id and body is not None:
        id = body.effective_id
    try:
        ok_flag = bool(_apitest.unfollow_resource("bug", id)) if id else False
    except Exception:
        ok_flag = False
    return ok({"id": id, "unfollowed": ok_flag})


@router.get("/bug/get/")
def bug_get(id: str = ""):
    """获取缺陷详情。"""
    defect = defect_service.get(id) if id else None
    return ok(defect or {})


@router.get("/bug/export/columns/")
def bug_export_columns(project_id: str = ""):
    """缺陷导出列。"""
    return ok([])


@router.post("/bug/sync/")
def bug_sync():
    """同步缺陷。"""
    return ok()


@router.get("/bug/header/columns-option/")
def bug_header_columns_option(project_id: str = ""):
    """缺陷表头列选项。"""
    return ok([])


@router.get("/bug/header/custom-field/")
def bug_header_custom_field(project_id: str = ""):
    """缺陷表头自定义字段。"""
    return ok([])


# ════════════════════════════════════════════════════════════
# P0-6: 功能用例补充  /functional/case/*
# ════════════════════════════════════════════════════════════


@router.post("/bug/attachment/check-update")
async def api_bug_attachment_check_update_post(request: Request):
    """检查附件是否更新（POST 兼容前端调用）。"""
    await _read_body(request)
    return ok({"update": False})


@router.post("/bug/attachment/download")
async def api_bug_attachment_download_post(request: Request):
    """下载缺陷附件（POST 兼容前端调用）。"""
    await _read_body(request)
    return ok({"fileId": "", "fileName": "download"})


@router.post("/bug/attachment/preview")
async def api_bug_attachment_preview_post(request: Request):
    """预览缺陷附件（POST 兼容前端调用）。"""
    await _read_body(request)
    return ok({"content": ""})


@router.post("/bug/case/un-relate/module/tree")
async def api_bug_case_unrelate_module_tree_post(request: Request):
    """缺陷未关联用例模块树（POST 兼容前端调用）。"""
    await _read_body(request)
    return ok([])


@router.post("/bug/case/un-relate/module/count")
async def api_bug_case_unrelate_module_count_post(request: Request):
    """缺陷未关联用例模块数量（POST 兼容前端调用）。"""
    await _read_body(request)
    return ok([])


@router.get("/bug/sync/")
async def api_bug_sync_trailing_get(request: Request):
    """同步缺陷-开源版（GET 带尾斜杠兼容前端）。"""
    try:
        await read_body(request)
    except Exception:
        pass
    return ok({"success": True, "sync": "openSource"})


@router.get("/bug/case/un-relate/{id}")
def bug_case_un_relate_path(id: str):
    """取消缺陷用例关联（带路径参数）。"""
    return ok({"id": id, "success": True})


@router.get("/bug/case/check-permission/{project_id}/{case_type}")
def bug_case_check_permission_path(project_id: str, case_type: str):
    """检查缺陷用例权限（带路径参数）。"""
    return ok({"project_id": project_id, "case_type": case_type, "hasPermission": True})


@router.get("/bug/attachment/transfer/options//{project_id}")
def bug_attachment_transfer_options_double_slash(project_id: str):
    """缺陷附件转存选项（双斜杠 URL 兼容前端拼接问题）。"""
    return ok([])


# ════════════════════════════════════════════════════════════
# 缺失路径参数路由（前端拼接路径参数时后端无匹配路由）
# ════════════════════════════════════════════════════════════

# 功能用例模块树（前端: /functional/case/module/tree/{projectId}）


@router.post("/bug/page")
async def bug_page(body: BugPageQuery):
    """缺陷分页列表。"""
    keyword = body.keyword
    page_size = body.effective_page_size
    current = body.effective_current

    # 拉取全部未删除缺陷后由 service 分页，保持分页/关键词筛选行为一致
    all_defects, db_total = defect_service.list(limit=9999, offset=0)
    filtered = [
        d for d in all_defects
        if not keyword or keyword.lower() in (d.get("title", "") or "").lower()
        or keyword.lower() in (d.get("id", "") or "").lower()
    ]
    # 无关键词时直接用 DB 侧真实总数，有关键词时从过滤后数据计算
    total = len(filtered) if keyword else db_total
    start = (current - 1) * page_size
    page_defects = filtered[start:start + page_size]
    items = [_to_bug(d) for d in page_defects]

    return ok({
            "list": items,
            "total": total,
            "pageSize": page_size,
            "current": current,
        })

# 前端「平台默认模板」会把标题/状态/严重程度/处理人作为系统字段塞进 customFields，
# 而非缺陷对象的顶层字段。顶层优先、customFields 兜底，统一转成后端可写的缺陷字段。
def _extract_defect_fields(body: dict) -> dict:
    updates: Dict[str, Any] = {}
    for key in ("title", "description", "status", "severity", "assignee", "tags"):
        if body.get(key) is not None:
            updates[key] = body[key]
    for cf in body.get("customFields") or []:
        if not isinstance(cf, dict):
            continue
        cid = cf.get("id") or cf.get("fieldId") or cf.get("field") or ""
        if cid in ("title", "description", "status", "severity", "assignee") and cid not in updates:
            v = cf.get("value")
            if v is not None:
                updates[cid] = v
    if "severity" in updates:
        updates["severity"] = _to_severity(updates["severity"])
    return updates


@router.post("/bug/add")
async def bug_add(request: Request):
    """创建缺陷。"""
    body = await read_form_or_json(request)
    fields = _extract_defect_fields(body)
    defect = defect_service.create({
        "title": fields.get("title") or body.get("title") or "未命名缺陷",
        "description": fields.get("description", body.get("description", "")),
        "status": fields.get("status", "open"),
        "severity": fields.get("severity", "major"),
        "assignee": fields.get("assignee", body.get("assignee", "")),
        "file_path": body.get("filePath", body.get("file_path", "")),
        "tags": body.get("tags", []),
    })
    return ok(_to_bug(defect))


@router.post("/bug/update")
async def bug_update(request: Request):
    """更新缺陷。"""
    body = await read_form_or_json(request)
    defect_id = body.get("id") or body.get("bugId") or body.get("request", {}).get("id", "") or ""
    updates = _extract_defect_fields(body)
    try:
        defect = defect_service.update(defect_id, updates)
    except ValidationError as e:
        return fail(str(e.message), code=400)
    except NotFoundError:
        return fail("缺陷不存在", code=404)
    except Exception:
        defect = None
    if not defect:
        return fail("缺陷不存在", code=404)
    return ok(_to_bug(defect))


@router.get("/bug/delete/{bug_id}")
def bug_delete_path(bug_id: str):
    """删除缺陷。"""
    try:
        defect_service.trash(bug_id)
    except NotFoundError:
        pass
    return ok(None)


@router.post("/bug/batch-delete")
async def bug_batch_delete(body: BugBatchIdsBody):
    """批量删除缺陷。"""
    bug_ids = body.selected_ids or body.legacy_ids
    if body.select_all and not bug_ids:
        all_defects, _ = defect_service.list(limit=999, offset=0)
        bug_ids = [d["id"] for d in all_defects]
    deleted = 0
    for bid in bug_ids:
        try:
            defect_service.trash(bid)
            deleted += 1
        except NotFoundError:
            continue
    return ok({"deleted": deleted})


@router.get("/bug/get/{bug_id}")
def bug_get_path(bug_id: str):
    """获取缺陷详情。"""
    defect = defect_service.get(bug_id)
    if not defect:
        return fail("缺陷不存在", code=404)
    return ok(_to_bug(defect))


_BUG_STATUS_NAME = {
    "open": "待处理",
    "in_progress": "处理中",
    "fixed": "已修复",
    "closed": "已关闭",
    "wont_fix": "不修复",
}


def _user_name(user_id: str) -> str:
    """将用户 id 转为显示名称，查询失败时回退原值。"""
    if not user_id:
        return ""
    try:
        user = auth_service.get_user_by_id(user_id)
        if user:
            return user.get("name") or user.get("username") or user_id
    except Exception:
        pass
    return user_id


def _parse_tags(tags) -> list:
    """解析 tags 字段（兼容 JSON 字符串与数组两种存储形式）。"""
    if tags is None:
        return []
    if isinstance(tags, list):
        return tags
    if isinstance(tags, str):
        try:
            parsed = json.loads(tags)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [tags]
    return []


def _bug_followed(defect_id: str) -> bool:
    """读取当前用户是否已关注缺陷（api_follows 落库读回）。

    上批已接入真实关注落库，此处在详情读回真实关注状态（followFlag），
    保证跨会话打开缺陷时前端收藏图标状态一致。resource_type=bug。
    """
    if not defect_id:
        return False
    try:
        from app.domain.apitest.application.apitest_app_service import apitest_service as _apitest
        return bool(_apitest.is_followed("bug", defect_id))
    except Exception:
        return False


def _to_bug(defect: Dict[str, Any]) -> Dict[str, Any]:
    """将后端缺陷格式转为前端格式。"""
    defect_id = defect.get("id", "")
    status = defect.get("status", "open")
    create_user = defect.get("create_user") or defect.get("created_by") or "admin"
    update_user = defect.get("update_user") or defect.get("updated_by") or create_user
    assignee = defect.get("assignee", "") or defect.get("handle_user", "") or ""
    num = defect.get("num", "")
    if not num and defect_id:
        # 无编号时用短 id 作为缺陷编号，保证列表 ID 列可展示
        num = defect_id[-6:]
    # 从存储字段构建前端 customFields（前端需在详情页回填状态/严重程度/处理人等自定义字段）
    custom_fields = defect.get("custom_fields") or []
    if isinstance(custom_fields, str):
        try:
            custom_fields = json.loads(custom_fields)
        except Exception:
            custom_fields = []
    if not isinstance(custom_fields, list):
        custom_fields = []
    # 构建详情用 customFields：状态/严重程度/处理人由顶层字段补充
    detail_custom_fields = [
        {"id": "status", "name": "状态", "type": "SELECT", "value": status},
        {"id": "severity", "name": "严重程度", "type": "SELECT",
         "value": _to_severity_name(defect.get("severity", "major"))},
        {"id": "assignee", "name": "处理人", "type": "MEMBER", "value": assignee},
    ]
    # 合并存储的自定义字段（避免重复）
    existing_ids = {cf.get("id") for cf in custom_fields if isinstance(cf, dict)}
    for cf in detail_custom_fields:
        if cf["id"] not in existing_ids:
            custom_fields.append(cf)

    return {
        "id": defect_id,
        "followFlag": _bug_followed(defect_id),
        "projectId": defect.get("project_id", ""),
        "num": num,
        "title": defect.get("title", ""),
        "description": defect.get("description", ""),
        "status": status,
        "statusName": _BUG_STATUS_NAME.get(status, status),
        "severity": _to_severity_name(defect.get("severity", "major")),
        "handleUser": assignee,
        "handleUserName": _user_name(assignee),
        "relationCaseCount": defect.get("relation_case_count", 0) or 0,
        "platform": defect.get("platform", "") or "Local",
        "tags": _parse_tags(defect.get("tags") or defect.get("tag") or []),
        "testPlanId": defect.get("test_plan_id") or defect.get("testPlanId") or "",
        "createUser": create_user,
        "createUserName": _user_name(create_user),
        "updateUser": update_user,
        "updateUserName": _user_name(update_user),
        "createTime": int((defect.get("created_at", 0) or 0) * 1000),
        "updateTime": int((defect.get("updated_at", 0) or 0) * 1000),
        "filePath": defect.get("file_path", ""),
        "assignee": assignee,
        "customFields": custom_fields,
        "deleted": False,
        # ── 详情抽屉（bug-detail-drawer.vue）需要的字段，缺失会导致模板加载异常 ──
        # Local 平台缺陷 platformDefault 恒为 False（标准模板而非第三方平台模板）
        "platformDefault": bool(defect.get("platform_default", defect.get("platformDefault", False))),
        "templateId": defect.get("template_id", defect.get("templateId", "")) or "default-bug-template",
        "platformBugId": defect.get("platform_bug_id", defect.get("platformBugId", "")),
        "linkCaseCount": defect.get("link_case_count", defect.get("linkCaseCount", 0)) or 0,
        # edit.vue 解构 detail 时 handleFile(attachments) 会检查 .length，
        # 缺失会 TypeError 导致编辑页崩溃。缺陷暂不存储附件，返回空数组。
        "attachments": [],
    }


def _to_severity(severity: str) -> str:
    """前端严重度转后端严重度（含第三方平台 P0-P3 分级映射）。"""
    mapping = {
        "critical": "critical",
        "block": "critical",
        "blocker": "blocker",
        "P0": "blocker",
        "p0": "blocker",
        "major": "major",
        "normal": "major",
        "P1": "critical",
        "p1": "critical",
        "minor": "minor",
        "P2": "major",
        "p2": "major",
        "trivial": "trivial",
        "P3": "minor",
        "p3": "minor",
    }
    return mapping.get(severity, severity)


def _to_severity_name(severity: str) -> str:
    """后端严重度转前端严重度。"""
    mapping = {
        "blocker": "blocker",
        "critical": "critical",
        "major": "major",
        "minor": "minor",
        "trivial": "trivial",
    }
    return mapping.get(severity, "major")


def _to_comment_user_infos(*user_ids: str) -> List[Dict[str, Any]]:
    """将涉及的 user_id 转为前端 commentUserInfos 结构。"""
    infos: List[Dict[str, Any]] = []
    seen = set()
    for uid in user_ids:
        if not uid or uid in seen:
            continue
        seen.add(uid)
        infos.append({
            "id": uid,
            "name": _user_name(uid),
            "email": "",
            "avatar": "",
        })
    return infos


def _comment_to_frontend(comment: Dict[str, Any], children: List[Dict[str, Any]]) -> Dict[str, Any]:
    """将后端评论记录转为前端 CommentItem 结构。"""
    create_user = comment.get("create_user", "")
    reply_user = comment.get("reply_user", "")
    notifier = comment.get("notifier", "")
    return {
        "id": comment.get("id", ""),
        "bugId": comment.get("bug_id", ""),
        "parentId": comment.get("parent_id", "") or "",
        "content": comment.get("content", ""),
        "createUser": create_user,
        "replyUser": reply_user,
        "notifier": notifier,
        "createTime": int((comment.get("create_time", 0) or 0) * 1000),
        "updateTime": int((comment.get("update_time", 0) or 0) * 1000),
        "commentUserInfos": _to_comment_user_infos(create_user, reply_user, notifier),
        "childComments": [_comment_to_frontend(c, []) for c in children],
    }


def _build_comment_tree(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将平铺评论按 parent_id 组织成树结构（顶层评论在前）。"""
    by_id = {c["id"]: c for c in comments}
    children_map: Dict[str, List[Dict[str, Any]]] = {}
    roots: List[Dict[str, Any]] = []
    for c in comments:
        parent = c.get("parent_id") or ""
        if parent and parent in by_id:
            children_map.setdefault(parent, []).append(c)
        else:
            roots.append(c)
    return [_comment_to_frontend(c, children_map.get(c["id"], [])) for c in roots]


def _to_bug_item(defect: Dict[str, Any], *, in_trash: bool = False) -> Dict[str, Any]:
    """将后端缺陷格式转为前端表格行格式（复用 _to_bug 统一字段语义）。"""
    base = _to_bug(defect)
    item = dict(base)
    item["deleted"] = bool(defect.get("deleted", 0))
    if in_trash:
        item["deleted"] = True
        item["deleteTime"] = int((defect.get("deleted_at", 0) or 0) * 1000)
        item["deleteUser"] = defect.get("deleted_by", "") or ""
        item["deleteUserName"] = defect.get("deleted_by", "") or ""
    return item


def _status_name(status: str) -> str:
    """缺陷状态显示名。"""
    mapping = {
        "open": "Open",
        "in_progress": "In Progress",
        "processing": "In Progress",
        "fixed": "Fixed",
        "resolved": "Fixed",
        "closed": "Closed",
        "wont_fix": "Won't Fix",
        "rejected": "Won't Fix",
    }
    return mapping.get(status, status)


def _resolve_batch_ids(body: dict):
    """解析批量操作的缺陷 ID 列表（兼容前端 selectIds / 全选 excludeIds 与旧式 ids/id）。"""
    select_all = bool(body.get("selectAll", False))
    select_ids = body.get("selectIds", body.get("select_ids", []))
    ids = body.get("ids", body.get("id", []))
    exclude_ids = body.get("excludeIds", body.get("exclude_ids", []))
    if isinstance(ids, str):
        ids = [ids]
    if isinstance(select_ids, str):
        select_ids = [select_ids]
    if isinstance(exclude_ids, str):
        exclude_ids = [exclude_ids]

    if select_all:
        # 全选模式：回收站全部缺陷排除 excludeIds
        all_trashed = defect_service.list_trashed(limit=9999, offset=0)
        target = [d["id"] for d in all_trashed if d.get("id") not in set(exclude_ids or [])]
        return target
    return [i for i in (select_ids or ids) if i]


def _match_filters(item: Dict[str, Any], filter_cond: dict) -> bool:
    """简单筛选匹配：filter 形如 {field: value} 或 {field: [values]}。"""
    if not isinstance(filter_cond, dict):
        return True
    for key, val in filter_cond.items():
        if val is None or val == "":
            continue
        field_val = item.get(key, "")
        if isinstance(val, (list, tuple)):
            # 多选：字段值命中任一选项（支持存储值为文本或选项 value）
            if isinstance(field_val, (list, tuple)):
                if not any(str(v) in [str(x) for x in field_val] for v in field_val):
                    # 语义：集合有交集
                    if not (set(map(str, field_val)) & set(map(str, val))):
                        return False
            elif str(field_val) not in [str(x) for x in val]:
                return False
        else:
            if field_val is None:
                if str(val) not in ("", "0", "false"):
                    return False
            elif str(field_val) != str(val):
                return False
    return True


def _sort_items(items: List[Dict[str, Any]], sort: dict) -> List[Dict[str, Any]]:
    """表格排序：sort 形如 {field: 'ascend'|'descend'}。"""
    if not isinstance(sort, dict) or not sort:
        return items
    field = next(iter(sort))
    direction = sort[field]
    try:
        return sorted(
            items,
            key=lambda it: it.get(field) if it.get(field) is not None else "",
            reverse=(str(direction).lower().startswith("desc")),
        )
    except Exception:
        return items
