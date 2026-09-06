---
name: deployment-ops
description: 部署与运维排障，诊断 Docker 构建失败、环境变量问题、容器启动异常与日志分析
---

# 部署运维排障器

针对本项目的部署与运维问题诊断技能，帮助 NPC 排查 Docker 构建、容器运行、环境配置等部署环节的故障。

## 适用场景

- Docker / docker-compose 构建失败诊断
- 容器启动异常排查
- 环境变量配置错误
- 端口 / 网络 / 卷挂载问题
- 日志分析定位运行期故障

## 排障流程

### 1. 构建阶段诊断

检查 `Dockerfile` / `Dockerfile.backend`：
- 基础镜像是否存在 / 版本可用
- 依赖安装步骤（`pip install` / `npm install`）是否成功
- 构建上下文是否包含必要文件
- 多阶段构建是否正确（builder → runtime）
- 架构问题：amd64/arm64 是否都支持

### 2. 配置与启动

检查 `docker-compose.yml`：
- 服务依赖顺序（backend 依赖 db 等）
- 环境变量是否完整（对照 `.env.example`）
- 端口映射是否正确、无冲突
- 卷挂载路径是否存在 / 权限正确
- healthcheck 是否配置

### 3. 运行期日志

- 查看容器日志定位异常（启动失败、崩溃循环、依赖连接失败）
- 分析应用日志（FastAPI / uvicorn 输出）
- 检查数据库连接 / 初始化是否成功
- 识别资源限制（内存 / CPU / 磁盘不足）

### 4. 常见问题库

- **ModuleNotFoundError**：依赖未装 / 版本不匹配
- **Connection refused**：依赖服务未就绪或端口错
- **Permission denied**：卷/文件权限问题
- **Address already in use**：端口冲突
- **timeout**：网络或资源等待超时

### 5. 输出诊断报告

- 问题现象与根因
- 排查过程与依据
- 修复方案（命令 / 配置修改）
- 验证方式

## 项目约定

- 主镜像：`Dockerfile`（多架构 amd64/arm64）
- 后端镜像：`Dockerfile.backend`
- 编排：`docker-compose.yml`
- 环境变量模板：`.env.example`
- 前端构建：Vue3 + Vite，产物由后端静态托管

## ✅ 验收标准

- [ ] 已定位到根因（有日志/配置/命令输出作为依据），不是猜测
- [ ] 修复方案给出具体命令或配置片段，可直接执行
- [ ] 环境变量相关改动同步核对了 `.env.example`
- [ ] 已给出验证方式（启动命令 + 预期输出）
- [ ] 涉及 Dockerfile / docker-compose 改动的，说明了影响面与回滚方式
