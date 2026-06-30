"""Runtime selection helpers for normal AI chat."""

from __future__ import annotations

from dataclasses import dataclass

from ai import AIRouter
from ai.base import BaseAIProvider


@dataclass(frozen=True)
class ChatRuntimeSelection:
    """Effective provider and request settings for one chat turn."""

    provider_name: str
    provider: BaseAIProvider
    model_name: str | None
    temperature: float
    streaming: bool
    max_output_tokens: int


def select_chat_runtime(user, ai_router: AIRouter) -> ChatRuntimeSelection | None:
    """Resolve provider and global request defaults for a normal chat turn."""

    preferred_provider = getattr(user, "preferred_provider", None)
    provider_name = preferred_provider or ai_router.default_provider_name
    provider = ai_router.get_provider(provider_name) if provider_name else None

    if provider is None:
        provider = ai_router.get_default_provider()
        provider_name = ai_router.default_provider_name if provider is not None else provider_name

    if provider is None:
        return None

    return ChatRuntimeSelection(
        provider_name=provider_name,
        provider=provider,
        model_name=_resolve_model_name(getattr(user, "preferred_model", None), ai_router.default_model),
        temperature=_resolve_temperature(getattr(user, "temperature", None), ai_router.temperature),
        streaming=ai_router.streaming,
        max_output_tokens=ai_router.max_output_tokens,
    )


def _resolve_model_name(user_model: str | None, global_default_model: str | None) -> str | None:
    """Use the user-selected model first, then the TOML global default."""

    if user_model and str(user_model).strip():
        return str(user_model).strip()
    if global_default_model and str(global_default_model).strip():
        return str(global_default_model).strip()
    return None


def _resolve_temperature(user_temperature: str | float | int | None, global_temperature: float) -> float:
    """Resolve temperature while treating legacy DB defaults as unset.

    Older rows were created with ``"0.7"`` as an implicit default, so that
    value cannot reliably mean "the user explicitly chose 0.7". Treat it as
    unset so ``[global].temperature`` can take effect after the TOML migration.
    """

    if user_temperature is None:
        return float(global_temperature)
    if isinstance(user_temperature, str):
        normalized = user_temperature.strip()
        if not normalized or normalized == "0.7":
            return float(global_temperature)
        return float(normalized)
    return float(user_temperature)
