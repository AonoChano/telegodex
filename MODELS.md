# 支持的 AI 模型列表（2026-06 最新）

## 🌍 国际服务商

### OpenAI
- **gpt-4o** - 多模态旗舰模型
- **gpt-4o-mini** - 轻量版
- **gpt-4-turbo** - Turbo 版本
- gpt-3.5-turbo

**获取方式**: [platform.openai.com](https://platform.openai.com/api-keys)

---

### Anthropic (Claude)
- **claude-fable-5** ⭐ - Mythos 级别，最强 Claude 模型
- **claude-opus-4-8** - Claude 4.X 旗舰
- claude-sonnet-4-6 - 平衡性能
- claude-haiku-4-5-20251001 - 快速响应

**获取方式**: [console.anthropic.com](https://console.anthropic.com)

**参考**: 
- [Claude API Documentation](https://docs.anthropic.com)
- [Claude Code SDK](https://docs.anthropic.com/en/docs/claude-code/sdk/sdk-overview)

---

### Google (Gemini)
- **gemini-2.0-flash-exp** - 2026 实验版，最新最快
- gemini-1.5-pro - 生产级高性能
- gemini-1.5-flash - 快速轻量

**获取方式**: [aistudio.google.com](https://aistudio.google.com)

---

## 🇨🇳 国内服务商

### DeepSeek (2026-04 最新)
- **deepseek-v4-pro** ⭐ - 1.6T 参数，49B 激活，GPT-4 级别
- **deepseek-v4-flash** - 更快的轻量版本

**注意**: `deepseek-chat` 和 `deepseek-reasoner` 将于 **2026-07-24** 弃用

**获取方式**: [platform.deepseek.com](https://platform.deepseek.com)

**参考**:
- [DeepSeek API Docs](https://api-docs.deepseek.com/)
- [DeepSeek V4 Release](https://api-docs.deepseek.com/news/news260424)

---

### 阿里通义千问 (Qwen)
- **qwen-max** - 通义千问最强模型
- qwen-plus - 平衡性能
- qwen-turbo - 快速响应
- qwen-long - 长文本处理（1M tokens）
- qwen-vl-plus - 视觉理解
- qwen-vl-max - 视觉理解旗舰

**获取方式**: [dashscope.aliyun.com](https://dashscope.aliyun.com)

**参考**:
- [阿里云百炼平台](https://help.aliyun.com/zh/model-studio/developer-reference/use-qwen-by-calling-api)
- [Qwen GitHub](https://github.com/QwenLM/Qwen)

---

### Moonshot Kimi (2026-06 最新)
- **kimi-k2-7-code** ⭐ - 2026-06 最新，代码优化版，1T 参数
- **kimi-k2-6** - 2026-04，多模态，256K 上下文
- kimi-k2-5 - 2026-03，256K 上下文

**获取方式**: [platform.moonshot.cn](https://platform.moonshot.cn)

**参考**:
- [Kimi API Platform](https://platform.kimi.ai/docs/api/overview)
- [Kimi K2.7 Release](https://developers.cloudflare.com/changelog/post/2026-06-12-kimi-k2-7-code-workers-ai/)

---

### 智谱AI (GLM) (2026 最新)
- **glm-4-6** ⭐ - 2026 最新旗舰，355B 参数，200K 上下文
- glm-4-plus - GLM-4 增强版
- glm-4-air - 轻量高速版
- glm-4-flash - 免费版
- glm-4v - 多模态视觉

**获取方式**: [open.bigmodel.cn](https://open.bigmodel.cn)

**参考**:
- [Z.AI Developer Document](https://docs.z.ai/)
- [GLM-4.6 Release](https://github.com/THUDM/GLM-4)

---

### 百度文心一言 (ERNIE)
- **ernie-5.0-thinking-latest** - ERNIE 5.0 最新，多模态
- ernie-4.5-turbo-latest - ERNIE 4.5 Turbo
- ernie-4.0-turbo-latest - ERNIE 4.0 Turbo
- ernie-x-1.1 - 多模态深度推理

**注意**: 百度 API 使用特殊的 OAuth 2.0 鉴权机制

**获取方式**: [cloud.baidu.com](https://cloud.baidu.com/product/wenxinworkshop)

**参考**:
- [ERNIE GitHub](https://github.com/PaddlePaddle/ERNIE)

---

## 🔌 自定义 Provider

支持任何 **OpenAI 兼容 API**，包括：
- Ollama (本地模型)
- LiteLLM (多服务商代理)
- Azure OpenAI
- vLLM
- FastChat
- 任何实现 OpenAI `/v1/chat/completions` 接口的服务

### 配置方法

创建 `custom_providers.json`：

```json
{
  "my_provider": {
    "type": "openai_compatible",
    "api_key": "your_key",
    "base_url": "https://api.example.com/v1",
    "models": ["model-1", "model-2"],
    "default_model": "model-1"
  }
}
```

参考 `custom_providers.example.json` 查看更多示例。

**参考**:
- [OpenAI Compatible APIs](https://www.cometapi.com/openai-compatible-apis-explained/)
- [Building OpenAI Compatible API](https://dasroot.net/posts/2026/02/building-openai-compatible-api-local-models/)

---

## 📊 模型选择建议

| 需求 | 推荐模型 |
|------|----------|
| 最强性能 | claude-fable-5, deepseek-v4-pro |
| 性价比 | gpt-4o, qwen-plus |
| 代码生成 | kimi-k2-7-code, deepseek-v4-pro |
| 长文本处理 | kimi-k2-6 (256K), qwen-long (1M) |
| 多模态 | gemini-2.0-flash-exp, glm-4v |
| 免费/低成本 | gemini-1.5-flash, glm-4-flash |

---

**更新时间**: 2026-06-14

**数据来源**:
- 各服务商官方文档
- 搜索验证的 2026 年最新信息
