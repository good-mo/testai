# app/test_plan/router_dashboard_layout.py
"""工作台 Dashboard 布局 API（自 router_dashboard.py 拆分）。

包含用户工作台布局的获取/保存（真实落库）及其辅助函数。
"""

from fastapi import APIRouter, Request

from app.core.response import ok, read_body
from app.services.test_plan_service import test_plan_service

router = APIRouter(tags=["dashboard"])

# ── 工作台布局 ───────────────────────────────────────────

def _get_layout_user_id(request: Request) -> str:
    """从请求上下文解析当前用户 ID。"""
    try:
        user = getattr(request.state, "user", None)
        if user and user.get("id"):
            return str(user["id"])
    except Exception:
        pass
    # 兜底：从请求头解析会话
    try:
        from app.services.auth_service import auth_service
        session_id = request.headers.get("X-AUTH-TOKEN", "") or request.cookies.get("sessionId", "")
        if session_id:
            user = auth_service.get_session_user(session_id)
            if user and user.get("id"):
                return str(user["id"])
    except Exception:
        pass
    return "anonymous"

def _default_dashboard_cards(default_project_id: str = "") -> list:
    """构建默认工作台卡片（保证前端 defaultWorkList 正常渲染）。"""
    def _card(label, cid, key, pos, project_ids=None):
        return {
            "label": label,
            "id": cid,
            "key": key,
            "fullScreen": False,
            "isDisabledHalfScreen": False,
            "projectIds": [default_project_id] if project_ids is None else project_ids,
            "handleUsers": [],
            "selectAll": True,
            "planId": "",
            "groupId": "",
            "pos": pos,
        }
    return [
        _card("项目概览", "project-overview", "PROJECT_VIEW", 0),
        _card("用例数", "case-count", "CASE_COUNT", 1),
        _card("缺陷数", "bug-count", "BUG_COUNT", 2),
        _card("接口数", "api-count", "API_COUNT", 3),
    ]

@router.get("/dashboard/layout/get/{org_id}")
def dashboard_layout_get(org_id: str, request: Request):
    """获取用户 Dashboard 布局配置（有自定义布局则返回，否则返回默认卡片）。

    - 默认项目取「当前组织」的首个项目（避免指向组织外残留项目导致下拉"选项不存在"）
    - 用户已保存过布局时返回保存的卡片
    """
    from app.services.organization_service import organization_service
    from app.services.project_service import project_service

    # 默认项目：优先取当前组织下的首个项目
    default_project_id = ""
    try:
        org_projects = organization_service.list_projects(org_id or "default-org")
        if org_projects:
            default_project_id = org_projects[0]["id"]
    except Exception:
        pass
    if not default_project_id:
        try:
            projects = project_service.list(limit=1)
            if projects:
                default_project_id = projects[0]["id"]
        except Exception:
            default_project_id = ""

    # 用户自定义布局优先
    user_id = _get_layout_user_id(request)
    saved = test_plan_service.load_dashboard_layout(org_id, user_id)
    if saved is not None:
        # 若保存的卡片缺少默认项目 id（如空数组），补充默认项目供渲染
        cards = []
        for c in saved:
            item = dict(c)
            if not item.get("projectIds") and default_project_id:
                item["projectIds"] = [default_project_id]
            cards.append(item)
        return ok(cards)

    return ok(_default_dashboard_cards(default_project_id))

@router.post("/dashboard/layout/edit/{org_id}")
async def dashboard_layout_edit(org_id: str, request: Request):
    """更新用户 Dashboard 布局配置（真实落库）。

    前端 editDashboardLayout 直接把完整卡片数组作为请求体发送。
    """
    body = await read_body(request)
    # read_body 会把「裸数组请求体」归一化为 {"ids": [...]}，此处需还原
    if (isinstance(body, dict) and isinstance(body.get("ids"), list) and body.get("ids")
            and isinstance(body["ids"][0], dict) and "key" in body["ids"][0]):
        layout = body["ids"]
    else:
        layout = body if isinstance(body, list) else body.get("layout", body.get("cards", []))
    if not isinstance(layout, list):
        layout = []
    user_id = _get_layout_user_id(request)
    test_plan_service.save_dashboard_layout(org_id, user_id, layout)
    return ok(layout)
