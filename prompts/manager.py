"""
提示词管理模块

负责加载和管理系统提示词、角色提示词等。
"""

from pathlib import Path
from typing import Optional, Dict
from loguru import logger


class PromptManager:
    """提示词管理器"""

    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, str] = {}

    def load_prompt(self, prompt_name: str) -> Optional[str]:
        """
        加载提示词文件

        Args:
            prompt_name: 提示词文件名（不含扩展名），如 "system_prompt"

        Returns:
            提示词内容，如果文件不存在返回 None
        """
        # 检查缓存
        if prompt_name in self._cache:
            return self._cache[prompt_name]

        # 尝试加载文件
        prompt_file = self.prompts_dir / f"{prompt_name}.md"

        if not prompt_file.exists():
            logger.warning(f"提示词文件不存在: {prompt_file}")
            return None

        try:
            content = prompt_file.read_text(encoding="utf-8")
            self._cache[prompt_name] = content
            logger.info(f"✅ 加载提示词: {prompt_name} ({len(content)} 字符)")
            return content
        except Exception as e:
            logger.error(f"❌ 加载提示词失败: {prompt_name}, 错误: {e}")
            return None

    def get_system_prompt(self) -> str:
        """
        获取系统提示词

        如果文件不存在，返回默认提示词
        """
        prompt = self.load_prompt("system_prompt")

        if prompt:
            return prompt

        # 默认提示词
        return """You are an AI assistant. Please format your responses clearly and use proper markdown formatting where appropriate."""

    def reload_prompt(self, prompt_name: str) -> bool:
        """
        重新加载提示词（清除缓存）

        Args:
            prompt_name: 提示词名称

        Returns:
            是否成功重新加载
        """
        if prompt_name in self._cache:
            del self._cache[prompt_name]

        content = self.load_prompt(prompt_name)
        return content is not None

    def clear_cache(self):
        """清除所有缓存的提示词"""
        self._cache.clear()
        logger.info("🗑️ 提示词缓存已清空")


# 全局单例
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """获取全局提示词管理器"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
