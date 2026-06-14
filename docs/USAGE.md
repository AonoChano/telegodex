---
title: Complete Usage Guide
category: guide
last_updated: 2026-06-14
relevance: high
summary: Step-by-step guide for installation, configuration, and daily usage
related: [QUICKSTART.md, CUSTOM_PROVIDERS.md]
---

# Telegodex 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 必需：从 @BotFather 获取 Bot Token
TELEGRAM_BOT_TOKEN=your_bot_token_here

# 至少配置一个 AI 服务商
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# 可选：管理员 ID（从 @userinfobot 获取）
ADMIN_USER_IDS=123456789
```

### 3. 创建 Telegram Bot

1. 在 Telegram 中找到 [@BotFather](https://t.me/botfather)
2. 发送 `/newbot` 创建新 Bot
3. 按提示设置 Bot 名称和用户名
4. 获取 Bot Token 并填入 `.env` 文件

### 4. 获取 AI API Key

#### OpenAI
- 访问 [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- 创建新 API Key
- 充值（按需）

#### Anthropic (Claude)
- 访问 [console.anthropic.com](https://console.anthropic.com)
- 获取 API Key
- 当前最新模型：claude-opus-4-8, claude-fable-5

#### Google (Gemini)
- 访问 [aistudio.google.com](https://aistudio.google.com)
- 创建 API Key
- 免费配额：每分钟 60 请求

### 5. 启动 Bot

```bash
python run.py
```

或检查配置：

```bash
python run.py --check-config
```

## 使用功能

### 基本对话
直接发送消息即可与 AI 对话。Bot 会自动保存上下文。

### 命令列表

| 命令 | 功能 |
|------|------|
| `/start` | 启动 Bot |
| `/new` | 开始新对话 |
| `/clear` | 清空当前对话历史 |
| `/settings` | 打开设置菜单 |
| `/help` | 显示帮助 |

### 菜单按钮

使用底部菜单快速访问功能：
- 💬 **新对话**: 开始全新对话
- 📝 **历史记录**: 查看对话历史（开发中）
- ⚙️ **设置**: 切换 AI 服务商和模型
- ℹ️ **帮助**: 查看帮助信息

### 设置 AI 服务商

1. 点击 `⚙️ 设置` 或发送 `/settings`
2. 选择 `🤖 切换 AI 服务商`
3. 从可用列表中选择
4. 也可以选择具体的模型

### Markdown 支持

Bot 支持 Telegram MarkdownV2 格式：

```markdown
*斜体* - 斜体文本
**粗体** - 粗体文本
[链接](https://example.com) - 超链接
`代码` - 行内代码
```

## 高级功能

### 管理员功能（待实现）
- 查看使用统计
- 封禁/解封用户
- 广播消息

### 扩展功能（预留接口）
- **Codex 集成**: 代码生成和解释
- **Claude Code**: 自主代码任务执行
- 参考 `extensions/README.md`

## 常见问题

### Q: Bot 不响应？
A: 检查：
1. Bot Token 是否正确
2. 是否启动成功（查看日志）
3. 网络连接是否正常

### Q: AI 调用失败？
A: 检查：
1. API Key 是否正确
2. 账户是否有余额/配额
3. 网络是否能访问 API（可能需要代理）

### Q: 如何切换模型？
A: 
1. 发送 `/settings`
2. 选择 `🎯 选择模型`
3. 选择目标模型

### Q: 对话历史能保存多久？
A: 默认保存 50 条消息，可在 `.env` 中修改 `MAX_CONTEXT_MESSAGES`

### Q: 支持哪些 AI 模型？

**OpenAI**:
- gpt-4o (推荐)
- gpt-4o-mini
- gpt-4-turbo

**Anthropic**:
- claude-fable-5 (最新最强)
- claude-opus-4-8
- claude-sonnet-4-6
- claude-haiku-4-5-20251001

**Google**:
- gemini-2.0-flash-exp (推荐)
- gemini-1.5-pro
- gemini-1.5-flash

## 故障排除

### 日志位置
日志保存在 `logs/` 目录，按日期轮转。

### 数据库重置
删除 `telegodex.db` 文件可重置数据库：
```bash
rm telegodex.db
```

### 依赖问题
更新依赖：
```bash
pip install -r requirements.txt --upgrade
```

## 开发和贡献

### 项目结构
参考 `ARCHITECTURE.md`

### 添加新 AI 服务商
1. 在 `ai/` 下创建新 Provider 类
2. 继承 `BaseAIProvider`
3. 实现必需方法
4. 在 `AIRouter.PROVIDERS` 中注册

### 添加新功能
1. 在 `bot/handlers/` 添加处理器
2. 在 `bot/keyboards.py` 添加交互按钮
3. 更新文档

## 部署建议

### 生产环境
1. 使用 PostgreSQL 替代 SQLite
2. 配置 Redis 用于速率限制
3. 使用 systemd/supervisor 管理进程
4. 配置日志轮转
5. 启用 HTTPS webhook 替代轮询

### Docker 部署（待实现）
```bash
docker build -t telegodex .
docker run -d --env-file .env telegodex
```

## 相关资源

- [Telegram Bot API 文档](https://core.telegram.org/bots/api)
- [OpenAI API 文档](https://platform.openai.com/docs)
- [Anthropic API 文档](https://docs.anthropic.com)
- [Google AI 文档](https://ai.google.dev)

## 支持

如有问题或建议，请提交 Issue 或 PR。

## 许可证

MIT License
