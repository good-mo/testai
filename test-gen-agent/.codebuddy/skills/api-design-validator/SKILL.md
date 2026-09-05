---
name: api-design-validator
description: API 设计规范校验，检查 RESTful 命名、分页、幂等、状态码语义与鉴权覆盖，提升接口设计质量
---

# API 设计规范校验器

针对本项目的后端 API 设计规范性检查技能，校验 `app/routers/` 与 `app/adapters/` 下所有接口是否遵循统一设计规范。

## 适用场景

- 新增/修改 API 时的设计规范检查
- 对存量接口做设计规范性审计
- PR 评审时把关接口设计质量
- 生成接口文档前的一致性校验

## 校验维度

### 1. RESTful 资源命名
- URL 使用**名词复数**表示资源，如 `/cases`、`/projects`
- 操作动词不应出现在路径中（用 HTTP 方法表达），特殊动作可用 `-action` 后缀（如 `batch-delete`）
- 路径层级遵循"资源/子资源"结构，如 `/projects/{id}/cases`
- 命名一致：同义资源在不同模块不得使用不同名称

### 2. HTTP 方法语义
- `GET` — 查询（无副作用）
- `POST` — 创建 / 触发动作
- `PUT` — 全量更新
- `PATCH` — 部分更新
- `DELETE` — 删除

### 3. 分页与列表
- 列表接口支持 `page` / `pageSize` 参数（或 `page` / `size`）
- 响应结构统一为 `{code, message, data}`，data 内分页字段 `{items, total, page, pageSize}`
- 未分页的大列表接口应被标记为风险

### 4. 状态码语义
- `200` 成功、`201` 创建、`204` 无内容删除
- `400` 参数错误、`401` 未认证、`403` 无权限、`404` 不存在、`409` 冲突、`422` 校验失败
- 统一使用 CNB/项目约定的错误响应格式

### 5. 鉴权与权限覆盖
- 所有非公开接口均需鉴权
- 敏感操作（删除、批量删除、配置修改）需权限校验
- 越权访问防护（用户只能访问自己组织/项目内的资源）

### 6. 幂等与一致性
- `DELETE` / `PUT` 应为幂等操作
- 批量操作应支持部分失败回滚或明确返回失败项
- 响应体与请求体的字段命名风格一致（camelCase / snake_case 统一）

## 校验方法

- 扫描 `app/routers/*.py` 与 `app/adapters/*.py` 中的路由装饰器与处理函数
- 结合 `docs/api_mapping.md` 与 `frontend/src/api/contracts.ts` 交叉核对
- 输出问题清单，标注严重程度与修复建议

## 项目约定

- 统一响应结构：`{code, message, data}`
- 后端路由前缀参考 `docs/api_mapping.md` 的映射约定
- 现有 `scripts/route_conflict_check.py` 检测重复注册，本技能补充设计规范维度

## ✅ 验收标准

- [ ] 已扫描 `app/routers/*.py` 与 `app/adapters/*.py` 的全部路由装饰器
- [ ] 每个接口都核对过：RESTful 命名、分页参数、幂等性、状态码语义、鉴权覆盖
- [ ] 所有响应均使用统一结构 `{code, message, data}`
- [ ] 报告按严重程度分组，每条附带文件:行号与可落地的修改建议
- [ ] 已运行 `python3 scripts/route_conflict_check.py --check` 确认无冲突
