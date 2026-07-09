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
in ``provider.toml``. Legacy vendor-specific provider classes were removed
after the TOML provider system became the production path.
"""

from __future__ import annotations

from loguru import logger

from config.provider_loader import GlobalConfig, ProviderConfig

from .anthropic_provider import AnthropicProvider
from .base import BaseAIProvider
from .openai_compatible_provider import OpenAICompatibleProvider
from .openai_provider import OpenAIProvider


def unavailable_default_provider_error(router: AIRouter) -> str | None:
    """Return a user-facing error when the configured default is unavailable."""

    if router.get_default_provider() is not None:
        return None
    if not router.default_provider_name:
        return "[global].default_provider is empty in provider.toml"
    return (
        f"default_provider '{router.default_provider_name}' is configured but not available; "
        "check provider.toml and the referenced API key environment variable"
    )


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

    def _build_provider(self, config: ProviderConfig) -> BaseAIProvider | None:
        """Resolve secrets and build a provider instance for *config*."""
        provider_class = self.TRANSPORT_REGISTRY.get(config.transport)
        if provider_class is None:
            logger.error(
                f"✗ Unknown transport '{config.transport}' for provider "
                f"'{config.name}'; skipping"
            )
            return None

        api_key = config.resolve_api_key()
        if api_key is None:
            logger.warning(
                f"⚠ Skipping provider '{config.name}': API key not resolved "
                f"(api_key_env={config.api_key_env!r} not set in environment, "
                f"and no api_key_literal provided)"
            )
            return None

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
                    return None
                return OpenAICompatibleProvider(
                    api_key=api_key,
                    base_url=base_url,
                    provider_name=config.name,
                    default_model=config.default_model or "gpt-3.5-turbo",
                    available_models=config.models,
                    headers=config.headers,
                    query=config.query,
                )

            # OpenAIProvider / AnthropicProvider accept the same kwargs
            # (base_url / default_model / available_models) and use
            # their own SDK defaults when None.
            return provider_class(
                api_key=api_key,
                base_url=base_url,
                default_model=config.default_model or None,
                available_models=config.models or None,
                headers=config.headers,
                query=config.query,
            )
        except Exception as e:
            logger.error(f"✗ Failed to initialize provider '{config.name}': {e}")
            return None

    def _instantiate_provider(self, config: ProviderConfig) -> None:
        """Resolve secrets and build a provider instance.

        Skips the provider with a warning if the API key cannot be
        resolved (env var missing). Does NOT raise — startup continues
        with the remaining providers.
        """
        instance = self._build_provider(config)
        if instance is None:
            return
        self.providers[config.name] = instance
        logger.info(f"✓ Initialized provider: {config.name} (transport={config.transport})")

    def reload(
        self,
        provider_configs: list[ProviderConfig],
        global_config: GlobalConfig,
    ) -> bool:
        """Hot-reload provider configuration in place.

        The active router is replaced only when the new config leaves at
        least one provider available and the configured default provider can
        be instantiated. Invalid in-progress edits keep the previous router.
        """
        new_providers: dict[str, BaseAIProvider] = {}
        for config in provider_configs:
            instance = self._build_provider(config)
            if instance is not None:
                new_providers[config.name] = instance

        if not new_providers:
            logger.warning("Provider hot reload skipped: no providers could be instantiated")
            return False

        if global_config.default_provider not in new_providers:
            logger.warning(
                f"Provider hot reload skipped: default provider '{global_config.default_provider}' is not available"
            )
            return False

        old_names = set(self.providers)
        self.global_config = global_config
        self._default_provider_name = global_config.default_provider
        self.providers = new_providers
        provider_names = ", ".join(self.providers)
        added = ", ".join(sorted(set(new_providers) - old_names)) or "none"
        removed = ", ".join(sorted(old_names - set(new_providers))) or "none"
        logger.info(
            f"Provider hot reload applied: providers={provider_names}, "
            f"default={self._default_provider_name}, added={added}, removed={removed}"
        )
        return True

    # ------------------------------------------------------------------
    # Lookup helpers (unchanged API — handlers stay provider-agnostic)
    # ------------------------------------------------------------------

    def get_provider(self, name: str) -> BaseAIProvider | None:
        """Return the provider registered under *name* (or ``None``)."""
        return self.providers.get(name)

    def get_default_provider(self) -> BaseAIProvider | None:
        """Return the provider named by ``[global].default_provider``.

        Returns ``None`` when the configured default provider was not
        instantiated. This fails closed instead of routing user traffic to
        an unintended provider.
        """
        if not self.providers:
            return None

        configured = self.providers.get(self._default_provider_name)
        if configured is not None:
            return configured

        logger.error(
            f"Default provider '{self._default_provider_name}' is configured "
            f"but not available; refusing implicit fallback"
        )
        return None

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
    def default_provider_name(self) -> str:
        """Provider id configured as ``[global].default_provider``."""
        return self._default_provider_name

    @property
    def default_model(self) -> str:
        """Proxy to ``global_config.default_model`` for handler use."""
        return self.global_config.default_model

    @property
    def temperature(self) -> float:
        """Proxy to ``global_config.temperature`` for handler use."""
        return self.global_config.temperature

    @property
    def streaming(self) -> bool:
        """Proxy to ``global_config.streaming`` for handler use."""
        return self.global_config.streaming

    @property
    def max_output_tokens(self) -> int:
        """Proxy to ``global_config.max_output_tokens`` for handler use."""
        return self.global_config.max_output_tokens
