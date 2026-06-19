from __future__ import annotations

from types import SimpleNamespace

from bot.startup import (
    TELEGRAM_BOT_COMMANDS,
    check_threaded_mode,
    configure_bot_commands,
)


class FakeStartupBot:
    def __init__(self, me: object | None = None) -> None:
        self.me = me
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    async def set_my_commands(self, commands: object, **kwargs: object) -> bool:
        self.calls.append(("set_my_commands", (commands,), kwargs))
        return True

    async def get_me(self) -> object:
        self.calls.append(("get_me", (), {}))
        return self.me or SimpleNamespace(username="telegodex_bot")

    async def send_message(self, chat_id: int, text: str, **kwargs: object) -> bool:
        self.calls.append(("send_message", (chat_id, text), kwargs))
        return True

    def get_calls(self, method: str) -> list[tuple[str, tuple[object, ...], dict[str, object]]]:
        return [call for call in self.calls if call[0] == method]


async def test_configure_bot_commands_sets_expected_menu() -> None:
    bot = FakeStartupBot()

    assert await configure_bot_commands(bot)

    calls = bot.get_calls("set_my_commands")
    assert len(calls) == 1
    commands = calls[0][1][0]
    assert commands == list(TELEGRAM_BOT_COMMANDS)
    assert [command.command for command in commands] == [
        "start",
        "help",
        "new",
        "clear",
        "settings",
        "codex",
        "model",
        "shell",
        "send",
        "history",
        "status",
        "stop",
        "live",
        "last",
        "screenshot",
    ]


async def test_check_threaded_mode_enabled_does_not_notify_admins() -> None:
    bot = FakeStartupBot(SimpleNamespace(username="telegodex_bot", has_topics_enabled=True))

    assert await check_threaded_mode(bot, admin_ids=[1001])

    assert len(bot.get_calls("get_me")) == 1
    assert bot.get_calls("send_message") == []


async def test_check_threaded_mode_disabled_notifies_admins() -> None:
    bot = FakeStartupBot(SimpleNamespace(username="telegodex_bot", has_topics_enabled=False))

    assert not await check_threaded_mode(bot, admin_ids=[1001, 1002])

    sends = bot.get_calls("send_message")
    assert len(sends) == 2
    assert sends[0][1][0] == 1001
    assert "Threaded Mode" in sends[0][1][1]
    assert "BotFather" in sends[0][1][1]
    assert "Forum supergroup topics are separate" in sends[0][1][1]
