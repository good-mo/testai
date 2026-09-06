---
name: cnb-platform-tips
description: CNB 平台实用技巧速查，覆盖 NPC/Skill、流水线/CI、Issue/PR 附件分析、TAPD 直连、知识库检索等，帮助 NPC 高效完成平台任务
---

# CNB 平台实用技巧速查

针对本项目在 CNB 平台上高效协作的实用技巧，NPC 执行任务时可直接参考。

## 🧠 NPC / Skill 类

- **召唤指定角色**：在 Issue/PR 评论中直接 `@MOMO.MO/test-gen-agent(测试专家)` 唤醒对应 NPC。
- **只提及不召唤**：用反引号包裹 `@xxx` 可只提及而不触发 NPC（避免误触发流水线）。
- **自定义专属 NPC**：在 `.cnb/settings.yml` 的 `npc.roles` 下新增 role，配置 `slogan` + `prompt` + `enableThinking`。
- **Skills 即插即用**：`.codebuddy/skills/<name>/SKILL.md` 即技能说明书，NPC 会自动加载。新增能力只需写规范 Markdown。

## 🚀 流水线 / CI 类

- **覆盖率质量门槛**：本项目用 `scripts/report_coverage.py coverage.lcov [行阈值] [分支阈值]` 自行解析 lcov（CNB 内置 `testing:coverage` 无法解析 coverage.py 的 lcov），PR 流水线当前为行 40% / 分支 20%；分支数据需给 pytest 加 `--cov-branch`。
- **失败通知**：用 `failStages` 放失败专用提醒（如 Webhook 机器人通知），`endStages` 放成功/失败都会执行的清理任务。
- **CI 失败自动唤起 NPC**：构建失败时平台会自动唤起 NPC 介入排查，无需手动盯日志。
- **多架构镜像**：`cnb:resolve` + `cnb:await` + `manifest` 组合做 amd64/arm64 双架构构建与清单合并。
- **AI 代码评审**：`npc:go` 类型任务可在每次 PR 自动跑 AI 审查，用 `systemPrompt` 定制审查重点。

## 🛠 平台操作类

- **Issue/PR 附件与图片**：用 `cnb issues get-imgs` / `cnb issues get-files` 拉取评论中的图片、附件做分析；配合 OCR 识别截图报错。
- **OCR 识别截图**：截图报错可用 OCR（tesseract-ocr skill）提取文字信息定位问题。
- **TAPD 资源直连**：粘贴 TAPD 需求/缺陷链接，用 `cnb-tapd-resource-fetcher` skill 自动解析迭代、任务、缺陷信息。
- **知识库检索**：仓库配置知识库后，用 `cnb-repo-knowledge-base` skill 检索相关文本片段辅助答疑。

## 📌 本项目推荐实践

1. 契约检查：`scripts/frontend_contract_check.py --check`（前端 requrls → 后端路由比对）
2. 路由冲突：`scripts/route_conflict_check.py --check`（检测重复注册）
3. 覆盖率门槛已在 `.cnb.yml` PR 流水线中开启（行 40% / 分支 20%），由 `scripts/report_coverage.py` 判定
4. 数据库合并冲突检查：`python3 scripts/merge_databases.py --check`
5. 前端冒烟分组：PR 流水线先跑 `tests/test_frontend_*.py`，再跑全量测试
6. 契约修复思路：优先核对 `frontend/src/api/contracts.ts` 与后端实际路由，路径缺失补注册、方法不匹配改契约。

## ✅ 验收标准

- [ ] 给出的命令都是本仓库真实存在的（脚本路径、参数名核对过）
- [ ] 涉及流水线改动的，已用 cnb-pipeline 校验器校验 `.cnb.yml` 通过
- [ ] 涉及覆盖率口径的，与 `.cnb.yml` 中 `scripts/report_coverage.py` 的实际阈值一致
- [ ] 不臆造平台能力，不确定的标注「待确认」
- [ ] 技巧描述包含可直接复制的命令或配置片段
