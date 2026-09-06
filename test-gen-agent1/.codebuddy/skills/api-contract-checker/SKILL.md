---
name: api-contract-checker
description: 检查前后端 API 契约一致性，确保路由路径、参数和响应格式匹配
---

# API 契约检查器

检查前后端 API 契约一致性，确保所有接口调用与后端实现匹配。

## 检查范围

- 路由路径匹配（前端调用路径 vs 后端路由定义）
- HTTP 方法匹配（GET/POST/PUT/DELETE）
- 请求参数匹配（query params / path params / body）
- 响应格式匹配（`{code, message, data}` 契约）

## 检查步骤

### 1. 获取前端 API 定义

- 查看 `frontend/src/api/contracts.ts` — 前端 API 契约中心
- 查看各页面模块的 API 调用代码

### 2. 获取后端路由定义

- 查看 `app/routers/` 目录下的路由文件
- 查看 `app/adapters/` 目录下的适配路由
- 运行 `python3 scripts/route_conflict_check.py --check` 检查路由冲突

### 3. 对比分析

检查以下一致性：
1. **路径**：前端调用的 URL 路径是否与后端路由匹配
2. **方法**：HTTP 方法是否一致
3. **参数**：请求参数是否与后端 Pydantic 模型匹配
4. **响应**：响应字段是否与前端期望匹配

### 4. 输出结果

列出所有不匹配项，包括：
- 前端调用的路径和方法
- 后端实际的路由定义
- 差异描述和修改建议

## 项目工具

- 路由冲突检测：`python3 scripts/route_conflict_check.py --check`
- 前端契约检查：`python3 scripts/frontend_contract_check.py --check`
- API 映射文档：`docs/api_mapping.md`

## ✅ 验收标准

执行完本技能后，逐项自检，全部满足才算完成：

- [ ] 已运行 `python3 scripts/route_conflict_check.py --check`，输出「未发现路由冲突」
- [ ] 已运行 `python3 scripts/frontend_contract_check.py --check`，输出「契约已对齐」
- [ ] 前端 `requrls` 与后端路由逐条比对完毕，无「前端定义但后端未注册」项
- [ ] 报告中对每个不匹配项都给出：前端路径+方法、后端实际定义、修复建议
- [ ] 修复后重新跑一遍两个检查脚本，确认仍为通过状态
