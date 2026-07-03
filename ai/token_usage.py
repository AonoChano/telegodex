"""Token usage estimation helpers for normal AI chat."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from unicodedata import east_asian_width

from ai.base import Message


@dataclass(frozen=True)
class TokenUsage:
    """Token usage for one AI chat turn or message set."""

    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int
    estimated: bool
    tokenizer_name: str


def token_usage_from_provider_usage(usage: dict[str, int] | None) -> TokenUsage | None:
    """Normalize provider-returned usage into ``TokenUsage``."""
    if not usage:
        return None

    prompt_tokens = _optional_int(usage.get("prompt_tokens") or usage.get("input_tokens"))
    completion_tokens = _optional_int(usage.get("completion_tokens") or usage.get("output_tokens"))
    total_tokens = _optional_int(usage.get("total_tokens"))
    if total_tokens is None:
        total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
    if total_tokens <= 0:
        return None

    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated=False,
        tokenizer_name="provider_usage",
    )


def combine_token_usages(*usages: TokenUsage | None) -> TokenUsage | None:
    """Combine multiple usage objects from one logical AI chat turn."""
    present = [usage for usage in usages if usage is not None]
    if not present:
        return None

    prompt_tokens = _sum_optional(usage.prompt_tokens for usage in present)
    completion_tokens = _sum_optional(usage.completion_tokens for usage in present)
    total_tokens = sum(usage.total_tokens for usage in present)
    tokenizer_names = sorted({usage.tokenizer_name for usage in present})
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated=any(usage.estimated for usage in present),
        tokenizer_name=" + ".join(tokenizer_names),
    )

def estimate_text_tokens(text: str, *, model: str | None = None) -> tuple[int, str]:
    """Estimate tokens in *text*, preferring ``tiktoken`` when available."""
    if not text:
        return 0, _tokenizer_name(model, exact=False)

    encoding = _load_tiktoken_encoding(model)
    if encoding is not None:
        try:
            return len(encoding.encode(text)), _tokenizer_name(model, exact=True)
        except Exception:
            pass

    return _heuristic_text_tokens(text), _tokenizer_name(model, exact=False)


def estimate_messages_tokens(messages: list[Message], *, model: str | None = None) -> TokenUsage:
    """Estimate prompt/context tokens for chat messages."""
    total = 3  # assistant priming overhead used by OpenAI-style chat formats.
    tokenizer_name = _tokenizer_name(model, exact=False)
    for message in messages:
        content_tokens, tokenizer_name = estimate_text_tokens(message.content, model=model)
        total += content_tokens + 4
        total += estimate_text_tokens(str(message.role.value), model=model)[0]
    return TokenUsage(
        prompt_tokens=max(total, 0),
        completion_tokens=0,
        total_tokens=max(total, 0),
        estimated=True,
        tokenizer_name=tokenizer_name,
    )


def estimate_chat_usage(
    messages: list[Message],
    completion: str,
    *,
    model: str | None = None,
) -> TokenUsage:
    """Estimate total usage for one chat completion."""
    prompt = estimate_messages_tokens(messages, model=model)
    completion_tokens, tokenizer_name = estimate_text_tokens(completion, model=model)
    return TokenUsage(
        prompt_tokens=prompt.prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=(prompt.prompt_tokens or 0) + completion_tokens,
        estimated=True,
        tokenizer_name=tokenizer_name,
    )


def _sum_optional(values) -> int | None:
    total = 0
    saw_value = False
    for value in values:
        if value is None:
            continue
        total += value
        saw_value = True
    return total if saw_value else None

def _optional_int(value: object) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_tiktoken_encoding(model: str | None):
    try:
        import tiktoken  # type: ignore[import-not-found]
    except Exception:
        return None

    if model:
        try:
            return tiktoken.encoding_for_model(model)
        except Exception:
            pass
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def _heuristic_text_tokens(text: str) -> int:
    weighted_chars = 0
    for char in text:
        if char.isspace():
            weighted_chars += 1
        elif char.isascii():
            weighted_chars += 1
        elif east_asian_width(char) in {"F", "W"}:
            weighted_chars += 2
        else:
            weighted_chars += 2
    return max(1, ceil(weighted_chars / 4))


def _tokenizer_name(model: str | None, *, exact: bool) -> str:
    suffix = model or "generic"
    return f"tiktoken:{suffix}" if exact else "heuristic"
