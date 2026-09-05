"""测试路径参数兼容修复路由。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


def _login_client(client):
    """登录并添加认证头。"""
    r = client.post("/login", json={"username": "admin", "password": "admin123"})
    if r.status_code == 200:
        session = r.json()["data"]
        client.headers.update({
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        })
    return client



def test_ws_api_report_path():
    """WebSocket /ws/api/{report_id} 应正常工作。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    with client.websocket_connect("/ws/api/report123") as ws:
        data = ws.receive_text()
        assert "connected" in data
        assert "report123" in data
        ws.send_text("test")
        data = ws.receive_text()
        assert "pong" in data


def test_ws_debug_path():
    """WebSocket /ws/debug 应正常工作。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    with client.websocket_connect("/ws/debug") as ws:
        data = ws.receive_text()
        assert "connected" in data


def test_ws_debug_report_path():
    """WebSocket /ws/debug/{report_id} 应正常工作。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    with client.websocket_connect("/ws/debug/r1") as ws:
        data = ws.receive_text()
        assert "r1" in data


def test_ws_export_path():
    """WebSocket /ws/export 应正常工作。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    with client.websocket_connect("/ws/export") as ws:
        data = ws.receive_text()
        assert "connected" in data


def test_ws_export_report_path():
    """WebSocket /ws/export/{report_id} 应正常工作。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    with client.websocket_connect("/ws/export/e1") as ws:
        data = ws.receive_text()
        assert "e1" in data


def test_definition_stop_path():
    """接口定义停止（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/api/definition/stop/def123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_scenario_export_path():
    """场景导出（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/api/scenario/export/scn001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_scenario_stop_path():
    """场景停止（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.post("/api/scenario/stop/scn001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_scenario_update_priority_path():
    """场景更新优先级（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/api/scenario/update-priority/scn001/P0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_scenario_update_status_path():
    """场景更新状态（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.post("/api/scenario/update-status/scn001/Open")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_attachment_options_path():
    """附件选项（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/attachment/options/proj1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_attachment_update_path():
    """更新附件（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.post("/attachment/update/att1/proj1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_func_case_custom_field_path():
    """功能用例自定义字段（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/functional/case/custom/field/proj1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_func_case_module_delete_path():
    """功能用例模块删除（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.post("/functional/case/module/delete/mod1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_func_case_demand_cancel_path():
    """功能用例需求关联取消（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/functional/case/demand/cancel/case1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_org_template_delete_path():
    """组织模板删除（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.post("/organization/template/delete/tpl1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_project_template_delete_path():
    """项目模板删除（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/project/template/delete/tpl1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_project_template_get_path():
    """项目模板获取（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.post("/project/template/get/tpl1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_project_template_set_default_path():
    """项目模板设置默认（带路径参数）。

    前端调用顺序: setDefaultTemplate(projectId, id) -> /project/template/set-default/{projectId}/{id}。
    """
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    proj = "proj-tpl-default"
    # 先创建一条模板，得到真实 id
    created = client.post(
        "/project/template/add",
        json={
            "name": "默认设置模板",
            "scene": "FUNCTIONAL",
            "scopeId": proj,
            "customFields": [],
            "systemFields": [],
        },
    )
    assert created.status_code == 200
    tid = created.json()["data"]["id"]
    # 前端顺序: {projectId}/{templateId}
    resp = client.post(f"/project/template/set-default/{proj}/{tid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_test_plan_copy_path():
    """测试计划复制（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/test-plan/copy/plan1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_project_file_jar_status_path():
    """项目 JAR 文件状态（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/project/file/jar-file-status/jar1/proj1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_project_member_get_member_option_path():
    """项目成员选项（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.post("/project/member/get-member/option/proj1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_system_task_center_delete_path():
    """系统任务中心删除（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/system/task-center/exec-task/delete/task1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_org_task_center_schedule_switch_path():
    """组织任务中心定时任务切换（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.post("/organization/task-center/schedule/switch/sched1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_project_task_center_exec_stop_path():
    """项目任务中心执行停止（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/project/task-center/exec-task/stop/task1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_doc_share_download_file_path():
    """文档分享文件下载（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/api/doc/share/download/file/share1/file1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_doc_share_export_path():
    """文档分享导出（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.post("/api/doc/share/export/share1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_report_scenario_export_path():
    """场景报告导出（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/api/report/scenario/export/rpt1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_user_platform_validate_path():
    """用户平台验证（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/user/platform/validate/jira/user1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_ai_config_delete_path():
    """AI 配置删除（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.delete("/ai/config/delete/cfg1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_personal_model_delete_path():
    """个人模型删除（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.post("/personal/model/delete/model1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200


def test_plugin_image_path():
    """插件图片（带路径参数）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/plugin/image/plugin1")
    assert resp.status_code == 200


def test_project_template_enable_config_path():
    """项目模板启用配置（带路径参数）应返回状态映射。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/project/template/enable/config/p1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    status = data["data"]
    assert isinstance(status, dict)
    for key in ("FUNCTIONAL", "BUG", "API", "UI", "TEST_PLAN"):
        assert key in status
        assert isinstance(status[key], bool)


def test_project_custom_field_list_path():
    """项目自定义字段列表（带路径参数）应返回数组。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/project/custom/field/list/p1/FUNCTIONAL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)


def test_project_custom_field_crud_path():
    """项目自定义字段增删改查（带路径参数）应正常工作。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    field_body = {
        "name": "测试字段-路径",
        "scene": "FUNCTIONAL",
        "type": "INPUT",
        "remark": "desc",
        "scopeId": "p1",
        "enableOptionKey": False,
        "options": [],
        "used": False,
    }
    # 新增
    resp = client.post("/project/custom/field/add", json=field_body)
    assert resp.status_code == 200
    created = resp.json()["data"]
    assert created.get("id")
    field_id = created["id"]

    # 查询详情
    resp = client.get(f"/project/custom/field/get/{field_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == field_id

    # 列表包含新字段
    resp = client.get("/project/custom/field/list/p1/FUNCTIONAL")
    assert any(f["id"] == field_id for f in resp.json()["data"])

    # 删除
    resp = client.get(f"/project/custom/field/delete/{field_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["deleted"] is True

    # 删除后列表不含该字段
    resp = client.get("/project/custom/field/list/p1/FUNCTIONAL")
    assert all(f["id"] != field_id for f in resp.json()["data"])


def test_func_case_custom_field_returns_array():
    """功能用例自定义字段应返回数组格式（前端 getFilterCustomFields 依赖）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/functional/case/custom/field/proj1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)


def test_func_case_default_template_field_returns_template():
    """功能用例默认模板字段应返回 {id, customFields} 结构（前端 getCaseDefaultFields 依赖）。"""
    import app.main
    client = TestClient(app.main.app)
    _login_client(client)
    resp = client.get("/functional/case/default/template/field/proj1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    result = data["data"]
    assert "id" in result
    assert "name" in result
    assert isinstance(result.get("customFields"), list)
    assert len(result.get("customFields", [])) > 0
    # 验证默认字段包含 functional_priority
    has_priority = any(
        f.get("internalFieldKey") == "functional_priority"
        for f in result.get("customFields", [])
    )
    assert has_priority
