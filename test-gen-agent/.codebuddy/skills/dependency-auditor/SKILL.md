---
name: dependency-auditor
description: 依赖安全审计与版本管理，扫描 Python/前端依赖漏洞并提供升级建议，保障供应链安全
---

# 依赖安全审计器

针对本项目的第三方依赖安全审计技能，检查 `requirements.txt`、`requirements-dev.txt` 与 `frontend/package.json` 中的依赖安全问题。

## 适用场景

- 检查 Python 依赖（requirements.txt / requirements-dev.txt）的已知漏洞（CVE）
- 检查前端依赖（frontend/package.json）的已知漏洞
- 依赖版本过旧、存在重大漏洞时给出升级建议
- PR 变更涉及依赖文件时的安全性把关

## 审计流程

### 1. 收集依赖清单

读取以下文件：
- `requirements.txt`（核心后端依赖）
- `requirements-dev.txt`（开发/测试依赖）
- `frontend/package.json`（前端依赖）

提取依赖名与版本号。

### 2. 漏洞扫描

对每个依赖执行：
- **Python**：使用 `pip-audit` / `safety` 或查询 OSV / NVD 数据库
- **前端**：使用 `npm audit` / `yarn audit`（对照 package-lock.json / yarn.lock）
- 检查是否存在已知 CVE、严重等级（Critical/High/Medium/Low）

### 3. 风险评估

对发现的漏洞按优先级评估：
- 🔴 **Critical/High**：可被远程利用、可能 RCE/注入，立即处理
- 🟠 **Medium**：有限条件下可利用，尽快处理
- 🟡 **Low**：影响面小，随版本升级自然修复

### 4. 升级建议

给出针对性建议：
- 直接升级到无漏洞的稳定版本（注意 break change）
- 若无直接修复版，提供 workaround 或迁移方案
- 对前端锁定版本（避免范围内自动升级引入新问题）

### 5. 项目约定

- 本项目后端为 **FastAPI + LangGraph + LangChain** 技术栈，需重点关注 AI/LLM 相关依赖的供应链风险
- 前端为 **Vue3 + Arco Design**，需关注构建链与运行时依赖
- 生产与开发依赖分离管理
- 修改依赖需同步更新 `requirements.txt` 与 `requirements-dev.txt`，前端需更新 `package.json` 与 lock 文件

## 输出格式

按严重程度分组输出漏洞报告，包含：依赖名、当前版本、漏洞编号（CVE）、严重等级、影响说明、建议版本/方案。

## ✅ 验收标准

- [ ] 已扫描 `requirements.txt`、`requirements-dev.txt` 及前端 `package.json`
- [ ] 每条漏洞含：依赖名、当前版本、CVE 编号、严重等级、建议版本
- [ ] 升级建议已评估 break change，并给出回退方案
- [ ] 修改依赖后同步更新了对应清单文件与 lock 文件
- [ ] 无「为了升级而破坏现有功能」的高风险改动未说明
