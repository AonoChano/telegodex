---
title: Anthropic API Compatibility
category: reference
last_updated: 2026-06-14
relevance: medium
summary: DeepSeek and other providers supporting Anthropic-compatible API format
related: [CUSTOM_PROVIDERS.md, MODELS.md]
---

# Anthropic API 兼容接口支持

部分 AI 服务商（如 DeepSeek）为了方便 Claude Code 等工具接入，提供了 **Anthropic 兼容 API**。

## 支持的服务商

### DeepSeek

DeepSeek 提供两种 API 格式：

1. **OpenAI 兼容格式**（默认）
   - Base URL: `https://api.deepseek.com`
   - 使用标准 OpenAI SDK

2. **Anthropic 兼容格式**
   - Base URL: `https://api.deepseek.com`（相同域名，通过 SDK 自动识别）
   - 支持 Anthropic Messages API
   - 适用于 Claude Code、Cline 等工具

**官方文档**: [DeepSeek Anthropic API](https://api-docs.deepseek.com/zh-cn/guides/anthropic_api)

---

## 使用方式

### 方式 1：内置 DeepSeek Provider（OpenAI 格式）

在 `.env` 中配置：
```env
DEEPSEEK_API_KEY=sk-...
```

代码自动使用 OpenAI 兼容格式。

---

### 方式 2：自定义 Provider（Anthropic 格式）

如果需要使用 Anthropic 格式（例如在其他工具中已配置为 Anthropic 格式），创建 `custom_providers.json`：

```json
{
  "deepseek_anthropic": {
    "type": "openai_compatible",
    "api_key": "sk-...",
    "base_url": "https://api.deepseek.com",
    "models": ["deepseek-v4-pro", "deepseek-v4-flash"],
    "default_model": "deepseek-v4-pro"
  }
}
```

**说明**：
- DeepSeek 的 Anthropic 兼容接口与 OpenAI 格式使用相同的 Base URL
- SDK 会根据请求格式自动识别 API 类型
- 两种格式功能完全一致，可按需选择

---

## Claude Code / Cline 集成

当你在 Claude Code 或 Cline 中配置了 DeepSeek（Anthropic 格式）：

```json
{
  "provider": "anthropic",
  "apiKey": "sk-...",
  "baseURL": "https://api.deepseek.com",
  "model": "deepseek-v4-pro"
}
```

**Telegodex 中对应配置**：

创建 `custom_providers.json`：
```json
{
  "deepseek_from_claude_code": {
    "type": "openai_compatible",
    "api_key": "sk-...",
    "base_url": "https://api.deepseek.com",
    "models": ["deepseek-v4-pro"],
    "default_model": "deepseek-v4-pro"
  }
}
```

两者可共享同一个 API Key。

---

## 其他可能支持 Anthropic 格式的服务商

随着 Claude 生态扩展，更多服务商可能提供 Anthropic 兼容接口：

1. **检查官方文档**：搜索 "Anthropic API" 或 "Claude API compatibility"
2. **测试兼容性**：使用自定义 Provider 配置测试
3. **提交 Issue**：如发现其他服务商支持，欢迎反馈

---

## 技术细节

### Anthropic Messages API 格式

**请求示例**：
```json
{
  "model": "claude-3-opus-20240229",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "max_tokens": 1024
}
```

**响应示例**：
```json
{
  "id": "msg_xxx",
  "type": "message",
  "role": "assistant",
  "content": [{"type": "text", "text": "Hello!"}],
  "model": "claude-3-opus-20240229",
  "usage": {
    "input_tokens": 10,
    "output_tokens": 5
  }
}
```

### 与 OpenAI 格式的区别

| 特性 | OpenAI | Anthropic |
|------|--------|-----------|
| System 消息 | 在 messages 数组中 | 单独的 `system` 参数 |
| 内容格式 | 字符串 | 对象数组 `[{type, text}]` |
| 响应结构 | `choices[0].message.content` | `content[0].text` |
| Token 字段 | `usage.prompt_tokens` | `usage.input_tokens` |

**Telegodex 处理**：内部已自动适配两种格式。

---

## FAQ

**Q: 为什么 DeepSeek 提供两种格式？**
A: 为了兼容更多工具。OpenAI 格式生态更广，Anthropic 格式适配 Claude Code 等专用工具。

**Q: 两种格式有性能差异吗？**
A: 无差异，底层使用相同模型，仅 API 格式不同。

**Q: 如何选择？**
A: 
- 默认使用 OpenAI 格式（更通用）
- 需要与 Claude Code 配置统一时使用 Anthropic 格式

**Q: 其他服务商（Qwen、Kimi 等）支持 Anthropic 格式吗？**
A: 目前官方文档仅 DeepSeek 明确支持，其他服务商待验证。

---

**参考资源**：
- [DeepSeek Anthropic API 文档](https://api-docs.deepseek.com/zh-cn/guides/anthropic_api)
- [Anthropic Messages API](https://docs.anthropic.com/en/api/messages)
- [Claude Code 文档](https://docs.anthropic.com/en/docs/claude-code)

**更新时间**: 2026-06-14
