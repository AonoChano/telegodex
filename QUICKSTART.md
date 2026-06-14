# 🚀 Telegodex 快速参考

## 一分钟启动

```bash
# 安装
pip install -r requirements.txt

# 配置（填入你的 Token 和 API Keys）
cp .env.example .env && notepad .env

# 启动
python run.py
```

## 核心命令

| 命令 | 功能 |
|------|------|
| `/start` | 启动 Bot |
| `/new` | 新对话 |
| `/clear` | 清空历史 |
| `/settings` | 设置菜单（切换 AI 服务商）|

## 支持的 AI 服务商

### 🌍 国际（3 个）
- OpenAI, Anthropic, Google

### 🇨🇳 国内（5+ 个）  
- DeepSeek, 通义千问, Kimi, GLM, 文心一言

### 🔌 自定义
- 任何 OpenAI 兼容 API
- Ollama, LiteLLM, vLLM 等

## 配置要点

```env
# 必需
TELEGRAM_BOT_TOKEN=从 @BotFather 获取

# 至少配置一个 AI 服务商
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
QWEN_API_KEY=sk-...
MOONSHOT_API_KEY=sk-...
ZHIPU_API_KEY=...
```

### 自定义 Provider（可选）
创建 `custom_providers.json`：
```json
{
  "ollama": {
    "type": "openai_compatible",
    "api_key": "ollama",
    "base_url": "http://localhost:11434/v1",
    "models": ["llama3.2"],
    "default_model": "llama3.2"
  }
}
```

## 最新模型（2026-06）

| 服务商 | 推荐模型 | 特点 |
|--------|----------|------|
| Anthropic | `claude-fable-5` | 🏆 最强 |
| DeepSeek | `deepseek-v4-pro` | 🔥 1.6T 参数 |
| Kimi | `kimi-k2-7-code` | 💻 代码优化 |
| GLM | `glm-4-6` | 🇨🇳 355B 参数 |
| OpenAI | `gpt-4o` | 🌍 多模态 |
| Qwen | `qwen-max` | 📚 长文本 1M |
| Google | `gemini-2.0-flash-exp` | ⚡ 免费快 |

## 架构速览

```
ai/              统一 AI 抽象层
bot/             Telegram 交互层
storage/         数据库和上下文
security/        限流和认证
extensions/      Codex/Claude Code 预留
```

## 文档索引

- 📖 [完整使用指南](USAGE.md)
- 🏗️ [架构设计](ARCHITECTURE.md)
- 📊 [项目总结](PROJECT_SUMMARY.md)
- 🔌 [扩展开发](extensions/README.md)
- 🤖 [模型列表](MODELS.md) ⭐ NEW
- ⚙️ [自定义配置](CUSTOM_PROVIDERS.md) ⭐ NEW
- 📝 [更新日志](CHANGELOG.md) ⭐ NEW

## 常见问题

**Q: 模型列表不对？**
A: 已更新为 2026 年 6 月最新版本，包含 DeepSeek V4, Kimi K2.7, GLM-4.6 等

**Q: Telegram Bot API 有何变化？**
A: 当前支持 MarkdownV2、HTML 三种格式，详见[官方文档](https://core.telegram.org/bots/api)

**Q: 如何添加新 AI？**
A: 
- 内置：继承 `BaseAIProvider`，实现 4 个方法，在 `AIRouter` 注册
- 自定义：编辑 `custom_providers.json`，支持任何 OpenAI 兼容 API

**Q: 如何使用国内模型？**
A: 在 `.env` 中配置对应的 API Key：
```env
DEEPSEEK_API_KEY=sk-...
QWEN_API_KEY=sk-...
MOONSHOT_API_KEY=sk-...
ZHIPU_API_KEY=...
```

**Q: 支持本地模型吗（Ollama）？**
A: ✅ 支持！创建 `custom_providers.json`：
```json
{
  "ollama": {
    "type": "openai_compatible",
    "api_key": "ollama",
    "base_url": "http://localhost:11434/v1",
    "models": ["llama3.2", "qwen2.5"],
    "default_model": "llama3.2"
  }
}
```

详见 [CUSTOM_PROVIDERS.md](CUSTOM_PROVIDERS.md)

## 项目统计

- 📝 **40+ 个文件**
- 🐍 **22 个 Python 模块**
- 📚 **8 份文档**
- 🤖 **8+ AI 服务商**（内置）
- 🔌 **无限扩展**（自定义 Provider）
- ⚡ **~100KB 代码**

---

**开发者**: CYcha  
**协助**: Claude Code (Opus 4.8)  
**日期**: 2026-06-14
