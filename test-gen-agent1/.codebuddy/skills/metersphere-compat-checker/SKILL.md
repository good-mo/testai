---
name: metersphere-compat-checker
description: MeterSphere 兼容性核对，校验接口测试模块的导入导出格式与原生 MeterSphere 的一致性
---

# MeterSphere 兼容核对器

针对本项目接口测试模块与原生 MeterSphere 的兼容性检查技能，校验导入/导出数据格式是否兼容。

## 适用场景

- 校验 API 定义 / 用例 / 场景的导入导出格式与 MeterSphere 兼容
- 检查 `frontend/`（MeterSphere 官方工程）与后端交互的契约
- 数据迁移时验证格式一致性
- 新增接口测试功能时确保兼容原生格式

## 校验维度

### 1. API 定义格式
- 接口定义字段（method、path、headers、body）是否与 MeterSphere 兼容
- 请求 / 响应体结构（JSON Schema / 示例）是否可互转
- 断言与脚本（前置/后置）格式是否一致

### 2. 接口用例格式
- 用例结构（请求 + 断言 + 提取）是否兼容
- 变量 / 参数化表达是否一致（MeterSphere 的 `${var}` 语法）
- 环境配置（base_url、全局变量）兼容性

### 3. 场景 / 流程格式
- 场景步骤编排是否可导入 MeterSphere
- 逻辑控制器（循环、条件、等待）映射是否完整
- 数据源 / 数据驱动兼容性

### 4. 导入导出互转
- 导出的 JSON / YAML 是否可被原生 MeterSphere 导入
- 原生 MeterSphere 导出的文件本项目是否可导入
- 字段缺失 / 多余时的容错处理

### 5. 前端契约
- `frontend/src/api/` 与 `app/adapters/` 的交互是否保持 MeterSphere 兼容路径
- `docs/api_mapping.md` 中 `api/apitest/*` 映射是否符合预期

## 校验方法

- 对比本项目 `app/apitest/`、`app/api_testing/` 的数据结构与 MeterSphere 规范
- 用示例导入文件做往返验证（导入→导出→比对）
- 检查缺失字段、类型不匹配、默认值差异
- 输出兼容性报告与修复建议

## 项目约定

- 前端为 MeterSphere 官方工程 `frontend/`（Vue3 + Arco）
- 后端 `app/adapters/` 负责 MeterSphere 风格路由适配
- 映射约定见 `docs/api_mapping.md`
- 路由冲突检查 `scripts/route_conflict_check.py` 与此技能互补

## ✅ 验收标准

- [ ] 已用示例文件做「导入→导出→比对」往返验证
- [ ] 字段缺失、类型不匹配、默认值差异均已列出
- [ ] 对比基准是 MeterSphere 官方规范，不是本项目自身实现
- [ ] 报告标注了不兼容项的严重程度与影响面（是否阻塞导入）
- [ ] 已运行 `python3 scripts/route_conflict_check.py --check` 确认路由无冲突
