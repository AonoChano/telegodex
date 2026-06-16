"""Provider manager for authentication, model resolution, and metadata."""

from __future__ import annotations

from typing import Any

from ai import AIRouter


class ProviderManager:
    """Manage provider authentication, model resolution, and metadata.

    Wraps :class:`ai.AIRouter` with convenience helpers used by the
    :class:`~core.orchestrator.core.Orchestrator`.
    """

    def __init__(self, ai_router: AIRouter) -> None:
        self._router = ai_router

    def get_provider(self, name: str | None = None) -> Any | None:
        """Return a provider by name, or the default if *name* is ``None``."""
        if name is None:
            return self._router.get_default_provider()
        return self._router.get_provider(name)

    def resolve_model(
        self, provider_name: str, user_preferred: str | None = None
    ) -> str | None:
        """Resolve the effective model for a provider."""
        provider = self.get_provider(provider_name)
        if provider is None:
            return None
        if user_preferred:
            available = provider.get_available_models()
            if user_preferred in available:
                return user_preferred
        return getattr(provider, "default_model", None)

    def list_available(self) -> list[str]:
        """List all available provider names."""
        return self._router.list_available_providers()

    def get_all_models(self) -> dict[str, list[str]]:
        """Get all models for all providers."""
        return self._router.get_all_models()

    def is_available(self, name: str) -> bool:
        """Check if a provider is available."""
        return self._router.is_provider_available(name)

    def get_display_name(self, name: str) -> str:
        """Return a human-readable provider name."""
        return self._router.get_provider_display_name(name)

    @property
    def router(self) -> AIRouter:
        """Access the underlying :class:`ai.AIRouter`."""
        return self._router
