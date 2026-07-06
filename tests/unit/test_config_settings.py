from config import Settings


def test_settings_allows_missing_telegram_bot_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    settings = Settings(_env_file=None)

    assert settings.telegram_bot_token == ""