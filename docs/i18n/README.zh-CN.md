<div align="center">

<img src="../assets/logo.svg" alt="Telegodex Logo" width="900">

# 🐉 Telegodex

跑 AI 聊天的 Telegram Bot 框架。内置 8 家服务商，通过 JSON 配置接入更多。

<p>
  <a href="../../LICENSE"><img src="https://img.shields.io/badge/License-MIT-22c55e.svg" alt="License"></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://docs.aiogram.dev/"><img src="https://img.shields.io/badge/aiogram-3.x-26A5E4?logo=telegram&logoColor=white" alt="aiogram 3.x"></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy 2.x"></a>
  <a href="#roadmap"><img src="https://img.shields.io/badge/status-active%20development-f59e0b.svg" alt="Active development"></a>
</p>

[English](../../README.md) · 简体中文 · [日本語](./README.ja.md)

</div>

---

## 它做什么

一个 Telegram Bot，把大部分 demo 会跳过的生产细节都补上。

- **8 家服务商，一个接口。** OpenAI、Anthropic、Google、DeepSeek、通义千问、Kimi、GLM、文心。改一个配置项切换。
- **通过 JSON 加自己的。** 把 OpenAI 兼容端点（Ollama、vLLM、LiteLLM、Azure、LM Studio）写进 `custom_providers.json`，不改代码。
- **新服务商 <50 行。** 继承 `BaseAIProvider`，实现 4 个方法，在 router 注册。是插件，不是 fork。
- **Telegram 原生渲染。** MarkdownV2 支持表格、任务列表、脚注、可展开引用、LaTeX。内联按钮、回复键盘、模型与温度选择器。
- **持久化与安全内置。** 对话历史、用户偏好、按用户限流、管理员白名单、输入清洗、日志里不出密钥。

## 快速开始

```bash
git clone https://github.com/CYcha/Telegodex.git
cd Telegodex
pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 里填 `TELEGRAM_BOT_TOKEN` 和至少一个服务商的 key，然后：

```bash
python run.py
```

给 Bot 发 `/start`。

完整教程：[docs/QUICKSTART.md](../QUICKSTART.md)。

## 加自定义服务商

```json
{
  "ollama": {
    "type": "openai_compatible",
    "base_url": "http://localhost:11434/v1",
    "models": ["llama3.2"]
  }
}
```

往 `custom_providers.json` 里加这段，重启，搞定。

参考：[docs/CUSTOM_PROVIDERS.md](../CUSTOM_PROVIDERS.md)。

## 目录结构

```
ai/          BaseAIProvider + 8 个实现
bot/         aiogram 处理器、键盘、富文本渲染
storage/     SQLAlchemy 异步 ORM（User、Conversation、Message）
security/    限流、管理员鉴权、输入校验
extensions/  Codex、Claude Code 桥接
```

服务商契约：`chat()`、`chat_stream()`、`get_available_models()`、`validate_api_key()`。在 router 换服务商，处理器不动。

## 支持的服务商

| 地区 | 服务商 | 默认模型 |
|---|---|---|
| 国际 | OpenAI、Anthropic、Google | `gpt-4o`、`claude-sonnet-4.6`、`gemini-2.0-flash` |
| 国内 | DeepSeek、通义千问、Kimi、GLM、文心 | `deepseek-v4-pro`、`qwen-max`、`kimi-k2-7-code`、`glm-4-6`、`ernie-5.0` |

任意 OpenAI 兼容端点通过 `custom_providers.json` 接入。完整目录：[docs/MODELS.md](../MODELS.md)。

## 技术栈

Python 3.11+ · aiogram 3.x · SQLAlchemy 2.x async · Pydantic Settings · Alembic · Redis（可选）

## 文档

- [快速参考](../QUICKSTART.md)
- [使用指南](../USAGE.md)
- [架构设计](../ARCHITECTURE.md)
- [自定义 Provider](../CUSTOM_PROVIDERS.md)
- [模型目录](../MODELS.md)
- [富文本消息](../RICH_MESSAGES.md)

## 路线图

- [x] 多服务商抽象（v1.0）
- [x] 富文本 Markdown、交互键盘、上下文窗口（v1.1）
- [ ] Codex 桥接
- [ ] Claude Code 桥接
- [ ] Web 管理后台
- [ ] 语音与图像输入
- [ ] Docker compose 与 Helm chart

## 贡献

欢迎 PR。先读 [docs/ARCHITECTURE.md](../ARCHITECTURE.md) 与 [CLAUDE.md](../../CLAUDE.md)。

## 安全

漏洞：直接邮件给维护者（见提交记录），别开公开 Issue。

代码强制：API Key 不进日志、每个边界做输入清洗、`ADMIN_USER_IDS` 白名单、按用户限流。

## 许可证

MIT。详见 [LICENSE](../../LICENSE)。


