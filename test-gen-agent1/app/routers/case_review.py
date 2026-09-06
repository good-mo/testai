# app/routers/case_review.py
"""用例评审管理路由（自 cases.py 拆分，控制文件行数 <800）。"""
import json
import time

from fastapi import APIRouter, Depends, Request

from app.core.response import fail, ok, read_body
from app.core.helpers import as_model
from app.models.case_review import (
    ReviewAssociateBody,
    ReviewBatchMoveBody,
    ReviewCaseStatusBody,
    ReviewCopyBody,
    ReviewCreateBody,
    ReviewDetailBatchReviewBody,
    ReviewDetailBatchReviewersBody,
    ReviewDetailPageQuery,
    ReviewDetailTreeBody,
    ReviewEditBody,
    ReviewFollowerBody,
    ReviewIdBody,
    ReviewModuleAddBody,
    ReviewModuleCountBody,
    ReviewModuleDeleteBody,
    ReviewModuleMoveBody,
    ReviewModuleUpdateBody,
    ReviewMovePosBody,
    ReviewPageQuery,
    ReviewUserOptionQuery,
)
from app.services.apitest_service import apitest_service
from app.services.case_review_service import case_review_service as cvs
from app.services.case_service import case_service

router = APIRouter(tags=["case_review"])


# ════════════════════════════════════════════════════════════
# 用例评审管理（TestPilot 前端契约 · 收敛迁移样板）
# ------------------------------------------------------------
# 由 app/adapters/domains/case_reviews.py 收敛迁移而来。
# 数据持久化在 app/cases/review_store.py（评审头 + 评审-用例关联），
# 不再拿 test_cases 表行伪装评审。
# ════════════════════════════════════════════════════════════

_REVIEW_STATUS = ("review", "pending", "in_review", "under_review")


def _reviewers_of(header: dict) -> list:
    """从评审头提取前端 reviewers 数组。"""
    raw = header.get("reviewers_json") or []
    result = []
    for r in raw:
        if isinstance(r, dict):
            uid = r.get("userId", "")
            uname = r.get("userName", "") or uid
            result.append({"userId": uid, "userName": uname})
        else:
            result.append({"userId": str(r), "userName": str(r)})
    if not result:
        result = [{"userId": "admin", "userName": "admin"}]
    return result


def _review_view_item(h: dict) -> dict:
    """评审头 -> 前端 ReviewItem 列表项。"""
    status = h.get("status", "UNDERWAY")
    counts = cvs.get_review_case_status(h.get("id", ""))
    case_count = len(cvs.list_links(h.get("id", "")))
    create_time = int((h.get("create_time") or time.time()) * 1000)
    update_time = int((h.get("update_time") or time.time()) * 1000)
    return {
        "id": h.get("id", ""),
        "name": h.get("name", ""),
        "num": h.get("num", 1),
        "moduleId": h.get("module_id", "root"),
        "projectId": h.get("project_id", ""),
        "status": status,
        "reviewPassRule": h.get("review_pass_rule", "SINGLE"),
        "pos": h.get("pos", 0),
        "startTime": int((h.get("start_time") or 0) * 1000),
        "endTime": int((h.get("end_time") or 0) * 1000) if h.get("end_time") else None,
        "createUser": h.get("create_user", "admin"),
        "createUserName": h.get("create_user", "admin"),
        "createTime": create_time,
        "updateTime": update_time,
        "updateUser": h.get("update_user", "admin"),
        "description": h.get("description", ""),
        "tags": h.get("tags", []),
        "caseCount": case_count,
        "passRate": round(counts["passCount"] / case_count * 100, 1) if case_count else 0,
        "reviewers": _reviewers_of(h),
        "passCount": counts["passCount"],
        "unPassCount": counts["unPassCount"],
        "reReviewedCount": counts["reReviewedCount"],
        "underReviewedCount": counts["underReviewedCount"],
        "unReviewCount": counts["unReviewCount"],
        "reviewedCount": counts["reviewedCount"],
        "followFlag": False,
    }


def _review_detail(h: dict) -> dict:
    """评审头 -> 前端 ReviewItem 完整详情。"""
    item = _review_view_item(h)
    return item


def _get_current_user_id(request: Request) -> str:
    """从请求上下文获取当前用户 ID。"""
    try:
        user = getattr(request.state, "user", None)
        if user and user.get("id"):
            return str(user["id"])
    except Exception:
        pass
    try:
        from app.services.auth_service import auth_service
        session_id = request.headers.get("X-AUTH-TOKEN", "") or request.cookies.get("sessionId", "")
        if session_id:
            user = auth_service.get_session_user(session_id)
            if user and user.get("id"):
                return str(user["id"])
    except Exception:
        pass
    return "admin"


def _case_module_id(c: dict) -> str:
    """从用例记录中提取 module_id。"""
    meta = c.get("metadata", {}) or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except (json.JSONDecodeError, TypeError):
            meta = {}
    return meta.get("module_id", "") or c.get("module_id", "") or "root"


def _module_name_of(module_id: str) -> str:
    """根据模块 ID 查找模块名称。"""
    if not module_id or module_id == "root":
        return ""
    try:
        m = apitest_service.get_module(module_id)
        if m:
            return m.get("name", "")
    except Exception:
        pass
    return ""


def _case_review_item(link: dict, review_id: str, current_user_id: str = "") -> dict:
    """将评审-用例关联记录转为前端 ReviewCaseItem（含功能用例格式化字段）。

    前端 ReviewCaseItem 需要：
      id / name / num / caseId / reviewId / status / myStatus
      reviewers: string[] / reviewNames: string[]
      caseLevel: string（P0-P3）/ customFields（供 getCaseLevels 提取）
      moduleId / moduleName / versionId / versionName
    """
    c = case_service.get(link.get("case_id", "")) or {}
    if not c:
        # 用例已被彻底删除，仅返回基础信息
        return {
            "id": link.get("case_id", ""),
            "caseId": link.get("case_id", ""),
            "reviewId": review_id,
            "name": "",
            "num": "",
            "versionId": "",
            "versionName": "",
            "reviewers": [],
            "reviewNames": [],
            "status": link.get("status", "UN_REVIEWED"),
            "myStatus": link.get("status", "UN_REVIEWED"),
            "moduleId": "root",
            "moduleName": "",
            "customFields": [],
            "caseLevel": "P2",
            "createUser": "admin",
            "createUserName": "admin",
            "createTime": int((link.get("create_time") or 0) * 1000),
            "deleted": True,
            "caseEditType": "",
            "steps": "",
            "priority": "P2",
        }
    # 先复用 case_service.to_functional_case 获取完整功能用例字段
    fc = case_service.to_functional_case(c)
    reviewer = link.get("reviewer", "") or ""
    reviewers_list = [reviewer] if reviewer else []
    review_names = reviewers_list
    if reviewer:
        # 尝试将 userId 解析为用户名
        try:
            users = cvs.list_review_users()
            for u in users:
                if str(u.get("id", "")) == reviewer:
                    review_names = [u.get("name", reviewer)]
                    break
        except Exception:
            pass
    mod_id = _case_module_id(c)
    mod_name = _module_name_of(mod_id)
    return {
        **fc,
        "id": link.get("case_id", ""),
        "caseId": link.get("case_id", ""),
        "reviewId": review_id,
        "versionId": fc.get("versionId", "") or "",
        "versionName": fc.get("versionName", "") or "",
        "reviewers": reviewers_list,
        "reviewNames": review_names,
        "status": link.get("status", "UN_REVIEWED"),
        "myStatus": link.get("status", "UN_REVIEWED") if not current_user_id or reviewer == current_user_id else "UN_REVIEWED",
        "moduleId": mod_id,
        "moduleName": mod_name or "全部用例",
        "caseLevel": fc.get("priority", "P2"),
        "priority": fc.get("priority", "P2"),
    }


def _build_review_detail_module_tree(review_id: str) -> list:
    """构建评审详情已关联用例的模块树（root 全部用例 + 关联模块节点）。

    每个模块节点 count = 该模块下（含子模块）已关联评审的用例数。
    """
    if not review_id:
        return []
    links = cvs.list_links(review_id)
    # 按用例 module_id 分组计数
    case_mods: dict = {}  # case_id -> module_id
    module_counts: dict = {"root": 0}
    for link in links:
        c = case_service.get(link.get("case_id", "")) or {}
        if not c:
            continue
        mod_id = _case_module_id(c)
        case_mods[link.get("case_id", "")] = mod_id
        module_counts[mod_id] = module_counts.get(mod_id, 0) + 1

    # 加载 functional scope 模块结构
    try:
        modules = apitest_service.list_modules("functional", "")
    except Exception:
        modules = []

    module_map: dict = {}
    for m in modules:
        mid = m["id"]
        module_map[mid] = {
            "id": mid,
            "name": m.get("name", ""),
            "type": "MODULE",
            "parentId": m.get("parent_id", "root"),
            "children": [],
            "count": module_counts.get(mid, 0),
            "pos": m.get("pos", 0),
        }

    # 组装层级
    children_map: dict = {}
    for _mid, node in module_map.items():
        parent = node["parentId"]
        if parent in module_map:
            children_map.setdefault(parent, []).append(node)
        elif parent == "root":
            children_map.setdefault("root", []).append(node)

    # 递归累计子模块用例数到父模块
    def _accumulate(node: dict) -> int:
        total = node.get("count", 0)
        for child in children_map.get(node["id"], []):
            total += _accumulate(child)
        node["count"] = total
        return total

    # 只有 count > 0 的模块才显示在评审详情树中。
    # _accumulate 已递归累计所有子孙模块，node_count==0 即该模块及其子孙
    # 均无用例，无需再对子节点重复累计判断，移除冗余/死代码。
    top_children = []
    for node in children_map.get("root", []):
        if _accumulate(node) > 0:
            top_children.append(node)

    root = {
        "id": "root",
        "name": "全部用例",
        "type": "MODULE",
        "parentId": "",
        "children": top_children,
        "count": len(links),
        "pos": 0,
    }
    return [root]


@router.post("/case/review/page")
async def case_review_page(request: Request):
    """获取评审列表（真实评审头表）。"""
    body = await read_body(request)
    q = as_model(body, ReviewPageQuery)
    keyword = q.keyword
    page_size = int(q.pageSize or 10)
    current = int(q.current or 1)
    project_id = q.projectId or ""
    # Service 层 list_reviews 签名: (keyword, project_id, page_size, current),
    # 内部已按 DB 侧真实总数分页并格式化, 返回 {list,total,pageSize,current}。
    data = cvs.list_reviews(
        keyword=keyword, project_id=project_id,
        page_size=page_size, current=current,
    )
    return ok(data)


@router.post("/case/review/add")
async def case_review_add(
    request: Request,
    current_user_id: str = Depends(_get_current_user_id),
):
    """新增评审（真实落库评审头，含评审人与初始关联用例）。"""
    body = await read_body(request)
    b = as_model(body, ReviewCreateBody)
    name = b.name
    reviewers = b.reviewers or []
    if isinstance(reviewers, str):
        reviewers = [reviewers]
    # 新建时如带关联用例请求，创建后直接关联
    base_associate = b.baseAssociateCaseRequest
    assoc = base_associate.model_dump() if isinstance(base_associate, ReviewAssociateBody) else (base_associate or {})
    select_ids = assoc.get("selectIds", []) or []
    if isinstance(select_ids, str):
        select_ids = [select_ids]
    # 全选场景：selectIds 为空但 selectAll 为 true
    if not select_ids and assoc.get("selectAll"):
        all_cases = case_service.list_cases(limit=999)
        select_ids = [c["id"] for c in all_cases]
    header = cvs.create_review(
        name=name,
        description=b.description,
        project_id=b.projectId or "",
        module_id=b.moduleId or "root",
        review_pass_rule=b.reviewPassRule or "SINGLE",
        reviewers=reviewers,
        create_user=current_user_id,
        tags=b.tags,
        start_time=b.startTime or 0,
        end_time=b.endTime or 0,
    )
    if select_ids:
        cvs.link_cases(header.get("id", ""), select_ids)
    return ok({
        "id": header.get("id", ""),
        "name": name,
        "status": header.get("status", "UNDERWAY"),
        "caseCount": len(select_ids),
    })


@router.post("/case/review/edit")
async def case_review_edit(request: Request):
    """编辑评审。"""
    body = await read_body(request)
    b = as_model(body, ReviewEditBody)
    review_id = b.review_id
    if not review_id:
        return fail("评审不存在", 404)
    fields = {
        "name": b.name,
        "description": b.description,
        "module_id": b.moduleId,
        "project_id": b.projectId,
        "status": b.status,
        "review_pass_rule": b.reviewPassRule,
    }
    if b.reviewers is not None:
        fields["reviewers"] = b.reviewers or []
    header = cvs.update_review(review_id, {k: v for k, v in fields.items() if v is not None})
    if not header:
        return fail("评审不存在", 404)
    return ok(_review_detail(header))


@router.post("/case/review/delete")
async def case_review_delete(request: Request):
    """删除用例评审（软删除评审头）。"""
    body = await read_body(request)
    review_id = as_model(body, ReviewIdBody).review_id
    if not review_id:
        return fail("评审不存在", 404)
    cvs.delete_review(review_id)
    return ok()


@router.post("/case/review/copy")
async def case_review_copy(request: Request):
    """复制评审（含已关联用例与评审人）。"""
    body = await read_body(request)
    b = as_model(body, ReviewCopyBody)
    copy_id = b.source_id
    new_name = b.name
    header = cvs.copy_review(copy_id, new_name=new_name)
    if not header:
        return fail("评审不存在", 404)
    return ok({
        "id": header.get("id", ""),
        "name": header.get("name", ""),
        "caseCount": len(cvs.list_links(header.get("id", ""))),
        "createTime": int((header.get("create_time") or time.time()) * 1000),
        "createUser": header.get("create_user", "admin"),
        "status": header.get("status", "UNDERWAY"),
        "moduleId": header.get("module_id", "root"),
        "projectId": header.get("project_id", ""),
        "reviewPassRule": header.get("review_pass_rule", "SINGLE"),
        "passRate": 0,
        "pos": header.get("pos", 0),
    })


@router.post("/case/review/batch/move")
async def case_review_batch_move(request: Request):
    """移动评审（更新 module_id）。"""
    body = await read_body(request)
    b = as_model(body, ReviewBatchMoveBody)
    ids = b.ids or []
    if isinstance(ids, str):
        ids = [ids]
    move_module_id = b.target_module_id
    for rid in ids:
        if rid:
            cvs.update_review(rid, {"module_id": move_module_id or "root"})
    return ok()


@router.post("/case/review/edit/pos")
async def case_review_edit_pos(request: Request):
    """评审拖拽排序（更新 pos）。"""
    body = await read_body(request)
    b = as_model(body, ReviewMovePosBody)
    move_id = b.moveId
    pos = b.pos or (1 if b.targetId else 0)
    if move_id:
        cvs.update_review(move_id, {"pos": pos})
    return ok()


@router.post("/case/review/edit/follower")
async def case_review_edit_follower(request: Request):
    """关注/取消关注评审。"""
    body = await read_body(request)
    b = as_model(body, ReviewFollowerBody)
    review_id = b.review_id
    user_id = b.userId or _get_current_user_id(request)
    following = False
    if review_id:
        following = cvs.toggle_follow(review_id, user_id)
    return ok({"followFlag": following})


@router.post("/case/review/associate")
async def case_review_associate(request: Request):
    """关联用例到评审（真实落库评审-用例关联）。"""
    body = await read_body(request)
    b = as_model(body, ReviewAssociateBody)
    review_id = b.reviewId or ""
    if not review_id or not cvs.get_review(review_id):
        return fail("评审不存在", 404)
    req = getattr(b, "baseAssociateCaseRequest", None) or {}
    case_ids = req.get("selectIds", []) or []
    if isinstance(case_ids, str):
        case_ids = [case_ids]
    if not case_ids and req.get("selectAll"):
        all_cases = case_service.list_cases(limit=999)
        case_ids = [c["id"] for c in all_cases]
    cvs.link_cases(review_id, case_ids)
    return ok({"reviewId": review_id, "caseCount": len(cvs.list_links(review_id))})


@router.post("/case/review/disassociate")
async def case_review_disassociate(request: Request):
    """取消关联用例（真实落库）。"""
    body = await read_body(request)
    b = as_model(body, ReviewAssociateBody)
    review_id = b.reviewId or ""
    if not review_id:
        return fail("评审不存在", 404)
    req = getattr(b, "baseAssociateCaseRequest", None) or {}
    case_ids = req.get("selectIds", []) or []
    if not case_ids and b.caseId:
        case_ids = [b.caseId]
    if not case_ids and b.ids:
        case_ids = b.ids
    cvs.unlink_cases(review_id, case_ids)
    return ok({"reviewId": review_id, "caseCount": len(cvs.list_links(review_id))})


@router.post("/case/review/detail")
async def case_review_detail(request: Request):
    """获取评审详情（真实评审头）。"""
    body = await read_body(request)
    review_id = as_model(body, ReviewIdBody).review_id
    header = cvs.get_review(review_id) if review_id else None
    if not header:
        return fail("评审不存在", 404)
    return ok(_review_detail(header))


@router.get("/case/review/detail")
def case_review_detail_get(request: Request):
    """获取评审详情（GET 方式，兼容查询参数）。"""
    review_id = request.query_params.get("id", request.query_params.get("reviewId", ""))
    header = cvs.get_review(review_id) if review_id else None
    if not header:
        return fail("评审不存在", 404)
    return ok(_review_detail(header))


@router.get("/case/review/detail/{id}")
def case_review_detail_get_path(id: str):
    """获取评审详情（带路径参数，兼容前端 RESTful 调用）。"""
    header = cvs.get_review(id) if id else None
    if not header:
        return fail("评审不存在", 404)
    return ok(_review_detail(header))


@router.post("/case/review/detail/page")
async def case_review_detail_page(
    request: Request,
    current_user_id: str = Depends(_get_current_user_id),
):
    """评审详情-获取已关联用例列表。"""
    body = await read_body(request)
    q = as_model(body, ReviewDetailPageQuery)
    review_id = q.reviewId
    page_size = int(q.pageSize or 10)
    current = int(q.current or 1)
    keyword = q.keyword or ""
    module_ids = q.moduleIds or []
    if isinstance(module_ids, str):
        module_ids = [module_ids]
    view_status_flag = q.viewStatusFlag
    links = cvs.list_links(review_id) if review_id else []
    # 关键词与模块过滤
    if keyword or module_ids:
        filtered = []
        for link in links:
            c = case_service.get(link.get("case_id", "")) or {}
            if not c:
                continue
            if keyword:
                kw = keyword.lower()
                title = (c.get("title", "") or "").lower()
                if kw not in title and kw not in (c.get("id", "") or "").lower():
                    continue
            if module_ids and "root" not in module_ids:
                mod_id = _case_module_id(c)
                if mod_id not in module_ids:
                    continue
            filtered.append(link)
        links = filtered
    total = len(links)
    start = (current - 1) * page_size
    paged_links = links[start:start + page_size]
    items = []
    for link in paged_links:
        item = _case_review_item(link, review_id, current_user_id)
        if view_status_flag:
            # 只显示当前用户的评审状态
            item["myStatus"] = item["status"] if current_user_id and (link.get("reviewer", "") or "") == current_user_id else "UN_REVIEWED"
        items.append(item)
    return ok({
        "list": items,
        "total": total,
        "pageSize": page_size,
        "current": current,
    })


@router.post("/case/review/user-option")
async def case_review_user_option(request: Request):
    """获取评审人员列表（真实成员）。"""
    body = await read_body(request)
    q = as_model(body, ReviewUserOptionQuery)
    return ok(cvs.list_review_users(q.projectId or "", q.keyword or ""))


@router.get("/case/review/user-option")
def case_review_user_option_get():
    """获取评审人员列表（GET 方式）。"""
    return ok(cvs.list_review_users())


# ── 评审模块管理 ─────────────────────────────────────────


@router.get("/case/review/module/tree")
def case_review_module_tree():
    """获取评审模块树。"""
    return ok(cvs.build_review_module_tree())


@router.get("/case/review/module/tree/{project_id}")
def case_review_module_tree_path(project_id: str):
    """获取评审模块树（带项目ID路径参数）。"""
    return ok(cvs.build_review_module_tree(project_id))


@router.post("/case/review/module/add")
async def case_review_module_add(request: Request):
    """新增评审模块（真实落库）。"""
    body = await read_body(request)
    b = as_model(body, ReviewModuleAddBody)
    node = cvs.add_review_module(
        name=b.name,
        project_id=b.projectId or "",
        parent_id=b.parentId or "root",
    )
    return ok(node)


@router.post("/case/review/module/update")
async def case_review_module_update(request: Request):
    """更新评审模块。"""
    body = await read_body(request)
    b = as_model(body, ReviewModuleUpdateBody)
    module_id = b.id
    name = b.name
    if not module_id:
        return fail("模块不存在", 404)
    cvs.update_review_module(module_id, name)
    return ok()


@router.post("/case/review/module/delete")
async def case_review_module_delete(request: Request):
    """删除评审模块。"""
    body = await read_body(request)
    module_id = as_model(body, ReviewModuleDeleteBody).id
    if module_id:
        cvs.delete_review_module(module_id)
    return ok()


@router.post("/case/review/module/move")
async def case_review_module_move(request: Request):
    """移动评审模块。"""
    body = await read_body(request)
    b = as_model(body, ReviewModuleMoveBody)
    drag_id = b.dragNodeId
    drop_id = b.dropNodeId
    pos = b.dropPosition
    if drag_id:
        cvs.move_review_module(drag_id, drop_id or "root", pos)
    return ok()


@router.post("/case/review/module/count")
async def case_review_module_count(request: Request):
    """模块下评审数量统计（返回 {all: n, <moduleId>: n, root: n}）。"""
    body = await read_body(request)
    project_id = as_model(body, ReviewModuleCountBody).projectId or ""
    return ok(cvs.review_count_by_module(project_id))


@router.get("/case/review/module/delete")
def case_review_module_delete_get(id: str = ""):
    """删除评审模块（GET 方式）。"""
    if id:
        cvs.delete_review_module(id)
    return ok({"id": id, "deleted": True})


# ── 评审详情操作 ─────────────────────────────────────────


@router.post("/case/review/detail/edit/pos")
async def case_review_detail_edit_pos(request: Request):
    """评审详情-已关联用例拖拽排序。"""
    await read_body(request)
    return ok()


@router.post("/case/review/detail/batch/review")
async def case_review_detail_batch_review(request: Request):
    """评审详情-批量评审（真实落库用例评审结果）。

    归属校验 + 事务：评审必须真实存在；批量提交结果前先过滤出真正关联
    到该评审的用例（归属该校验），更新整体置于事务内由 update_link_status
    保证原子性，只返回实际生效的用例数。
    """
    body = await read_body(request)
    b = as_model(body, ReviewDetailBatchReviewBody)
    review_id = b.reviewId
    if not review_id or not cvs.get_review(review_id):
        return fail("评审不存在", 404)
    # 前端批量操作发送 selectIds / selectedIds，兼容 ids / id
    ids = b.effective_ids()
    if isinstance(ids, str):
        ids = [ids]
    ids = [str(cid) for cid in (ids or []) if cid]
    if not ids and b.selectAll:
        ids = [link["case_id"] for link in cvs.list_links(review_id)]
    if not ids:
        return ok({"updated": 0})
    status_map = {
        "PASS": cvs.RESULT_PASS,
        "UN_PASS": cvs.RESULT_UN_PASS,
        "UNDER_REVIEWED": cvs.RESULT_UNDER_REVIEWED,
        "RE_REVIEWED": cvs.RESULT_RE_REVIEWED,
    }
    status = status_map.get(b.status, cvs.RESULT_UNDER_REVIEWED)
    reviewer = b.effective_reviewer or _get_current_user_id(request)
    comment = b.effective_comment
    # 归属校验：仅保留确实关联到该评审的用例，防止越权批量改写非本评审用例
    owned = cvs.list_link_case_ids(review_id)
    valid_ids = [cid for cid in ids if cid in owned]
    updated = cvs.update_link_status(review_id, valid_ids, status,
                                    reviewer=reviewer, comment=comment)
    return ok({"updated": updated, "requested": len(ids)})


@router.post("/case/review/detail/batch/disassociate")
async def case_review_detail_batch_disassociate(request: Request):
    """评审详情-批量取消关联用例。"""
    body = await read_body(request)
    b = as_model(body, ReviewDetailBatchReviewBody)
    review_id = b.reviewId
    # 前端批量操作发送 selectIds / selectedIds，兼容 ids / id
    ids = b.selectIds or b.ids or b.selectedIds or []
    if isinstance(ids, str):
        ids = [ids]
    if review_id:
        cvs.unlink_cases(review_id, ids)
    return ok({"removed": len(ids)})


@router.post("/case/review/detail/batch/edit/reviewers")
async def case_review_detail_batch_edit_reviewers(request: Request):
    """评审详情-批量修改评审人。"""
    body = await read_body(request)
    b = as_model(body, ReviewDetailBatchReviewersBody)
    review_id = b.reviewId
    reviewer_ids = b.reviewer_ids
    if isinstance(reviewer_ids, str):
        reviewer_ids = [reviewer_ids]
    if review_id:
        cvs._save_reviewers(review_id, reviewer_ids)
    return ok()


@router.post("/case/review/detail/get-ids")
async def case_review_detail_get_ids(request: Request):
    """获取已关联用例id集合。"""
    body = await read_body(request)
    review_id = as_model(body, ReviewIdBody).review_id
    links = cvs.list_links(review_id) if review_id else []
    return ok([link["case_id"] for link in links])


@router.post("/case/review/detail/module/count")
async def case_review_detail_module_count(request: Request):
    """评审详情-模块下用例数量统计。

    返回 {all: 已关联用例总数, root: 根模块数, <moduleId>: 对应模块用例数}。
    """
    body = await read_body(request)
    review_id = as_model(body, ReviewIdBody).review_id
    if not review_id:
        return ok({"all": 0, "root": 0})
    links = cvs.list_links(review_id)
    counts: dict = {"all": len(links), "root": 0}
    for link in links:
        c = case_service.get(link.get("case_id", "")) or {}
        mod_id = _case_module_id(c) if c else "root"
        counts[mod_id] = counts.get(mod_id, 0) + 1
    return ok(counts)


@router.post("/case/review/detail/tree")
async def case_review_detail_tree(request: Request):
    """评审详情-已关联用例模块树。"""
    body = await read_body(request)
    review_id = as_model(body, ReviewDetailTreeBody).review_id
    return ok(_build_review_detail_module_tree(review_id))


@router.get("/case/review/detail/reviewer/list")
def case_review_detail_reviewer_list():
    """评审详情-获取用例的评审人。"""
    return ok([])


@router.post("/case/review/detail/reviewer/status/total")
async def case_review_detail_reviewer_status_total(request: Request):
    """脑图-获取用例评审最终结果。"""
    await read_body(request)
    return ok([])


@router.post("/case/review/detail/mind/multiple/review")
async def case_review_detail_mind_multiple_review(request: Request):
    """评审详情-脑图评审用例。"""
    body = await read_body(request)
    b = as_model(body, ReviewCaseStatusBody)
    review_id = getattr(b, "reviewId", "") or ""
    case_id = getattr(b, "caseId", "") or ""
    status_map = {
        "PASS": cvs.RESULT_PASS,
        "UN_PASS": cvs.RESULT_UN_PASS,
        "UNDER_REVIEWED": cvs.RESULT_UNDER_REVIEWED,
    }
    status = status_map.get(b.status, cvs.RESULT_UNDER_REVIEWED)
    if review_id and case_id:
        cvs.update_link_status(review_id, [case_id], status,
                              reviewer=b.effective_reviewer or "admin",
                              comment=b.effective_comment)
    return ok()


@router.get("/case/review/user-option/{project_id}")
def case_review_user_option_get_route(project_id: str, keyword: str = ""):
    """获取评审人员列表（GET）。"""
    return ok(cvs.list_review_users(project_id, keyword))


@router.get("/case/review/disassociate/{review_id}/{case_id}")
def case_review_disassociate_get_route(review_id: str, case_id: str):
    """取消关联用例（GET）。"""
    if review_id and case_id:
        cvs.unlink_cases(review_id, [case_id])
    return ok()


@router.get("/case/review/delete/{project_id}/{review_id}")
def case_review_delete_get_route(project_id: str, review_id: str):
    """删除评审（GET）。"""
    if review_id:
        cvs.delete_review(review_id)
    return ok()


@router.get("/case/review/detail/get-ids/{review_id}")
def case_review_detail_get_ids_get_route(review_id: str):
    """获取已关联用例id集合（GET）。"""
    links = cvs.list_links(review_id) if review_id else []
    return ok([link["case_id"] for link in links])


@router.get("/case/review/detail/tree/{review_id}")
def case_review_detail_tree_get_route(review_id: str):
    """评审详情-模块树（GET）。"""
    return ok(_build_review_detail_module_tree(review_id))


@router.get("/case/review/detail/reviewer/list/{review_id}/{case_id}")
def case_review_detail_reviewer_list_get_route(review_id: str, case_id: str):
    """评审详情-获取用例的评审人（GET）。"""
    header = cvs.get_review(review_id) if review_id else None
    if not header:
        return ok([])
    # 返回评审头中配置的评审人列表（仅 userId / reviewId / caseId 字段）
    result = []
    reviewers_json = header.get("reviewers_json", []) or []
    for r in reviewers_json:
        if isinstance(r, dict):
            result.append({
                "caseId": case_id,
                "reviewId": review_id,
                "userId": r.get("userId", ""),
            })
        else:
            result.append({
                "caseId": case_id,
                "reviewId": review_id,
                "userId": str(r),
            })
    return ok(result)


@router.get("/case/review/detail/reviewer/status/total/{review_id}/{case_id}")
def case_review_detail_reviewer_status_total_get_route(review_id: str, case_id: str):
    """脑图-获取用例评审结果（GET）。"""
    # 获取评审通过规则和最终状态
    header = cvs.get_review(review_id) if review_id else None
    if not header:
        return ok({"status": "UN_REVIEWED", "caseId": case_id, "reviewerStatus": []})
    # 查找该用例的评审结果
    links = cvs.list_links(review_id) if review_id else []
    status = "UN_REVIEWED"
    for link in links:
        if link.get("case_id", "") == case_id:
            status = link.get("status", "UN_REVIEWED")
            break
    reviewers_list = []
    header_reviewers = header.get("reviewers_json", []) or []
    for r in header_reviewers:
        if isinstance(r, dict):
            reviewers_list.append({
                "userId": r.get("userId", ""),
                "userName": r.get("userName", "") or r.get("userId", ""),
                "status": status,
            })
    return ok({
        "status": status,
        "caseId": case_id,
        "reviewerStatus": reviewers_list,
    })


@router.get("/case/review/module/delete/{id}")
@router.post("/case/review/module/delete/{id}")
def case_review_module_delete_path(id: str):
    """/case/review/module/delete 带路径参数（前端 RESTful 调用兼容）。"""
    if id:
        cvs.delete_review_module(id)
    return ok({"id": id, "deleted": True})
