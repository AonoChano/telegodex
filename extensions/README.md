# Extensions 预留接口

此目录包含扩展功能的预留接口，便于后续集成高级功能。

## 已预留接口

### 1. Codex (`codex/`)
OpenAI Codex 代码生成功能：
- `generate_code()`: 根据描述生成代码
- `explain_code()`: 解释代码功能
- `fix_code()`: 修复代码错误

**集成时机**: OpenAI Codex 完全开放后

**参考文档**: [OpenAI Codex](https://platform.openai.com/docs/guides/code)

### 2. Claude Code (`claude_code/`)
Claude Code Agent SDK 集成：
- `execute_task()`: 执行自主代码任务
- `analyze_code()`: 代码质量分析
- `refactor_code()`: 智能重构
- `debug_code()`: 智能调试

**集成方式**: 
- 使用 Anthropic Agent SDK
- 支持自主文件操作、命令执行等

**参考文档**: 
- [Claude Code SDK](https://docs.anthropic.com/en/docs/claude-code/sdk/sdk-overview)
- [Agent SDK Overview](https://docs.anthropic.com/en/docs/claude-code/sdk/sdk-overview)

## 使用方式

在 `bot/handlers/` 中根据用户指令调用扩展功能：

```python
from extensions.codex import CodexExtension
from extensions.claude_code import ClaudeCodeExtension

# 初始化扩展
codex = CodexExtension(api_key=settings.codex_api_key)
claude_code = ClaudeCodeExtension(api_key=settings.anthropic_api_key)

# 使用扩展
if "/code" in message.text:
    result = await codex.generate_code(user_prompt)
    await message.answer(result)
```

## 扩展开发规范

1. 每个扩展独立目录
2. 实现统一的 `__init__.py` 作为入口
3. 错误处理：所有方法应 raise RuntimeError 当扩展未启用
4. 日志记录：使用 loguru 记录关键操作
5. 异步优先：所有 I/O 操作使用 async/await

## 未来扩展方向

- [ ] 图像生成集成（DALL-E、Midjourney）
- [ ] 语音识别/TTS 集成
- [ ] 文档解析器（PDF、DOCX 等）
- [ ] Web 搜索增强
- [ ] 插件市场
