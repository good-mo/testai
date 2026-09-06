# -*- coding: utf-8 -*-
"""app.api_testing.management 包（由原 management.py 拆分，对外符号保持一致）。

按业务域拆分为子模块：
- _base        数据库连接 / 列迁移 / 表结构初始化
- definitions  接口定义管理
- cases        接口用例管理
- scenarios    场景编排
- mocks        Mock 服务
- environments 环境管理
- assertions   断言规则管理
- imports      Postman/Swagger 接口导入
- debug        接口调试与调试日志
- execution    场景执行
"""

from app.api_testing.management._base import (
    _ensure_api_columns,
    _get_conn,
    _init_tables,
)
from app.api_testing.management.assertions import (
    create_assertion_rule,
    delete_assertion_rule,
    get_assertion_rule,
    list_assertion_rules,
)
from app.api_testing.management.cases import (
    create_api_test_case,
    delete_api_test_case,
    get_api_test_case,
    list_api_test_cases,
    list_trash_cases,
    restore_case,
    update_api_test_case,
)
from app.api_testing.management.debug import (
    _log_debug_call,
    clear_debug_logs,
    debug_api_call,
    list_debug_logs,
)
from app.api_testing.management.definitions import (
    create_api_definition,
    delete_api_definition,
    get_api_definition,
    list_api_definitions,
    list_trash_definitions,
    restore_definition,
    update_api_definition,
)
from app.api_testing.management.environments import (
    create_environment,
    delete_environment,
    get_environment,
    list_environments,
    update_environment,
)
from app.api_testing.management.execution import execute_scenario
from app.api_testing.management.imports import import_from_postman, import_from_swagger
from app.api_testing.management.mocks import (
    create_mock_service,
    delete_mock_service,
    get_mock_service,
    list_mock_services,
    list_trash_mocks,
    restore_mock,
    update_mock_service,
)
from app.api_testing.management.scenarios import (
    create_scenario,
    delete_scenario,
    get_scenario,
    list_scenarios,
    list_trash_scenarios,
    restore_scenario,
    update_scenario,
)

__all__ = [
    '_ensure_api_columns',
    '_get_conn',
    '_init_tables',
    'create_api_definition',
    'get_api_definition',
    'list_api_definitions',
    'update_api_definition',
    'delete_api_definition',
    'list_trash_definitions',
    'restore_definition',
    'create_api_test_case',
    'get_api_test_case',
    'list_api_test_cases',
    'update_api_test_case',
    'delete_api_test_case',
    'list_trash_cases',
    'restore_case',
    'create_scenario',
    'get_scenario',
    'list_scenarios',
    'update_scenario',
    'delete_scenario',
    'list_trash_scenarios',
    'restore_scenario',
    'create_mock_service',
    'get_mock_service',
    'list_mock_services',
    'update_mock_service',
    'delete_mock_service',
    'list_trash_mocks',
    'restore_mock',
    'create_environment',
    'get_environment',
    'list_environments',
    'update_environment',
    'delete_environment',
    'create_assertion_rule',
    'get_assertion_rule',
    'list_assertion_rules',
    'delete_assertion_rule',
    'import_from_postman',
    'import_from_swagger',
    'debug_api_call',
    '_log_debug_call',
    'list_debug_logs',
    'clear_debug_logs',
    'execute_scenario',
]
