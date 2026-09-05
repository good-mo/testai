---
name: database-schema-validator
description: 数据库结构一致性校验，检查字段约束、索引、软删除一致性与跨库合并正确性
---

# 数据库结构校验器

针对本项目的数据库 Schema 校验技能，检查 `app/models/`、`app/db.py` 及各业务模块的表结构是否一致、规范。

## 适用场景

- 新增/修改数据表时的 Schema 校验
- 检查字段约束、索引、唯一性
- 软删除（deleted_at / is_deleted）一致性检查
- 数据库合并脚本（`scripts/merge_databases.py`）正确性验证
- 表结构变更的迁移检查

## 校验维度

### 1. 字段约束完整性
- 主键：每表必须有主键（建议自增 id 或 UUID）
- NOT NULL：业务必需字段不得为空
- DEFAULT：可选字段应设合理默认值
- 唯一约束：需唯一的数据列必须加 UNIQUE 索引

### 2. 索引合理性
- 高频查询列应有索引
- 外键关联列建议建索引
- 避免冗余索引与过宽索引
- 查询 `ORDER BY` / `WHERE` 常用列有覆盖

### 3. 软删除一致性
- 使用软删除的表统一有 `deleted_at`（DATETIME，NULL=未删除）或 `is_deleted`（INT/BOOL）
- 查询过滤条件必须含软删除判断，避免"幽灵数据"
- 关联查询要连带过滤被软删记录

### 4. 跨库合并正确性
- 检查 `app/db.py` 中 `_LEGACY_DB_MAP` 映射是否完整
- 表名带业务前缀避免冲突（如 `auth_users`、`test_cases`）
- 合并脚本需验证：数据不丢失、外键关系保持、前缀冲突已解决
- 合并后旧引用（指向旧 .db 文件的连接）应全部更新

### 5. 类型与一致性
- 同名字段在不同表类型一致（如 id 都为 INTEGER）
- 时间字段统一使用 `DATETIME` / ISO8601 字符串
- JSON 字段使用 TEXT 存 JSON 字符串，需校验可反序列化

## 校验方法

- 读取 `app/models/` 下各模型定义
- 读取业务模块中的建表语句与查询
- 检查 `app/db.py` 数据库映射与合并配置
- 运行查询验证约束与软删除行为
- 输出不一致清单与修复建议

## 项目约定

- 统一数据库文件 `tga.db`（见 `app/db.py`）
- 表名带业务前缀（`auth_*`、`test_*`、`api_*` 等）
- 软删除字段统一为 `deleted_at`
- 迁移脚本位于 `scripts/merge_databases.py`

## ✅ 验收标准

- [ ] 已运行 `python3 scripts/merge_databases.py --check`，输出「未发现数据库合并冲突」
- [ ] 字段约束（类型/非空/主键）、索引、软删除字段 `deleted_at` 均已核对
- [ ] 无跨库同表名但字段定义不一致的情况
- [ ] 建表语句与模型定义一致，无「模型有字段、表缺列」
- [ ] 报告中的问题标注了数据库名+表名+字段名
