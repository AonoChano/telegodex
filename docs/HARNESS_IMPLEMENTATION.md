---
title: Harness Engineering Implementation Summary
category: changelog
last_updated: 2026-06-14
relevance: high
summary: Complete record of Harness structure implementation (v1.0) on 2026-06-14
related: [ARCHITECTURE.md, CHANGELOG.md]
---

# Harness Engineering Structure - Implementation Summary

## ✅ Completed (2026-06-14)

### 核心文件

#### 1. **CLAUDE.md** - AI 协作指南
- 📍 项目真实目的说明（Telegram → Codex 远程接入桥）
- 🏗️ 架构概览和关键模式
- 🔒 安全规则（禁止读取的文件清单）
- 📚 文档阅读协议（两步法：速览 → 精读）
- 📑 完整文档索引
- 🔧 开发工作流
- 📋 任务管理规范（YAML+MD 格式）
- 🔄 自适应 Harness 管理
- 🚀 快速参考

#### 2. **RULES.md** - 开发与安全规范
- 🔒 **安全边界**（Critical）
  - ⛔ 绝对禁止读取的文件（.env, custom_providers.json, *.db, logs）
  - ✅ 安全可读文件（.env.example, 源代码, 文档）
  - 🛡️ 凭据处理规范
- 🏗️ **开发标准**
  - 类型安全、异步优先、错误处理、文档规范
  - 架构模式（插件架构、关注点分离）
  - 配置管理
- 🧪 **测试要求**
  - 提交前检查清单
  - 未来自动化测试计划
- 📝 **Git 工作流**
  - Conventional Commits 规范
  - 分支策略
  - 推送前检查
- 🔐 **安全检查清单**
  - 输入验证、速率限制、管理员认证、API Key 验证
- 📋 **文档要求**
  - YAML frontmatter 标准
  - Markdown 风格指南
- 🚨 **红旗警告**（需要用户批准的操作）
- 🔄 **规则演化**机制

#### 3. **HARNESS.md** - Harness 管理协议
- 📚 **文档管理**
  - 文档生命周期（Created → Active → [Stale] → Archived）
  - 文档分类（Living / Reference / Historical）
  - 渐进式披露协议（YAML frontmatter + 两步阅读）
  - 文档更新工作流
  - 归档流程
- 📋 **任务管理**
  - YAML+MD 格式规范
  - 任务生命周期（planned → in_progress → testing → completed）
  - 任务文件命名约定（[Closed] / [Abandoned] 前缀）
  - AI 阅读协议（跳过已关闭任务）
  - 任务创建、完成、归档工作流
- 🔧 **规则管理**
  - 规则分类
  - 规则更新流程
  - 规则变更日志
- 🔄 **自适应行为**
  - 上下文管理策略
  - 反馈循环
  - Harness 健康检查（月度审查）
- 🚀 **Harness 升级路径**
  - Phase 2: Codex 集成
  - Phase 3: 多用户支持
  - Phase 4: 插件生态
  - 版本历史追踪
- 📖 **快速参考**（AI 助手 & 人类开发者）

---

## 📂 目录结构调整

### Before (混乱)
```
Telegodex/
├── README.md
├── ARCHITECTURE.md         ❌ 根目录堆积文档
├── USAGE.md
├── MODELS.md
├── CUSTOM_PROVIDERS.md
├── PROJECT_SUMMARY.md
├── CHANGELOG.md
├── QUICKSTART.md
├── FEATURES.md
├── ANTHROPIC_COMPATIBILITY.md
├── COMPLETION_REPORT.md
├── 需求.md
├── ai/
├── bot/
└── ...
```

### After (整洁)
```
Telegodex/
├── README.md               ✅ 根目录只保留核心文件
├── CLAUDE.md               ✅ AI 协作指南
├── RULES.md                ✅ 开发与安全规范
├── HARNESS.md              ✅ Harness 管理协议
├── .gitignore              ✅ 更新以包含 harness 结构
│
├── docs/                   ✅ 所有文档集中管理
│   ├── QUICKSTART.md       （带 YAML frontmatter）
│   ├── USAGE.md
│   ├── ARCHITECTURE.md
│   ├── MODELS.md
│   ├── CUSTOM_PROVIDERS.md
│   ├── ANTHROPIC_COMPATIBILITY.md
│   ├── CHANGELOG.md
│   ├── FEATURES.md
│   ├── PROJECT_SUMMARY.md  （标记为 archived）
│   ├── COMPLETION_REPORT.md（标记为 archived）
│   ├── 需求.md              （标记为 archived）
│   └── archive/            （未来归档目录）
│       └── .gitkeep
│
├── .claude/                ✅ Harness 元数据
│   ├── tasks/              ✅ YAML+MD 任务文件
│   │   ├── task-001-example-streaming.md
│   │   └── archive/        ✅ 完成任务归档
│   │       └── .gitkeep
│   └── settings.local.json
│
├── ai/                     （代码不变）
├── bot/
├── storage/
└── ...
```

---

## 📄 YAML Frontmatter 标准

所有 `docs/` 下的文档现在都有 YAML frontmatter：

```yaml
---
title: Human-Readable Title
category: guide | reference | architecture | changelog | archive
last_updated: 2026-06-14
relevance: high | medium | low
summary: One-sentence description (max 100 chars)
related: [other-doc.md]
status: active | archived | stale  # optional
---
```

### 已添加 frontmatter 的文档

- ✅ `docs/QUICKSTART.md` - category: guide, relevance: high
- ✅ `docs/USAGE.md` - category: guide, relevance: high
- ✅ `docs/ARCHITECTURE.md` - category: architecture, relevance: high
- ✅ `docs/MODELS.md` - category: reference, relevance: high
- ✅ `docs/CUSTOM_PROVIDERS.md` - category: reference, relevance: high
- ✅ `docs/ANTHROPIC_COMPATIBILITY.md` - category: reference, relevance: medium
- ✅ `docs/CHANGELOG.md` - category: changelog, relevance: medium
- ✅ `docs/FEATURES.md` - category: changelog, relevance: medium
- ✅ `docs/PROJECT_SUMMARY.md` - status: archived, relevance: low
- ✅ `docs/COMPLETION_REPORT.md` - status: archived, relevance: low
- ✅ `docs/需求.md` - status: archived, relevance: low

---

## 🔐 安全改进

### 明确的禁止文件列表

AI 助手**绝对禁止**读取的文件（RULES.md + CLAUDE.md 双重声明）：

#### 🚫 凭据文件
- `.env` - 真实 API keys
- `custom_providers.json` - 用户真实配置
- 任何 `*.env` 文件
- `secrets/` 目录

#### 🚫 运行时数据
- `telegodex.db` - 用户对话数据
- `*.db`, `*.sqlite`, `*.sqlite3`
- `logs/*.log`
- `*.log`

#### 🚫 会话状态
- `__pycache__/`
- `.pytest_cache/`
- 运行时生成的状态文件

### 安全可读文件

✅ `.env.example` - 配置模板  
✅ `custom_providers.example.json` - 示例配置  
✅ `custom_providers.schema.json` - JSON Schema  
✅ 所有 `.py` 源代码  
✅ 所有 `docs/` 文档

---

## 📋 任务管理系统

### YAML+MD 格式示例

创建了示例任务文件：`.claude/tasks/task-001-example-streaming.md`

```yaml
---
id: task-001
title: Add streaming response support (EXAMPLE)
status: planned
priority: medium
created: 2026-06-14
updated: 2026-06-14
assigned: future-ai-assistant
estimated_effort: 1d
related_files:
  - bot/handlers/messages.py
  - ai/base.py
tags: [feature, streaming, telegram, example]
blocks: []
blocked_by: []
---

## Description
...

## Acceptance Criteria
- [ ] Item 1
- [ ] Item 2

## Progress Log
### 2026-06-14 16:00
- Progress note
```

### 任务生命周期

```
📝 planned
  ↓
🏗️ in_progress
  ↓
🧪 testing
  ↓
✅ completed → [Closed] prefix → archive after 30 days
  
Alternative:
❌ abandoned → [Abandoned] prefix → delete after 7 days
```

### AI 阅读规则

- ✅ 读取：`planned`, `in_progress`, `blocked`, `testing` 状态的任务
- ⏭️ 跳过：`[Closed]` 任务（除非明确引用或用户要求）
- 🚫 忽略：`[Abandoned]` 任务

---

## 🔄 两步阅读协议

### Step 1: 速览（Metadata Scan）

AI 助手开始任务时：
1. 扫描 `docs/` 所有文档的 YAML frontmatter
2. 根据 `category` 和 `relevance` 过滤
3. 仅加载相关文档到 Step 2

### Step 2: 精读（Precision Read）

仅在以下情况读取完整内容：
- 任务明确需要此文档
- YAML `relevance: high` 且与任务域相关
- 被其他相关文档引用（`related: [...]`）
- 用户明确要求

### 示例场景

| 任务 | Metadata Scan | Precision Read |
|------|---------------|----------------|
| "添加 Gemini 2.0 支持" | 所有 docs | `ARCHITECTURE.md`, `MODELS.md`, `CUSTOM_PROVIDERS.md` |
| "如何配置 Telegram？" | Guide 类别 | `USAGE.md`, `QUICKSTART.md` |
| "原始需求是什么？" | Archive 类别 | `需求.md`（仅在需要时）|
| "修复 Markdown 渲染" | Guide + 代码 | `USAGE.md` + `bot/handlers/messages.py` |

---

## 🎯 关键价值

### 对 AI 助手

1. **安全边界清晰**：明确知道哪些文件绝对不能读
2. **文档导航高效**：YAML metadata 快速定位相关文档
3. **任务上下文明确**：YAML+MD 格式提供完整任务描述
4. **避免重复工作**：跳过 `[Closed]` 任务，避免加载无关历史

### 对人类开发者

1. **根目录整洁**：核心 Harness 文件 + README，文档在 `docs/`
2. **规则透明**：RULES.md 定义所有开发标准和安全边界
3. **文档可维护**：YAML frontmatter 追踪更新时间和相关性
4. **任务可追溯**：`.claude/tasks/` 记录所有开发任务历史

### 对项目长期发展

1. **可演化**：HARNESS.md 定义规则和文档如何随项目更新
2. **可扩展**：为 Phase 2（Codex 集成）预留清晰的扩展路径
3. **符合 2026 最佳实践**：基于 Harness Engineering 理念构建
4. **多 AI 协作友好**：任何 AI 助手读取 CLAUDE.md 即可理解项目

---

## 📦 Git 提交

### Commit Message
```
chore: implement Harness Engineering structure

- Create CLAUDE.md with AI guidance for reading/modifying docs
- Create RULES.md defining security boundaries and dev standards
- Create HARNESS.md for adaptive document/rule/task management
- Reorganize: move all docs to docs/ directory (keep root clean)
- Add YAML frontmatter to all docs for progressive disclosure
- Implement .claude/tasks/ with YAML+MD format
- Add example task file demonstrating task lifecycle
- Update .gitignore to include harness structure
- Update README.md references to new doc locations

Security improvements:
- Explicit ban list for sensitive files (.env, custom_providers.json, *.db, logs)
- Two-step reading protocol (metadata scan → precision read)
- Task completion tracking with [Closed]/[Abandoned] prefixes

Based on Harness Engineering principles (2026):
Agent = Model + Harness
https://medium.com/@tort_mario/ai-agent-best-practices-production-ready-harness-engineering-2026-guide-c1236d713fac
```

### 文件变更
- 19 files changed
- 4058 insertions(+), 13 deletions(-)
- 新增：CLAUDE.md, RULES.md, HARNESS.md
- 新增：.claude/tasks/ 目录和示例任务
- 移动：11 个 MD 文件到 docs/
- 更新：.gitignore, README.md

---

## 🚀 下一步

### Phase 2: Codex 集成（未来）

根据 HARNESS.md 升级路径，当准备实现 Telegram → Codex 远程接入时：

1. 创建 `.claude/codex/` 目录
2. 添加 `docs/CODEX_INTEGRATION.md`
3. 更新 `RULES.md` 添加 Codex 特定安全规则
4. 在 `.claude/tasks/` 创建 Codex 集成任务

### 维护建议

#### 月度检查（HARNESS.md → Harness Health Checks）

1. **文档新鲜度**：检查 `last_updated` > 90 天的文档
2. **任务积压**：检查 `blocked` > 14 天或 `in_progress` > 7 天无更新
3. **规则合规**：检查 git 历史是否有 .env 提交（不应存在）
4. **结构清理**：
   - 归档 `[Closed]` 任务 > 30 天到 `.claude/tasks/archive/`
   - 删除 `[Abandoned]` 任务 > 7 天

#### 文档更新触发器（HARNESS.md → Document Management）

**Living Documents**（每次相关变更时更新）：
- `docs/CHANGELOG.md` - 每个 feature/fix
- `docs/MODELS.md` - 添加/删除 AI 模型时
- `docs/FEATURES.md` - 完成功能时
- `CLAUDE.md` - Harness 结构变化时
- `RULES.md` - 安全/开发规则变化时

**Reference Documents**（内容区域变化时更新）：
- `docs/ARCHITECTURE.md` - 设计模式变化时
- `docs/CUSTOM_PROVIDERS.md` - 配置系统变化时
- `docs/USAGE.md` - 用户行为变化时

---

## 📚 参考资源

- [Harness Engineering: AI Agent Best Practices 2026](https://medium.com/@tort_mario/ai-agent-best-practices-production-ready-harness-engineering-2026-guide-c1236d713fac)
- [Harness Engineering: The Infrastructure Layer](https://medium.com/@sezenerdem/harness-engineering-the-infrastructure-layer-of-ai-agents-e0de2eb28537)
- [Agent harness engineering: terminal-bench-langchain-2026](https://explainx.ai/blog/agent-harness-engineering-terminal-bench-langchain-2026)

---

**实施日期**: 2026-06-14  
**Harness 版本**: 1.0  
**项目版本**: v1.1.0  
**提交哈希**: 33aec3e  
**实施者**: CYcha  
**协助**: Claude Code (Opus 4.8)
