# 空壳路由（stub / 假成功）报告

> 由 `scripts/stub_route_report.py` 自动生成。识别口径：路由处理函数体内
> 不存在对 service/repo/store/DB 等业务数据访问层的副作用调用。

- 扫描路由函数总数：**1851**
- 疑似空壳路由：**882**（A 假成功占位 661 · X 待人工核查 221）

## 按文件分布（疑似空壳）

| 路由文件 | 疑似空壳数 |
|----------|------------|
| `app/routers/task_center.py` | 107 |
| `app/test_plan/router.py` | 68 |
| `app/routers/other_compat.py` | 62 |
| `app/routers/functional_cases_extra.py` | 48 |
| `app/routers/system_compat.py` | 47 |
| `app/routers/apitest_compat_definition.py` | 42 |
| `app/routers/case_review.py` | 38 |
| `app/routers/apitest_compat_scenario.py` | 36 |
| `app/routers/defects_compat_extra.py` | 34 |
| `app/routers/integrations.py` | 33 |
| `app/routers/project_compat_environment.py` | 28 |
| `app/routers/project_compat_file.py` | 27 |
| `app/routers/reports_compat.py` | 26 |
| `app/routers/apitest_compat_case.py` | 24 |
| `app/routers/functional_cases.py` | 22 |
| `app/routers/method_compat.py` | 22 |
| `app/routers/defects_compat.py` | 18 |
| `app/auth/router_system.py` | 17 |
| `app/routers/system_compat_extra.py` | 17 |
| `app/routers/attachment.py` | 16 |
| `app/routers/project_compat_extra2.py` | 14 |
| `app/routers/test_resources.py` | 14 |
| `app/routers/project_compat_extra.py` | 12 |
| `app/routers/system_compat_userrole.py` | 12 |
| `app/routers/plugins.py` | 10 |
| `app/routers/debug_compat.py` | 9 |
| `app/routers/gap_fixes.py` | 9 |
| `app/routers/project_compat_application.py` | 8 |
| `app/routers/apitest_compat_mock.py` | 7 |
| `app/test_plan/router_system.py` | 7 |
| `app/file_mgmt/router.py` | 6 |
| `app/test_plan/router_dashboard_stats.py` | 6 |
| `app/auth/router.py` | 5 |
| `app/routers/platform.py` | 5 |
| `app/routers/system.py` | 5 |
| `app/routers/extra_router.py` | 4 |
| `app/routers/project_compat_member.py` | 4 |
| `app/routers/auth_compat.py` | 2 |
| `app/test_plan/router_dashboard_home.py` | 2 |
| `app/routers/missing_admin.py` | 2 |
| `app/test_plan/router_dashboard_mine.py` | 2 |
| `app/routers/apitest.py` | 1 |
| `app/routers/notifications.py` | 1 |
| `app/routers/ai_config.py` | 1 |
| `app/routers/generation.py` | 1 |
| `app/routers/organizations.py` | 1 |

## A 类：假成功占位（最需修复——接真实 Service，或确认纯兼容后返回显式 stub()）

| 文件 | 行 | 函数 | 方法 | 路径 | 前端引用 | 返回形态 |
|------|----|------|------|------|----------|----------|
| `app/auth/router.py` | 282 | get_authentication_list | GET | `/authentication/get-list` | ✅ | `ok(["LOCAL"])` |
| `app/auth/router.py` | 509 | get_default_locale | GET | `/user/local/config/default-locale` | ✅ | `ok("zh-CN")` |
| `app/auth/router_system.py` | 26 | get_system_version | GET | `/system/version/current` | ✅ | `ok("v0.2.0")` |
| `app/auth/router_system.py` | 32 | get_package_type | GET | `/system/version/package-type` | ✅ | `ok("enterprise")` |
| `app/auth/router_system.py` | 324 | get_base_info | GET | `/system/parameter/get/base-info` | ✅ | `ok({
        "name": "Test Generation Agent",
        "description": "…` |
| `app/auth/router_system.py` | 335 | save_base_info | POST | `/system/parameter/save/base-info` | ✅ | `ok()` |
| `app/auth/router_system.py` | 341 | save_base_url | POST | `/system/parameter/save/base-url` | ✅ | `ok()` |
| `app/auth/router_system.py` | 418 | get_logo_platform | GET | `/base-display/get/logo-platform` | — | `ok({"url": "", "name": ""})` |
| `app/auth/router_system.py` | 424 | get_login_logo | GET | `/base-display/get/login-logo` | ✅ | `ok({"url": "", "name": ""})` |
| `app/auth/router_system.py` | 430 | get_login_image | GET | `/base-display/get/login-image` | ✅ | `ok({"url": "", "name": ""})` |
| `app/auth/router_system.py` | 436 | get_platform_icon | GET | `/base-display/get/icon` | — | `ok({"url": "", "name": ""})` |
| `app/auth/router_system.py` | 468 | get_env_detail | GET | `/api/test/environment/get` | ✅ | `ok()` |
| `app/auth/router_system.py` | 535 | get_environment | GET | `/api/test/environment/{env_id}` | ✅ | `ok({
        "id": env_id,
        "name": "默认环境",
        "config": {…` |
| `app/auth/router_system.py` | 545 | get_plugin_options | GET | `/api/test/plugin/form/option` | ✅ | `ok([])` |
| `app/auth/router_system.py` | 551 | get_plugin_script | GET | `/api/test/plugin/script` | ✅ | `ok()` |
| `app/file_mgmt/router.py` | 156 | project_file_type | POST | `/project/file/type` | ✅ | `ok([
        "FILE", "IMAGE", "JAR", "XLS", "XLSX", "CSV",
        "DO…` |
| `app/file_mgmt/router.py` | 192 | file_preview_original | GET | `/file/preview/original` | ✅ | `ok(None)` |
| `app/file_mgmt/router.py` | 198 | file_preview_compressed | GET | `/file/preview/compressed` | ✅ | `ok(None)` |
| `app/file_mgmt/router.py` | 280 | bug_attachment_list | GET | `/bug/attachment/list/{bug_id}` | ✅ | `ok([])` |
| `app/file_mgmt/router.py` | 286 | bug_attachment_delete | POST | `/bug/attachment/delete` | ✅ | `ok(None)` |
| `app/file_mgmt/router.py` | 323 | project_file_version | GET | `/project/file/file-version/{file_id}` | ✅ | `ok([])` |
| `app/routers/apitest.py` | 778 | api_transfer_options | GET | `/api/apitest/transfer/options` | — | `ok({
        "projects": [],
        "modules": [],
    })` |
| `app/routers/apitest_compat_case.py` | 106 | api_case_api_change_clear_by_id | GET | `/api/case/api-change/clear/{case_id}` | ✅ | `ok()` |
| `app/routers/apitest_compat_case.py` | 112 | api_case_api_change_ignore_by_id | GET | `/api/case/api-change/ignore/{case_id}` | ✅ | `ok()` |
| `app/routers/apitest_compat_case.py` | 118 | api_case_api_compare_by_id | GET | `/api/case/api/compare/{case_id}` | ✅ | `ok()` |
| `app/routers/apitest_compat_case.py` | 172 | api_case_transfer_options | GET | `/api/case/transfer/options` | ✅ | `ok([])` |
| `app/routers/apitest_compat_case.py` | 178 | api_case_api_change_clear | POST | `/api/case/api-change/clear` | ✅ | `ok()` |
| `app/routers/apitest_compat_case.py` | 185 | api_case_api_change_ignore | POST | `/api/case/api-change/ignore` | ✅ | `ok()` |
| `app/routers/apitest_compat_case.py` | 192 | api_case_api_change_sync | POST | `/api/case/api-change/sync` | ✅ | `ok({})` |
| `app/routers/apitest_compat_case.py` | 199 | api_case_api_compare | POST | `/api/case/api/compare` | ✅ | `ok([])` |
| `app/routers/apitest_compat_case.py` | 206 | api_case_batch_api_change_sync | POST | `/api/case/batch/api-change/sync` | ✅ | `ok()` |
| `app/routers/apitest_compat_case.py` | 672 | api_case_edit_pos | POST | `/api/case/edit/pos` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_case.py` | 678 | api_case_debug | POST | `/api/case/debug` | ✅ | `ok({
        "status": 200,
        "success": True,
        "body": {…` |
| `app/routers/apitest_compat_case.py` | 735 | api_case_get_reference | POST | `/api/case/get-reference` | ✅ | `ok([])` |
| `app/routers/apitest_compat_case.py` | 741 | api_case_statistics | POST | `/api/case/statistics` | ✅ | `ok([])` |
| `app/routers/apitest_compat_case.py` | 836 | api_case_file_copy | POST | `/api/case/file/copy` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_case.py` | 842 | api_case_transfer | POST | `/api/case/transfer` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_case.py` | 848 | api_case_transfer_options_path | GET | `/api/case/transfer/options/{project_id}` | ✅ | `ok([])` |
| `app/routers/apitest_compat_case.py` | 854 | api_case_upload_temp_file | POST | `/api/case/upload/temp/file` | ✅ | `ok({
        "fileId": str(uuid.uuid4()),
    })` |
| `app/routers/apitest_compat_case.py` | 895 | api_case_ai_chat | POST | `/api/case/ai/chat` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_case.py` | 902 | api_case_ai_transform | POST | `/api/case/ai/transform` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_case.py` | 909 | api_case_ai_batch_save | POST | `/api/case/ai/batch/save` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 47 | api_definition_schedule_delete_get | GET | `/api/definition/schedule/delete` | ✅ | `ok()` |
| `app/routers/apitest_compat_definition.py` | 54 | api_definition_schedule_switch_get | GET | `/api/definition/schedule/switch` | ✅ | `ok()` |
| `app/routers/apitest_compat_definition.py` | 114 | api_definition_export_by_type | POST | `/api/definition/export/{export_type}` | ✅ | `ok()` |
| `app/routers/apitest_compat_definition.py` | 164 | api_definition_download_file | GET | `/api/definition/download/file` | ✅ | `ok({"fileId": file_id, "fileName": "file"})` |
| `app/routers/apitest_compat_definition.py` | 171 | api_definition_transfer_options | GET | `/api/definition/transfer/options` | ✅ | `ok([])` |
| `app/routers/apitest_compat_definition.py` | 178 | api_definition_get_reference | GET | `/api/definition/get-reference` | ✅ | `ok([])` |
| `app/routers/apitest_compat_definition.py` | 185 | api_definition_schedule_add | POST | `/api/definition/schedule/add` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/apitest_compat_definition.py` | 193 | api_definition_schedule_update | POST | `/api/definition/schedule/update` | ✅ | `ok()` |
| `app/routers/apitest_compat_definition.py` | 201 | api_definition_schedule_delete | POST | `/api/definition/schedule/delete` | ✅ | `ok()` |
| `app/routers/apitest_compat_definition.py` | 209 | api_definition_schedule_check | POST | `/api/definition/schedule/check` | ✅ | `ok({"exist": True})` |
| `app/routers/apitest_compat_definition.py` | 217 | api_definition_schedule_switch | POST | `/api/definition/schedule/switch` | ✅ | `ok()` |
| `app/routers/apitest_compat_definition.py` | 225 | api_definition_schedule_get | POST | `/api/definition/schedule/get` | ✅ | `ok({})` |
| `app/routers/apitest_compat_definition.py` | 233 | api_definition_schedule_get_query | GET | `/api/definition/schedule/get` | ✅ | `ok({})` |
| `app/routers/apitest_compat_definition.py` | 249 | definition_stop_path | GET | `/api/definition/stop/{definition_id}` | ✅ | `ok({"id": definition_id, "stopped": True})` |
| `app/routers/apitest_compat_definition.py` | 249 | definition_stop_path | POST | `/api/definition/stop/{definition_id}` | ✅ | `ok({"id": definition_id, "stopped": True})` |
| `app/routers/apitest_compat_definition.py` | 261 | api_definition_module_trash_count_post | POST | `/api/definition/module/trash/count` | ✅ | `ok(_build_trash_count_map())` |
| `app/routers/apitest_compat_definition.py` | 460 | api_definition_import | POST | `/api/definition/import` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 467 | api_definition_export | POST | `/api/definition/export` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 491 | api_definition_batch_update | POST | `/api/definition/batch-update` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 498 | api_definition_batch_move | POST | `/api/definition/batch-move` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 505 | api_definition_copy | POST | `/api/definition/copy` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 512 | api_definition_debug | POST | `/api/definition/debug` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 534 | api_definition_edit_pos | POST | `/api/definition/edit/pos` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 669 | api_definition_module_move | POST | `/api/definition/module/move` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 699 | api_definition_stop | POST | `/api/definition/stop` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 706 | api_definition_download_file_path | GET | `/api/definition/download/file/{project_id}/{file_id}` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 713 | api_definition_transfer | POST | `/api/definition/transfer` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 720 | api_definition_transfer_options_path | GET | `/api/definition/transfer/options/{project_id}` | ✅ | `ok([])` |
| `app/routers/apitest_compat_definition.py` | 727 | api_definition_upload_temp_file | POST | `/api/definition/upload/temp/file` | ✅ | `ok({
        "fileId": str(uuid.uuid4()),
    })` |
| `app/routers/apitest_compat_definition.py` | 819 | api_definition_operation_history_save | POST | `/api/definition/operation-history/save` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 826 | api_definition_operation_history_recover | POST | `/api/definition/operation-history/recover` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 833 | api_definition_get_reference_route | POST | `/api/definition/get-reference` | ✅ | `ok([])` |
| `app/routers/apitest_compat_definition.py` | 840 | api_definition_json_schema_preview | POST | `/api/definition/json-schema/preview` | ✅ | `ok({})` |
| `app/routers/apitest_compat_definition.py` | 847 | api_definition_json_schema_auto_generate | POST | `/api/definition/json-schema/auto-generate` | ✅ | `ok({})` |
| `app/routers/apitest_compat_definition.py` | 854 | api_definition_file_copy | POST | `/api/definition/file/copy` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_definition.py` | 888 | api_definition_module_trash_tree | GET | `/api/definition/module/trash/tree` | ✅ | `ok([])` |
| `app/routers/apitest_compat_definition.py` | 895 | api_definition_module_trash_count | GET | `/api/definition/module/trash/count` | ✅ | `ok(_build_trash_count_map())` |
| `app/routers/apitest_compat_definition.py` | 948 | api_definition_module_trash_tree_post | POST | `/api/definition/module/trash/tree` | ✅ | `ok({
        "id": "root", "name": "根模块", "parentId": "root",
        …` |
| `app/routers/apitest_compat_definition.py` | 1056 | api_definition_schedule_delete_path | GET | `/api/definition/schedule/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/apitest_compat_definition.py` | 1056 | api_definition_schedule_delete_path | POST | `/api/definition/schedule/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/apitest_compat_definition.py` | 1067 | api_definition_schedule_get_path | GET | `/api/definition/schedule/get/{id}` | ✅ | `ok({"id": id, "schedule": None})` |
| `app/routers/apitest_compat_definition.py` | 1067 | api_definition_schedule_get_path | POST | `/api/definition/schedule/get/{id}` | ✅ | `ok({"id": id, "schedule": None})` |
| `app/routers/apitest_compat_definition.py` | 1078 | api_definition_schedule_switch_path | GET | `/api/definition/schedule/switch/{id}` | ✅ | `ok({"id": id, "enabled": True})` |
| `app/routers/apitest_compat_definition.py` | 1078 | api_definition_schedule_switch_path | POST | `/api/definition/schedule/switch/{id}` | ✅ | `ok({"id": id, "enabled": True})` |
| `app/routers/apitest_compat_mock.py` | 31 | api_definition_mock_transfer_options | GET | `/api/definition/mock/transfer/options` | ✅ | `ok([])` |
| `app/routers/apitest_compat_mock.py` | 38 | api_definition_mock_get_url | GET | `/api/definition/mock/get-url` | ✅ | `ok("/mock/" + mock_id if mock_id else "/mock/")` |
| `app/routers/apitest_compat_mock.py` | 250 | api_definition_mock_upload_temp_file | POST | `/api/definition/mock/upload/temp/file` | ✅ | `ok({
        "fileId": str(uuid.uuid4()),
    })` |
| `app/routers/apitest_compat_mock.py` | 259 | api_definition_mock_transfer | POST | `/api/definition/mock/transfer` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_mock.py` | 266 | api_definition_mock_transfer_options_path | GET | `/api/definition/mock/transfer/options/{project_id}` | ✅ | `ok([])` |
| `app/routers/apitest_compat_mock.py` | 273 | api_definition_mock_get_url_path | GET | `/api/definition/mock/get-url/{mock_id}` | ✅ | `ok("/mock/" + mock_id)` |
| `app/routers/apitest_compat_scenario.py` | 86 | api_scenario_schedule_config_delete_get | GET | `/api/scenario/schedule-config-delete` | ✅ | `ok()` |
| `app/routers/apitest_compat_scenario.py` | 127 | api_scenario_get_system_request_post | POST | `/api/scenario/get/system-request` | ✅ | `ok([])` |
| `app/routers/apitest_compat_scenario.py` | 135 | api_scenario_associate_all | POST | `/api/scenario/associate/all` | ✅ | `ok()` |
| `app/routers/apitest_compat_scenario.py` | 279 | api_scenario_schedule_config | POST | `/api/scenario/schedule-config` | ✅ | `ok()` |
| `app/routers/apitest_compat_scenario.py` | 287 | api_scenario_schedule_config_delete | POST | `/api/scenario/schedule-config-delete` | ✅ | `ok()` |
| `app/routers/apitest_compat_scenario.py` | 307 | api_scenario_batch_operation_schedule_config | POST | `/api/scenario/batch-operation/schedule-config` | ✅ | `ok()` |
| `app/routers/apitest_compat_scenario.py` | 315 | api_scenario_transfer_options | GET | `/api/scenario/transfer/options` | ✅ | `ok([])` |
| `app/routers/apitest_compat_scenario.py` | 322 | api_scenario_transfer | POST | `/api/scenario/transfer` | ✅ | `ok()` |
| `app/routers/apitest_compat_scenario.py` | 330 | api_scenario_upload_temp_file | POST | `/api/scenario/upload/temp/file` | ✅ | `ok({"fileId": str(uuid.uuid4()), "fileName": "temp"})` |
| `app/routers/apitest_compat_scenario.py` | 337 | api_scenario_step_transfer | POST | `/api/scenario/step/transfer` | ✅ | `ok()` |
| `app/routers/apitest_compat_scenario.py` | 345 | api_scenario_step_file_copy | POST | `/api/scenario/step/file/copy` | ✅ | `ok()` |
| `app/routers/apitest_compat_scenario.py` | 353 | api_scenario_download_file | GET | `/api/scenario/download/file` | ✅ | `ok({"fileId": file_id, "fileName": "file"})` |
| `app/routers/apitest_compat_scenario.py` | 378 | api_scenario_edit_pos | POST | `/api/scenario/edit/pos` | ✅ | `ok()` |
| `app/routers/apitest_compat_scenario.py` | 386 | api_scenario_stop | POST | `/api/scenario/stop` | ✅ | `ok()` |
| `app/routers/apitest_compat_scenario.py` | 394 | api_scenario_step_resource_info | POST | `/api/scenario/step/resource-info` | ✅ | `ok({})` |
| `app/routers/apitest_compat_scenario.py` | 406 | scenario_download_file_path | GET | `/api/scenario/download/file/{scenario_id}/{file_id}` | ✅ | `ok({"scenario_id": scenario_id, "file_id": file_id})` |
| `app/routers/apitest_compat_scenario.py` | 406 | scenario_download_file_path | POST | `/api/scenario/download/file/{scenario_id}/{file_id}` | ✅ | `ok({"scenario_id": scenario_id, "file_id": file_id})` |
| `app/routers/apitest_compat_scenario.py` | 417 | scenario_export_path | GET | `/api/scenario/export/{scenario_id}` | ✅ | `ok({"id": scenario_id, "exported": True})` |
| `app/routers/apitest_compat_scenario.py` | 417 | scenario_export_path | POST | `/api/scenario/export/{scenario_id}` | ✅ | `ok({"id": scenario_id, "exported": True})` |
| `app/routers/apitest_compat_scenario.py` | 428 | scenario_stop_path | GET | `/api/scenario/stop/{scenario_id}` | ✅ | `ok({"id": scenario_id, "stopped": True})` |
| `app/routers/apitest_compat_scenario.py` | 428 | scenario_stop_path | POST | `/api/scenario/stop/{scenario_id}` | ✅ | `ok({"id": scenario_id, "stopped": True})` |
| `app/routers/apitest_compat_scenario.py` | 439 | scenario_update_priority_path | GET | `/api/scenario/update-priority/{scenario_id}/{priority}` | ✅ | `ok({"id": scenario_id, "priority": priority})` |
| `app/routers/apitest_compat_scenario.py` | 439 | scenario_update_priority_path | POST | `/api/scenario/update-priority/{scenario_id}/{priority}` | ✅ | `ok({"id": scenario_id, "priority": priority})` |
| `app/routers/apitest_compat_scenario.py` | 450 | scenario_update_status_path | GET | `/api/scenario/update-status/{scenario_id}/{status}` | ✅ | `ok({"id": scenario_id, "status": status})` |
| `app/routers/apitest_compat_scenario.py` | 450 | scenario_update_status_path | POST | `/api/scenario/update-status/{scenario_id}/{status}` | ✅ | `ok({"id": scenario_id, "status": status})` |
| `app/routers/apitest_compat_scenario.py` | 462 | scenario_step_resource_info_path | GET | `/api/scenario/step/resource-info/{step_id}` | ✅ | `ok({"id": step_id})` |
| `app/routers/apitest_compat_scenario.py` | 725 | api_scenario_step_get | POST | `/api/scenario/step/get` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_scenario.py` | 732 | api_scenario_debug | POST | `/api/scenario/debug` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_scenario.py` | 739 | api_scenario_import | POST | `/api/scenario/import` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_scenario.py` | 746 | api_scenario_export | POST | `/api/scenario/export` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_scenario.py` | 768 | api_scenario_batch_operation_move | POST | `/api/scenario/batch-operation/move` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_scenario.py` | 775 | api_scenario_batch_operation_copy | POST | `/api/scenario/batch-operation/copy` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_scenario.py` | 782 | api_scenario_batch_operation_run | POST | `/api/scenario/batch-operation/run` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_scenario.py` | 789 | api_scenario_update_priority | POST | `/api/scenario/update-priority` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_scenario.py` | 796 | api_scenario_update_status | POST | `/api/scenario/update-status` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_scenario.py` | 882 | api_scenario_module_move | POST | `/api/scenario/module/move` | ✅ | `ok(None)` |
| `app/routers/apitest_compat_scenario.py` | 939 | api_scenario_step_get_un_save | POST | `/api/scenario/step/get/un-save` | ✅ | `ok({
        "id": step_id, "type": "API", "name": "", "isNew": True,
…` |
| `app/routers/apitest_compat_scenario.py` | 1035 | api_scenario_schedule_config_delete_path | GET | `/api/scenario/schedule-config-delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/apitest_compat_scenario.py` | 1035 | api_scenario_schedule_config_delete_path | POST | `/api/scenario/schedule-config-delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/apitest_compat_scenario.py` | 1046 | api_scenario_step_get_path | GET | `/api/scenario/step/get/{stepId}` | ✅ | `ok({"id": stepId, "step": None})` |
| `app/routers/apitest_compat_scenario.py` | 1046 | api_scenario_step_get_path | POST | `/api/scenario/step/get/{stepId}` | ✅ | `ok({"id": stepId, "step": None})` |
| `app/routers/apitest_compat_scenario.py` | 1057 | api_scenario_transfer_options_path | GET | `/api/scenario/transfer/options/{projectId}` | ✅ | `ok([])` |
| `app/routers/apitest_compat_scenario.py` | 1057 | api_scenario_transfer_options_path | POST | `/api/scenario/transfer/options/{projectId}` | ✅ | `ok([])` |
| `app/routers/attachment.py` | 22 | attachment_check_update_post | POST | `/attachment/check-update` | ✅ | `ok()` |
| `app/routers/attachment.py` | 28 | attachment_download_file_post | POST | `/attachment/download/file` | ✅ | `ok({"fileId": file_id})` |
| `app/routers/attachment.py` | 35 | attachment_preview_post | POST | `/attachment/preview` | ✅ | `ok()` |
| `app/routers/attachment.py` | 42 | attachment_options_path | GET | `/attachment/options/{project_id}` | ✅ | `ok({"project_id": project_id})` |
| `app/routers/attachment.py` | 42 | attachment_options_path | POST | `/attachment/options/{project_id}` | ✅ | `ok({"project_id": project_id})` |
| `app/routers/attachment.py` | 49 | attachment_update_path | GET | `/attachment/update/{attachment_id}/{project_id}` | ✅ | `ok({"attachment_id": attachment_id, "project_id": project_id})` |
| `app/routers/attachment.py` | 49 | attachment_update_path | POST | `/attachment/update/{attachment_id}/{project_id}` | ✅ | `ok({"attachment_id": attachment_id, "project_id": project_id})` |
| `app/routers/attachment.py` | 67 | attachment_upload_file | POST | `/attachment/upload/file` | ✅ | `ok({
        "fileId": str(uuid.uuid4()),
        "fileName": "uploade…` |
| `app/routers/attachment.py` | 76 | attachment_transfer | POST | `/attachment/transfer` | ✅ | `ok(None)` |
| `app/routers/attachment.py` | 82 | attachment_preview | GET | `/attachment/preview` | ✅ | `ok(None)` |
| `app/routers/attachment.py` | 88 | attachment_download | GET | `/attachment/download` | ✅ | `ok(None)` |
| `app/routers/attachment.py` | 94 | attachment_delete_file | POST | `/attachment/delete/file` | ✅ | `ok(None)` |
| `app/routers/attachment.py` | 100 | attachment_options | GET | `/attachment/options` | ✅ | `ok([])` |
| `app/routers/attachment.py` | 106 | attachment_update | POST | `/attachment/update` | ✅ | `ok(None)` |
| `app/routers/attachment.py` | 112 | attachment_check_update | GET | `/attachment/check-update` | ✅ | `ok({"hasUpdate": False})` |
| `app/routers/attachment.py` | 118 | attachment_upload_temp_file | POST | `/attachment/upload/temp/file` | ✅ | `ok({
        "fileId": str(uuid.uuid4()),
    })` |
| `app/routers/attachment.py` | 126 | attachment_download_file | GET | `/attachment/download/file` | ✅ | `ok(None)` |
| `app/routers/auth_compat.py` | 15 | signout_get | GET | `/signout` | ✅ | `ok()` |
| `app/routers/case_review.py` | 602 | case_review_user_option_get | GET | `/case/review/user-option` | ✅ | `ok(cvs.list_review_users())` |
| `app/routers/case_review.py` | 611 | case_review_module_tree | GET | `/case/review/module/tree` | ✅ | `ok(cvs.build_review_module_tree())` |
| `app/routers/case_review.py` | 617 | case_review_module_tree_path | GET | `/case/review/module/tree/{project_id}` | ✅ | `ok(cvs.build_review_module_tree(project_id))` |
| `app/routers/case_review.py` | 680 | case_review_module_delete_get | GET | `/case/review/module/delete` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/case_review.py` | 691 | case_review_detail_edit_pos | POST | `/case/review/detail/edit/pos` | ✅ | `ok()` |
| `app/routers/case_review.py` | 802 | case_review_detail_reviewer_list | GET | `/case/review/detail/reviewer/list` | ✅ | `ok([])` |
| `app/routers/case_review.py` | 808 | case_review_detail_reviewer_status_total | POST | `/case/review/detail/reviewer/status/total` | ✅ | `ok([])` |
| `app/routers/case_review.py` | 835 | case_review_user_option_get_route | GET | `/case/review/user-option/{project_id}` | ✅ | `ok(cvs.list_review_users(project_id, keyword))` |
| `app/routers/case_review.py` | 841 | case_review_disassociate_get_route | GET | `/case/review/disassociate/{review_id}/{case_id}` | ✅ | `ok()` |
| `app/routers/case_review.py` | 849 | case_review_delete_get_route | GET | `/case/review/delete/{project_id}/{review_id}` | ✅ | `ok()` |
| `app/routers/case_review.py` | 857 | case_review_detail_get_ids_get_route | GET | `/case/review/detail/get-ids/{review_id}` | ✅ | `ok([link["case_id"] for link in links])` |
| `app/routers/case_review.py` | 926 | case_review_module_delete_path | GET | `/case/review/module/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/case_review.py` | 926 | case_review_module_delete_path | POST | `/case/review/module/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/debug_compat.py` | 94 | api_debug_delete_get | GET | `/api/debug/delete` | ✅ | `ok()` |
| `app/routers/debug_compat.py` | 136 | api_debug_transfer | POST | `/api/debug/transfer` | ✅ | `ok()` |
| `app/routers/debug_compat.py` | 142 | api_debug_transfer_options | GET | `/api/debug/transfer/options` | ✅ | `ok([])` |
| `app/routers/debug_compat.py` | 735 | api_debug_file_copy | POST | `/api/debug/file/copy` | ✅ | `ok(None)` |
| `app/routers/debug_compat.py` | 757 | api_debug_transfer_options_path | GET | `/api/debug/transfer/options/{projectId}` | ✅ | `ok([])` |
| `app/routers/debug_compat.py` | 757 | api_debug_transfer_options_path | POST | `/api/debug/transfer/options/{projectId}` | ✅ | `ok([])` |
| `app/routers/defects_compat.py` | 30 | bug_attachment_list | GET | `/bug/attachment/list/` | ✅ | `ok([])` |
| `app/routers/defects_compat.py` | 36 | bug_attachment_transfer_options | GET | `/bug/attachment/transfer/options/` | ✅ | `ok([])` |
| `app/routers/defects_compat.py` | 103 | bug_check_exist | GET | `/bug/check-exist/` | ✅ | `ok({"exist": True})` |
| `app/routers/defects_compat.py` | 150 | bug_export_columns | GET | `/bug/export/columns/` | ✅ | `ok([])` |
| `app/routers/defects_compat.py` | 156 | bug_sync | POST | `/bug/sync/` | ✅ | `ok()` |
| `app/routers/defects_compat.py` | 162 | bug_header_columns_option | GET | `/bug/header/columns-option/` | ✅ | `ok([])` |
| `app/routers/defects_compat.py` | 168 | bug_header_custom_field | GET | `/bug/header/custom-field/` | ✅ | `ok([])` |
| `app/routers/defects_compat.py` | 214 | api_bug_sync_trailing_get | GET | `/bug/sync/` | ✅ | `ok({"success": True, "sync": "openSource"})` |
| `app/routers/defects_compat.py` | 224 | bug_case_un_relate_path | GET | `/bug/case/un-relate/{id}` | ✅ | `ok({"id": id, "success": True})` |
| `app/routers/defects_compat.py` | 230 | bug_case_check_permission_path | GET | `/bug/case/check-permission/{project_id}/{case_type}` | ✅ | `ok({"project_id": project_id, "case_type": case_type, "hasPermission":…` |
| `app/routers/defects_compat.py` | 236 | bug_attachment_transfer_options_double_slash | GET | `/bug/attachment/transfer/options//{project_id}` | ✅ | `ok([])` |
| `app/routers/defects_compat_extra.py` | 303 | bug_current_platform | GET | `/bug/current-platform` | ✅ | `ok("Local")` |
| `app/routers/defects_compat_extra.py` | 319 | bug_template_option | GET | `/bug/template/option` | ✅ | `ok([])` |
| `app/routers/defects_compat_extra.py` | 377 | bug_export | POST | `/bug/export` | ✅ | `ok({
        "taskId": str(uuid.uuid4()),
    })` |
| `app/routers/defects_compat_extra.py` | 478 | bug_attachment_transfer | POST | `/bug/attachment/transfer` | ✅ | `ok(None)` |
| `app/routers/defects_compat_extra.py` | 484 | bug_attachment_transfer_options_path | GET | `/bug/attachment/transfer/options/{project_id}` | ✅ | `ok([])` |
| `app/routers/defects_compat_extra.py` | 490 | bug_attachment_preview | GET | `/bug/attachment/preview` | ✅ | `ok(None)` |
| `app/routers/defects_compat_extra.py` | 496 | bug_attachment_download | GET | `/bug/attachment/download` | ✅ | `ok(None)` |
| `app/routers/defects_compat_extra.py` | 502 | bug_attachment_check_update | GET | `/bug/attachment/check-update` | ✅ | `ok({"hasUpdate": False})` |
| `app/routers/defects_compat_extra.py` | 508 | bug_attachment_update | POST | `/bug/attachment/update` | ✅ | `ok(None)` |
| `app/routers/defects_compat_extra.py` | 514 | bug_attachment_file_page | POST | `/bug/attachment/file/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/defects_compat_extra.py` | 523 | bug_editor_preview_file | GET | `/bug/attachment/preview/md` | ✅ | `ok(None)` |
| `app/routers/defects_compat_extra.py` | 532 | bug_case_page | GET | `/bug/case/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/defects_compat_extra.py` | 541 | bug_case_page_post | POST | `/bug/case/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/defects_compat_extra.py` | 550 | bug_case_relate | POST | `/bug/case/relate` | ✅ | `ok(None)` |
| `app/routers/defects_compat_extra.py` | 556 | bug_case_un_relate | GET | `/bug/case/un-relate` | ✅ | `ok(None)` |
| `app/routers/defects_compat_extra.py` | 562 | bug_case_un_relate_page | POST | `/bug/case/un-relate/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/defects_compat_extra.py` | 571 | bug_case_un_relate_module_tree | GET | `/bug/case/un-relate/module/tree` | ✅ | `ok([])` |
| `app/routers/defects_compat_extra.py` | 577 | bug_case_un_relate_module_count | GET | `/bug/case/un-relate/module/count` | ✅ | `ok([])` |
| `app/routers/defects_compat_extra.py` | 583 | bug_case_check_permission | GET | `/bug/case/check-permission` | ✅ | `ok(True)` |
| `app/routers/defects_compat_extra.py` | 592 | bug_history_page | POST | `/bug/history/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/defects_compat_extra.py` | 602 | bug_history_page_get | GET | `/bug/history/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/defects_compat_extra.py` | 727 | bug_sync_path | GET | `/bug/sync/{project_id}` | ✅ | `ok({
        "status": "COMPLETED",
        "count": 0,
    })` |
| `app/routers/defects_compat_extra.py` | 736 | bug_sync_all | POST | `/bug/sync/all` | ✅ | `ok(None)` |
| `app/routers/defects_compat_extra.py` | 755 | bug_current_platform_project | GET | `/bug/current-platform/{project_id}` | ✅ | `ok("Local")` |
| `app/routers/defects_compat_extra.py` | 803 | dashboard_bug_handle_user_list_path | GET | `/dashboard/bug_handle_user/list/{projectId}` | ✅ | `ok({"list": [], "total": 0})` |
| `app/routers/defects_compat_extra.py` | 803 | dashboard_bug_handle_user_list_path | POST | `/dashboard/bug_handle_user/list/{projectId}` | ✅ | `ok({"list": [], "total": 0})` |
| `app/routers/extra_router.py` | 118 | extra_project_application | GET | `/project/application/{project_id}` | ✅ | `ok({})` |
| `app/routers/extra_router.py` | 151 | extra_project_application_validate | POST | `/project/application/validate/{project_id}` | ✅ | `ok({})` |
| `app/routers/functional_cases.py` | 133 | functional_case_test_associate_module_count_post | POST | `/functional/case/test/associate/case/module/count` | ✅ | `ok([])` |
| `app/routers/functional_cases.py` | 146 | functional_case_test_associate_case_module_tree_post | POST | `/functional/case/test/associate/case/module/tree` | ✅ | `ok([])` |
| `app/routers/functional_cases.py` | 152 | functional_case_comment_delete | POST | `/functional/case/comment/delete` | ✅ | `ok()` |
| `app/routers/functional_cases.py` | 159 | functional_case_comment_get_list | POST | `/functional/case/comment/get/list` | ✅ | `ok([])` |
| `app/routers/functional_cases.py` | 166 | functional_case_review_comment | POST | `/functional/case/review/comment` | ✅ | `ok()` |
| `app/routers/functional_cases.py` | 173 | functional_case_demand_page | POST | `/functional/case/demand/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/functional_cases.py` | 181 | func_case_custom_field_path | GET | `/functional/case/custom/field/{project_id}` | ✅ | `ok([])` |
| `app/routers/functional_cases.py` | 181 | func_case_custom_field_path | POST | `/functional/case/custom/field/{project_id}` | ✅ | `ok([])` |
| `app/routers/functional_cases.py` | 225 | func_case_demand_cancel_path | GET | `/functional/case/demand/cancel/{case_id}` | ✅ | `ok({"id": case_id, "cancelled": True})` |
| `app/routers/functional_cases.py` | 225 | func_case_demand_cancel_path | POST | `/functional/case/demand/cancel/{case_id}` | ✅ | `ok({"id": case_id, "cancelled": True})` |
| `app/routers/functional_cases.py` | 286 | func_case_module_delete_path | GET | `/functional/case/module/delete/{module_id}` | ✅ | `ok({"id": module_id, "deleted": True})` |
| `app/routers/functional_cases.py` | 286 | func_case_module_delete_path | POST | `/functional/case/module/delete/{module_id}` | ✅ | `ok({"id": module_id, "deleted": True})` |
| `app/routers/functional_cases.py` | 293 | func_case_stop_path | GET | `/functional/case/stop/{case_id}` | ✅ | `ok({"id": case_id, "stopped": True})` |
| `app/routers/functional_cases.py` | 293 | func_case_stop_path | POST | `/functional/case/stop/{case_id}` | ✅ | `ok({"id": case_id, "stopped": True})` |
| `app/routers/functional_cases.py` | 300 | func_case_disassociate_bug_path | GET | `/functional/case/test/disassociate/bug/{case_id}` | ✅ | `ok({"id": case_id, "disassociated": True})` |
| `app/routers/functional_cases.py` | 300 | func_case_disassociate_bug_path | POST | `/functional/case/test/disassociate/bug/{case_id}` | ✅ | `ok({"id": case_id, "disassociated": True})` |
| `app/routers/functional_cases.py` | 340 | functional_case_relationship_get_ids_path | GET | `/functional/case/relationship/get-ids/{case_id}` | ✅ | `ok([])` |
| `app/routers/functional_cases.py` | 349 | functional_case_test_plan_comment_path | GET | `/functional/case/test/plan/comment/{case_id}` | ✅ | `ok([])` |
| `app/routers/functional_cases.py` | 358 | functional_case_batch_edit | POST | `/functional/case/batch/edit` | ✅ | `ok(None)` |
| `app/routers/functional_cases.py` | 364 | functional_case_batch_move | POST | `/functional/case/batch/move` | ✅ | `ok(None)` |
| `app/routers/functional_cases.py` | 397 | functional_case_custom_field | POST | `/functional/case/custom/field` | ✅ | `ok([])` |
| `app/routers/functional_cases.py` | 440 | functional_case_module_move | POST | `/functional/case/module/move` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 109 | functional_mind_case_edit | POST | `/functional/mind/case/edit` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 116 | functional_mind_case_tree | GET | `/functional/mind/case/tree` | ✅ | `ok({
        "id": "root",
        "name": "全部用例",
        "type": "MO…` |
| `app/routers/functional_cases_extra.py` | 130 | functional_case_pre_check_excel | POST | `/functional/case/pre-check/excel` | ✅ | `ok({
        "success": True,
        "errors": [],
    })` |
| `app/routers/functional_cases_extra.py` | 139 | functional_case_pre_check_xmind | POST | `/functional/case/pre-check/xmind` | ✅ | `ok({
        "success": True,
        "errors": [],
    })` |
| `app/routers/functional_cases_extra.py` | 148 | functional_case_import_excel | POST | `/functional/case/import/excel` | ✅ | `ok({
        "successCount": 0,
        "failCount": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 157 | functional_case_import_xmind | POST | `/functional/case/import/xmind` | ✅ | `ok({
        "successCount": 0,
        "failCount": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 214 | functional_case_download_file | GET | `/functional/case/download/file` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 220 | functional_case_stop | GET | `/functional/case/stop` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 226 | functional_case_download_excel_template | GET | `/functional/case/download/excel/template` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 232 | functional_case_download_xmind_template | GET | `/functional/case/download/xmind/template` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 241 | functional_case_comment_get_list_by_id | GET | `/functional/case/comment/get/list/{case_id}` | ✅ | `ok([])` |
| `app/routers/functional_cases_extra.py` | 247 | functional_case_comment_save | POST | `/functional/case/comment/save` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 253 | functional_case_comment_update | POST | `/functional/case/comment/update` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 259 | functional_case_comment_delete_by_id | GET | `/functional/case/comment/delete/{comment_id}` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 265 | functional_case_review_comment_by_id | GET | `/functional/case/review/comment/{case_id}` | ✅ | `ok([])` |
| `app/routers/functional_cases_extra.py` | 274 | functional_case_demand_page_by_id | GET | `/functional/case/demand/page/{case_id}` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 283 | functional_case_demand_add | POST | `/functional/case/demand/add` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 289 | functional_case_demand_update | POST | `/functional/case/demand/update` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 295 | functional_case_demand_batch_relevance | POST | `/functional/case/demand/batch/relevance` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 301 | functional_case_demand_cancel | POST | `/functional/case/demand/cancel` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 307 | functional_case_demand_third_list | GET | `/functional/case/demand/third/list/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 319 | functional_case_relationship_page | GET | `/functional/case/relationship/page/{case_id}` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 328 | functional_case_relationship_page_post | POST | `/functional/case/relationship/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 337 | functional_case_relationship_relate_page | POST | `/functional/case/relationship/relate/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 346 | functional_case_relationship_add | POST | `/functional/case/relationship/add` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 352 | functional_case_relationship_delete | POST | `/functional/case/relationship/delete` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 358 | functional_case_relationship_get_ids | GET | `/functional/case/relationship/get-ids` | ✅ | `ok([])` |
| `app/routers/functional_cases_extra.py` | 367 | functional_case_test_associate_case_page | POST | `/functional/case/test/associate/case/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 376 | functional_case_test_associate_case_module_count | GET | `/functional/case/test/associate/case/module/count` | ✅ | `ok([])` |
| `app/routers/functional_cases_extra.py` | 382 | functional_case_test_associate_case_module_tree | GET | `/functional/case/test/associate/case/module/tree` | ✅ | `ok([])` |
| `app/routers/functional_cases_extra.py` | 388 | functional_case_test_associate_case | POST | `/functional/case/test/associate/case` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 394 | functional_case_test_has_associate_case_page | POST | `/functional/case/test/has/associate/case/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 403 | functional_case_test_disassociate_case | POST | `/functional/case/test/disassociate/case` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 409 | functional_case_test_associate_bug_page | POST | `/functional/case/test/associate/bug/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 418 | functional_case_test_associate_bug | POST | `/functional/case/test/associate/bug` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 424 | functional_case_test_disassociate_bug | POST | `/functional/case/test/disassociate/bug` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 430 | functional_case_test_has_associate_bug_page | POST | `/functional/case/test/has/associate/bug/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 439 | functional_case_test_has_associate_plan_page | POST | `/functional/case/test/has/associate/plan/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 448 | functional_case_test_plan_comment | POST | `/functional/case/test/plan/comment` | ✅ | `ok([])` |
| `app/routers/functional_cases_extra.py` | 454 | functional_case_test_associate_case_page_get | GET | `/functional/case/test/associate/case/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 466 | functional_case_operation_history | POST | `/functional/case/operation-history` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 478 | functional_case_edit_pos | POST | `/functional/case/edit/pos` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 505 | functional_case_default_template_field | GET | `/functional/case/default/template/field` | ✅ | `ok([])` |
| `app/routers/functional_cases_extra.py` | 514 | functional_case_review_page | POST | `/functional/case/review/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/routers/functional_cases_extra.py` | 560 | functional_case_ai_transform | POST | `/functional/case/ai/transform` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 567 | functional_case_ai_chat | POST | `/functional/case/ai/chat` | ✅ | `ok(None)` |
| `app/routers/functional_cases_extra.py` | 574 | functional_case_ai_batch_save | POST | `/functional/case/ai/batch/save` | ✅ | `ok(None)` |
| `app/routers/gap_fixes.py` | 42 | task_center_api_project_real_time_page | POST | `/task/center/api/project/real-time/page` | — | `page_result([], len([]), current=current, page_size=page_size)` |
| `app/routers/gap_fixes.py` | 52 | task_center_api_org_real_time_page | POST | `/task/center/api/org/real-time/page` | — | `page_result([], len([]), current=current, page_size=page_size)` |
| `app/routers/gap_fixes.py` | 62 | task_center_api_system_real_time_page | POST | `/task/center/api/system/real-time/page` | — | `page_result([], len([]), current=current, page_size=page_size)` |
| `app/routers/gap_fixes.py` | 74 | api_test_plugin_script_path | GET | `/api/test/plugin/script/{plugin_id}` | ✅ | `ok({"id": plugin_id, "script": "", "config": {}})` |
| `app/routers/gap_fixes.py` | 80 | api_test_pool_option_path | GET | `/api/test/pool-option/{project_id}` | ✅ | `ok([])` |
| `app/routers/gap_fixes.py` | 145 | project_file_association_list_path | GET | `/project/file/association/list/{id}` | ✅ | `ok([])` |
| `app/routers/gap_fixes.py` | 145 | project_file_association_list_path | POST | `/project/file/association/list/{id}` | ✅ | `ok([])` |
| `app/routers/gap_fixes.py` | 162 | project_file_repository_list_path | GET | `/project/file/repository/list/{project_id}` | ✅ | `ok([])` |
| `app/routers/gap_fixes.py` | 168 | project_file_type_path | GET | `/project/file/type/{project_id}` | ✅ | `ok(["JAR", "FILE", "IMAGE", "DOC", "XLS", "CONFIG"])` |
| `app/routers/integrations.py` | 33 | service_integration_delete_get | GET | `/service/integration/delete` | ✅ | `ok()` |
| `app/routers/integrations.py` | 39 | service_integration_validate_get | GET | `/service/integration/validate` | ✅ | `ok()` |
| `app/routers/integrations.py` | 45 | service_integration_list | GET | `/service/integration/list` | ✅ | `ok([])` |
| `app/routers/integrations.py` | 51 | service_integration_list_path | GET | `/service/integration/list/{org_id}` | ✅ | `ok([])` |
| `app/routers/integrations.py` | 75 | service_integration_script | GET | `/service/integration/script` | ✅ | `ok({})` |
| `app/routers/integrations.py` | 98 | we_com_info | GET | `/we_com/info` | ✅ | `ok({})` |
| `app/routers/integrations.py` | 104 | we_com_info_with_detail | GET | `/we_com/info/with_detail` | ✅ | `ok({})` |
| `app/routers/integrations.py` | 110 | we_com_save | POST | `/we_com/save` | ✅ | `ok()` |
| `app/routers/integrations.py` | 116 | we_com_validate | POST | `/we_com/validate` | ✅ | `ok({"success": True})` |
| `app/routers/integrations.py` | 122 | we_com_enable | POST | `/we_com/enable` | ✅ | `ok()` |
| `app/routers/integrations.py` | 128 | we_com_change_validate | POST | `/we_com/change/validate` | ✅ | `ok({"success": True})` |
| `app/routers/integrations.py` | 137 | ding_talk_info | GET | `/ding_talk/info` | ✅ | `ok({})` |
| `app/routers/integrations.py` | 143 | ding_talk_info_with_detail | GET | `/ding_talk/info/with_detail` | ✅ | `ok({})` |
| `app/routers/integrations.py` | 149 | ding_talk_save | POST | `/ding_talk/save` | ✅ | `ok()` |
| `app/routers/integrations.py` | 155 | ding_talk_validate | POST | `/ding_talk/validate` | ✅ | `ok({"success": True})` |
| `app/routers/integrations.py` | 161 | ding_talk_enable | POST | `/ding_talk/enable` | ✅ | `ok()` |
| `app/routers/integrations.py` | 167 | ding_talk_change_validate | POST | `/ding_talk/change/validate` | ✅ | `ok({"success": True})` |
| `app/routers/integrations.py` | 176 | lark_info | GET | `/lark/info` | ✅ | `ok({})` |
| `app/routers/integrations.py` | 182 | lark_info_with_detail | GET | `/lark/info/with_detail` | ✅ | `ok({})` |
| `app/routers/integrations.py` | 188 | lark_save | POST | `/lark/save` | ✅ | `ok()` |
| `app/routers/integrations.py` | 194 | lark_validate | POST | `/lark/validate` | ✅ | `ok({"success": True})` |
| `app/routers/integrations.py` | 200 | lark_enable | POST | `/lark/enable` | ✅ | `ok()` |
| `app/routers/integrations.py` | 206 | lark_change_validate | POST | `/lark/change/validate` | ✅ | `ok({"success": True})` |
| `app/routers/integrations.py` | 215 | lark_suite_info | GET | `/lark_suite/info` | ✅ | `ok({})` |
| `app/routers/integrations.py` | 221 | lark_suite_info_with_detail | GET | `/lark_suite/info/with_detail` | ✅ | `ok({})` |
| `app/routers/integrations.py` | 227 | lark_suite_save | POST | `/lark_suite/save` | ✅ | `ok()` |
| `app/routers/integrations.py` | 233 | lark_suite_validate | POST | `/lark_suite/validate` | ✅ | `ok({"success": True})` |
| `app/routers/integrations.py` | 239 | lark_suite_enable | POST | `/lark_suite/enable` | ✅ | `ok()` |
| `app/routers/integrations.py` | 245 | lark_suite_change_validate | POST | `/lark_suite/change/validate` | ✅ | `ok({"success": True})` |
| `app/routers/integrations.py` | 259 | service_integration_delete_path | GET | `/service/integration/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/integrations.py` | 259 | service_integration_delete_path | POST | `/service/integration/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/integrations.py` | 266 | service_integration_script_path | GET | `/service/integration/script/{pluginId}` | ✅ | `ok({"id": pluginId, "script": ""})` |
| `app/routers/integrations.py` | 266 | service_integration_script_path | POST | `/service/integration/script/{pluginId}` | ✅ | `ok({"id": pluginId, "script": ""})` |
| `app/routers/integrations.py` | 273 | service_integration_validate_path | GET | `/service/integration/validate/{id}` | ✅ | `ok({"id": id, "valid": True})` |
| `app/routers/integrations.py` | 273 | service_integration_validate_path | POST | `/service/integration/validate/{id}` | ✅ | `ok({"id": id, "valid": True})` |
| `app/routers/integrations.py` | 280 | service_integration_validate_org_path | GET | `/service/integration/validate/{plugin_id}/{org_id}` | ✅ | `ok({"pluginId": plugin_id, "organizationId": org_id, "valid": True})` |
| `app/routers/integrations.py` | 280 | service_integration_validate_org_path | POST | `/service/integration/validate/{plugin_id}/{org_id}` | ✅ | `ok({"pluginId": plugin_id, "organizationId": org_id, "valid": True})` |
| `app/routers/method_compat.py` | 212 | project_exec_task_item_page_post | POST | `/project/task-center/exec-task/item/page` | ✅ | `page_result([], len([]), current=current, page_size=page_size)` |
| `app/routers/method_compat.py` | 221 | project_exec_task_item_order_post | POST | `/project/task-center/exec-task/item/order` | ✅ | `ok(result)` |
| `app/routers/method_compat.py` | 232 | project_exec_task_batch_page_post | POST | `/project/task-center/exec-task/batch/page` | ✅ | `page_result([], len([]), current=current, page_size=page_size)` |
| `app/routers/method_compat.py` | 264 | system_exec_task_item_page_post | POST | `/system/task-center/exec-task/item/page` | ✅ | `page_result([], len([]), current=current, page_size=page_size)` |
| `app/routers/method_compat.py` | 273 | system_exec_task_item_order_post | POST | `/system/task-center/exec-task/item/order` | ✅ | `ok(result)` |
| `app/routers/method_compat.py` | 284 | system_exec_task_batch_page_post | POST | `/system/task-center/exec-task/batch/page` | ✅ | `page_result([], len([]), current=current, page_size=page_size)` |
| `app/routers/method_compat.py` | 316 | org_exec_task_item_page_post | POST | `/organization/task-center/exec-task/item/page` | ✅ | `page_result([], len([]), current=current, page_size=page_size)` |
| `app/routers/method_compat.py` | 325 | org_exec_task_item_order_post | POST | `/organization/task-center/exec-task/item/order` | ✅ | `ok(result)` |
| `app/routers/method_compat.py` | 336 | org_exec_task_batch_page_post | POST | `/organization/task-center/exec-task/batch/page` | ✅ | `page_result([], len([]), current=current, page_size=page_size)` |
| `app/routers/method_compat.py` | 358 | task_center_api_project_stop_post | POST | `/task/center/api/project/stop` | ✅ | `ok()` |
| `app/routers/method_compat.py` | 369 | api_scenario_step_get_get | GET | `/api/scenario/step/get` | ✅ | `ok(None)` |
| `app/routers/method_compat.py` | 424 | test_resource_pool_capacity_task_list_post | POST | `/test/resource/pool/capacity/task/list` | ✅ | `page_result([], len([]), current=current, page_size=page_size)` |
| `app/routers/method_compat.py` | 452 | project_file_list | GET | `/project/file/list` | — | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/notifications.py` | 225 | api_chat_list | GET | `/api/chat/list` | ✅ | `ok([])` |
| `app/routers/notifications.py` | 225 | api_chat_list | POST | `/api/chat/list` | ✅ | `ok([])` |
| `app/routers/other_compat.py` | 104 | api_doc_share_delete_get | GET | `/api/doc/share/delete` | ✅ | `ok()` |
| `app/routers/other_compat.py` | 110 | api_doc_share_detail_get | GET | `/api/doc/share/detail` | ✅ | `ok({
        "invalid": False,
        "allowExport": False,
        "…` |
| `app/routers/other_compat.py` | 136 | api_doc_share_get_detail_get | GET | `/api/doc/share/get-detail` | ✅ | `ok({})` |
| `app/routers/other_compat.py` | 188 | sso_callback_we_com_get | GET | `/sso/callback/we_com` | ✅ | `ok({"success": True})` |
| `app/routers/other_compat.py` | 194 | sso_callback_ding_talk_get | GET | `/sso/callback/ding_talk` | ✅ | `ok({"success": True})` |
| `app/routers/other_compat.py` | 200 | sso_callback_lark_get | GET | `/sso/callback/lark` | ✅ | `ok({"success": True})` |
| `app/routers/other_compat.py` | 206 | sso_callback_lark_suite_get | GET | `/sso/callback/lark_suite` | ✅ | `ok({"success": True})` |
| `app/routers/other_compat.py` | 216 | api_doc_share_module_count_post | POST | `/api/doc/share/module/count` | ✅ | `ok({})` |
| `app/routers/other_compat.py` | 244 | api_test_download | GET | `/api/test/download` | ✅ | `ok({"fileId": download_id, "fileName": file_name or "report.zip"})` |
| `app/routers/other_compat.py` | 250 | api_test_download_post | POST | `/api/test/download` | ✅ | `ok({"fileId": str(uuid.uuid4())})` |
| `app/routers/other_compat.py` | 262 | api_stop | POST | `/api/stop` | ✅ | `ok()` |
| `app/routers/other_compat.py` | 269 | api_stop_get | GET | `/api/stop` | ✅ | `ok()` |
| `app/routers/other_compat.py` | 280 | api_doc_share_add | POST | `/api/doc/share/add` | ✅ | `ok({"id": str(uuid.uuid4()), **body})` |
| `app/routers/other_compat.py` | 287 | api_doc_share_update | POST | `/api/doc/share/update` | ✅ | `ok()` |
| `app/routers/other_compat.py` | 294 | api_doc_share_delete | POST | `/api/doc/share/delete` | ✅ | `ok()` |
| `app/routers/other_compat.py` | 301 | api_doc_share_page | POST | `/api/doc/share/page` | ✅ | `page_result([], len([]), current=body.get("current", 1), page_size=bod…` |
| `app/routers/other_compat.py` | 308 | api_doc_share_check | POST | `/api/doc/share/check` | ✅ | `ok(True)` |
| `app/routers/other_compat.py` | 331 | api_doc_share_module_tree | GET | `/api/doc/share/module/tree` | ✅ | `ok([])` |
| `app/routers/other_compat.py` | 337 | api_doc_share_module_count | GET | `/api/doc/share/module/count` | ✅ | `ok({})` |
| `app/routers/other_compat.py` | 343 | api_doc_share_export | POST | `/api/doc/share/export` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/other_compat.py` | 350 | api_doc_share_download_file | GET | `/api/doc/share/download/file` | ✅ | `ok({"fileId": file_id, "fileName": "share"})` |
| `app/routers/other_compat.py` | 356 | api_doc_share_stop | POST | `/api/doc/share/stop` | ✅ | `ok()` |
| `app/routers/other_compat.py` | 363 | api_doc_share_get_detail | POST | `/api/doc/share/get-detail` | ✅ | `ok({})` |
| `app/routers/other_compat.py` | 370 | api_doc_share_plugin_script | POST | `/api/doc/share/plugin/script` | ✅ | `ok({})` |
| `app/routers/other_compat.py` | 382 | api_test_pool_option | GET | `/api/test/pool-option` | ✅ | `ok([])` |
| `app/routers/other_compat.py` | 388 | api_test_get_pool | GET | `/api/test/get-pool` | ✅ | `ok({})` |
| `app/routers/other_compat.py` | 394 | api_test_get_pool_trailing | GET | `/api/test/get-pool/` | ✅ | `ok({})` |
| `app/routers/other_compat.py` | 426 | api_test_environment | GET | `/api/test/environment` | ✅ | `ok({})` |
| `app/routers/other_compat.py` | 446 | api_test_common_script | GET | `/api/test/common-script` | ✅ | `ok([])` |
| `app/routers/other_compat.py` | 479 | api_test_custom_func_run | POST | `/api/test/custom/func/run` | ✅ | `ok({"result": "success"})` |
| `app/routers/other_compat.py` | 493 | task_center_api_project_stop | GET | `/task/center/api/project/stop` | ✅ | `ok()` |
| `app/routers/other_compat.py` | 499 | task_center_project_schedule_page | GET | `/task/center/project/schedule/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/other_compat.py` | 751 | sso_callback_we_com | POST | `/sso/callback/we_com` | ✅ | `ok({"success": True})` |
| `app/routers/other_compat.py` | 758 | sso_callback_ding_talk | POST | `/sso/callback/ding_talk` | ✅ | `ok({"success": True})` |
| `app/routers/other_compat.py` | 765 | sso_callback_lark | POST | `/sso/callback/lark` | ✅ | `ok({"success": True})` |
| `app/routers/other_compat.py` | 772 | sso_callback_lark_suite | POST | `/sso/callback/lark_suite` | ✅ | `ok({"success": True})` |
| `app/routers/other_compat.py` | 921 | dashboard_header_columns_option | GET | `/dashboard/header/columns-option` | ✅ | `ok([])` |
| `app/routers/other_compat.py` | 927 | dashboard_header_custom_field | GET | `/dashboard/header/custom-field` | ✅ | `ok([])` |
| `app/routers/other_compat.py` | 953 | dashboard_layout_edit | POST | `/dashboard/layout/edit` | ✅ | `ok()` |
| `app/routers/other_compat.py` | 960 | dashboard_member_get_project_member_option | GET | `/dashboard/member/get-project-member/option` | ✅ | `ok([])` |
| `app/routers/other_compat.py` | 966 | dashboard_plan_option | GET | `/dashboard/plan/option` | ✅ | `ok([])` |
| `app/routers/other_compat.py` | 977 | status_endpoint | GET | `/status` | ✅ | `ok({"status": "UP", "time": int(time.time())})` |
| `app/routers/other_compat.py` | 989 | doc_share_download_file_path | GET | `/api/doc/share/download/file/{share_id}/{file_id}` | ✅ | `ok({"share_id": share_id, "file_id": file_id})` |
| `app/routers/other_compat.py` | 989 | doc_share_download_file_path | POST | `/api/doc/share/download/file/{share_id}/{file_id}` | ✅ | `ok({"share_id": share_id, "file_id": file_id})` |
| `app/routers/other_compat.py` | 996 | doc_share_export_path | GET | `/api/doc/share/export/{share_id}` | ✅ | `ok({"id": share_id, "exported": True})` |
| `app/routers/other_compat.py` | 996 | doc_share_export_path | POST | `/api/doc/share/export/{share_id}` | ✅ | `ok({"id": share_id, "exported": True})` |
| `app/routers/other_compat.py` | 1003 | doc_share_stop_path | GET | `/api/doc/share/stop/{share_id}` | ✅ | `ok({"id": share_id, "stopped": True})` |
| `app/routers/other_compat.py` | 1003 | doc_share_stop_path | POST | `/api/doc/share/stop/{share_id}` | ✅ | `ok({"id": share_id, "stopped": True})` |
| `app/routers/other_compat.py` | 1028 | doc_share_plugin_script_path | GET | `/api/doc/share/plugin/script/{id}/{org_id}` | ✅ | `ok({"id": id, "org_id": org_id})` |
| `app/routers/other_compat.py` | 1053 | task_center_api_project_stop_path | GET | `/task/center/api/project/stop/{task_id}` | ✅ | `ok({"id": task_id, "stopped": True})` |
| `app/routers/other_compat.py` | 1059 | task_center_api_project_stop_type_path | GET | `/task/center/api/project/stop/{task_type}/{task_id}` | ✅ | `ok({"type": task_type, "id": task_id, "stopped": True})` |
| `app/routers/other_compat.py` | 1068 | api_stop_path | POST | `/api/stop/{task_id}` | ✅ | `ok({"id": task_id, "stopped": True})` |
| `app/routers/other_compat.py` | 1074 | api_stop_type_path | POST | `/api/stop/{task_type}/{task_id}` | ✅ | `ok({"type": task_type, "id": task_id, "stopped": True})` |
| `app/routers/other_compat.py` | 1080 | api_stop_get_path | GET | `/api/stop/{task_id}` | ✅ | `ok({"id": task_id, "stopped": True})` |
| `app/routers/other_compat.py` | 1086 | api_stop_get_type_path | GET | `/api/stop/{task_type}/{task_id}` | ✅ | `ok({"type": task_type, "id": task_id, "stopped": True})` |
| `app/routers/other_compat.py` | 1092 | api_test_mock | POST | `/api/test/mock` | ✅ | `ok(None)` |
| `app/routers/other_compat.py` | 1162 | api_doc_share_delete_path | GET | `/api/doc/share/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/other_compat.py` | 1162 | api_doc_share_delete_path | POST | `/api/doc/share/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/platform.py` | 36 | setting_get_platform_info | GET | `/setting/get/platform/info` | ✅ | `ok([])` |
| `app/routers/platform.py` | 64 | license_add | POST | `/license/add` | ✅ | `ok({"success": True})` |
| `app/routers/plugins.py` | 17 | plugin_delete_get | GET | `/plugin/delete` | ✅ | `ok()` |
| `app/routers/plugins.py` | 23 | plugin_options_post | POST | `/plugin/options` | ✅ | `ok([])` |
| `app/routers/plugins.py` | 29 | plugin_list | GET | `/plugin/list` | ✅ | `ok([])` |
| `app/routers/plugins.py` | 35 | plugin_add | POST | `/plugin/add` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/plugins.py` | 41 | plugin_update | POST | `/plugin/update` | ✅ | `ok()` |
| `app/routers/plugins.py` | 47 | plugin_delete | POST | `/plugin/delete` | ✅ | `ok()` |
| `app/routers/plugins.py` | 53 | plugin_options | GET | `/plugin/options` | ✅ | `ok([])` |
| `app/routers/plugins.py` | 59 | plugin_script_get | GET | `/plugin/script/get` | ✅ | `ok({})` |
| `app/routers/plugins.py` | 65 | plugin_image | GET | `/plugin/image/` | ✅ | `ok({})` |
| `app/routers/plugins.py` | 76 | plugin_image_path | GET | `/plugin/image/{plugin_id}` | ✅ | `ok({"id": plugin_id})` |
| `app/routers/project_compat_application.py` | 73 | project_application_resource_pool_get | GET | `/project/application/{suffix}/resource/pool/{project_id}` | ✅ | `ok([
        {"id": "local", "name": "本地资源池"},
        {"id": "default…` |
| `app/routers/project_compat_application.py` | 94 | project_application | GET | `/project/application/` | ✅ | `ok([])` |
| `app/routers/project_compat_application.py` | 100 | project_application_bug_platform | GET | `/project/application/bug/platform/` | ✅ | `ok([
        {"id": "jira", "name": "JIRA"},
        {"id": "tapd", "n…` |
| `app/routers/project_compat_application.py` | 100 | project_application_bug_platform | GET | `/project/application/bug/platform/{org_id}` | ✅ | `ok([
        {"id": "jira", "name": "JIRA"},
        {"id": "tapd", "n…` |
| `app/routers/project_compat_application.py` | 110 | project_application_bug_platform_info | GET | `/project/application/bug/platform/info/` | ✅ | `ok({"formItems": []})` |
| `app/routers/project_compat_application.py` | 110 | project_application_bug_platform_info | GET | `/project/application/bug/platform/info/{plugin_id}` | ✅ | `ok({"formItems": []})` |
| `app/routers/project_compat_application.py` | 135 | project_application_case_platform | GET | `/project/application/case/platform/` | ✅ | `ok([
        {"id": "tapd", "name": "TAPD"},
        {"id": "jira", "n…` |
| `app/routers/project_compat_application.py` | 135 | project_application_case_platform | GET | `/project/application/case/platform/{org_id}` | ✅ | `ok([
        {"id": "tapd", "name": "TAPD"},
        {"id": "jira", "n…` |
| `app/routers/project_compat_application.py` | 144 | project_application_case_platform_info | GET | `/project/application/case/platform/info/` | ✅ | `ok({"formItems": []})` |
| `app/routers/project_compat_application.py` | 144 | project_application_case_platform_info | GET | `/project/application/case/platform/info/{plugin_id}` | ✅ | `ok({"formItems": []})` |
| `app/routers/project_compat_application.py` | 238 | project_application_update | POST | `/project/application/update/` | ✅ | `ok()` |
| `app/routers/project_compat_application.py` | 342 | project_application_validate | POST | `/project/application/validate/` | ✅ | `ok()` |
| `app/routers/project_compat_environment.py` | 62 | project_environment_get | GET | `/project/environment/get` | ✅ | `ok(env or {})` |
| `app/routers/project_compat_environment.py` | 68 | project_environment_get_trailing | GET | `/project/environment/get/` | ✅ | `ok(env or {})` |
| `app/routers/project_compat_environment.py` | 86 | project_environment_delete | POST | `/project/environment/delete` | ✅ | `ok()` |
| `app/routers/project_compat_environment.py` | 91 | project_environment_delete_del | DELETE | `/project/environment/delete/` | ✅ | `ok()` |
| `app/routers/project_compat_environment.py` | 96 | project_environment_edit_pos | POST | `/project/environment/edit/pos` | ✅ | `ok()` |
| `app/routers/project_compat_environment.py` | 103 | project_environment_export | GET | `/project/environment/export` | ✅ | `ok({"fileName": "environment.json", "content": "{}"})` |
| `app/routers/project_compat_environment.py` | 121 | project_environment_database_validate | POST | `/project/environment/database/validate` | ✅ | `ok({"success": True, "message": "连接成功"}); fail("数据库连接信息不完整", 400)` |
| `app/routers/project_compat_environment.py` | 226 | project_environment_group_get | GET | `/project/environment/group/get` | ✅ | `ok({})` |
| `app/routers/project_compat_environment.py` | 231 | project_environment_group_get_trailing | GET | `/project/environment/group/get/` | ✅ | `ok({})` |
| `app/routers/project_compat_environment.py` | 236 | project_environment_group_delete | POST | `/project/environment/group/delete/` | ✅ | `ok({"id": id, "deleted": result})` |
| `app/routers/project_compat_environment.py` | 244 | project_environment_group_edit_pos | POST | `/project/environment/group/edit/pos` | ✅ | `ok()` |
| `app/routers/project_compat_environment.py` | 258 | project_environment_scripts | GET | `/project/environment/scripts/` | ✅ | `ok([])` |
| `app/routers/project_compat_environment.py` | 266 | project_environment_group_delete_path | GET | `/project/environment/group/delete/{group_id}` | ✅ | `ok({"id": group_id, "deleted": result})` |
| `app/routers/project_compat_environment.py` | 287 | project_environment_scripts_path | GET | `/project/environment/scripts/{project_id}` | ✅ | `ok([])` |
| `app/routers/project_compat_environment.py` | 382 | project_environment_get_path | GET | `/project/environment/get/{env_id}` | ✅ | `ok(frontend_env); fail("环境不存在", code=404)` |
| `app/routers/project_compat_environment.py` | 393 | project_environment_delete_path | POST | `/project/environment/delete/{env_id}` | ✅ | `ok(None)` |
| `app/routers/project_compat_environment.py` | 393 | project_environment_delete_path | GET | `/project/environment/delete/{env_id}` | ✅ | `ok(None)` |
| `app/routers/project_compat_environment.py` | 441 | project_environment_get_options | GET | `/project/environment/get-options` | ✅ | `ok([
        {"id": e.get("id"), "name": e.get("name")} for e in envs
…` |
| `app/routers/project_compat_environment.py` | 449 | project_environment_get_options_by_project | GET | `/project/environment/get-options/{project_id}` | ✅ | `ok([
        {"id": e.get("id"), "name": e.get("name")} for e in envs
…` |
| `app/routers/project_compat_extra.py` | 75 | project_custom_field_delete_get | GET | `/project/custom/field/delete` | ✅ | `ok()` |
| `app/routers/project_compat_extra.py` | 80 | project_status_flow_status_delete_get | GET | `/project/status/flow/setting/status/delete` | ✅ | `ok()` |
| `app/routers/project_compat_extra.py` | 143 | project_template_enable_config | POST | `/project/template/enable/config` | ✅ | `ok()` |
| `app/routers/project_compat_extra.py` | 149 | project_template_set_default | POST | `/project/template/set-default` | ✅ | `ok()` |
| `app/routers/project_compat_extra.py` | 155 | project_template_img_preview | POST | `/project/template/img/preview` | ✅ | `ok({})` |
| `app/routers/project_compat_extra.py` | 161 | project_template_upload_temp_img | POST | `/project/template/upload/temp/img` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/project_compat_extra.py` | 401 | project_custom_func_columns_option | GET | `/project/custom/func/columns-option/` | ✅ | `ok([])` |
| `app/routers/project_compat_extra.py` | 406 | project_custom_func_history_page | GET | `/project/custom/func/history/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/project_compat_extra.py` | 411 | project_custom_func_history_page_post | POST | `/project/custom/func/history/page` | ✅ | `page_result([], len([]), current=current, page_size=page_size)` |
| `app/routers/project_compat_extra2.py` | 244 | project_global_params_delete | POST | `/project/global/params/delete` | — | `ok({"deleted": deleted})` |
| `app/routers/project_compat_extra2.py` | 253 | project_global_params_delete_by_id | POST | `/project/global/params/delete/{param_id}` | — | `ok({"deleted": deleted})` |
| `app/routers/project_compat_extra2.py` | 253 | project_global_params_delete_by_id | GET | `/project/global/params/delete/{param_id}` | — | `ok({"deleted": deleted})` |
| `app/routers/project_compat_extra2.py` | 259 | project_global_params_get | GET | `/project/global/params/get` | ✅ | `ok({})` |
| `app/routers/project_compat_extra2.py` | 264 | project_global_params_get_trailing | GET | `/project/global/params/get/` | ✅ | `ok({})` |
| `app/routers/project_compat_extra2.py` | 310 | project_global_params_export | GET | `/project/global/params/export/` | ✅ | `ok({"fileName": "params.json"})` |
| `app/routers/project_compat_extra2.py` | 524 | project_has_permission | GET | `/project/has-permission` | ✅ | `ok({"hasPermission": True})` |
| `app/routers/project_compat_extra2.py` | 781 | project_list_options | GET | `/project/list/options` | ✅ | `ok([
        {"id": "default", "name": "默认项目"},
    ])` |
| `app/routers/project_compat_file.py` | 59 | project_file_type_get | GET | `/project/file/type` | ✅ | `ok([
        "FILE", "IMAGE", "JAR", "XLS", "XLSX", "CSV",
        "DO…` |
| `app/routers/project_compat_file.py` | 67 | project_file_repository_pull_file_get | GET | `/project/file/repository/pull-file` | ✅ | `ok()` |
| `app/routers/project_compat_file.py` | 72 | project_file_association_list_get | GET | `/project/file/association/list` | ✅ | `ok([])` |
| `app/routers/project_compat_file.py` | 77 | project_file_download_post | POST | `/project/file/download` | ✅ | `ok({"fileId": file_id})` |
| `app/routers/project_compat_file.py` | 168 | project_file_re_upload | POST | `/project/file/re-upload` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/project_compat_file.py` | 173 | project_file_update | POST | `/project/file/update` | ✅ | `ok()` |
| `app/routers/project_compat_file.py` | 263 | project_file_batch_download | POST | `/project/file/batch-download` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/project_compat_file.py` | 268 | project_file_download | GET | `/project/file/download` | ✅ | `ok({"fileId": file_id})` |
| `app/routers/project_compat_file.py` | 273 | project_file_jar_file_status | POST | `/project/file/jar-file-status` | ✅ | `ok([])` |
| `app/routers/project_compat_file.py` | 305 | project_file_repository_add | POST | `/project/file/repository/add-repository` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/project_compat_file.py` | 310 | project_file_repository_update | POST | `/project/file/repository/update-repository` | ✅ | `ok()` |
| `app/routers/project_compat_file.py` | 315 | project_file_repository_connect | POST | `/project/file/repository/connect` | ✅ | `ok()` |
| `app/routers/project_compat_file.py` | 320 | project_file_repository_info | GET | `/project/file/repository/info` | ✅ | `ok({})` |
| `app/routers/project_compat_file.py` | 325 | project_file_repository_list | GET | `/project/file/repository/list` | ✅ | `ok([])` |
| `app/routers/project_compat_file.py` | 330 | project_file_repository_file_type | GET | `/project/file/repository/file-type` | ✅ | `ok([])` |
| `app/routers/project_compat_file.py` | 335 | project_file_repository_add_file | POST | `/project/file/repository/add-file` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/project_compat_file.py` | 340 | project_file_repository_pull_file | POST | `/project/file/repository/pull-file` | ✅ | `ok()` |
| `app/routers/project_compat_file.py` | 345 | project_file_association_list | POST | `/project/file/association/list` | ✅ | `ok([])` |
| `app/routers/project_compat_file.py` | 350 | project_file_association_delete | POST | `/project/file/association/delete` | ✅ | `ok()` |
| `app/routers/project_compat_file.py` | 355 | project_file_association_upgrade | POST | `/project/file/association/upgrade` | ✅ | `ok()` |
| `app/routers/project_compat_file.py` | 360 | project_file_file_version | GET | `/project/file/file-version` | ✅ | `ok([])` |
| `app/routers/project_compat_file.py` | 365 | project_file_module_count | GET | `/project/file/module/count` | ✅ | `ok(counts)` |
| `app/routers/project_compat_file.py` | 373 | project_file_association_upgrade_path | GET | `/project/file/association/upgrade/{file_id}` | ✅ | `ok({"id": file_id, "upgraded": True})` |
| `app/routers/project_compat_file.py` | 373 | project_file_association_upgrade_path | POST | `/project/file/association/upgrade/{file_id}` | ✅ | `ok({"id": file_id, "upgraded": True})` |
| `app/routers/project_compat_file.py` | 379 | project_file_jar_status_path | GET | `/project/file/jar-file-status/{file_id}/{project_id}` | ✅ | `ok({"file_id": file_id, "project_id": project_id})` |
| `app/routers/project_compat_file.py` | 379 | project_file_jar_status_path | POST | `/project/file/jar-file-status/{file_id}/{project_id}` | ✅ | `ok({"file_id": file_id, "project_id": project_id})` |
| `app/routers/project_compat_member.py` | 159 | project_member_comment_user_option | GET | `/project/member/comment/user-option` | ✅ | `ok([])` |
| `app/routers/project_compat_member.py` | 174 | project_get_member_option | GET | `/project/get-member/option` | ✅ | `ok([])` |
| `app/routers/project_compat_member.py` | 247 | project_member_comment_user_option_path | GET | `/project/member/comment/user-option/{project_id}` | ✅ | `ok([])` |
| `app/routers/reports_compat.py` | 30 | api_report_case_export_by_id | POST | `/api/report/case/export/{report_id}` | ✅ | `ok()` |
| `app/routers/reports_compat.py` | 36 | api_report_case_get_trailing | POST | `/api/report/case/get/` | ✅ | `ok({"id": "", "name": "接口用例报告", "status": "SUCCESS"})` |
| `app/routers/reports_compat.py` | 42 | api_report_case_get_detail_trailing | POST | `/api/report/case/get/detail/` | ✅ | `ok({"steps": []})` |
| `app/routers/reports_compat.py` | 48 | api_report_case_share_detail | POST | `/api/report/case/share/detail` | ✅ | `ok({"steps": []})` |
| `app/routers/reports_compat.py` | 54 | api_report_scenario_share_detail | POST | `/api/report/scenario/share/detail` | ✅ | `ok({"steps": []})` |
| `app/routers/reports_compat.py` | 60 | api_report_share_get_post | POST | `/api/report/share/get` | ✅ | `ok({})` |
| `app/routers/reports_compat.py` | 66 | api_report_case_task_report | POST | `/api/report/case/task-report` | ✅ | `ok([])` |
| `app/routers/reports_compat.py` | 72 | api_report_scenario_task_report | POST | `/api/report/scenario/task-report` | ✅ | `ok([])` |
| `app/routers/reports_compat.py` | 78 | api_report_scenario_task_step | POST | `/api/report/scenario/task-step` | ✅ | `ok([])` |
| `app/routers/reports_compat.py` | 84 | api_report_case_export | POST | `/api/report/case/export` | ✅ | `ok({"id": str(uuid.uuid4()), "fileName": "report.zip"})` |
| `app/routers/reports_compat.py` | 90 | api_report_case_batch_export | POST | `/api/report/case/batch-export` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/reports_compat.py` | 107 | api_report_scenario_export | POST | `/api/report/scenario/export` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/reports_compat.py` | 113 | api_report_scenario_batch_export | POST | `/api/report/scenario/batch-export` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/reports_compat.py` | 349 | api_report_scenario_task_step_path | GET | `/api/report/scenario/task-step/{task_id}` | ✅ | `ok({
        "task_id": task_id,
        "status": normalize_status("C…` |
| `app/routers/reports_compat.py` | 423 | api_report_case_rename | POST | `/api/report/case/rename` | ✅ | `ok(None)` |
| `app/routers/reports_compat.py` | 429 | api_report_scenario_rename | POST | `/api/report/scenario/rename` | ✅ | `ok(None)` |
| `app/routers/reports_compat.py` | 435 | api_report_case_delete | POST | `/api/report/case/delete` | ✅ | `ok(None)` |
| `app/routers/reports_compat.py` | 441 | api_report_case_batch_delete | POST | `/api/report/case/batch/delete` | ✅ | `ok(None)` |
| `app/routers/reports_compat.py` | 447 | api_report_scenario_delete | POST | `/api/report/scenario/delete` | ✅ | `ok(None)` |
| `app/routers/reports_compat.py` | 453 | api_report_scenario_batch_delete | POST | `/api/report/scenario/batch/delete` | ✅ | `ok(None)` |
| `app/routers/reports_compat.py` | 860 | api_report_share_get_time | POST | `/api/report/share/get-share-time` | ✅ | `ok(0)` |
| `app/routers/reports_compat.py` | 866 | api_report_case_delete_get | GET | `/api/report/case/delete/{report_id}` | ✅ | `ok(None)` |
| `app/routers/reports_compat.py` | 872 | api_report_scenario_delete_get | GET | `/api/report/scenario/delete/{report_id}` | ✅ | `ok(None)` |
| `app/routers/reports_compat.py` | 902 | api_report_share_get_time_path | GET | `/api/report/share/get-share-time/{project_id}` | ✅ | `ok(0)` |
| `app/routers/system.py` | 17 | index | GET | `/` | ✅ | `HTMLResponse("<h1>Test Generation Agent Toolkit</h1><p>API is running.…` |
| `app/routers/system.py` | 28 | health | GET | `/health` | — | `ok({
        "status": "ok",
        "version": "0.2.0",
        "serv…` |
| `app/routers/system_compat.py` | 49 | organization_custom_field_delete_get | GET | `/organization/custom/field/delete` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 54 | organization_status_flow_status_delete_get | GET | `/organization/status/flow/setting/status/delete` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 59 | system_authsource_delete_get | GET | `/system/authsource/delete` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 64 | system_user_check_invite_get | GET | `/system/user/check-invite` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 69 | user_api_key_validate_get | GET | `/user/api/key/validate` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 110 | system_parameter_edit_upload_config_post | POST | `/system/parameter/edit/upload-config` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 141 | system_parameter_save_base_url | GET | `/system/parameter/save/base-url` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 146 | user_api_key_add_get | GET | `/user/api/key/add` | ✅ | `ok({"apiKey": api_key})` |
| `app/routers/system_compat.py` | 277 | organization_project_delete_post | POST | `/organization/project/delete/` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 282 | organization_project_remove_member | POST | `/organization/project/remove-member/` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 287 | organization_project_user_list | GET | `/organization/project/user-list` | ✅ | `ok([])` |
| `app/routers/system_compat.py` | 292 | organization_project_user_admin_list | GET | `/organization/project/user-admin-list/` | ✅ | `ok([])` |
| `app/routers/system_compat.py` | 297 | organization_project_user_member_list | GET | `/organization/project/user-member-list/` | ✅ | `ok([])` |
| `app/routers/system_compat.py` | 302 | organization_project_pool_options | GET | `/organization/project/pool-options` | ✅ | `ok([])` |
| `app/routers/system_compat.py` | 416 | organization_template_enable_config | POST | `/organization/template/enable/config` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 422 | organization_template_set_default | POST | `/organization/template/set-default` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 428 | organization_template_img_preview | POST | `/organization/template/img/preview` | ✅ | `ok({})` |
| `app/routers/system_compat.py` | 434 | organization_template_upload_temp_img | POST | `/organization/template/upload/temp/img` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/system_compat.py` | 441 | organization_custom_field_add | POST | `/organization/custom/field/add` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/system_compat.py` | 447 | organization_custom_field_update | POST | `/organization/custom/field/update` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 453 | organization_custom_field_delete | POST | `/organization/custom/field/delete` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 459 | organization_custom_field_get | GET | `/organization/custom/field/get` | ✅ | `ok({})` |
| `app/routers/system_compat.py` | 464 | organization_custom_field_list | GET | `/organization/custom/field/list` | ✅ | `ok([])` |
| `app/routers/system_compat.py` | 802 | system_get | GET | `/system/get` | ✅ | `ok({})` |
| `app/routers/system_compat.py` | 807 | system_get_trailing | GET | `/system/get/` | ✅ | `ok({})` |
| `app/routers/system_compat.py` | 1047 | system_project_pool_options | GET | `/system/project/pool-options` | ✅ | `ok([])` |
| `app/routers/system_compat.py` | 1066 | system_project_remove_member | POST | `/system/project/remove-member/` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 1073 | system_user_get_organization | GET | `/system/user/get/organization` | ✅ | `ok([])` |
| `app/routers/system_compat.py` | 1078 | system_user_get_project | GET | `/system/user/get/project` | ✅ | `ok([])` |
| `app/routers/system_compat.py` | 1083 | system_user_add_org_member | POST | `/system/user/add-org-member` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 1089 | system_user_add_project_member | POST | `/system/user/add-project-member` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 1095 | system_user_add_batch_user_role | POST | `/system/user/add/batch/user-role` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 1267 | system_parameter_get_email_info | GET | `/system/parameter/get/email-info` | ✅ | `ok({})` |
| `app/routers/system_compat.py` | 1272 | system_parameter_edit_email_info | POST | `/system/parameter/edit/email-info` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 1278 | system_parameter_test_email | POST | `/system/parameter/test/email` | ✅ | `ok({"success": True})` |
| `app/routers/system_compat.py` | 1284 | system_parameter_get_clean_config | GET | `/system/parameter/get/clean-config` | ✅ | `ok({})` |
| `app/routers/system_compat.py` | 1289 | system_parameter_edit_clean_config | POST | `/system/parameter/edit/clean-config` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 1295 | system_parameter_edit_upload_config | GET | `/system/parameter/edit/upload-config` | ✅ | `ok({})` |
| `app/routers/system_compat.py` | 1302 | system_authsource_list | GET | `/system/authsource/list` | ✅ | `ok([])` |
| `app/routers/system_compat.py` | 1307 | system_authsource_list_post | POST | `/system/authsource/list` | ✅ | `ok([])` |
| `app/routers/system_compat.py` | 1312 | system_authsource_add | POST | `/system/authsource/add` | ✅ | `ok({"id": str(uuid.uuid4())})` |
| `app/routers/system_compat.py` | 1318 | system_authsource_update | POST | `/system/authsource/update` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 1324 | system_authsource_delete | POST | `/system/authsource/delete` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 1330 | system_authsource_get | GET | `/system/authsource/get` | ✅ | `ok({})` |
| `app/routers/system_compat.py` | 1335 | system_authsource_update_status | POST | `/system/authsource/update/status` | ✅ | `ok()` |
| `app/routers/system_compat.py` | 1341 | system_authsource_ldap_test_connect | POST | `/system/authsource/ldap/test-connect` | ✅ | `ok({"success": True})` |
| `app/routers/system_compat.py` | 1347 | system_authsource_ldap_test_login | POST | `/system/authsource/ldap/test-login` | ✅ | `ok({"success": True})` |
| `app/routers/system_compat_extra.py` | 35 | organization_template_disable | POST | `/organization/template/disable` | ✅ | `ok()` |
| `app/routers/system_compat_extra.py` | 42 | org_custom_field_list_path | GET | `/organization/custom/field/list/{organization_id}/{scene}` | ✅ | `ok([])` |
| `app/routers/system_compat_extra.py` | 42 | org_custom_field_list_path | POST | `/organization/custom/field/list/{organization_id}/{scene}` | ✅ | `ok([])` |
| `app/routers/system_compat_extra.py` | 75 | org_template_disable_path | GET | `/organization/template/disable/{template_id}/{organization_id}` | ✅ | `ok({"id": template_id, "organization_id": organization_id, "disabled":…` |
| `app/routers/system_compat_extra.py` | 75 | org_template_disable_path | POST | `/organization/template/disable/{template_id}/{organization_id}` | ✅ | `ok({"id": template_id, "organization_id": organization_id, "disabled":…` |
| `app/routers/system_compat_extra.py` | 108 | user_platform_validate_path | GET | `/user/platform/validate/{platform}/{user_id}` | ✅ | `ok({"platform": platform, "user_id": user_id})` |
| `app/routers/system_compat_extra.py` | 108 | user_platform_validate_path | POST | `/user/platform/validate/{platform}/{user_id}` | ✅ | `ok({"platform": platform, "user_id": user_id})` |
| `app/routers/system_compat_extra.py` | 129 | api_org_project_pool_options_post | POST | `/organization/project/pool-options` | ✅ | `ok([])` |
| `app/routers/system_compat_extra.py` | 189 | system_org_get_option_path | GET | `/system/organization/get-option/{source_id}` | ✅ | `ok([])` |
| `app/routers/system_compat_extra.py` | 194 | org_project_delete_path | GET | `/organization/project/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/system_compat_extra.py` | 199 | org_project_revoke_path | GET | `/organization/project/revoke/{id}` | ✅ | `ok({"id": id, "revoked": True})` |
| `app/routers/system_compat_extra.py` | 204 | org_project_remove_member_path | GET | `/organization/project/remove-member/{project_id}/{user_id}` | ✅ | `ok({"project_id": project_id, "user_id": user_id, "removed": True})` |
| `app/routers/system_compat_extra.py` | 209 | org_project_user_member_list_path | GET | `/organization/project/user-member-list/{organization_id}/{project_id}` | ✅ | `ok([])` |
| `app/routers/system_compat_extra.py` | 304 | organization_custom_field_delete_path | GET | `/organization/custom/field/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/system_compat_extra.py` | 304 | organization_custom_field_delete_path | POST | `/organization/custom/field/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/system_compat_extra.py` | 310 | organization_custom_field_get_path | GET | `/organization/custom/field/get/{id}` | ✅ | `ok({"id": id, "field": None})` |
| `app/routers/system_compat_extra.py` | 310 | organization_custom_field_get_path | POST | `/organization/custom/field/get/{id}` | ✅ | `ok({"id": id, "field": None})` |
| `app/routers/system_compat_extra.py` | 323 | system_authsource_delete_path | GET | `/system/authsource/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/system_compat_extra.py` | 323 | system_authsource_delete_path | POST | `/system/authsource/delete/{id}` | ✅ | `ok({"id": id, "deleted": True})` |
| `app/routers/system_compat_extra.py` | 387 | user_platform_get_path | GET | `/user/platform/get/{orgId}` | ✅ | `ok({"id": orgId, "platforms": []})` |
| `app/routers/system_compat_extra.py` | 387 | user_platform_get_path | POST | `/user/platform/get/{orgId}` | ✅ | `ok({"id": orgId, "platforms": []})` |
| `app/routers/system_compat_userrole.py` | 349 | user_role_project_get_member_option_old | GET | `/user/role/project/get-member/option/` | ✅ | `ok([])` |
| `app/routers/system_compat_userrole.py` | 547 | user_platform_get | GET | `/user/platform/get` | ✅ | `ok({})` |
| `app/routers/system_compat_userrole.py` | 552 | user_platform_save | POST | `/user/platform/save` | ✅ | `ok()` |
| `app/routers/system_compat_userrole.py` | 557 | user_platform_switch_option | GET | `/user/platform/switch-option` | ✅ | `ok([])` |
| `app/routers/system_compat_userrole.py` | 562 | user_platform_account_info | GET | `/user/platform/account/info` | ✅ | `ok({})` |
| `app/routers/system_compat_userrole.py` | 567 | user_platform_validate | POST | `/user/platform/validate` | ✅ | `ok({"success": True})` |
| `app/routers/system_compat_userrole.py` | 574 | user_api_key_update | POST | `/user/api/key/update` | ✅ | `ok({"accessKey": str(uuid.uuid4()).replace("-", ""),
                "…` |
| `app/routers/system_compat_userrole.py` | 580 | user_api_key_validate | POST | `/user/api/key/validate` | ✅ | `ok({"valid": True})` |
| `app/routers/task_center.py` | 156 | proj_task_center_statistics_post | POST | `/project/task-center/exec-task/statistics` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 161 | project_task_center_exec_task_page | GET | `/project/task-center/exec-task/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/task_center.py` | 166 | project_task_center_exec_task_item_page | GET | `/project/task-center/exec-task/item/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/task_center.py` | 171 | project_task_center_exec_task_item_order | GET | `/project/task-center/exec-task/item/order` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 176 | project_task_center_exec_task_statistics | GET | `/project/task-center/exec-task/statistics` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 209 | project_task_center_exec_task_batch_page | GET | `/project/task-center/exec-task/batch/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/task_center.py` | 246 | project_task_center_schedule_page | GET | `/project/task-center/schedule/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/task_center.py` | 290 | project_task_center_resource_pool_options | GET | `/project/task-center/resource-pool/options` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 457 | org_task_center_statistics_post | POST | `/organization/task-center/exec-task/statistics` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 462 | sys_task_center_statistics_post | POST | `/system/task-center/exec-task/statistics` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 467 | sys_task_center_resource_pool_status_post | POST | `/system/task-center/resource-pool/status` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 472 | organization_task_center_exec_task_page | GET | `/organization/task-center/exec-task/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/task_center.py` | 477 | organization_task_center_exec_task_item_page | GET | `/organization/task-center/exec-task/item/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/task_center.py` | 482 | organization_task_center_exec_task_item_order | GET | `/organization/task-center/exec-task/item/order` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 487 | organization_task_center_exec_task_statistics | GET | `/organization/task-center/exec-task/statistics` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 519 | organization_task_center_exec_task_batch_page | GET | `/organization/task-center/exec-task/batch/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/task_center.py` | 556 | organization_task_center_schedule_page | GET | `/organization/task-center/schedule/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/task_center.py` | 600 | organization_task_center_project_options | GET | `/organization/task-center/project/options` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 605 | organization_task_center_resource_pool_options | GET | `/organization/task-center/resource-pool/options` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 610 | system_task_center_exec_task_page | GET | `/system/task-center/exec-task/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/task_center.py` | 615 | system_task_center_exec_task_item_page | GET | `/system/task-center/exec-task/item/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/task_center.py` | 620 | system_task_center_exec_task_item_order | GET | `/system/task-center/exec-task/item/order` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 625 | system_task_center_exec_task_statistics | GET | `/system/task-center/exec-task/statistics` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 658 | system_task_center_exec_task_batch_page | GET | `/system/task-center/exec-task/batch/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/task_center.py` | 695 | system_task_center_schedule_page | GET | `/system/task-center/schedule/page` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/task_center.py` | 739 | system_task_center_organization_options | GET | `/system/task-center/organization/options` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 744 | system_task_center_project_options | GET | `/system/task-center/project/options` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 749 | system_task_center_resource_pool_options | GET | `/system/task-center/resource-pool/options` | ✅ | `ok([])` |
| `app/routers/task_center.py` | 754 | system_task_center_resource_pool_status | GET | `/system/task-center/resource-pool/status` | ✅ | `ok([])` |
| `app/routers/test_resources.py` | 17 | test_resource_pool_delete_get | GET | `/test/resource/pool/delete` | ✅ | `ok()` |
| `app/routers/test_resources.py` | 23 | test_resource_pool_capacity_detail_post | POST | `/test/resource/pool/capacity/detail` | ✅ | `ok({})` |
| `app/routers/test_resources.py` | 149 | test_plan_functional_case_tree_post | POST | `/test-plan/functional/case/tree` | ✅ | `ok([])` |
| `app/routers/test_resources.py` | 282 | test_resource_pool_capacity_task_list | GET | `/test/resource/pool/capacity/task/list` | ✅ | `page_result([], len([]), current=1, page_size=10)` |
| `app/routers/test_resources.py` | 301 | test_plan_execute_user_option | GET | `/test-plan-execute/user-option` | ✅ | `ok([])` |
| `app/routers/test_resources.py` | 307 | test_plan_api_case_run | POST | `/test-plan/api/case/run` | ✅ | `ok()` |
| `app/routers/test_resources.py` | 314 | test_plan_api_case_disassociate_bug | POST | `/test-plan/api/case/disassociate/bug` | ✅ | `ok()` |
| `app/routers/test_resources.py` | 321 | test_plan_api_scenario_run | POST | `/test-plan/api/scenario/run` | ✅ | `ok()` |
| `app/routers/test_resources.py` | 328 | test_plan_api_scenario_disassociate_bug | POST | `/test-plan/api/scenario/disassociate/bug` | ✅ | `ok()` |
| `app/routers/test_resources.py` | 335 | test_plan_report_get_task | POST | `/test-plan/report/get-task` | ✅ | `ok({})` |
| `app/routers/test_resources.py` | 378 | test_plan_report_get_result_path | GET | `/test-plan/report/get-result/{plan_id}` | ✅ | `ok({"plan_id": plan_id, "status": "SUCCESS"})` |
| `app/routers/test_resources.py` | 395 | test_plan_group_list_path | GET | `/test-plan/group-list/{project_id}` | ✅ | `ok({"project_id": project_id})` |
| `app/routers/test_resources.py` | 411 | test_resource_pool_delete_path | GET | `/test/resource/pool/delete/{poolId}` | ✅ | `ok({"id": poolId, "deleted": True})` |
| `app/routers/test_resources.py` | 411 | test_resource_pool_delete_path | POST | `/test/resource/pool/delete/{poolId}` | ✅ | `ok({"id": poolId, "deleted": True})` |
| `app/test_plan/router.py` | 649 | test_plan_batch_move | POST | `/test-plan/batch-move` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 655 | test_plan_sort | POST | `/test-plan/sort` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 701 | test_plan_edit_follower | POST | `/test-plan/edit/follower` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 805 | test_plan_functional_case_module_count | POST | `/test-plan/functional/case/module/count` | ✅ | `ok([])` |
| `app/test_plan/router.py` | 811 | test_plan_functional_case_tree | GET | `/test-plan/functional/case/tree` | ✅ | `ok([
        {"id": "root", "name": "全部用例", "type": "MODULE", "childre…` |
| `app/test_plan/router.py` | 819 | test_plan_functional_case_sort | POST | `/test-plan/functional/case/sort` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 855 | test_plan_functional_case_batch_run | POST | `/test-plan/functional/case/batch/run` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 861 | test_plan_functional_case_batch_move | POST | `/test-plan/functional/case/batch/move` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 867 | test_plan_functional_case_associate_bug_page | POST | `/test-plan/functional/case/has/associate/bug/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/test_plan/router.py` | 894 | test_plan_functional_case_associate_bug | POST | `/test-plan/functional/case/associate/bug` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 900 | test_plan_functional_case_disassociate_bug | POST | `/test-plan/functional/case/disassociate/bug` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 906 | test_plan_functional_case_user_option | GET | `/test-plan/functional/case/user-option` | ✅ | `ok([
        {"id": "admin", "name": "admin"},
    ])` |
| `app/test_plan/router.py` | 914 | test_plan_functional_case_batch_update_executor | POST | `/test-plan/functional/case/batch/update/executor` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 920 | test_plan_functional_case_exec_history | POST | `/test-plan/functional/case/exec/history` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/test_plan/router.py` | 929 | test_plan_his_page | POST | `/test-plan/his/page` | ✅ | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/test_plan/router.py` | 1165 | test_plan_report_batch_delete | POST | `/test-plan/report/batch-delete` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 1540 | test_plan_report_share_get_share_time | GET | `/test-plan/report/share/get-share-time` | ✅ | `ok(86400)` |
| `app/test_plan/router.py` | 1540 | test_plan_report_share_get_share_time | GET | `/test-plan/report/share/get-share-time/{report_id}` | ✅ | `ok(86400)` |
| `app/test_plan/router.py` | 1546 | test_plan_report_detail_edit | POST | `/test-plan/report/detail/edit` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 1811 | test_plan_report_detail_functional_case_step | POST | `/test-plan/report/detail/functional/case/step` | ✅ | `ok([])` |
| `app/test_plan/router.py` | 1811 | test_plan_report_detail_functional_case_step | GET | `/test-plan/report/detail/functional/case/step/{report_id}` | ✅ | `ok([])` |
| `app/test_plan/router.py` | 1817 | test_plan_report_export | POST | `/test-plan/report/export` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 1823 | test_plan_report_batch_export | POST | `/test-plan/report/batch-export` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 1846 | test_plan_report_get_result | POST | `/test-plan/report/get-result` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 1852 | test_plan_report_preview_md | POST | `/test-plan/report/preview/md` | ✅ | `ok("")` |
| `app/test_plan/router.py` | 1858 | test_plan_report_preview_md_get | GET | `/test-plan/report/preview/md` | ✅ | `ok("")` |
| `app/test_plan/router.py` | 1864 | test_plan_report_upload_md_file | POST | `/test-plan/report/upload/md/file` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 1958 | test_plan_functional_case_user_option_get | GET | `/test-plan/functional/case/user-option/{project_id}` | ✅ | `ok([
        {"id": "admin", "name": "admin"},
    ])` |
| `app/test_plan/router.py` | 1983 | test_plan_functional_case_disassociate_bug_get | GET | `/test-plan/functional/case/disassociate/bug/{rel_id}` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 1989 | test_plan_api_case_run_get | GET | `/test-plan/api/case/run/{case_id}` | ✅ | `ok({
        "status": "success",
        "result": "SUCCESS",
    })` |
| `app/test_plan/router.py` | 2026 | test_plan_api_case_tree | POST | `/test-plan/api/case/tree` | ✅ | `ok([
        {"id": "root", "name": "全部接口用例", "type": "MODULE", "child…` |
| `app/test_plan/router.py` | 2034 | test_plan_api_case_module_count | POST | `/test-plan/api/case/module/count` | ✅ | `ok([])` |
| `app/test_plan/router.py` | 2040 | test_plan_api_case_sort | POST | `/test-plan/api/case/sort` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2046 | test_plan_api_case_disassociate | POST | `/test-plan/api/case/disassociate` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2052 | test_plan_api_case_batch_disassociate | POST | `/test-plan/api/case/batch/disassociate` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2058 | test_plan_api_case_batch_run | POST | `/test-plan/api/case/batch/run` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2064 | test_plan_api_case_batch_move | POST | `/test-plan/api/case/batch/move` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2070 | test_plan_api_case_report_get | GET | `/test-plan/api/case/report/get/{report_id}` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2076 | test_plan_api_case_report_detail | GET | `/test-plan/api/case/report/get/detail/{report_id}/{step_id}` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2110 | test_plan_api_scenario_tree | POST | `/test-plan/api/scenario/tree` | ✅ | `ok([
        {"id": "root", "name": "全部场景", "type": "MODULE", "childre…` |
| `app/test_plan/router.py` | 2118 | test_plan_api_scenario_module_count | POST | `/test-plan/api/scenario/module/count` | ✅ | `ok([])` |
| `app/test_plan/router.py` | 2124 | test_plan_api_scenario_sort | POST | `/test-plan/api/scenario/sort` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2130 | test_plan_api_scenario_run_get | GET | `/test-plan/api/scenario/run/{scenario_id}` | ✅ | `ok({
        "status": "success",
        "result": "SUCCESS",
    })` |
| `app/test_plan/router.py` | 2139 | test_plan_api_scenario_disassociate | POST | `/test-plan/api/scenario/disassociate` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2145 | test_plan_api_scenario_batch_disassociate | POST | `/test-plan/api/scenario/batch/disassociate` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2151 | test_plan_api_scenario_batch_run | POST | `/test-plan/api/scenario/batch/run` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2157 | test_plan_api_scenario_batch_move | POST | `/test-plan/api/scenario/batch/move` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2163 | test_plan_api_scenario_report_get | GET | `/test-plan/api/scenario/report/get/{report_id}` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2169 | test_plan_api_scenario_report_detail | GET | `/test-plan/api/scenario/report/get/detail/{report_id}/{step_id}` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2179 | test_plan_execute_single | POST | `/test-plan-execute/single` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2185 | test_plan_execute_batch | POST | `/test-plan-execute/batch` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2222 | test_plan_mind_data_edit | POST | `/test-plan/mind/data/edit` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2228 | test_plan_association_api_case_module_count | POST | `/test-plan/association/api/case/module/count` | ✅ | `ok([])` |
| `app/test_plan/router.py` | 2234 | test_plan_execute_user_option | GET | `/test-plan-execute/user-option/{project_id}` | ✅ | `ok([
        {"id": "admin", "name": "admin"},
    ])` |
| `app/test_plan/router.py` | 2259 | test_plan_api_case_associate_bug_page | POST | `/test-plan/api/case/associate/bug/page` | ✅ | `ok({
        "list": [], "total": 0,
    })` |
| `app/test_plan/router.py` | 2267 | test_plan_api_scenario_associate_bug_page | POST | `/test-plan/api/scenario/associate/bug/page` | ✅ | `ok({
        "list": [], "total": 0,
    })` |
| `app/test_plan/router.py` | 2275 | test_plan_api_case_associate_bug | POST | `/test-plan/api/case/associate/bug` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2281 | test_plan_api_scenario_associate_bug | POST | `/test-plan/api/scenario/associate/bug` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2287 | test_plan_api_case_disassociate_bug_get | GET | `/test-plan/api/case/disassociate/bug/{rel_id}` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2293 | test_plan_api_scenario_disassociate_bug_get | GET | `/test-plan/api/scenario/disassociate/bug/{rel_id}` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2299 | test_plan_functional_case_batch_associate_bug | POST | `/test-plan/functional/case/batch/associate-bug` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2305 | test_plan_functional_case_batch_add_bug | POST | `/test-plan/functional/case/batch/add-bug` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2311 | test_plan_api_case_batch_add_bug | POST | `/test-plan/api/case/batch/add-bug` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2317 | test_plan_api_scenario_batch_add_bug | POST | `/test-plan/api/scenario/batch/add-bug` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2323 | test_plan_api_case_batch_associate_bug | POST | `/test-plan/api/case/batch/associate-bug` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2329 | test_plan_api_scenario_batch_associate_bug | POST | `/test-plan/api/scenario/batch/associate-bug` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2335 | test_plan_functional_case_minder_batch_associate_bug | POST | `/test-plan/functional/case/minder/batch/associate-bug` | ✅ | `ok(None)` |
| `app/test_plan/router.py` | 2341 | test_plan_functional_case_minder_batch_add_bug | POST | `/test-plan/functional/case/minder/batch/add-bug` | ✅ | `ok(None)` |
| `app/test_plan/router_dashboard_home.py` | 75 | dashboard_execution_trend | GET | `/dashboard/execution-trend` | — | `ok({
        "dates": [],
        "executed": [],
        "passed": []…` |
| `app/test_plan/router_dashboard_home.py` | 85 | dashboard_recent_activity | GET | `/dashboard/recent-activity` | — | `ok([])` |
| `app/test_plan/router_dashboard_stats.py` | 389 | dashboard_bug_handle_user | POST | `/dashboard/bug_handle_user` | ✅ | `ok({
        "caseCountMap": {},
        "projectCountList": [],
     …` |
| `app/test_plan/router_dashboard_stats.py` | 399 | dashboard_bug_handle_user_list | GET | `/dashboard/bug_handle_user/list` | ✅ | `ok([
        {"id": "admin", "name": "admin"},
    ])` |
| `app/test_plan/router_dashboard_stats.py` | 443 | dashboard_member_option | GET | `/dashboard/member/get-project-member/option/{project_id}` | ✅ | `ok([
        {"id": "admin", "name": "admin"},
    ])` |
| `app/test_plan/router_system.py` | 68 | template_option | GET | `/template/option/{project_id}/{type}` | — | `ok([
        {"id": "default", "name": "默认模板"}
    ])` |
| `app/test_plan/router_system.py` | 77 | resource_pool_list | GET | `/resource/pool/list` | — | `ok([])` |
| `app/test_plan/router_system.py` | 84 | plugin_list | GET | `/system/plugin/list` | ✅ | `ok([])` |
| `app/test_plan/router_system.py` | 91 | operation_log_page | GET | `/system/operation-log/page` | — | `ok({
        "list": [],
        "total": 0,
    })` |
| `app/test_plan/router_system.py` | 120 | system_project_list | GET | `/system/project/list` | ✅ | `ok([])` |

## X 类：无副作用但转发 helper / 体量超阈（需人工核查是否真空壳）

| 文件 | 行 | 函数 | 方法 | 路径 | 前端引用 | 行数 |
|------|----|------|------|------|----------|------|
| `app/auth/router.py` | 288 | get_menu_list | POST | `/api/user/menu` | ✅ | 4 |
| `app/auth/router.py` | 423 | get_personal_info | GET | `/personal/get` | ✅ | 19 |
| `app/auth/router.py` | 1042 | get_system_roles | GET | `/system/user/get/global/system/role` | ✅ | 34 |
| `app/auth/router_system.py` | 165 | get_org_switch_options | GET | `/system/organization/switch-option` | ✅ | 3 |
| `app/auth/router_system.py` | 226 | project_list_options | GET | `/project/list/options/{organization_id}` | ✅ | 4 |
| `app/auth/router_system.py` | 308 | project_list_by_org_module | GET | `/project/list/options/{org_id}/{module}` | ✅ | 4 |
| `app/auth/router_system.py` | 496 | get_protocol_list | GET | `/api/test/protocol/{organization_id}` | ✅ | 11 |
| `app/routers/ai_config.py` | 278 | ai_conversation_chat_list | GET | `/ai/conversation/chat/list` | ✅ | 3 |
| `app/routers/apitest_compat_case.py` | 325 | api_case_execute_page | GET | `/api/case/execute/page` | ✅ | 10 |
| `app/routers/apitest_compat_case.py` | 338 | api_case_operation_history_page | GET | `/api/case/operation-history/page` | ✅ | 10 |
| `app/routers/apitest_compat_case.py` | 703 | api_case_execute_page_route | POST | `/api/case/execute/page` | ✅ | 13 |
| `app/routers/apitest_compat_case.py` | 719 | api_case_operation_history_page_route | POST | `/api/case/operation-history/page` | ✅ | 13 |
| `app/routers/apitest_compat_definition.py` | 736 | api_definition_operation_history | GET | `/api/definition/operation-history` | ✅ | 37 |
| `app/routers/apitest_compat_definition.py` | 777 | api_definition_operation_history_post | POST | `/api/definition/operation-history` | ✅ | 38 |
| `app/routers/apitest_compat_mock.py` | 287 | api_definition_mock_operation_history_page | POST | `/api/definition/mock/operation-history/page` | — | 38 |
| `app/routers/apitest_compat_scenario.py` | 803 | api_scenario_statistics | POST | `/api/scenario/statistics` | ✅ | 12 |
| `app/routers/attachment.py` | 60 | api_attachment_download_post | POST | `/attachment/download` | ✅ | 4 |
| `app/routers/auth_compat.py` | 21 | authentication_get_by_type | GET | `/authentication/get/by/type` | ✅ | 17 |
| `app/routers/case_review.py` | 312 | case_review_page | POST | `/case/review/page` | ✅ | 15 |
| `app/routers/case_review.py` | 374 | case_review_edit | POST | `/case/review/edit` | ✅ | 21 |
| `app/routers/case_review.py` | 398 | case_review_delete | POST | `/case/review/delete` | ✅ | 8 |
| `app/routers/case_review.py` | 409 | case_review_copy | POST | `/case/review/copy` | ✅ | 22 |
| `app/routers/case_review.py` | 434 | case_review_batch_move | POST | `/case/review/batch/move` | ✅ | 12 |
| `app/routers/case_review.py` | 449 | case_review_edit_pos | POST | `/case/review/edit/pos` | ✅ | 9 |
| `app/routers/case_review.py` | 461 | case_review_edit_follower | POST | `/case/review/edit/follower` | ✅ | 10 |
| `app/routers/case_review.py` | 493 | case_review_disassociate | POST | `/case/review/disassociate` | ✅ | 15 |
| `app/routers/case_review.py` | 511 | case_review_detail | POST | `/case/review/detail` | ✅ | 8 |
| `app/routers/case_review.py` | 522 | case_review_detail_get | GET | `/case/review/detail` | ✅ | 7 |
| `app/routers/case_review.py` | 532 | case_review_detail_get_path | GET | `/case/review/detail/{id}` | ✅ | 6 |
| `app/routers/case_review.py` | 594 | case_review_user_option | POST | `/case/review/user-option` | ✅ | 5 |
| `app/routers/case_review.py` | 623 | case_review_module_add | POST | `/case/review/module/add` | ✅ | 10 |
| `app/routers/case_review.py` | 636 | case_review_module_update | POST | `/case/review/module/update` | ✅ | 10 |
| `app/routers/case_review.py` | 649 | case_review_module_delete | POST | `/case/review/module/delete` | ✅ | 7 |
| `app/routers/case_review.py` | 659 | case_review_module_move | POST | `/case/review/module/move` | ✅ | 10 |
| `app/routers/case_review.py` | 672 | case_review_module_count | POST | `/case/review/module/count` | ✅ | 5 |
| `app/routers/case_review.py` | 698 | case_review_detail_batch_review | POST | `/case/review/detail/batch/review` | ✅ | 36 |
| `app/routers/case_review.py` | 737 | case_review_detail_batch_disassociate | POST | `/case/review/detail/batch/disassociate` | ✅ | 12 |
| `app/routers/case_review.py` | 752 | case_review_detail_batch_edit_reviewers | POST | `/case/review/detail/batch/edit/reviewers` | ✅ | 11 |
| `app/routers/case_review.py` | 766 | case_review_detail_get_ids | POST | `/case/review/detail/get-ids` | ✅ | 6 |
| `app/routers/case_review.py` | 794 | case_review_detail_tree | POST | `/case/review/detail/tree` | ✅ | 5 |
| `app/routers/case_review.py` | 815 | case_review_detail_mind_multiple_review | POST | `/case/review/detail/mind/multiple/review` | ✅ | 17 |
| `app/routers/case_review.py` | 864 | case_review_detail_tree_get_route | GET | `/case/review/detail/tree/{review_id}` | ✅ | 3 |
| `app/routers/case_review.py` | 870 | case_review_detail_reviewer_list_get_route | GET | `/case/review/detail/reviewer/list/{review_id}/{case_id}` | ✅ | 22 |
| `app/routers/case_review.py` | 895 | case_review_detail_reviewer_status_total_get_route | GET | `/case/review/detail/reviewer/status/total/{review_id}/{case_id}` | ✅ | 27 |
| `app/routers/debug_compat.py` | 148 | api_debug_upload_temp_file | POST | `/api/debug/upload/temp/file` | ✅ | 28 |
| `app/routers/debug_compat.py` | 179 | api_debug | POST | `/api/debug` | ✅ | 19 |
| `app/routers/debug_compat.py` | 201 | api_debug_import_curl | POST | `/api/debug/import-curl` | ✅ | 30 |
| `app/routers/debug_compat.py` | 239 | api_debug_execute | POST | `/api/debug/debug` | ✅ | 109 |
| `app/routers/defects_compat.py` | 109 | bug_follow | POST | `/bug/follow/` | ✅ | 14 |
| `app/routers/defects_compat.py` | 126 | bug_unfollow | POST | `/bug/unfollow/` | ✅ | 14 |
| `app/routers/defects_compat.py` | 179 | api_bug_attachment_check_update_post | POST | `/bug/attachment/check-update` | ✅ | 4 |
| `app/routers/defects_compat.py` | 186 | api_bug_attachment_download_post | POST | `/bug/attachment/download` | ✅ | 4 |
| `app/routers/defects_compat.py` | 193 | api_bug_attachment_preview_post | POST | `/bug/attachment/preview` | ✅ | 4 |
| `app/routers/defects_compat.py` | 200 | api_bug_case_unrelate_module_tree_post | POST | `/bug/case/un-relate/module/tree` | ✅ | 4 |
| `app/routers/defects_compat.py` | 207 | api_bug_case_unrelate_module_count_post | POST | `/bug/case/un-relate/module/count` | ✅ | 4 |
| `app/routers/defects_compat_extra.py` | 276 | bug_header_custom_field_path | GET | `/bug/header/custom-field/{project_id}` | ✅ | 3 |
| `app/routers/defects_compat_extra.py` | 282 | bug_columns_option | GET | `/bug/columns-option/{project_id}` | — | 12 |
| `app/routers/defects_compat_extra.py` | 325 | bug_template_detail | GET | `/bug/template/detail` | ✅ | 14 |
| `app/routers/defects_compat_extra.py` | 614 | bug_follow_path | GET | `/bug/follow/{bug_id}` | ✅ | 11 |
| `app/routers/defects_compat_extra.py` | 628 | bug_unfollow_path | GET | `/bug/unfollow/{bug_id}` | ✅ | 11 |
| `app/routers/defects_compat_extra.py` | 645 | bug_template_option_project | GET | `/bug/template/option/{project_id}` | ✅ | 10 |
| `app/routers/defects_compat_extra.py` | 658 | bug_template_detail_post | POST | `/bug/template/detail` | ✅ | 18 |
| `app/routers/defects_compat_extra.py` | 679 | bug_export_columns_path | GET | `/bug/export/columns/{project_id}` | ✅ | 16 |
| `app/routers/defects_compat_extra.py` | 742 | bug_sync_check | GET | `/bug/sync/check/{project_id}` | ✅ | 10 |
| `app/routers/extra_router.py` | 102 | extra_module_setting | GET | `/project/application/module-setting/{project_id}` | ✅ | 13 |
| `app/routers/extra_router.py` | 124 | extra_project_application_by_suffix | POST | `/project/application/{suffix}` | ✅ | 5 |
| `app/routers/functional_cases.py` | 192 | func_case_default_template_field_path | GET | `/functional/case/default/template/field/{project_id}` | ✅ | 29 |
| `app/routers/functional_cases.py` | 192 | func_case_default_template_field_path | POST | `/functional/case/default/template/field/{project_id}` | ✅ | 29 |
| `app/routers/functional_cases.py` | 248 | func_case_export_columns_path | GET | `/functional/case/export/columns/{project_id}` | ✅ | 34 |
| `app/routers/functional_cases.py` | 248 | func_case_export_columns_path | POST | `/functional/case/export/columns/{project_id}` | ✅ | 34 |
| `app/routers/functional_cases.py` | 327 | functional_case_module_trash_tree_path | GET | `/functional/case/module/trash/tree/{project_id}` | ✅ | 7 |
| `app/routers/functional_cases.py` | 446 | functional_case_module_trash_tree | GET | `/functional/case/module/trash/tree` | ✅ | 3 |
| `app/routers/functional_cases.py` | 513 | functional_case_trash_module_count | GET | `/functional/case/trash/module/count` | ✅ | 3 |
| `app/routers/functional_cases_extra.py` | 192 | functional_case_export_columns | GET | `/functional/case/export/columns` | ✅ | 19 |
| `app/routers/gap_fixes.py` | 28 | api_execute_resourcescript | POST | `/api/execute/resourcescript` | — | 9 |
| `app/routers/generation.py` | 169 | generate_structured_api | POST | `/api/generate/structured` | ✅ | 32 |
| `app/routers/method_compat.py` | 120 | functional_mind_case_tree_post | POST | `/functional/mind/case/tree` | ✅ | 9 |
| `app/routers/method_compat.py` | 191 | project_schedule_page_post | POST | `/project/task-center/schedule/page` | ✅ | 8 |
| `app/routers/method_compat.py` | 202 | project_exec_task_page_post | POST | `/project/task-center/exec-task/page` | ✅ | 7 |
| `app/routers/method_compat.py` | 243 | system_schedule_page_post | POST | `/system/task-center/schedule/page` | ✅ | 8 |
| `app/routers/method_compat.py` | 254 | system_exec_task_page_post | POST | `/system/task-center/exec-task/page` | ✅ | 7 |
| `app/routers/method_compat.py` | 295 | org_schedule_page_post | POST | `/organization/task-center/schedule/page` | ✅ | 8 |
| `app/routers/method_compat.py` | 306 | org_exec_task_page_post | POST | `/organization/task-center/exec-task/page` | ✅ | 7 |
| `app/routers/method_compat.py` | 347 | task_center_project_schedule_page_post | POST | `/task/center/project/schedule/page` | ✅ | 8 |
| `app/routers/method_compat.py` | 407 | api_test_plugin_form_option_post | POST | `/api/test/plugin/form/option` | ✅ | 10 |
| `app/routers/missing_admin.py` | 135 | user_role_global_permission_setting | GET | `/user/role/global/permission/setting/{role_id}` | — | 3 |
| `app/routers/missing_admin.py` | 211 | user_role_org_permission_setting | GET | `/user/role/organization/permission/setting/{role_id}` | — | 3 |
| `app/routers/organizations.py` | 431 | org_user_role_list_path | GET | `/organization/user/role/list/{org_id}` | ✅ | 3 |
| `app/routers/other_compat.py` | 121 | api_doc_share_detail_path | GET | `/api/doc/share/detail/{share_id}` | ✅ | 12 |
| `app/routers/other_compat.py` | 142 | api_doc_share_get_detail_path | GET | `/api/doc/share/get-detail/{share_id}` | ✅ | 43 |
| `app/routers/other_compat.py` | 316 | api_doc_share_detail | POST | `/api/doc/share/detail` | ✅ | 12 |
| `app/routers/other_compat.py` | 432 | api_test_protocol | GET | `/api/test/protocol` | ✅ | 11 |
| `app/routers/other_compat.py` | 779 | ldap_login | POST | `/ldap/login` | ✅ | 63 |
| `app/routers/other_compat.py` | 933 | dashboard_layout_get | GET | `/dashboard/layout/get` | ✅ | 17 |
| `app/routers/other_compat.py` | 1101 | review_functional_case_get_list | POST | `/review/functional/case/get/list` | ✅ | 6 |
| `app/routers/other_compat.py` | 1151 | review_functional_case_get_list_get_route | GET | `/review/functional/case/get/list/{review_id}/{case_id}` | ✅ | 3 |
| `app/routers/platform.py` | 16 | license_validate_get | GET | `/license/validate` | ✅ | 17 |
| `app/routers/platform.py` | 47 | setting_get_platform_param | GET | `/setting/get/platform/param` | ✅ | 9 |
| `app/routers/platform.py` | 71 | license_validate | POST | `/license/validate` | ✅ | 14 |
| `app/routers/project_compat_environment.py` | 75 | project_environment_get_entry | GET | `/project/environment/get/entry` | ✅ | 9 |
| `app/routers/project_compat_environment.py` | 75 | project_environment_get_entry | POST | `/project/environment/get/entry` | ✅ | 9 |
| `app/routers/project_compat_environment.py` | 108 | project_environment_database_driver_options | GET | `/project/environment/database/driver-options/` | ✅ | 11 |
| `app/routers/project_compat_environment.py` | 130 | project_environment_group_list | GET | `/project/environment/group/list` | ✅ | 20 |
| `app/routers/project_compat_environment.py` | 130 | project_environment_group_list | POST | `/project/environment/group/list` | ✅ | 20 |
| `app/routers/project_compat_environment.py` | 152 | project_environment_group_add | POST | `/project/environment/group/add` | ✅ | 19 |
| `app/routers/project_compat_environment.py` | 173 | project_environment_group_update | POST | `/project/environment/group/update` | ✅ | 51 |
| `app/routers/project_compat_environment.py` | 272 | project_environment_group_get_path | GET | `/project/environment/group/get/{group_id}` | ✅ | 13 |
| `app/routers/project_compat_environment.py` | 292 | project_environment_driver_options_path | GET | `/project/environment/database/driver-options/{organization_id}` | ✅ | 11 |
| `app/routers/project_compat_environment.py` | 313 | project_environment_list | POST | `/project/environment/list` | ✅ | 19 |
| `app/routers/project_compat_environment.py` | 313 | project_environment_list | GET | `/project/environment/list` | ✅ | 19 |
| `app/routers/project_compat_environment.py` | 399 | project_environment_import | POST | `/project/environment/import` | ✅ | 27 |
| `app/routers/project_compat_environment.py` | 428 | project_environment_export_path | POST | `/project/environment/export` | ✅ | 11 |
| `app/routers/project_compat_extra.py` | 369 | project_custom_func_page | GET | `/project/custom/func/page` | ✅ | 3 |
| `app/routers/project_compat_extra.py` | 374 | project_custom_func_page_post | POST | `/project/custom/func/page` | ✅ | 13 |
| `app/routers/project_compat_extra.py` | 531 | project_template_enable_config_path | GET | `/project/template/enable/config/{scoped_id}` | ✅ | 3 |
| `app/routers/project_compat_extra2.py` | 202 | project_global_params_add | POST | `/project/global/params/add` | ✅ | 19 |
| `app/routers/project_compat_extra2.py` | 223 | project_global_params_update | POST | `/project/global/params/update` | ✅ | 19 |
| `app/routers/project_compat_extra2.py` | 269 | project_global_params_import | POST | `/project/global/params/import` | ✅ | 39 |
| `app/routers/project_compat_extra2.py` | 720 | project_log_user_list | GET | `/project/log/user/list` | ✅ | 3 |
| `app/routers/project_compat_extra2.py` | 725 | project_log_user_list_path | GET | `/project/log/user/list/{id}` | ✅ | 9 |
| `app/routers/project_compat_extra2.py` | 742 | project_global_params_get_path | GET | `/project/global/params/get/{param_id}` | ✅ | 21 |
| `app/routers/project_compat_extra2.py` | 765 | project_global_params_export_path | GET | `/project/global/params/export/{param_id}` | ✅ | 14 |
| `app/routers/project_compat_file.py` | 178 | project_file_batch_delete | POST | `/project/file/batch-delete` | — | 26 |
| `app/routers/project_compat_file.py` | 206 | project_file_get | GET | `/project/file/get` | ✅ | 29 |
| `app/routers/project_compat_file.py` | 237 | project_file_batch_move | POST | `/project/file/batch-move` | ✅ | 24 |
| `app/routers/project_compat_member.py` | 117 | project_member_get_role_option | GET | `/project/member/get-role/option` | ✅ | 3 |
| `app/routers/project_compat_member.py` | 117 | project_member_get_role_option | GET | `/project/member/get-role/option/{project_id}` | ✅ | 3 |
| `app/routers/reports_compat.py` | 333 | api_report_case_task_report_path | GET | `/api/report/case/task-report/{task_id}` | ✅ | 13 |
| `app/routers/reports_compat.py` | 360 | api_report_scenario_task_report_step_path | GET | `/api/report/scenario/task-report/{task_id}/{step_id}` | ✅ | 9 |
| `app/routers/system.py` | 38 | api_test_types | GET | `/api/test-types` | ✅ | 14 |
| `app/routers/system.py` | 63 | api_debug_logs | GET | `/api/debug/logs` | ✅ | 18 |
| `app/routers/system.py` | 84 | api_clear_debug_logs | DELETE | `/api/debug/logs` | ✅ | 15 |
| `app/routers/system_compat_extra.py` | 151 | api_system_org_option_all_post | POST | `/system/organization/option/all` | ✅ | 4 |
| `app/routers/system_compat_extra.py` | 157 | api_system_project_pool_options_post | POST | `/system/project/pool-options` | ✅ | 4 |
| `app/routers/system_compat_extra.py` | 292 | organization_template_enable_config_path | GET | `/organization/template/enable/config/{scoped_id}` | ✅ | 3 |
| `app/routers/system_compat_userrole.py` | 252 | user_role_project_list | POST | `/user/role/project/list` | ✅ | 9 |
| `app/routers/system_compat_userrole.py` | 354 | user_role_project_permission_setting | GET | `/user/role/project/permission/setting/{role_id}` | ✅ | 3 |
| `app/routers/system_compat_userrole.py` | 359 | user_role_project_permission_setting_old | GET | `/user/role/project/permission/setting/` | ✅ | 3 |
| `app/routers/system_compat_userrole.py` | 493 | user_role_project_permission_update | POST | `/user/role/project/permission/update` | ✅ | 7 |
| `app/routers/task_center.py` | 107 | proj_task_center_batch_delete_post | POST | `/project/task-center/exec-task/batch-delete` | ✅ | 6 |
| `app/routers/task_center.py` | 115 | proj_task_center_batch_stop_post | POST | `/project/task-center/exec-task/batch-stop` | ✅ | 6 |
| `app/routers/task_center.py` | 123 | proj_task_center_item_batch_stop_post | POST | `/project/task-center/exec-task/item/batch-stop` | ✅ | 6 |
| `app/routers/task_center.py` | 131 | proj_task_center_schedule_batch_disable_post | POST | `/project/task-center/schedule/batch-disable` | ✅ | 6 |
| `app/routers/task_center.py` | 139 | proj_task_center_schedule_batch_enable_post | POST | `/project/task-center/schedule/batch-enable` | ✅ | 6 |
| `app/routers/task_center.py` | 147 | proj_task_center_schedule_update_cron_post | POST | `/project/task-center/schedule/update-cron` | ✅ | 7 |
| `app/routers/task_center.py` | 181 | project_task_center_exec_task_item_stop | GET | `/project/task-center/exec-task/item/stop` | ✅ | 5 |
| `app/routers/task_center.py` | 188 | project_task_center_exec_task_stop | GET | `/project/task-center/exec-task/stop` | ✅ | 5 |
| `app/routers/task_center.py` | 195 | project_task_center_exec_task_rerun | GET | `/project/task-center/exec-task/rerun` | ✅ | 5 |
| `app/routers/task_center.py` | 202 | project_task_center_exec_task_delete | GET | `/project/task-center/exec-task/delete` | ✅ | 5 |
| `app/routers/task_center.py` | 214 | project_task_center_exec_task_batch_stop | GET | `/project/task-center/exec-task/batch-stop` | ✅ | 6 |
| `app/routers/task_center.py` | 222 | project_task_center_exec_task_batch_delete | GET | `/project/task-center/exec-task/batch-delete` | ✅ | 6 |
| `app/routers/task_center.py` | 230 | project_task_center_exec_task_item_batch_stop | GET | `/project/task-center/exec-task/item/batch-stop` | ✅ | 6 |
| `app/routers/task_center.py` | 238 | project_task_center_exec_task_item_batch_delete | GET | `/project/task-center/exec-task/item/batch-delete` | — | 6 |
| `app/routers/task_center.py` | 251 | project_task_center_schedule_delete | GET | `/project/task-center/schedule/delete` | ✅ | 5 |
| `app/routers/task_center.py` | 258 | project_task_center_schedule_switch | GET | `/project/task-center/schedule/switch` | ✅ | 5 |
| `app/routers/task_center.py` | 265 | project_task_center_schedule_batch_enable | GET | `/project/task-center/schedule/batch-enable` | ✅ | 6 |
| `app/routers/task_center.py` | 273 | project_task_center_schedule_batch_disable | GET | `/project/task-center/schedule/batch-disable` | ✅ | 6 |
| `app/routers/task_center.py` | 281 | project_task_center_schedule_update_cron | GET | `/project/task-center/schedule/update-cron` | ✅ | 7 |
| `app/routers/task_center.py` | 296 | project_task_center_exec_delete_path | GET | `/project/task-center/exec-task/delete/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 296 | project_task_center_exec_delete_path | POST | `/project/task-center/exec-task/delete/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 303 | project_task_center_exec_item_stop_path | GET | `/project/task-center/exec-task/item/stop/{task_id}/{item_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 303 | project_task_center_exec_item_stop_path | POST | `/project/task-center/exec-task/item/stop/{task_id}/{item_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 310 | project_task_center_exec_rerun_path | GET | `/project/task-center/exec-task/rerun/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 310 | project_task_center_exec_rerun_path | POST | `/project/task-center/exec-task/rerun/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 317 | project_task_center_exec_stop_path | GET | `/project/task-center/exec-task/stop/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 317 | project_task_center_exec_stop_path | POST | `/project/task-center/exec-task/stop/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 324 | project_task_center_schedule_delete_path | GET | `/project/task-center/schedule/delete/{schedule_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 324 | project_task_center_schedule_delete_path | POST | `/project/task-center/schedule/delete/{schedule_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 331 | project_task_center_schedule_switch_path | GET | `/project/task-center/schedule/switch/{schedule_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 331 | project_task_center_schedule_switch_path | POST | `/project/task-center/schedule/switch/{schedule_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 338 | project_task_item_stop_single_path | GET | `/project/task-center/exec-task/item/stop/{id}` | ✅ | 4 |
| `app/routers/task_center.py` | 338 | project_task_item_stop_single_path | POST | `/project/task-center/exec-task/item/stop/{id}` | ✅ | 4 |
| `app/routers/task_center.py` | 353 | project_task_center_stop | GET | `/project/task-center/stop/{task_id}` | — | 4 |
| `app/routers/task_center.py` | 359 | org_task_center_batch_delete_post | POST | `/organization/task-center/exec-task/batch-delete` | ✅ | 6 |
| `app/routers/task_center.py` | 367 | org_task_center_batch_stop_post | POST | `/organization/task-center/exec-task/batch-stop` | ✅ | 6 |
| `app/routers/task_center.py` | 375 | org_task_center_item_batch_stop_post | POST | `/organization/task-center/exec-task/item/batch-stop` | ✅ | 6 |
| `app/routers/task_center.py` | 383 | org_task_center_schedule_batch_disable_post | POST | `/organization/task-center/schedule/batch-disable` | ✅ | 6 |
| `app/routers/task_center.py` | 391 | org_task_center_schedule_batch_enable_post | POST | `/organization/task-center/schedule/batch-enable` | ✅ | 6 |
| `app/routers/task_center.py` | 399 | org_task_center_schedule_update_cron_post | POST | `/organization/task-center/schedule/update-cron` | ✅ | 7 |
| `app/routers/task_center.py` | 408 | sys_task_center_batch_delete_post | POST | `/system/task-center/exec-task/batch-delete` | ✅ | 6 |
| `app/routers/task_center.py` | 416 | sys_task_center_batch_stop_post | POST | `/system/task-center/exec-task/batch-stop` | ✅ | 6 |
| `app/routers/task_center.py` | 424 | sys_task_center_item_batch_stop_post | POST | `/system/task-center/exec-task/item/batch-stop` | ✅ | 6 |
| `app/routers/task_center.py` | 432 | sys_task_center_schedule_batch_disable_post | POST | `/system/task-center/schedule/batch-disable` | ✅ | 6 |
| `app/routers/task_center.py` | 440 | sys_task_center_schedule_batch_enable_post | POST | `/system/task-center/schedule/batch-enable` | ✅ | 6 |
| `app/routers/task_center.py` | 448 | sys_task_center_schedule_update_cron_post | POST | `/system/task-center/schedule/update-cron` | ✅ | 7 |
| `app/routers/task_center.py` | 492 | organization_task_center_exec_task_item_stop | GET | `/organization/task-center/exec-task/item/stop/{id}` | ✅ | 4 |
| `app/routers/task_center.py` | 498 | organization_task_center_exec_task_stop | GET | `/organization/task-center/exec-task/stop` | ✅ | 5 |
| `app/routers/task_center.py` | 505 | organization_task_center_exec_task_rerun | GET | `/organization/task-center/exec-task/rerun` | ✅ | 5 |
| `app/routers/task_center.py` | 512 | organization_task_center_exec_task_delete | GET | `/organization/task-center/exec-task/delete` | ✅ | 5 |
| `app/routers/task_center.py` | 524 | organization_task_center_exec_task_batch_stop | GET | `/organization/task-center/exec-task/batch-stop` | ✅ | 6 |
| `app/routers/task_center.py` | 532 | organization_task_center_exec_task_batch_delete | GET | `/organization/task-center/exec-task/batch-delete` | ✅ | 6 |
| `app/routers/task_center.py` | 540 | organization_task_center_exec_task_item_batch_stop | GET | `/organization/task-center/exec-task/item/batch-stop` | ✅ | 6 |
| `app/routers/task_center.py` | 548 | organization_task_center_exec_task_item_batch_delete | GET | `/organization/task-center/exec-task/item/batch-delete` | — | 6 |
| `app/routers/task_center.py` | 561 | organization_task_center_schedule_delete | GET | `/organization/task-center/schedule/delete` | ✅ | 5 |
| `app/routers/task_center.py` | 568 | organization_task_center_schedule_switch | GET | `/organization/task-center/schedule/switch` | ✅ | 5 |
| `app/routers/task_center.py` | 575 | organization_task_center_schedule_batch_enable | GET | `/organization/task-center/schedule/batch-enable` | ✅ | 6 |
| `app/routers/task_center.py` | 583 | organization_task_center_schedule_batch_disable | GET | `/organization/task-center/schedule/batch-disable` | ✅ | 6 |
| `app/routers/task_center.py` | 591 | organization_task_center_schedule_update_cron | GET | `/organization/task-center/schedule/update-cron` | ✅ | 7 |
| `app/routers/task_center.py` | 630 | system_task_center_exec_task_item_stop | GET | `/system/task-center/exec-task/item/stop` | ✅ | 5 |
| `app/routers/task_center.py` | 637 | system_task_center_exec_task_stop | GET | `/system/task-center/exec-task/stop` | ✅ | 5 |
| `app/routers/task_center.py` | 644 | system_task_center_exec_task_rerun | GET | `/system/task-center/exec-task/rerun` | ✅ | 5 |
| `app/routers/task_center.py` | 651 | system_task_center_exec_task_delete | GET | `/system/task-center/exec-task/delete` | ✅ | 5 |
| `app/routers/task_center.py` | 663 | system_task_center_exec_task_batch_stop | GET | `/system/task-center/exec-task/batch-stop` | ✅ | 6 |
| `app/routers/task_center.py` | 671 | system_task_center_exec_task_batch_delete | GET | `/system/task-center/exec-task/batch-delete` | ✅ | 6 |
| `app/routers/task_center.py` | 679 | system_task_center_exec_task_item_batch_stop | GET | `/system/task-center/exec-task/item/batch-stop` | ✅ | 6 |
| `app/routers/task_center.py` | 687 | system_task_center_exec_task_item_batch_delete | GET | `/system/task-center/exec-task/item/batch-delete` | — | 6 |
| `app/routers/task_center.py` | 700 | system_task_center_schedule_delete | GET | `/system/task-center/schedule/delete` | ✅ | 5 |
| `app/routers/task_center.py` | 707 | system_task_center_schedule_switch | GET | `/system/task-center/schedule/switch` | ✅ | 5 |
| `app/routers/task_center.py` | 714 | system_task_center_schedule_batch_enable | GET | `/system/task-center/schedule/batch-enable` | ✅ | 6 |
| `app/routers/task_center.py` | 722 | system_task_center_schedule_batch_disable | GET | `/system/task-center/schedule/batch-disable` | ✅ | 6 |
| `app/routers/task_center.py` | 730 | system_task_center_schedule_update_cron | GET | `/system/task-center/schedule/update-cron` | ✅ | 7 |
| `app/routers/task_center.py` | 760 | org_task_center_exec_delete_path | GET | `/organization/task-center/exec-task/delete/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 760 | org_task_center_exec_delete_path | POST | `/organization/task-center/exec-task/delete/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 767 | org_task_center_exec_item_stop_path | GET | `/organization/task-center/exec-task/item/stop/{id}/{item_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 767 | org_task_center_exec_item_stop_path | POST | `/organization/task-center/exec-task/item/stop/{id}/{item_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 774 | org_task_center_exec_rerun_path | GET | `/organization/task-center/exec-task/rerun/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 774 | org_task_center_exec_rerun_path | POST | `/organization/task-center/exec-task/rerun/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 781 | org_task_center_exec_stop_path | GET | `/organization/task-center/exec-task/stop/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 781 | org_task_center_exec_stop_path | POST | `/organization/task-center/exec-task/stop/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 788 | org_task_center_schedule_delete_path | GET | `/organization/task-center/schedule/delete/{schedule_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 788 | org_task_center_schedule_delete_path | POST | `/organization/task-center/schedule/delete/{schedule_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 795 | org_task_center_schedule_switch_path | GET | `/organization/task-center/schedule/switch/{schedule_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 795 | org_task_center_schedule_switch_path | POST | `/organization/task-center/schedule/switch/{schedule_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 802 | system_task_center_exec_delete_path | GET | `/system/task-center/exec-task/delete/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 802 | system_task_center_exec_delete_path | POST | `/system/task-center/exec-task/delete/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 809 | system_task_center_exec_item_stop_path | GET | `/system/task-center/exec-task/item/stop/{task_id}/{item_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 809 | system_task_center_exec_item_stop_path | POST | `/system/task-center/exec-task/item/stop/{task_id}/{item_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 816 | system_task_center_exec_rerun_path | GET | `/system/task-center/exec-task/rerun/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 816 | system_task_center_exec_rerun_path | POST | `/system/task-center/exec-task/rerun/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 823 | system_task_center_exec_stop_path | GET | `/system/task-center/exec-task/stop/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 823 | system_task_center_exec_stop_path | POST | `/system/task-center/exec-task/stop/{task_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 830 | system_task_center_schedule_delete_path | GET | `/system/task-center/schedule/delete/{schedule_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 830 | system_task_center_schedule_delete_path | POST | `/system/task-center/schedule/delete/{schedule_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 837 | system_task_center_schedule_switch_path | GET | `/system/task-center/schedule/switch/{schedule_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 837 | system_task_center_schedule_switch_path | POST | `/system/task-center/schedule/switch/{schedule_id}` | ✅ | 4 |
| `app/routers/task_center.py` | 844 | system_task_item_stop_single_path | GET | `/system/task-center/exec-task/item/stop/{id}` | ✅ | 4 |
| `app/routers/task_center.py` | 844 | system_task_item_stop_single_path | POST | `/system/task-center/exec-task/item/stop/{id}` | ✅ | 4 |
| `app/routers/test_resources.py` | 270 | test_resource_pool_capacity_detail | GET | `/test/resource/pool/capacity/detail` | ✅ | 9 |
| `app/test_plan/router.py` | 1330 | test_plan_report_get_layout | POST | `/test-plan/report/get-layout` | ✅ | 46 |
| `app/test_plan/router.py` | 1330 | test_plan_report_get_layout | GET | `/test-plan/report/get-layout/{report_id}` | ✅ | 46 |
| `app/test_plan/router.py` | 1380 | test_plan_report_share_get_layout | POST | `/test-plan/report/share/get-layout` | ✅ | 45 |
| `app/test_plan/router.py` | 1380 | test_plan_report_share_get_layout | GET | `/test-plan/report/share/get-layout/{share_id}/{report_id}` | ✅ | 45 |
| `app/test_plan/router_dashboard_mine.py` | 428 | dashboard_header_custom_field | GET | `/dashboard/header/custom-field/{project_id}` | ✅ | 82 |
| `app/test_plan/router_dashboard_mine.py` | 513 | dashboard_header_columns_option | GET | `/dashboard/header/columns-option/{project_id}` | ✅ | 21 |
| `app/test_plan/router_dashboard_stats.py` | 97 | dashboard_project_view | POST | `/dashboard/project_view` | ✅ | 4 |
| `app/test_plan/router_dashboard_stats.py` | 104 | dashboard_create_by_me | POST | `/dashboard/create_by_me` | ✅ | 4 |
| `app/test_plan/router_dashboard_stats.py` | 111 | dashboard_project_member_view | POST | `/dashboard/project_member_view` | ✅ | 16 |
| `app/test_plan/router_system.py` | 32 | user_group_list | GET | `/system/user-group/list` | — | 18 |
| `app/test_plan/router_system.py` | 54 | template_list | GET | `/template/list/{project_id}/{type}` | — | 11 |

_自动生成于 2026-09-04 19:46:23_