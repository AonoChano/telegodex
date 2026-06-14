# 自定义 AI Provider 配置指南

Telegodex 支持通过配置文件添加任何 **OpenAI 兼容 API** 的 AI 服务商，无需修改代码。

## 快速开始

1. **复制示例文件**：
   ```bash
   cp custom_providers.example.json custom_providers.json
   ```

2. **编辑配置**：
   ```json
   {
     "my_provider": {
       "type": "openai_compatible",
       "api_key": "sk-your-key",
       "base_url": "https://api.example.com/v1",
       "models": ["model-1", "model-2"],
       "default_model": "model-1"
     }
   }
   ```

3. **重启 Bot** - 配置会自动加载

## 配置格式

### 完整示例

```json
{
  "配置名称": {
    "type": "openai_compatible",
    "api_key": "你的 API Key",
    "base_url": "API 基础 URL",
    "models": ["模型1", "模型2"],
    "default_model": "默认模型"
  }
}
```

### 字段说明

| 字段 | 必需 | 说明 | 示例 |
|------|------|------|------|
| `type` | ✅ | Provider 类型，当前仅支持 `openai_compatible` | `"openai_compatible"` |
| `api_key` | ✅ | API Key | `"sk-xxxxx"` |
| `base_url` | ✅ | API 基础 URL（需包含版本号，如 `/v1`） | `"https://api.example.com/v1"` |
| `models` | ❌ | 可用模型列表，留空则仅使用 default_model | `["gpt-4", "gpt-3.5-turbo"]` |
| `default_model` | ❌ | 默认模型，不指定则使用 models 第一个 | `"gpt-4"` |

## 常见场景

### 1. Ollama（本地大模型）

```json
{
  "ollama": {
    "type": "openai_compatible",
    "api_key": "ollama",
    "base_url": "http://localhost:11434/v1",
    "models": ["llama3.2", "qwen2.5", "deepseek-coder", "gemma2"],
    "default_model": "llama3.2"
  }
}
```

**说明**：
- Ollama 不需要真实 API Key，填任意值即可
- 确保 Ollama 服务已启动（`ollama serve`）
- 模型需提前下载（`ollama pull llama3.2`）

**参考**: [Ollama](https://ollama.ai)

---

### 2. LiteLLM Proxy（多服务商统一代理）

```json
{
  "litellm": {
    "type": "openai_compatible",
    "api_key": "sk-your-litellm-key",
    "base_url": "http://localhost:4000",
    "models": ["gpt-4", "claude-3-opus", "gemini-pro"],
    "default_model": "gpt-4"
  }
}
```

**说明**：
- LiteLLM 可统一管理多个 AI 服务商
- 支持负载均衡、fallback、缓存等高级特性
- 需先启动 LiteLLM Proxy

**参考**: [LiteLLM](https://docs.litellm.ai/docs/)

---

### 3. Azure OpenAI

```json
{
  "azure": {
    "type": "openai_compatible",
    "api_key": "your_azure_api_key",
    "base_url": "https://your-resource.openai.azure.com/openai/deployments",
    "models": ["gpt-4", "gpt-35-turbo"],
    "default_model": "gpt-4"
  }
}
```

**说明**：
- Azure OpenAI 使用不同的端点格式
- `base_url` 需包含你的资源名称
- 模型名称对应 Azure 部署名称

**参考**: [Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-services/openai/)

---

### 4. vLLM（自托管推理引擎）

```json
{
  "vllm": {
    "type": "openai_compatible",
    "api_key": "vllm",
    "base_url": "http://localhost:8000/v1",
    "models": ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.1-70B"],
    "default_model": "Qwen/Qwen2.5-72B-Instruct"
  }
}
```

**说明**：
- vLLM 提供高性能推理加速
- 支持多种开源模型
- 需要 GPU 环境

**参考**: [vLLM](https://docs.vllm.ai/)

---

### 5. FastChat（Vicuna/ChatGLM 等开源模型）

```json
{
  "fastchat": {
    "type": "openai_compatible",
    "api_key": "fastchat",
    "base_url": "http://localhost:8000/v1",
    "models": ["vicuna-13b", "chatglm3-6b"],
    "default_model": "vicuna-13b"
  }
}
```

**参考**: [FastChat](https://github.com/lm-sys/FastChat)

---

### 6. 自建 API（任何 OpenAI 兼容接口）

```json
{
  "my_api": {
    "type": "openai_compatible",
    "api_key": "your_custom_key",
    "base_url": "https://api.yourcompany.com/v1",
    "models": ["custom-model-v1", "custom-model-v2"],
    "default_model": "custom-model-v1"
  }
}
```

**要求**：
- 实现 OpenAI `/v1/chat/completions` 接口
- 支持标准的请求/响应格式
- 可选支持流式响应（`stream=true`）

---

## 配置预设管理

### 保存多个配置预设

你可以创建多个配置文件，按需切换：

```
custom_providers.json          # 默认配置
custom_providers.dev.json      # 开发环境
custom_providers.prod.json     # 生产环境
custom_providers.ollama.json   # Ollama 专用
```

在 `.env` 中指定使用哪个：

```env
CUSTOM_PROVIDERS_CONFIG=custom_providers.ollama.json
```

### 预设示例：本地开发

```json
{
  "ollama_llama": {
    "type": "openai_compatible",
    "api_key": "ollama",
    "base_url": "http://localhost:11434/v1",
    "models": ["llama3.2"],
    "default_model": "llama3.2"
  },
  "ollama_qwen": {
    "type": "openai_compatible",
    "api_key": "ollama",
    "base_url": "http://localhost:11434/v1",
    "models": ["qwen2.5:14b"],
    "default_model": "qwen2.5:14b"
  }
}
```

### 预设示例：生产部署

```json
{
  "production_llm": {
    "type": "openai_compatible",
    "api_key": "sk-prod-xxxxx",
    "base_url": "https://api.production.com/v1",
    "models": ["gpt-4", "claude-3-opus"],
    "default_model": "gpt-4"
  }
}
```

## 验证配置

启动 Bot 时会自动验证配置：

```bash
python run.py --check-config
```

查看日志确认 Provider 是否成功加载：

```
✓ 初始化自定义 Provider: ollama (OpenAI 兼容)
✓ 初始化自定义 Provider: my_api (OpenAI 兼容)
```

## 常见问题

### Q: 配置后没有生效？
A: 
1. 检查 JSON 格式是否正确（可用 [jsonlint.com](https://jsonlint.com) 验证）
2. 查看启动日志是否有错误信息
3. 确认 `base_url` 包含版本号（如 `/v1`）
4. 重启 Bot

### Q: API 调用失败？
A:
1. 检查网络连接（curl 测试 base_url）
2. 验证 API Key 是否正确
3. 确认模型名称拼写无误
4. 查看 `logs/` 目录下的错误日志

### Q: 支持哪些服务商？
A: 任何实现 **OpenAI Chat Completions API** 的服务，包括：
- ✅ Ollama
- ✅ LiteLLM
- ✅ vLLM
- ✅ FastChat
- ✅ LocalAI
- ✅ Text Generation WebUI
- ✅ Azure OpenAI
- ✅ 自建 API

### Q: 如何临时禁用某个 Provider？
A: 
1. 方法一：删除配置文件中的对应条目
2. 方法二：将配置移到另一个文件（如 `custom_providers.backup.json`）

### Q: 可以同时使用内置和自定义 Provider 吗？
A: ✅ 可以！内置 Provider（通过 `.env` 配置）和自定义 Provider（通过 `custom_providers.json` 配置）会自动合并。

## 技术细节

### OpenAI API 兼容标准

你的 API 需要支持以下接口：

**请求格式**：
```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer {api_key}

{
  "model": "model-name",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 4096,
  "stream": false
}
```

**响应格式**：
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "model-name",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 8,
    "total_tokens": 18
  }
}
```

### Schema 验证

配置文件遵循 JSON Schema，详见 `custom_providers.schema.json`。

## 相关资源

- [OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat/create)
- [OpenAI Compatible APIs Explained](https://www.cometapi.com/openai-compatible-apis-explained/)
- [Building OpenAI Compatible API](https://dasroot.net/posts/2026/02/building-openai-compatible-api-local-models/)

---

**需要帮助？** 
- 查看 `logs/` 目录下的日志
- 参考 `custom_providers.example.json` 示例
- 提交 Issue 获取支持
