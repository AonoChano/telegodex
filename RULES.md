# Telegodex Development & Security Rules

## 🔒 Security Boundaries

### Critical: Files AI Must NEVER Read

These files contain actual secrets, user data, or runtime state. AI assistants are **absolutely forbidden** from reading them:

#### 🚫 Credential Files
- **`.env`** — Real API keys, bot tokens, database URLs
- **`custom_providers.json`** — User's actual provider configurations with API keys
- **Any `*.env` files** (e.g., `.env.local`, `.env.production`)
- **`secrets/`** directory (if created)

#### 🚫 Runtime Data
- **`telegodex.db`** — SQLite database with user conversations
- **`*.db`** — Any database files
- **`logs/*.log`** — Runtime logs may contain sensitive data
- **`*.log`** — Any log files in root or subdirectories

#### 🚫 Session State
- **`__pycache__/`** — Python bytecode cache
- **`.pytest_cache/`** — Test cache
- **Any runtime-generated state files**

### ✅ Safe to Read

- **`.env.example`** — Template configuration (no real secrets)
- **`custom_providers.example.json`** — Example provider config
- **`custom_providers.schema.json`** — JSON schema for validation
- **All Python source code** (`*.py`) — Code review is safe and encouraged
- **All documentation** (`docs/*.md`, `README.md`)
- **Configuration templates** (any file with `.example` suffix)

### 🛡️ When Handling Credentials

**DO**:
- Reference `.env.example` when explaining configuration
- Use placeholder values like `sk-...`, `your_api_key_here`
- Validate configuration structure, not actual values
- Guide users to proper secret management

**DON'T**:
- Read or parse actual `.env` files
- Log API keys or tokens in any output
- Store secrets in code or documentation
- Suggest committing `.env` to git

---

## 🏗️ Development Standards

### Code Quality Requirements

#### 1. Type Safety
```python
# ✅ Good: Full type annotations
async def chat(
    self,
    messages: List[Message],
    model: str | None = None,
    temperature: float = 0.7
) -> AIResponse:
    ...

# ❌ Bad: No type hints
async def chat(self, messages, model=None, temperature=0.7):
    ...
```

#### 2. Async-First
```python
# ✅ Good: Async all the way
async def handle_message(message: types.Message):
    response = await ai_provider.chat(messages)
    await message.answer(response.content)

# ❌ Bad: Blocking calls in async context
async def handle_message(message: types.Message):
    response = requests.get(url)  # Blocking!
    await message.answer(response.text)
```

#### 3. Error Handling
```python
# ✅ Good: Specific exceptions with logging
try:
    response = await client.chat.completions.create(...)
except openai.APIError as e:
    logger.error(f"OpenAI API error: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise

# ❌ Bad: Bare except
try:
    response = await client.chat.completions.create(...)
except:
    pass
```

#### 4. Documentation
```python
# ✅ Good: Docstring with parameters and returns
async def chat(
    self,
    messages: List[Message],
    model: str | None = None,
) -> AIResponse:
    """
    Send chat request to AI provider.
    
    Args:
        messages: List of conversation messages
        model: Model name (uses default if None)
    
    Returns:
        AIResponse with content and metadata
    
    Raises:
        APIError: If provider API call fails
    """
    ...

# ❌ Bad: No documentation
async def chat(self, messages, model=None):
    ...
```

### Architectural Patterns

#### Plugin Architecture
- **New AI providers**: Must inherit from `BaseAIProvider`
- **All abstract methods must be implemented**: `chat()`, `chat_stream()`, `get_available_models()`, `validate_api_key()`
- **Register in router**: Add to `ai/router.py` `BUILTIN_PROVIDERS` dict

#### Separation of Concerns
```
bot/          → Telegram-specific logic (aiogram handlers)
ai/           → AI provider abstractions (provider-agnostic)
storage/      → Database models and operations (SQLAlchemy)
security/     → Cross-cutting concerns (rate limiting, validation)
extensions/   → Future integrations (Codex, Claude Code)
```

#### Configuration Management
- **Environment variables**: Use Pydantic `BaseSettings`
- **Validation**: Validate at startup, fail fast
- **Defaults**: Provide sensible defaults in `config.py`
- **Documentation**: Always update `.env.example` when adding new config

---

## 🧪 Testing Requirements

### Before Committing

1. **Manual Testing** (minimum):
   - Start the bot: `python main.py`
   - Send a test message
   - Verify response is received
   - Check logs for errors

2. **Code Review Checklist**:
   - [ ] No syntax errors
   - [ ] Type hints present
   - [ ] Docstrings for public methods
   - [ ] Error handling in place
   - [ ] No hardcoded secrets
   - [ ] `.env.example` updated if config changed

3. **Import Verification**:
   ```powershell
   python -c "import main; print('OK')"
   ```

### Future: Automated Testing

When test suite is added:
- Unit tests for each provider (`tests/ai/test_providers.py`)
- Integration tests for bot handlers (`tests/bot/test_handlers.py`)
- Mock external APIs (OpenAI, Anthropic, etc.)
- Minimum 70% code coverage

---

## 📝 Git Workflow

### Commit Messages

Follow **Conventional Commits** format:

```
<type>(<scope>): <subject>

<body>
```

**Types**:
- `feat`: New feature (e.g., `feat(ai): add Moonshot provider`)
- `fix`: Bug fix (e.g., `fix(config): handle invalid admin IDs`)
- `docs`: Documentation only (e.g., `docs: update CUSTOM_PROVIDERS guide`)
- `refactor`: Code restructuring (e.g., `refactor(bot): extract message formatting`)
- `test`: Test addition or modification
- `chore`: Maintenance (e.g., `chore: update .gitignore`)

**Scope** (optional): `ai`, `bot`, `storage`, `security`, `docs`, `config`

**Examples**:
```bash
feat(ai): add DeepSeek V4 provider with Anthropic compatibility
fix(config): skip comments when parsing admin IDs
docs: add Harness Engineering structure guide
refactor(bot): extract Telegram markdown formatting to utils
chore: move documentation to docs/ directory
```

### Branch Strategy

- **Main branch**: `master` (current default)
- **Feature branches**: `feature/provider-streaming`, `feature/codex-integration`
- **Fix branches**: `fix/admin-id-parsing`, `fix/event-loop-error`
- **Always branch for non-trivial changes**

### Before Pushing

1. Review changes: `git diff`
2. Stage selectively: `git add <specific-files>`
3. **Never `git add .`** blindly (might include `.env`)
4. Check `.gitignore` includes:
   ```
   .env
   *.db
   *.log
   logs/
   __pycache__/
   custom_providers.json
   ```

---

## 🔐 Security Checklist

### Input Validation

**All user inputs must be validated** before processing:

```python
from security.input_validation import sanitize_input

# ✅ Good: Sanitize before use
user_text = sanitize_input(message.text, max_length=4000)

# ❌ Bad: Direct use of user input
user_text = message.text
```

### Rate Limiting

**Apply rate limits** to prevent abuse:

```python
# Check in handlers
if not await rate_limiter.check(user_id):
    await message.answer("请求过于频繁，请稍后再试")
    return
```

### Admin Authentication

**Verify admin status** for privileged operations:

```python
from config import settings

if message.from_user.id not in settings.admin_ids:
    await message.answer("权限不足")
    return
```

### API Key Validation

**Validate keys at startup**, not at first use:

```python
# In provider initialization
if not self.validate_api_key():
    logger.warning(f"{self.provider_name} API key invalid")
```

---

## 📋 Documentation Requirements

### When to Update Docs

Update documentation when:

1. **Adding features**: Update `docs/FEATURES.md` and `docs/CHANGELOG.md`
2. **Adding providers**: Update `docs/MODELS.md` and `docs/CUSTOM_PROVIDERS.md`
3. **Changing config**: Update `.env.example` and `docs/USAGE.md`
4. **Changing architecture**: Update `docs/ARCHITECTURE.md`
5. **Bug fixes** (user-facing): Update `docs/CHANGELOG.md`

### Documentation Standards

#### YAML Frontmatter (Required)

All docs in `docs/` must have:

```yaml
---
title: Document Title
category: guide | reference | architecture | changelog
last_updated: 2026-06-14
relevance: high | medium | low
summary: One-line description
related: [other-doc.md]
---
```

#### Markdown Style

- Use clear headers (`##`, `###`)
- Code blocks with language hints (\`\`\`python)
- Tables for comparisons
- Bullet points for lists
- Links to related docs

---

## 🚨 Red Flags (Review Required)

Require user approval before:

1. **Deleting databases**: `telegodex.db`
2. **Modifying `.gitignore`**: Might expose secrets
3. **Changing authentication logic**: Security-critical
4. **Bulk file deletion**: Risk of data loss
5. **Production deployment**: Needs manual review

---

## 🔄 Rule Evolution

These rules will evolve as the project matures. When rules need updates:

1. **Propose changes** in conversation
2. **Update this file** after user approval
3. **Update `CLAUDE.md`** to reference new rules
4. **Announce in commit message**: `docs(rules): add Docker deployment security rules`

---

**Last Updated**: 2026-06-14  
**Version**: 1.0  
**Status**: Active - All AI assistants must follow these rules
