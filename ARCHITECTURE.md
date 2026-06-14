# Telegodex - 项目结构

```
Telegodex/
├── main.py                          # 主入口
├── config.py                        # 配置管理
├── requirements.txt                 # 依赖包
├── .env.example                     # 环境变量示例
├── .gitignore
│
├── ai/                              # AI 服务商抽象层
│   ├── __init__.py
│   ├── base.py                      # 统一接口定义
│   ├── router.py                    # AI 路由器
│   ├── openai_provider.py           # OpenAI 实现
│   ├── anthropic_provider.py        # Claude 实现
│   └── google_provider.py           # Gemini 实现
│
├── bot/                             # Telegram Bot 层
│   ├── __init__.py
│   ├── keyboards.py                 # 交互键盘
│   └── handlers/                    # 消息处理器
│       ├── __init__.py
│       ├── messages.py              # 文本消息处理
│       └── callbacks.py             # 回调处理
│
├── storage/                         # 存储层
│   ├── __init__.py
│   ├── models.py                    # 数据库模型
│   └── context_manager.py           # 上下文管理
│
├── security/                        # 安全层（待实现）
│   ├── rate_limiter.py              # 限流
│   └── auth.py                      # 认证
│
└── extensions/                      # 扩展接口
    ├── README.md                    # 扩展开发文档
    ├── codex/                       # Codex 预留接口
    │   └── __init__.py
    └── claude_code/                 # Claude Code 预留接口
        └── __init__.py
```

## 设计原则

1. **插件化架构**: 每个 AI 服务商是独立模块，易于扩展
2. **统一接口**: 所有 AI Provider 实现相同的基类接口
3. **异步优先**: 全部使用 async/await，提升并发性能
4. **类型安全**: 使用 Pydantic 进行配置验证
5. **分层设计**: Bot 层 → 业务层 → 存储层，职责清晰
6. **预留扩展**: 为 Codex/Claude Code 预留接口

## 核心功能实现状态

✅ 多 AI 服务商支持（OpenAI, Anthropic, Google）
✅ 完整 Markdown 格式支持
✅ 上下文管理和对话历史
✅ 交互式键盘（菜单、设置、选择器）
✅ 数据库持久化（SQLAlchemy + SQLite）
✅ 模块化架构设计
✅ 扩展接口预留

🚧 待实现：
- 速率限制（Redis）
- 用户认证和权限管理
- 流式响应（打字机效果）
- 使用统计和计费
- 多语言支持
- 测试覆盖
