# Discord Twitter/X Translation Bot

Discordに投稿されたTwitter/Xのリンクを検出し、投稿本文を翻訳して返信するBOTです。
翻訳返信には言語切り替えボタンが付き、日本語・英語・中国語・韓国語へその場で切り替えられます。

## Features

- `twitter.com`、`x.com`、`fxtwitter.com`、`fixupx.com`、`vxtwitter.com` の投稿リンクを検出
- FxTwitter/FxEmbed APIから投稿本文と翻訳文を取得
- デフォルト言語以外の投稿だけ自動翻訳
- 翻訳返信に `日本語`、`English`、`中文`、`한국어` の切り替えボタンを表示
- 原文と同じ言語のボタンは表示しない
- 日本語など翻訳不要の投稿でも、動画付きの場合は `fxtwitter.com` リンクを返信
- `/set_ui_lang` でBOTの応答メッセージを日本語・英語・中国語・韓国語に変更可能
- `/translate_tweet` でURLと言語を指定して手動翻訳
- `/set_default_lang` で自動翻訳のデフォルト言語を変更
- Dockerfile同梱のため、Northflankなどのコンテナホスティングへデプロイ可能
- (予定)応答メッセージを4ヶ国語に変更するコマンドを実装中

## Supported Languages

| Code | Language | API code |
| --- | --- | --- |
| `ja` | 日本語 | `ja` |
| `en` | English | `en` |
| `zh` | 中文 | `zh` |
| `ko` | 한국어 | `ko` |


## Slash Commands

| Command | Description |
| --- | --- |
| `/ping` | BOTのWebSocket latencyとInteraction応答時間を表示 |
| `/tweet_test url:<URL>` | Twitter/Xリンクの検出、取得、翻訳可否を確認 |
| `/translate_tweet url:<URL> lang:<ja/en/zh/ko>` | 指定した投稿を指定言語へ翻訳 |
| `/set_default_lang lang:<ja/en/zh/ko>` | 自動翻訳のデフォルト言語を変更 |
| `/set_ui_lang lang:<ja/en/zh/ko>` | BOTからの案内やエラーなどの表示言語を変更 |

`/set_default_lang` はサーバー管理権限を持つユーザー向けのコマンドです。
変更したデフォルト言語は `bot_config.json` に保存され、BOT再起動後も維持されます。

翻訳返信の下に表示される言語ボタンは、BOTが起動している間は時間経過で無効化されません。
原文と同じ言語のボタンは表示されません。
BOTを再起動した後に古い返信のボタンが反応しない場合は、もう一度リンクを投稿するか `/translate_tweet` を使ってください。

## Requirements

- Python 3.11以上
- Discord BOTトークン
- Discord Developer Portalで `MESSAGE CONTENT INTENT` を有効化
- BOT招待時に `bot` と `applications.commands` scope を付与

## Discord Bot Setup

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーションを作成します。
2. `Bot` 画面でBOTを作成し、トークンを控えます。
3. `Privileged Gateway Intents` の `MESSAGE CONTENT INTENT` を有効にします。
4. `OAuth2` → `URL Generator` を開きます。
5. `SCOPES` で `bot` と `applications.commands` を選択します。
6. `BOT PERMISSIONS` で最低限以下を選択します。

| Permission | Purpose |
| --- | --- |
| `View Channels` | 対象チャンネルを見る |
| `Send Messages` | 翻訳結果を返信する |
| `Read Message History` | メッセージ内容を扱う |
| `Use Slash Commands` | スラッシュコマンドを使う |

生成されたURLからBOTをサーバーに招待してください。

## Local Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` を開き、`DISCORD_TOKEN` にBOTトークンを設定します。

```env
DISCORD_TOKEN=your_discord_bot_token
TARGET_LANG=ja
BOT_CONFIG_PATH=bot_config.json
LOG_LEVEL=INFO
```

開発中は `DISCORD_GUILD_ID` にテスト用サーバーIDを入れると、スラッシュコマンドがそのサーバーへ即時同期されます。
空欄の場合はグローバル同期になり、Discord側の反映に時間がかかることがあります。

## Run

仮想環境を有効化している場合:

```powershell
python -m src.bot
```

仮想環境を有効化していない場合:

```powershell
.\.venv\Scripts\python.exe -m src.bot
```

起動ログに `Logged in as ...` が表示されれば起動成功です。

## Environment Variables

| Name | Required | Description |
| --- | --- | --- |
| `DISCORD_TOKEN` | Yes | Discord BOTトークン |
| `DISCORD_GUILD_ID` | No | 開発用サーバーID。設定するとスラッシュコマンドをそのサーバーへ即時同期 |
| `TARGET_LANG` | No | 起動時の翻訳先。`ja`、`en`、`zh`、`ko` に対応。既定値は `ja` |
| `BOT_CONFIG_PATH` | No | `/set_default_lang` の保存先。既定値は `bot_config.json` |
| `FXTWITTER_API_BASE` | No | FxTwitter/FxEmbed APIのURL |
| `REQUEST_TIMEOUT_SECONDS` | No | APIリクエストのタイムアウト秒数 |
| `LOG_LEVEL` | No | `INFO`、`DEBUG` など |

`.env` と `bot_config.json` は公開しないでください。
このリポジトリでは `.gitignore` に追加済みです。

## Docker

このリポジトリには `Dockerfile` が含まれています。
コンテナ環境では環境変数をホスティングサービス側に設定してください。

```bash
docker build -t discord-twitter-translation-bot .
docker run --env-file .env discord-twitter-translation-bot
```

## Deploy to Northflank

Northflankなどのコンテナ対応ホスティングでは、GitHubリポジトリを接続してDockerfileからビルドできます。

1. GitHubにこのリポジトリをpushします。
2. Northflankで `Create service` を選びます。
3. GitHubリポジトリを接続します。
4. Build methodで `Dockerfile` を選びます。
5. Dockerfile pathを `/Dockerfile` にします。
6. Start commandは空欄で構いません。
7. Ports / Networking は不要です。
8. Environment variablesに必要な値を登録します。

最低限必要な環境変数:

```env
DISCORD_TOKEN=your_discord_bot_token
TARGET_LANG=ja
BOT_CONFIG_PATH=bot_config.json
LOG_LEVEL=INFO
```

デプロイ後、ログに `Logged in as ...` が表示されれば起動成功です。

## Tests

```powershell
python -m unittest discover -s tests
```

構文チェック:

```powershell
python -m compileall src tests
```

## Notes

- 投稿本文と翻訳の取得には公開のFxTwitter/FxEmbed APIを使用しています。
- 非公開投稿、削除済み投稿、API側で翻訳文が返らない投稿は翻訳できません。
- DiscordやFxTwitter/FxEmbed APIの仕様変更、レート制限により一時的に動作しない場合があります。

Reference: [FxEmbed API - Get status](https://docs.fxembed.com/api/twitter/operations/2statusid/)
