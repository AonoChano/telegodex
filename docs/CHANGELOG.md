---
title: Changelog
category: changelog
last_updated: 2026-06-15
relevance: medium
summary: Version history and updates (currently v1.2.0)
related: [FEATURES.md, COMPLETION_REPORT.md]
---

# Telegodex 更新日志

## v1.2.0 - 2026-06-15

### 🎉 新增功能

#### 话题 / Topic 会话路由
- ✅ `conversations` 表新增 `thread_id` 列（启动时自动轻量迁移，老库无须删库）
- ✅ 不同 topic / 私聊 topic 独立上下文，handler 按 `message_thread_id` 拉会话并回发
- ✅ 结束对话、列对话等管理命令同样按 thread 隔离

#### Rich Message 流式预览
- ✅ 集成 Telegram `sendRichMessageDraft` / `sendMessageDraft`（Bot API 7.3+）
- ✅ 字符数（≥64）+ 时间（≥1.5s）双触发刷新草稿，避免 API 限流
- ✅ 流式失败 / 无 chunk 时自动回退到非流式 `chat()`
- ✅ 最终用 `sendRichMessage` 持久化消息

#### LaTeX 符号归一化
- ✅ AI 输出里的 `\alpha` `\int` `\sum` `\pm` 等数学命令自动转成对应 Unicode
- ✅ 代码块（含行内代码）内的 LaTeX 源码**原样保留**——教学场景不被破坏
- ✅ 流式链路中每个 chunk 单独走归一化，预览里也是符号而不是 LaTeX 源码

#### Telegram 原生 Expandable Blockquote（Bot API 7.3+）
- ✅ AI 现在可输出 `<blockquote expandable>...</blockquote>`（富 markdown 直通）
- ✅ MarkdownV2 fallback 路径自动转成 `**>...` + 末行 `||` 形式
- ✅ fallback 里代码块用占位符保护，不会被按行加 `>` 时切碎

#### 网络抖动重试
- ✅ 共享 aiohttp `ClientSession` 复用 TCP 连接，关 bot 时显式关闭（修 Proactor `Event loop is closed`）
- ✅ 基于 Fibonacci 序列的退避重试（10 次，封顶 20s）
- ✅ 重试用灰色 `RETRY` log level，区分瞬时网络错误和真错误

#### 可观测性 / 日志
- ✅ Loguru 双 sink：终端单行精简 / 文件完整 traceback
- ✅ `_InterceptHandler` 接管 stdlib logging（aiogram / aiohttp / asyncio）
- ✅ 关 aiogram 自己的 `aiogram.event` / `aiogram.dispatcher` / `aiogram.middlewares` 噪音 logger

#### 富消息结构改进
- ✅ blockquote / task list（`- [ ]` / `- [x]`）支持
- ✅ standalone URL 自动保留（Telegram 自动渲染）
- ✅ 链接文本和 URL 内的 MarkdownV2 特殊字符正确 escape

### 🐛 Bug 修复
- 修复草稿 `draft_id` 短时间内碰撞（线程安全单调计数器）
- 修复 LaTeX 转义序列 `\$` `\_` 误替换（保留用户输入的 `$` `_`）
- 修复流式链路中 LaTeX 未替换（每 chunk 单独走归一化）
- 修复 aiogram polling "Sleep 1s 实际卡几分钟"——把 `bot.session.timeout` 显式设到 20s，`request_timeout` 上限从 70s 降到 30s；backoff `max_delay` 从 5s 收到 3s
- 修复 bot 关闭时 `'_ProactorBasePipeTransport.__del__'` 在已关闭 event loop 上抛 `Event loop is closed`——共享 aiohttp session 显式关闭
- 修复 loguru 双 traceback（移除 format 中 `{exception}` token，依赖默认行为 + sink 控制可见性）
- 修复 `sendRichMessage` / `sendMessageDraft` 真实错误被吞——surfaced the real exception
- 修复 `sendMessage` / `sendRichMessage` 失败被静默重试到原 chat（应 fallback 到 MarkdownV2）

### 📚 文档
- 英文 README 重写 + 居中 logo + 状态徽章
- `docs/i18n/README.ja.md` / `docs/i18n/README.zh-CN.md` 国际化起步
- `docs/assets/logo.svg` 项目 mark
- `docs/RICH_MESSAGES.md` 加 expandable blockquote 章节，修正 "<details> 优先" 错误说法
- `prompts/system_prompt.md` 加 expandable blockquote 语法，重写 "Three Kinds Of Hiding" 决策表
- `RULES.md` 加 "git push 时同步更新 CHANGELOG" 规则

### 🧪 测试
- `tests_smoke_latex.py` — 26 个断言
- `tests_smoke_retry.py` — 11 个断言（退避序列、可重试异常集、共享 session 状态）
- `tests_smoke_logging.py` — 13 个断言（终端单行、文件 traceback、aiogram 拦截）
- `tests_smoke_blockquote.py` — 25 个断言
- `tests_smoke_polling.py` — 5 个断言（backoff 行为）

### 🔧 技术改进
- 共享 aiohttp `ClientSession`（`bot/utils/rich_messages.py`）
- draft_id 线程安全单调计数器（避免并发碰撞）
- 修 `MarkdownV2` 步骤 -1 抽出 `<blockquote expandable>` 递归处理，步骤 8 加 `EXPBQ` 还原分支
- `dp.start_polling` 显式 `BackoffConfig`（min=0.5, max=3.0, factor=1.3, jitter=0.1）
- `Bot` 显式 `AiohttpSession(timeout=20)`，覆盖 aiogram 默认 60s
- `.gitignore` 把 `CLAUDE.md` 改成 `CLAUDE.*` 模式，把 `RULES.md` 移到文件末尾独立 block

### ⚠️ 升级注意
- v1.1.0 → v1.2.0 数据库自动迁移（添加 `thread_id` 列），**无需删库**
- 共享 aiohttp session 改动后，关 bot 流程变成：HTTP session → aiogram session → db，**不能**并行关闭

---

## v1.1.0 - 2026-06-14

### 🎉 新增功能

#### 国内 AI 模型支持
- ✅ **DeepSeek V4** (2026-04 最新)
  - deepseek-v4-pro: 1.6T 参数，49B 激活
  - deepseek-v4-flash: 快速版本
  
- ✅ **阿里通义千问 (Qwen)**
  - qwen-max, qwen-plus, qwen-turbo
  - qwen-long: 1M tokens 长文本
  - qwen-vl-max: 视觉理解

- ✅ **Moonshot Kimi** (2026-06 最新)
  - kimi-k2-7-code: 代码优化，1T 参数
  - kimi-k2-6: 256K 上下文
  
- ✅ **智谱 GLM** (2026 最新)
  - glm-4-6: 355B 参数，200K 上下文
  - glm-4-plus, glm-4v
  
- ✅ **百度文心一言 (ERNIE)**
  - ernie-5.0-thinking-latest
  - ernie-4.5-turbo-latest

#### 自定义 Provider 系统
- ✅ 支持任何 OpenAI 兼容 API
- ✅ 配置预设管理（可保存多个配置）
- ✅ 热加载（修改配置后重启生效）
- ✅ JSON Schema 验证
- ✅ 完整文档和示例

#### 支持的自定义场景
- Ollama（本地模型）
- LiteLLM（多服务商代理）
- vLLM, FastChat（高性能推理）
- Azure OpenAI
- 任何自建 API

### 📚 新增文档
- `MODELS.md` - 所有支持的模型列表（2026 最新）
- `CUSTOM_PROVIDERS.md` - 自定义 Provider 配置指南
- `custom_providers.example.json` - 配置示例
- `custom_providers.schema.json` - JSON Schema

### 🔄 模型版本更新
所有模型版本已通过搜索验证，更新到 2026 年 6 月最新：
- Claude Fable 5（Mythos 级别）
- DeepSeek V4 Pro/Flash
- Kimi K2.7 Code
- GLM-4.6
- Gemini 2.0 Flash Exp

### ⚠️ 重要提醒
- DeepSeek 旧模型 `deepseek-chat` 和 `deepseek-reasoner` 将于 **2026-07-24 弃用**

### 🔧 技术改进
- 新增 `OpenAICompatibleProvider` 通用适配器
- 优化 `AIRouter` 支持动态配置加载
- 改进配置管理系统
- 完善错误处理和日志

---

## v1.0.0 - 2026-06-14

### 🎉 首次发布

- ✅ 多 AI 服务商支持（OpenAI, Anthropic, Google）
- ✅ 完整 Telegram Markdown 格式
- ✅ 产品级交互体验
- ✅ 安全保护措施
- ✅ 插件化架构
- ✅ Codex/Claude Code 预留接口
- ✅ 完整文档

### 核心功能
- 对话历史管理
- 上下文自动保存
- 速率限制
- 用户认证
- 多轮对话
- 交互式设置

### 文档
- README.md
- USAGE.md
- ARCHITECTURE.md
- PROJECT_SUMMARY.md
- QUICKSTART.md

---

## 后续计划

### v1.2.0（计划中）
- [x] 流式响应（打字机效果）
- [ ] 使用统计和计费
- [x] 多语言支持 (i18n)
- [ ] 更多国内模型（讯飞星火、字节豆包等）

### v1.3.0（计划中）
- [ ] Docker 部署支持
- [ ] Webhook 模式
- [ ] 图像生成集成
- [ ] 语音识别/TTS
- [ ] 测试覆盖

---

**搜索来源**：
- [DeepSeek API Docs](https://api-docs.deepseek.com)
- [Kimi Platform Changelog](https://developers.cloudflare.com/changelog/)
- [GLM-4.6 Release](https://github.com/THUDM/GLM-4)
- [OpenAI Compatible APIs](https://www.cometapi.com/openai-compatible-apis-explained/)
