# Telegodex

一个产品级的 Telegram AI Bot 服务器，支持多 AI 服务商统一接入，提供丝滑的交互体验。

## 特性

- 🤖 **多 AI 支持**：OpenAI (GPT-5)、Anthropic (Claude)、Google (Gemini)、DeepSeek、通义千问、Kimi、GLM、文心一言等
- 🔌 **自定义 Provider**：支持任何 OpenAI 兼容 API（Ollama、LiteLLM、vLLM 等）
- 💬 **完整 Markdown**：支持 Telegram MarkdownV2 全部特性
- 🎨 **产品级交互**：内联按钮、回复键盘、上下文管理
- 🔒 **安全保护**：速率限制、用户认证、敏感信息过滤
- 🧩 **插件化架构**：易于扩展新 AI 服务商
- 🔌 **预留接口**：Codex/Claude Code 集成预留
- 🌏 **国内优化**：深度支持国内主流 AI 模型

## 技术栈

- Python 3.11+
- aiogram 3.x (Telegram Bot 框架)
- SQLAlchemy (ORM)
- Redis (缓存/限流)
- OpenAI SDK / Anthropic SDK / Google SDK
- 支持所有 OpenAI 兼容 API

## 支持的 AI 服务商

### 内置支持
- 🌍 **国际**: OpenAI, Anthropic (Claude), Google (Gemini)
- 🇨🇳 **国内**: DeepSeek, 通义千问, Moonshot Kimi, 智谱 GLM, 百度文心

### 自定义支持
- ✅ Ollama（本地模型）
- ✅ LiteLLM（多服务商代理）
- ✅ vLLM, FastChat
- ✅ Azure OpenAI
- ✅ 任何 OpenAI 兼容 API

详见 [MODELS.md](MODELS.md) 和 [CUSTOM_PROVIDERS.md](CUSTOM_PROVIDERS.md)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_bot_token

# AI Provider API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key

# Database
DATABASE_URL=sqlite:///telegodex.db

# Redis (可选)
REDIS_URL=redis://localhost:6379

# Security
ADMIN_USER_IDS=123456,789012  # 管理员 Telegram User IDs
MAX_REQUESTS_PER_MINUTE=20
```

### 3. 运行

```bash
python main.py
```

## 架构设计

参考 [需求.md](需求.md) 和以下官方文档：

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Claude API Documentation](https://docs.anthropic.com/en/docs/overview)
- [OpenAI API Documentation](https://platform.openai.com/docs)

## 扩展开发

参考 `extensions/` 目录下的接口定义。
