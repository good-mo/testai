# app/auth/router.py
"""认证 API 路由：登录、登出、会话、用户、个人信息、用户管理。"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.response import fail, ok, read_body
from app.models.auth import (
    ApiKeyAddBody,
    ApiKeyIdBody,
    ImportUserItem,
    LocalConfigAddBody,
    LocalConfigUpdateBody,
    LocaleUpdateBody,
    LoginRequest,
    PasswordUpdateBody,
    PersonalUpdateBody,
    SystemUserPageBody,
    UserAddBody,
    UserIdBody,
    UserImportBody,
    UserUpdateBody,
)
from app.services.auth_service import auth_service
from app.services.project_service import project_service

# 兼容旧 auth_store 引用：auth_store 是 AuthStore 实例的别名
auth_store = auth_service.store


# ── 依赖：从请求头获取会话用户 ─────────────────────────────
def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """从请求中获取当前用户。

    优先从全局认证中间件注入的 request.state.user 获取；
    若中间件未注入（如公开路由），则手动从令牌中解析。
    """
    # 中间件已将用户注入 request.state
    user = getattr(request.state, "user", None)
    if user:
        return user
    # 兜底：手动解析令牌（兼容直接调用场景）
    token = request.headers.get("X-AUTH-TOKEN", "")
    if not token:
        token = request.cookies.get("sessionId", "")
    if not token:
        return None
    return auth_store.get_session_user(token)


def require_user(request: Request) -> Dict[str, Any]:
    """FastAPI 依赖：要求用户已登录，否则返回 None。

    全局认证中间件已拦截未登录请求，此依赖仅用于路由内便捷获取用户。
    若直接调用（中间件未生效时），未登录返回 401 响应。
    """
    user = getattr(request.state, "user", None)
    if not user:
        # 兜底：尝试从请求头解析
        user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或会话已过期")
    return user


# ── 路由 ───────────────────────────────────────────────────
router = APIRouter(tags=["auth"])


@router.post("/login")
def login(req: LoginRequest, request: Request):
    """用户登录。

    前端使用 RSA 公钥加密密码后发送，后端解密后验证。
    """
    # 解密用户名和密码（前端使用 RSA 公钥加密）
    username = auth_service.rsa_decrypt(req.username)
    password = auth_service.rsa_decrypt(req.password)

    user = auth_store.authenticate(username, password)
    if not user:
        return fail("用户名或密码错误", code=400)

    client_ip = request.client.host if request.client else ""
    session = auth_store.create_session(user["id"], client_ip)

    # 构建登录响应
    # 如果用户没有项目，自动关联一个默认项目
    if not user.get("last_project_id"):
        projects = project_service.list()
        if projects:
            default_project_id = projects[0]["id"]
        else:
            # 自动创建默认项目
            proj = project_service.create({"name": "默认项目", "description": "系统自动创建"})
            default_project_id = proj["id"] if proj else ""
        if default_project_id:
            auth_store.update_user(user["id"], last_project_id=default_project_id)
            user["last_project_id"] = default_project_id
    if not user.get("last_organization_id"):
        auth_store.update_user(user["id"], last_organization_id="default-org")
        user["last_organization_id"] = "default-org"

    response_data = {
        "sessionId": session["sessionId"],
        "csrfToken": session["csrfToken"],
        "token": session["sessionId"],
        "id": user["id"],
        "name": user.get("name") or user["username"],
        "username": user["username"],
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "avatar": user.get("avatar", ""),
        "role": user.get("role", "user"),
        "lastOrganizationId": user.get("last_organization_id", "default-org"),
        "lastProjectId": user.get("last_project_id", ""),
        "loginType": ["LOCAL"],
        "userRoleRelations": [
            {
                "id": str(uuid.uuid4()),
                "userId": user["id"],
                "roleId": user.get("role", "user"),
                "sourceId": "global",
                "organizationId": "",
                "createTime": int(user.get("create_time", 0) * 1000),
                "createUser": "system",
                "userRolePermissions": [
                    {
                        "id": str(uuid.uuid4()),
                        "permissionId": "*",
                        "roleId": user.get("role", "user"),
                    }
                ],
                "userRole": {
                    "id": user.get("role", "user"),
                    "name": "管理员" if user.get("role") == "admin" else "普通用户",
                    "scopeId": "global",
                    "type": "SYSTEM",
                },
            }
        ],
        "userRolePermissions": [
            {
                "id": str(uuid.uuid4()),
                "userRole": {
                    "id": user.get("role", "user"),
                    "name": "管理员" if user.get("role") == "admin" else "普通用户",
                    "scopeId": "global",
                    "type": "SYSTEM",
                },
                "userRolePermissions": [
                    {
                        "id": str(uuid.uuid4()),
                        "permissionId": "*",
                        "roleId": user.get("role", "user"),
                    }
                ],
            }
        ],
        "userRoles": [
            {
                "id": user.get("role", "user"),
                "name": "管理员" if user.get("role") == "admin" else "普通用户",
                "scopeId": "global",
                "type": "SYSTEM",
            }
        ],
    }
    return ok(response_data)


@router.get("/is-login")
def is_login(request: Request):
    """检查当前是否已登录。"""
    user = get_current_user(request)
    if not user:
        return fail("未登录", code=401)

    session_id = request.headers.get("X-AUTH-TOKEN", "") or request.cookies.get("sessionId", "")

    # 如果用户没有项目，自动关联一个默认项目
    if not user.get("last_project_id"):
        projects = project_service.list()
        if projects:
            default_project_id = projects[0]["id"]
        else:
            proj = project_service.create({"name": "默认项目", "description": "系统自动创建"})
            default_project_id = proj["id"] if proj else ""
        if default_project_id:
            auth_store.update_user(user["id"], last_project_id=default_project_id)
            user["last_project_id"] = default_project_id
    if not user.get("last_organization_id"):
        auth_store.update_user(user["id"], last_organization_id="default-org")
        user["last_organization_id"] = "default-org"

    response_data = {
        "sessionId": session_id,
        "csrfToken": request.headers.get("CSRF-TOKEN", "") or request.cookies.get("csrfToken", ""),
        "token": session_id,
        "id": user["id"],
        "name": user.get("name") or user.get("username", ""),
        "username": user.get("username", ""),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "avatar": user.get("avatar", ""),
        "role": user.get("role", "user"),
        "lastOrganizationId": user.get("last_organization_id", "default-org"),
        "lastProjectId": user.get("last_project_id", ""),
        "loginType": ["LOCAL"],
        "userRoleRelations": [
            {
                "id": str(uuid.uuid4()),
                "userId": user["id"],
                "roleId": user.get("role", "user"),
                "sourceId": "global",
                "organizationId": "",
                "createTime": int(user.get("create_time", 0) * 1000),
                "createUser": "system",
                "userRolePermissions": [
                    {
                        "id": str(uuid.uuid4()),
                        "permissionId": "*",
                        "roleId": user.get("role", "user"),
                    }
                ],
                "userRole": {
                    "id": user.get("role", "user"),
                    "name": "管理员" if user.get("role") == "admin" else "普通用户",
                    "scopeId": "global",
                    "type": "SYSTEM",
                },
            }
        ],
        "userRolePermissions": [
            {
                "id": str(uuid.uuid4()),
                "userRole": {
                    "id": user.get("role", "user"),
                    "name": "管理员" if user.get("role") == "admin" else "普通用户",
                    "scopeId": "global",
                    "type": "SYSTEM",
                },
                "userRolePermissions": [
                    {
                        "id": str(uuid.uuid4()),
                        "permissionId": "*",
                        "roleId": user.get("role", "user"),
                    }
                ],
            }
        ],
        "userRoles": [
            {
                "id": user.get("role", "user"),
                "name": "管理员" if user.get("role") == "admin" else "普通用户",
                "scopeId": "global",
                "type": "SYSTEM",
            }
        ],
    }
    return ok(response_data)


@router.post("/signout")
def signout(request: Request):
    """用户登出。"""
    token = request.headers.get("X-AUTH-TOKEN", "") or request.cookies.get("sessionId", "")
    if token:
        auth_store.delete_session(token)
    return ok()


@router.get("/get-key")
def get_key():
    """返回 RSA 公钥（前端用于密码加密）。"""
    return ok(auth_service.get_rsa_public_key())


@router.get("/authentication/get-list")
def get_authentication_list():
    """返回可用的认证方式。"""
    return ok(["LOCAL"])


@router.post("/api/user/menu")
def get_menu_list():
    """返回前端菜单列表。"""
    menus = _build_menu_list()
    return ok(menus)


def _build_menu_list() -> List[Dict[str, Any]]:
    """构建前端菜单列表（与路由结构对应）。"""
    return [
        {
            "path": "/workstation",
            "name": "workbench",
            "component": "DEFAULT_LAYOUT",
            "redirect": "/workstation/home",
            "meta": {
                "locale": "menu.workbench",
                "icon": "icon-icon_home_filled",
                "order": 0,
                "hideChildrenInMenu": True,
                "roles": ["*"],
            },
            "children": [
                {
                    "path": "home",
                    "name": "workbenchIndex",
                    "component": "/workbench/homePage/index.vue",
                    "meta": {"locale": "menu.workbenchHome", "roles": ["*"]},
                },
            ],
        },
        {
            "path": "/case",
            "name": "caseManagement",
            "component": "DEFAULT_LAYOUT",
            "redirect": "/case/featureCase",
            "meta": {
                "locale": "menu.caseManagement",
                "icon": "icon-icon_test-tracking_filled",
                "order": 1,
                "roles": ["*"],
            },
            "children": [
                {
                    "path": "featureCase",
                    "name": "caseManagementFeatureCase",
                    "component": "/case-management/featureCase/index.vue",
                    "meta": {"locale": "menu.featureCase", "roles": ["*"]},
                },
            ],
        },
        {
            "path": "/api-test",
            "name": "apiTest",
            "component": "DEFAULT_LAYOUT",
            "redirect": "/api-test/definition",
            "meta": {
                "locale": "menu.apiTest",
                "icon": "icon-icon_api-test_filled",
                "order": 2,
                "roles": ["*"],
            },
            "children": [
                {
                    "path": "definition",
                    "name": "apiTestDefinition",
                    "component": "/api-test/management/index.vue",
                    "meta": {"locale": "menu.apiDefinition", "roles": ["*"]},
                },
            ],
        },
        {
            "path": "/test-plan",
            "name": "testPlan",
            "component": "DEFAULT_LAYOUT",
            "redirect": "/test-plan/testPlanIndex",
            "meta": {
                "locale": "menu.testPlan",
                "icon": "icon-icon_test-plan_filled",
                "order": 3,
                "roles": ["*"],
            },
            "children": [
                {
                    "path": "testPlanIndex",
                    "name": "testPlanIndex",
                    "component": "/test-plan/testPlan/index.vue",
                    "meta": {"locale": "menu.testPlanIndex", "roles": ["*"]},
                },
            ],
        },
        {
            "path": "/bug-management",
            "name": "bugManagement",
            "component": "DEFAULT_LAYOUT",
            "redirect": "/bug-management/bugManagementIndex",
            "meta": {
                "locale": "menu.bugManagement",
                "icon": "icon-icon_bug_filled",
                "order": 4,
                "roles": ["*"],
            },
            "children": [
                {
                    "path": "bugManagementIndex",
                    "name": "bugManagementIndex",
                    "component": "/bug-management/bug/index.vue",
                    "meta": {"locale": "menu.bugManagement", "roles": ["*"]},
                },
            ],
        },
        {
            "path": "/setting",
            "name": "setting",
            "component": "DEFAULT_LAYOUT",
            "redirect": "/setting/system/user",
            "meta": {
                "locale": "menu.setting",
                "icon": "icon-icon_setting_filled",
                "order": 10,
                "roles": ["*"],
            },
            "children": [
                {
                    "path": "system/user",
                    "name": "systemUser",
                    "component": "/setting/system/user/index.vue",
                    "meta": {"locale": "menu.systemUser", "roles": ["*"]},
                },
            ],
        },
    ]


# ── 个人信息 ───────────────────────────────────────────────
@router.get("/personal/get")
def get_personal_info(user: Dict[str, Any] = Depends(require_user)):
    """获取当前用户个人信息。"""
    data = {
        "id": user["id"],
        "name": user.get("name") or user.get("username", ""),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "language": user.get("language", "zh-CN"),
        "lastOrganizationId": user.get("last_organization_id", ""),
        "lastProjectId": user.get("last_project_id", ""),
        "source": "LOCAL",
        "enable": True,
        "deleted": False,
        "avatar": user.get("avatar", ""),
        "createTime": int(user.get("create_time", 0) * 1000),
        "updateTime": int(user.get("update_time", 0) * 1000),
        "orgProjectList": [],
    }
    return ok(data)


@router.post("/personal/update-info")
def update_personal_info(payload: PersonalUpdateBody, user: Dict[str, Any] = Depends(require_user)):
    """更新当前用户个人信息。"""
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = auth_store.update_user(user["id"], **updates)
    return ok(updated)


@router.post("/personal/update-password")
def update_password(payload: PasswordUpdateBody, user: Dict[str, Any] = Depends(require_user)):
    """修改密码。"""
    old_pwd = auth_service.rsa_decrypt(payload.oldPassword)
    new_pwd = auth_service.rsa_decrypt(payload.newPassword)

    if auth_store.change_password(user["id"], old_pwd, new_pwd):
        # 安全加固：修改密码后吊销该用户的全部会话，防止已泄露会话持续有效
        auth_store.revoke_user_sessions(user["id"])
        return ok()
    return fail("旧密码错误", code=400)


@router.post("/personal/update-locale")
def update_locale(payload: LocaleUpdateBody, user: Dict[str, Any] = Depends(require_user)):
    """更新语言偏好。"""
    auth_store.update_user(user["id"], language=payload.language)
    return ok()


# ── 本地执行配置 ──────────────────────────────────────────
@router.get("/user/local/config/get")
def get_local_configs(user: Dict[str, Any] = Depends(require_user)):
    """获取本地执行配置列表。"""
    configs = auth_store.get_local_configs(user["id"])
    return ok(configs)


@router.post("/user/local/config/add")
def add_local_config(payload: LocalConfigAddBody, user: Dict[str, Any] = Depends(require_user)):
    """添加本地执行配置。"""
    config = auth_store.add_local_config(user["id"], payload.user_url, payload.type)
    return ok(config)


@router.post("/user/local/config/update")
def update_local_config(payload: LocalConfigUpdateBody):
    """更新本地执行配置。"""
    auth_store.update_local_config(payload.id, payload.user_url)
    return ok()


@router.get("/user/local/config/enable")
def enable_local_config(id: str = ""):
    """启用本地执行配置。"""
    auth_store.toggle_local_config(id, True)
    return ok()


@router.get("/user/local/config/disable")
def disable_local_config(id: str = ""):
    """禁用本地执行配置。"""
    auth_store.toggle_local_config(id, False)
    return ok()


@router.get("/user/local/config/default-locale")
def get_default_locale():
    """获取默认语言。"""
    return ok("zh-CN")


# ── API Key 管理 ──────────────────────────────────────────
@router.get("/user/api/key/list")
def list_api_keys(user: Dict[str, Any] = Depends(require_user)):
    """获取当前用户 API Key 列表。"""
    keys = auth_store.list_api_keys(user["id"])
    return ok(keys)


@router.post("/user/api/key/add")
def add_api_key(payload: ApiKeyAddBody, user: Dict[str, Any] = Depends(require_user)):
    """创建 API Key。"""
    key = auth_store.create_api_key(user["id"], payload.description, payload.forever, payload.expire_time)
    return ok(key)


@router.post("/user/api/key/enable")
def enable_api_key(payload: ApiKeyIdBody):
    """启用 API Key。"""
    auth_store.toggle_api_key(payload.id, True)
    return ok()

@router.post("/user/api/key/disable")
def disable_api_key(payload: ApiKeyIdBody):
    """禁用 API Key。"""
    auth_store.toggle_api_key(payload.id, False)
    return ok()

@router.post("/user/api/key/delete")
def delete_api_key(payload: ApiKeyIdBody):
    """删除 API Key。"""
    auth_store.delete_api_key(payload.id)
    return ok()

# ── 用户管理（管理员） ────────────────────────────────────
@router.get("/system/user/list")
def list_users():
    """获取用户列表。"""
    users = auth_store.list_users()
    return ok(users)


@router.post("/system/user/page", operation_id="system_user_page_post")
@router.get("/system/user/page", operation_id="system_user_page_get")
def system_user_page(request: Request, payload: Optional[SystemUserPageBody] = None):
    """系统用户分页列表。"""
    if request.method == "POST":
        payload = payload or SystemUserPageBody()
        current = int(payload.current)
        pageSize = int(payload.pageSize)
        keyword = payload.keyword
    else:
        current = int(request.query_params.get("current", 1))
        pageSize = int(request.query_params.get("pageSize", 10))
        keyword = request.query_params.get("keyword", "")
    users = auth_store.list_users()
    if keyword:
        users = [u for u in users if keyword.lower() in u.get("username", "").lower()
                 or keyword.lower() in u.get("name", "").lower()
                 or keyword.lower() in u.get("email", "").lower()]
    total = len(users)
    start = (current - 1) * pageSize
    page_users = users[start:start + pageSize]

    # 批量反查用户所属组织（避免 N+1 逐用户 SQL 查询拖慢列表加载）
    org_map: Dict[str, List[Dict[str, Any]]] = {}
    try:
        from app.services.organization_service import organization_service

        page_user_ids = [u.get("id", "") for u in page_users]
        org_map = organization_service.list_orgs_by_users(page_user_ids)
    except Exception:
        # 组织反查异常不影响用户列表主流程
        org_map = {}

    items = [_with_user_relations(u, org_map.get(u.get("id", ""), [])) for u in page_users]
    return ok({
            "list": items,
            "total": total,
            "pageSize": pageSize,
            "current": current,
        })


def _user_role_item(role: str) -> Dict[str, Any]:
    """将系统用户 role 映射为系统用户组项（与前端 UserRoleListItem 对齐）。"""
    role = role or "user"
    name = "系统管理员" if role == "admin" else "普通用户"
    return {
        "id": role,
        "name": name,
        "description": name,
        "internal": True,
        "type": "SYSTEM",
        "scopeId": "SYSTEM",
        "createTime": 0,
        "updateTime": 0,
        "createUser": "admin",
    }


def _organization_item(org: Dict[str, Any]) -> Dict[str, Any]:
    """将组织存储对象映射为前端 OrganizationListItem 结构。"""
    return {
        "id": org.get("id", ""),
        "num": org.get("num", 0),
        "name": org.get("name", ""),
        "description": org.get("description", ""),
        "createTime": int((org.get("create_time", 0) or 0) * 1000),
        "updateTime": int((org.get("update_time", 0) or 0) * 1000),
        "createUser": org.get("create_user", "admin"),
        "updateUser": org.get("update_user", "admin"),
        "deleted": bool(org.get("deleted", 0)),
        "deleteUser": "",
        "deleteTime": 0,
        "enable": org.get("status", "active") == "active",
    }


def _with_user_relations(user: Dict[str, Any], orgs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """为用户补充所属组织(organizationList)与用户组(userRoleList)字段。

    该页面前端会直接对每条记录执行
    ``record.organizationList.filter(...)`` / ``record.userRoleList.filter(...)``，
    若缺失这两个数组字段会导致渲染抛异常、页面空白。

    - ``orgs``：可选，调用方已批量反查到的用户组织列表；
      缺省时按用户 ID 单查（兼容其它调用路径）。
    """
    item = dict(user)
    # 用户组：由系统用户 role 映射
    item["userRoleList"] = [_user_role_item(item.get("role", "user"))]
    # 所属组织：优先使用调用方批量反查结果，避免 N+1 逐用户 SQL
    if orgs is None:
        orgs = []
        try:
            from app.services.organization_service import organization_service

            orgs = organization_service.list_orgs_by_user(item.get("id", ""))
        except Exception:
            orgs = []
    try:
        item["organizationList"] = [_organization_item(o) for o in orgs]
    except Exception:
        item["organizationList"] = []
    return item


@router.get("/system/user/get")
def system_user_get(id: str = "", username: str = "", keyword: str = ""):
    """获取系统用户详情。keyword 可为邮箱或用户 ID。"""
    user = None
    search = keyword or username or id
    if search:
        user = auth_store.get_user_by_id(search)
        if not user:
            user = auth_store.get_user_by_username(search)
    if not user:
        return fail("用户不存在", code=404)
    if user:
        user.pop("password_hash", None)
    return ok(user)


@router.post("/system/user/add")
async def add_user(request: Request, payload: Optional[UserAddBody] = None):
    """添加用户（兼容前端批量创建与后端单用户两种格式）。

    前端 user 页通过 batchCreateUser 发送:
      {userInfoList: [{name, email, phone}], userRoleIdList: ["admin"]}
    测试/脚本采用单用户格式:
      {username, password, name, email, phone, role}
    """
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}

    # ── 单用户格式: {username, ...} ──
    username = body.get("username", "") or (payload.username if payload else "")
    if username:
        password = body.get("password", "") or (payload.password if payload else "")
        if password:
            password = auth_service.rsa_decrypt(password) or password
        if not password:
            password = "123456"
        name = body.get("name", "") or (payload.name if payload else "") or username
        email = body.get("email", "") or (payload.email if payload else "")
        phone = body.get("phone", "") or (payload.phone if payload else "")
        role = body.get("role", "") or (payload.role if payload else "") or "user"
        if auth_store.get_user_by_username(username):
            return fail("用户名已存在", code=400)
        user = auth_store.create_user(
            username=username, password=password,
            name=name, email=email, phone=phone, role=role,
        )
        return ok(user)

    # ── 批量创建格式: {userInfoList: [...], userRoleIdList: [...]} ──
    user_info_list = body.get("userInfoList", []) or []
    if isinstance(user_info_list, str):
        import json as _json
        try:
            user_info_list = _json.loads(user_info_list)
        except Exception:
            user_info_list = []
    if not isinstance(user_info_list, list):
        user_info_list = []

    role_id_list = body.get("userRoleIdList", []) or []
    if isinstance(role_id_list, str):
        import json as _json
        try:
            role_id_list = _json.loads(role_id_list)
        except Exception:
            role_id_list = [role_id_list]
    if not isinstance(role_id_list, list):
        role_id_list = [role_id_list] if role_id_list else []
    default_role = str(role_id_list[0]) if role_id_list else "user"

    # 兼容：只有 userInfoList 为空但 payload 有 username 时走单用户逻辑
    if not user_info_list and payload and payload.username:
        username = payload.username
        password = auth_service.rsa_decrypt(payload.password) or payload.password
        if not username or not password:
            return fail("用户名和密码不能为空", code=400)
        if auth_store.get_user_by_username(username):
            return fail("用户名已存在", code=400)
        user = auth_store.create_user(
            username=username, password=password,
            name=payload.name or username, email=payload.email,
            phone=payload.phone, role=payload.role,
        )
        return ok(user)

    if not user_info_list:
        return fail("用户信息不能为空", code=400)

    error_emails: Dict[str, str] = {}
    success_list: List[Dict[str, Any]] = []
    all_users = auth_store.list_users()
    for item in user_info_list:
        if not isinstance(item, dict):
            continue
        item_name = str(item.get("name", "") or "")
        item_email = str(item.get("email", "") or "")
        item_phone = str(item.get("phone", "") or "")
        if not item_email:
            continue
        uname = item_email.split("@")[0] or item_email

        exists = False
        for u in all_users:
            if u.get("email", "").lower() == item_email.lower() or \
               u.get("username", "").lower() == uname.lower():
                exists = True
                break
        if exists:
            error_emails[item_email] = "用户已存在"
            continue

        try:
            user = auth_store.create_user(
                username=uname,
                password="123456",
                name=item_name or uname,
                email=item_email,
                phone=item_phone,
                role=default_role,
            )
            success_list.append(user)
            all_users.append(user)
        except Exception:
            error_emails[item_email] = "创建用户失败"

    return ok({
        "errorEmails": error_emails if error_emails else None,
        "successList": success_list,
    })


def _resolve_batch_user_ids(body: dict) -> List[str]:
    """从批量请求体中解析用户 ID 列表。

    前端 user 页的删除/启停/重置密码均以批量参数发送:
      {selectIds, selectAll, excludeIds, condition}
    即使只操作单个用户，也用 selectIds: [id] 数组。
    后端单用户调用使用 {id: "xxx"} 格式。

    当 selectAll=true 时按 condition 筛选全部匹配用户再排除 excludeIds。
    """
    if not isinstance(body, dict):
        return []
    sid = body.get("id") or body.get("userId") or ""
    has_batch = body.get("selectIds") is not None or body.get("selectAll") is not None
    if sid and not has_batch:
        return [str(sid)]

    select_ids = body.get("selectIds", []) or []
    if isinstance(select_ids, str):
        select_ids = [select_ids]
    ids = [str(i) for i in select_ids if str(i)]

    select_all = bool(body.get("selectAll", False))
    if select_all:
        keyword = ""
        cond = body.get("condition") or {}
        if isinstance(cond, dict):
            keyword = cond.get("keyword", "") or ""
        elif isinstance(cond, str):
            keyword = cond
        all_users = auth_store.list_users()
        if keyword:
            kw = keyword.lower()
            all_users = [u for u in all_users
                         if kw in (u.get("username", "") or "").lower()
                         or kw in (u.get("name", "") or "").lower()
                         or kw in (u.get("email", "") or "").lower()]
        exclude_ids = body.get("excludeIds", []) or []
        if isinstance(exclude_ids, str):
            exclude_ids = [exclude_ids]
        exclude_set = {str(e) for e in exclude_ids}
        ids = [u.get("id", "") for u in all_users
               if str(u.get("id", "")) and str(u.get("id", "")) not in exclude_set]
    return [uid for uid in ids if uid]


@router.post("/system/user/update")
async def update_user(request: Request, payload: Optional[UserUpdateBody] = None):
    """更新用户（兼容前端携带 userRoleIdList 的格式）。

    前端 user 页通过 updateUserInfo 发送:
      {id, name, email, phone, userRoleIdList: ["admin"]}
    userRoleIdList 中的首个 ID 作为用户的 role 值。
    """
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}

    user_id = body.get("id", "") or (payload.id if payload else "")
    if not user_id:
        return fail("用户ID不能为空", code=400)

    updates: Dict[str, Any] = {}
    for key in ("name", "email", "phone", "avatar", "language"):
        if body.get(key) is not None:
            updates[key] = body[key]
        elif payload and getattr(payload, key, None) is not None:
            updates[key] = getattr(payload, key)

    if body.get("role") is not None:
        updates["role"] = body["role"]
    elif payload and payload.role is not None:
        updates["role"] = payload.role

    # 处理 userRoleIdList → role
    role_id_list = body.get("userRoleIdList")
    if role_id_list is None and payload:
        role_id_list = getattr(payload, "userRoleIdList", None)
    if role_id_list:
        if isinstance(role_id_list, str):
            import json as _json
            try:
                role_id_list = _json.loads(role_id_list)
            except Exception:
                role_id_list = [role_id_list]
        if isinstance(role_id_list, list) and role_id_list:
            updates["role"] = str(role_id_list[0])

    # 同步 user_group_members 关联
    if role_id_list:
        if isinstance(role_id_list, str):
            import json as _json
            try:
                role_id_list = _json.loads(role_id_list)
            except Exception:
                role_id_list = [role_id_list]
        if isinstance(role_id_list, list):
            try:
                for grp in auth_service.list_groups("SYSTEM", "global"):
                    auth_service.remove_group_member(grp.get("id", ""), user_id)
                user = auth_store.get_user_by_id(user_id)
                for rid in role_id_list:
                    rid_str = str(rid)
                    try:
                        auth_service.add_group_member(
                            group_id=rid_str, user_id=user_id,
                            username=user.get("username", "") if user else "",
                            name=user.get("name", "") if user else "",
                            email=user.get("email", "") if user else "",
                            group_type="SYSTEM",
                            scope_id="global",
                        )
                    except Exception:
                        pass
            except Exception:
                pass

    if not updates:
        return ok(auth_store.get_user_by_id(user_id))

    user = auth_store.update_user(user_id, **updates)
    if not user:
        return fail("用户不存在", code=404)
    return ok(user)


@router.post("/system/user/delete")
async def delete_user(request: Request, payload: Optional[UserIdBody] = None):
    """删除用户（兼容批量 selectIds 与单用户 id 两种格式）。"""
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}
    user_ids = _resolve_batch_user_ids(body)
    if not user_ids and payload and payload.id:
        user_ids = [payload.id]
    deleted_count = 0
    for uid in user_ids:
        if auth_store.delete_user(uid):
            deleted_count += 1
    return ok({"deleted": deleted_count})


@router.post("/system/user/update/enable")
async def toggle_user_enabled(request: Request, payload: Optional[UserIdBody] = None):
    """启用/禁用用户（兼容批量 selectIds 与单用户 id 两种格式）。"""
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}

    if body.get("enable") is not None:
        enable = bool(body.get("enable"))
    elif body.get("status") is not None:
        enable = str(body.get("status")) == "enable"
    elif payload and payload.enable is not None:
        enable = bool(payload.enable)
    elif payload and payload.status is not None:
        enable = payload.status == "enable"
    else:
        enable = True

    user_ids = _resolve_batch_user_ids(body)
    if not user_ids and payload and payload.id:
        user_ids = [payload.id]

    if not user_ids:
        return fail("用户不存在", code=404)

    changed = 0
    for uid in user_ids:
        if auth_store.set_user_enabled(uid, enable):
            changed += 1
    if changed == 0:
        return fail("用户不存在", code=404)
    return ok({"changed": changed})


@router.post("/system/user/reset/password")
async def reset_user_password(request: Request, payload: Optional[UserIdBody] = None):
    """重置用户密码（兼容批量 selectIds 与单用户 id 两种格式）。"""
    body = await read_body(request)
    if not isinstance(body, dict):
        body = {}

    password = body.get("password", "") or (payload.password if payload else "")
    if password:
        password = auth_service.rsa_decrypt(password) or password
    if not password:
        return fail("密码不能为空", code=400)

    user_ids = _resolve_batch_user_ids(body)
    if not user_ids and payload and payload.id:
        user_ids = [payload.id]

    if not user_ids:
        return fail("用户不存在", code=404)

    changed = 0
    for uid in user_ids:
        if auth_store.reset_password(uid, password):
            changed += 1
            try:
                auth_store.revoke_user_sessions(uid)
            except Exception:
                pass
    if changed == 0:
        return fail("用户不存在", code=404)
    return ok({"changed": changed})




@router.post("/system/user/import")
async def import_users(request: Request):
    """导入用户（支持 JSON/表单数组）。

    前端经 MSR.uploadFile 以 multipart/form-data 上传 userList，
    需兼容 JSON 请求体；属文件上传场景，保留 form/JSON 双格式解析。
    """
    items = []
    try:
        payload = UserImportBody.model_validate(await read_body(request))
        items = payload.users or payload.userList
    except Exception:
        form = await request.form()
        import json as _json
        for k in form:
            if k == "userList":
                try:
                    raw = _json.loads(form[k])
                    items = [ImportUserItem.model_validate(u) for u in raw]
                except Exception:
                    items = []
                break
    created = 0
    for u in items:
        username = u.username
        password = auth_service.rsa_decrypt(u.password) or "123456"
        if not username or auth_store.get_user_by_username(username):
            continue
        auth_store.create_user(
            username=username, password=password,
            name=u.name or username, email=u.email,
            phone=u.phone, role=u.role,
        )
        created += 1
    return ok({"successCount": created})


@router.get("/system/user/get/global/system/role")
def get_system_roles():
    """获取全局系统角色。

    前端 SystemRole 模型要求每条角色包含 selected / closeable 等字段，
    缺失会导致用户表单里用户组下拉无法正确预设/切换，页面异常。
    """
    return ok([
        {
            "id": "admin",
            "name": "系统管理员",
            "description": "系统管理员",
            "selected": False,
            "closeable": True,
            "internal": True,
            "type": "SYSTEM",
            "scopeId": "SYSTEM",
            "createTime": 0,
            "updateTime": 0,
            "createUser": "admin",
        },
        {
            "id": "user",
            "name": "普通用户",
            "description": "普通用户",
            "selected": True,
            "closeable": True,
            "internal": True,
            "type": "SYSTEM",
            "scopeId": "SYSTEM",
            "createTime": 0,
            "updateTime": 0,
            "createUser": "admin",
        },
    ])
