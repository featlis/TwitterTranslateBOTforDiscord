# Discord Twitter/X Translation Bot / Discord 用 Twitter/X 翻訳ボット

## English — Project Overview

This repository contains a Discord bot that detects Twitter/X links posted in Discord, fetches the tweet content using public FxTwitter/FxEmbed APIs, and replies with an automatic translation. The bot shows language-switch buttons on the reply so users can switch the translated text between Japanese, English, Chinese, and Korean on the fly.

Key features

- Detects tweet links from `twitter.com`, `x.com`, `fxtwitter.com`, `fixupx.com`, `vxtwitter.com`.
- Fetches tweet text and translation using FxTwitter / FxEmbed APIs.
- Automatically translates tweets when the source language is different from the configured default target language.
- Reply includes language-switch buttons (日本語 / English / 中文 / 한국어). Buttons for the original-language are not shown.
- For tweets that do not need translation but contain video, the bot can reply with an `fxtwitter.com` link so the media can be viewed.
- Slash commands to test and control behavior: `/tweet_test`, `/translate_tweet`, `/set_default_lang`, `/set_ui_lang`, and `/ping`.
- Dockerfile included for containerized deployment (e.g. Northflank).

Supported languages

| Code | Language |
| ---: | :--- |
| `ja` | Japanese / 日本語 |
| `en` | English |
| `zh` | Chinese / 中文 |
| `ko` | Korean / 한국語 |

Slash commands

| Command | Description |
| --- | --- |
| `/ping` | Shows bot WebSocket latency and interaction response time |
| `/tweet_test url:<URL>` | Tests detection/fetching/translation availability for a Twitter/X link |
| `/translate_tweet url:<URL> lang:<ja/en/zh/ko>` | Translate the specified tweet into the chosen language |
| `/set_default_lang lang:<ja/en/zh/ko>` | Change the server default automatic-translation target (requires server admin) |
| `/set_ui_lang lang:<ja/en/zh/ko>` | Change the language used for bot messages and errors |

Notes about slash commands

- `/set_default_lang` is intended for server administrators. The chosen default is stored in `bot_config.json` and persists across restarts.
- Language buttons on bot replies remain active while the bot is running. If buttons become unresponsive after a bot restart, re-post the link or use `/translate_tweet`.

Requirements

- Python 3.11 or newer
- A Discord bot token
- Enable MESSAGE CONTENT INTENT in the Discord Developer Portal
- When inviting the bot, include `bot` and `applications.commands` OAuth scopes and grant minimal required permissions (View Channels, Send Messages, Read Message History, Use Slash Commands).

Discord Bot setup (summary)

1. Create an application in the Discord Developer Portal: https://discord.com/developers/applications
2. Create a Bot user and copy its token.
3. Enable `MESSAGE CONTENT INTENT` under Privileged Gateway Intents.
4. Use OAuth2 URL Generator to create an invite URL with `bot` and `applications.commands` scopes and invite the bot to your server.

Local development / install

1. Create and activate a virtualenv:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

2. Edit `.env` (or create it from `env_sample.txt`) and set your token and settings. Example:

```env
DISCORD_TOKEN=your_discord_bot_token
TARGET_LANG=ja
BOT_CONFIG_PATH=bot_config.json
LOG_LEVEL=INFO
```

3. (Optional) For faster slash-command testing during development, set `DISCORD_GUILD_ID` to your test server ID. Otherwise the commands will sync globally and may take longer to appear.

Running the bot

- If your virtualenv is active:

```powershell
python -m src.bot
```

- If not active:

```powershell
.\.venv\Scripts\python.exe -m src.bot
```

Check the logs for `Logged in as ...` to confirm successful startup.

Environment variables reference

| Name | Required | Description |
| --- | ---: | :--- |
| `DISCORD_TOKEN` | Yes | Discord bot token. Keep secret. |
| `DISCORD_GUILD_ID` | No | Test guild ID for immediate slash-command sync (development only). |
| `TARGET_LANG` | No | Default translation target on startup (`ja`, `en`, `zh`, `ko`). Default: `ja`. |
| `BOT_CONFIG_PATH` | No | Path to the persistent bot config file. Default: `bot_config.json`. |
| `FXTWITTER_API_BASE` | No | FxTwitter/FxEmbed API base URL (if overriding). |
| `REQUEST_TIMEOUT_SECONDS` | No | API request timeout in seconds. |
| `LOG_LEVEL` | No | Logging level like `INFO`, `DEBUG`. |

Security and Bot token handling (important)

- Never commit `.env` or `bot_config.json` containing tokens or secrets to version control. This repository already lists these files in `.gitignore`.
- Treat your `DISCORD_TOKEN` like any secret: store it in your host or CI provider's secret manager.
- For containerized hosting (Docker, Northflank, etc.) use the platform's environment-secret mechanism rather than embedding tokens in images.
- If a token is accidentally leaked, immediately rotate it from the Discord Developer Portal.

Docker

This repository includes a `Dockerfile`. Build and run locally for testing:

```bash
docker build -t discord-twitter-translation-bot .
docker run --env-file .env discord-twitter-translation-bot
```

Deploying to container platforms (example: Northflank)

- Connect your GitHub repository to the hosting platform and select Dockerfile build.
- Configure environment variables / secrets in the hosting platform (DO NOT push them to the repo).
- Minimum required environment variables:

```env
DISCORD_TOKEN=your_discord_bot_token
TARGET_LANG=ja
BOT_CONFIG_PATH=bot_config.json
LOG_LEVEL=INFO
```

When deployed, check logs for `Logged in as ...` to confirm the bot is running.

Testing

Run unit tests included in the `tests/` directory:

```powershell
python -m unittest discover -s tests
```

Code quality

Run simple syntax checks:

```powershell
python -m compileall src tests
```

Contributing

Contributions are welcome. To contribute:

1. Fork this repository and create a feature branch.
2. Make changes and add tests where appropriate.
3. Run tests locally and fix linting/formatting issues.
4. Open a pull request describing the change.

When opening issues or PRs, include: the bot version / commit, Python version, and a short reproduction or logs if applicable.

License

This project is licensed under the MIT License. See the License section below.

---

## 日本語 — プロジェクト概要

このリポジトリは、Discordに投稿されたTwitter/Xリンクを検出し、FxTwitter/FxEmbedなどの公開APIから本文と翻訳を取得して返信するDiscord用ボットを提供します。返信には日本語・英語・中国語・韓国語の切替ボタンが付き、その場で翻訳を切り替えられます。

主な機能

- `twitter.com`、`x.com`、`fxtwitter.com`、`fixupx.com`、`vxtwitter.com` の投稿リンクを検出
- FxTwitter / FxEmbed APIを使って投稿本文と翻訳を取得
- 投稿言語がデフォルトの翻訳先と異なる場合に自動で翻訳
- 返信に言語切替ボタン（日本語 / English / 中文 / 한국어）を表示。元の言語と同じボタンは表示しません。
- 翻訳不要な投稿でも動画がある場合、`fxtwitter.com` などのメディアリンクを返信可能
- `/tweet_test`、`/translate_tweet`、`/set_default_lang`、`/set_ui_lang`、`/ping` などのスラッシュコマンドを提供
- Dockerfileが含まれており、Northflank などのコンテナホスティングにデプロイできます

対応言語

| コード | 言語 |
| ---: | :--- |
| `ja` | 日本語 |
| `en` | English |
| `zh` | 中文 |
| `ko` | 한국語 |

スラッシュコマンド

| コマンド | 説明 |
| --- | --- |
| `/ping` | BOTのWebSocketレイテンシとInteraction応答時間を表示 |
| `/tweet_test url:<URL>` | Twitter/Xリンクの検出・取得・翻訳可否を確認 |
| `/translate_tweet url:<URL> lang:<ja/en/zh/ko>` | 指定投稿を指定言語に翻訳 |
| `/set_default_lang lang:<ja/en/zh/ko>` | 自動翻訳のサーバー既定言語を変更（管理者向け） |
| `/set_ui_lang lang:<ja/en/zh/ko>` | BOTの案内表示言語を変更 |

注意事項

- `/set_default_lang` はサーバー管理者向けコマンドです。設定は `bot_config.json` に保存され、再起動後も維持されます。
- 返信の言語ボタンはBOTが動作している間は有効です。再起動後に古いボタンが反応しない場合はリンクを再投稿するか `/translate_tweet` をお使いください。

要件

- Python 3.11 以上
- Discord BOTトークン
- Discord Developer Portalで `MESSAGE CONTENT INTENT` を有効化
- BOT招待時に `bot` と `applications.commands` スコープを付与し、最低限の権限（チャンネル閲覧、メッセージ送信、メッセージ履歴を読む、スラッシュコマンド利用）を与える

Discord ボットのセットアップ（概要）

1. Discord Developer Portal（https://discord.com/developers/applications）でアプリケーションを作成
2. Botユーザーを作成し、トークンを控える
3. Privileged Gateway Intentsで `MESSAGE CONTENT INTENT` を有効にする
4. OAuth2のURLジェネレータで `bot` と `applications.commands` を選択して招待URLを作成し、サーバーに招待する

ローカル開発 / インストール

1. 仮想環境を作成して有効化:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

2. `.env` を `env_sample.txt` を参考に編集し、トークンや設定を入れる:

```env
DISCORD_TOKEN=your_discord_bot_token
TARGET_LANG=ja
BOT_CONFIG_PATH=bot_config.json
LOG_LEVEL=INFO
```

3. 開発中は `DISCORD_GUILD_ID` にテスト用サーバーIDを設定するとスラッシュコマンドの反映が速くなります。

起動方法

- 仮想環境が有効な場合:

```powershell
python -m src.bot
```

- 有効でない場合:

```powershell
.\.venv\Scripts\python.exe -m src.bot
```

ログに `Logged in as ...` が出力されれば起動成功です。

環境変数一覧

| 名前 | 必須 | 説明 |
| --- | ---: | :--- |
| `DISCORD_TOKEN` | 必須 | Discord ボットのトークン。機密扱い |
| `DISCORD_GUILD_ID` | 任意 | 開発用サーバーID（テスト用）。設定すると即時同期されます |
| `TARGET_LANG` | 任意 | 起動時の既定翻訳先（`ja`、`en`、`zh`、`ko`）。既定: `ja` |
| `BOT_CONFIG_PATH` | 任意 | `/set_default_lang` の保存先（既定: `bot_config.json`） |
| `FXTWITTER_API_BASE` | 任意 | FxTwitter/FxEmbed APIのベースURL（上書き時） |
| `REQUEST_TIMEOUT_SECONDS` | 任意 | APIリクエストのタイムアウト（秒） |
| `LOG_LEVEL` | 任意 | ログレベル（例: `INFO`, `DEBUG`） |

トークンの扱い（重要）

- `.env` や `bot_config.json` にトークンを含めた状態でコミットしないでください。このリポジトリはすでに `.gitignore` に登録しています。
- `DISCORD_TOKEN` は必ずホストやCIのシークレットマネージャに保存してください。
- コンテナホスティングを利用する場合は、プラットフォームのシークレット機能を使って環境変数を注入してください。
- トークンが漏えいしたと思われる場合は、Discord Developer Portalでただちにローテーション（再発行）してください。

Docker

This repository includes a `Dockerfile`. Build and run locally for testing:

```bash
docker build -t discord-twitter-translation-bot .
docker run --env-file .env discord-twitter-translation-bot
```

Northflank等へのデプロイ（概要）

- GitHubリポジトリをホスティングプラットフォームに接続し、Dockerfileビルドを選びます。
- 環境変数/シークレットはホスティングプラットフォーム上で設定してください（リポジトリに含めない）。
- 最低限必要な環境変数:

```env
DISCORD_TOKEN=your_discord_bot_token
TARGET_LANG=ja
BOT_CONFIG_PATH=bot_config.json
LOG_LEVEL=INFO
```

デプロイ後はログに `Logged in as ...` が表示されれば正常に稼働しています。

テスト

```powershell
python -m unittest discover -s tests
```

Code quality

Run simple syntax checks:

```powershell
python -m compileall src tests
```

Contributing

Contributions are welcome. To contribute:

1. Fork this repository and create a feature branch.
2. Make changes and add tests where appropriate.
3. Run tests locally and fix linting/formatting issues.
4. Open a pull request describing the change.

When opening issues or PRs, include: the bot version / commit, Python version, and a short reproduction or logs if applicable.

License

This project is licensed under the MIT License. See the License section below.

---

## 日本語 — プロジェクト概要

このリポジトリは、Discordに投稿されたTwitter/Xリンクを検出し、FxTwitter/FxEmbedなどの公開APIから本文と翻訳を取得して返信するDiscord用ボットを提供します。返信には日本語・英語・中国語・韓国語の切替ボタンが付き、その場で翻訳を切り替えられます。

主な機能

- `twitter.com`、`x.com`、`fxtwitter.com`、`fixupx.com`、`vxtwitter.com` の投稿リンクを検出
- FxTwitter / FxEmbed APIを使って投稿本文と翻訳を取得
- 投稿言語がデフォルトの翻訳先と異なる場合に自動で翻訳
- 返信に言語切替ボタン（日本語 / English / 中文 / 한국어）を表示。元の言語と同じボタンは表示しません。
- 翻訳不要な投稿でも動画がある場合、`fxtwitter.com` などのメディアリンクを返信可能
- `/tweet_test`、`/translate_tweet`、`/set_default_lang`、`/set_ui_lang`、`/ping` などのスラッシュコマンドを提供
- Dockerfileが含まれており、Northflank などのコンテナホスティングにデプロイできます

対応言語

| コード | 言語 |
| ---: | :--- |
| `ja` | 日本語 |
| `en` | English |
| `zh` | 中文 |
| `ko` | 한국語 |

スラッシュコマンド

| コマンド | 説明 |
| --- | --- |
| `/ping` | BOTのWebSocketレイテンシとInteraction応答時間を表示 |
| `/tweet_test url:<URL>` | Twitter/Xリンクの検出・取得・翻訳可否を確認 |
| `/translate_tweet url:<URL> lang:<ja/en/zh/ko>` | 指定投稿を指定言語に翻訳 |
| `/set_default_lang lang:<ja/en/zh/ko>` | 自動翻訳のサーバー既定言語を変更（管理者向け） |
| `/set_ui_lang lang:<ja/en/zh/ko>` | BOTの案内表示言語を変更 |

注意事項

- `/set_default_lang` はサーバー管理者向けコマンドです。設定は `bot_config.json` に保存され、再起動後も維持されます。
- 返信の言語ボタンはBOTが動作している間は有効です。再起動後に古いボタンが反応しない場合はリンクを再投稿するか `/translate_tweet` をお使いください。

要件

- Python 3.11 以上
- Discord BOTトークン
- Discord Developer Portalで `MESSAGE CONTENT INTENT` を有効化
- BOT招待時に `bot` と `applications.commands` スコープを付与し、最低限の権限（チャンネル閲覧、メッセージ送信、メッセージ履歴を読む、スラッシュコマンド利用）を与える

Discord ボットのセットアップ（概要）

1. Discord Developer Portal（https://discord.com/developers/applications）でアプリケーションを作成
2. Botユーザーを作成し、トークンを控える
3. Privileged Gateway Intentsで `MESSAGE CONTENT INTENT` を有効にする
4. OAuth2のURLジェネレータで `bot` と `applications.commands` を選択して招待URLを作成し、サーバーに招待する

ローカル開発 / インストール

1. 仮想環境を作成して有効化:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

2. `.env` を `env_sample.txt` を参考に編集し、トークンや設定を入れる:

```env
DISCORD_TOKEN=your_discord_bot_token
TARGET_LANG=ja
BOT_CONFIG_PATH=bot_config.json
LOG_LEVEL=INFO
```

3. 開発中は `DISCORD_GUILD_ID` にテスト用サーバーIDを設定するとスラッシュコマンドの反映が速くなります。

起動方法

- 仮想環境が有効な場合:

```powershell
python -m src.bot
```

- 有効でない場合:

```powershell
.\.venv\Scripts\python.exe -m src.bot
```

ログに `Logged in as ...` が出力されれば起動成功です。

環境変数一覧

| 名前 | 必須 | 説明 |
| --- | ---: | :--- |
| `DISCORD_TOKEN` | 必須 | Discord ボットのトークン。機密扱い |
| `DISCORD_GUILD_ID` | 任意 | 開発用サーバーID（テスト用）。設定すると即時同期されます |
| `TARGET_LANG` | 任意 | 起動時の既定翻訳先（`ja`、`en`、`zh`、`ko`）。既定: `ja` |
| `BOT_CONFIG_PATH` | 任意 | `/set_default_lang` の保存先（既定: `bot_config.json`） |
| `FXTWITTER_API_BASE` | 任意 | FxTwitter/FxEmbed APIのベースURL（上書き時） |
| `REQUEST_TIMEOUT_SECONDS` | 任意 | APIリクエストのタイムアウト（秒） |
| `LOG_LEVEL` | 任意 | ログレベル（例: `INFO`, `DEBUG`） |

トークンの扱い（重要）

- `.env` や `bot_config.json` にトークンを含めた状態でコミットしないでください。このリポジトリはすでに `.gitignore` に登録しています。
- `DISCORD_TOKEN` は必ずホストやCIのシークレットマネージャに保存してください。
- コンテナホスティングを利用する場合は、プラットフォームのシークレット機能を使って環境変数を注入してください。
- トークンが漏えいしたと思われる場合は、Discord Developer Portalでただちにローテーション（再発行）してください。

