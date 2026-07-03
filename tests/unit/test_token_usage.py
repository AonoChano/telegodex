from ai import Message, MessageRole
from ai.token_usage import (
    combine_token_usages,
    estimate_chat_usage,
    estimate_messages_tokens,
    estimate_text_tokens,
    token_usage_from_provider_usage,
)


def test_token_usage_from_provider_usage_prefers_provider_totals() -> None:
    usage = token_usage_from_provider_usage(
        {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 99}
    )

    assert usage is not None
    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 5
    assert usage.total_tokens == 99
    assert usage.estimated is False
    assert usage.tokenizer_name == "provider_usage"


def test_token_usage_from_provider_usage_supports_input_output_names() -> None:
    usage = token_usage_from_provider_usage({"input_tokens": 11, "output_tokens": 7})

    assert usage is not None
    assert usage.prompt_tokens == 11
    assert usage.completion_tokens == 7
    assert usage.total_tokens == 18


def test_estimate_messages_tokens_counts_chat_overhead() -> None:
    usage = estimate_messages_tokens(
        [
            Message(role=MessageRole.SYSTEM, content="You are concise."),
            Message(role=MessageRole.USER, content="你好 hello"),
        ]
    )

    assert usage.total_tokens > 0
    assert usage.prompt_tokens == usage.total_tokens
    assert usage.completion_tokens == 0
    assert usage.estimated is True


def test_estimate_chat_usage_adds_completion_tokens() -> None:
    usage = estimate_chat_usage(
        [Message(role=MessageRole.USER, content="hello")],
        "world",
    )

    assert usage.total_tokens == (usage.prompt_tokens or 0) + (usage.completion_tokens or 0)
    assert usage.completion_tokens and usage.completion_tokens > 0
    assert usage.estimated is True


def test_estimate_text_tokens_handles_empty_text() -> None:
    tokens, tokenizer = estimate_text_tokens("")

    assert tokens == 0
    assert tokenizer


def test_combine_token_usages_sums_totals_and_marks_estimated() -> None:
    exact = token_usage_from_provider_usage({"prompt_tokens": 10, "completion_tokens": 5})
    estimated = estimate_chat_usage([Message(role=MessageRole.USER, content="hi")], "there")

    combined = combine_token_usages(exact, estimated)

    assert combined is not None
    assert combined.total_tokens == exact.total_tokens + estimated.total_tokens
    assert combined.prompt_tokens == (exact.prompt_tokens or 0) + (estimated.prompt_tokens or 0)
    assert combined.completion_tokens == (exact.completion_tokens or 0) + (estimated.completion_tokens or 0)
    assert combined.estimated is True