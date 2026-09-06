# 数据库字段规范统一审计（时间戳 / 软删除 / JSON）

> 目标：把全库 75 张表的**时间戳 / 软删除 / JSON 承载字段**收敛到同一套规范，
> 并提供一个可被 CI 调用的审计工具持续拦截回潮。

## 统一规范

以现代业务表（`api_*`、`test_plan_*`、`projects`、`defects`、`environments` 等）为准：

| 维度 | 规范 | 说明 |
|------|------|------|
| 时间戳 | `created_at` / `updated_at`（REAL，epoch 秒） | 弃用遗留 `create_time` / `update_time` |
| 软删除 | `deleted`(0/1) + `deleted_at`(删除时刻 REAL) | 列表过滤 `deleted IS NULL OR deleted=0`；删除写 `deleted=1, deleted_at=now` |
| JSON 承载列 | `TEXT`（存 JSON 字符串） | 统一 `json.dumps` 写入 / `json.loads` 读取，禁止直接存 Python repr |

说明：API 层对外已统一映射为驼峰 `createTime / updateTime / deleted`，本规范针对**物理表列名 / 落库字段**。

## 审计方法

```bash
python3 scripts/sync_schema_registry.py --check-fields
```

该命令读取全仓所有 `CREATE TABLE IF NOT EXISTS`，对每张唯一表按其首个 DDL 检查
三类偏离并输出清单，存在偏离时返回非 0。

## 当前偏离盘点（基准 2026-09）

运行审计共发现 **31 处**偏离，主要分两类：

### A. 时间戳沿用遗留命名 `create_time / update_time`（约 28 处）
集中于老业务域，物理表列名与主域不一致：

- auth / 组织域：`users`、`sessions`、`api_keys`、`user_local_configs`、
  `organizations`、`organization_members`、`user_groups`、`user_group_members`、
  `user_group_permissions`、`invitations`
- AI 域：`ai_configs`、`ai_conversations`、`ai_conversation_messages`、`ai_model_sources`
- 消息/机器人域：`message_tasks`、`notifications`、`project_robots`
- 用例评审域：`case_review_headers`、`case_review_case_links`、`case_review_follows`
- 缺陷域：`defect_comments`
- 模板/自定义/调试/工作流：`templates`、`custom_funcs`、`project_custom_fields`、
  `debug_items`、`workflow_statuses`、`project_versions`、`fake_error_rules`（该表新旧混用）

### B. 软删除仅 `deleted`、缺 `deleted_at` 删除时间戳（3 处）
- `users`、`defect_comments`、`case_review_headers`

> 说明：`api_*`、`defects`、`environments` 等现代表虽在 CREATE 中声明 `deleted`，
> 但运行时经 `_ensure_column` 补齐了 `deleted_at`，过滤口径（`deleted=0`）与删除
> 行为一致，无“幽灵数据”，故不列为偏离。

## 迁移建议（分期，勿一次性盲改）

1. **软删除统一（低风险、可先行）**：为仅 `deleted` 的三张表补 `deleted_at` 列并在
   删除路径落删除时刻，与主域对齐。
2. **时间戳列名统一（需带数据迁移）**：对 28 张遗留表做 `create_time→created_at`、
   `update_time→updated_at` 的列迁移（新库建表直接采用规范命名；存量库走
   alembic 数据保全迁移）。由于 auth/org/defect 等模块有严格的对齐回归测试，
   需逐域改造并跑对应 `*_repo_alignment` / CRUD 测试。
3. **收口回潮**：改造完成后把 `--check-fields` 挂进 CI，确保新表不再沿用遗留命名。

---

## 附：api_definitions 单一真源（同名表多物理版本治理）

### 问题

`api_definitions` 曾同时存在两份 `CREATE TABLE` 声明：

| 版本 | 来源 | 主要列 |
|------|------|--------|
| V1 | `app/api_testing/management/_base.py`（前端兼容层） | `method` NOT NULL、`path` NOT NULL、`request_*` / `response_*` |
| V2 | `app/apitest/store/_base.py`（主引擎） | `headers`/`body`/`query`/`params`、`version_id`/`ref_id`/`latest`/`metadata`/`project_id` |

两边都靠 `_ensure_column` 给对方补列，带来三个后果：

1. **物理结构由 import 顺序决定**——谁先被 import，谁的列集合就是基准；
2. **注册表出现同表名 2 个物理版本**——`scripts/sync_schema_registry.py --check`
   长期输出「1 处 schema 冲突」，CI 红灯被当成背景噪音；
3. **`module_id` 谁都没建，但 SQL 在用**——`list_definitions(module_ids=...)`、
   `count_definitions_by_module()` 都在用这一列，前端按模块筛选接口列表
   （`POST /api/definition/page` 带 `moduleIds`）直接 500 `no such column: module_id`。

### 收敛方案

1. **权威 DDL 落到单一模块** `app/apitest/schema_ddl.py`，列集合 = V1 ∪ V2 ∪ 运行期
   实际使用列（`module_id`），并附带全部索引声明；
2. **两侧建表统一调用** `ensure_api_definitions_table(conn)`：新建库直接按权威 DDL 建；
   存量库按「从 DDL 字面量解析出的列清单」逐列 `ALTER ADD COLUMN` 补齐——
   补列清单不再手写在第二处，从根上消除「DDL 改了、补列没跟着改」的漂移；
3. **注册表同步脚本升级为列级比对**：`--check` 除校验表清单外，逐列比对
   注册表 DDL 与源码 DDL 的列集合/列定义；来源行号漂移降级为提示（行号随日常
   编辑变动，卡门禁噪音大、收益低）；
4. **`module_id` 纳入写入与过滤口径**：`create_definition(module_id=...)`、
   `update_definition(module_id=...)`、版本复制均带该列；筛选时
   `module_id` 为空/NULL 视为 root，仅在选中 root 时计入。

### 验证

```bash
python3 scripts/sync_schema_registry.py --check   # 0 处 schema 冲突
python3 -m pytest tests/test_api_definitions_schema_consistency.py -q
```

回归测试覆盖：全仓唯一建表声明、注册表与权威 DDL 逐列一致、import 顺序无关
（子进程分别以 V1/V2 先建库，列集合相同）、存量库补列数据不丢且幂等、
alembic 基线列集合一致、`module_id` 过滤可用、`/api/definition/page` 带
`moduleIds` 不再 500。
