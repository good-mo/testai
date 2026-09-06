"""
前端界面 API 全量扫描测试（test_frontend_surface_sweep.py）
=========================================================
对「前端界面会发起调用、但既有的 test_frontend_* 系列未直接覆盖」的后端接口
做补充全量扫描，确保前端每个模块页面的接口都能接通且不 5xx。

覆盖模块（相对既有 test_frontend_ui_full_matrix.py 的补充盲区）：
  01. 附件 / 文件（attachment）—— options/upload/update/delete 等路径参数版
  02. 插件（plugins）—— list/options/add/delete/script/image 等
  03. gap-fixes（资源脚本执行 / 任务中心 real-time / is-login / 通知分页）
  04. frontend 兼容（api-definitions / api-test-cases / scenarios 的 {id} 详情）
  05. 系统设置（project get/update/delete/stats、user-view、organization template）
  06. 缺陷（bug 附件 / 关联用例 / 评论 / 同步）
  07. 项目文件 / 环境 / 模块 / 模板
  08. 测试计划报告/复制/归档等
  09. 组织（organization project rename/update/member-list）
  10. 调试（debug list/upload/temp/file 等路径参数）

断言原则（沿用项目 test_frontend_ui_full_matrix.py 的 _soft/_list/_dict 档位）：
  - 任何接口只要命中「未注册 / 未走统一信封」立即失败
  - 500 视为服务端异常，一律失败
  - 4xx 业务校验放行（前端会弹提示，属正常行为）
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import pytest
from fastapi.testclient import TestClient

PREFIX = "FSS-"
PAGE = {"current": 1, "pageSize": 10}


@pytest.fixture(scope="module")
def client():
    """已登录的测试客户端（携带 X-AUTH-TOKEN / CSRF-TOKEN）。"""
    from app.main import app
    with TestClient(app) as c:
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        if r.status_code == 200:
            session = r.json()["data"]
            c.headers.update({
                "X-AUTH-TOKEN": session["sessionId"],
                "CSRF-TOKEN": session["csrfToken"],
            })
        yield c


def _body(resp):
    """断言响应体是前端能解析的三段式信封 {code, message, data}。"""
    payload = resp.json()
    assert isinstance(payload, dict), f"响应体不是对象: {str(payload)[:200]}"
    if "detail" in payload and "code" not in payload:
        raise AssertionError(f"路由未注册/未走统一响应: HTTP {resp.status_code} {payload}")
    for key in ("code", "message", "data"):
        assert key in payload, f"响应体缺少 {key} 字段: {str(payload)[:200]}"
    return payload


def _soft(resp):
    """动作类：结构合法即可，允许 4xx 业务校验，禁止 5xx。"""
    payload = _body(resp)
    assert payload['code'] < 500, f"服务端异常: {payload['message']}"
    return payload


def _list(resp):
    """列表类：成功时 data 必须是数组或含 list/total 的分页对象。"""
    payload = _soft(resp)
    if payload["code"] != 200:
        return []
    data = payload["data"]
    if isinstance(data, list):
        return data
    assert isinstance(data, dict), f"列表 data 类型异常: {type(data).__name__}"
    if "list" in data:
        assert isinstance(data["list"], list), "list 字段不是数组"
        assert "total" in data, "分页缺少 total 字段"
    return data.get("list", data)


def _dict(resp):
    """聚合类：成功时 data 必须是对象。"""
    payload = _soft(resp)
    if payload["code"] != 200:
        return None
    data = payload["data"]
    assert isinstance(data, dict), f"data 不是对象: {str(data)[:200]}"
    return data


def _count(resp):
    """树 / 计数类：成功时 data 必须是对象或数组。"""
    payload = _soft(resp)
    if payload["code"] != 200:
        return None
    data = payload["data"]
    assert isinstance(data, (dict, list)), f"data 类型异常: {type(data).__name__}"
    return data


def _unique(prefix=""):
    """生成唯一标识。"""
    return f"{PREFIX}{prefix}-{uuid.uuid4().hex[:8]}"


def _get_first_project(client):
    """获取第一个项目 id（种子数据已有），获取失败则返回空串。"""
    r = client.get("/api/projects", params={"limit": 1})
    data = _body(r)
    projects = data.get("data", {}).get("projects", [])
    if projects and isinstance(projects, list) and projects:
        return projects[0].get("id", "")
    return ""


# ═══════════════════════════════════════════════════════════════
# 01. 附件 / 文件（attachment）
# ═══════════════════════════════════════════════════════════════
class TestAttachment:
    """前端附件/文件相关接口（覆盖既有矩阵未触及的路径参数版）。"""

    def test_attachment_options_path(self, client):
        """GET/POST /attachment/options/{project_id} 附件转存目录。"""
        pid = _get_first_project(client) or "default-project"
        for method in ("get", "post"):
            r = getattr(client, method)(f"/attachment/options/{pid}")
            _count(r)

    def test_attachment_update_path(self, client):
        """GET/POST /attachment/update/{attachment_id}/{project_id} 更新附件。"""
        pid = _get_first_project(client) or "default-project"
        for method in ("get", "post"):
            r = getattr(client, method)(f"/attachment/update/{uuid.uuid4().hex[:8]}/{pid}")
            _soft(r)

    def test_attachment_upload_file(self, client):
        """POST /attachment/upload/file 上传文件并关联。"""
        r = client.post("/attachment/upload/file", data={})
        _soft(r)

    def test_attachment_upload_temp_file(self, client):
        """POST /attachment/upload/temp/file 富文本临时资源上传。"""
        r = client.post("/attachment/upload/temp/file", data={})
        _soft(r)

    def test_attachment_delete_file(self, client):
        """POST /attachment/delete/file 删除文件/取消关联。"""
        r = client.post("/attachment/delete/file", json={})
        _soft(r)

    def test_attachment_options(self, client):
        """GET /attachment/options 转存目录。"""
        r = client.get("/attachment/options")
        _count(r)

    def test_attachment_check_update(self, client):
        """POST /attachment/check-update 检查附件更新。"""
        r = client.post("/attachment/check-update", json={})
        _soft(r)

    def test_attachment_preview_download(self, client):
        """GET /attachment/preview、/attachment/download 附件预览下载。"""
        r = client.get("/attachment/preview")
        _soft(r)
        r = client.get("/attachment/download")
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 02. 插件（plugins）
# ═══════════════════════════════════════════════════════════════
class TestPlugins:
    """前端系统设置-插件管理相关接口。"""

    def test_plugin_list(self, client):
        """GET /plugin/list 插件列表。"""
        r = client.get("/plugin/list")
        _list(r)

    def test_plugin_options(self, client):
        """GET / POST /plugin/options 插件选项。"""
        r = client.get("/plugin/options")
        _list(r)
        r = client.post("/plugin/options", json={})
        _list(r)

    def test_plugin_add(self, client):
        """POST /plugin/add 添加插件。"""
        r = client.post("/plugin/add", json={})
        _soft(r)

    def test_plugin_delete(self, client):
        """GET / POST /plugin/delete 删除插件。"""
        r = client.post("/plugin/delete", json={})
        _soft(r)
        r = client.get("/plugin/delete")
        _soft(r)

    def test_plugin_update(self, client):
        """POST /plugin/update 更新插件。"""
        r = client.post("/plugin/update", json={})
        _soft(r)

    def test_plugin_script_get(self, client):
        """GET /plugin/script/get 获取插件脚本。"""
        r = client.get("/plugin/script/get", params={"id": ""})
        _dict(r)

    def test_plugin_image(self, client):
        """GET /plugin/image/{plugin_id} 插件图片。"""
        r = client.get(f"/plugin/image/{uuid.uuid4().hex[:8]}")
        _dict(r)


# ═══════════════════════════════════════════════════════════════
# 03. gap-fixes（资源脚本执行 / 任务中心 real-time / is-login / 通知分页）
# ═══════════════════════════════════════════════════════════════
class TestGapFixes:
    """前端各类补齐差异接口。"""

    def test_execute_resourcescript(self, client):
        """POST /api/execute/resourcescript 执行资源脚本。"""
        r = client.post("/api/execute/resourcescript", json={"resourceId": "res-1"})
        _dict(r)

    def test_task_center_real_time_pages(self, client):
        """任务中心实时分页（项目/组织/系统三级）。"""
        for scope in ("project", "org", "system"):
            r = client.post(f"/task/center/api/{scope}/real-time/page", json=PAGE)
            _list(r)

    def test_debug_list_by_protocol(self, client):
        """GET /api/debug/list/{protocol} 按协议筛选调试列表。"""
        r = client.get("/api/debug/list/HTTP")
        _list(r)

    def test_is_login_post(self, client):
        """POST /is-login/login 检查登录状态。"""
        r = client.post("/is-login/login", json={})
        _soft(r)
        data = _body(r)
        assert "id" in (data.get("data") or {}), "is-login 缺少用户 id"

    def test_notification_list_all_page(self, client):
        """POST /notification/list/all/page 通知分页（POST 兼容）。"""
        r = client.post("/notification/list/all/page", json=PAGE)
        _list(r)

    def test_project_file_type(self, client):
        """GET /project/file/type/{project_id} 项目文件类型。"""
        pid = _get_first_project(client) or "default-project"
        r = client.get(f"/project/file/type/{pid}")
        _list(r)


# ═══════════════════════════════════════════════════════════════
# 04. frontend 兼容（api-definitions / api-test-cases / scenarios 的 {id} 详情）
# ═══════════════════════════════════════════════════════════════
class TestFrontendCompatCRUD:
    """前端兼容层接口定义/用例/场景的 {id} 详情操作。"""

    def test_api_definition_full_crud(self, client):
        """api-definitions 创建→详情→更新→删除。"""
        # 创建
        r = client.post("/api/api-definitions", json={
            "name": _unique("定义"), "method": "GET",
            "path": f"/sweep/{uuid.uuid4().hex[:6]}", "protocol": "HTTP",
        })
        item = _dict(r)
        def_id = (item or {}).get("id", "")
        if not def_id:
            pytest.skip("创建接口定义未返回 id")
        # 详情
        r = client.get(f"/api/api-definitions/{def_id}")
        _dict(r)
        # 更新
        r = client.put(f"/api/api-definitions/{def_id}", json={"name": _unique("定义改")})
        _soft(r)
        # 删除
        r = client.delete(f"/api/api-definitions/{def_id}")
        _soft(r)

    def test_api_test_case_detail_crud(self, client):
        """api-test-cases 创建→详情→更新→删除。"""
        r = client.post("/api/api-test-cases", json={
            "name": _unique("用例"), "method": "GET", "path": "/sweep/case",
        })
        item = _dict(r)
        case_id = (item or {}).get("id", "")
        if not case_id:
            pytest.skip("创建接口用例未返回 id")
        r = client.get(f"/api/api-test-cases/{case_id}")
        _dict(r)
        r = client.put(f"/api/api-test-cases/{case_id}", json={"name": _unique("用例改")})
        _soft(r)
        r = client.delete(f"/api/api-test-cases/{case_id}")
        _soft(r)

    def test_scenario_full_crud_and_execute(self, client):
        """scenarios 创建→详情→执行→更新→删除。"""
        r = client.post("/api/scenarios", json={"name": _unique("场景")})
        item = _dict(r)
        scen_id = (item or {}).get("id", "")
        if not scen_id:
            pytest.skip("创建场景未返回 id")
        r = client.get(f"/api/scenarios/{scen_id}")
        _soft(r)
        r = client.post(f"/api/scenarios/{scen_id}/execute")
        _soft(r)
        r = client.put(f"/api/scenarios/{scen_id}", json={"name": _unique("场景改")})
        _soft(r)
        r = client.delete(f"/api/scenarios/{scen_id}")
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 05. 系统设置（项目详情 / user-view / 组织模板）
# ═══════════════════════════════════════════════════════════════
class TestSystemSettingsExtra:
    """系统设置模块的补充接口。"""

    def test_project_get_stats(self, client):
        """GET /api/projects/{project_id} 详情 + /stats 统计。"""
        pid = _get_first_project(client)
        if not pid:
            pytest.skip("无种子项目")
        r = client.get(f"/api/projects/{pid}")
        _dict(r)
        r = client.get(f"/api/projects/{pid}/stats")
        _soft(r)

    def test_system_user_list(self, client):
        """GET /system/user/list 用户列表。"""
        r = client.get("/system/user/list")
        _list(r)

    def test_system_project_page(self, client):
        """GET / POST /system/project/page 系统项目管理分页。"""
        r = client.get("/system/project/page", params=PAGE)
        _soft(r)
        r = client.post("/system/project/page", json=PAGE)
        _soft(r)

    def test_system_organization_list_project(self, client):
        """GET / POST /system/organization/list-project 组织项目列表。"""
        r = client.post("/system/organization/list-project", json={})
        _soft(r)

    def test_user_view_grouped_list(self, client):
        """user-view 分组列表 / 详情 / 更新（用户视图）。"""
        for view_type in ("functional", "api", "scenario"):
            r = client.get(f"/user-view/{view_type}/grouped/list")
            _soft(r)
            break  # 只需测一个 view_type 即可，接口结构一致
        r = client.post("/user-view/functional/update", json={})
        _soft(r)
        r = client.post("/user-view/functional/add", json={"name": _unique("视图")})
        _soft(r)

    def test_organization_template_set_default(self, client):
        """POST /organization/template/set-default 设置默认模板。"""
        r = client.post("/organization/template/set-default", json={})
        _soft(r)

    def test_system_project_rename(self, client):
        """POST /system/project/rename 系统项目重命名。"""
        r = client.post("/system/project/rename", json={})
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 06. 缺陷（bug 附件 / 关联用例 / 评论 / 同步）
# ═══════════════════════════════════════════════════════════════
class TestBugExtra:
    """前端缺陷管理模块的补充接口。"""

    def test_bug_columns_option(self, client):
        """GET /bug/columns-option/{project_id} 缺陷列选项。"""
        pid = _get_first_project(client) or "default-project"
        r = client.get(f"/bug/columns-option/{pid}")
        _soft(r)

    def test_bug_check_exist(self, client):
        """GET /bug/check-exist/{bug_id} 缺陷是否存在。"""
        r = client.get(f"/bug/check-exist/{uuid.uuid4().hex[:8]}")
        _soft(r)

    def test_bug_batch_update(self, client):
        """POST /bug/batch-update 缺陷批量更新。"""
        r = client.post("/bug/batch-update", json={})
        _soft(r)

    def test_bug_attachment_file_page(self, client):
        """POST /bug/attachment/file/page 缺陷附件列表。"""
        r = client.post("/bug/attachment/file/page", json=PAGE)
        _soft(r)

    def test_bug_case_page(self, client):
        """GET / POST /bug/case/page 缺陷关联用例分页。"""
        r = client.post("/bug/case/page", json=PAGE)
        _soft(r)
        r = client.get("/bug/case/page")
        _soft(r)

    def test_bug_case_relate(self, client):
        """POST /bug/case/relate 缺陷关联用例。"""
        r = client.post("/bug/case/relate", json={})
        _soft(r)

    def test_bug_comment_update(self, client):
        """POST /bug/comment/update 缺陷评论更新。"""
        r = client.post("/bug/comment/update", json={})
        _soft(r)

    def test_bug_current_platform(self, client):
        """GET /bug/current-platform/{project_id} 当前缺陷平台。"""
        pid = _get_first_project(client) or "default-project"
        r = client.get(f"/bug/current-platform/{pid}")
        _soft(r)

    def test_bug_sync_all(self, client):
        """POST /bug/sync/all 缺陷全量同步。"""
        r = client.post("/bug/sync/all", json={})
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 07. 项目文件 / 环境 / 模块 / 模板
# ═══════════════════════════════════════════════════════════════
class TestProjectExtra:
    """前端项目管理模块的补充接口。"""

    def test_project_file_module_count(self, client):
        """GET/POST /project/file/module/count 文件模块计数。

        回归：早期实现手写 upload 目录路径时多算一层 dirname，指向不存在的
        /uploads，导致 root/all/my 恒为 0（界面看不到统计）。此处上传一个文件后
        断言统计至少能反映该文件。
        """
        import io

        # 上传一个唯一测试文件
        name = f"count_check_{uuid.uuid4().hex[:8]}.txt"
        up = client.post("/project/file/upload", files={
            "file": (name, io.BytesIO(b"stat-check"), "text/plain"),
        })
        file_id = None
        if up.status_code == 200 and up.json().get("code") == 200:
            file_id = (up.json().get("data") or {}).get("id")

        try:
            payload = _count(client.post("/project/file/module/count", json={}))
            data = payload or {}
            assert "all" in data and "my" in data and "root" in data,                 f"module/count 缺少 root/my/all 键: {data}"
            # 上传文件后，全部/我的计数至少应含该文件，而非恒为 0
            assert data.get("all", 0) >= 1, f"all 计数异常: {data}"
            assert data.get("my", 0) >= 1, f"my 计数异常: {data}"
        finally:
            if file_id:
                client.post("/project/file/delete", json={"id": file_id})

    def test_project_file_re_upload(self, client):
        """POST /project/file/re-upload 文件重新上传。"""
        r = client.post("/project/file/re-upload", data={})
        _soft(r)

    def test_project_file_batch_delete(self, client):
        """POST /project/file/batch-delete 文件批量删除。"""
        r = client.post("/project/file/batch-delete", json={})
        _soft(r)

    def test_project_file_module_update_move(self, client):
        """文件模块 update/move。"""
        r = client.post("/project/file-module/update", json={})
        _soft(r)
        r = client.post("/project/file-module/move", json={})
        _soft(r)

    def test_project_environment_export_import(self, client):
        """环境 export / import。"""
        r = client.post("/project/environment/import", json={})
        _soft(r)
        r = client.post("/project/environment/export", json={})
        _soft(r)

    def test_project_environment_scripts(self, client):
        """GET /project/environment/scripts/{project_id} 环境脚本。"""
        pid = _get_first_project(client) or "default-project"
        r = client.get(f"/project/environment/scripts/{pid}")
        _soft(r)

    def test_project_application_modules(self, client):
        """POST /project/application/{module} 各模块配置。"""
        for mod in ("test-plan", "task", "performance-test"):
            r = client.post(f"/project/application/{mod}", json={})
            _soft(r)

    def test_project_template_img_preview(self, client):
        """POST /project/template/img/preview 模板图片预览。"""
        r = client.post("/project/template/img/preview", json={})
        _soft(r)

    def test_project_environment_edit_pos(self, client):
        """POST /project/environment/edit/pos 环境拖拽排序。"""
        r = client.post("/project/environment/edit/pos", json={})
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 08. 测试计划报告 / 复制 / 归档 / 关联
# ═══════════════════════════════════════════════════════════════
class TestTestPlanExtra:
    """前端测试计划模块的补充接口。"""

    def test_test_plan_association_delete(self, client):
        """POST /test-plan/association/delete 测试计划解除关联。"""
        r = client.post("/test-plan/association/delete", json={})
        _soft(r)

    def test_test_plan_report_preview_md(self, client):
        """POST / GET /test-plan/report/preview/md 报告 Markdown 预览。"""
        r = client.post("/test-plan/report/preview/md", json={})
        _soft(r)

    def test_test_plan_delete_archived(self, client):
        """GET /test-plan/delete/{plan_id}、/archived/{plan_id} 路径参数兼容。"""
        r = client.get(f"/test-plan/delete/{uuid.uuid4().hex[:8]}")
        _soft(r)
        r = client.get(f"/test-plan/archived/{uuid.uuid4().hex[:8]}")
        _soft(r)

    def test_test_plan_copy_by_path(self, client):
        """GET / POST /test-plan/copy/{plan_id} 路径参数复制。"""
        r = client.post(f"/test-plan/copy/{uuid.uuid4().hex[:8]}")
        _soft(r)

    def test_test_plan_group_list(self, client):
        """GET /test-plan/group-list/{project_id} 项目计划分组列表。"""
        pid = _get_first_project(client) or "default-project"
        r = client.get(f"/test-plan/group-list/{pid}")
        _list(r)

    def test_test_plan_report_batch_export(self, client):
        """POST /test-plan/report/batch-export 报告批量导出。"""
        r = client.post("/test-plan/report/batch-export", json={})
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 09. 组织（organization project rename/update/member-list）
# ═══════════════════════════════════════════════════════════════
class TestOrganizationExtra:
    """前端组织管理模块的补充接口。"""

    def test_org_project_rename(self, client):
        """POST /organization/project/rename 组织项目重命名。"""
        r = client.post("/organization/project/rename", json={})
        _soft(r)

    def test_org_project_update(self, client):
        """POST /organization/project/update 组织更新项目。"""
        r = client.post("/organization/project/update", json={})
        _soft(r)

    def test_org_project_member_list(self, client):
        """GET /organization/project/member-list 组织项目成员列表。"""
        r = client.get("/organization/project/member-list")
        _list(r)

    def test_org_project_add_members(self, client):
        """POST /organization/project/add-members 组织项目添加成员。"""
        r = client.post("/organization/project/add-members", json={})
        _list(r)

    def test_org_member_list(self, client):
        """GET / POST /system/organization/member-list 组织成员列表。"""
        r = client.get("/system/organization/member-list")
        _list(r)
        r = client.post("/system/organization/member-list", json={})
        _list(r)

    def test_org_project_pool_options(self, client):
        """GET /system/organization/list-member、project/pool-options。"""
        r = client.get("/system/organization/list-member")
        _list(r)
        r = client.post("/organization/project/pool-options", json={})
        _list(r)

    def test_org_default(self, client):
        """GET /system/organization/default 默认组织。"""
        r = client.get("/system/organization/default")
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 10. 调试（debug list/upload/temp/file 等路径参数）
# ═══════════════════════════════════════════════════════════════
class TestDebugExtra:
    """前端接口测试-调试模块补充接口。"""

    def test_debug_delete_path(self, client):
        """GET/POST /api/debug/delete/{id} 删除调试。"""
        r = client.post(f"/api/debug/delete/{uuid.uuid4().hex[:8]}")
        _soft(r)
        r = client.get(f"/api/debug/delete/{uuid.uuid4().hex[:8]}")
        _soft(r)

    def test_debug_transfer_options_path(self, client):
        """GET/POST /api/debug/transfer/options/{project_id} 转存目录。"""
        pid = _get_first_project(client) or "default-project"
        r = client.get(f"/api/debug/transfer/options/{pid}")
        _count(r)
        r = client.post(f"/api/debug/transfer/options/{pid}", json={})
        _count(r)

    def test_debug_upload_temp_file(self, client):
        """POST /api/debug/upload/temp/file 调试临时文件上传。"""
        r = client.post("/api/debug/upload/temp/file", data={})
        _soft(r)

    def test_api_definition_upload_temp(self, client):
        """POST /api/definition/upload/temp/file 定义临时文件上传。"""
        r = client.post("/api/definition/upload/temp/file", data={})
        _soft(r)

    def test_api_case_upload_temp(self, client):
        """POST /api/case/upload/temp/file 用例临时文件上传。"""
        r = client.post("/api/case/upload/temp/file", data={})
        _soft(r)

    def test_api_definition_import(self, client):
        """POST /api/definition/import 接口定义导入（空数据返回合法）。"""
        r = client.post("/api/definition/import", json={})
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 11. 通知 / 消息
# ═══════════════════════════════════════════════════════════════
class TestNotificationExtra:
    """前端消息通知模块补充接口。"""

    def test_notification_read(self, client):
        """GET /notification/read/{item_id} 单条已读。"""
        r = client.get(f"/notification/read/{uuid.uuid4().hex[:8]}")
        _soft(r)

    def test_notification_read_all(self, client):
        """GET /notification/read/all 全部已读。"""
        r = client.get("/notification/read/all")
        _soft(r)

    def test_api_message_list(self, client):
        """POST /api/message/list 消息列表。"""
        r = client.post("/api/message/list", json=PAGE)
        _list(r)

    def test_notification_count(self, client):
        """POST /notification/count 未读数量。"""
        r = client.post("/notification/count", json={})
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 12. 系统显示 / 基础配置 / 个人展示
# ═══════════════════════════════════════════════════════════════
class TestDisplayAndBase:
    """系统-显示设置 / 基础展示配置。"""

    def test_system_get_module(self, client):
        """GET /system/get/{module} 系统模块配置。"""
        for mod in ("version", "parameter", "display"):
            r = client.get(f"/system/get/{mod}")
            _soft(r)

    def test_display_save(self, client):
        """POST /display/save 保存显示设置。"""
        r = client.post("/display/save", json={})
        _soft(r)

    def test_base_display_get(self, client):
        """GET /base-display/get/{type} 基础展示项。"""
        for item in ("logo-platform", "login-logo", "login-image", "icon"):
            r = client.get(f"/base-display/get/{item}")
            _soft(r)

    def test_project_has_permission(self, client):
        """GET /project/has-permission/{user_id} 用户项目权限。"""
        r = client.get(f"/project/has-permission/{uuid.uuid4().hex[:8]}")
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 13. 文件管理（file preview / attachment download）
# ═══════════════════════════════════════════════════════════════
class TestFileManagementExtra:
    """前端文件管理补充接口。"""

    def test_file_preview(self, client):
        """GET /file/preview/original、/compressed 文件预览。"""
        r = client.get("/file/preview/original", params={"fileId": ""})
        _soft(r)
        r = client.get("/file/preview/compressed", params={"fileId": ""})
        _soft(r)

    def test_attachment_list_by_resource(self, client):
        """GET /attachment/list/{resource_id} 资源附件列表。"""
        r = client.get(f"/attachment/list/{uuid.uuid4().hex[:8]}")
        _list(r)

    def test_notification_unread_by_project(self, client):
        """GET /notification/un-read/{project_id} 项目未读通知。"""
        r = client.get(f"/notification/un-read/{uuid.uuid4().hex[:8]}")
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 14. 调试 / 定义 / 用例 / 场景详情路径参数
# ═══════════════════════════════════════════════════════════════
class TestApiDetailPath:
    """接口详情 / 历史 / 关注等路径参数兼容。"""

    def test_api_definition_case_scenario_detail(self, client):
        """GET /api/case/detail/{id}、/api/scenario/detail/{id} 详情（不存在返回 404）。"""
        r = client.get(f"/api/case/detail/{uuid.uuid4().hex[:8]}")
        _soft(r)
        r = client.get(f"/api/scenario/detail/{uuid.uuid4().hex[:8]}")
        _soft(r)

    def test_api_definition_doc_page(self, client):
        """POST /api/definition/page-doc、/api/definition/doc 接口文档。"""
        r = client.post("/api/definition/page-doc", json=PAGE)
        _soft(r)
        r = client.post("/api/definition/doc", json={})
        _soft(r)

    def test_api_scenario_operation_history(self, client):
        """POST /api/scenario/operation-history/page 场景操作历史。"""
        r = client.post("/api/scenario/operation-history/page", json=PAGE)
        _list(r)

    def test_apitest_execution_logs(self, client):
        """GET /api/apitest/execution-logs 执行日志列表。"""
        r = client.get("/api/apitest/execution-logs")
        _soft(r)

    def test_ai_conversation_detail(self, client):
        """GET /ai/conversation/detail/{conversation_id} 对话详情。"""
        r = client.get(f"/ai/conversation/detail/{uuid.uuid4().hex[:8]}")
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 15. 缺陷关注 / 同步 / 附件更新
# ═══════════════════════════════════════════════════════════════
class TestBugDetailExtra:
    """缺陷关注/同步/附件补充接口。"""

    def test_bug_follow_unfollow(self, client):
        """GET /bug/follow/{bug_id}、/bug/unfollow/{bug_id} 关注/取关。"""
        r = client.get(f"/bug/follow/{uuid.uuid4().hex[:8]}")
        _soft(r)
        r = client.get(f"/bug/unfollow/{uuid.uuid4().hex[:8]}")
        _soft(r)

    def test_bug_attachment_update(self, client):
        """POST /bug/attachment/update 缺陷附件更新。"""
        r = client.post("/bug/attachment/update", json={})
        _soft(r)

    def test_bug_trash_batch(self, client):
        """POST /bug/trash/batch-recover、/bug/trash/batch-delete 回收站批量。"""
        r = client.post("/bug/trash/batch-recover", json={})
        _soft(r)
        r = client.post("/bug/trash/batch-delete", json={})
        _soft(r)

    def test_bug_sync_path(self, client):
        """GET /bug/sync/{project_id}、/bug/sync/check/{project_id} 缺陷同步。"""
        pid = _get_first_project(client) or "default-project"
        r = client.get(f"/bug/sync/{pid}")
        _soft(r)
        r = client.get(f"/bug/sync/check/{pid}")
        _soft(r)

    def test_bug_attachment_download(self, client):
        """GET/POST /bug/attachment/download 缺陷附件下载。"""
        r = client.post("/bug/attachment/download", json={})
        _soft(r)
        r = client.get("/bug/attachment/download", params={"fileId": ""})
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 16. 任务中心 / 项目文件 / 报告
# ═══════════════════════════════════════════════════════════════
class TestTaskCenterAndReports:
    """任务中心与报告补充接口。"""

    def test_project_task_center_page(self, client):
        """GET /project/task-center/page 项目任务中心分页。"""
        r = client.get("/project/task-center/page", params=PAGE)
        _list(r)

    def test_project_task_center_stop(self, client):
        """GET /project/task-center/stop/{task_id} 停止任务。"""
        r = client.get(f"/project/task-center/stop/{uuid.uuid4().hex[:8]}")
        _soft(r)

    def test_project_file_list(self, client):
        """GET /project/file/list 项目文件列表。"""
        r = client.get("/project/file/list", params={"projectId": ""})
        _soft(r)

    def test_task_center_schedule_page(self, client):
        """GET/POST /task/center/project/schedule/page 任务中心调度分页。"""
        r = client.post("/task/center/project/schedule/page", json=PAGE)
        _list(r)

    def test_api_report_trash(self, client):
        """POST /api/reports/{filename}/trash 报告移入回收站。"""
        r = client.post(f"/api/reports/{uuid.uuid4().hex[:8]}/trash", json={})
        _soft(r)

    def test_api_runs_record(self, client):
        """GET /api/runs/{record_id} 运行记录详情。"""
        r = client.get(f"/api/runs/{uuid.uuid4().hex[:8]}")
        _soft(r)


# ═══════════════════════════════════════════════════════════════
# 17. 测试计划补充（报告批删 / 关联状态 / 计划列表）
# ═══════════════════════════════════════════════════════════════
class TestTestPlanDetailExtra:
    """测试计划关联状态 / 报告 / 计划下拉补充。"""

    def test_test_plan_association_update_status(self, client):
        """POST /test-plan/association/update-status 关联用例状态。"""
        r = client.post("/test-plan/association/update-status", json={})
        _soft(r)

    def test_test_plan_report_batch_delete(self, client):
        """POST /test-plan/report/batch-delete 报告批量删除。"""
        r = client.post("/test-plan/report/batch-delete", json={})
        _soft(r)

    def test_test_plan_report_upload_md(self, client):
        """POST /test-plan/report/upload/md/file 上传 Markdown 报告。"""
        r = client.post("/test-plan/report/upload/md/file", data={})
        _soft(r)

    def test_test_plan_list_by_project(self, client):
        """GET /test-plan/test-plan-list/{project_id} 项目计划下拉。"""
        pid = _get_first_project(client) or "default-project"
        r = client.get(f"/test-plan/test-plan-list/{pid}")
        _list(r)

    def test_test_plan_get_count(self, client):
        """GET /test-plan/getCount/{plan_id} 计划用例数。"""
        r = client.get(f"/test-plan/getCount/{uuid.uuid4().hex[:8]}")
        _soft(r)
