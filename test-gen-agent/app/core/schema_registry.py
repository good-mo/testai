"""
Schema Registry：统一管理所有数据库表结构声明（Phase D · 地基）。

⚠ 本文件由 scripts/sync_schema_registry.py 自动生成，请勿手工编辑。

单一来源约定：
  - 所有表：唯一权威来源是「模块内联的 CREATE TABLE」，本文件据此自动生成。
    修改某模块表结构后执行 scripts/sync_schema_registry.py --update 重新生成；
    CI 以 --check 校验漂移。
  - 跨模块共享表（api_definitions）已在各模块代码中收敛为同一 DDL，此处仅记录来源。

用途：
  1. 作为表结构的唯一可查清单（审计 / 漂移检测）
  2. 供 Alembic 迁移基线生成时参考
  3. 为 Repository 层与未来 ORM 迁移提供 DDL 出处
"""

# ── 表来源映射 ───────────────────────────────────────────────
# {table_name: ["file:line", ...]}
TABLE_SOURCES: dict = {
    "ai_configs": ["app/repositories/ai_config_repo.py:45"],
    "ai_conversation_messages": ["app/repositories/ai_conversation_repo.py:56"],
    "ai_conversations": ["app/repositories/ai_conversation_repo.py:38"],
    "ai_model_sources": ["app/repositories/ai_model_repo.py:52"],
    "alerts": ["app/environment/manager.py:115"],
    "api_cases": ["app/apitest/store/_base.py:56"],
    "api_definition_versions": ["app/apitest/store/_base.py:225"],
    "api_definitions": ["app/apitest/schema_ddl.py:50"],
    "api_environments": ["app/apitest/store/_base.py:145"],
    "api_execution_logs": ["app/apitest/execution_log.py:31"],
    "api_follows": ["app/apitest/store/ops.py:54"],
    "api_keys": ["app/auth/store.py:222"],
    "api_mocks": ["app/apitest/store/_base.py:113"],
    "api_operation_logs": ["app/apitest/store/_base.py:204"],
    "api_scenarios": ["app/apitest/store/_base.py:89"],
    "api_test_cases": ["app/api_testing/management/_base.py:44"],
    "assertion_rules": ["app/api_testing/management/_base.py:103"],
    "case_change_logs": ["app/cases/management/_base.py:160"],
    "case_dependencies": ["app/cases/management/_base.py:106"],
    "case_relations": ["app/cases/management/_base.py:85"],
    "case_requirements": ["app/cases/management/_base.py:190"],
    "case_review_case_links": ["app/repositories/case_review_repo.py:77"],
    "case_review_follows": ["app/repositories/case_review_repo.py:93"],
    "case_review_headers": ["app/repositories/case_review_repo.py:51"],
    "case_reviews": ["app/cases/management/_base.py:124"],
    "case_trash": ["app/cases/management/_base.py:178"],
    "case_versions": ["app/cases/management/_base.py:142"],
    "custom_funcs": ["app/repositories/project_repo.py:413"],
    "dashboard_layouts": ["app/repositories/test_plan_repo.py:654"],
    "data_batches": ["app/repositories/datafactory_repo.py:76"],
    "data_templates": ["app/repositories/datafactory_repo.py:62"],
    "debug_items": ["app/repositories/debug_repo.py:36"],
    "defect_comments": ["app/repositories/defect_repo.py:68"],
    "defects": ["app/repositories/defect_repo.py:46"],
    "env_groups": ["app/apitest/store/_base.py:170"],
    "environments": ["app/environment/manager.py:55"],
    "execution_history": ["app/repositories/script_repo.py:67"],
    "fake_error_rules": ["app/repositories/fake_error_repo.py:54"],
    "global_params": ["app/apitest/store/_base.py:186"],
    "invitations": ["app/repositories/invitation_repo.py:39"],
    "message_tasks": ["app/repositories/message_repo.py:57"],
    "mock_services": ["app/api_testing/management/_base.py:82"],
    "modules": ["app/apitest/module_store.py:31"],
    "notifications": ["app/repositories/message_repo.py:75"],
    "organization_members": ["app/repositories/organization_repo.py:69"],
    "organizations": ["app/repositories/organization_repo.py:52"],
    "page_display_configs": ["app/repositories/display_config_repo.py:42"],
    "project_app_configs": ["app/repositories/project_app_config_repo.py:33"],
    "project_custom_fields": ["app/repositories/project_repo.py:559"],
    "project_envs": ["app/repositories/project_repo.py:72"],
    "project_files": ["app/repositories/file_repo.py (dynamic)"],
    "project_members": ["app/repositories/project_repo.py:82"],
    "project_robots": ["app/repositories/message_repo.py:39"],
    "project_versions": ["app/repositories/project_version_repo.py:47"],
    "projects": ["app/repositories/project_repo.py:45"],
    "resource_pools": ["app/repositories/resource_pool_repo.py:15"],
    "run_records": ["app/repositories/run_repo.py:44"],
    "scripts": ["app/repositories/script_repo.py:48"],
    "sessions": ["app/auth/store.py:202"],
    "tasks": ["app/repositories/task_repo.py:58"],
    "templates": ["app/repositories/template_repo.py:26"],
    "test_cases": ["app/repositories/case_repo.py:131"],
    "test_plan_cases": ["app/repositories/test_plan_repo.py:85"],
    "test_plan_modules": ["app/repositories/test_plan_repo.py:96"],
    "test_plan_schedules": ["app/repositories/test_plan_repo.py:106"],
    "test_plans": ["app/repositories/test_plan_repo.py:59"],
    "test_runs": ["app/insights/trace.py:48"],
    "user_group_members": ["app/repositories/user_group_repo.py:110"],
    "user_group_permissions": ["app/repositories/user_group_repo.py:130"],
    "user_groups": ["app/repositories/user_group_repo.py:92"],
    "user_local_configs": ["app/auth/store.py:212"],
    "user_views": ["app/repositories/user_view_repo.py:36"],
    "users": ["app/auth/store.py:181"],
    "workflow_flows": ["app/repositories/workflow_repo.py:50"],
    "workflow_statuses": ["app/repositories/workflow_repo.py:34"],
}

# ── 逻辑库映射 ───────────────────────────────────────────────
# 大部分逻辑库（auth.db / apitest.db 等）经 app.db 统一映射到 tga.db。
LOGICAL_DB_MAP: dict = {
    "ai_configs": "tga.db",
    "ai_conversation_messages": "tga.db",
    "ai_conversations": "tga.db",
    "ai_model_sources": "auth.db",
    "alerts": "environments.db",
    "api_cases": "apitest.db",
    "api_definition_versions": "apitest.db",
    "api_definitions": "apitest.db",
    "api_environments": "apitest.db",
    "api_execution_logs": "apitest.db",
    "api_follows": "apitest.db",
    "api_keys": "auth.db",
    "api_mocks": "apitest.db",
    "api_operation_logs": "apitest.db",
    "api_scenarios": "apitest.db",
    "api_test_cases": "apitest.db",
    "assertion_rules": "apitest.db",
    "case_change_logs": "tga.db",
    "case_dependencies": "tga.db",
    "case_relations": "tga.db",
    "case_requirements": "tga.db",
    "case_review_case_links": "testcases.db",
    "case_review_follows": "testcases.db",
    "case_review_headers": "testcases.db",
    "case_reviews": "tga.db",
    "case_trash": "tga.db",
    "case_versions": "tga.db",
    "custom_funcs": "projects.db",
    "dashboard_layouts": "tga.db",
    "data_batches": "tga.db",
    "data_templates": "tga.db",
    "debug_items": "apitest.db",
    "defect_comments": "defects.db",
    "defects": "defects.db",
    "env_groups": "apitest.db",
    "environments": "environments.db",
    "execution_history": "tga.db",
    "fake_error_rules": "projects.db",
    "global_params": "apitest.db",
    "invitations": "auth.db",
    "message_tasks": "tga.db",
    "mock_services": "apitest.db",
    "modules": "apitest.db",
    "notifications": "tga.db",
    "organization_members": "projects.db",
    "organizations": "projects.db",
    "page_display_configs": "auth.db",
    "project_app_configs": "projects.db",
    "project_custom_fields": "projects.db",
    "project_envs": "projects.db",
    "project_files": "tga.db",
    "project_members": "projects.db",
    "project_robots": "tga.db",
    "project_versions": "projects.db",
    "projects": "projects.db",
    "resource_pools": "tga.db",
    "run_records": "tga.db",
    "scripts": "tga.db",
    "sessions": "auth.db",
    "tasks": "tga.db",
    "templates": "tga.db",
    "test_cases": "testcases.db",
    "test_plan_cases": "tga.db",
    "test_plan_modules": "tga.db",
    "test_plan_schedules": "tga.db",
    "test_plans": "tga.db",
    "test_runs": "trace.db",
    "user_group_members": "tga.db",
    "user_group_permissions": "tga.db",
    "user_groups": "tga.db",
    "user_local_configs": "auth.db",
    "user_views": "tga.db",
    "users": "auth.db",
    "workflow_flows": "tga.db",
    "workflow_statuses": "tga.db",
}

# ── 表结构 DDL 常量 ─────────────────────────────────────────
# 命名规范：DDL_<表名大写>；同名表多个不同版本以 _V2/_V3… 后缀区分。
# ⚠ 由 sync_schema_registry.py 从各模块内联 DDL 自动提取，勿手工维护。

DDL_AI_MODEL_SOURCES = """
CREATE TABLE IF NOT EXISTS ai_model_sources (
    id TEXT PRIMARY KEY,
    name TEXT DEFAULT '',
    type TEXT DEFAULT 'LLM',
    provider_name TEXT DEFAULT '',
    permission_type TEXT DEFAULT 'PUBLIC',
    status INTEGER DEFAULT 1,
    owner TEXT DEFAULT '',
    owner_type TEXT DEFAULT 'SYSTEM',
    base_name TEXT DEFAULT '',
    app_key TEXT DEFAULT '',
    api_url TEXT DEFAULT '',
    adv_setting TEXT DEFAULT '[]',
    create_user TEXT DEFAULT 'admin',
    create_time REAL,
    update_time REAL
)
"""

DDL_ALERTS = """
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    env_id TEXT,
    env_name TEXT DEFAULT '',
    level TEXT DEFAULT 'warning',
    message TEXT DEFAULT '',
    detail TEXT DEFAULT '',
    status TEXT DEFAULT 'open',
    created_at REAL,
    resolved_at REAL
)
"""

DDL_API_CASES = """
CREATE TABLE IF NOT EXISTS api_cases (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    api_definition_id TEXT DEFAULT '',
    request TEXT DEFAULT '{}',        -- 请求体（覆盖定义）
    asserts TEXT DEFAULT '[]',        -- 断言规则列表
    pre_scripts TEXT DEFAULT '[]',    -- 前置脚本
    post_scripts TEXT DEFAULT '[]',   -- 后置脚本
    pre_sql TEXT DEFAULT '[]',        -- 前置 SQL
    post_sql TEXT DEFAULT '[]',       -- 后置 SQL
    variables TEXT DEFAULT '[]',      -- 变量提取
    logic_controllers TEXT DEFAULT '[]',  -- 逻辑控制器
    environment_id TEXT DEFAULT '',
    status TEXT DEFAULT 'draft',
    priority TEXT DEFAULT 'P2',
    description TEXT DEFAULT '',
    project_id TEXT DEFAULT '',
    created_at REAL,
    updated_at REAL,
    metadata TEXT DEFAULT '{}',
    deleted INTEGER DEFAULT 0,
    deleted_at REAL
)
"""

DDL_API_DEFINITION_VERSIONS = """
CREATE TABLE IF NOT EXISTS api_definition_versions (
    id TEXT PRIMARY KEY,
    ref_id TEXT DEFAULT '',          -- 版本分组 ID（同一接口的多个版本共享）
    definition_id TEXT DEFAULT '',
    version TEXT DEFAULT 'v1',       -- 版本号
    version_id TEXT DEFAULT '',       -- 对应版本 ID
    snapshot TEXT DEFAULT '{}',       -- 版本快照
    created_at REAL,
    created_by TEXT DEFAULT ''
)
"""

DDL_API_DEFINITIONS = """
CREATE TABLE IF NOT EXISTS api_definitions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    protocol TEXT DEFAULT 'HTTP',      -- HTTP/TCP/SQL/DUBBO
    method TEXT DEFAULT 'GET',
    path TEXT DEFAULT '',
    headers TEXT DEFAULT '{}',         -- V2 请求头（apitest 主引擎）
    body TEXT DEFAULT '',
    query TEXT DEFAULT '{}',
    params TEXT DEFAULT '{}',
    description TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    module_id TEXT DEFAULT '',         -- 所属模块（模块树筛选，空=root）
    project_id TEXT DEFAULT '',
    version_id TEXT DEFAULT '',
    ref_id TEXT DEFAULT '',
    latest INTEGER DEFAULT 1,          -- 是否为最新版本
    created_at REAL,
    updated_at REAL,
    metadata TEXT DEFAULT '{}',
    deleted INTEGER DEFAULT 0,
    deleted_at REAL,
    -- V1 字段（api_testing 前端兼容层）
    request_headers TEXT DEFAULT '{}',
    request_params TEXT DEFAULT '{}',
    request_body TEXT DEFAULT '',
    request_body_type TEXT DEFAULT 'json',
    response_code TEXT DEFAULT '200',
    response_headers TEXT DEFAULT '{}',
    response_body TEXT DEFAULT '',
    response_body_type TEXT DEFAULT 'json',
    created_by TEXT DEFAULT 'system'
)
"""

DDL_API_ENVIRONMENTS = """
CREATE TABLE IF NOT EXISTS api_environments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    base_url TEXT DEFAULT '',
    headers TEXT DEFAULT '{}',
    variables TEXT DEFAULT '{}',
    description TEXT DEFAULT '',
    project_id TEXT DEFAULT '',
    script TEXT DEFAULT '',           -- 环境前置脚本
    database_config TEXT DEFAULT '{}', -- 数据库驱动配置
    config TEXT DEFAULT '{}',          -- 前端完整 EnvDetailItem 配置
    deleted INTEGER DEFAULT 0,         -- 0: 正常, 1: 已删除(回收站)
    deleted_at REAL,
    created_at REAL,
    updated_at REAL
)
"""

DDL_API_EXECUTION_LOGS = """
CREATE TABLE IF NOT EXISTS api_execution_logs (
    id TEXT PRIMARY KEY,
    exec_type TEXT DEFAULT 'case',      -- case/scenario/debug
    target_id TEXT DEFAULT '',          -- 用例ID或场景ID
    target_name TEXT DEFAULT '',
    method TEXT DEFAULT 'GET',
    url TEXT DEFAULT '',
    request_data TEXT DEFAULT '{}',      -- JSON: 完整请求
    response_data TEXT DEFAULT '{}',     -- JSON: 完整响应
    asserts TEXT DEFAULT '[]',           -- JSON: 断言结果
    extracted_variables TEXT DEFAULT '{}',-- JSON: 提取的变量
    passed INTEGER DEFAULT 0,
    response_code INTEGER DEFAULT 0,
    duration_ms REAL DEFAULT 0,
    error TEXT DEFAULT '',
    detail TEXT DEFAULT '{}',            -- JSON: 附加详情(场景步骤等)
    created_at REAL
)
"""

DDL_API_FOLLOWS = """
CREATE TABLE IF NOT EXISTS api_follows (
    id TEXT PRIMARY KEY,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    user_id TEXT DEFAULT 'admin',
    created_at REAL,
    UNIQUE(resource_type, resource_id, user_id)
)
"""

DDL_API_KEYS = """
CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    access_key TEXT DEFAULT '',
    secret_key TEXT DEFAULT '',
    description TEXT DEFAULT '',
    enable INTEGER DEFAULT 1,
    forever INTEGER DEFAULT 0,
    expire_time REAL DEFAULT 0,
    create_time REAL
)
"""

DDL_API_MOCKS = """
CREATE TABLE IF NOT EXISTS api_mocks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    api_definition_id TEXT DEFAULT '',
    method TEXT DEFAULT 'GET',
    path TEXT DEFAULT '',
    status_code INTEGER DEFAULT 200,
    response_body TEXT DEFAULT '',
    response_headers TEXT DEFAULT '{}',
    delay_ms INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    description TEXT DEFAULT '',
    project_id TEXT DEFAULT '',
    match_type TEXT DEFAULT 'exact',   -- exact/path/wildcard/script
    match_script TEXT DEFAULT '',       -- 复杂匹配脚本
    created_at REAL,
    updated_at REAL,
    deleted INTEGER DEFAULT 0,
    deleted_at REAL
)
"""

DDL_API_OPERATION_LOGS = """
CREATE TABLE IF NOT EXISTS api_operation_logs (
    id TEXT PRIMARY KEY,
    resource_type TEXT DEFAULT '',   -- definition/case/scenario/mock/environment
    resource_id TEXT DEFAULT '',
    resource_name TEXT DEFAULT '',
    action TEXT DEFAULT '',          -- create/update/delete/restore/recover/version
    operator TEXT DEFAULT '',
    detail TEXT DEFAULT '{}',
    project_id TEXT DEFAULT '',
    created_at REAL
)
"""

DDL_API_SCENARIOS = """
CREATE TABLE IF NOT EXISTS api_scenarios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    steps TEXT DEFAULT '[]',          -- 编排步骤（有序）
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'draft',
    environment_id TEXT DEFAULT '',
    project_id TEXT DEFAULT '',
    created_at REAL,
    updated_at REAL,
    metadata TEXT DEFAULT '{}',
    deleted INTEGER DEFAULT 0,
    deleted_at REAL
)
"""

DDL_API_TEST_CASES = """
CREATE TABLE IF NOT EXISTS api_test_cases (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    definition_id TEXT,
    method TEXT NOT NULL DEFAULT 'GET',
    path TEXT NOT NULL,
    request_headers TEXT DEFAULT '{}',
    request_params TEXT DEFAULT '{}',
    request_body TEXT DEFAULT '',
    request_body_type TEXT DEFAULT 'json',
    assertions TEXT DEFAULT '[]',      -- JSON 数组: [{type, field, value}]
    pre_scripts TEXT DEFAULT '[]',      -- JSON 数组
    post_scripts TEXT DEFAULT '[]',     -- JSON 数组
    pre_sql TEXT DEFAULT '',
    post_sql TEXT DEFAULT '',
    variables TEXT DEFAULT '{}',        -- JSON 对象: {name: {type, value}}
    enabled INTEGER DEFAULT 1,
    status TEXT DEFAULT 'draft',        -- draft/approved/deprecated
    environment_id TEXT,
    timeout INTEGER DEFAULT 30,
    retry_count INTEGER DEFAULT 0,
    created_at REAL,
    updated_at REAL,
    created_by TEXT DEFAULT 'system',
    deleted INTEGER DEFAULT 0,
    deleted_at REAL,
    project_id TEXT DEFAULT ''
)
"""

DDL_ASSERTION_RULES = """
CREATE TABLE IF NOT EXISTS assertion_rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    rule_type TEXT NOT NULL,   -- text/regex/jsonpath/xpath/status_code/header
    target TEXT DEFAULT '',
    expression TEXT DEFAULT '',
    expected TEXT DEFAULT '',
    description TEXT DEFAULT '',
    created_at REAL
)
"""

DDL_CASE_CHANGE_LOGS = """
CREATE TABLE IF NOT EXISTS case_change_logs (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    action TEXT NOT NULL,
    field TEXT DEFAULT '',
    old_value TEXT DEFAULT '',
    new_value TEXT DEFAULT '',
    operator TEXT DEFAULT '',
    created_at REAL
)
"""

DDL_CASE_DEPENDENCIES = """
CREATE TABLE IF NOT EXISTS case_dependencies (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    depends_on TEXT NOT NULL,
    dep_type TEXT DEFAULT 'before',  -- before=前置, after=后置
    description TEXT DEFAULT '',
    created_at REAL,
    FOREIGN KEY (case_id) REFERENCES test_cases(id),
    FOREIGN KEY (depends_on) REFERENCES test_cases(id)
)
"""

DDL_CASE_RELATIONS = """
CREATE TABLE IF NOT EXISTS case_relations (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    related_case_id TEXT NOT NULL,
    relation_type TEXT DEFAULT 'related',
    created_at REAL,
    FOREIGN KEY (case_id) REFERENCES test_cases(id),
    FOREIGN KEY (related_case_id) REFERENCES test_cases(id)
)
"""

DDL_CASE_REQUIREMENTS = """
CREATE TABLE IF NOT EXISTS case_requirements (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    requirement_id TEXT NOT NULL,   -- JIRA/TAPD 工单号
    requirement_type TEXT DEFAULT 'jira',  -- jira/tapd
    requirement_title TEXT DEFAULT '',
    requirement_url TEXT DEFAULT '',
    created_at REAL,
    FOREIGN KEY (case_id) REFERENCES test_cases(id)
)
"""

DDL_CASE_REVIEW_CASE_LINKS = """
CREATE TABLE IF NOT EXISTS case_review_case_links (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    status TEXT DEFAULT 'UN_REVIEWED',
    reviewer TEXT DEFAULT '',
    comment TEXT DEFAULT '',
    create_time REAL,
    update_time REAL
)
"""

DDL_CASE_REVIEW_FOLLOWS = """
CREATE TABLE IF NOT EXISTS case_review_follows (
    review_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    create_time REAL,
    PRIMARY KEY (review_id, user_id)
)
"""

DDL_CASE_REVIEW_HEADERS = """
CREATE TABLE IF NOT EXISTS case_review_headers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    num INTEGER DEFAULT 1,
    module_id TEXT DEFAULT 'root',
    project_id TEXT DEFAULT '',
    status TEXT DEFAULT 'UNDERWAY',
    review_pass_rule TEXT DEFAULT 'SINGLE',
    pos INTEGER DEFAULT 0,
    start_time REAL DEFAULT 0,
    end_time REAL DEFAULT 0,
    tags TEXT DEFAULT '[]',
    description TEXT DEFAULT '',
    create_time REAL,
    create_user TEXT DEFAULT 'admin',
    update_time REAL,
    update_user TEXT DEFAULT 'admin',
    deleted INTEGER DEFAULT 0,
    reviewers_json TEXT DEFAULT '[]'  -- 评审人 JSON 数组
)
"""

DDL_CASE_REVIEWS = """
CREATE TABLE IF NOT EXISTS case_reviews (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    review_status TEXT DEFAULT 'pending',
    reviewer TEXT DEFAULT '',
    comment TEXT DEFAULT '',
    created_at REAL,
    reviewed_at REAL,
    FOREIGN KEY (case_id) REFERENCES test_cases(id)
)
"""

DDL_CASE_TRASH = """
CREATE TABLE IF NOT EXISTS case_trash (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    case_data TEXT NOT NULL,
    deleted_at REAL,
    deleted_by TEXT DEFAULT '',
    reason TEXT DEFAULT ''
)
"""

DDL_CASE_VERSIONS = """
CREATE TABLE IF NOT EXISTS case_versions (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    snapshot TEXT NOT NULL,
    created_at REAL,
    created_by TEXT DEFAULT '',
    change_desc TEXT DEFAULT '',
    FOREIGN KEY (case_id) REFERENCES test_cases(id)
)
"""

DDL_CUSTOM_FUNCS = """
CREATE TABLE IF NOT EXISTS custom_funcs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    script TEXT DEFAULT '',
    type TEXT DEFAULT 'HTTP',
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'DRAFT',
    project_id TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    params TEXT DEFAULT '[]',
    result TEXT DEFAULT '',
    internal INTEGER DEFAULT 0,
    create_time REAL,
    update_time REAL,
    create_user TEXT DEFAULT 'admin',
    update_user TEXT DEFAULT 'admin'
)
"""

DDL_DASHBOARD_LAYOUTS = """
CREATE TABLE IF NOT EXISTS dashboard_layouts (
    org_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    layout TEXT NOT NULL DEFAULT '[]',
    updated_at REAL,
    PRIMARY KEY (org_id, user_id)
)
"""

DDL_DATA_BATCHES = """
CREATE TABLE IF NOT EXISTS data_batches (
    id TEXT PRIMARY KEY,
    template_id TEXT,
    template_name TEXT DEFAULT '',
    batch_size INTEGER DEFAULT 1,
    env_key TEXT DEFAULT 'default',
    data_json TEXT DEFAULT '[]',
    status TEXT DEFAULT 'active',
    created_at REAL,
    updated_at REAL
)
"""

DDL_DATA_TEMPLATES = """
CREATE TABLE IF NOT EXISTS data_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'custom',
    schema_json TEXT DEFAULT '{}',
    deps_json TEXT DEFAULT '[]',
    tags TEXT DEFAULT '[]',
    status TEXT DEFAULT 'active',
    created_at REAL,
    updated_at REAL
)
"""

DDL_DEBUG_ITEMS = """
CREATE TABLE IF NOT EXISTS debug_items (
    id TEXT PRIMARY KEY,
    name TEXT DEFAULT '',
    protocol TEXT DEFAULT 'HTTP',
    method TEXT DEFAULT 'GET',
    path TEXT DEFAULT '/',
    url TEXT DEFAULT '/',
    project_id TEXT DEFAULT '',
    module_id TEXT DEFAULT 'root',
    request_data TEXT DEFAULT '{}',
    response_data TEXT DEFAULT '{}',
    create_time REAL,
    update_time REAL,
    create_user TEXT DEFAULT 'admin',
    update_user TEXT DEFAULT 'admin',
    num INTEGER DEFAULT 0
)
"""

DDL_DEFECT_COMMENTS = """
CREATE TABLE IF NOT EXISTS defect_comments (
    id TEXT PRIMARY KEY,
    bug_id TEXT NOT NULL,
    parent_id TEXT DEFAULT '',
    content TEXT DEFAULT '',
    create_user TEXT DEFAULT '',
    reply_user TEXT DEFAULT '',
    notifier TEXT DEFAULT '',
    create_time REAL,
    update_time REAL,
    deleted INTEGER DEFAULT 0
)
"""

DDL_DEFECTS = """
CREATE TABLE IF NOT EXISTS defects (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    severity TEXT DEFAULT 'major',
    status TEXT DEFAULT 'open',
    file_path TEXT DEFAULT '',
    test_case_id TEXT DEFAULT '',
    error_snippet TEXT DEFAULT '',
    created_at REAL,
    updated_at REAL,
    assignee TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    deleted INTEGER DEFAULT 0,
    deleted_at REAL
)
"""

DDL_ENV_GROUPS = """
CREATE TABLE IF NOT EXISTS env_groups (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    project_id TEXT DEFAULT '',
    env_group_project TEXT DEFAULT '[]',
    pos INTEGER DEFAULT 0,
    created_at REAL,
    updated_at REAL
)
"""

DDL_ENVIRONMENTS = """
CREATE TABLE IF NOT EXISTS environments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    env_type TEXT DEFAULT 'docker',
    status TEXT DEFAULT 'offline',
    endpoint TEXT DEFAULT '',
    docker_compose_path TEXT DEFAULT '',
    container_name TEXT DEFAULT '',
    image TEXT DEFAULT '',
    health_check_url TEXT DEFAULT '',
    owner TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    last_checked_at REAL,
    last_status_change REAL,
    error_message TEXT DEFAULT '',
    created_at REAL,
    updated_at REAL,
    deleted INTEGER DEFAULT 0,
    deleted_at REAL,
    project_id TEXT DEFAULT '',      -- 所属项目
    base_url TEXT DEFAULT '',        -- 基础 URL（兼容 api_environments 风格）
    headers TEXT DEFAULT '{}',       -- 默认请求头
    variables TEXT DEFAULT '{}',     -- 全局变量
    is_default INTEGER DEFAULT 0     -- 是否默认环境
)
"""

DDL_EXECUTION_HISTORY = """
CREATE TABLE IF NOT EXISTS execution_history (
    id TEXT PRIMARY KEY,
    script_id TEXT DEFAULT '',
    script_name TEXT DEFAULT '',
    success INTEGER DEFAULT 0,
    duration REAL DEFAULT 0,
    error_type TEXT DEFAULT '',
    error_message TEXT DEFAULT '',
    locator_failures_json TEXT DEFAULT '[]',
    created_at REAL
)
"""

DDL_FAKE_ERROR_RULES = """
CREATE TABLE IF NOT EXISTS fake_error_rules (
    id TEXT PRIMARY KEY,
    project_id TEXT DEFAULT '',
    name TEXT DEFAULT '',
    enable INTEGER DEFAULT 1,
    label TEXT DEFAULT '',
    rule TEXT DEFAULT '',
    rule_result TEXT DEFAULT '',
    create_user TEXT DEFAULT '',
    update_time REAL,
    created_at REAL,
    type TEXT DEFAULT '',          -- 错误注入类型
    resp_type TEXT DEFAULT '',     -- 响应类型（RESPONSE_HEADERS/DATA/CODE）
    relation TEXT DEFAULT '',      -- 匹配关系（CONTAINS/EQUALS 等）
    expression TEXT DEFAULT ''     -- 匹配表达式
)
"""

DDL_GLOBAL_PARAMS = """
CREATE TABLE IF NOT EXISTS global_params (
    id TEXT PRIMARY KEY,
    project_id TEXT DEFAULT '',
    headers TEXT DEFAULT '[]',
    common_variables TEXT DEFAULT '[]',
    created_at REAL,
    updated_at REAL
)
"""

DDL_INVITATIONS = """
CREATE TABLE IF NOT EXISTS invitations (
    id TEXT PRIMARY KEY,
    invite_id TEXT NOT NULL UNIQUE,
    email TEXT DEFAULT '',
    scope TEXT DEFAULT 'SYSTEM',      -- SYSTEM / ORGANIZATION / PROJECT
    organization_id TEXT DEFAULT '',
    project_id TEXT DEFAULT '',
    role_ids TEXT DEFAULT '[]',        -- JSON 数组（user_group id）
    expire_time REAL,
    used INTEGER DEFAULT 0,
    create_time REAL,
    create_user TEXT DEFAULT 'admin'
)
"""

DDL_MESSAGE_TASKS = """
CREATE TABLE IF NOT EXISTS message_tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT DEFAULT '',
    task_type TEXT DEFAULT '',
    event TEXT DEFAULT '',
    robot_id TEXT DEFAULT '',
    receiver_ids TEXT DEFAULT '[]',
    subject TEXT DEFAULT '',
    template TEXT DEFAULT '',
    use_default_subject INTEGER DEFAULT 1,
    use_default_template INTEGER DEFAULT 1,
    enable INTEGER DEFAULT 0,
    create_time REAL,
    update_time REAL
)
"""

DDL_MOCK_SERVICES = """
CREATE TABLE IF NOT EXISTS mock_services (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'GET',
    path TEXT NOT NULL,
    response_code INTEGER DEFAULT 200,
    response_headers TEXT DEFAULT '{}',
    response_body TEXT DEFAULT '{}',
    delay_ms INTEGER DEFAULT 0,
    enabled INTEGER DEFAULT 1,
    created_at REAL,
    updated_at REAL,
    created_by TEXT DEFAULT 'system',
    deleted INTEGER DEFAULT 0,
    deleted_at REAL,
    project_id TEXT DEFAULT ''
)
"""

DDL_MODULES = """
CREATE TABLE IF NOT EXISTS modules (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,          -- definition / scenario / debug / functional
    name TEXT NOT NULL,
    parent_id TEXT DEFAULT 'root',
    pos INTEGER DEFAULT 1,
    project_id TEXT DEFAULT '',
    created_at REAL,
    updated_at REAL
)
"""

DDL_NOTIFICATIONS = """
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    type TEXT DEFAULT 'message',
    title TEXT DEFAULT '',
    sub_title TEXT DEFAULT '',
    content TEXT DEFAULT '',
    avatar TEXT DEFAULT '',
    resource_type TEXT DEFAULT '',
    resource_id TEXT DEFAULT '',
    resource_name TEXT DEFAULT '',
    operation TEXT DEFAULT '',
    receiver TEXT DEFAULT '',
    operator TEXT DEFAULT '',
    project_id TEXT DEFAULT '',
    organization_id TEXT DEFAULT '',
    status TEXT DEFAULT 'UNREAD',
    create_time REAL
)
"""

DDL_ORGANIZATION_MEMBERS = """
CREATE TABLE IF NOT EXISTS organization_members (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT DEFAULT '',
    name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    role TEXT DEFAULT 'member',   -- admin/member
    create_time REAL,
    update_time REAL
)
"""

DDL_ORGANIZATIONS = """
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    num INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',   -- active/disabled/deleted
    deleted INTEGER DEFAULT 0,
    create_time REAL,
    update_time REAL,
    create_user TEXT DEFAULT 'admin',
    update_user TEXT DEFAULT 'admin'
)
"""

DDL_PAGE_DISPLAY_CONFIGS = """
CREATE TABLE IF NOT EXISTS page_display_configs (
    param_key TEXT PRIMARY KEY,
    param_value TEXT DEFAULT '',
    param_type TEXT DEFAULT 'text',
    file_name TEXT DEFAULT '',
    updated_at REAL
)
"""

DDL_PROJECT_APP_CONFIGS = """
CREATE TABLE IF NOT EXISTS project_app_configs (
    project_id TEXT NOT NULL,
    module TEXT NOT NULL,          -- workstation/testPlan/bugManagement/...
    config_key TEXT NOT NULL,      -- API_CLEAN_REPORT 等
    config_value TEXT DEFAULT '',
    updated_at REAL,
    PRIMARY KEY (project_id, module, config_key)
)
"""

DDL_PROJECT_CUSTOM_FIELDS = """
CREATE TABLE IF NOT EXISTS project_custom_fields (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    remark TEXT DEFAULT '',
    type TEXT DEFAULT 'INPUT',
    scene TEXT DEFAULT 'FUNCTIONAL',
    scope_id TEXT DEFAULT '',
    internal INTEGER DEFAULT 0,
    enable_option_key INTEGER DEFAULT 0,
    options TEXT DEFAULT '[]',
    used INTEGER DEFAULT 0,
    create_time REAL,
    update_time REAL,
    create_user TEXT DEFAULT 'admin',
    update_user TEXT DEFAULT 'admin'
)
"""

DDL_PROJECT_ENVS = """
CREATE TABLE IF NOT EXISTS project_envs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    env_id TEXT NOT NULL,
    created_at REAL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
)
"""

DDL_PROJECT_FILES = """
CREATE TABLE IF NOT EXISTS project_files (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    project_id TEXT DEFAULT '',
    module_id TEXT DEFAULT 'root',
    create_user TEXT DEFAULT '',
    update_user TEXT DEFAULT '',
    storage TEXT DEFAULT 'minio',
    file_type TEXT DEFAULT 'FILE',
    enable INTEGER DEFAULT 1,
    description TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    size INTEGER DEFAULT 0,
    created_at REAL,
    updated_at REAL
)
"""

DDL_PROJECT_MEMBERS = """
CREATE TABLE IF NOT EXISTS project_members (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT DEFAULT '',
    name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    role TEXT DEFAULT 'member',  -- admin/member/guest
    user_group TEXT DEFAULT '',
    created_at REAL,
    updated_at REAL
)
"""

DDL_PROJECT_ROBOTS = """
CREATE TABLE IF NOT EXISTS project_robots (
    id TEXT PRIMARY KEY,
    project_id TEXT DEFAULT '',
    name TEXT DEFAULT '',
    platform TEXT DEFAULT 'CUSTOM',
    type TEXT DEFAULT 'CUSTOM',
    webhook TEXT DEFAULT '',
    app_key TEXT DEFAULT '',
    app_secret TEXT DEFAULT '',
    enable INTEGER DEFAULT 1,
    description TEXT DEFAULT '',
    create_user TEXT DEFAULT 'admin',
    create_time REAL,
    update_user TEXT DEFAULT 'admin',
    update_time REAL
)
"""

DDL_PROJECT_VERSIONS = """
CREATE TABLE IF NOT EXISTS project_versions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status INTEGER DEFAULT 0,
    latest INTEGER DEFAULT 0,
    publish_time REAL,
    create_time REAL,
    create_user TEXT DEFAULT 'admin',
    update_time REAL
)
"""

DDL_PROJECTS = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    repo_url TEXT DEFAULT '',
    language TEXT DEFAULT 'python',
    path TEXT DEFAULT '',
    status TEXT DEFAULT 'active',  -- active/archived/deleted
    organization_id TEXT DEFAULT '',  -- 所属组织
    deleted INTEGER DEFAULT 0,       -- 0: 正常, 1: 已删除(回收站)
    deleted_at REAL,
    created_at REAL,
    updated_at REAL
)
"""

DDL_RESOURCE_POOLS = """
CREATE TABLE IF NOT EXISTS resource_pools (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    enable INTEGER DEFAULT 1,
    created_at REAL,
    updated_at REAL
)
"""

DDL_RUN_RECORDS = """
CREATE TABLE IF NOT EXISTS run_records (
    id TEXT PRIMARY KEY,
    source TEXT DEFAULT 'single',
    file_path TEXT DEFAULT '',
    source_code TEXT DEFAULT '',
    generated_tests TEXT DEFAULT '',
    test_result TEXT DEFAULT '{}',
    coverage_report TEXT DEFAULT '{}',
    performance_report TEXT DEFAULT '{}',
    retry_count INTEGER DEFAULT 0,
    passed INTEGER DEFAULT 0,
    saved_to TEXT DEFAULT '',
    error TEXT DEFAULT '',
    created_at REAL,
    metadata TEXT DEFAULT '{}'
)
"""

DDL_SCRIPTS = """
CREATE TABLE IF NOT EXISTS scripts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT DEFAULT '',
    framework TEXT DEFAULT 'pytest',
    description TEXT DEFAULT '',
    locators_json TEXT DEFAULT '[]',
    total_runs INTEGER DEFAULT 0,
    success_runs INTEGER DEFAULT 0,
    fail_runs INTEGER DEFAULT 0,
    last_run_at REAL,
    last_status TEXT DEFAULT '',
    health_score REAL DEFAULT 100.0,
    status TEXT DEFAULT 'healthy',
    created_at REAL,
    updated_at REAL
)
"""

DDL_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    csrf_token TEXT NOT NULL,
    create_time REAL,
    expire_time REAL,
    ip TEXT DEFAULT ''
)
"""

DDL_TASKS = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    created_at REAL,
    started_at REAL,
    finished_at REAL,
    result TEXT,
    error TEXT,
    coro_name TEXT DEFAULT '',
    args TEXT DEFAULT '[]',
    handler_name TEXT DEFAULT '',
    handler_args TEXT DEFAULT '[]',
    handler_kwargs TEXT DEFAULT '{}',
    restartable INTEGER DEFAULT 0,
    claimed_by TEXT DEFAULT ''
)
"""

DDL_TEMPLATES = """
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    remark TEXT DEFAULT '',
    scene TEXT DEFAULT 'FUNCTIONAL',
    scope_type TEXT DEFAULT 'PROJECT',
    scope_id TEXT DEFAULT '',
    internal INTEGER DEFAULT 0,
    enable_default INTEGER DEFAULT 0,
    enable_third_part INTEGER DEFAULT 0,
    ref_id TEXT DEFAULT '',
    platform_default INTEGER DEFAULT 0,
    custom_fields TEXT DEFAULT '[]',
    system_fields TEXT DEFAULT '[]',
    upload_img_file_ids TEXT DEFAULT '[]',
    create_time REAL,
    update_time REAL,
    create_user TEXT DEFAULT 'admin',
    update_user TEXT DEFAULT 'admin'
)
"""

DDL_TEST_CASES = """
CREATE TABLE IF NOT EXISTS test_cases (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    source_code TEXT DEFAULT '',
    test_code TEXT DEFAULT '',
    file_path TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    status TEXT DEFAULT 'draft',
    priority TEXT DEFAULT 'P2',
    requirement_ref TEXT DEFAULT '',
    created_at REAL,
    updated_at REAL,
    last_result TEXT DEFAULT '',
    metadata TEXT DEFAULT '{}',
    structured_cases TEXT DEFAULT '[]'
)
"""

DDL_TEST_PLAN_CASES = """
CREATE TABLE IF NOT EXISTS test_plan_cases (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    case_type TEXT DEFAULT 'functional',
    status TEXT DEFAULT 'pending',
    execute_time REAL DEFAULT 0,
    created_at REAL
)
"""

DDL_TEST_PLAN_MODULES = """
CREATE TABLE IF NOT EXISTS test_plan_modules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT DEFAULT 'root',
    project_id TEXT DEFAULT '',
    pos INTEGER DEFAULT 0,
    created_at REAL
)
"""

DDL_TEST_PLAN_SCHEDULES = """
CREATE TABLE IF NOT EXISTS test_plan_schedules (
    plan_id TEXT PRIMARY KEY,
    cron TEXT NOT NULL DEFAULT '',
    enable INTEGER DEFAULT 1,
    run_mode TEXT DEFAULT 'SERIAL',
    project_id TEXT DEFAULT '',
    updated_at REAL,
    created_at REAL
)
"""

DDL_TEST_PLANS = """
CREATE TABLE IF NOT EXISTS test_plans (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'prepared',
    priority TEXT DEFAULT 'P2',
    module_id TEXT DEFAULT 'root',
    project_id TEXT DEFAULT '',
    created_by TEXT DEFAULT 'admin',
    created_at REAL,
    updated_at REAL,
    start_time REAL DEFAULT 0,
    end_time REAL DEFAULT 0,
    execution_rate REAL DEFAULT 0,
    pass_rate REAL DEFAULT 0,
    tags TEXT DEFAULT '[]',
    pass_threshold REAL DEFAULT 100,
    test_planning INTEGER DEFAULT 0,
    auto_update_status INTEGER DEFAULT 0,
    repeat_case INTEGER DEFAULT 0,
    metadata TEXT DEFAULT '{}',
    type TEXT DEFAULT 'TEST_PLAN',
    group_id TEXT DEFAULT 'NONE'
)
"""

DDL_TEST_RUNS = """
CREATE TABLE IF NOT EXISTS test_runs (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    source_hash TEXT DEFAULT '',
    result TEXT DEFAULT 'unknown',      -- passed / failed / error
    passed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    coverage REAL DEFAULT 0,
    env_info TEXT DEFAULT '{}',          -- 运行环境 JSON
    attribution TEXT DEFAULT '',
    note TEXT DEFAULT '',
    created_at REAL,
    created_by TEXT DEFAULT ''
)
"""

DDL_USER_GROUP_MEMBERS = """
CREATE TABLE IF NOT EXISTS user_group_members (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT DEFAULT '',
    name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    type TEXT DEFAULT 'SYSTEM',
    scope_id TEXT DEFAULT '',
    create_time REAL,
    update_time REAL
)
"""

DDL_USER_GROUP_PERMISSIONS = """
CREATE TABLE IF NOT EXISTS user_group_permissions (
    group_id TEXT PRIMARY KEY,
    permissions TEXT DEFAULT '[]',
    update_time REAL
)
"""

DDL_USER_GROUPS = """
CREATE TABLE IF NOT EXISTS user_groups (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    internal INTEGER DEFAULT 0,
    type TEXT DEFAULT 'SYSTEM',      -- SYSTEM/ORGANIZATION/PROJECT
    scope_id TEXT DEFAULT '',
    pos INTEGER DEFAULT 99,
    create_time REAL,
    update_time REAL,
    create_user TEXT DEFAULT 'admin',
    update_user TEXT DEFAULT 'admin'
)
"""

DDL_USER_LOCAL_CONFIGS = """
CREATE TABLE IF NOT EXISTS user_local_configs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    user_url TEXT DEFAULT '',
    type TEXT DEFAULT 'API',
    enable INTEGER DEFAULT 0,
    create_time REAL
)
"""

DDL_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    avatar TEXT DEFAULT '',
    name TEXT DEFAULT '',
    role TEXT DEFAULT 'user',
    enable INTEGER DEFAULT 1,
    create_time REAL,
    update_time REAL,
    create_user TEXT DEFAULT 'system',
    update_user TEXT DEFAULT 'system',
    deleted INTEGER DEFAULT 0,
    language TEXT DEFAULT 'zh-CN',
    last_organization_id TEXT DEFAULT '',
    last_project_id TEXT DEFAULT ''
)
"""

DDL_WORKFLOW_FLOWS = """
CREATE TABLE IF NOT EXISTS workflow_flows (
    source_status_id TEXT,
    target_status_id TEXT,
    PRIMARY KEY (source_status_id, target_status_id)
)
"""

DDL_WORKFLOW_STATUSES = """
CREATE TABLE IF NOT EXISTS workflow_statuses (
    id TEXT PRIMARY KEY,
    scope_type TEXT DEFAULT 'PROJECT',
    scope_id TEXT DEFAULT '',
    scene TEXT DEFAULT 'FUNCTIONAL',
    name TEXT DEFAULT '',
    remark TEXT DEFAULT '',
    pos INTEGER DEFAULT 0,
    status_definitions TEXT DEFAULT '[]',
    internal INTEGER DEFAULT 0,
    create_time REAL,
    update_time REAL,
    create_user TEXT DEFAULT 'admin'
)
"""

DDL_AI_CONFIGS = """
CREATE TABLE IF NOT EXISTS ai_configs (
    id TEXT PRIMARY KEY,
    scope TEXT DEFAULT '',
    config_type TEXT DEFAULT '',
    owner TEXT DEFAULT '',
    owner_type TEXT DEFAULT 'PERSONAL',
    project_id TEXT DEFAULT '',
    config_value TEXT DEFAULT '{}',
    create_user TEXT DEFAULT 'admin',
    create_time REAL,
    update_time REAL
)
"""

DDL_AI_CONVERSATIONS = """
CREATE TABLE IF NOT EXISTS ai_conversations (
    id TEXT PRIMARY KEY,
    title TEXT DEFAULT '新对话',
    owner TEXT DEFAULT '',
    owner_type TEXT DEFAULT 'PERSONAL',
    project_id TEXT DEFAULT '',
    module_type TEXT DEFAULT 'ai',
    meta TEXT DEFAULT '{}',
    create_user TEXT DEFAULT 'admin',
    create_time REAL,
    update_time REAL
)
"""

DDL_AI_CONVERSATION_MESSAGES = """
CREATE TABLE IF NOT EXISTS ai_conversation_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT DEFAULT '',
    role TEXT DEFAULT 'user',
    type TEXT DEFAULT 'text',
    content TEXT DEFAULT '',
    message_meta TEXT DEFAULT '{}',
    create_time REAL
)
"""

DDL_USER_VIEWS = """
CREATE TABLE IF NOT EXISTS user_views (
    id TEXT PRIMARY KEY,
    view_type TEXT NOT NULL,
    scope_id TEXT DEFAULT '',
    user_id TEXT DEFAULT 'admin',
    name TEXT DEFAULT '',
    search_mode TEXT DEFAULT 'AND',
    pos INTEGER DEFAULT 0,
    payload TEXT DEFAULT '{}',
    create_time REAL,
    update_time REAL
)
"""
# ── 统一注册表 ────────────────────────────────────────────
# {table_name: DDL 常量}，同名冲突时默认取第一个来源的 DDL（V1）。
TABLE_DDL: dict = {
    "ai_configs": DDL_AI_CONFIGS,
    "ai_conversation_messages": DDL_AI_CONVERSATION_MESSAGES,
    "ai_conversations": DDL_AI_CONVERSATIONS,
    "ai_model_sources": DDL_AI_MODEL_SOURCES,
    "alerts": DDL_ALERTS,
    "api_cases": DDL_API_CASES,
    "api_definition_versions": DDL_API_DEFINITION_VERSIONS,
    "api_definitions": DDL_API_DEFINITIONS,
    "api_environments": DDL_API_ENVIRONMENTS,
    "api_execution_logs": DDL_API_EXECUTION_LOGS,
    "api_follows": DDL_API_FOLLOWS,
    "api_keys": DDL_API_KEYS,
    "api_mocks": DDL_API_MOCKS,
    "api_operation_logs": DDL_API_OPERATION_LOGS,
    "api_scenarios": DDL_API_SCENARIOS,
    "api_test_cases": DDL_API_TEST_CASES,
    "assertion_rules": DDL_ASSERTION_RULES,
    "case_change_logs": DDL_CASE_CHANGE_LOGS,
    "case_dependencies": DDL_CASE_DEPENDENCIES,
    "case_relations": DDL_CASE_RELATIONS,
    "case_requirements": DDL_CASE_REQUIREMENTS,
    "case_review_case_links": DDL_CASE_REVIEW_CASE_LINKS,
    "case_review_follows": DDL_CASE_REVIEW_FOLLOWS,
    "case_review_headers": DDL_CASE_REVIEW_HEADERS,
    "case_reviews": DDL_CASE_REVIEWS,
    "case_trash": DDL_CASE_TRASH,
    "case_versions": DDL_CASE_VERSIONS,
    "custom_funcs": DDL_CUSTOM_FUNCS,
    "dashboard_layouts": DDL_DASHBOARD_LAYOUTS,
    "data_batches": DDL_DATA_BATCHES,
    "data_templates": DDL_DATA_TEMPLATES,
    "debug_items": DDL_DEBUG_ITEMS,
    "defect_comments": DDL_DEFECT_COMMENTS,
    "defects": DDL_DEFECTS,
    "env_groups": DDL_ENV_GROUPS,
    "environments": DDL_ENVIRONMENTS,
    "execution_history": DDL_EXECUTION_HISTORY,
    "fake_error_rules": DDL_FAKE_ERROR_RULES,
    "global_params": DDL_GLOBAL_PARAMS,
    "invitations": DDL_INVITATIONS,
    "message_tasks": DDL_MESSAGE_TASKS,
    "mock_services": DDL_MOCK_SERVICES,
    "modules": DDL_MODULES,
    "notifications": DDL_NOTIFICATIONS,
    "organization_members": DDL_ORGANIZATION_MEMBERS,
    "organizations": DDL_ORGANIZATIONS,
    "page_display_configs": DDL_PAGE_DISPLAY_CONFIGS,
    "project_app_configs": DDL_PROJECT_APP_CONFIGS,
    "project_custom_fields": DDL_PROJECT_CUSTOM_FIELDS,
    "project_envs": DDL_PROJECT_ENVS,
    "project_files": DDL_PROJECT_FILES,
    "project_members": DDL_PROJECT_MEMBERS,
    "project_robots": DDL_PROJECT_ROBOTS,
    "project_versions": DDL_PROJECT_VERSIONS,
    "projects": DDL_PROJECTS,
    "resource_pools": DDL_RESOURCE_POOLS,
    "run_records": DDL_RUN_RECORDS,
    "scripts": DDL_SCRIPTS,
    "sessions": DDL_SESSIONS,
    "tasks": DDL_TASKS,
    "templates": DDL_TEMPLATES,
    "test_cases": DDL_TEST_CASES,
    "test_plan_cases": DDL_TEST_PLAN_CASES,
    "test_plan_modules": DDL_TEST_PLAN_MODULES,
    "test_plan_schedules": DDL_TEST_PLAN_SCHEDULES,
    "test_plans": DDL_TEST_PLANS,
    "test_runs": DDL_TEST_RUNS,
    "user_group_members": DDL_USER_GROUP_MEMBERS,
    "user_group_permissions": DDL_USER_GROUP_PERMISSIONS,
    "user_groups": DDL_USER_GROUPS,
    "user_local_configs": DDL_USER_LOCAL_CONFIGS,
    "user_views": DDL_USER_VIEWS,
    "users": DDL_USERS,
    "workflow_flows": DDL_WORKFLOW_FLOWS,
    "workflow_statuses": DDL_WORKFLOW_STATUSES,
}

# 同名表的多版本 DDL（用于冲突检测 / Alembic 决策）
TABLE_DDL_ALL: dict = {
    "ai_configs": [DDL_AI_CONFIGS],
    "ai_conversation_messages": [DDL_AI_CONVERSATION_MESSAGES],
    "ai_conversations": [DDL_AI_CONVERSATIONS],
    "ai_model_sources": [DDL_AI_MODEL_SOURCES],
    "alerts": [DDL_ALERTS],
    "api_cases": [DDL_API_CASES],
    "api_definition_versions": [DDL_API_DEFINITION_VERSIONS],
    "api_definitions": [DDL_API_DEFINITIONS],
    "api_environments": [DDL_API_ENVIRONMENTS],
    "api_execution_logs": [DDL_API_EXECUTION_LOGS],
    "api_follows": [DDL_API_FOLLOWS],
    "api_keys": [DDL_API_KEYS],
    "api_mocks": [DDL_API_MOCKS],
    "api_operation_logs": [DDL_API_OPERATION_LOGS],
    "api_scenarios": [DDL_API_SCENARIOS],
    "api_test_cases": [DDL_API_TEST_CASES],
    "assertion_rules": [DDL_ASSERTION_RULES],
    "case_change_logs": [DDL_CASE_CHANGE_LOGS],
    "case_dependencies": [DDL_CASE_DEPENDENCIES],
    "case_relations": [DDL_CASE_RELATIONS],
    "case_requirements": [DDL_CASE_REQUIREMENTS],
    "case_review_case_links": [DDL_CASE_REVIEW_CASE_LINKS],
    "case_review_follows": [DDL_CASE_REVIEW_FOLLOWS],
    "case_review_headers": [DDL_CASE_REVIEW_HEADERS],
    "case_reviews": [DDL_CASE_REVIEWS],
    "case_trash": [DDL_CASE_TRASH],
    "case_versions": [DDL_CASE_VERSIONS],
    "custom_funcs": [DDL_CUSTOM_FUNCS],
    "dashboard_layouts": [DDL_DASHBOARD_LAYOUTS],
    "data_batches": [DDL_DATA_BATCHES],
    "data_templates": [DDL_DATA_TEMPLATES],
    "debug_items": [DDL_DEBUG_ITEMS],
    "defect_comments": [DDL_DEFECT_COMMENTS],
    "defects": [DDL_DEFECTS],
    "env_groups": [DDL_ENV_GROUPS],
    "environments": [DDL_ENVIRONMENTS],
    "execution_history": [DDL_EXECUTION_HISTORY],
    "fake_error_rules": [DDL_FAKE_ERROR_RULES],
    "global_params": [DDL_GLOBAL_PARAMS],
    "invitations": [DDL_INVITATIONS],
    "message_tasks": [DDL_MESSAGE_TASKS],
    "mock_services": [DDL_MOCK_SERVICES],
    "modules": [DDL_MODULES],
    "notifications": [DDL_NOTIFICATIONS],
    "organization_members": [DDL_ORGANIZATION_MEMBERS],
    "organizations": [DDL_ORGANIZATIONS],
    "page_display_configs": [DDL_PAGE_DISPLAY_CONFIGS],
    "project_app_configs": [DDL_PROJECT_APP_CONFIGS],
    "project_custom_fields": [DDL_PROJECT_CUSTOM_FIELDS],
    "project_envs": [DDL_PROJECT_ENVS],
    "project_files": [DDL_PROJECT_FILES],
    "project_members": [DDL_PROJECT_MEMBERS],
    "project_robots": [DDL_PROJECT_ROBOTS],
    "project_versions": [DDL_PROJECT_VERSIONS],
    "projects": [DDL_PROJECTS],
    "resource_pools": [DDL_RESOURCE_POOLS],
    "run_records": [DDL_RUN_RECORDS],
    "scripts": [DDL_SCRIPTS],
    "sessions": [DDL_SESSIONS],
    "tasks": [DDL_TASKS],
    "templates": [DDL_TEMPLATES],
    "test_cases": [DDL_TEST_CASES],
    "test_plan_cases": [DDL_TEST_PLAN_CASES],
    "test_plan_modules": [DDL_TEST_PLAN_MODULES],
    "test_plan_schedules": [DDL_TEST_PLAN_SCHEDULES],
    "test_plans": [DDL_TEST_PLANS],
    "test_runs": [DDL_TEST_RUNS],
    "user_group_members": [DDL_USER_GROUP_MEMBERS],
    "user_group_permissions": [DDL_USER_GROUP_PERMISSIONS],
    "user_groups": [DDL_USER_GROUPS],
    "user_local_configs": [DDL_USER_LOCAL_CONFIGS],
    "user_views": [DDL_USER_VIEWS],
    "users": [DDL_USERS],
    "workflow_flows": [DDL_WORKFLOW_FLOWS],
    "workflow_statuses": [DDL_WORKFLOW_STATUSES],
}


# ── 工具函数 ───────────────────────────────────────────────

def get_table_ddl(table_name: str) -> str:
    """返回指定表的默认 DDL 声明（空串表示未注册）。"""
    return TABLE_DDL.get(table_name, "")


def list_all_tables() -> list:
    """返回按字典序排序的全部已注册表名。"""
    return sorted(TABLE_DDL.keys())


def get_table_sources(table_name: str) -> list:
    """返回指定表在代码中的来源文件与行号列表。"""
    return TABLE_SOURCES.get(table_name, [])


def get_duplicate_tables() -> list:
    """返回代码中出现多次的同名表清单。"""
    return [t for t, s in TABLE_SOURCES.items() if len(s) > 1]


def ensure_schema_consistent() -> list:
    """检查同名表是否有冲突 schema，返回冲突清单。"""
    conflicts = []
    for t in sorted(TABLE_SOURCES.keys()):
        all_variants = TABLE_DDL_ALL.get(t, [])
        unique_ddls = set(all_variants)
        if len(unique_ddls) > 1:
            conflicts.append({
                "table": t,
                "variant_count": len(unique_ddls),
                "sources": TABLE_SOURCES.get(t, []),
            })
    return conflicts


def audit_all_schemas() -> dict:
    """汇总注册表状态：表数量 / 重复表 / 冲突表。"""
    return {
        "total_tables": len(TABLE_DDL),
        "duplicates": get_duplicate_tables(),
        "conflicts": ensure_schema_consistent(),
    }


__all__ = [
    "TABLE_DDL", "TABLE_DDL_ALL", "TABLE_SOURCES", "LOGICAL_DB_MAP",
    "get_table_ddl", "list_all_tables", "get_table_sources",
    "get_duplicate_tables", "ensure_schema_consistent", "audit_all_schemas",
]
