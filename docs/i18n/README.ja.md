<div align="center">

<img src="../assets/logo.svg" alt="Telegodex Logo" width="900">

# 🐉 Telegodex

Telegram 上で AI チャットを動かすための Bot フレームワーク。8 プロバイダーを内蔵し、JSON 設定でさらに追加可能。

<p>
  <a href="../../LICENSE"><img src="https://img.shields.io/badge/License-MIT-22c55e.svg" alt="License"></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://docs.aiogram.dev/"><img src="https://img.shields.io/badge/aiogram-3.x-26A5E4?logo=telegram&logoColor=white" alt="aiogram 3.x"></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy 2.x"></a>
  <a href="#roadmap"><img src="https://img.shields.io/badge/status-active%20development-f59e0b.svg" alt="Active development"></a>
</p>

[English](../../README.md) · [简体中文](./README.zh-CN.md) · 日本語

</div>

---

## 概要

Telegram Bot フレームワーク。デモでは省かれがちな本番向けの作り込みを含みます。

- **8 プロバイダー、1 つのインターフェース。** OpenAI、Anthropic、Google、DeepSeek、Qwen、Kimi、GLM、ERNIE。設定フラグ 1 つで切替。
- **JSON で独自 Provider を追加。** OpenAI 互換エンドポイント（Ollama、vLLM、LiteLLM、Azure、LM Studio）を `custom_providers.json` に追記。コード変更なし。
- **新 Provider を 50 行未満で。** `BaseAIProvider` を継承し、4 メソッドを実装し、router に登録。プラグインであり、fork ではない。
- **Telegram ネイティブ描画。** MarkdownV2（表、ToDo、注釈、展開可能引用、LaTeX）。インラインボタン、返信キーボード、モデル・温度ピッカー。
- **永続化とセキュリティ標準装備。** 会話履歴、ユーザー単位の好み、レート制限、管理者許可リスト、入力サニタイズ、ログに機密なし。

## クイックスタート

```bash
git clone https://github.com/CYcha/Telegodex.git
cd Telegodex
pip install -r requirements.txt
cp .env.example .env
```

`.env` に `TELEGRAM_BOT_TOKEN` と 1 つ以上の Provider キーを記入してから：

```bash
python run.py
```

Bot に `/start` を送る。

詳細：[docs/QUICKSTART.md](../QUICKSTART.md)。

## 独自 Provider の追加

```json
{
  "ollama": {
    "type": "openai_compatible",
    "base_url": "http://localhost:11434/v1",
    "models": ["llama3.2"]
  }
}
```

`custom_providers.json` に追記して再起動。

リファレンス：[docs/CUSTOM_PROVIDERS.md](../CUSTOM_PROVIDERS.md)。

## ディレクトリ構成

```
ai/          BaseAIProvider + 8 実装
bot/         aiogram ハンドラ、キーボード、リッチ描画
storage/     SQLAlchemy 非同期 ORM（User、Conversation、Message）
security/    レート制限、管理者ゲート、入力検証
extensions/  Codex、Claude Code ブリッジ
```

Provider 契約：`chat()`、`chat_stream()`、`get_available_models()`、`validate_api_key()`。router で差し替えれば、ハンドラはそのまま。

## 対応 Provider

| 地域 | Provider | デフォルトモデル |
|---|---|---|
| 国際 | OpenAI、Anthropic、Google | `gpt-4o`、`claude-sonnet-4.6`、`gemini-2.0-flash` |
| 中国 | DeepSeek、Qwen、Kimi、GLM、ERNIE | `deepseek-v4-pro`、`qwen-max`、`kimi-k2-7-code`、`glm-4-6`、`ernie-5.0` |

`custom_providers.json` 経由で任意の OpenAI 互換エンドポイント対応。モデル一覧：[docs/MODELS.md](../MODELS.md)。

## テックスタック

Python 3.11+ · aiogram 3.x · SQLAlchemy 2.x async · Pydantic Settings · Alembic · Redis（任意）

## ドキュメント

- [クイックスタート](../QUICKSTART.md)
- [利用ガイド](../USAGE.md)
- [アーキテクチャ](../ARCHITECTURE.md)
- [カスタム Provider](../CUSTOM_PROVIDERS.md)
- [モデル一覧](../MODELS.md)
- [リッチメッセージ](../RICH_MESSAGES.md)

## ロードマップ

- [x] マルチ Provider 抽象（v1.0）
- [x] リッチ Markdown、インタラクティブキーボード、コンテキストウィンドウ（v1.1）
- [ ] Codex ブリッジ
- [ ] Claude Code ブリッジ
- [ ] Web 管理ダッシュボード
- [ ] 音声・画像入力
- [ ] Docker compose / Helm chart

## コントリビュート

PR 歓迎。まず [docs/ARCHITECTURE.md](../ARCHITECTURE.md) と [CLAUDE.md](../../CLAUDE.md) を読むこと。

## セキュリティ

脆弱性：公開 Issue ではなく直接メンテナーにメール（コミット履歴参照）。

コードで強制される事項：API キー非ログ出力、全境界でのサニタイズ、`ADMIN_USER_IDS` 許可リスト、ユーザー単位レート制限。

## ライセンス

MIT。[LICENSE](../../LICENSE) を参照。

