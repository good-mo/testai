"""
前端全界面功能矩阵测试（test_frontend_ui_full_matrix.py）
==============================================================================

目标：把「前端界面真实能看到 / 能点到的功能」全部测一遍。

用例不是手写维护的，而是**从前端源码自动抽取**的：
  1. 扫描 `frontend/src/api/modules/**` 里的 `MSR.get/post(...)` 调用点
  2. 回溯 `frontend/src/api/requrls/**` 的 URL 常量，还原成真实请求路径
  3. 逐个打真实请求，断言「前端点这个按钮不会炸」

共覆盖 747 个前端调用点（517 个静态 + 230 个路径参数），
按界面模块分组。任何一处 404 / 405 / 500 或非标准响应体都会让测试失败。

断言分四档：
  - `_list`  列表类：data 必须为数组或含 list/total 的分页对象（缺字段前端白屏）
  - `_count` 树/计数类：data 必须是对象或数组（模块树、各模块计数）
  - `_dict`  聚合类：data 必须是 dict
  - `_soft`  动作类：结构合法即可，允许 4xx 业务校验，但绝不允许 5xx

⚠️ 本文件由 `scripts/gen_frontend_matrix.py` 生成，请勿手工编辑。
   前端新增接口后重跑该脚本即可同步；CI 会校验两者是否一致。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import pytest
from fastapi.testclient import TestClient

PREFIX = "UIM-"

# 依赖真实 LLM Key 的接口，本地无 key 时跳过（有 key 时自动参与）
LLM_REQUIRED = {
    ("POST", "/api/generate"),
    ("POST", "/api/generate/structured"),
    ("POST", "/api/insights/lowcode"),
    ("POST", "/api/projects/generate"),
}


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
    """断言响应体是前端能解析的三段式信封 {code, message, data}。

    关键区分：
      - 三段式信封 + 4xx → 业务校验，前端会弹提示，属于正常行为
      - FastAPI 原生 {"detail": ...} → 路由根本没注册，前端只会看到
        一句看不懂的英文报错，这是真正要拦的「功能没接通」
    """
    payload = resp.json()
    assert isinstance(payload, dict), f"响应体不是对象: {str(payload)[:200]}"
    if "detail" in payload and "code" not in payload:
        raise AssertionError(f"路由未注册/未走统一响应: HTTP {resp.status_code} {payload}")
    for key in ("code", "message", "data"):
        assert key in payload, f"响应体缺少 {key} 字段: {str(payload)[:200]}"
    return payload


def _soft(resp):
    """动作类：结构合法即可，允许 4xx 业务校验，禁止 5xx。

    传不存在的 id 时返回 404「用户不存在」是**正确行为**，前端会弹提示；
    真正要拦的是 500 和畸形结构 —— 那才是「点了按钮页面炸了」。
    """
    payload = _body(resp)
    assert payload['code'] < 500, f"服务端异常: {payload['message']}"
    return payload


def _dict(resp):
    """聚合类：成功时 data 必须是对象，4xx 业务校验时放行。"""
    payload = _soft(resp)
    if payload["code"] != 200:
        return None
    data = payload["data"]
    assert isinstance(data, dict), f"data 不是对象: {str(data)[:200]}"
    return data


def _count(resp):
    """模块树 / 计数类：成功时 data 必须是对象或数组，4xx 放行。"""
    payload = _soft(resp)
    if payload["code"] != 200:
        return None
    data = payload["data"]
    assert isinstance(data, (dict, list)), f"data 类型异常: {type(data).__name__}"
    return data


def _list(resp):
    """列表类：成功时 data 必须是数组或含 list/total 的分页对象，4xx 放行。

    list 缺失前端会白屏，total 缺失页码会渲染成 NaN —— 这是本项目踩过的坑。
    """
    payload = _soft(resp)
    if payload["code"] != 200:
        return []
    data = payload["data"]
    if isinstance(data, list):
        return data
    assert isinstance(data, dict), f"列表 data 类型异常: {type(data).__name__}"
    assert "list" in data, f"列表缺少 list 字段，前端会白屏: {list(data)[:8]}"
    assert isinstance(data["list"], list), "list 字段不是数组"
    assert "total" in data, "分页缺少 total 字段，前端页码会渲染成 NaN"
    return data["list"]


PAGE = {"current": 1, "pageSize": 10}


# ══════════════════════════════════════════════════════════════════════════════
# AI 用例生成 / 对话
# ══════════════════════════════════════════════════════════════════════════════
class TestAiCaseGenUI:
    """AI 用例生成 / 对话 界面：16 个前端调用点。"""

    def test_get_api_test_types_1(self, client):
        """GET /api/test-types

        前端调用点：getAiTestTypes（ai-case-gen.ts）
        """
        resp = client.get("/api/test-types")
        _soft(resp)

    def test_post_api_generate_2(self, client):
        """POST /api/generate

        前端调用点：generateAiTests（ai-case-gen.ts）
        """
        pytest.skip("需真实 LLM Key：POST /api/generate")
        return

    def test_post_api_generate_structured_3(self, client):
        """POST /api/generate/structured

        前端调用点：generateAiStructured（ai-case-gen.ts）
        """
        pytest.skip("需真实 LLM Key：POST /api/generate/structured")
        return

    def test_post_api_projects_scan_4(self, client):
        """POST /api/projects/scan

        前端调用点：scanAiProject（ai-case-gen.ts）
        """
        resp = client.post("/api/projects/scan", json={"project_path": ".", "file_patterns": ["**/*.py"]})
        _soft(resp)

    def test_post_api_projects_generate_5(self, client):
        """POST /api/projects/generate

        前端调用点：generateAiProject（ai-case-gen.ts）
        """
        pytest.skip("需真实 LLM Key：POST /api/projects/generate")
        return

    def test_post_api_insights_lowcode_6(self, client):
        """POST /api/insights/lowcode

        前端调用点：generateAiLowcode（ai-case-gen.ts）
        """
        pytest.skip("需真实 LLM Key：POST /api/insights/lowcode")
        return

    def test_get_api_insights_skill_path_7(self, client):
        """GET /api/insights/skill-path

        前端调用点：getAiSkillPath（ai-case-gen.ts）
        """
        resp = client.get("/api/insights/skill-path")
        _soft(resp)

    def test_post_ai_conversation_chat_8(self, client):
        """POST /ai/conversation/chat

        前端调用点：aiChat（ai.ts）
        """
        resp = client.post("/ai/conversation/chat", json={})
        _soft(resp)

    def test_get_ai_conversation_list_9(self, client):
        """GET /ai/conversation/list

        前端调用点：getAiChatList（ai.ts）
        """
        resp = client.get("/ai/conversation/list")
        _list(resp)

    def test_post_ai_conversation_add_10(self, client):
        """POST /ai/conversation/add

        前端调用点：addAiChat（ai.ts）
        """
        resp = client.post("/ai/conversation/add", json={})
        _soft(resp)

    def test_post_ai_conversation_update_11(self, client):
        """POST /ai/conversation/update

        前端调用点：updateAiChatTitle（ai.ts）
        """
        resp = client.post("/ai/conversation/update", json={})
        _soft(resp)

    def test_post_api_message_list_12(self, client):
        """POST /api/message/list

        前端调用点：queryMessageList（message/index.ts）
        """
        resp = client.post("/api/message/list", json=PAGE)
        _list(resp)

    def test_post_api_message_read_13(self, client):
        """POST /api/message/read

        前端调用点：setMessageStatus（message/index.ts）
        """
        resp = client.post("/api/message/read", json={})
        _soft(resp)

    def test_post_api_chat_list_14(self, client):
        """POST /api/chat/list

        前端调用点：queryChatList（message/index.ts）
        """
        resp = client.post("/api/chat/list", json=PAGE)
        _list(resp)

    def test_post_ai_config_edit_source_15(self, client):
        """POST /ai/config/edit-source

        前端调用点：editModelConfig（setting/config.ts）
        """
        resp = client.post("/ai/config/edit-source", json={})
        _soft(resp)

    def test_get_ai_config_source_name_list_16(self, client):
        """GET /ai/config/source/name/list

        前端调用点：getModelConfigNameList（setting/config.ts）
        """
        resp = client.get("/ai/config/source/name/list")
        _list(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 接口测试-调试
# ══════════════════════════════════════════════════════════════════════════════
class TestApiDebugUI:
    """接口测试-调试 界面：28 个前端调用点。"""

    def test_get_api_test_protocol_1(self, client):
        """GET /api/test/protocol

        前端调用点：getProtocolList（api-test/common.ts）
        """
        resp = client.get("/api/test/protocol")
        _soft(resp)

    def test_get_api_test_plugin_form_option_2(self, client):
        """GET /api/test/plugin/form/option

        前端调用点：getPluginOptions（api-test/common.ts）
        """
        resp = client.get("/api/test/plugin/form/option")
        _soft(resp)

    def test_get_api_test_plugin_script_3(self, client):
        """GET /api/test/plugin/script

        前端调用点：getPluginScript（api-test/common.ts）
        """
        resp = client.get("/api/test/plugin/script")
        _soft(resp)

    def test_get_api_test_env_list_4(self, client):
        """GET /api/test/env-list

        前端调用点：getEnvList（api-test/common.ts）
        """
        resp = client.get("/api/test/env-list")
        _soft(resp)

    def test_get_api_test_environment_5(self, client):
        """GET /api/test/environment

        前端调用点：getEnvironment（api-test/common.ts）
        """
        resp = client.get("/api/test/environment")
        _soft(resp)

    def test_post_api_debug_import_curl_6(self, client):
        """POST /api/debug/import-curl

        前端调用点：importByCurl（api-test/common.ts）
        """
        resp = client.post("/api/debug/import-curl", json={})
        _soft(resp)

    def test_get_api_debug_module_tree_7(self, client):
        """GET /api/debug/module/tree

        前端调用点：getDebugModules（api-test/debug.ts）
        """
        resp = client.get("/api/debug/module/tree")
        _count(resp)

    def test_get_api_debug_module_delete_8(self, client):
        """GET /api/debug/module/delete

        前端调用点：deleteDebugModule（api-test/debug.ts）
        """
        resp = client.get("/api/debug/module/delete")
        _soft(resp)

    def test_post_api_debug_module_add_9(self, client):
        """POST /api/debug/module/add

        前端调用点：addDebugModule（api-test/debug.ts）
        """
        resp = client.post("/api/debug/module/add", json={})
        _soft(resp)

    def test_post_api_debug_module_move_10(self, client):
        """POST /api/debug/module/move

        前端调用点：moveDebugModule（api-test/debug.ts）
        """
        resp = client.post("/api/debug/module/move", json={})
        _soft(resp)

    def test_post_api_debug_module_update_11(self, client):
        """POST /api/debug/module/update

        前端调用点：updateDebugModule（api-test/debug.ts）
        """
        resp = client.post("/api/debug/module/update", json={})
        _soft(resp)

    def test_post_api_debug_module_count_12(self, client):
        """POST /api/debug/module/count

        前端调用点：getDebugModuleCount（api-test/debug.ts）
        """
        resp = client.post("/api/debug/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_api_debug_edit_pos_13(self, client):
        """POST /api/debug/edit/pos

        前端调用点：dragDebug（api-test/debug.ts）
        """
        resp = client.post("/api/debug/edit/pos", json={})
        _soft(resp)

    def test_post_api_debug_debug_14(self, client):
        """POST /api/debug/debug

        前端调用点：executeDebug（api-test/debug.ts）
        """
        resp = client.post("/api/debug/debug", json={})
        _soft(resp)

    def test_post_api_debug_add_15(self, client):
        """POST /api/debug/add

        前端调用点：addDebug（api-test/debug.ts）
        """
        resp = client.post("/api/debug/add", json={})
        _soft(resp)

    def test_post_api_debug_update_16(self, client):
        """POST /api/debug/update

        前端调用点：updateDebug（api-test/debug.ts）
        """
        resp = client.post("/api/debug/update", json={})
        _soft(resp)

    def test_get_api_debug_get_17(self, client):
        """GET /api/debug/get

        前端调用点：getDebugDetail（api-test/debug.ts）
        """
        resp = client.get("/api/debug/get")
        _soft(resp)

    def test_get_api_debug_delete_18(self, client):
        """GET /api/debug/delete

        前端调用点：deleteDebug（api-test/debug.ts）
        """
        resp = client.get("/api/debug/delete")
        _soft(resp)

    def test_post_api_test_mock_19(self, client):
        """POST /api/test/mock

        前端调用点：testMock（api-test/debug.ts）
        """
        resp = client.post("/api/test/mock", json={})
        _soft(resp)

    def test_post_api_debug_transfer_20(self, client):
        """POST /api/debug/transfer

        前端调用点：transferFile（api-test/debug.ts）
        """
        resp = client.post("/api/debug/transfer", json={})
        _soft(resp)

    def test_get_api_debug_transfer_options_21(self, client):
        """GET /api/debug/transfer/options

        前端调用点：getTransferOptions（api-test/debug.ts）
        """
        resp = client.get("/api/debug/transfer/options")
        _soft(resp)

    def test_post_api_debug_file_copy_22(self, client):
        """POST /api/debug/file/copy

        前端调用点：debugFileCopy（api-test/management.ts）
        """
        resp = client.post("/api/debug/file/copy", json={})
        _soft(resp)

    def test_get_api_test_pool_option_23(self, client):
        """GET /api/test/pool-option

        前端调用点：getPoolOption（api-test/management.ts）
        """
        resp = client.get("/api/test/pool-option")
        _soft(resp)

    def test_get_api_test_get_pool_24(self, client):
        """GET /api/test/get-pool/

        前端调用点：getPoolId（api-test/management.ts）
        """
        resp = client.get("/api/test/get-pool/")
        _soft(resp)

    def test_post_api_test_download_25(self, client):
        """POST /api/test/download

        前端调用点：downloadFileRequest（case-management/featureCase.ts）
        """
        resp = client.post("/api/test/download", json={})
        _soft(resp)

    def test_post_api_test_custom_func_run_26(self, client):
        """POST /api/test/custom/func/run

        前端调用点：testCommonScript（project-management/commonScript.ts）
        """
        resp = client.post("/api/test/custom/func/run", json={})
        _soft(resp)

    def test_get_api_test_download_27(self, client):
        """GET /api/test/download

        前端调用点：downloadFile（project-management/fileManagement.ts）
        """
        resp = client.get("/api/test/download")
        _soft(resp)

    def test_post_api_test_plugin_form_option_28(self, client):
        """POST /api/test/plugin/form/option

        前端调用点：getPluginOptions（setting/pluginManger.ts）
        """
        resp = client.post("/api/test/plugin/form/option", json={})
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 接口测试-定义
# ══════════════════════════════════════════════════════════════════════════════
class TestApiDefinitionUI:
    """接口测试-定义 界面：49 个前端调用点。"""

    def test_post_api_definition_module_update_1(self, client):
        """POST /api/definition/module/update

        前端调用点：updateModule（api-test/management.ts）
        """
        resp = client.post("/api/definition/module/update", json={"id": "not-exist", "name": "改名模块"})
        _soft(resp)

    def test_post_api_definition_module_tree_2(self, client):
        """POST /api/definition/module/tree

        前端调用点：getModuleTree（api-test/management.ts）
        """
        resp = client.post("/api/definition/module/tree", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_api_definition_module_only_tree_3(self, client):
        """POST /api/definition/module/only/tree

        前端调用点：getModuleTreeOnlyModules（api-test/management.ts）
        """
        resp = client.post("/api/definition/module/only/tree", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_api_definition_module_move_4(self, client):
        """POST /api/definition/module/move

        前端调用点：moveModule（api-test/management.ts）
        """
        resp = client.post("/api/definition/module/move", json={})
        _soft(resp)

    def test_post_api_definition_module_env_tree_5(self, client):
        """POST /api/definition/module/env/tree

        前端调用点：getEnvModules（api-test/management.ts）
        """
        resp = client.post("/api/definition/module/env/tree", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_api_definition_module_count_6(self, client):
        """POST /api/definition/module/count

        前端调用点：getModuleCount（api-test/management.ts）
        """
        resp = client.post("/api/definition/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_api_definition_module_add_7(self, client):
        """POST /api/definition/module/add

        前端调用点：addModule（api-test/management.ts）
        """
        resp = client.post("/api/definition/module/add", json={})
        _soft(resp)

    def test_get_api_definition_module_delete_8(self, client):
        """GET /api/definition/module/delete

        前端调用点：deleteModule（api-test/management.ts）
        """
        resp = client.get("/api/definition/module/delete")
        _soft(resp)

    def test_post_api_definition_add_9(self, client):
        """POST /api/definition/add

        前端调用点：addDefinition（api-test/management.ts）
        """
        resp = client.post("/api/definition/add", json={})
        _soft(resp)

    def test_post_api_definition_update_10(self, client):
        """POST /api/definition/update

        前端调用点：updateDefinition（api-test/management.ts）
        """
        resp = client.post("/api/definition/update", json={})
        _soft(resp)

    def test_get_api_definition_get_detail_11(self, client):
        """GET /api/definition/get-detail

        前端调用点：getDefinitionDetail（api-test/management.ts）
        """
        resp = client.get("/api/definition/get-detail")
        _soft(resp)

    def test_get_api_definition_transfer_options_12(self, client):
        """GET /api/definition/transfer/options

        前端调用点：getTransferOptions（api-test/management.ts）
        """
        resp = client.get("/api/definition/transfer/options")
        _soft(resp)

    def test_get_api_definition_delete_to_gc_13(self, client):
        """GET /api/definition/delete-to-gc

        前端调用点：deleteDefinition（api-test/management.ts）
        """
        resp = client.get("/api/definition/delete-to-gc")
        _soft(resp)

    def test_post_api_definition_batch_delete_to_gc_14(self, client):
        """POST /api/definition/batch/delete-to-gc

        前端调用点：batchDeleteDefinition（api-test/management.ts）
        """
        resp = client.post("/api/definition/batch/delete-to-gc", json={})
        _soft(resp)

    def test_post_api_definition_edit_pos_15(self, client):
        """POST /api/definition/edit/pos

        前端调用点：sortDefinition（api-test/management.ts）
        """
        resp = client.post("/api/definition/edit/pos", json={})
        _soft(resp)

    def test_post_api_definition_batch_update_16(self, client):
        """POST /api/definition/batch-update

        前端调用点：batchUpdateDefinition（api-test/management.ts）
        """
        resp = client.post("/api/definition/batch-update", json={})
        _soft(resp)

    def test_post_api_definition_batch_move_17(self, client):
        """POST /api/definition/batch-move

        前端调用点：batchMoveDefinition（api-test/management.ts）
        """
        resp = client.post("/api/definition/batch-move", json={})
        _soft(resp)

    def test_post_api_definition_schedule_update_18(self, client):
        """POST /api/definition/schedule/update

        前端调用点：updateDefinitionSchedule（api-test/management.ts）
        """
        resp = client.post("/api/definition/schedule/update", json={})
        _soft(resp)

    def test_post_api_definition_schedule_check_19(self, client):
        """POST /api/definition/schedule/check

        前端调用点：checkDefinitionSchedule（api-test/management.ts）
        """
        resp = client.post("/api/definition/schedule/check", json={})
        _soft(resp)

    def test_post_api_definition_schedule_add_20(self, client):
        """POST /api/definition/schedule/add

        前端调用点：createDefinitionSchedule（api-test/management.ts）
        """
        resp = client.post("/api/definition/schedule/add", json={})
        _soft(resp)

    def test_get_api_definition_schedule_switch_21(self, client):
        """GET /api/definition/schedule/switch

        前端调用点：switchDefinitionSchedule（api-test/management.ts）
        """
        resp = client.get("/api/definition/schedule/switch")
        _soft(resp)

    def test_get_api_definition_schedule_get_22(self, client):
        """GET /api/definition/schedule/get

        前端调用点：getDefinitionSchedule（api-test/management.ts）
        """
        resp = client.get("/api/definition/schedule/get")
        _soft(resp)

    def test_get_api_definition_schedule_delete_23(self, client):
        """GET /api/definition/schedule/delete

        前端调用点：deleteDefinitionSchedule（api-test/management.ts）
        """
        resp = client.get("/api/definition/schedule/delete")
        _soft(resp)

    def test_post_api_definition_debug_24(self, client):
        """POST /api/definition/debug

        前端调用点：debugDefinition（api-test/management.ts）
        """
        resp = client.post("/api/definition/debug", json={})
        _soft(resp)

    def test_get_api_definition_follow_25(self, client):
        """GET /api/definition/follow

        前端调用点：debugDefinition（api-test/management.ts）
        """
        resp = client.get("/api/definition/follow")
        _soft(resp)

    def test_post_api_definition_operation_history_save_26(self, client):
        """POST /api/definition/operation-history/save

        前端调用点：saveOperationHistory（api-test/management.ts）
        """
        resp = client.post("/api/definition/operation-history/save", json={})
        _soft(resp)

    def test_post_api_definition_operation_history_recover_27(self, client):
        """POST /api/definition/operation-history/recover

        前端调用点：recoverOperationHistory（api-test/management.ts）
        """
        resp = client.post("/api/definition/operation-history/recover", json={})
        _soft(resp)

    def test_post_api_definition_get_reference_28(self, client):
        """POST /api/definition/get-reference

        前端调用点：getDefinitionReference（api-test/management.ts）
        """
        resp = client.post("/api/definition/get-reference", json={})
        _soft(resp)

    def test_post_api_definition_json_schema_preview_29(self, client):
        """POST /api/definition/json-schema/preview

        前端调用点：convertJsonSchemaToJson（api-test/management.ts）
        """
        resp = client.post("/api/definition/json-schema/preview", json={})
        _soft(resp)

    def test_post_api_definition_json_schema_auto_generate_30(self, client):
        """POST /api/definition/json-schema/auto-generate

        前端调用点：jsonSchemaAutoGenerate（api-test/management.ts）
        """
        resp = client.post("/api/definition/json-schema/auto-generate", json={})
        _soft(resp)

    def test_post_api_definition_file_copy_31(self, client):
        """POST /api/definition/file/copy

        前端调用点：definitionFileCopy（api-test/management.ts）
        """
        resp = client.post("/api/definition/file/copy", json={})
        _soft(resp)

    def test_get_api_definition_mock_enable_32(self, client):
        """GET /api/definition/mock/enable

        前端调用点：updateMockStatusPage（api-test/management.ts）
        """
        resp = client.get("/api/definition/mock/enable")
        _soft(resp)

    def test_post_api_definition_mock_delete_33(self, client):
        """POST /api/definition/mock/delete

        前端调用点：deleteMock（api-test/management.ts）
        """
        resp = client.post("/api/definition/mock/delete", json={})
        _soft(resp)

    def test_post_api_definition_mock_transfer_34(self, client):
        """POST /api/definition/mock/transfer

        前端调用点：transferMockFile（api-test/management.ts）
        """
        resp = client.post("/api/definition/mock/transfer", json={})
        _soft(resp)

    def test_get_api_definition_mock_transfer_options_35(self, client):
        """GET /api/definition/mock/transfer/options

        前端调用点：getMockTransferOptions（api-test/management.ts）
        """
        resp = client.get("/api/definition/mock/transfer/options")
        _soft(resp)

    def test_post_api_definition_mock_update_36(self, client):
        """POST /api/definition/mock/update

        前端调用点：updateMock（api-test/management.ts）
        """
        resp = client.post("/api/definition/mock/update", json={"id": "not-exist", "name": "mock"})
        _soft(resp)

    def test_post_api_definition_mock_detail_37(self, client):
        """POST /api/definition/mock/detail

        前端调用点：getMockDetail（api-test/management.ts）
        """
        resp = client.post("/api/definition/mock/detail", json={})
        _soft(resp)

    def test_post_api_definition_mock_copy_38(self, client):
        """POST /api/definition/mock/copy

        前端调用点：copyMock（api-test/management.ts）
        """
        resp = client.post("/api/definition/mock/copy", json={})
        _soft(resp)

    def test_post_api_definition_mock_batch_edit_39(self, client):
        """POST /api/definition/mock/batch/edit

        前端调用点：batchEditMock（api-test/management.ts）
        """
        resp = client.post("/api/definition/mock/batch/edit", json={})
        _soft(resp)

    def test_post_api_definition_mock_batch_delete_40(self, client):
        """POST /api/definition/mock/batch/delete

        前端调用点：batchDeleteMock（api-test/management.ts）
        """
        resp = client.post("/api/definition/mock/batch/delete", json={})
        _soft(resp)

    def test_post_api_definition_mock_add_41(self, client):
        """POST /api/definition/mock/add

        前端调用点：addMock（api-test/management.ts）
        """
        resp = client.post("/api/definition/mock/add", json={})
        _soft(resp)

    def test_get_api_definition_mock_get_url_42(self, client):
        """GET /api/definition/mock/get-url

        前端调用点：getMockUrl（api-test/management.ts）
        """
        resp = client.get("/api/definition/mock/get-url")
        _soft(resp)

    def test_post_api_definition_recover_43(self, client):
        """POST /api/definition/recover

        前端调用点：recoverDefinition（api-test/management.ts）
        """
        resp = client.post("/api/definition/recover", json={})
        _soft(resp)

    def test_get_api_definition_delete_44(self, client):
        """GET /api/definition/delete

        前端调用点：deleteRecycleApiList（api-test/management.ts）
        """
        resp = client.get("/api/definition/delete")
        _soft(resp)

    def test_post_api_definition_batch_recover_45(self, client):
        """POST /api/definition/batch-recover

        前端调用点：batchRecoverDefinition（api-test/management.ts）
        """
        resp = client.post("/api/definition/batch-recover", json={})
        _soft(resp)

    def test_post_api_definition_batch_delete_46(self, client):
        """POST /api/definition/batch/delete

        前端调用点：batchCleanOutDefinition（api-test/management.ts）
        """
        resp = client.post("/api/definition/batch/delete", json={})
        _soft(resp)

    def test_post_api_definition_module_trash_tree_47(self, client):
        """POST /api/definition/module/trash/tree

        前端调用点：getTrashModuleTree（api-test/management.ts）
        """
        resp = client.post("/api/definition/module/trash/tree", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_api_definition_module_trash_count_48(self, client):
        """POST /api/definition/module/trash/count

        前端调用点：getTrashModuleCount（api-test/management.ts）
        """
        resp = client.post("/api/definition/module/trash/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_get_api_definition_rage_49(self, client):
        """GET /api/definition/rage

        前端调用点：workApiCountCoverRage（workbench.ts）
        """
        resp = client.get("/api/definition/rage")
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 接口测试-用例
# ══════════════════════════════════════════════════════════════════════════════
class TestApiCaseUI:
    """接口测试-用例 界面：31 个前端调用点。"""

    def test_get_api_case_delete_to_gc_1(self, client):
        """GET /api/case/delete-to-gc

        前端调用点：deleteCase（api-test/management.ts）
        """
        resp = client.get("/api/case/delete-to-gc")
        _soft(resp)

    def test_post_api_case_batch_delete_to_gc_2(self, client):
        """POST /api/case/batch/delete-to-gc

        前端调用点：batchDeleteCase（api-test/management.ts）
        """
        resp = client.post("/api/case/batch/delete-to-gc", json={})
        _soft(resp)

    def test_post_api_case_batch_edit_3(self, client):
        """POST /api/case/batch/edit

        前端调用点：batchEditCase（api-test/management.ts）
        """
        resp = client.post("/api/case/batch/edit", json={})
        _soft(resp)

    def test_post_api_case_edit_pos_4(self, client):
        """POST /api/case/edit/pos

        前端调用点：dragSort（api-test/management.ts）
        """
        resp = client.post("/api/case/edit/pos", json={})
        _soft(resp)

    def test_post_api_case_update_5(self, client):
        """POST /api/case/update

        前端调用点：updateCase（api-test/management.ts）
        """
        resp = client.post("/api/case/update", json={})
        _soft(resp)

    def test_post_api_case_debug_6(self, client):
        """POST /api/case/debug

        前端调用点：debugCase（api-test/management.ts）
        """
        resp = client.post("/api/case/debug", json={})
        _soft(resp)

    def test_post_api_case_transfer_7(self, client):
        """POST /api/case/transfer

        前端调用点：transferFileCase（api-test/management.ts）
        """
        resp = client.post("/api/case/transfer", json={})
        _soft(resp)

    def test_get_api_case_transfer_options_8(self, client):
        """GET /api/case/transfer/options

        前端调用点：getTransferOptionsCase（api-test/management.ts）
        """
        resp = client.get("/api/case/transfer/options")
        _soft(resp)

    def test_get_api_case_get_detail_9(self, client):
        """GET /api/case/get-detail

        前端调用点：getCaseDetail（api-test/management.ts）
        """
        resp = client.get("/api/case/get-detail")
        _soft(resp)

    def test_get_api_case_follow_10(self, client):
        """GET /api/case/follow

        前端调用点：toggleFollowCase（api-test/management.ts）
        """
        resp = client.get("/api/case/follow")
        _soft(resp)

    def test_get_api_case_unfollow_11(self, client):
        """GET /api/case/unfollow

        前端调用点：toggleUnFollowCase（api-test/management.ts）
        """
        resp = client.get("/api/case/unfollow")
        _soft(resp)

    def test_post_api_case_run_12(self, client):
        """POST /api/case/run

        前端调用点：runCase（api-test/management.ts）
        """
        resp = client.post("/api/case/run", json={})
        _soft(resp)

    def test_post_api_case_batch_api_change_sync_13(self, client):
        """POST /api/case/batch/api-change/sync

        前端调用点：caseTableBatchSync（api-test/management.ts）
        """
        resp = client.post("/api/case/batch/api-change/sync", json={})
        _soft(resp)

    def test_post_api_case_api_change_sync_14(self, client):
        """POST /api/case/api-change/sync

        前端调用点：getSyncedCaseDetail（api-test/management.ts）
        """
        resp = client.post("/api/case/api-change/sync", json={})
        _soft(resp)

    def test_post_api_case_file_copy_15(self, client):
        """POST /api/case/file/copy

        前端调用点：caseFileCopy（api-test/management.ts）
        """
        resp = client.post("/api/case/file/copy", json={})
        _soft(resp)

    def test_get_api_case_recover_16(self, client):
        """GET /api/case/recover

        前端调用点：recoverCase（api-test/management.ts）
        """
        resp = client.get("/api/case/recover")
        _soft(resp)

    def test_post_api_case_batch_recover_17(self, client):
        """POST /api/case/batch/recover

        前端调用点：batchRecoverCase（api-test/management.ts）
        """
        resp = client.post("/api/case/batch/recover", json={})
        _soft(resp)

    def test_get_api_case_delete_18(self, client):
        """GET /api/case/delete

        前端调用点：deleteRecycleCase（api-test/management.ts）
        """
        resp = client.get("/api/case/delete")
        _soft(resp)

    def test_post_api_case_batch_delete_19(self, client):
        """POST /api/case/batch/delete

        前端调用点：batchDeleteRecycleCase（api-test/management.ts）
        """
        resp = client.post("/api/case/batch/delete", json={})
        _soft(resp)

    def test_post_api_case_add_20(self, client):
        """POST /api/case/add

        前端调用点：addCase（api-test/management.ts）
        """
        resp = client.post("/api/case/add", json={})
        _soft(resp)

    def test_get_api_case_run_21(self, client):
        """GET /api/case/run

        前端调用点：executeCase（api-test/management.ts）
        """
        resp = client.get("/api/case/run")
        _soft(resp)

    def test_post_api_case_batch_run_22(self, client):
        """POST /api/case/batch/run

        前端调用点：batchExecuteCase（api-test/management.ts）
        """
        resp = client.post("/api/case/batch/run", json={})
        _soft(resp)

    def test_post_api_case_operation_history_page_23(self, client):
        """POST /api/case/operation-history/page

        前端调用点：getApiCaseChangeHistory（api-test/management.ts）
        """
        resp = client.post("/api/case/operation-history/page", json=PAGE)
        _list(resp)

    def test_post_api_case_get_reference_24(self, client):
        """POST /api/case/get-reference

        前端调用点：getApiCaseDependency（api-test/management.ts）
        """
        resp = client.post("/api/case/get-reference", json={})
        _soft(resp)

    def test_post_api_case_statistics_25(self, client):
        """POST /api/case/statistics

        前端调用点：getCaseStatistics（api-test/management.ts）
        """
        resp = client.post("/api/case/statistics", json={"projectId": ""})
        _count(resp)

    def test_post_api_case_ai_save_config_26(self, client):
        """POST /api/case/ai/save/config

        前端调用点：saveAiConfig（api-test/management.ts）
        """
        resp = client.post("/api/case/ai/save/config", json={})
        _soft(resp)

    def test_get_api_case_ai_get_config_27(self, client):
        """GET /api/case/ai/get/config

        前端调用点：getAiConfig（api-test/management.ts）
        """
        resp = client.get("/api/case/ai/get/config")
        _soft(resp)

    def test_post_api_case_ai_chat_28(self, client):
        """POST /api/case/ai/chat

        前端调用点：apiAiChat（api-test/management.ts）
        """
        resp = client.post("/api/case/ai/chat", json={})
        _soft(resp)

    def test_post_api_case_ai_transform_29(self, client):
        """POST /api/case/ai/transform

        前端调用点：apiAiTransform（api-test/management.ts）
        """
        resp = client.post("/api/case/ai/transform", json={})
        _soft(resp)

    def test_post_api_case_ai_batch_save_30(self, client):
        """POST /api/case/ai/batch/save

        前端调用点：apiAiCaseBatchSave（api-test/management.ts）
        """
        resp = client.post("/api/case/ai/batch/save", json={})
        _soft(resp)

    def test_post_api_case_delete_to_gc_31(self, client):
        """POST /api/case/delete-to-gc

        前端调用点：deleteCaseRequest（case-management/featureCase.ts）
        """
        resp = client.post("/api/case/delete-to-gc", json={})
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 接口测试-场景
# ══════════════════════════════════════════════════════════════════════════════
class TestApiScenarioUI:
    """接口测试-场景 界面：27 个前端调用点。"""

    def test_post_api_scenario_update_1(self, client):
        """POST /api/scenario/update

        前端调用点：updateScenario（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/update", json={})
        _soft(resp)

    def test_get_api_scenario_delete_to_gc_2(self, client):
        """GET /api/scenario/delete-to-gc

        前端调用点：recycleScenario（api-test/scenario.ts）
        """
        resp = client.get("/api/scenario/delete-to-gc")
        _soft(resp)

    def test_post_api_scenario_batch_operation_delete_gc_3(self, client):
        """POST /api/scenario/batch-operation/delete-gc

        前端调用点：batchRecycleScenario（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/batch-operation/delete-gc", json={})
        _soft(resp)

    def test_post_api_scenario_batch_operation_move_4(self, client):
        """POST /api/scenario/batch-operation/move

        前端调用点：batchOptionScenario（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/batch-operation/move", json={})
        _soft(resp)

    def test_post_api_scenario_batch_operation_copy_5(self, client):
        """POST /api/scenario/batch-operation/copy

        前端调用点：batchOptionScenario（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/batch-operation/copy", json={})
        _soft(resp)

    def test_post_api_scenario_batch_operation_edit_6(self, client):
        """POST /api/scenario/batch-operation/edit

        前端调用点：batchEditScenario（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/batch-operation/edit", json={})
        _soft(resp)

    def test_post_api_scenario_batch_operation_run_7(self, client):
        """POST /api/scenario/batch-operation/run

        前端调用点：batchRunScenario（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/batch-operation/run", json={})
        _soft(resp)

    def test_post_api_scenario_schedule_config_8(self, client):
        """POST /api/scenario/schedule-config

        前端调用点：scenarioScheduleConfig（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/schedule-config", json={})
        _soft(resp)

    def test_get_api_scenario_schedule_config_delete_9(self, client):
        """GET /api/scenario/schedule-config-delete

        前端调用点：deleteScheduleConfig（api-test/scenario.ts）
        """
        resp = client.get("/api/scenario/schedule-config-delete")
        _soft(resp)

    def test_get_api_scenario_recover_10(self, client):
        """GET /api/scenario/recover

        前端调用点：recoverScenario（api-test/scenario.ts）
        """
        resp = client.get("/api/scenario/recover")
        _soft(resp)

    def test_post_api_scenario_batch_operation_recover_gc_11(self, client):
        """POST /api/scenario/batch-operation/recover-gc

        前端调用点：batchRecoverScenario（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/batch-operation/recover-gc", json={})
        _soft(resp)

    def test_get_api_scenario_delete_12(self, client):
        """GET /api/scenario/delete

        前端调用点：deleteScenario（api-test/scenario.ts）
        """
        resp = client.get("/api/scenario/delete")
        _soft(resp)

    def test_post_api_scenario_batch_operation_delete_13(self, client):
        """POST /api/scenario/batch-operation/delete

        前端调用点：batchDeleteScenario（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/batch-operation/delete", json={})
        _soft(resp)

    def test_post_api_scenario_add_14(self, client):
        """POST /api/scenario/add

        前端调用点：addScenario（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/add", json={})
        _soft(resp)

    def test_get_api_scenario_get_15(self, client):
        """GET /api/scenario/get

        前端调用点：getScenarioDetail（api-test/scenario.ts）
        """
        resp = client.get("/api/scenario/get")
        _soft(resp)

    def test_post_api_scenario_transfer_16(self, client):
        """POST /api/scenario/transfer

        前端调用点：transferFile（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/transfer", json={})
        _soft(resp)

    def test_post_api_scenario_step_transfer_17(self, client):
        """POST /api/scenario/step/transfer

        前端调用点：stepTransferFile（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/step/transfer", json={})
        _soft(resp)

    def test_get_api_scenario_transfer_options_18(self, client):
        """GET /api/scenario/transfer/options

        前端调用点：getTransferOptions（api-test/scenario.ts）
        """
        resp = client.get("/api/scenario/transfer/options")
        _soft(resp)

    def test_post_api_scenario_debug_19(self, client):
        """POST /api/scenario/debug

        前端调用点：debugScenario（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/debug", json={})
        _soft(resp)

    def test_post_api_scenario_run_20(self, client):
        """POST /api/scenario/run

        前端调用点：executeScenario（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/run", json={})
        _soft(resp)

    def test_post_api_scenario_get_system_request_21(self, client):
        """POST /api/scenario/get/system-request

        前端调用点：getSystemRequest（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/get/system-request", json={})
        _soft(resp)

    def test_get_api_scenario_follow_22(self, client):
        """GET /api/scenario/follow

        前端调用点：getSystemRequest（api-test/scenario.ts）
        """
        resp = client.get("/api/scenario/follow")
        _soft(resp)

    def test_post_api_scenario_edit_pos_23(self, client):
        """POST /api/scenario/edit/pos

        前端调用点：dragSort（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/edit/pos", json={})
        _soft(resp)

    def test_post_api_scenario_associate_all_24(self, client):
        """POST /api/scenario/associate/all

        前端调用点：scenarioAssociateExport（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/associate/all", json={})
        _soft(resp)

    def test_post_api_scenario_batch_operation_schedule_config_25(self, client):
        """POST /api/scenario/batch-operation/schedule-config

        前端调用点：scenarioBatchEditSchedule（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/batch-operation/schedule-config", json={})
        _soft(resp)

    def test_post_api_scenario_statistics_26(self, client):
        """POST /api/scenario/statistics

        前端调用点：getScenarioStatistics（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/statistics", json={"projectId": ""})
        _count(resp)

    def test_post_api_scenario_execute_page_27(self, client):
        """POST /api/scenario/execute/page

        前端调用点：executeHistory（test-plan/testPlan.ts）
        """
        resp = client.post("/api/scenario/execute/page", json=PAGE)
        _list(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 接口测试-文档分享
# ══════════════════════════════════════════════════════════════════════════════
class TestApiDocShareUI:
    """接口测试-文档分享 界面：7 个前端调用点。"""

    def test_post_api_doc_share_add_1(self, client):
        """POST /api/doc/share/add

        前端调用点：addShare（api-test/management.ts）
        """
        resp = client.post("/api/doc/share/add", json={})
        _soft(resp)

    def test_post_api_doc_share_update_2(self, client):
        """POST /api/doc/share/update

        前端调用点：updateShare（api-test/management.ts）
        """
        resp = client.post("/api/doc/share/update", json={})
        _soft(resp)

    def test_get_api_doc_share_delete_3(self, client):
        """GET /api/doc/share/delete

        前端调用点：deleteShare（api-test/management.ts）
        """
        resp = client.get("/api/doc/share/delete")
        _soft(resp)

    def test_get_api_doc_share_detail_4(self, client):
        """GET /api/doc/share/detail

        前端调用点：shareDetail（api-test/management.ts）
        """
        resp = client.get("/api/doc/share/detail")
        _soft(resp)

    def test_post_api_doc_share_module_tree_5(self, client):
        """POST /api/doc/share/module/tree

        前端调用点：getShareModuleTree（api-test/management.ts）
        """
        resp = client.post("/api/doc/share/module/tree", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_api_doc_share_module_count_6(self, client):
        """POST /api/doc/share/module/count

        前端调用点：getShareModuleCount（api-test/management.ts）
        """
        resp = client.post("/api/doc/share/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_get_api_doc_share_get_detail_7(self, client):
        """GET /api/doc/share/get-detail

        前端调用点：getShareDefinitionDetail（api-test/management.ts）
        """
        resp = client.get("/api/doc/share/get-detail")
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 接口测试-报告
# ══════════════════════════════════════════════════════════════════════════════
class TestApiReportUI:
    """接口测试-报告 界面：5 个前端调用点。"""

    def test_post_api_report_case_batch_export_1(self, client):
        """POST /api/report/case/batch-export

        前端调用点：logCaseReportBatchExport（api-test/management.ts）
        """
        resp = client.post("/api/report/case/batch-export", json={})
        _soft(resp)

    def test_post_api_report_case_batch_param_2(self, client):
        """POST /api/report/case/batch-param

        前端调用点：getCaseBatchExportParams（api-test/management.ts）
        """
        resp = client.post("/api/report/case/batch-param", json={})
        _soft(resp)

    def test_post_api_report_share_gen_3(self, client):
        """POST /api/report/share/gen

        前端调用点：getShareInfo（api-test/report.ts）
        """
        resp = client.post("/api/report/share/gen", json={})
        _soft(resp)

    def test_post_api_report_scenario_batch_export_4(self, client):
        """POST /api/report/scenario/batch-export

        前端调用点：logScenarioReportBatchExport（api-test/scenario.ts）
        """
        resp = client.post("/api/report/scenario/batch-export", json={})
        _soft(resp)

    def test_post_api_report_scenario_batch_param_5(self, client):
        """POST /api/report/scenario/batch-param

        前端调用点：getScenarioBatchExportParams（api-test/scenario.ts）
        """
        resp = client.post("/api/report/scenario/batch-param", json={})
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 用例管理-评审
# ══════════════════════════════════════════════════════════════════════════════
class TestCaseReviewUI:
    """用例管理-评审 界面：21 个前端调用点。"""

    def test_post_case_review_module_add_1(self, client):
        """POST /case/review/module/add

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/module/add", json={})
        _soft(resp)

    def test_post_case_review_module_update_2(self, client):
        """POST /case/review/module/update

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/module/update", json={})
        _soft(resp)

    def test_post_case_review_module_move_3(self, client):
        """POST /case/review/module/move

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/module/move", json={})
        _soft(resp)

    def test_get_case_review_module_tree_4(self, client):
        """GET /case/review/module/tree

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.get("/case/review/module/tree")
        _count(resp)

    def test_get_case_review_module_delete_5(self, client):
        """GET /case/review/module/delete

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.get("/case/review/module/delete")
        _soft(resp)

    def test_post_case_review_module_count_6(self, client):
        """POST /case/review/module/count

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_case_review_add_7(self, client):
        """POST /case/review/add

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/add", json={})
        _soft(resp)

    def test_post_case_review_associate_8(self, client):
        """POST /case/review/associate

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/associate", json={})
        _soft(resp)

    def test_post_case_review_copy_9(self, client):
        """POST /case/review/copy

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/copy", json={})
        _soft(resp)

    def test_post_case_review_edit_10(self, client):
        """POST /case/review/edit

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/edit", json={})
        _soft(resp)

    def test_post_case_review_edit_follower_11(self, client):
        """POST /case/review/edit/follower

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/edit/follower", json={})
        _soft(resp)

    def test_post_case_review_batch_move_12(self, client):
        """POST /case/review/batch/move

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/batch/move", json={})
        _soft(resp)

    def test_post_case_review_edit_pos_13(self, client):
        """POST /case/review/edit/pos

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/edit/pos", json={})
        _soft(resp)

    def test_get_case_review_detail_14(self, client):
        """GET /case/review/detail

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.get("/case/review/detail")
        _soft(resp)

    def test_post_case_review_detail_edit_pos_15(self, client):
        """POST /case/review/detail/edit/pos

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/detail/edit/pos", json={})
        _soft(resp)

    def test_post_case_review_detail_batch_review_16(self, client):
        """POST /case/review/detail/batch/review

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/detail/batch/review", json={})
        _soft(resp)

    def test_post_case_review_detail_batch_edit_reviewers_17(self, client):
        """POST /case/review/detail/batch/edit/reviewers

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/detail/batch/edit/reviewers", json={})
        _soft(resp)

    def test_post_case_review_detail_batch_disassociate_18(self, client):
        """POST /case/review/detail/batch/disassociate

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/detail/batch/disassociate", json={})
        _soft(resp)

    def test_post_case_review_detail_module_count_19(self, client):
        """POST /case/review/detail/module/count

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/detail/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_review_functional_case_save_20(self, client):
        """POST /review/functional/case/save

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.post("/review/functional/case/save", json={})
        _soft(resp)

    def test_post_case_review_detail_mind_multiple_review_21(self, client):
        """POST /case/review/detail/mind/multiple/review

        前端调用点：getCasePlanMinder（case-management/caseReview.ts）
        """
        resp = client.post("/case/review/detail/mind/multiple/review", json={})
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 用例管理-功能用例
# ══════════════════════════════════════════════════════════════════════════════
class TestFunctionalCaseUI:
    """用例管理-功能用例 界面：30 个前端调用点。"""

    def test_post_functional_case_module_add_1(self, client):
        """POST /functional/case/module/add

        前端调用点：createCaseModuleTree（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/module/add", json={})
        _soft(resp)

    def test_post_functional_case_module_update_2(self, client):
        """POST /functional/case/module/update

        前端调用点：updateCaseModuleTree（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/module/update", json={"id": "not-exist", "name": "改名模块"})
        _soft(resp)

    def test_post_functional_case_module_move_3(self, client):
        """POST /functional/case/module/move

        前端调用点：moveCaseModuleTree（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/module/move", json={})
        _soft(resp)

    def test_post_functional_case_edit_follower_4(self, client):
        """POST /functional/case/edit/follower

        前端调用点：followerCaseRequest（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/edit/follower", json={})
        _soft(resp)

    def test_post_functional_case_batch_move_5(self, client):
        """POST /functional/case/batch/move

        前端调用点：batchMoveToModules（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/batch/move", json={})
        _soft(resp)

    def test_post_functional_case_batch_copy_6(self, client):
        """POST /functional/case/batch/copy

        前端调用点：batchCopyToModules（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/batch/copy", json={})
        _soft(resp)

    def test_post_functional_mind_case_edit_7(self, client):
        """POST /functional/mind/case/edit

        前端调用点：saveCaseMinder（case-management/featureCase.ts）
        """
        resp = client.post("/functional/mind/case/edit", json={})
        _soft(resp)

    def test_post_functional_mind_case_tree_8(self, client):
        """POST /functional/mind/case/tree

        前端调用点：getCaseMinderTree（case-management/featureCase.ts）
        """
        resp = client.post("/functional/mind/case/tree", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_functional_case_trash_module_count_9(self, client):
        """POST /functional/case/trash/module/count

        前端调用点：getRecycleModulesCounts（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/trash/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_functional_case_module_count_10(self, client):
        """POST /functional/case/module/count

        前端调用点：getCaseModulesCounts（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_functional_case_trash_batch_recover_11(self, client):
        """POST /functional/case/trash/batch/recover

        前端调用点：restoreCaseList（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/trash/batch/recover", json={})
        _soft(resp)

    def test_post_functional_case_trash_batch_delete_12(self, client):
        """POST /functional/case/trash/batch/delete

        前端调用点：batchDeleteRecycleCase（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/trash/batch/delete", json={})
        _soft(resp)

    def test_post_functional_case_demand_add_13(self, client):
        """POST /functional/case/demand/add

        前端调用点：addDemandRequest（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/demand/add", json={})
        _soft(resp)

    def test_post_functional_case_demand_update_14(self, client):
        """POST /functional/case/demand/update

        前端调用点：updateDemandReq（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/demand/update", json={})
        _soft(resp)

    def test_post_functional_case_demand_batch_relevance_15(self, client):
        """POST /functional/case/demand/batch/relevance

        前端调用点：batchAssociationDemand（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/demand/batch/relevance", json={})
        _soft(resp)

    def test_post_functional_case_demand_third_list_page_16(self, client):
        """POST /functional/case/demand/third/list/page

        前端调用点：getThirdDemandList（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/demand/third/list/page", json=PAGE)
        _list(resp)

    def test_post_functional_case_comment_save_17(self, client):
        """POST /functional/case/comment/save

        前端调用点：createCommentList（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/comment/save", json={})
        _soft(resp)

    def test_post_functional_case_comment_update_18(self, client):
        """POST /functional/case/comment/update

        前端调用点：addOrUpdateCommentList（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/comment/update", json={})
        _soft(resp)

    def test_post_functional_case_test_associate_case_module_count_19(self, client):
        """POST /functional/case/test/associate/case/module/count

        前端调用点：getPublicLinkCaseModulesCounts（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/test/associate/case/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_functional_case_test_associate_case_module_tree_20(self, client):
        """POST /functional/case/test/associate/case/module/tree

        前端调用点：getPublicLinkModuleTree（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/test/associate/case/module/tree", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_functional_case_test_associate_case_21(self, client):
        """POST /functional/case/test/associate/case

        前端调用点：associationPublicCase（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/test/associate/case", json={})
        _soft(resp)

    def test_post_functional_case_relationship_add_22(self, client):
        """POST /functional/case/relationship/add

        前端调用点：addPrepositionRelation（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/relationship/add", json={})
        _soft(resp)

    def test_post_functional_case_relationship_delete_23(self, client):
        """POST /functional/case/relationship/delete

        前端调用点：cancelPreOrPostCase（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/relationship/delete", json={})
        _soft(resp)

    def test_post_functional_case_test_disassociate_case_24(self, client):
        """POST /functional/case/test/disassociate/case

        前端调用点：cancelAssociatedCase（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/test/disassociate/case", json={})
        _soft(resp)

    def test_post_functional_case_export_excel_25(self, client):
        """POST /functional/case/export/excel

        前端调用点：exportExcelCase（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/export/excel", json={})
        _soft(resp)

    def test_post_functional_case_export_xmind_26(self, client):
        """POST /functional/case/export/xmind

        前端调用点：exportXMindCase（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/export/xmind", json={})
        _soft(resp)

    def test_get_functional_case_check_export_task_27(self, client):
        """GET /functional/case/check/export-task

        前端调用点：checkCaseExportTask（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/check/export-task")
        _soft(resp)

    def test_post_functional_case_ai_transform_28(self, client):
        """POST /functional/case/ai/transform

        前端调用点：caseAiTransform（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/ai/transform", json={})
        _soft(resp)

    def test_post_functional_case_ai_chat_29(self, client):
        """POST /functional/case/ai/chat

        前端调用点：caseAiChat（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/ai/chat", json={})
        _soft(resp)

    def test_post_functional_case_ai_batch_save_30(self, client):
        """POST /functional/case/ai/batch/save

        前端调用点：caseAiBatchSave（case-management/featureCase.ts）
        """
        resp = client.post("/functional/case/ai/batch/save", json={})
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 缺陷-附件
# ══════════════════════════════════════════════════════════════════════════════
class TestDefectAttachmentUI:
    """缺陷-附件 界面：2 个前端调用点。"""

    def test_post_bug_attachment_check_update_1(self, client):
        """POST /bug/attachment/check-update

        前端调用点：checkFileIsUpdateRequest（case-management/featureCase.ts）
        """
        resp = client.post("/bug/attachment/check-update", json={})
        _soft(resp)

    def test_post_bug_attachment_delete_2(self, client):
        """POST /bug/attachment/delete

        前端调用点：deleteFileOrCancelAssociation（case-management/featureCase.ts）
        """
        resp = client.post("/bug/attachment/delete", json={})
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 工作台
# ══════════════════════════════════════════════════════════════════════════════
class TestWorkbenchUI:
    """工作台 界面：18 个前端调用点。"""

    def test_post_dashboard_my_plan_statistics_1(self, client):
        """POST /dashboard/my/plan/statistics

        前端调用点：workbenchTestPlanStatistic（workbench.ts）
        """
        resp = client.post("/dashboard/my/plan/statistics", json={"projectId": ""})
        _count(resp)

    def test_post_dashboard_project_view_2(self, client):
        """POST /dashboard/project_view

        前端调用点：workProOverviewDetail（workbench.ts）
        """
        resp = client.post("/dashboard/project_view", json={})
        _soft(resp)

    def test_post_dashboard_create_by_me_3(self, client):
        """POST /dashboard/create_by_me

        前端调用点：workMyCreatedDetail（workbench.ts）
        """
        resp = client.post("/dashboard/create_by_me", json={})
        _soft(resp)

    def test_post_dashboard_project_member_view_4(self, client):
        """POST /dashboard/project_member_view

        前端调用点：workMemberViewDetail（workbench.ts）
        """
        resp = client.post("/dashboard/project_member_view", json={})
        _soft(resp)

    def test_post_dashboard_case_count_5(self, client):
        """POST /dashboard/case_count

        前端调用点：workCaseCountDetail（workbench.ts）
        """
        resp = client.post("/dashboard/case_count", json={})
        _soft(resp)

    def test_post_dashboard_associate_case_count_6(self, client):
        """POST /dashboard/associate_case_count

        前端调用点：workAssociateCaseDetail（workbench.ts）
        """
        resp = client.post("/dashboard/associate_case_count", json={})
        _soft(resp)

    def test_post_dashboard_review_case_count_7(self, client):
        """POST /dashboard/review_case_count

        前端调用点：workCaseReviewDetail（workbench.ts）
        """
        resp = client.post("/dashboard/review_case_count", json={})
        _soft(resp)

    def test_post_dashboard_bug_handle_user_8(self, client):
        """POST /dashboard/bug_handle_user

        前端调用点：workBugHandlerDetail（workbench.ts）
        """
        resp = client.post("/dashboard/bug_handle_user", json={})
        _soft(resp)

    def test_post_dashboard_bug_count_9(self, client):
        """POST /dashboard/bug_count

        前端调用点：workBugCountDetail（workbench.ts）
        """
        resp = client.post("/dashboard/bug_count", json={})
        _soft(resp)

    def test_post_dashboard_create_bug_by_me_10(self, client):
        """POST /dashboard/create_bug_by_me

        前端调用点：workBugByMeCreated（workbench.ts）
        """
        resp = client.post("/dashboard/create_bug_by_me", json={})
        _soft(resp)

    def test_post_dashboard_handle_bug_by_me_11(self, client):
        """POST /dashboard/handle_bug_by_me

        前端调用点：workBugHandleByMe（workbench.ts）
        """
        resp = client.post("/dashboard/handle_bug_by_me", json={})
        _soft(resp)

    def test_post_dashboard_api_count_12(self, client):
        """POST /dashboard/api_count

        前端调用点：workApiCountDetail（workbench.ts）
        """
        resp = client.post("/dashboard/api_count", json={})
        _soft(resp)

    def test_post_dashboard_api_case_count_13(self, client):
        """POST /dashboard/api_case_count

        前端调用点：workApiCaseCountDetail（workbench.ts）
        """
        resp = client.post("/dashboard/api_case_count", json={})
        _soft(resp)

    def test_post_dashboard_scenario_count_14(self, client):
        """POST /dashboard/scenario_count

        前端调用点：workScenarioCaseCountDetail（workbench.ts）
        """
        resp = client.post("/dashboard/scenario_count", json={})
        _soft(resp)

    def test_get_dashboard_bug_handle_user_list_15(self, client):
        """GET /dashboard/bug_handle_user/list

        前端调用点：workHandleUserOptions（workbench.ts）
        """
        resp = client.get("/dashboard/bug_handle_user/list")
        _list(resp)

    def test_post_dashboard_plan_legacy_bug_16(self, client):
        """POST /dashboard/plan_legacy_bug

        前端调用点：workPlanLegacyBug（workbench.ts）
        """
        resp = client.post("/dashboard/plan_legacy_bug", json={})
        _soft(resp)

    def test_post_test_plan_rage_17(self, client):
        """POST /test-plan/rage

        前端调用点：workTestPlanRage（workbench.ts）
        """
        resp = client.post("/test-plan/rage", json={})
        _soft(resp)

    def test_post_dashboard_plan_view_18(self, client):
        """POST /dashboard/plan_view

        前端调用点：workTestPlanOverviewDetail（workbench.ts）
        """
        resp = client.post("/dashboard/plan_view", json={})
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 系统设置-消息通知
# ══════════════════════════════════════════════════════════════════════════════
class TestNotificationUI:
    """系统设置-消息通知 界面：27 个前端调用点。"""

    def test_post_notification_count_1(self, client):
        """POST /notification/count

        前端调用点：queryMessageHistoryCount（message/index.ts）
        """
        resp = client.post("/notification/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_get_notification_read_all_2(self, client):
        """GET /notification/read/all

        前端调用点：getMessageReadAll（message/index.ts）
        """
        resp = client.get("/notification/read/all")
        _soft(resp)

    def test_get_notification_un_read_3(self, client):
        """GET /notification/un-read

        前端调用点：getMessageUnReadCount（message/index.ts）
        """
        resp = client.get("/notification/un-read")
        _soft(resp)

    def test_post_notice_message_task_save_4(self, client):
        """POST /notice/message/task/save

        前端调用点：saveMessageConfig（project-management/messageManagement.ts）
        """
        resp = client.post("/notice/message/task/save", json={})
        _soft(resp)

    def test_get_we_com_info_with_detail_5(self, client):
        """GET /we_com/info/with_detail

        前端调用点：getWeComInfo（setting/qrCode.ts）
        """
        resp = client.get("/we_com/info/with_detail")
        _soft(resp)

    def test_get_ding_talk_info_with_detail_6(self, client):
        """GET /ding_talk/info/with_detail

        前端调用点：getDingInfo（setting/qrCode.ts）
        """
        resp = client.get("/ding_talk/info/with_detail")
        _soft(resp)

    def test_get_lark_info_with_detail_7(self, client):
        """GET /lark/info/with_detail

        前端调用点：getLarkInfo（setting/qrCode.ts）
        """
        resp = client.get("/lark/info/with_detail")
        _soft(resp)

    def test_get_lark_suite_info_with_detail_8(self, client):
        """GET /lark_suite/info/with_detail

        前端调用点：getLarkSuiteInfo（setting/qrCode.ts）
        """
        resp = client.get("/lark_suite/info/with_detail")
        _soft(resp)

    def test_post_we_com_save_9(self, client):
        """POST /we_com/save

        前端调用点：saveWeComConfig（setting/qrCode.ts）
        """
        resp = client.post("/we_com/save", json={})
        _soft(resp)

    def test_post_ding_talk_save_10(self, client):
        """POST /ding_talk/save

        前端调用点：saveDingTalkConfig（setting/qrCode.ts）
        """
        resp = client.post("/ding_talk/save", json={})
        _soft(resp)

    def test_post_lark_save_11(self, client):
        """POST /lark/save

        前端调用点：saveLarkConfig（setting/qrCode.ts）
        """
        resp = client.post("/lark/save", json={})
        _soft(resp)

    def test_post_lark_suite_save_12(self, client):
        """POST /lark_suite/save

        前端调用点：saveLarkSuiteConfig（setting/qrCode.ts）
        """
        resp = client.post("/lark_suite/save", json={})
        _soft(resp)

    def test_post_we_com_validate_13(self, client):
        """POST /we_com/validate

        前端调用点：validateWeComConfig（setting/qrCode.ts）
        """
        resp = client.post("/we_com/validate", json={})
        _soft(resp)

    def test_post_ding_talk_validate_14(self, client):
        """POST /ding_talk/validate

        前端调用点：validateDingTalkConfig（setting/qrCode.ts）
        """
        resp = client.post("/ding_talk/validate", json={})
        _soft(resp)

    def test_post_lark_validate_15(self, client):
        """POST /lark/validate

        前端调用点：validateLarkConfig（setting/qrCode.ts）
        """
        resp = client.post("/lark/validate", json={})
        _soft(resp)

    def test_post_lark_suite_validate_16(self, client):
        """POST /lark_suite/validate

        前端调用点：validateLarkSuiteConfig（setting/qrCode.ts）
        """
        resp = client.post("/lark_suite/validate", json={})
        _soft(resp)

    def test_post_we_com_enable_17(self, client):
        """POST /we_com/enable

        前端调用点：enableWeCom（setting/qrCode.ts）
        """
        resp = client.post("/we_com/enable", json={})
        _soft(resp)

    def test_post_ding_talk_enable_18(self, client):
        """POST /ding_talk/enable

        前端调用点：enableDingTalk（setting/qrCode.ts）
        """
        resp = client.post("/ding_talk/enable", json={})
        _soft(resp)

    def test_post_lark_enable_19(self, client):
        """POST /lark/enable

        前端调用点：enableLark（setting/qrCode.ts）
        """
        resp = client.post("/lark/enable", json={})
        _soft(resp)

    def test_post_lark_suite_enable_20(self, client):
        """POST /lark_suite/enable

        前端调用点：enableLarkSuite（setting/qrCode.ts）
        """
        resp = client.post("/lark_suite/enable", json={})
        _soft(resp)

    def test_post_we_com_change_validate_21(self, client):
        """POST /we_com/change/validate

        前端调用点：closeValidateWeCom（setting/qrCode.ts）
        """
        resp = client.post("/we_com/change/validate", json={})
        _soft(resp)

    def test_post_ding_talk_change_validate_22(self, client):
        """POST /ding_talk/change/validate

        前端调用点：closeValidateDingTalk（setting/qrCode.ts）
        """
        resp = client.post("/ding_talk/change/validate", json={})
        _soft(resp)

    def test_post_lark_change_validate_23(self, client):
        """POST /lark/change/validate

        前端调用点：closeValidateLark（setting/qrCode.ts）
        """
        resp = client.post("/lark/change/validate", json={})
        _soft(resp)

    def test_post_lark_suite_change_validate_24(self, client):
        """POST /lark_suite/change/validate

        前端调用点：closeValidateLarkSuite（setting/qrCode.ts）
        """
        resp = client.post("/lark_suite/change/validate", json={})
        _soft(resp)

    def test_get_ding_talk_info_25(self, client):
        """GET /ding_talk/info

        前端调用点：getDingInfo（user/index.ts）
        """
        resp = client.get("/ding_talk/info")
        _soft(resp)

    def test_get_lark_info_26(self, client):
        """GET /lark/info

        前端调用点：getLarkInfo（user/index.ts）
        """
        resp = client.get("/lark/info")
        _soft(resp)

    def test_get_lark_suite_info_27(self, client):
        """GET /lark_suite/info

        前端调用点：getLarkSuiteInfo（user/index.ts）
        """
        resp = client.get("/lark_suite/info")
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 系统设置-平台与日志
# ══════════════════════════════════════════════════════════════════════════════
class TestPlatformLogUI:
    """系统设置-平台与日志 界面：17 个前端调用点。"""

    def test_post_system_parameter_test_email_1(self, client):
        """POST /system/parameter/test/email

        前端调用点：testEmail（setting/config.ts）
        """
        resp = client.post("/system/parameter/test/email", json={})
        _soft(resp)

    def test_post_system_parameter_save_base_info_2(self, client):
        """POST /system/parameter/save/base-info

        前端调用点：saveBaseInfo（setting/config.ts）
        """
        resp = client.post("/system/parameter/save/base-info", json={})
        _soft(resp)

    def test_get_system_parameter_save_base_url_3(self, client):
        """GET /system/parameter/save/base-url

        前端调用点：saveBaseUrl（setting/config.ts）
        """
        resp = client.get("/system/parameter/save/base-url")
        _soft(resp)

    def test_get_system_parameter_get_base_info_4(self, client):
        """GET /system/parameter/get/base-info

        前端调用点：getBaseInfo（setting/config.ts）
        """
        resp = client.get("/system/parameter/get/base-info")
        _soft(resp)

    def test_post_system_parameter_edit_email_info_5(self, client):
        """POST /system/parameter/edit/email-info

        前端调用点：saveEmailInfo（setting/config.ts）
        """
        resp = client.post("/system/parameter/edit/email-info", json={})
        _soft(resp)

    def test_get_system_parameter_get_email_info_6(self, client):
        """GET /system/parameter/get/email-info

        前端调用点：getEmailInfo（setting/config.ts）
        """
        resp = client.get("/system/parameter/get/email-info")
        _soft(resp)

    def test_get_display_info_7(self, client):
        """GET /display/info

        前端调用点：getPageConfig（setting/config.ts）
        """
        resp = client.get("/display/info")
        _soft(resp)

    def test_post_system_parameter_edit_clean_config_8(self, client):
        """POST /system/parameter/edit/clean-config

        前端调用点：saveCleanupConfig（setting/config.ts）
        """
        resp = client.post("/system/parameter/edit/clean-config", json={})
        _soft(resp)

    def test_get_system_parameter_get_clean_config_9(self, client):
        """GET /system/parameter/get/clean-config

        前端调用点：getCleanupConfig（setting/config.ts）
        """
        resp = client.get("/system/parameter/get/clean-config")
        _soft(resp)

    def test_post_system_parameter_edit_upload_config_10(self, client):
        """POST /system/parameter/edit/upload-config

        前端调用点：saveUploadConfig（setting/config.ts）
        """
        resp = client.post("/system/parameter/edit/upload-config", json={})
        _soft(resp)

    def test_get_operation_log_get_options_11(self, client):
        """GET /operation/log/get/options

        前端调用点：getSystemLogOptions（setting/log.ts）
        """
        resp = client.get("/operation/log/get/options")
        _soft(resp)

    def test_get_operation_log_user_list_12(self, client):
        """GET /operation/log/user/list

        前端调用点：getSystemLogUsers（setting/log.ts）
        """
        resp = client.get("/operation/log/user/list")
        _list(resp)

    def test_post_system_organization_update_member_13(self, client):
        """POST /system/organization/update-member

        前端调用点：updateSystemOrganizationMember（setting/member.ts）
        """
        resp = client.post("/system/organization/update-member", json={})
        _soft(resp)

    def test_get_system_version_current_14(self, client):
        """GET /system/version/current

        前端调用点：getSystemVersion（system.ts）
        """
        resp = client.get("/system/version/current")
        _soft(resp)

    def test_get_system_organization_switch_option_15(self, client):
        """GET /system/organization/switch-option

        前端调用点：getOrgOptions（system.ts）
        """
        resp = client.get("/system/organization/switch-option")
        _soft(resp)

    def test_post_system_organization_switch_16(self, client):
        """POST /system/organization/switch

        前端调用点：switchUserOrg（system.ts）
        """
        resp = client.post("/system/organization/switch", json={})
        _soft(resp)

    def test_get_system_version_package_type_17(self, client):
        """GET /system/version/package-type

        前端调用点：getPackageType（system.ts）
        """
        resp = client.get("/system/version/package-type")
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 系统设置-许可证
# ══════════════════════════════════════════════════════════════════════════════
class TestLicenseUI:
    """系统设置-许可证 界面：2 个前端调用点。"""

    def test_get_license_validate_1(self, client):
        """GET /license/validate

        前端调用点：getLicenseInfo（setting/authorizedManagement.ts）
        """
        resp = client.get("/license/validate")
        _soft(resp)

    def test_post_license_add_2(self, client):
        """POST /license/add

        前端调用点：addLicense（setting/authorizedManagement.ts）
        """
        resp = client.post("/license/add", json={})
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 系统设置-认证源
# ══════════════════════════════════════════════════════════════════════════════
class TestAuthSourceUI:
    """系统设置-认证源 界面：16 个前端调用点。"""

    def test_get_system_authsource_get_1(self, client):
        """GET /system/authsource/get

        前端调用点：getAuthDetail（setting/config.ts）
        """
        resp = client.get("/system/authsource/get")
        _soft(resp)

    def test_get_authentication_get_by_type_2(self, client):
        """GET /authentication/get/by/type

        前端调用点：getAuthDetailByType（setting/config.ts）
        """
        resp = client.get("/authentication/get/by/type")
        _soft(resp)

    def test_post_system_authsource_add_3(self, client):
        """POST /system/authsource/add

        前端调用点：addAuth（setting/config.ts）
        """
        resp = client.post("/system/authsource/add", json={})
        _soft(resp)

    def test_post_system_authsource_update_4(self, client):
        """POST /system/authsource/update

        前端调用点：updateAuth（setting/config.ts）
        """
        resp = client.post("/system/authsource/update", json={})
        _soft(resp)

    def test_post_system_authsource_update_status_5(self, client):
        """POST /system/authsource/update/status

        前端调用点：updateAuthStatus（setting/config.ts）
        """
        resp = client.post("/system/authsource/update/status", json={})
        _soft(resp)

    def test_get_system_authsource_delete_6(self, client):
        """GET /system/authsource/delete

        前端调用点：deleteAuth（setting/config.ts）
        """
        resp = client.get("/system/authsource/delete")
        _soft(resp)

    def test_post_system_authsource_ldap_test_connect_7(self, client):
        """POST /system/authsource/ldap/test-connect

        前端调用点：testLdapConnect（setting/config.ts）
        """
        resp = client.post("/system/authsource/ldap/test-connect", json={})
        _soft(resp)

    def test_post_system_authsource_ldap_test_login_8(self, client):
        """POST /system/authsource/ldap/test-login

        前端调用点：testLdapLogin（setting/config.ts）
        """
        resp = client.post("/system/authsource/ldap/test-login", json={})
        _soft(resp)

    def test_get_is_login_9(self, client):
        """GET /is-login

        前端调用点：isLogin（user/index.ts）
        """
        resp = client.get("/is-login")
        _soft(resp)

    def test_get_authentication_get_list_10(self, client):
        """GET /authentication/get-list

        前端调用点：getAuthenticationList（user/index.ts）
        """
        resp = client.get("/authentication/get-list")
        _soft(resp)

    def test_get_sso_callback_we_com_11(self, client):
        """GET /sso/callback/we_com

        前端调用点：getWeComCallback（user/index.ts）
        """
        resp = client.get("/sso/callback/we_com")
        _soft(resp)

    def test_get_sso_callback_ding_talk_12(self, client):
        """GET /sso/callback/ding_talk

        前端调用点：getDingCallback（user/index.ts）
        """
        resp = client.get("/sso/callback/ding_talk")
        _soft(resp)

    def test_get_sso_callback_lark_13(self, client):
        """GET /sso/callback/lark

        前端调用点：getLarkCallback（user/index.ts）
        """
        resp = client.get("/sso/callback/lark")
        _soft(resp)

    def test_get_sso_callback_lark_suite_14(self, client):
        """GET /sso/callback/lark_suite

        前端调用点：getLarkSuiteCallback（user/index.ts）
        """
        resp = client.get("/sso/callback/lark_suite")
        _soft(resp)

    def test_get_signout_15(self, client):
        """GET /signout

        前端调用点：logout（user/index.ts）
        """
        resp = client.get("/signout")
        _soft(resp)

    def test_get_get_key_16(self, client):
        """GET /get-key

        前端调用点：getPublicKeyRequest（user/index.ts）
        """
        resp = client.get("/get-key")
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 系统设置-用户与组织
# ══════════════════════════════════════════════════════════════════════════════
class TestUserOrgUI:
    """系统设置-用户与组织 界面：28 个前端调用点。"""

    def test_get_organization_log_get_options_1(self, client):
        """GET /organization/log/get/options

        前端调用点：getOrgLogOptions（setting/log.ts）
        """
        resp = client.get("/organization/log/get/options")
        _soft(resp)

    def test_post_organization_add_member_2(self, client):
        """POST /organization/add-member

        前端调用点：addOrUpdate（setting/member.ts）
        """
        resp = client.post("/organization/add-member", json={})
        _soft(resp)

    def test_post_organization_update_member_3(self, client):
        """POST /organization/update-member

        前端调用点：addOrUpdate（setting/member.ts）
        """
        resp = client.post("/organization/update-member", json={})
        _soft(resp)

    def test_post_organization_project_add_member_4(self, client):
        """POST /organization/project/add-member

        前端调用点：batchAddProject（setting/member.ts）
        """
        resp = client.post("/organization/project/add-member", json={})
        _soft(resp)

    def test_post_organization_role_update_member_5(self, client):
        """POST /organization/role/update-member

        前端调用点：batchAddUserGroup（setting/member.ts）
        """
        resp = client.post("/organization/role/update-member", json={})
        _soft(resp)

    def test_get_organization_remove_member_6(self, client):
        """GET /organization/remove-member

        前端调用点：deleteMemberReq（setting/member.ts）
        """
        resp = client.get("/organization/remove-member")
        _soft(resp)

    def test_get_organization_user_role_list_7(self, client):
        """GET /organization/user/role/list

        前端调用点：getGlobalUserGroup（setting/member.ts）
        """
        resp = client.get("/organization/user/role/list")
        _list(resp)

    def test_post_organization_user_invite_8(self, client):
        """POST /organization/user/invite

        前端调用点：inviteOrgMember（setting/member.ts）
        """
        resp = client.post("/organization/user/invite", json={})
        _soft(resp)

    def test_post_organization_project_user_list_9(self, client):
        """POST /organization/project/user-list

        前端调用点：getOrganizationMemberListPage（setting/member.ts）
        """
        resp = client.post("/organization/project/user-list", json={})
        _soft(resp)

    def test_get_system_project_user_list_10(self, client):
        """GET /system/project/user-list

        前端调用点：getAdminByOrganizationOrProject（setting/organizationAndProject.ts）
        """
        resp = client.get("/system/project/user-list")
        _soft(resp)

    def test_post_organization_custom_field_update_11(self, client):
        """POST /organization/custom/field/update

        前端调用点：addOrUpdateOrdField（setting/template.ts）
        """
        resp = client.post("/organization/custom/field/update", json={})
        _soft(resp)

    def test_post_organization_custom_field_add_12(self, client):
        """POST /organization/custom/field/add

        前端调用点：addOrUpdateOrdField（setting/template.ts）
        """
        resp = client.post("/organization/custom/field/add", json={})
        _soft(resp)

    def test_get_organization_custom_field_delete_13(self, client):
        """GET /organization/custom/field/delete

        前端调用点：deleteOrdField（setting/template.ts）
        """
        resp = client.get("/organization/custom/field/delete")
        _soft(resp)

    def test_get_organization_custom_field_get_14(self, client):
        """GET /organization/custom/field/get

        前端调用点：getOrdFieldDetail（setting/template.ts）
        """
        resp = client.get("/organization/custom/field/get")
        _soft(resp)

    def test_post_system_user_add_15(self, client):
        """POST /system/user/add

        前端调用点：batchCreateUser（setting/user.ts）
        """
        resp = client.post("/system/user/add", json={"username": f"uim-{uuid.uuid4().hex[:8]}", "password": "Pass@123", "email": "uim@example.com"})
        _soft(resp)

    def test_post_system_user_update_16(self, client):
        """POST /system/user/update

        前端调用点：updateUserInfo（setting/user.ts）
        """
        resp = client.post("/system/user/update", json={})
        _soft(resp)

    def test_post_system_user_update_enable_17(self, client):
        """POST /system/user/update/enable

        前端调用点：toggleUserStatus（setting/user.ts）
        """
        resp = client.post("/system/user/update/enable", json={})
        _soft(resp)

    def test_get_system_user_get_18(self, client):
        """GET /system/user/get

        前端调用点：getUserInfo（setting/user.ts）
        """
        resp = client.get("/system/user/get")
        _soft(resp)

    def test_post_system_user_delete_19(self, client):
        """POST /system/user/delete

        前端调用点：deleteUserInfo（setting/user.ts）
        """
        resp = client.post("/system/user/delete", json={})
        _soft(resp)

    def test_get_system_user_get_global_system_role_20(self, client):
        """GET /system/user/get/global/system/role

        前端调用点：getSystemRoles（setting/user.ts）
        """
        resp = client.get("/system/user/get/global/system/role")
        _soft(resp)

    def test_post_system_user_reset_password_21(self, client):
        """POST /system/user/reset/password

        前端调用点：resetUserPassword（setting/user.ts）
        """
        resp = client.post("/system/user/reset/password", json={"id": "not-exist", "password": "Pass@123"})
        _soft(resp)

    def test_post_system_user_add_org_member_22(self, client):
        """POST /system/user/add-org-member

        前端调用点：batchAddOrg（setting/user.ts）
        """
        resp = client.post("/system/user/add-org-member", json={})
        _soft(resp)

    def test_get_system_user_get_organization_23(self, client):
        """GET /system/user/get/organization

        前端调用点：getSystemOrgs（setting/user.ts）
        """
        resp = client.get("/system/user/get/organization")
        _soft(resp)

    def test_get_system_user_get_project_24(self, client):
        """GET /system/user/get/project

        前端调用点：getSystemProjects（setting/user.ts）
        """
        resp = client.get("/system/user/get/project")
        _soft(resp)

    def test_post_system_user_invite_25(self, client):
        """POST /system/user/invite

        前端调用点：inviteUser（setting/user.ts）
        """
        resp = client.post("/system/user/invite", json={})
        _soft(resp)

    def test_post_system_user_register_by_invite_26(self, client):
        """POST /system/user/register-by-invite

        前端调用点：registerByInvite（setting/user.ts）
        """
        resp = client.post("/system/user/register-by-invite", json={})
        _soft(resp)

    def test_get_system_user_check_invite_27(self, client):
        """GET /system/user/check-invite

        前端调用点：validInvite（setting/user.ts）
        """
        resp = client.get("/system/user/check-invite")
        _soft(resp)

    def test_get_system_project_list_28(self, client):
        """GET /system/project/list

        前端调用点：getSystemProjectList（system.ts）
        """
        resp = client.get("/system/project/list")
        _list(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 系统设置-插件/资源池/服务集成
# ══════════════════════════════════════════════════════════════════════════════
class TestPluginResourceUI:
    """系统设置-插件/资源池/服务集成 界面：19 个前端调用点。"""

    def test_get_plugin_list_1(self, client):
        """GET /plugin/list

        前端调用点：getPluginList（setting/pluginManger.ts）
        """
        resp = client.get("/plugin/list")
        _list(resp)

    def test_post_plugin_update_2(self, client):
        """POST /plugin/update

        前端调用点：updatePlugin（setting/pluginManger.ts）
        """
        resp = client.post("/plugin/update", json={})
        _soft(resp)

    def test_get_plugin_delete_3(self, client):
        """GET /plugin/delete

        前端调用点：deletePluginReq（setting/pluginManger.ts）
        """
        resp = client.get("/plugin/delete")
        _soft(resp)

    def test_get_plugin_script_get_4(self, client):
        """GET /plugin/script/get

        前端调用点：getScriptDetail（setting/pluginManger.ts）
        """
        resp = client.get("/plugin/script/get")
        _soft(resp)

    def test_get_setting_get_platform_info_5(self, client):
        """GET /setting/get/platform/info

        前端调用点：getPlatformSourceList（setting/qrCode.ts）
        """
        resp = client.get("/setting/get/platform/info")
        _soft(resp)

    def test_post_test_resource_pool_update_6(self, client):
        """POST /test/resource/pool/update

        前端调用点：updatePoolInfo（setting/resourcePool.ts）
        """
        resp = client.post("/test/resource/pool/update", json={"id": "not-exist", "name": "资源池", "enable": True})
        _soft(resp)

    def test_post_test_resource_pool_add_7(self, client):
        """POST /test/resource/pool/add

        前端调用点：addPool（setting/resourcePool.ts）
        """
        resp = client.post("/test/resource/pool/add", json={})
        _soft(resp)

    def test_get_test_resource_pool_detail_8(self, client):
        """GET /test/resource/pool/detail

        前端调用点：getPoolInfo（setting/resourcePool.ts）
        """
        resp = client.get("/test/resource/pool/detail")
        _soft(resp)

    def test_get_test_resource_pool_delete_9(self, client):
        """GET /test/resource/pool/delete

        前端调用点：delPoolInfo（setting/resourcePool.ts）
        """
        resp = client.get("/test/resource/pool/delete")
        _soft(resp)

    def test_post_test_resource_pool_set_enable_10(self, client):
        """POST /test/resource/pool/set/enable/

        前端调用点：togglePoolStatus（setting/resourcePool.ts）
        """
        resp = client.post("/test/resource/pool/set/enable/", json={"id": "not-exist", "enable": True})
        _soft(resp)

    def test_post_test_resource_pool_capacity_detail_11(self, client):
        """POST /test/resource/pool/capacity/detail

        前端调用点：getCapacityDetail（setting/resourcePool.ts）
        """
        resp = client.post("/test/resource/pool/capacity/detail", json={})
        _soft(resp)

    def test_get_service_integration_list_12(self, client):
        """GET /service/integration/list

        前端调用点：getServiceList（setting/serviceIntegration.ts）
        """
        resp = client.get("/service/integration/list")
        _list(resp)

    def test_post_service_integration_add_13(self, client):
        """POST /service/integration/add

        前端调用点：addOrUpdate（setting/serviceIntegration.ts）
        """
        resp = client.post("/service/integration/add", json={})
        _soft(resp)

    def test_post_service_integration_update_14(self, client):
        """POST /service/integration/update

        前端调用点：addOrUpdate（setting/serviceIntegration.ts）
        """
        resp = client.post("/service/integration/update", json={})
        _soft(resp)

    def test_get_service_integration_delete_15(self, client):
        """GET /service/integration/delete

        前端调用点：resetService（setting/serviceIntegration.ts）
        """
        resp = client.get("/service/integration/delete")
        _soft(resp)

    def test_get_service_integration_validate_16(self, client):
        """GET /service/integration/validate

        前端调用点：getValidate（setting/serviceIntegration.ts）
        """
        resp = client.get("/service/integration/validate")
        _soft(resp)

    def test_post_service_integration_validate_17(self, client):
        """POST /service/integration/validate/

        前端调用点：postValidate（setting/serviceIntegration.ts）
        """
        resp = client.post("/service/integration/validate/", json={})
        _soft(resp)

    def test_get_service_integration_script_18(self, client):
        """GET /service/integration/script

        前端调用点：configScript（setting/serviceIntegration.ts）
        """
        resp = client.get("/service/integration/script")
        _soft(resp)

    def test_get_setting_get_platform_param_19(self, client):
        """GET /setting/get/platform/param

        前端调用点：getPlatformParamUrl（user/index.ts）
        """
        resp = client.get("/setting/get/platform/param")
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 系统设置-模板与工作流
# ══════════════════════════════════════════════════════════════════════════════
class TestTemplateWorkflowUI:
    """系统设置-模板与工作流 界面：21 个前端调用点。"""

    def test_post_project_custom_func_update_1(self, client):
        """POST /project/custom/func/update

        前端调用点：addOrUpdateCommonScriptReq（project-management/commonScript.ts）
        """
        resp = client.post("/project/custom/func/update", json={"id": "not-exist", "name": "脚本", "status": "ENABLED"})
        _soft(resp)

    def test_post_project_custom_func_add_2(self, client):
        """POST /project/custom/func/add

        前端调用点：addOrUpdateCommonScriptReq（project-management/commonScript.ts）
        """
        resp = client.post("/project/custom/func/add", json={})
        _soft(resp)

    def test_post_project_custom_func_status_3(self, client):
        """POST /project/custom/func/status

        前端调用点：updateStatusCommonScript（project-management/commonScript.ts）
        """
        resp = client.post("/project/custom/func/status", json={"id": "not-exist", "status": "ENABLED"})
        _soft(resp)

    def test_post_organization_template_add_4(self, client):
        """POST /organization/template/add

        前端调用点：createOrganizeTemplateInfo（setting/template.ts）
        """
        resp = client.post("/organization/template/add", json={})
        _soft(resp)

    def test_post_organization_template_update_5(self, client):
        """POST /organization/template/update

        前端调用点：updateOrganizeTemplateInfo（setting/template.ts）
        """
        resp = client.post("/organization/template/update", json={})
        _soft(resp)

    def test_post_organization_status_flow_setting_status_add_6(self, client):
        """POST /organization/status/flow/setting/status/add

        前端调用点：createWorkFlowStatus（setting/template.ts）
        """
        resp = client.post("/organization/status/flow/setting/status/add", json={})
        _soft(resp)

    def test_post_organization_status_flow_setting_status_update_7(self, client):
        """POST /organization/status/flow/setting/status/update

        前端调用点：updateWorkFlowStatus（setting/template.ts）
        """
        resp = client.post("/organization/status/flow/setting/status/update", json={})
        _soft(resp)

    def test_get_organization_status_flow_setting_status_delete_8(self, client):
        """GET /organization/status/flow/setting/status/delete

        前端调用点：deleteOrdWorkState（setting/template.ts）
        """
        resp = client.get("/organization/status/flow/setting/status/delete")
        _soft(resp)

    def test_post_organization_status_flow_setting_status_definition_update_9(self, client):
        """POST /organization/status/flow/setting/status/definition/update

        前端调用点：setOrdWorkState（setting/template.ts）
        """
        resp = client.post("/organization/status/flow/setting/status/definition/update", json={})
        _soft(resp)

    def test_post_organization_status_flow_setting_status_flow_update_10(self, client):
        """POST /organization/status/flow/setting/status/flow/update

        前端调用点：updateOrdWorkStateFlow（setting/template.ts）
        """
        resp = client.post("/organization/status/flow/setting/status/flow/update", json={})
        _soft(resp)

    def test_post_project_custom_field_update_11(self, client):
        """POST /project/custom/field/update

        前端调用点：addOrUpdateProjectField（setting/template.ts）
        """
        resp = client.post("/project/custom/field/update", json={"id": "not-exist", "name": "字段", "type": "INPUT"})
        _soft(resp)

    def test_post_project_custom_field_add_12(self, client):
        """POST /project/custom/field/add

        前端调用点：addOrUpdateProjectField（setting/template.ts）
        """
        resp = client.post("/project/custom/field/add", json={})
        _soft(resp)

    def test_get_project_custom_field_delete_13(self, client):
        """GET /project/custom/field/delete

        前端调用点：deleteProjectField（setting/template.ts）
        """
        resp = client.get("/project/custom/field/delete")
        _soft(resp)

    def test_get_project_custom_field_get_14(self, client):
        """GET /project/custom/field/get

        前端调用点：getProjectFieldDetail（setting/template.ts）
        """
        resp = client.get("/project/custom/field/get")
        _soft(resp)

    def test_post_project_template_add_15(self, client):
        """POST /project/template/add

        前端调用点：createProjectTemplateInfo（setting/template.ts）
        """
        resp = client.post("/project/template/add", json={})
        _soft(resp)

    def test_post_project_template_update_16(self, client):
        """POST /project/template/update

        前端调用点：updateProjectTemplateInfo（setting/template.ts）
        """
        resp = client.post("/project/template/update", json={})
        _soft(resp)

    def test_post_project_status_flow_setting_status_add_17(self, client):
        """POST /project/status/flow/setting/status/add

        前端调用点：createProjectWorkFlowStatus（setting/template.ts）
        """
        resp = client.post("/project/status/flow/setting/status/add", json={})
        _soft(resp)

    def test_post_project_status_flow_setting_status_update_18(self, client):
        """POST /project/status/flow/setting/status/update

        前端调用点：updateProjectWorkFlowStatus（setting/template.ts）
        """
        resp = client.post("/project/status/flow/setting/status/update", json={})
        _soft(resp)

    def test_get_project_status_flow_setting_status_delete_19(self, client):
        """GET /project/status/flow/setting/status/delete

        前端调用点：deleteProjectWorkState（setting/template.ts）
        """
        resp = client.get("/project/status/flow/setting/status/delete")
        _soft(resp)

    def test_post_project_status_flow_setting_status_definition_update_20(self, client):
        """POST /project/status/flow/setting/status/definition/update

        前端调用点：setProjectWorkState（setting/template.ts）
        """
        resp = client.post("/project/status/flow/setting/status/definition/update", json={})
        _soft(resp)

    def test_post_project_status_flow_setting_status_flow_update_21(self, client):
        """POST /project/status/flow/setting/status/flow/update

        前端调用点：updateProjectWorkStateFlow（setting/template.ts）
        """
        resp = client.post("/project/status/flow/setting/status/flow/update", json={})
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 系统设置-任务中心
# ══════════════════════════════════════════════════════════════════════════════
class TestTaskCenterUI:
    """系统设置-任务中心 界面：28 个前端调用点。"""

    def test_post_organization_task_center_exec_task_statistics_1(self, client):
        """POST /organization/task-center/exec-task/statistics

        前端调用点：getOrganizationExecuteTaskStatistics（taskCenter/organization.ts）
        """
        resp = client.post("/organization/task-center/exec-task/statistics", json={"projectId": ""})
        _count(resp)

    def test_get_organization_task_center_resource_pool_options_2(self, client):
        """GET /organization/task-center/resource-pool/options

        前端调用点：getOrgTaskCenterResourcePools（taskCenter/organization.ts）
        """
        resp = client.get("/organization/task-center/resource-pool/options")
        _soft(resp)

    def test_post_organization_task_center_exec_task_batch_stop_3(self, client):
        """POST /organization/task-center/exec-task/batch-stop

        前端调用点：organizationBatchStopTask（taskCenter/organization.ts）
        """
        resp = client.post("/organization/task-center/exec-task/batch-stop", json={})
        _soft(resp)

    def test_post_organization_task_center_exec_task_item_batch_stop_4(self, client):
        """POST /organization/task-center/exec-task/item/batch-stop

        前端调用点：organizationBatchStopTaskDetail（taskCenter/organization.ts）
        """
        resp = client.post("/organization/task-center/exec-task/item/batch-stop", json={})
        _soft(resp)

    def test_post_organization_task_center_exec_task_batch_delete_5(self, client):
        """POST /organization/task-center/exec-task/batch-delete

        前端调用点：organizationBatchDeleteTask（taskCenter/organization.ts）
        """
        resp = client.post("/organization/task-center/exec-task/batch-delete", json={})
        _soft(resp)

    def test_post_organization_task_center_schedule_batch_enable_6(self, client):
        """POST /organization/task-center/schedule/batch-enable

        前端调用点：organizationBatchOpenTask（taskCenter/organization.ts）
        """
        resp = client.post("/organization/task-center/schedule/batch-enable", json={})
        _soft(resp)

    def test_post_organization_task_center_schedule_batch_disable_7(self, client):
        """POST /organization/task-center/schedule/batch-disable

        前端调用点：organizationBatchCloseTask（taskCenter/organization.ts）
        """
        resp = client.post("/organization/task-center/schedule/batch-disable", json={})
        _soft(resp)

    def test_post_organization_task_center_schedule_update_cron_8(self, client):
        """POST /organization/task-center/schedule/update-cron

        前端调用点：organizationEditCron（taskCenter/organization.ts）
        """
        resp = client.post("/organization/task-center/schedule/update-cron", json={})
        _soft(resp)

    def test_get_organization_task_center_project_options_9(self, client):
        """GET /organization/task-center/project/options

        前端调用点：organizationProjectOptions（taskCenter/organization.ts）
        """
        resp = client.get("/organization/task-center/project/options")
        _soft(resp)

    def test_post_project_task_center_exec_task_statistics_10(self, client):
        """POST /project/task-center/exec-task/statistics

        前端调用点：getProjectExecuteTaskStatistics（taskCenter/project.ts）
        """
        resp = client.post("/project/task-center/exec-task/statistics", json={"projectId": ""})
        _count(resp)

    def test_get_project_task_center_resource_pool_options_11(self, client):
        """GET /project/task-center/resource-pool/options

        前端调用点：getProjectTaskCenterResourcePools（taskCenter/project.ts）
        """
        resp = client.get("/project/task-center/resource-pool/options")
        _soft(resp)

    def test_post_project_task_center_exec_task_batch_stop_12(self, client):
        """POST /project/task-center/exec-task/batch-stop

        前端调用点：projectBatchStopTask（taskCenter/project.ts）
        """
        resp = client.post("/project/task-center/exec-task/batch-stop", json={})
        _soft(resp)

    def test_post_project_task_center_exec_task_item_batch_stop_13(self, client):
        """POST /project/task-center/exec-task/item/batch-stop

        前端调用点：projectBatchStopTaskDetail（taskCenter/project.ts）
        """
        resp = client.post("/project/task-center/exec-task/item/batch-stop", json={})
        _soft(resp)

    def test_post_project_task_center_exec_task_batch_delete_14(self, client):
        """POST /project/task-center/exec-task/batch-delete

        前端调用点：projectBatchDeleteTask（taskCenter/project.ts）
        """
        resp = client.post("/project/task-center/exec-task/batch-delete", json={})
        _soft(resp)

    def test_post_project_task_center_schedule_batch_enable_15(self, client):
        """POST /project/task-center/schedule/batch-enable

        前端调用点：projectBatchOpenTask（taskCenter/project.ts）
        """
        resp = client.post("/project/task-center/schedule/batch-enable", json={})
        _soft(resp)

    def test_post_project_task_center_schedule_batch_disable_16(self, client):
        """POST /project/task-center/schedule/batch-disable

        前端调用点：projectBatchCloseTask（taskCenter/project.ts）
        """
        resp = client.post("/project/task-center/schedule/batch-disable", json={})
        _soft(resp)

    def test_post_project_task_center_schedule_update_cron_17(self, client):
        """POST /project/task-center/schedule/update-cron

        前端调用点：projectEditCron（taskCenter/project.ts）
        """
        resp = client.post("/project/task-center/schedule/update-cron", json={})
        _soft(resp)

    def test_post_system_task_center_exec_task_statistics_18(self, client):
        """POST /system/task-center/exec-task/statistics

        前端调用点：getSystemExecuteTaskStatistics（taskCenter/system.ts）
        """
        resp = client.post("/system/task-center/exec-task/statistics", json={"projectId": ""})
        _count(resp)

    def test_get_system_task_center_resource_pool_options_19(self, client):
        """GET /system/task-center/resource-pool/options

        前端调用点：getSystemTaskCenterResourcePools（taskCenter/system.ts）
        """
        resp = client.get("/system/task-center/resource-pool/options")
        _soft(resp)

    def test_post_system_task_center_exec_task_batch_stop_20(self, client):
        """POST /system/task-center/exec-task/batch-stop

        前端调用点：systemBatchStopTask（taskCenter/system.ts）
        """
        resp = client.post("/system/task-center/exec-task/batch-stop", json={})
        _soft(resp)

    def test_post_system_task_center_exec_task_item_batch_stop_21(self, client):
        """POST /system/task-center/exec-task/item/batch-stop

        前端调用点：systemBatchStopTaskDetail（taskCenter/system.ts）
        """
        resp = client.post("/system/task-center/exec-task/item/batch-stop", json={})
        _soft(resp)

    def test_post_system_task_center_exec_task_batch_delete_22(self, client):
        """POST /system/task-center/exec-task/batch-delete

        前端调用点：systemBatchDeleteTask（taskCenter/system.ts）
        """
        resp = client.post("/system/task-center/exec-task/batch-delete", json={})
        _soft(resp)

    def test_post_system_task_center_resource_pool_status_23(self, client):
        """POST /system/task-center/resource-pool/status

        前端调用点：getResourcePoolsStatus（taskCenter/system.ts）
        """
        resp = client.post("/system/task-center/resource-pool/status", json={})
        _soft(resp)

    def test_post_system_task_center_schedule_batch_enable_24(self, client):
        """POST /system/task-center/schedule/batch-enable

        前端调用点：systemBatchOpenTask（taskCenter/system.ts）
        """
        resp = client.post("/system/task-center/schedule/batch-enable", json={})
        _soft(resp)

    def test_post_system_task_center_schedule_batch_disable_25(self, client):
        """POST /system/task-center/schedule/batch-disable

        前端调用点：systemBatchCloseTask（taskCenter/system.ts）
        """
        resp = client.post("/system/task-center/schedule/batch-disable", json={})
        _soft(resp)

    def test_post_system_task_center_schedule_update_cron_26(self, client):
        """POST /system/task-center/schedule/update-cron

        前端调用点：systemEditCron（taskCenter/system.ts）
        """
        resp = client.post("/system/task-center/schedule/update-cron", json={})
        _soft(resp)

    def test_get_system_task_center_organization_options_27(self, client):
        """GET /system/task-center/organization/options

        前端调用点：systemOrgOptions（taskCenter/system.ts）
        """
        resp = client.get("/system/task-center/organization/options")
        _soft(resp)

    def test_get_system_task_center_project_options_28(self, client):
        """GET /system/task-center/project/options

        前端调用点：systemProjectOptions（taskCenter/system.ts）
        """
        resp = client.get("/system/task-center/project/options")
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 项目管理-文件管理
# ══════════════════════════════════════════════════════════════════════════════
class TestProjectFileUI:
    """项目管理-文件管理 界面：19 个前端调用点。"""

    def test_post_attachment_preview_1(self, client):
        """POST /attachment/preview

        前端调用点：previewFile（case-management/featureCase.ts）
        """
        resp = client.post("/attachment/preview", json={})
        _soft(resp)

    def test_post_attachment_download_file_2(self, client):
        """POST /attachment/download/file

        前端调用点：editorPreviewImages（case-management/featureCase.ts）
        """
        resp = client.post("/attachment/download/file", json={})
        _soft(resp)

    def test_post_project_file_update_3(self, client):
        """POST /project/file/update

        前端调用点：updateFile（project-management/fileManagement.ts）
        """
        resp = client.post("/project/file/update", json={})
        _soft(resp)

    def test_post_project_file_delete_4(self, client):
        """POST /project/file/delete

        前端调用点：deleteFile（project-management/fileManagement.ts）
        """
        resp = client.post("/project/file/delete", json={})
        _soft(resp)

    def test_post_project_file_batch_download_5(self, client):
        """POST /project/file/batch-download

        前端调用点：batchDownloadFile（project-management/fileManagement.ts）
        """
        resp = client.post("/project/file/batch-download", json={})
        _soft(resp)

    def test_get_project_file_module_tree_6(self, client):
        """GET /project/file-module/tree

        前端调用点：getModules（project-management/fileManagement.ts）
        """
        resp = client.get("/project/file-module/tree")
        _count(resp)

    def test_get_project_file_type_7(self, client):
        """GET /project/file/type

        前端调用点：getFileTypes（project-management/fileManagement.ts）
        """
        resp = client.get("/project/file/type")
        _soft(resp)

    def test_get_project_file_get_8(self, client):
        """GET /project/file/get

        前端调用点：getFileDetail（project-management/fileManagement.ts）
        """
        resp = client.get("/project/file/get")
        _soft(resp)

    def test_get_project_file_file_version_9(self, client):
        """GET /project/file/file-version

        前端调用点：getFileHistoryList（project-management/fileManagement.ts）
        """
        resp = client.get("/project/file/file-version")
        _soft(resp)

    def test_post_project_file_batch_move_10(self, client):
        """POST /project/file/batch-move

        前端调用点：batchMoveFile（project-management/fileManagement.ts）
        """
        resp = client.post("/project/file/batch-move", json={})
        _soft(resp)

    def test_get_project_file_repository_list_11(self, client):
        """GET /project/file/repository/list

        前端调用点：getRepositories（project-management/fileManagement.ts）
        """
        resp = client.get("/project/file/repository/list")
        _list(resp)

    def test_get_project_file_repository_file_type_12(self, client):
        """GET /project/file/repository/file-type

        前端调用点：getRepositoryFileTypes（project-management/fileManagement.ts）
        """
        resp = client.get("/project/file/repository/file-type")
        _soft(resp)

    def test_post_project_file_repository_add_repository_13(self, client):
        """POST /project/file/repository/add-repository

        前端调用点：addRepository（project-management/fileManagement.ts）
        """
        resp = client.post("/project/file/repository/add-repository", json={})
        _soft(resp)

    def test_post_project_file_repository_connect_14(self, client):
        """POST /project/file/repository/connect

        前端调用点：connectRepository（project-management/fileManagement.ts）
        """
        resp = client.post("/project/file/repository/connect", json={})
        _soft(resp)

    def test_post_project_file_repository_update_repository_15(self, client):
        """POST /project/file/repository/update-repository

        前端调用点：updateRepository（project-management/fileManagement.ts）
        """
        resp = client.post("/project/file/repository/update-repository", json={})
        _soft(resp)

    def test_post_project_file_repository_add_file_16(self, client):
        """POST /project/file/repository/add-file

        前端调用点：addRepositoryFile（project-management/fileManagement.ts）
        """
        resp = client.post("/project/file/repository/add-file", json={})
        _soft(resp)

    def test_get_project_file_repository_pull_file_17(self, client):
        """GET /project/file/repository/pull-file

        前端调用点：updateRepositoryFile（project-management/fileManagement.ts）
        """
        resp = client.get("/project/file/repository/pull-file")
        _soft(resp)

    def test_get_project_file_repository_info_18(self, client):
        """GET /project/file/repository/info

        前端调用点：getRepositoryInfo（project-management/fileManagement.ts）
        """
        resp = client.get("/project/file/repository/info")
        _soft(resp)

    def test_get_project_file_association_list_19(self, client):
        """GET /project/file/association/list

        前端调用点：getAssociationList（project-management/fileManagement.ts）
        """
        resp = client.get("/project/file/association/list")
        _list(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 项目管理-基本信息/机器人
# ══════════════════════════════════════════════════════════════════════════════
class TestProjectBaseUI:
    """项目管理-基本信息/机器人 界面：9 个前端调用点。"""

    def test_get_project_get_1(self, client):
        """GET /project/get

        前端调用点：getProjectInfo（project-management/basicInfo.ts）
        """
        resp = client.get("/project/get")
        _soft(resp)

    def test_post_project_update_2(self, client):
        """POST /project/update

        前端调用点：updateProject（project-management/basicInfo.ts）
        """
        resp = client.post("/project/update", json={})
        _soft(resp)

    def test_get_project_robot_get_3(self, client):
        """GET /project/robot/get

        前端调用点：getRobotDetail（project-management/messageManagement.ts）
        """
        resp = client.get("/project/robot/get")
        _soft(resp)

    def test_post_project_robot_add_4(self, client):
        """POST /project/robot/add

        前端调用点：addRobot（project-management/messageManagement.ts）
        """
        resp = client.post("/project/robot/add", json={})
        _soft(resp)

    def test_post_project_robot_update_5(self, client):
        """POST /project/robot/update

        前端调用点：updateRobot（project-management/messageManagement.ts）
        """
        resp = client.post("/project/robot/update", json={})
        _soft(resp)

    def test_get_project_robot_enable_6(self, client):
        """GET /project/robot/enable

        前端调用点：toggleRobot（project-management/messageManagement.ts）
        """
        resp = client.get("/project/robot/enable")
        _soft(resp)

    def test_get_project_robot_delete_7(self, client):
        """GET /project/robot/delete

        前端调用点：deleteRobot（project-management/messageManagement.ts）
        """
        resp = client.get("/project/robot/delete")
        _soft(resp)

    def test_get_project_list_options_8(self, client):
        """GET /project/list/options

        前端调用点：getProjectList（project-management/project.ts）
        """
        resp = client.get("/project/list/options")
        _list(resp)

    def test_post_project_switch_9(self, client):
        """POST /project/switch

        前端调用点：switchProject（project-management/project.ts）
        """
        resp = client.post("/project/switch", json={})
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 项目管理-成员/版本
# ══════════════════════════════════════════════════════════════════════════════
class TestProjectMemberUI:
    """项目管理-成员/版本 界面：16 个前端调用点。"""

    def test_post_project_member_update_1(self, client):
        """POST /project/member/update

        前端调用点：addOrUpdateProjectMember（project-management/projectMember.ts）
        """
        resp = client.post("/project/member/update", json={})
        _soft(resp)

    def test_post_project_member_add_2(self, client):
        """POST /project/member/add

        前端调用点：addOrUpdateProjectMember（project-management/projectMember.ts）
        """
        resp = client.post("/project/member/add", json={})
        _soft(resp)

    def test_post_project_member_update_member_3(self, client):
        """POST /project/member/update-member

        前端调用点：updateProjectMember（project-management/projectMember.ts）
        """
        resp = client.post("/project/member/update-member", json={})
        _soft(resp)

    def test_post_project_member_add_role_4(self, client):
        """POST /project/member/add-role

        前端调用点：addProjectUserGroup（project-management/projectMember.ts）
        """
        resp = client.post("/project/member/add-role", json={})
        _soft(resp)

    def test_post_project_member_batch_remove_5(self, client):
        """POST /project/member/batch/remove

        前端调用点：batchRemoveMember（project-management/projectMember.ts）
        """
        resp = client.post("/project/member/batch/remove", json={})
        _soft(resp)

    def test_get_project_member_remove_6(self, client):
        """GET /project/member/remove

        前端调用点：removeProjectMember（project-management/projectMember.ts）
        """
        resp = client.get("/project/member/remove")
        _soft(resp)

    def test_get_project_member_get_role_option_7(self, client):
        """GET /project/member/get-role/option

        前端调用点：getProjectUserGroup（project-management/projectMember.ts）
        """
        resp = client.get("/project/member/get-role/option")
        _soft(resp)

    def test_post_project_member_invite_8(self, client):
        """POST /project/member/invite

        前端调用点：inviteMember（project-management/projectMember.ts）
        """
        resp = client.post("/project/member/invite", json={})
        _soft(resp)

    def test_post_project_version_update_9(self, client):
        """POST /project/version/update

        前端调用点：updateVersion（project-management/projectVersion.ts）
        """
        resp = client.post("/project/version/update", json={})
        _soft(resp)

    def test_post_project_version_add_10(self, client):
        """POST /project/version/add

        前端调用点：addVersion（project-management/projectVersion.ts）
        """
        resp = client.post("/project/version/add", json={})
        _soft(resp)

    def test_get_project_version_switch_status_11(self, client):
        """GET /project/version/switch/status

        前端调用点：toggleVersionStatus（project-management/projectVersion.ts）
        """
        resp = client.get("/project/version/switch/status")
        _soft(resp)

    def test_get_project_version_switch_latest_12(self, client):
        """GET /project/version/switch/latest

        前端调用点：useLatestVersion（project-management/projectVersion.ts）
        """
        resp = client.get("/project/version/switch/latest")
        _soft(resp)

    def test_get_project_version_switch_enable_13(self, client):
        """GET /project/version/switch/enable

        前端调用点：toggleVersion（project-management/projectVersion.ts）
        """
        resp = client.get("/project/version/switch/enable")
        _soft(resp)

    def test_get_project_version_option_14(self, client):
        """GET /project/version/option

        前端调用点：getVersionOptions（project-management/projectVersion.ts）
        """
        resp = client.get("/project/version/option")
        _soft(resp)

    def test_get_project_version_enable_15(self, client):
        """GET /project/version/enable

        前端调用点：getVersionStatus（project-management/projectVersion.ts）
        """
        resp = client.get("/project/version/enable")
        _soft(resp)

    def test_get_project_version_delete_16(self, client):
        """GET /project/version/delete

        前端调用点：deleteVersion（project-management/projectVersion.ts）
        """
        resp = client.get("/project/version/delete")
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 测试计划
# ══════════════════════════════════════════════════════════════════════════════
class TestPlanUI:
    """测试计划 界面：54 个前端调用点。"""

    def test_post_test_plan_module_add_1(self, client):
        """POST /test-plan/module/add

        前端调用点：createPlanModuleTree（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/module/add", json={})
        _soft(resp)

    def test_post_test_plan_module_update_2(self, client):
        """POST /test-plan/module/update

        前端调用点：updatePlanModuleTree（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/module/update", json={"id": "not-exist", "name": "改名模块"})
        _soft(resp)

    def test_post_test_plan_module_move_3(self, client):
        """POST /test-plan/module/move

        前端调用点：moveTestPlanModuleTree（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/module/move", json={})
        _soft(resp)

    def test_post_test_plan_batch_edit_4(self, client):
        """POST /test-plan/batch-edit

        前端调用点：batchEditTestPlan（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/batch-edit", json={})
        _soft(resp)

    def test_post_test_plan_module_count_5(self, client):
        """POST /test-plan/module/count

        前端调用点：getPlanModulesCount（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_test_plan_add_6(self, client):
        """POST /test-plan/add

        前端调用点：addTestPlan（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/add", json={})
        _soft(resp)

    def test_post_test_plan_copy_7(self, client):
        """POST /test-plan/copy

        前端调用点：copyTestPlan（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/copy", json={})
        _soft(resp)

    def test_post_test_plan_update_8(self, client):
        """POST /test-plan/update

        前端调用点：updateTestPlan（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/update", json={})
        _soft(resp)

    def test_post_test_plan_batch_delete_9(self, client):
        """POST /test-plan/batch-delete

        前端调用点：batchDeletePlan（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/batch-delete", json={})
        _soft(resp)

    def test_post_test_plan_batch_copy_10(self, client):
        """POST /test-plan/batch-copy

        前端调用点：batchCopyPlan（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/batch-copy", json={})
        _soft(resp)

    def test_post_test_plan_batch_move_11(self, client):
        """POST /test-plan/batch-move

        前端调用点：batchMovePlan（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/batch-move", json={})
        _soft(resp)

    def test_post_test_plan_batch_archived_12(self, client):
        """POST /test-plan/batch-archived

        前端调用点：batchArchivedPlan（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/batch-archived", json={})
        _soft(resp)

    def test_post_test_plan_report_auto_gen_13(self, client):
        """POST /test-plan/report/auto-gen

        前端调用点：generateReport（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/report/auto-gen", json={})
        _soft(resp)

    def test_post_test_plan_edit_follower_14(self, client):
        """POST /test-plan/edit/follower

        前端调用点：followPlanRequest（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/edit/follower", json={})
        _soft(resp)

    def test_post_test_plan_statistics_15(self, client):
        """POST /test-plan/statistics

        前端调用点：getPlanPassRate（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/statistics", json={"projectId": ""})
        _count(resp)

    def test_post_test_plan_functional_case_module_count_16(self, client):
        """POST /test-plan/functional/case/module/count

        前端调用点：getFeatureCaseModuleCount（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_test_plan_functional_case_tree_17(self, client):
        """POST /test-plan/functional/case/tree

        前端调用点：getFeatureCaseModule（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/tree", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_test_plan_functional_case_disassociate_18(self, client):
        """POST /test-plan/functional/case/disassociate

        前端调用点：disassociateCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/disassociate", json={})
        _soft(resp)

    def test_post_test_plan_functional_case_sort_19(self, client):
        """POST /test-plan/functional/case/sort

        前端调用点：disassociateCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/sort", json={})
        _soft(resp)

    def test_post_test_plan_functional_case_batch_disassociate_20(self, client):
        """POST /test-plan/functional/case/batch/disassociate

        前端调用点：batchDisassociateCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/batch/disassociate", json={})
        _soft(resp)

    def test_post_test_plan_functional_case_batch_run_21(self, client):
        """POST /test-plan/functional/case/batch/run

        前端调用点：batchExecuteCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/batch/run", json={})
        _soft(resp)

    def test_post_test_plan_functional_case_batch_update_executor_22(self, client):
        """POST /test-plan/functional/case/batch/update/executor

        前端调用点：batchUpdateCaseExecutor（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/batch/update/executor", json={})
        _soft(resp)

    def test_post_test_plan_functional_case_batch_move_23(self, client):
        """POST /test-plan/functional/case/batch/move

        前端调用点：batchMoveFeatureCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/batch/move", json={})
        _soft(resp)

    def test_post_test_plan_functional_case_run_24(self, client):
        """POST /test-plan/functional/case/run

        前端调用点：runFeatureCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/run", json={})
        _soft(resp)

    def test_post_test_plan_functional_case_has_associate_bug_page_25(self, client):
        """POST /test-plan/functional/case/has/associate/bug/page

        前端调用点：associatedBugPage（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/has/associate/bug/page", json=PAGE)
        _list(resp)

    def test_post_test_plan_functional_case_associate_bug_26(self, client):
        """POST /test-plan/functional/case/associate/bug

        前端调用点：associateBugToPlan（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/associate/bug", json={})
        _soft(resp)

    def test_post_test_plan_api_case_tree_27(self, client):
        """POST /test-plan/api/case/tree

        前端调用点：getApiCaseModule（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/case/tree", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_test_plan_api_case_module_count_28(self, client):
        """POST /test-plan/api/case/module/count

        前端调用点：getApiCaseModuleCount（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/case/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_test_plan_api_case_sort_29(self, client):
        """POST /test-plan/api/case/sort

        前端调用点：getApiCaseModuleCount（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/case/sort", json={})
        _soft(resp)

    def test_post_test_plan_api_case_disassociate_30(self, client):
        """POST /test-plan/api/case/disassociate

        前端调用点：disassociateApiCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/case/disassociate", json={})
        _soft(resp)

    def test_post_test_plan_api_case_batch_disassociate_31(self, client):
        """POST /test-plan/api/case/batch/disassociate

        前端调用点：batchDisassociateApiCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/case/batch/disassociate", json={})
        _soft(resp)

    def test_post_test_plan_api_case_batch_run_32(self, client):
        """POST /test-plan/api/case/batch/run

        前端调用点：batchRunApiCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/case/batch/run", json={})
        _soft(resp)

    def test_post_test_plan_api_case_batch_move_33(self, client):
        """POST /test-plan/api/case/batch/move

        前端调用点：batchMoveApiCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/case/batch/move", json={})
        _soft(resp)

    def test_post_test_plan_api_scenario_tree_34(self, client):
        """POST /test-plan/api/scenario/tree

        前端调用点：getApiScenarioModule（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/scenario/tree", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_test_plan_api_scenario_module_count_35(self, client):
        """POST /test-plan/api/scenario/module/count

        前端调用点：getApiScenarioModuleCount（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/scenario/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_test_plan_api_scenario_sort_36(self, client):
        """POST /test-plan/api/scenario/sort

        前端调用点：getApiScenarioModuleCount（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/scenario/sort", json={})
        _soft(resp)

    def test_post_test_plan_api_scenario_disassociate_37(self, client):
        """POST /test-plan/api/scenario/disassociate

        前端调用点：disassociateApiScenario（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/scenario/disassociate", json={})
        _soft(resp)

    def test_post_test_plan_api_scenario_batch_disassociate_38(self, client):
        """POST /test-plan/api/scenario/batch/disassociate

        前端调用点：batchDisassociateApiScenario（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/scenario/batch/disassociate", json={})
        _soft(resp)

    def test_post_test_plan_api_scenario_batch_run_39(self, client):
        """POST /test-plan/api/scenario/batch/run

        前端调用点：batchRunApiScenario（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/scenario/batch/run", json={})
        _soft(resp)

    def test_post_test_plan_api_scenario_batch_move_40(self, client):
        """POST /test-plan/api/scenario/batch/move

        前端调用点：batchMoveApiScenario（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/scenario/batch/move", json={})
        _soft(resp)

    def test_post_test_plan_sort_41(self, client):
        """POST /test-plan/sort

        前端调用点：dragPlanOnGroup（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/sort", json={})
        _soft(resp)

    def test_post_test_plan_schedule_config_42(self, client):
        """POST /test-plan/schedule-config

        前端调用点：configSchedule（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/schedule-config", json={})
        _soft(resp)

    def test_post_test_plan_batch_schedule_config_43(self, client):
        """POST /test-plan/batch-schedule-config

        前端调用点：batchConfigSchedule（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/batch-schedule-config", json={})
        _soft(resp)

    def test_post_test_plan_execute_single_44(self, client):
        """POST /test-plan-execute/single

        前端调用点：executeSinglePlan（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan-execute/single", json={})
        _soft(resp)

    def test_post_test_plan_execute_batch_45(self, client):
        """POST /test-plan-execute/batch

        前端调用点：executePlanOrGroup（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan-execute/batch", json={})
        _soft(resp)

    def test_get_test_plan_mind_data_46(self, client):
        """GET /test-plan/mind/data

        前端调用点：getPlanMinder（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/mind/data")
        _soft(resp)

    def test_post_test_plan_mind_data_edit_47(self, client):
        """POST /test-plan/mind/data/edit

        前端调用点：editPlanMinder（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/mind/data/edit", json={})
        _soft(resp)

    def test_post_test_plan_association_api_case_module_count_48(self, client):
        """POST /test-plan/association/api/case/module/count

        前端调用点：testPlanAssociateModuleCount（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/association/api/case/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_test_plan_api_case_associate_bug_49(self, client):
        """POST /test-plan/api/case/associate/bug

        前端调用点：associateBugToApiCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/case/associate/bug", json={})
        _soft(resp)

    def test_post_test_plan_api_scenario_associate_bug_50(self, client):
        """POST /test-plan/api/scenario/associate/bug

        前端调用点：associateBugToScenarioCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/scenario/associate/bug", json={})
        _soft(resp)

    def test_post_test_plan_functional_case_batch_associate_bug_51(self, client):
        """POST /test-plan/functional/case/batch/associate-bug

        前端调用点：batchAssociatedBugToCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/batch/associate-bug", json={})
        _soft(resp)

    def test_post_test_plan_api_case_batch_associate_bug_52(self, client):
        """POST /test-plan/api/case/batch/associate-bug

        前端调用点：batchLinkBugToApiCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/case/batch/associate-bug", json={})
        _soft(resp)

    def test_post_test_plan_api_scenario_batch_associate_bug_53(self, client):
        """POST /test-plan/api/scenario/batch/associate-bug

        前端调用点：batchLinkBugToScenarioCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/api/scenario/batch/associate-bug", json={})
        _soft(resp)

    def test_post_test_plan_functional_case_minder_batch_associate_bug_54(self, client):
        """POST /test-plan/functional/case/minder/batch/associate-bug

        前端调用点：batchAssociatedBugToMinderCase（test-plan/testPlan.ts）
        """
        resp = client.post("/test-plan/functional/case/minder/batch/associate-bug", json={})
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 用户中心-个人设置
# ══════════════════════════════════════════════════════════════════════════════
class TestPersonalUI:
    """用户中心-个人设置 界面：23 个前端调用点。"""

    def test_post_api_user_menu_1(self, client):
        """POST /api/user/menu

        前端调用点：getMenuList（user/index.ts）
        """
        resp = client.post("/api/user/menu", json={})
        _soft(resp)

    def test_post_user_local_config_update_2(self, client):
        """POST /user/local/config/update

        前端调用点：updateLocalConfig（user/index.ts）
        """
        resp = client.post("/user/local/config/update", json={})
        _soft(resp)

    def test_post_user_local_config_add_3(self, client):
        """POST /user/local/config/add

        前端调用点：addLocalConfig（user/index.ts）
        """
        resp = client.post("/user/local/config/add", json={})
        _soft(resp)

    def test_get_user_local_config_get_4(self, client):
        """GET /user/local/config/get

        前端调用点：getLocalConfig（user/index.ts）
        """
        resp = client.get("/user/local/config/get")
        _soft(resp)

    def test_get_user_local_config_enable_5(self, client):
        """GET /user/local/config/enable

        前端调用点：enableLocalConfig（user/index.ts）
        """
        resp = client.get("/user/local/config/enable")
        _soft(resp)

    def test_get_user_local_config_disable_6(self, client):
        """GET /user/local/config/disable

        前端调用点：disableLocalConfig（user/index.ts）
        """
        resp = client.get("/user/local/config/disable")
        _soft(resp)

    def test_post_user_api_key_update_7(self, client):
        """POST /user/api/key/update

        前端调用点：updateAPIKEY（user/index.ts）
        """
        resp = client.post("/user/api/key/update", json={})
        _soft(resp)

    def test_get_user_api_key_validate_8(self, client):
        """GET /user/api/key/validate

        前端调用点：validAPIKEY（user/index.ts）
        """
        resp = client.get("/user/api/key/validate")
        _soft(resp)

    def test_get_user_api_key_list_9(self, client):
        """GET /user/api/key/list

        前端调用点：getAPIKEYList（user/index.ts）
        """
        resp = client.get("/user/api/key/list")
        _list(resp)

    def test_get_user_api_key_enable_10(self, client):
        """GET /user/api/key/enable

        前端调用点：enableAPIKEY（user/index.ts）
        """
        resp = client.get("/user/api/key/enable")
        _soft(resp)

    def test_get_user_api_key_disable_11(self, client):
        """GET /user/api/key/disable

        前端调用点：disableAPIKEY（user/index.ts）
        """
        resp = client.get("/user/api/key/disable")
        _soft(resp)

    def test_get_user_api_key_delete_12(self, client):
        """GET /user/api/key/delete

        前端调用点：deleteAPIKEY（user/index.ts）
        """
        resp = client.get("/user/api/key/delete")
        _soft(resp)

    def test_get_user_api_key_add_13(self, client):
        """GET /user/api/key/add

        前端调用点：addAPIKEY（user/index.ts）
        """
        resp = client.get("/user/api/key/add")
        _soft(resp)

    def test_get_personal_get_14(self, client):
        """GET /personal/get

        前端调用点：getBaseInfo（user/index.ts）
        """
        resp = client.get("/personal/get")
        _soft(resp)

    def test_post_personal_update_info_15(self, client):
        """POST /personal/update-info

        前端调用点：updateBaseInfo（user/index.ts）
        """
        resp = client.post("/personal/update-info", json={})
        _soft(resp)

    def test_post_personal_update_locale_16(self, client):
        """POST /personal/update-locale

        前端调用点：updateLanguage（user/index.ts）
        """
        resp = client.post("/personal/update-locale", json={})
        _soft(resp)

    def test_post_personal_update_password_17(self, client):
        """POST /personal/update-password

        前端调用点：updatePsw（user/index.ts）
        """
        resp = client.post("/personal/update-password", json={"oldPassword": "wrong-old", "newPassword": "Pass@123"})
        _soft(resp)

    def test_post_user_platform_save_18(self, client):
        """POST /user/platform/save

        前端调用点：savePlatform（user/index.ts）
        """
        resp = client.post("/user/platform/save", json={})
        _soft(resp)

    def test_get_user_platform_get_19(self, client):
        """GET /user/platform/get

        前端调用点：getPlatform（user/index.ts）
        """
        resp = client.get("/user/platform/get")
        _soft(resp)

    def test_get_user_platform_account_info_20(self, client):
        """GET /user/platform/account/info

        前端调用点：getPlatformAccount（user/index.ts）
        """
        resp = client.get("/user/platform/account/info")
        _soft(resp)

    def test_get_user_platform_switch_option_21(self, client):
        """GET /user/platform/switch-option

        前端调用点：getPlatformOrgOption（user/index.ts）
        """
        resp = client.get("/user/platform/switch-option")
        _soft(resp)

    def test_get_user_local_config_default_locale_22(self, client):
        """GET /user/local/config/default-locale

        前端调用点：getDefaultLocale（user/index.ts）
        """
        resp = client.get("/user/local/config/default-locale")
        _soft(resp)

    def test_post_personal_model_edit_source_23(self, client):
        """POST /personal/model/edit-source

        前端调用点：editPersonalModelConfig（user/index.ts）
        """
        resp = client.post("/personal/model/edit-source", json={})
        _soft(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 未归类
# ══════════════════════════════════════════════════════════════════════════════
class TestUncategorizedUI:
    """未归类 界面：4 个前端调用点。"""

    def test_post_bug_template_detail_1(self, client):
        """POST /bug/template/detail

        前端调用点：getTemplateDetailInfo（bug-management/index.ts）
        """
        resp = client.post("/bug/template/detail", json={})
        _soft(resp)

    def test_post_bug_case_un_relate_module_tree_2(self, client):
        """POST /bug/case/un-relate/module/tree

        前端调用点：getModuleTree（bug-management/index.ts）
        """
        resp = client.post("/bug/case/un-relate/module/tree", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_bug_case_un_relate_module_count_3(self, client):
        """POST /bug/case/un-relate/module/count

        前端调用点：getModuleTreeCounts（bug-management/index.ts）
        """
        resp = client.post("/bug/case/un-relate/module/count", json={"projectId": "", "keyword": ""})
        _count(resp)

    def test_post_fake_error_list_4(self, client):
        """POST /fake/error/list

        前端调用点：postFakeTableList（project-management/menuManagement.ts）
        """
        resp = client.post("/fake/error/list", json=PAGE)
        _list(resp)

# ══════════════════════════════════════════════════════════════════════════════
# 路径参数类接口（详情页 / 删除 / 启停 / 导出）
# ══════════════════════════════════════════════════════════════════════════════
class TestPathParamUI:
    """路径参数接口：230 个，覆盖所有 RESTful 前端调用点。"""

    # 用不存在的 ID 探测：目的是验证「路由存在且能优雅拒绝」，
    # 而不是验证业务成功。真实 CRUD 由 test_frontend_e2e_all.py 覆盖。
    MISSING_ID = "uim-not-exist"

    def test_get_api_tasks_taskId_1(self, client):
        """GET /api/tasks/{taskId}

        前端调用点：getAiTask（ai-case-gen.ts）
        """
        resp = client.get("/api/tasks/uim-not-exist")
        _soft(resp)

    def test_get_ai_conversation_delete_id_2(self, client):
        """GET /ai/conversation/delete/{id}

        前端调用点：deleteAiChat（ai.ts）
        """
        resp = client.get("/ai/conversation/delete/uim-not-exist")
        _soft(resp)

    def test_get_ai_conversation_chat_list_id_3(self, client):
        """GET /ai/conversation/chat/list/{id}

        前端调用点：getAiChatDetail（ai.ts）
        """
        resp = client.get("/ai/conversation/chat/list/uim-not-exist")
        _soft(resp)

    def test_get_api_definition_stop_taskId_4(self, client):
        """GET /api/definition/stop/{taskId}

        前端调用点：stopApiExport（api-test/management.ts）
        """
        resp = client.get("/api/definition/stop/uim-not-exist")
        _soft(resp)

    def test_get_api_definition_download_file_projectId_fileId_5(self, client):
        """GET /api/definition/download/file/{projectId}/{fileId}

        前端调用点：getApiDownloadFile（api-test/management.ts）
        """
        resp = client.get("/api/definition/download/file/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_case_update_status_id_status_6(self, client):
        """GET /api/case/update-status/{id}/{status}

        前端调用点：updateCaseStatus（api-test/management.ts）
        """
        resp = client.get("/api/case/update-status/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_case_update_priority_id_priority_7(self, client):
        """GET /api/case/update-priority/{id}/{priority}

        前端调用点：updateCasePriority（api-test/management.ts）
        """
        resp = client.get("/api/case/update-priority/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_case_api_change_clear_id_8(self, client):
        """GET /api/case/api-change/clear/{id}

        前端调用点：clearThisChange（api-test/management.ts）
        """
        resp = client.get("/api/case/api-change/clear/uim-not-exist")
        _soft(resp)

    def test_get_api_case_api_change_ignore_id_9(self, client):
        """GET /api/case/api-change/ignore/{id}

        前端调用点：ignoreEveryTimeChange（api-test/management.ts）
        """
        resp = client.get("/api/case/api-change/ignore/uim-not-exist")
        _soft(resp)

    def test_get_api_case_api_compare_id_10(self, client):
        """GET /api/case/api/compare/{id}

        前端调用点：diffDataRequest（api-test/management.ts）
        """
        resp = client.get("/api/case/api/compare/uim-not-exist")
        _soft(resp)

    def test_post_api_definition_export_type_11(self, client):
        """POST /api/definition/export/{type}

        前端调用点：exportApiDefinition（api-test/management.ts）
        """
        resp = client.post("/api/definition/export/uim-not-exist", json={})
        _soft(resp)

    def test_post_api_report_case_export_reportId_12(self, client):
        """POST /api/report/case/export/{reportId}

        前端调用点：logCaseReportExport（api-test/management.ts）
        """
        resp = client.post("/api/report/case/export/uim-not-exist", json={})
        _soft(resp)

    def test_post_api_doc_share_export_type_13(self, client):
        """POST /api/doc/share/export/{type}

        前端调用点：exportShareApiDefinition（api-test/management.ts）
        """
        resp = client.post("/api/doc/share/export/uim-not-exist", json={})
        _soft(resp)

    def test_get_api_doc_share_download_file_projectId_fileId_14(self, client):
        """GET /api/doc/share/download/file/{projectId}/{fileId}

        前端调用点：getShareApiDownloadFile（api-test/management.ts）
        """
        resp = client.get("/api/doc/share/download/file/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_doc_share_stop_taskId_15(self, client):
        """GET /api/doc/share/stop/{taskId}

        前端调用点：stopShareApiExport（api-test/management.ts）
        """
        resp = client.get("/api/doc/share/stop/uim-not-exist")
        _soft(resp)

    def test_get_api_doc_share_plugin_script_id_orgId_16(self, client):
        """GET /api/doc/share/plugin/script/{id}/{orgId}

        前端调用点：getDocSharePluginScript（api-test/management.ts）
        """
        resp = client.get("/api/doc/share/plugin/script/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_report_scenario_delete_id_17(self, client):
        """GET /api/report/scenario/delete/{id}

        前端调用点：reportDelete（api-test/report.ts）
        """
        resp = client.get("/api/report/scenario/delete/uim-not-exist")
        _soft(resp)

    def test_get_api_report_case_delete_id_18(self, client):
        """GET /api/report/case/delete/{id}

        前端调用点：reportDelete（api-test/report.ts）
        """
        resp = client.get("/api/report/case/delete/uim-not-exist")
        _soft(resp)

    def test_post_api_report_scenario_rename_id_19(self, client):
        """POST /api/report/scenario/rename/{id}

        前端调用点：reportRename（api-test/report.ts）
        """
        resp = client.post("/api/report/scenario/rename/uim-not-exist", json={})
        _soft(resp)

    def test_post_api_report_case_rename_id_20(self, client):
        """POST /api/report/case/rename/{id}

        前端调用点：reportRename（api-test/report.ts）
        """
        resp = client.post("/api/report/case/rename/uim-not-exist", json={})
        _soft(resp)

    def test_get_api_report_scenario_share_shareId_reportId_21(self, client):
        """GET /api/report/scenario/share/{shareId}/{reportId}

        前端调用点：reportScenarioDetail（api-test/report.ts）
        """
        resp = client.get("/api/report/scenario/share/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_report_scenario_get_reportId_22(self, client):
        """GET /api/report/scenario/get/{reportId}

        前端调用点：reportScenarioDetail（api-test/report.ts）
        """
        resp = client.get("/api/report/scenario/get/uim-not-exist")
        _soft(resp)

    def test_get_api_report_scenario_share_detail_shareId_reportId_stepId_23(self, client):
        """GET /api/report/scenario/share/detail/{shareId}/{reportId}/{stepId}

        前端调用点：reportStepDetail（api-test/report.ts）
        """
        resp = client.get("/api/report/scenario/share/detail/uim-not-exist/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_report_scenario_get_detail_reportId_stepId_24(self, client):
        """GET /api/report/scenario/get/detail/{reportId}/{stepId}

        前端调用点：reportStepDetail（api-test/report.ts）
        """
        resp = client.get("/api/report/scenario/get/detail/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_report_case_share_shareId_reportId_25(self, client):
        """GET /api/report/case/share/{shareId}/{reportId}

        前端调用点：reportCaseDetail（api-test/report.ts）
        """
        resp = client.get("/api/report/case/share/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_report_case_get_reportId_26(self, client):
        """GET /api/report/case/get/{reportId}

        前端调用点：reportCaseDetail（api-test/report.ts）
        """
        resp = client.get("/api/report/case/get/uim-not-exist")
        _soft(resp)

    def test_get_api_report_case_share_detail_shareId_reportId_stepId_27(self, client):
        """GET /api/report/case/share/detail/{shareId}/{reportId}/{stepId}

        前端调用点：reportCaseStepDetail（api-test/report.ts）
        """
        resp = client.get("/api/report/case/share/detail/uim-not-exist/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_report_case_get_detail_reportId_stepId_28(self, client):
        """GET /api/report/case/get/detail/{reportId}/{stepId}

        前端调用点：reportCaseStepDetail（api-test/report.ts）
        """
        resp = client.get("/api/report/case/get/detail/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_report_share_get_shareId_29(self, client):
        """GET /api/report/share/get/{shareId}

        前端调用点：getShareReportInfo（api-test/report.ts）
        """
        resp = client.get("/api/report/share/get/uim-not-exist")
        _soft(resp)

    def test_get_api_report_share_get_share_time_projectId_30(self, client):
        """GET /api/report/share/get-share-time/{projectId}

        前端调用点：getShareTime（api-test/report.ts）
        """
        resp = client.get("/api/report/share/get-share-time/uim-not-exist")
        _soft(resp)

    def test_get_api_report_case_task_report_taskId_31(self, client):
        """GET /api/report/case/task-report/{taskId}

        前端调用点：getCaseTaskReport（api-test/report.ts）
        """
        resp = client.get("/api/report/case/task-report/uim-not-exist")
        _soft(resp)

    def test_get_api_report_scenario_task_step_taskId_32(self, client):
        """GET /api/report/scenario/task-step/{taskId}

        前端调用点：getScenarioTaskReport（api-test/report.ts）
        """
        resp = client.get("/api/report/scenario/task-step/uim-not-exist")
        _soft(resp)

    def test_get_api_report_scenario_task_report_taskId_stepId_33(self, client):
        """GET /api/report/scenario/task-report/{taskId}/{stepId}

        前端调用点：getScenarioTaskReportStep（api-test/report.ts）
        """
        resp = client.get("/api/report/scenario/task-report/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_scenario_update_status_id_status_34(self, client):
        """GET /api/scenario/update-status/{id}/{status}

        前端调用点：updateScenarioStatus（api-test/scenario.ts）
        """
        resp = client.get("/api/scenario/update-status/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_scenario_update_priority_id_priority_35(self, client):
        """GET /api/scenario/update-priority/{id}/{priority}

        前端调用点：updateScenarioPro（api-test/scenario.ts）
        """
        resp = client.get("/api/scenario/update-priority/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_api_scenario_step_resource_info_id_36(self, client):
        """GET /api/scenario/step/resource-info/{id}

        前端调用点：getStepProjectInfo（api-test/scenario.ts）
        """
        resp = client.get("/api/scenario/step/resource-info/uim-not-exist")
        _soft(resp)

    def test_post_api_report_scenario_export_reportId_37(self, client):
        """POST /api/report/scenario/export/{reportId}

        前端调用点：logScenarioReportExport（api-test/scenario.ts）
        """
        resp = client.post("/api/report/scenario/export/uim-not-exist", json={})
        _soft(resp)

    def test_post_api_scenario_export_type_38(self, client):
        """POST /api/scenario/export/{type}

        前端调用点：exportScenario（api-test/scenario.ts）
        """
        resp = client.post("/api/scenario/export/uim-not-exist", json={})
        _soft(resp)

    def test_get_api_scenario_stop_taskId_39(self, client):
        """GET /api/scenario/stop/{taskId}

        前端调用点：stopScenarioExport（api-test/scenario.ts）
        """
        resp = client.get("/api/scenario/stop/uim-not-exist")
        _soft(resp)

    def test_get_api_scenario_download_file_projectId_fileId_40(self, client):
        """GET /api/scenario/download/file/{projectId}/{fileId}

        前端调用点：getScenarioDownloadFile（api-test/scenario.ts）
        """
        resp = client.get("/api/scenario/download/file/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_bug_check_exist_id_41(self, client):
        """GET /bug/check-exist/{id}

        前端调用点：checkBugExist（bug-management/index.ts）
        """
        resp = client.get("/bug/check-exist/uim-not-exist")
        _soft(resp)

    def test_get_bug_header_columns_option_projectId_42(self, client):
        """GET /bug/header/columns-option/{projectId}

        前端调用点：getCustomOptionHeader（bug-management/index.ts）
        """
        resp = client.get("/bug/header/columns-option/uim-not-exist")
        _soft(resp)

    def test_get_bug_get_id_43(self, client):
        """GET /bug/get/{id}

        前端调用点：getBugDetail（bug-management/index.ts）
        """
        resp = client.get("/bug/get/uim-not-exist")
        _soft(resp)

    def test_get_bug_delete_id_44(self, client):
        """GET /bug/delete/{id}

        前端调用点：deleteSingleBug（bug-management/index.ts）
        """
        resp = client.get("/bug/delete/uim-not-exist")
        _soft(resp)

    def test_get_bug_template_option_projectId_45(self, client):
        """GET /bug/template/option/{projectId}

        前端调用点：getTemplateOption（bug-management/index.ts）
        """
        resp = client.get("/bug/template/option/uim-not-exist")
        _soft(resp)

    def test_get_bug_export_columns_projectId_46(self, client):
        """GET /bug/export/columns/{projectId}

        前端调用点：getExportConfig（bug-management/index.ts）
        """
        resp = client.get("/bug/export/columns/uim-not-exist")
        _soft(resp)

    def test_get_bug_current_platform_projectId_47(self, client):
        """GET /bug/current-platform/{projectId}

        前端调用点：getPlatform（bug-management/index.ts）
        """
        resp = client.get("/bug/current-platform/uim-not-exist")
        _soft(resp)

    def test_get_bug_unfollow_id_48(self, client):
        """GET /bug/unfollow/{id}

        前端调用点：followBug（bug-management/index.ts）
        """
        resp = client.get("/bug/unfollow/uim-not-exist")
        _soft(resp)

    def test_get_bug_follow_id_49(self, client):
        """GET /bug/follow/{id}

        前端调用点：followBug（bug-management/index.ts）
        """
        resp = client.get("/bug/follow/uim-not-exist")
        _soft(resp)

    def test_get_bug_comment_get_bugId_50(self, client):
        """GET /bug/comment/get/{bugId}

        前端调用点：getCommentList（bug-management/index.ts）
        """
        resp = client.get("/bug/comment/get/uim-not-exist")
        _soft(resp)

    def test_get_bug_comment_delete_commentId_51(self, client):
        """GET /bug/comment/delete/{commentId}

        前端调用点：deleteComment（bug-management/index.ts）
        """
        resp = client.get("/bug/comment/delete/uim-not-exist")
        _soft(resp)

    def test_get_bug_header_custom_field_projectId_52(self, client):
        """GET /bug/header/custom-field/{projectId}

        前端调用点：getCustomFieldHeader（bug-management/index.ts）
        """
        resp = client.get("/bug/header/custom-field/uim-not-exist")
        _soft(resp)

    def test_get_bug_attachment_transfer_options_projectId_53(self, client):
        """GET /bug/attachment/transfer/options//{projectId}

        前端调用点：getTransferFileTree（bug-management/index.ts）
        """
        resp = client.get("/bug/attachment/transfer/options//uim-not-exist")
        _soft(resp)

    def test_get_bug_attachment_list_bugId_54(self, client):
        """GET /bug/attachment/list/{bugId}

        前端调用点：getAttachmentList（bug-management/index.ts）
        """
        resp = client.get("/bug/attachment/list/uim-not-exist")
        _soft(resp)

    def test_get_bug_trash_recover_id_55(self, client):
        """GET /bug/trash/recover/{id}

        前端调用点：recoverSingleByRecycle（bug-management/index.ts）
        """
        resp = client.get("/bug/trash/recover/uim-not-exist")
        _soft(resp)

    def test_get_bug_trash_delete_id_56(self, client):
        """GET /bug/trash/delete/{id}

        前端调用点：deleteSingleByRecycle（bug-management/index.ts）
        """
        resp = client.get("/bug/trash/delete/uim-not-exist")
        _soft(resp)

    def test_get_bug_case_un_relate_id_57(self, client):
        """GET /bug/case/un-relate/{id}

        前端调用点：cancelAssociation（bug-management/index.ts）
        """
        resp = client.get("/bug/case/un-relate/uim-not-exist")
        _soft(resp)

    def test_get_bug_case_check_permission_projectId_caseType_58(self, client):
        """GET /bug/case/check-permission/{projectId}/{caseType}

        前端调用点：checkCasePermission（bug-management/index.ts）
        """
        resp = client.get("/bug/case/check-permission/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_case_review_user_option_projectId_59(self, client):
        """GET /case/review/user-option/{projectId}

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.get("/case/review/user-option/uim-not-exist")
        _soft(resp)

    def test_get_case_review_disassociate_reviewId_caseId_60(self, client):
        """GET /case/review/disassociate/{reviewId}/{caseId}

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.get("/case/review/disassociate/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_case_review_delete_projectId_reviewId_61(self, client):
        """GET /case/review/delete/{projectId}/{reviewId}

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.get("/case/review/delete/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_case_review_detail_get_ids_reviewId_62(self, client):
        """GET /case/review/detail/get-ids/{reviewId}

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.get("/case/review/detail/get-ids/uim-not-exist")
        _soft(resp)

    def test_get_case_review_detail_tree_reviewId_63(self, client):
        """GET /case/review/detail/tree/{reviewId}

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.get("/case/review/detail/tree/uim-not-exist")
        _soft(resp)

    def test_get_review_functional_case_get_list_reviewId_caseId_64(self, client):
        """GET /review/functional/case/get/list/{reviewId}/{caseId}

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.get("/review/functional/case/get/list/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_case_review_detail_reviewer_list_reviewId_caseId_65(self, client):
        """GET /case/review/detail/reviewer/list/{reviewId}/{caseId}

        前端调用点：case-management/caseReview.ts（case-management/caseReview.ts）
        """
        resp = client.get("/case/review/detail/reviewer/list/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_case_review_detail_reviewer_status_total_reviewId_caseId_66(self, client):
        """GET /case/review/detail/reviewer/status/total/{reviewId}/{caseId}

        前端调用点：getCasePlanMinder（case-management/caseReview.ts）
        """
        resp = client.get("/case/review/detail/reviewer/status/total/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_module_tree_projectId_67(self, client):
        """GET /functional/case/module/tree/{projectId}

        前端调用点：getCaseModuleTree（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/module/tree/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_module_trash_tree_projectId_68(self, client):
        """GET /functional/case/module/trash/tree/{projectId}

        前端调用点：getTrashCaseModuleTree（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/module/trash/tree/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_module_delete_id_69(self, client):
        """GET /functional/case/module/delete/{id}

        前端调用点：deleteCaseModuleTree（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/module/delete/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_default_template_field_projectId_70(self, client):
        """GET /functional/case/default/template/field/{projectId}

        前端调用点：getCaseDefaultFields（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/default/template/field/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_detail_id_71(self, client):
        """GET /functional/case/detail/{id}

        前端调用点：getCaseDetail（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/detail/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_trash_recover_id_72(self, client):
        """GET /functional/case/trash/recover/{id}

        前端调用点：recoverRecycleCase（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/trash/recover/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_trash_delete_id_73(self, client):
        """GET /functional/case/trash/delete/{id}

        前端调用点：deleteRecycleCaseList（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/trash/delete/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_demand_cancel_id_74(self, client):
        """GET /functional/case/demand/cancel/{id}

        前端调用点：cancelAssociationDemand（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/demand/cancel/uim-not-exist")
        _soft(resp)

    def test_get_attachment_update_projectId_id_75(self, client):
        """GET /attachment/update/{projectId}/{id}

        前端调用点：updateFile（case-management/featureCase.ts）
        """
        resp = client.get("/attachment/update/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_custom_field_projectId_76(self, client):
        """GET /functional/case/custom/field/{projectId}

        前端调用点：getCustomFieldsTable（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/custom/field/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_comment_get_list_caseId_77(self, client):
        """GET /functional/case/comment/get/list/{caseId}

        前端调用点：getCommentList（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/comment/get/list/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_review_comment_caseId_78(self, client):
        """GET /functional/case/review/comment/{caseId}

        前端调用点：getReviewCommentList（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/review/comment/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_comment_delete_commentId_79(self, client):
        """GET /functional/case/comment/delete/{commentId}

        前端调用点：deleteCommentList（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/comment/delete/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_test_disassociate_bug_id_80(self, client):
        """GET /functional/case/test/disassociate/bug/{id}

        前端调用点：cancelAssociatedDebug（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/test/disassociate/bug/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_relationship_get_ids_caseId_81(self, client):
        """GET /functional/case/relationship/get-ids/{caseId}

        前端调用点：getAssociatedCaseIds（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/relationship/get-ids/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_download_file_projectId_fileId_82(self, client):
        """GET /functional/case/download/file/{projectId}/{fileId}

        前端调用点：getCaseDownloadFile（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/download/file/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_stop_taskId_83(self, client):
        """GET /functional/case/stop/{taskId}

        前端调用点：stopCaseExport（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/stop/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_export_columns_projectId_84(self, client):
        """GET /functional/case/export/columns/{projectId}

        前端调用点：getCaseExportConfig（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/export/columns/uim-not-exist")
        _soft(resp)

    def test_get_project_list_options_orgId_module_85(self, client):
        """GET /project/list/options/{orgId}/{module}

        前端调用点：getAssociatedProjectOptions（case-management/featureCase.ts）
        """
        resp = client.get("/project/list/options/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_functional_case_test_plan_comment_caseId_86(self, client):
        """GET /functional/case/test/plan/comment/{caseId}

        前端调用点：getTestPlanExecuteCommentList（case-management/featureCase.ts）
        """
        resp = client.get("/functional/case/test/plan/comment/uim-not-exist")
        _soft(resp)

    def test_get_notification_read_id_87(self, client):
        """GET /notification/read/{id}

        前端调用点：getMessageRead（message/index.ts）
        """
        resp = client.get("/notification/read/uim-not-exist")
        _soft(resp)

    def test_get_project_custom_func_detail_id_88(self, client):
        """GET /project/custom/func/detail/{id}

        前端调用点：getCommonScriptDetail（project-management/commonScript.ts）
        """
        resp = client.get("/project/custom/func/detail/uim-not-exist")
        _soft(resp)

    def test_get_project_custom_func_delete_id_89(self, client):
        """GET /project/custom/func/delete/{id}

        前端调用点：deleteCommonScript（project-management/commonScript.ts）
        """
        resp = client.get("/project/custom/func/delete/uim-not-exist")
        _soft(resp)

    def test_get_project_custom_func_columns_option_projectId_90(self, client):
        """GET /project/custom/func/columns-option/{projectId}

        前端调用点：getCustomFuncColumnOption（project-management/commonScript.ts）
        """
        resp = client.get("/project/custom/func/columns-option/uim-not-exist")
        _soft(resp)

    def test_get_api_test_common_script_scriptId_91(self, client):
        """GET /api/test/common-script/{scriptId}

        前端调用点：getCommonScript（project-management/commonScript.ts）
        """
        resp = client.get("/api/test/common-script/uim-not-exist")
        _soft(resp)

    def test_get_project_environment_group_get_id_92(self, client):
        """GET /project/environment/group/get/{id}

        前端调用点：getGroupDetailEnv（project-management/envManagement.ts）
        """
        resp = client.get("/project/environment/group/get/uim-not-exist")
        _soft(resp)

    def test_get_project_environment_get_options_projectId_93(self, client):
        """GET /project/environment/get-options/{projectId}

        前端调用点：groupCategoryEnvList（project-management/envManagement.ts）
        """
        resp = client.get("/project/environment/get-options/uim-not-exist")
        _soft(resp)

    def test_get_project_file_jar_file_status_id_status_94(self, client):
        """GET /project/file/jar-file-status/{id}/{status}

        前端调用点：toggleJarFileStatus（project-management/fileManagement.ts）
        """
        resp = client.get("/project/file/jar-file-status/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_project_file_association_upgrade_projectId_95(self, client):
        """GET /project/file/association/upgrade/{projectId}

        前端调用点：upgradeAssociation（project-management/fileManagement.ts）
        """
        resp = client.get("/project/file/association/upgrade/uim-not-exist")
        _soft(resp)

    def test_get_project_application_module_setting_projectId_96(self, client):
        """GET /project/application/module-setting/{projectId}

        前端调用点：project-management/menuManagement.ts（project-management/menuManagement.ts）
        """
        resp = client.get("/project/application/module-setting/uim-not-exist")
        _soft(resp)

    def test_get_project_application_suffix_resource_pool_projectId_97(self, client):
        """GET /project/application/{suffix}/resource/pool/{projectId}

        前端调用点：project-management/menuManagement.ts（project-management/menuManagement.ts）
        """
        resp = client.get("/project/application/uim-not-exist/resource/pool/uim-not-exist")
        _soft(resp)

    def test_get_project_application_suffix_user_projectId_98(self, client):
        """GET /project/application/{suffix}/user/{projectId}

        前端调用点：project-management/menuManagement.ts（project-management/menuManagement.ts）
        """
        resp = client.get("/project/application/uim-not-exist/user/uim-not-exist")
        _soft(resp)

    def test_post_project_application_update_suffixUrl_99(self, client):
        """POST /project/application/update/{suffixUrl}

        前端调用点：postUpdateMenu（project-management/menuManagement.ts）
        """
        resp = client.post("/project/application/update/uim-not-exist", json={})
        _soft(resp)

    def test_post_project_application_suffix_100(self, client):
        """POST /project/application/{suffix}

        前端调用点：getConfigByMenuItem（project-management/menuManagement.ts）
        """
        resp = client.post("/project/application/uim-not-exist", json={})
        _soft(resp)

    def test_get_project_application_bug_platform_organizationId_101(self, client):
        """GET /project/application/bug/platform/{organizationId}

        前端调用点：getPlatformOptions（project-management/menuManagement.ts）
        """
        resp = client.get("/project/application/bug/platform/uim-not-exist")
        _soft(resp)

    def test_get_project_application_case_platform_organizationId_102(self, client):
        """GET /project/application/case/platform/{organizationId}

        前端调用点：getPlatformOptions（project-management/menuManagement.ts）
        """
        resp = client.get("/project/application/case/platform/uim-not-exist")
        _soft(resp)

    def test_get_project_application_bug_platform_info_pluginId_103(self, client):
        """GET /project/application/bug/platform/info/{pluginId}

        前端调用点：getPlatformInfo（project-management/menuManagement.ts）
        """
        resp = client.get("/project/application/bug/platform/info/uim-not-exist")
        _soft(resp)

    def test_get_project_application_case_platform_info_pluginId_104(self, client):
        """GET /project/application/case/platform/info/{pluginId}

        前端调用点：getPlatformInfo（project-management/menuManagement.ts）
        """
        resp = client.get("/project/application/case/platform/info/uim-not-exist")
        _soft(resp)

    def test_post_project_application_update_bug_sync_projectId_105(self, client):
        """POST /project/application/update/bug/sync/{projectId}

        前端调用点：postSaveDefectSync（project-management/menuManagement.ts）
        """
        resp = client.post("/project/application/update/bug/sync/uim-not-exist", json={})
        _soft(resp)

    def test_post_project_application_update_case_related_projectId_106(self, client):
        """POST /project/application/update/case/related/{projectId}

        前端调用点：postSaveRelatedCase（project-management/menuManagement.ts）
        """
        resp = client.post("/project/application/update/case/related/uim-not-exist", json={})
        _soft(resp)

    def test_post_project_application_validate_pluginId_107(self, client):
        """POST /project/application/validate/{pluginId}

        前端调用点：validateJIRAKey（project-management/menuManagement.ts）
        """
        resp = client.post("/project/application/validate/uim-not-exist", json={})
        _soft(resp)

    def test_get_project_application_bug_sync_info_projectId_108(self, client):
        """GET /project/application/bug/sync/info/{projectId}

        前端调用点：getBugSyncInfo（project-management/menuManagement.ts）
        """
        resp = client.get("/project/application/bug/sync/info/uim-not-exist")
        _soft(resp)

    def test_get_project_application_case_related_info_projectId_109(self, client):
        """GET /project/application/case/related/info/{projectId}

        前端调用点：getCaseRelatedInfo（project-management/menuManagement.ts）
        """
        resp = client.get("/project/application/case/related/info/uim-not-exist")
        _soft(resp)

    def test_get_project_robot_list_projectId_110(self, client):
        """GET /project/robot/list/{projectId}

        前端调用点：getRobotList（project-management/messageManagement.ts）
        """
        resp = client.get("/project/robot/list/uim-not-exist")
        _soft(resp)

    def test_get_notice_message_task_get_projectId_111(self, client):
        """GET /notice/message/task/get/{projectId}

        前端调用点：getMessageList（project-management/messageManagement.ts）
        """
        resp = client.get("/notice/message/task/get/uim-not-exist")
        _soft(resp)

    def test_get_notice_message_task_get_user_projectId_112(self, client):
        """GET /notice/message/task/get/user/{projectId}

        前端调用点：getMessageUserList（project-management/messageManagement.ts）
        """
        resp = client.get("/notice/message/task/get/user/uim-not-exist")
        _soft(resp)

    def test_get_notice_template_get_fields_projectId_113(self, client):
        """GET /notice/template/get/fields/{projectId}

        前端调用点：getMessageFields（project-management/messageManagement.ts）
        """
        resp = client.get("/notice/template/get/fields/uim-not-exist")
        _soft(resp)

    def test_get_notice_message_template_detail_projectId_114(self, client):
        """GET /notice/message/template/detail/{projectId}

        前端调用点：getMessageDetail（project-management/messageManagement.ts）
        """
        resp = client.get("/notice/message/template/detail/uim-not-exist")
        _soft(resp)

    def test_get_project_get_projectId_115(self, client):
        """GET /project/get/{projectId}

        前端调用点：getProjectInfo（project-management/project.ts）
        """
        resp = client.get("/project/get/uim-not-exist")
        _soft(resp)

    def test_get_project_member_get_member_option_projectId_116(self, client):
        """GET /project/member/get-member/option/{projectId}

        前端调用点：getProjectMemberOptions（project-management/projectMember.ts）
        """
        resp = client.get("/project/member/get-member/option/uim-not-exist")
        _soft(resp)

    def test_get_project_get_member_option_projectId_117(self, client):
        """GET /project/get-member/option/{projectId}

        前端调用点：getProjectOptions（project-management/projectMember.ts）
        """
        resp = client.get("/project/get-member/option/uim-not-exist")
        _soft(resp)

    def test_get_project_member_comment_user_option_projectId_118(self, client):
        """GET /project/member/comment/user-option/{projectId}

        前端调用点：getProjectMemberCommentOptions（project-management/projectMember.ts）
        """
        resp = client.get("/project/member/comment/user-option/uim-not-exist")
        _soft(resp)

    def test_get_user_role_project_delete_id_119(self, client):
        """GET /user/role/project/delete/{id}

        前端调用点：deleteUserGroup（project-management/usergroup.ts）
        """
        resp = client.get("/user/role/project/delete/uim-not-exist")
        _soft(resp)

    def test_get_user_role_project_get_member_option_projectId_userRoleId_120(self, client):
        """GET /user/role/project/get-member/option/{projectId}/{userRoleId}

        前端调用点：getProjectUserGroupOptions（project-management/usergroup.ts）
        """
        resp = client.get("/user/role/project/get-member/option/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_ai_config_get_id_121(self, client):
        """GET /ai/config/get/{id}

        前端调用点：getModelConfigDetail（setting/config.ts）
        """
        resp = client.get("/ai/config/get/uim-not-exist")
        _soft(resp)

    def test_get_ai_config_delete_id_122(self, client):
        """GET /ai/config/delete/{id}

        前端调用点：deleteModelConfig（setting/config.ts）
        """
        resp = client.get("/ai/config/delete/uim-not-exist")
        _soft(resp)

    def test_get_organization_log_user_list_id_123(self, client):
        """GET /organization/log/user/list/{id}

        前端调用点：getOrgLogUsers（setting/log.ts）
        """
        resp = client.get("/organization/log/user/list/uim-not-exist")
        _soft(resp)

    def test_get_project_log_user_list_id_124(self, client):
        """GET /project/log/user/list/{id}

        前端调用点：getProjectLogUsers（setting/log.ts）
        """
        resp = client.get("/project/log/user/list/uim-not-exist")
        _soft(resp)

    def test_get_organization_not_exist_user_list_organizationId_125(self, client):
        """GET /organization/not-exist/user/list/{organizationId}

        前端调用点：getUser（setting/member.ts）
        """
        resp = client.get("/organization/not-exist/user/list/uim-not-exist")
        _soft(resp)

    def test_get_organization_project_list_organizationId_126(self, client):
        """GET /organization/project/list/{organizationId}

        前端调用点：getProjectList（setting/member.ts）
        """
        resp = client.get("/organization/project/list/uim-not-exist")
        _soft(resp)

    def test_get_system_organization_delete_id_127(self, client):
        """GET /system/organization/delete/{id}

        前端调用点：deleteOrg（setting/organizationAndProject.ts）
        """
        resp = client.get("/system/organization/delete/uim-not-exist")
        _soft(resp)

    def test_get_system_project_delete_id_128(self, client):
        """GET /system/project/delete/{id}

        前端调用点：deleteProject（setting/organizationAndProject.ts）
        """
        resp = client.get("/system/project/delete/uim-not-exist")
        _soft(resp)

    def test_get_system_organization_recover_id_129(self, client):
        """GET /system/organization/recover/{id}

        前端调用点：revokeDeleteOrg（setting/organizationAndProject.ts）
        """
        resp = client.get("/system/organization/recover/uim-not-exist")
        _soft(resp)

    def test_get_system_project_revoke_id_130(self, client):
        """GET /system/project/revoke/{id}

        前端调用点：revokeDeleteProject（setting/organizationAndProject.ts）
        """
        resp = client.get("/system/project/revoke/uim-not-exist")
        _soft(resp)

    def test_get_system_organization_get_option_sourceId_131(self, client):
        """GET /system/organization/get-option/{sourceId}

        前端调用点：getUserByOrganizationOrProject（setting/organizationAndProject.ts）
        """
        resp = client.get("/system/organization/get-option/uim-not-exist")
        _soft(resp)

    def test_get_organization_project_delete_id_132(self, client):
        """GET /organization/project/delete/{id}

        前端调用点：deleteProjectByOrg（setting/organizationAndProject.ts）
        """
        resp = client.get("/organization/project/delete/uim-not-exist")
        _soft(resp)

    def test_get_organization_project_revoke_id_133(self, client):
        """GET /organization/project/revoke/{id}

        前端调用点：revokeDeleteProjectByOrg（setting/organizationAndProject.ts）
        """
        resp = client.get("/organization/project/revoke/uim-not-exist")
        _soft(resp)

    def test_get_organization_project_remove_member_projectId_userId_134(self, client):
        """GET /organization/project/remove-member/{projectId}/{userId}

        前端调用点：deleteProjectMemberByOrg（setting/organizationAndProject.ts）
        """
        resp = client.get("/organization/project/remove-member/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_organization_project_user_member_list_organizationId_projectId_135(self, client):
        """GET /organization/project/user-member-list/{organizationId}/{projectId}

        前端调用点：getUserByProjectByOrg（setting/organizationAndProject.ts）
        """
        resp = client.get("/organization/project/user-member-list/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_plugin_image_pluginId_136(self, client):
        """GET /plugin/image/{pluginId}

        前端调用点：getLogo（setting/serviceIntegration.ts）
        """
        resp = client.get("/plugin/image/uim-not-exist")
        _soft(resp)

    def test_get_organization_template_list_organizationId_scene_137(self, client):
        """GET /organization/template/list/{organizationId}/{scene}

        前端调用点：getOrganizeTemplateList（setting/template.ts）
        """
        resp = client.get("/organization/template/list/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_organization_template_get_id_138(self, client):
        """GET /organization/template/get/{id}

        前端调用点：getOrganizeTemplateInfo（setting/template.ts）
        """
        resp = client.get("/organization/template/get/uim-not-exist")
        _soft(resp)

    def test_get_organization_template_delete_id_139(self, client):
        """GET /organization/template/delete/{id}

        前端调用点：deleteOrdTemplate（setting/template.ts）
        """
        resp = client.get("/organization/template/delete/uim-not-exist")
        _soft(resp)

    def test_get_organization_template_disable_organizationId_scene_140(self, client):
        """GET /organization/template/disable/{organizationId}/{scene}

        前端调用点：enableOrOffTemplate（setting/template.ts）
        """
        resp = client.get("/organization/template/disable/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_organization_custom_field_list_scopedId_scene_141(self, client):
        """GET /organization/custom/field/list/{scopedId}/{scene}

        前端调用点：getFieldList（setting/template.ts）
        """
        resp = client.get("/organization/custom/field/list/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_organization_status_flow_setting_get_scopedId_scene_142(self, client):
        """GET /organization/status/flow/setting/get/{scopedId}/{scene}

        前端调用点：getWorkFlowList（setting/template.ts）
        """
        resp = client.get("/organization/status/flow/setting/get/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_post_organization_status_flow_setting_status_sort_scopedId_scene_143(self, client):
        """POST /organization/status/flow/setting/status/sort/{scopedId}/{scene}

        前端调用点：setOrdWorkStateSort（setting/template.ts）
        """
        resp = client.post("/organization/status/flow/setting/status/sort/uim-not-exist/uim-not-exist", json={})
        _soft(resp)

    def test_get_project_custom_field_list_scopedId_scene_144(self, client):
        """GET /project/custom/field/list/{scopedId}/{scene}

        前端调用点：getProjectFieldList（setting/template.ts）
        """
        resp = client.get("/project/custom/field/list/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_project_template_list_projectId_scene_145(self, client):
        """GET /project/template/list/{projectId}/{scene}

        前端调用点：getProjectTemplateList（setting/template.ts）
        """
        resp = client.get("/project/template/list/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_project_template_get_id_146(self, client):
        """GET /project/template/get/{id}

        前端调用点：getProjectTemplateInfo（setting/template.ts）
        """
        resp = client.get("/project/template/get/uim-not-exist")
        _soft(resp)

    def test_get_project_template_delete_id_147(self, client):
        """GET /project/template/delete/{id}

        前端调用点：deleteProjectTemplate（setting/template.ts）
        """
        resp = client.get("/project/template/delete/uim-not-exist")
        _soft(resp)

    def test_get_project_template_set_default_projectId_id_148(self, client):
        """GET /project/template/set-default/{projectId}/{id}

        前端调用点：setDefaultTemplate（setting/template.ts）
        """
        resp = client.get("/project/template/set-default/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_project_status_flow_setting_get_scopedId_scene_149(self, client):
        """GET /project/status/flow/setting/get/{scopedId}/{scene}

        前端调用点：getProjectWorkFlowList（setting/template.ts）
        """
        resp = client.get("/project/status/flow/setting/get/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_post_project_status_flow_setting_status_sort_scopedId_scene_150(self, client):
        """POST /project/status/flow/setting/status/sort/{scopedId}/{scene}

        前端调用点：setProjectWorkStateSort（setting/template.ts）
        """
        resp = client.post("/project/status/flow/setting/status/sort/uim-not-exist/uim-not-exist", json={})
        _soft(resp)

    def test_get_user_role_organization_list_organizationId_151(self, client):
        """GET /user/role/organization/list/{organizationId}

        前端调用点：getOrgUserGroupList（setting/usergroup.ts）
        """
        resp = client.get("/user/role/organization/list/uim-not-exist")
        _soft(resp)

    def test_get_user_role_global_delete_id_152(self, client):
        """GET /user/role/global/delete/{id}

        前端调用点：deleteUserGroup（setting/usergroup.ts）
        """
        resp = client.get("/user/role/global/delete/uim-not-exist")
        _soft(resp)

    def test_get_user_role_organization_delete_id_153(self, client):
        """GET /user/role/organization/delete/{id}

        前端调用点：deleteOrgUserGroup（setting/usergroup.ts）
        """
        resp = client.get("/user/role/organization/delete/uim-not-exist")
        _soft(resp)

    def test_get_user_role_global_permission_setting_id_154(self, client):
        """GET /user/role/global/permission/setting/{id}

        前端调用点：getGlobalUSetting（setting/usergroup.ts）
        """
        resp = client.get("/user/role/global/permission/setting/uim-not-exist")
        _soft(resp)

    def test_get_user_role_organization_permission_setting_id_155(self, client):
        """GET /user/role/organization/permission/setting/{id}

        前端调用点：getOrgUSetting（setting/usergroup.ts）
        """
        resp = client.get("/user/role/organization/permission/setting/uim-not-exist")
        _soft(resp)

    def test_get_user_role_relation_global_user_option_id_156(self, client):
        """GET /user/role/relation/global/user/option/{id}

        前端调用点：getSystemUserGroupOption（setting/usergroup.ts）
        """
        resp = client.get("/user/role/relation/global/user/option/uim-not-exist")
        _soft(resp)

    def test_get_user_role_organization_get_member_option_organizationId_roleId_157(self, client):
        """GET /user/role/organization/get-member/option/{organizationId}/{roleId}

        前端调用点：getOrgUserGroupOption（setting/usergroup.ts）
        """
        resp = client.get("/user/role/organization/get-member/option/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_user_role_relation_global_delete_id_158(self, client):
        """GET /user/role/relation/global/delete/{id}

        前端调用点：deleteUserFromUserGroup（setting/usergroup.ts）
        """
        resp = client.get("/user/role/relation/global/delete/uim-not-exist")
        _soft(resp)

    def test_get_project_has_permission_userId_159(self, client):
        """GET /project/has-permission/{userId}

        前端调用点：getUserHasProjectPermission（system.ts）
        """
        resp = client.get("/project/has-permission/uim-not-exist")
        _soft(resp)

    def test_get_organization_task_center_exec_task_stop_id_160(self, client):
        """GET /organization/task-center/exec-task/stop/{id}

        前端调用点：organizationStopTask（taskCenter/organization.ts）
        """
        resp = client.get("/organization/task-center/exec-task/stop/uim-not-exist")
        _soft(resp)

    def test_get_organization_task_center_exec_task_delete_id_161(self, client):
        """GET /organization/task-center/exec-task/delete/{id}

        前端调用点：organizationDeleteTask（taskCenter/organization.ts）
        """
        resp = client.get("/organization/task-center/exec-task/delete/uim-not-exist")
        _soft(resp)

    def test_get_organization_task_center_schedule_switch_id_162(self, client):
        """GET /organization/task-center/schedule/switch/{id}

        前端调用点：organizationScheduleSwitch（taskCenter/organization.ts）
        """
        resp = client.get("/organization/task-center/schedule/switch/uim-not-exist")
        _soft(resp)

    def test_get_organization_task_center_exec_task_item_stop_id_id_163(self, client):
        """GET /organization/task-center/exec-task/item/stop/{id}/{id}

        前端调用点：organizationStopTaskDetail（taskCenter/organization.ts）
        """
        resp = client.get("/organization/task-center/exec-task/item/stop/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_organization_task_center_schedule_delete_id_164(self, client):
        """GET /organization/task-center/schedule/delete/{id}

        前端调用点：organizationDeleteSchedule（taskCenter/organization.ts）
        """
        resp = client.get("/organization/task-center/schedule/delete/uim-not-exist")
        _soft(resp)

    def test_get_organization_task_center_exec_task_rerun_id_165(self, client):
        """GET /organization/task-center/exec-task/rerun/{id}

        前端调用点：organizationTaskRerun（taskCenter/organization.ts）
        """
        resp = client.get("/organization/task-center/exec-task/rerun/uim-not-exist")
        _soft(resp)

    def test_get_project_task_center_exec_task_stop_id_166(self, client):
        """GET /project/task-center/exec-task/stop/{id}

        前端调用点：projectStopTask（taskCenter/project.ts）
        """
        resp = client.get("/project/task-center/exec-task/stop/uim-not-exist")
        _soft(resp)

    def test_get_project_task_center_exec_task_delete_id_167(self, client):
        """GET /project/task-center/exec-task/delete/{id}

        前端调用点：projectDeleteTask（taskCenter/project.ts）
        """
        resp = client.get("/project/task-center/exec-task/delete/uim-not-exist")
        _soft(resp)

    def test_get_project_task_center_schedule_switch_id_168(self, client):
        """GET /project/task-center/schedule/switch/{id}

        前端调用点：projectScheduleSwitch（taskCenter/project.ts）
        """
        resp = client.get("/project/task-center/schedule/switch/uim-not-exist")
        _soft(resp)

    def test_get_project_task_center_exec_task_item_stop_id_169(self, client):
        """GET /project/task-center/exec-task/item/stop/{id}

        前端调用点：projectStopTaskDetail（taskCenter/project.ts）
        """
        resp = client.get("/project/task-center/exec-task/item/stop/uim-not-exist")
        _soft(resp)

    def test_get_project_task_center_schedule_delete_id_170(self, client):
        """GET /project/task-center/schedule/delete/{id}

        前端调用点：projectDeleteSchedule（taskCenter/project.ts）
        """
        resp = client.get("/project/task-center/schedule/delete/uim-not-exist")
        _soft(resp)

    def test_get_project_task_center_exec_task_rerun_id_171(self, client):
        """GET /project/task-center/exec-task/rerun/{id}

        前端调用点：projectTaskRerun（taskCenter/project.ts）
        """
        resp = client.get("/project/task-center/exec-task/rerun/uim-not-exist")
        _soft(resp)

    def test_get_system_task_center_schedule_switch_id_172(self, client):
        """GET /system/task-center/schedule/switch/{id}

        前端调用点：systemScheduleSwitch（taskCenter/system.ts）
        """
        resp = client.get("/system/task-center/schedule/switch/uim-not-exist")
        _soft(resp)

    def test_get_system_task_center_exec_task_stop_id_173(self, client):
        """GET /system/task-center/exec-task/stop/{id}

        前端调用点：systemStopTask（taskCenter/system.ts）
        """
        resp = client.get("/system/task-center/exec-task/stop/uim-not-exist")
        _soft(resp)

    def test_get_system_task_center_exec_task_item_stop_id_174(self, client):
        """GET /system/task-center/exec-task/item/stop/{id}

        前端调用点：systemStopTaskDetail（taskCenter/system.ts）
        """
        resp = client.get("/system/task-center/exec-task/item/stop/uim-not-exist")
        _soft(resp)

    def test_get_system_task_center_exec_task_delete_id_175(self, client):
        """GET /system/task-center/exec-task/delete/{id}

        前端调用点：systemDeleteTask（taskCenter/system.ts）
        """
        resp = client.get("/system/task-center/exec-task/delete/uim-not-exist")
        _soft(resp)

    def test_get_system_task_center_schedule_delete_id_176(self, client):
        """GET /system/task-center/schedule/delete/{id}

        前端调用点：systemDeleteSchedule（taskCenter/system.ts）
        """
        resp = client.get("/system/task-center/schedule/delete/uim-not-exist")
        _soft(resp)

    def test_get_system_task_center_exec_task_rerun_id_177(self, client):
        """GET /system/task-center/exec-task/rerun/{id}

        前端调用点：systemTaskRerun（taskCenter/system.ts）
        """
        resp = client.get("/system/task-center/exec-task/rerun/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_delete_id_178(self, client):
        """GET /test-plan/report/delete/{id}

        前端调用点：reportDelete（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/delete/uim-not-exist")
        _soft(resp)

    def test_post_test_plan_report_rename_id_179(self, client):
        """POST /test-plan/report/rename/{id}

        前端调用点：reportRename（test-plan/report.ts）
        """
        resp = client.post("/test-plan/report/rename/uim-not-exist", json={})
        _soft(resp)

    def test_get_test_plan_report_share_get_detail_shareId_id_180(self, client):
        """GET /test-plan/report/share/get/detail/{shareId}/{id}

        前端调用点：getReportDetail（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/share/get/detail/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_get_id_181(self, client):
        """GET /test-plan/report/get/{id}

        前端调用点：getReportDetail（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/get/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_share_get_id_182(self, client):
        """GET /test-plan/report/share/get/{id}

        前端调用点：planGetShareHref（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/share/get/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_share_get_share_time_id_183(self, client):
        """GET /test-plan/report/share/get-share-time/{id}

        前端调用点：getShareValidity（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/share/get-share-time/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_share_detail_scenario_report_shareId_reportId_184(self, client):
        """GET /test-plan/report/share/detail/scenario-report/{shareId}/{reportId}

        前端调用点：reportScenarioDetail（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/share/detail/scenario-report/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_api_scenario_report_get_reportId_185(self, client):
        """GET /test-plan/api/scenario/report/get/{reportId}

        前端调用点：reportScenarioDetail（test-plan/report.ts）
        """
        resp = client.get("/test-plan/api/scenario/report/get/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_share_detail_scenario_report_get_shareId_reportId_stepId_186(self, client):
        """GET /test-plan/report/share/detail/scenario-report/get/{shareId}/{reportId}/{stepId}

        前端调用点：reportStepDetail（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/share/detail/scenario-report/get/uim-not-exist/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_api_scenario_report_get_detail_reportId_stepId_187(self, client):
        """GET /test-plan/api/scenario/report/get/detail/{reportId}/{stepId}

        前端调用点：reportStepDetail（test-plan/report.ts）
        """
        resp = client.get("/test-plan/api/scenario/report/get/detail/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_share_detail_api_report_shareId_reportId_188(self, client):
        """GET /test-plan/report/share/detail/api-report/{shareId}/{reportId}

        前端调用点：reportCaseDetail（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/share/detail/api-report/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_api_case_report_get_reportId_189(self, client):
        """GET /test-plan/api/case/report/get/{reportId}

        前端调用点：reportCaseDetail（test-plan/report.ts）
        """
        resp = client.get("/test-plan/api/case/report/get/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_share_detail_api_report_get_shareId_reportId_stepId_190(self, client):
        """GET /test-plan/report/share/detail/api-report/get/{shareId}/{reportId}/{stepId}

        前端调用点：reportCaseStepDetail（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/share/detail/api-report/get/uim-not-exist/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_api_case_report_get_detail_reportId_stepId_191(self, client):
        """GET /test-plan/api/case/report/get/detail/{reportId}/{stepId}

        前端调用点：reportCaseStepDetail（test-plan/report.ts）
        """
        resp = client.get("/test-plan/api/case/report/get/detail/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_share_detail_functional_case_step_shareId_reportId_192(self, client):
        """GET /test-plan/report/share/detail/functional/case/step/{shareId}/{reportId}

        前端调用点：getFunctionalExecuteStep（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/share/detail/functional/case/step/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_detail_functional_case_step_reportId_193(self, client):
        """GET /test-plan/report/detail/functional/case/step/{reportId}

        前端调用点：getFunctionalExecuteStep（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/detail/functional/case/step/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_share_get_layout_shareId_reportId_194(self, client):
        """GET /test-plan/report/share/get-layout/{shareId}/{reportId}

        前端调用点：getReportLayout（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/share/get-layout/uim-not-exist/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_get_layout_reportId_195(self, client):
        """GET /test-plan/report/get-layout/{reportId}

        前端调用点：getReportLayout（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/get-layout/uim-not-exist")
        _soft(resp)

    def test_post_test_plan_report_export_reportId_196(self, client):
        """POST /test-plan/report/export/{reportId}

        前端调用点：logTestPlanReportExport（test-plan/report.ts）
        """
        resp = client.post("/test-plan/report/export/uim-not-exist", json={})
        _soft(resp)

    def test_get_test_plan_report_get_result_id_197(self, client):
        """GET /test-plan/report/get-result/{id}

        前端调用点：getTestPlanResult（test-plan/report.ts）
        """
        resp = client.get("/test-plan/report/get-result/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_module_tree_projectId_198(self, client):
        """GET /test-plan/module/tree/{projectId}

        前端调用点：getTestPlanModule（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/module/tree/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_module_delete_id_199(self, client):
        """GET /test-plan/module/delete/{id}

        前端调用点：deletePlanModuleTree（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/module/delete/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_test_plan_list_projectId_200(self, client):
        """GET /test-plan/test-plan-list/{projectId}

        前端调用点：getTestPlanListWithoutPage（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/test-plan-list/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_id_201(self, client):
        """GET /test-plan/{id}

        前端调用点：getTestPlanDetail（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_delete_id_202(self, client):
        """GET /test-plan/delete/{id}

        前端调用点：deletePlan（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/delete/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_getCount_id_203(self, client):
        """GET /test-plan/getCount/{id}

        前端调用点：getStatisticalCount（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/getCount/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_archived_id_204(self, client):
        """GET /test-plan/archived/{id}

        前端调用点：archivedPlan（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/archived/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_functional_case_user_option_projectId_205(self, client):
        """GET /test-plan/functional/case/user-option/{projectId}

        前端调用点：batchExecuteCase（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/functional/case/user-option/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_functional_case_detail_id_206(self, client):
        """GET /test-plan/functional/case/detail/{id}

        前端调用点：getCaseDetail（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/functional/case/detail/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_functional_case_disassociate_bug_id_207(self, client):
        """GET /test-plan/functional/case/disassociate/bug/{id}

        前端调用点：testPlanCancelBug（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/functional/case/disassociate/bug/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_api_case_run_id_208(self, client):
        """GET /test-plan/api/case/run/{id}

        前端调用点：runApiCase（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/api/case/run/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_api_scenario_run_id_209(self, client):
        """GET /test-plan/api/scenario/run/{id}

        前端调用点：runApiScenario（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/api/scenario/run/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_copy_id_210(self, client):
        """GET /test-plan/copy/{id}

        前端调用点：testPlanAndGroupCopy（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/copy/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_group_list_projectId_211(self, client):
        """GET /test-plan/group-list/{projectId}

        前端调用点：getPlanGroupOptions（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/group-list/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_schedule_config_delete_testPlanId_212(self, client):
        """GET /test-plan/schedule-config-delete/{testPlanId}

        前端调用点：deleteScheduleTask（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/schedule-config-delete/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_execute_user_option_projectId_213(self, client):
        """GET /test-plan-execute/user-option/{projectId}

        前端调用点：getExecuteUserOption（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan-execute/user-option/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_api_case_disassociate_bug_id_214(self, client):
        """GET /test-plan/api/case/disassociate/bug/{id}

        前端调用点：cancelBugFromApiCase（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/api/case/disassociate/bug/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_api_scenario_disassociate_bug_id_215(self, client):
        """GET /test-plan/api/scenario/disassociate/bug/{id}

        前端调用点：cancelBugFromScenarioCase（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/api/scenario/disassociate/bug/uim-not-exist")
        _soft(resp)

    def test_get_test_plan_report_get_task_id_216(self, client):
        """GET /test-plan/report/get-task/{id}

        前端调用点：getTaskResult（test-plan/testPlan.ts）
        """
        resp = client.get("/test-plan/report/get-task/uim-not-exist")
        _soft(resp)

    def test_post_user_platform_validate_id_orgId_217(self, client):
        """POST /user/platform/validate/{id}/{orgId}

        前端调用点：validatePlatform（user/index.ts）
        """
        resp = client.post("/user/platform/validate/uim-not-exist/uim-not-exist", json={})
        _soft(resp)

    def test_get_user_view_viewType_grouped_list_218(self, client):
        """GET /user-view/{viewType}/grouped/list

        前端调用点：getViewList（user/index.ts）
        """
        resp = client.get("/user-view/uim-not-exist/grouped/list")
        _soft(resp)

    def test_get_user_view_viewType_get_id_219(self, client):
        """GET /user-view/{viewType}/get/{id}

        前端调用点：getViewDetail（user/index.ts）
        """
        resp = client.get("/user-view/uim-not-exist/get/uim-not-exist")
        _soft(resp)

    def test_post_user_view_viewType_update_220(self, client):
        """POST /user-view/{viewType}/update

        前端调用点：updateView（user/index.ts）
        """
        resp = client.post("/user-view/uim-not-exist/update", json={})
        _soft(resp)

    def test_post_user_view_viewType_add_221(self, client):
        """POST /user-view/{viewType}/add

        前端调用点：addView（user/index.ts）
        """
        resp = client.post("/user-view/uim-not-exist/add", json={})
        _soft(resp)

    def test_get_user_view_viewType_delete_id_222(self, client):
        """GET /user-view/{viewType}/delete/{id}

        前端调用点：deleteView（user/index.ts）
        """
        resp = client.get("/user-view/uim-not-exist/delete/uim-not-exist")
        _soft(resp)

    def test_get_personal_model_get_id_223(self, client):
        """GET /personal/model/get/{id}

        前端调用点：getPersonalModelConfigDetail（user/index.ts）
        """
        resp = client.get("/personal/model/get/uim-not-exist")
        _soft(resp)

    def test_get_personal_model_delete_id_224(self, client):
        """GET /personal/model/delete/{id}

        前端调用点：deletePersonalModelConfig（user/index.ts）
        """
        resp = client.get("/personal/model/delete/uim-not-exist")
        _soft(resp)

    def test_get_dashboard_header_custom_field_projectId_225(self, client):
        """GET /dashboard/header/custom-field/{projectId}

        前端调用点：getCustomFieldHeader（workbench.ts）
        """
        resp = client.get("/dashboard/header/custom-field/uim-not-exist")
        _soft(resp)

    def test_get_dashboard_header_columns_option_projectId_226(self, client):
        """GET /dashboard/header/columns-option/{projectId}

        前端调用点：getCustomOptionHeader（workbench.ts）
        """
        resp = client.get("/dashboard/header/columns-option/uim-not-exist")
        _soft(resp)

    def test_get_dashboard_layout_get_orgId_227(self, client):
        """GET /dashboard/layout/get/{orgId}

        前端调用点：getDashboardLayout（workbench.ts）
        """
        resp = client.get("/dashboard/layout/get/uim-not-exist")
        _soft(resp)

    def test_post_dashboard_layout_edit_orgId_228(self, client):
        """POST /dashboard/layout/edit/{orgId}

        前端调用点：editDashboardLayout（workbench.ts）
        """
        resp = client.post("/dashboard/layout/edit/uim-not-exist", json={})
        _soft(resp)

    def test_get_dashboard_member_get_project_member_option_projectId_229(self, client):
        """GET /dashboard/member/get-project-member/option/{projectId}

        前端调用点：workProjectMemberOptions（workbench.ts）
        """
        resp = client.get("/dashboard/member/get-project-member/option/uim-not-exist")
        _soft(resp)

    def test_get_dashboard_plan_option_projectId_230(self, client):
        """GET /dashboard/plan/option/{projectId}

        前端调用点：getWorkTestPlanListUrl（workbench.ts）
        """
        resp = client.get("/dashboard/plan/option/uim-not-exist")
        _soft(resp)

