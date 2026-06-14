---
title: Changelog
category: changelog
last_updated: 2026-06-14
relevance: medium
summary: Version history and updates (currently v1.1.0)
related: [FEATURES.md, COMPLETION_REPORT.md]
---

# Telegodex 更新日志

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
- [ ] 流式响应（打字机效果）
- [ ] 使用统计和计费
- [ ] 多语言支持 (i18n)
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
