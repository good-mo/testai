---
name: project-code-review
description: 项目代码审查，检查安全漏洞、代码质量问题和最佳实践
---

# 项目代码审查

针对 Test Generation Agent Toolkit 的代码审查技能，帮助 NPC 执行专业代码审查。

## 审查重点

### 1. 安全漏洞

- **SQL 注入**：检查 `sqlite3` 查询是否使用参数绑定
- **认证绕过**：检查 API 是否有未受保护的管理端点
- **敏感信息泄露**：检查日志、响应中是否暴露 API key 或密码
- **路径遍历**：检查文件操作是否验证用户输入路径
- **命令注入**：检查 `subprocess` 或 `os.system` 调用是否安全

### 2. 代码质量

- **重复代码**：检查是否有可以抽象/复用的重复逻辑
- **复杂度**：检查是否有过长函数或嵌套过深的逻辑
- **异常处理**：检查是否有吞掉异常的代码（bare except）
- **资源泄漏**：检查数据库连接、文件句柄是否正确关闭
- **死代码**：检查是否有未使用或不可达的代码

### 3. API 规范

- **统一响应格式**：应使用 `{code, message, data}` 结构
- **路由冲突**：检查是否有路径/方法重复的路由
- **参数验证**：检查是否使用 Pydantic 模型进行请求体校验
- **错误处理**：检查是否使用了 `app/core/exceptions.py` 定义的异常

### 4. 性能问题

- **N+1 查询**：检查循环中是否有数据库查询
- **大文件读取**：检查是否有不必要的整个文件加载
- **连接池**：检查是否使用了 `Database.get_conn()` 统一连接管理

## 审查流程

1. 阅读 `git diff` 了解变更范围
2. 逐文件审查，重点关注新增/修改的代码
3. 按照上述维度标记问题和改进建议
4. 输出结构化审查报告

## 项目代码规范参考

- 数据库访问：使用 `app/core/database.py` 的 `Database.get_conn()`
- 路由注册：使用 `app/core/router.py` 的 `api_route` 装饰器
- 异常处理：使用 `app/core/exceptions.py` 中定义的异常类型
- 统一响应：使用 `app/core/response.py` 的 `ok()` / `fail()`

## ✅ 验收标准

- [ ] 已阅读完整 `git diff`，覆盖所有变更文件
- [ ] 安全、API 契约、代码质量、性能四个维度均已检查并逐项给出结论
- [ ] 每个问题标注文件:行号 + 严重程度 + 修复建议
- [ ] 已运行 `python3 scripts/route_conflict_check.py --check` 与 `python3 scripts/frontend_contract_check.py --check`
- [ ] 已运行 `python3 -m pytest tests/ -q` 确认变更未破坏现有测试
- [ ] 区分「必须修」与「建议改」，不把主观偏好当缺陷
