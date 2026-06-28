"""
Prompt management module.

Loads and composes system prompts using a layered structure by provider.
"""

from pathlib import Path

from loguru import logger

from prompts._utils import load_prompt


class PromptManager:
    """提示词管理器

    使用分层组合模式：
    - base/identity.md  → 身份声明 (system role)
    - base/formatting.md → 格式能力描述 (developer role)
    - providers/{name}.md → 行为指导 (developer role)

    组合顺序: identity + formatting + provider
    """

    def __init__(self, prompts_dir: str = "prompts"):
        self._base_dir = Path(prompts_dir)
        self._cache: dict[str, str] = {}

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def get_system_prompt(self, provider: str = "default") -> str:
        """
        获取组合后的系统提示词。

        Args:
            provider: AI provider 名称，如 "openai", "deepseek", "anthropic"。
                      会尝试加载 providers/{provider}.md，不存在则回退到 default。

        Returns:
            组合后的完整系统提示词
        """
        cache_key = provider
        if cache_key in self._cache:
            return self._cache[cache_key]

        parts: list[str] = []

        # 1. 身份声明
        identity = self._load("base/identity")
        if identity:
            parts.append(identity.strip())

        # 2. 格式能力描述
        formatting = self._load("base/formatting")
        if formatting:
            parts.append(formatting.strip())

        # 3. 行为指导
        behaviour = self._load(f"providers/{provider}")
        if behaviour is None:
            behaviour = self._load("providers/default")
        if behaviour:
            parts.append(behaviour.strip())

        combined = "\n\n".join(parts)
        self._cache[cache_key] = combined
        return combined

    def reload(self) -> None:
        """清除缓存，下次调用时重新加载所有文件"""
        self._cache.clear()
        logger.info("提示词缓存已清空")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _load(self, name: str) -> str | None:
        """加载单个提示词片段，剥离 YAML frontmatter"""
        if not (self._base_dir / f"{name}.md").exists():
            if name.startswith("providers/"):
                return None
            logger.warning(f"提示词文件不存在: {self._base_dir / f'{name}.md'}")
            return None

        try:
            return load_prompt(name, self._base_dir)
        except Exception:
            logger.exception(f"加载提示词失败: {name}")
            return None


# 全局单例
_prompt_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    """获取全局提示词管理器"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
