<div align="center">

<img src="../assets/logo.svg" alt="Telegodex Logo" width="900">

# Telegodex

**Telegram Workbench Project。Telegram から Codex を操作する。**  
複数 AI Provider、自作 Provider 設定、Telegram ネイティブのリッチ出力を備えています。

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

Telegodex は Telegram 上で動く AI ワークベンチです。

目的は三つあります。

- **Codex / CLI Agent のリモート操作。** ターミナルで行う AI 作業を Telegram に持ち込み、スマートフォンから操作できるようにします。
- **複数 AI Provider への接続。** OpenAI、Anthropic、Google、DeepSeek、Qwen、Kimi、GLM、ERNIE を一つの UI で切り替えます。
- **Custom Provider の注入。** OpenAI-compatible endpoint を JSON 設定だけで追加できます。コアコードを変える必要はありません。

Telegodex は単なるチャット Bot ではありません。  
AI 作業のための操作面です。

---

## できること

- **Telegram から Codex ワークフローを操作する。** プロンプトを送り、ストリーム出力を受け取り、操作を確認し、モバイル上で作業を続けます。
- **AI 出力を Telegram ネイティブに表示する。** コードブロック、テーブル、リスト、引用、折りたたみ領域、数式、構造化サマリーを扱います。
- **Provider をまたいで同じ体験を保つ。** handler と UX は同じまま、バックエンドだけを差し替えます。
- **ローカル / セルフホストの endpoint を使う。** Ollama、vLLM、LiteLLM、Azure、LM Studio、その他 OpenAI-compatible サービスに接続できます。
- **ユーザー単位の状態を保存する。** 履歴、設定、モデル選択、temperature、レート制限を保持します。
- **基本的な安全境界を保つ。** 入力のサニタイズ、管理者 allow-list、API key をログに出さない設計を使います。

---

## 現在の焦点

プロジェクトは汎用 AI Bot から Telegram Workbench へ移行中です。

### Stage 1
- 複数 Provider のチャット基盤
- Custom Provider システム
- Telegram ネイティブ表示
- ストレージ、ユーザー設定、セキュリティ

### Stage 2
- Codex CLI bridge
- リモート実行 / コマンド中継
- セッション同期と出力ストリーミング
- 操作確認とツール呼び出しの可視化

### Stage 3
- Claude Code bridge
- Telegram 内の Agent ワークフロー
- 長時間タスクの編成
- Dashboard とデプロイ支援

---

## クイックスタート

```bash
git clone https://github.com/CYcha/Telegodex.git
cd Telegodex
pip install -r requirements.txt
cp .env.example .env
```

`.env` に `TELEGRAM_BOT_TOKEN` と少なくとも一つの Provider key を設定し、起動します。

```bash
python run.py
```

Telegram で Bot に `/start` を送ります。

手順の詳細：[docs/QUICKSTART.md](../QUICKSTART.md)

---

## Custom Provider を追加する

```json
{
  "ollama": {
    "type": "openai_compatible",
    "base_url": "http://localhost:11434/v1",
    "models": ["llama3.2"]
  }
}
```

このブロックを `custom_providers.json` に追加して再起動すると、Provider が使えるようになります。

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
| International | OpenAI, Anthropic, Google | `gpt-4o`, `claude-sonnet-4.6`, `gemini-2.0-flash` |
| China | DeepSeek, Qwen, Kimi, GLM, ERNIE | `deepseek-v4-pro`, `qwen-max`, `kimi-k2-7-code`, `glm-4-6`, `ernie-5.0` |

OpenAI-compatible endpoint は `custom_providers.json` から追加できます。

一覧：[docs/MODELS.md](../MODELS.md)

---

## 技術スタック

Python 3.11+ · aiogram 3.x · SQLAlchemy 2.x async · Pydantic Settings · Alembic · Redis (optional)

---

## ドキュメント

- [Quickstart](../QUICKSTART.md)
- [Usage](../USAGE.md)
- [Architecture](../ARCHITECTURE.md)
- [Custom providers](../CUSTOM_PROVIDERS.md)
- [Model catalog](../MODELS.md)
- [Rich messages](../RICH_MESSAGES.md)

---

## ロードマップ

- [x] Multi-provider abstraction
- [x] Rich Telegram rendering
- [x] Context windowing and user preferences
- [ ] Codex bridge
- [ ] Claude Code bridge
- [ ] Agent/task execution layer
- [ ] Web admin dashboard
- [ ] Voice and image input
- [ ] Docker compose & Helm chart

---

## コントリビュート

PR を歓迎します。変更前に [docs/ARCHITECTURE.md](../ARCHITECTURE.md) を読んでください。

---

## セキュリティ

脆弱性はメンテナーへ非公開で報告してください。

コードベースで守ること：

- API key をログに出さない
- すべての境界で入力をサニタイズする
- `ADMIN_USER_IDS` allow-list を使う
- ユーザー単位でレート制限する

---

## ライセンス

MIT。詳しくは [LICENSE](../../LICENSE) を参照してください。
