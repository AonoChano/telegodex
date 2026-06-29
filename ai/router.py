"""AI provider router.

Routes chat requests to the right provider based on user preference or
the global default. Provider instantiation is driven by TOML config
(see :mod:`config.provider_loader`) — this module no longer maintains a
hardcoded name→class mapping.

Transport registry (3 entries, mirrors the spec):

* ``openai``            → :class:`OpenAIProvider` (native OpenAI SDK)
* ``anthropic``         → :class:`AnthropicProvider` (native Anthropic SDK)
* ``openai_compatible`` → :class:`OpenAICompatibleProvider` (generic HTTP)

All other vendor variety (qwen / kimi / zhipu / baidu / gemini / deepseek /
ollama / lmstudio / etc.) is expressed via ``transport = "openai_compatible"``
in ``provider.toml``. The legacy dedicated classes
(``GoogleProvider`` / ``DeepSeekProvider`` / ``QwenProvider`` /
``MoonshotProvider`` / ``ZhipuProvider`` / ``BaiduProvider``) remain in the
codebase as deprecated dead code and are NOT instantiated from this router.
"""

from __future__ import annotations

from config.provider_loader import GlobalConfig, ProviderConfig
from loguru import logger

from .anthropic_provider import AnthropicProvider
from .base import BaseAIProvider
from .openai_compatible_provider import OpenAICompatibleProvider
from .openai_provider import OpenAIProvider


class AIRouter:
    """Route chat requests across multiple AI providers.

    Provider instances are built from ``ProviderConfig`` values produced
    by :func:`config.provider_loader.load_provider_toml`. The router
    resolves secrets (api_key / base_url) at construction time and skips
    any provider whose required env var is missing — startup does not
    crash when one provider is misconfigured.
    """

    #: Maps a ``transport`` string to the provider class that implements it.
    TRANSPORT_REGISTRY: dict[str, type[BaseAIProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "openai_compatible": OpenAICompatibleProvider,
    }

    def __init__(
        self,
        provider_configs: list[ProviderConfig],
        global_config: GlobalConfig,
    ):
        """
        Args:
            provider_configs: Filtered list of provider configs (already
                reduced to those listed in ``[global].available_providers``).
            global_config: Parsed ``[global]`` section. Used to look up
                the default provider and global request behavior.
        """
        self.global_config = global_config
        self.providers: dict[str, BaseAIProvider] = {}
        self._default_provider_name = global_config.default_provider

        for config in provider_configs:
            self._instantiate_provider(config)

    # ------------------------------------------------------------------
    # Instantiation
    # ------------------------------------------------------------------

    def _instantiate_provider(self, config: ProviderConfig) -> None:
        """Resolve secrets and build a provider instance.

        Skips the provider with a warning if the API key cannot be
        resolved (env var missing). Does NOT raise — startup continues
        with the remaining providers.
        """
        provider_class = self.TRANSPORT_REGISTRY.get(config.transport)
        if provider_class is None:
            logger.error(
                f"✗ Unknown transport '{config.transport}' for provider "
                f"'{config.name}'; skipping"
            )
            return

        api_key = config.resolve_api_key()
        if api_key is None:
            logger.warning(
                f"⚠ Skipping provider '{config.name}': API key not resolved "
                f"(api_key_env={config.api_key_env!r} not set in environment, "
                f"and no api_key_literal provided)"
            )
            return

        base_url = config.resolve_base_url()

        try:
            if provider_class is OpenAICompatibleProvider:
                # OpenAICompatibleProvider requires base_url and uses
                # explicit provider_name / default_model / available_models
                # kwargs (the other transports read these from **kwargs).
                if not base_url:
                    logger.warning(
                        f"⚠ Skipping provider '{config.name}': transport "
                        f"'openai_compatible' requires base_url or base_url_env"
                    )
                    return
                instance = OpenAICompatibleProvider(
                    api_key=api_key,
                    base_url=base_url,
                    provider_name=config.name,
                    default_model=config.default_model or "gpt-3.5-turbo",
                    available_models=config.models,
                )
            else:
                # OpenAIProvider / AnthropicProvider accept the same kwargs
                # (base_url / default_model / available_models) and use
                # their own SDK defaults when None.
                instance = provider_class(
                    api_key=api_key,
                    base_url=base_url,
                    default_model=config.default_model or None,
                    available_models=config.models or None,
                )

            self.providers[config.name] = instance
            logger.info(f"✓ Initialized provider: {config.name} (transport={config.transport})")
        except Exception as e:
            logger.error(f"✗ Failed to initialize provider '{config.name}': {e}")

    # ------------------------------------------------------------------
    # Lookup helpers (unchanged API — handlers stay provider-agnostic)
    # ------------------------------------------------------------------

    def get_provider(self, name: str) -> BaseAIProvider | None:
        """Return the provider registered under *name* (or ``None``)."""
        return self.providers.get(name)

    def get_default_provider(self) -> BaseAIProvider | None:
        """Return the provider named by ``[global].default_provider``.

        Falls back to the first available provider if the configured
        default is not instantiated. Returns ``None`` when no providers
        are available at all.
        """
        if not self.providers:
            return None

        configured = self.providers.get(self._default_provider_name)
        if configured is not None:
            return configured

        logger.warning(
            f"Default provider '{self._default_provider_name}' is not "
            f"available; falling back to first instantiated provider"
        )
        return next(iter(self.providers.values()))

    def list_available_providers(self) -> list[str]:
        """List the names of all instantiated providers."""
        return list(self.providers.keys())

    def is_provider_available(self, name: str) -> bool:
        """Return ``True`` if *name* refers to an instantiated provider."""
        return name in self.providers

    def get_all_models(self) -> dict[str, list[str]]:
        """Return ``{provider_name: [model_ids]}`` for every provider."""
        return {
            name: provider.get_available_models()
            for name, provider in self.providers.items()
        }

    def get_provider_display_name(self, name: str) -> str:
        """Return the human-readable name of provider *name*."""
        provider = self.get_provider(name)
        if provider:
            return provider.provider_name
        return name

    @property
    def max_output_tokens(self) -> int:
        """Proxy to ``global_config.max_output_tokens`` for handler use."""
        return self.global_config.max_output_tokens
