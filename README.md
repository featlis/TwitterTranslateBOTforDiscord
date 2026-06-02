# Discord Twitter/X Translation Bot

## できること

- `twitter.com`、`x.com`、`fxtwitter.com`、`fixupx.com`、`vxtwitter.com` の投稿リンクを検出
- FxTwitter/FxEmbed APIから投稿本文と日本語訳を取得
- 日本語投稿はスキップし、日本語以外の投稿だけ翻訳を返信
- 日本語投稿でも動画付きの場合は `fxtwitter.com` リンクを返信
- `/ping` でWebSocket latencyとInteraction応答時間を表示

## セットアップ

1. Discord Developer PortalでアプリケーションとBOTを作成する。
2. BOT設定で `MESSAGE CONTENT INTENT` を有効化する。
3. OAuth2 URL Generatorで `bot` と `applications.commands` を選び、BOTをサーバーへ招待する。
4. このフォルダで仮想環境を作り、依存関係を入れる。

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

5. `.env.example` を `.env` にコピーして、`DISCORD_TOKEN` を設定する。

```powershell
Copy-Item .env.example .env
```

`DISCORD_GUILD_ID` に開発用サーバーIDを入れると、`/ping` がすぐ同期される。
空欄の場合はグローバル同期になり、Discord側の反映に時間がかかることがある。

## 起動

```powershell
python -m src.bot
```

## 無料ホスティング案: Northflank Sandbox

Northflank Sandboxでコンテナとして動かす。
`Always-on-compute`、`2× free services` 

1. GitHubにこのBOTのリポジトリを作成して、このフォルダの中身をpush。
2. Northflankで `Create service` を選択。
3. GitHubリポジトリを接続する。
4. Build methodは `Dockerfile` を選ぶ。
5. Start commandは空欄でOK。Dockerfileの `CMD ["python", "-m", "src.bot"]` が使われる。
7. Environment variablesに `.env` と同じ値を登録（トークン）

最低限必要な環境変数:

```env
DISCORD_TOKEN=あなたのBOTトークン
TARGET_LANG=ja
LOG_LEVEL=INFO
```

デプロイ後、Northflankのログに `Logged in as ...` が出ればOK。

## 環境変数

| 名前 | 必須 | 説明 |
| --- | --- | --- |
| `DISCORD_TOKEN` | はい | Discord BOTトークン |
| `DISCORD_GUILD_ID` | いいえ | 開発用サーバーID。設定すると slash command をそのサーバーへ即時同期 |
| `TARGET_LANG` | いいえ | 翻訳先。既定値は `ja` |
| `FXTWITTER_API_BASE` | いいえ | FxTwitter/FxEmbed APIのURL |
| `REQUEST_TIMEOUT_SECONDS` | いいえ | APIリクエストのタイムアウト秒数 |
| `LOG_LEVEL` | いいえ | `INFO`、`DEBUG` など |

## 注意

- BOTが通常メッセージを読むには、Discord Developer Portal側の `MESSAGE CONTENT INTENT` と、サーバー内の閲覧・送信権限が必要。
- 投稿本文と翻訳の取得には公開の FxTwitter/FxEmbed API を使っています。API側の仕様変更やレート制限がある場合はログに警告。
- 参照: [FxEmbed API - Get status](https://docs.fxembed.com/api/twitter/operations/2statusid/)
