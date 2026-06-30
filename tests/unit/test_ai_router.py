from __future__ import annotations

from ai.base import AIResponse, BaseAIProvider, Message
from ai.router import AIRouter
from bot.handlers.chat_runtime import select_chat_runtime
from config.provider_loader import GlobalConfig, ProviderConfig


class FakeProvider(BaseAIProvider):
    instances: list[FakeProvider] = []

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.kwargs = kwargs
        FakeProvider.instances.append(self)

    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs,
    ) -> AIResponse:
        return AIResponse(content="ok", model=model or "fake")

    async def chat_stream(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ):
        yield "ok"

    def get_available_models(self) -> list[str]:
        return ["fake-model"]

    def validate_api_key(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "Fake"


def _config(
    name: str,
    *,
    api_key_literal: str | None = "sk-test",
    headers: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
) -> ProviderConfig:
    return ProviderConfig(
        name=name,
        transport="fake",
        default_model=f"{name}-model",
        models=[f"{name}-model"],
        api_key_literal=api_key_literal,
        headers=headers,
        query=query,
    )


def _router(configs: list[ProviderConfig], global_config: GlobalConfig) -> AIRouter:
    FakeProvider.instances.clear()
    original_registry = AIRouter.TRANSPORT_REGISTRY.copy()
    AIRouter.TRANSPORT_REGISTRY = {**original_registry, "fake": FakeProvider}
    try:
        return AIRouter(configs, global_config)
    finally:
        AIRouter.TRANSPORT_REGISTRY = original_registry


def test_default_provider_does_not_fall_back_to_first_available_provider() -> None:
    router = _router(
        [
            _config("zhipu", api_key_literal=None),
            _config("deepseek", api_key_literal="sk-deepseek"),
        ],
        GlobalConfig(default_provider="zhipu", available_providers=["zhipu", "deepseek"]),
    )

    assert router.list_available_providers() == ["deepseek"]
    assert router.get_default_provider() is None


def test_provider_headers_and_query_are_forwarded_to_provider_constructor() -> None:
    router = _router(
        [
            _config(
                "gateway",
                headers={"X-Tenant": "abc"},
                query={"api-version": "2026-06-30"},
            )
        ],
        GlobalConfig(default_provider="gateway", available_providers=["gateway"]),
    )

    provider = router.get_provider("gateway")
    assert provider is FakeProvider.instances[0]
    assert FakeProvider.instances[0].kwargs["headers"] == {"X-Tenant": "abc"}
    assert FakeProvider.instances[0].kwargs["query"] == {"api-version": "2026-06-30"}


def test_router_exposes_global_request_defaults() -> None:
    router = _router(
        [_config("zhipu")],
        GlobalConfig(
            default_provider="zhipu",
            default_model="glm-global",
            temperature=0.2,
            max_output_tokens=1234,
            streaming=False,
            available_providers=["zhipu"],
        ),
    )

    assert router.default_provider_name == "zhipu"
    assert router.default_model == "glm-global"
    assert router.temperature == 0.2
    assert router.max_output_tokens == 1234
    assert router.streaming is False


def test_select_chat_runtime_uses_global_defaults_and_effective_provider_name() -> None:
    router = _router(
        [_config("zhipu")],
        GlobalConfig(
            default_provider="zhipu",
            default_model="glm-global",
            temperature=0.2,
            max_output_tokens=1234,
            streaming=False,
            available_providers=["zhipu"],
        ),
    )
    user = type(
        "UserStub",
        (),
        {
            "preferred_provider": None,
            "preferred_model": None,
            "temperature": "0.7",
        },
    )()

    selection = select_chat_runtime(user, router)

    assert selection is not None
    assert selection.provider_name == "zhipu"
    assert selection.provider is router.get_provider("zhipu")
    assert selection.model_name == "glm-global"
    assert selection.temperature == 0.2
    assert selection.streaming is False
    assert selection.max_output_tokens == 1234


def test_select_chat_runtime_falls_back_to_default_for_missing_preferred_provider() -> None:
    router = _router(
        [_config("deepseek")],
        GlobalConfig(default_provider="deepseek", available_providers=["deepseek"]),
    )
    user = type(
        "UserStub",
        (),
        {
            "preferred_provider": "zhipu",
            "preferred_model": None,
            "temperature": None,
        },
    )()

    selection = select_chat_runtime(user, router)

    assert selection is not None
    assert selection.provider_name == "deepseek"
    assert selection.provider is router.get_provider("deepseek")
