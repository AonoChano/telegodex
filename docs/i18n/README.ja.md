<div align="center">

<img src="../assets/logo.svg" alt="Telegodex Logo" width="900">

# Telegodex

**Telegram Workbench Project。Telegram から Codex を操作する。**  
複数 AI Provider、TOML Provider registry、Codex bridge foundation、Telegram ネイティブのリッチ出力を備えています。

<p>
  <a href="../../LICENSE"><img src="https://img.shields.io/badge/License-MIT-22c55e.svg" alt="License"></a>
  <a href="#技術スタック"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://docs.aiogram.dev/"><img src="https://img.shields.io/badge/aiogram-3.x-26A5E4?logo=telegram&logoColor=white" alt="aiogram 3.x"></a>
  <a href="#技術スタック"><img src="https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy 2.x"></a>
  <a href="#ロードマップ"><img src="https://img.shields.io/badge/status-active%20development-f59e0b.svg" alt="Active development"></a>
</p>

[English](../../README.md) · [简体中文](./README.zh-CN.md) · <u>日本語</u>

</div>

---

## このプロジェクトについて

Telegodex は、スマートフォンからローカル CLI AI ワークフローを操作するための Telegram ワークベンチです。

主目的は、PC 上で動く Codex CLI セッションのモバイル操作面として Telegram を使うことです。Codex は Telegodex 内部の Agent ではありません。独立した外部 CLI/runtime プロセスであり、Telegodex は対応する machine-readable interface を通じて起動、接続、表示、操作します。

目的は三つあります。

- **Codex / CLI Agent のリモート操作。** Telegram topic から、ターミナル級の AI 作業を resume、bind、operate、approve、inspect できます。
- **補助的な複数 AI Provider チャット。** Telegram を離れずに、OpenAI、Anthropic、Google、DeepSeek、Qwen、Kimi、GLM、ERNIE へ軽い質問ができます。
- **TOML Provider registry。** `provider.toml` で OpenAI-compatible endpoint を追加、無効化、切り替えできます。

Telegodex は単なるチャット Bot ではありません。  
Telegram とローカル AI コマンドライン作業をつなぐ bridge です。

---

## できること

- **Telegram から Codex ワークフローを操作する。** プロンプト送信、thread resume、ストリーム出力、approval 処理をモバイル上で行います。
- **AI 出力を Telegram ネイティブに表示する。** コードブロック、テーブル、リスト、引用、折りたたみ領域、数式、構造化サマリーを扱います。
- **Provider をまたいで同じ体験を保つ。** handler と UX は同じまま、バックエンドだけを差し替えます。
- **ローカル / セルフホストの endpoint を使う。** Ollama、vLLM、LiteLLM、Azure、LM Studio、その他 OpenAI-compatible サービスに接続できます。
- **通常チャットのローカルツール利用を制御する。** テキストのみ、インライン確認、または許可済み shell tool の直接実行を選べます。
- **ユーザー単位の状態を保存する。** 履歴、設定、モデル選択、temperature、レート制限を保持します。

---

## 現在の焦点

プロジェクトは、汎用 AI Bot ではなく Telegram-to-Codex Workbench へ方向修正しています。

### Stage 1
- 補助的な複数 Provider チャット基盤
- TOML Provider registry
- Telegram ネイティブ表示
- ストレージ、ユーザー設定、セキュリティ

### Stage 2
- `codex app-server` による Codex CLI bridge foundation
- Codex thread resume、Telegram topic binding、出力ストリーミング
- インライン承認プロンプト
- ツール呼び出しの可視化とローカル shell 権限制御

### Stage 3
- 完全な Codex topic workbench UX
- Codex が公開する場合は、Codex 自身の background/sub-agent activity を表示する
- Claude Code / other CLI bridges
- Dashboard とデプロイ支援

---

## クイックスタート

```bash
git clone https://github.com/CYcha/Telegodex.git
cd Telegodex
pip install -r requirements.txt
cp .env.example .env
cp provider.toml.example provider.toml
```

`.env` に `TELEGRAM_BOT_TOKEN` と `provider.toml` が参照する Provider key を設定します。
次に `[global].available_providers` で有効な Provider を選び、起動します。

```bash
python run.py --check-config
python run.py
```

Telegram で Bot に `/start` を送ります。

手順の詳細：[docs/QUICKSTART.md](../QUICKSTART.md)

---

## Custom Provider を追加する

```toml
[global]
default_provider = "ollama"
available_providers = ["ollama"]

[providers.ollama]
transport = "openai_compatible"
api_key_literal = "ollama"
base_url = "http://localhost:11434/v1"
default_model = "llama3.2"
models = ["llama3.2"]
```

このブロックを `provider.toml` に追加し、`python run.py --check-config` を実行してから再起動すると、Provider が使えるようになります。

参照：[docs/CUSTOM_PROVIDERS.md](../CUSTOM_PROVIDERS.md)

---

## レイアウト

```text
ai/          BaseAIProvider と Provider 実装
bot/         aiogram handlers、keyboards、rich rendering
storage/     SQLAlchemy async ORM (User, Conversation, Message)
security/    rate limit、admin gate、input validation
extensions/  Codex と Claude Code bridges
```

Provider contract:

- `chat()`
- `chat_stream()`
- `get_available_models()`
- `validate_api_key()`

router が Provider を選びます。  
handler は具体的なバックエンドを知りません。

---

## 対応 Provider

| Region | Provider | Default models |
|---|---|---|
| International | OpenAI, Anthropic, Google | `provider.toml` で設定 |
| China | DeepSeek, Qwen, Kimi, GLM, ERNIE | `provider.toml` で設定 |

OpenAI-compatible endpoint は `provider.toml` から追加できます。

一覧：[docs/MODELS.md](../MODELS.md)

---

## 技術スタック

Python 3.11+ · aiogram 3.x · SQLAlchemy 2.x async · Pydantic Settings · Alembic · Redis (optional)

---

## ドキュメント

- [Quickstart](../QUICKSTART.md)
- [Usage](../USAGE.md)
- [プロダクト体験](../PRODUCT_EXPERIENCE.md)
- [Architecture](../ARCHITECTURE.md)
- [Custom providers](../CUSTOM_PROVIDERS.md)
- [Model catalog](../MODELS.md)
- [Rich messages](../RICH_MESSAGES.md)

---

## ロードマップ

- [x] Multi-provider abstraction
- [x] Rich Telegram rendering
- [x] Context windowing and user preferences
- [x] Codex bridge foundation
- [ ] Hot reload model mechanism
- [ ] Codex thread resume と Telegram topic binding の polish
- [ ] 完全な Codex Workbench UX
- [ ] Claude Code bridge
- [ ] Codex の task engine を重複実装せず、Codex-owned long-running work を表示する
- [ ] Web admin dashboard
- [ ] Voice and image input
- [ ] Docker compose & Helm chart

---

## コントリビュート

変更前に [docs/ARCHITECTURE.md](../ARCHITECTURE.md) を読んでください。

---
## Star History

[![Star History Chart](https://star-history.com)](https://star-history.com)

---

## ライセンス

MIT。詳しくは [LICENSE](../../LICENSE) を参照してください。
