# Discord Twitter/X Translation Bot

## トラブルシュート: `/ping` は動くがリンクに反応しない

まずBOTを再起動して、`/tweet_test` にTwitter/XのURLを渡してください。
このコマンドで、リンク認識、投稿取得、翻訳有無、スキップ理由を確認できます。

- `/tweet_test` は成功するのに生リンクだけ無反応な場合、ほぼ通常メッセージ本文の取得設定が原因です。
- Discord Developer Portalの `Bot` 画面で `MESSAGE CONTENT INTENT` が有効か確認してください。
- BOTを再起動してください。Intent設定は起動中のBOTには反映されません。
- BOTのチャンネル権限に `チャンネルを見る`、`メッセージを送信`、`メッセージ履歴を読む` があるか確認してください。
- `@BOT名 https://x.com/user/status/123...` のようにBOTをメンションして試してください。メンションありだけ反応する場合は、Message Content IntentがDiscord側で有効になっていません。
- 日本語投稿、非公開投稿、削除済み投稿、翻訳APIから翻訳文が返らない投稿は返信しません。
- 原因調査中は `.env` の `LOG_LEVEL=DEBUG` にすると、ターミナルにリンク検出状況が出ます。

DiscordにTwitter/Xリンクが投稿されたとき、投稿本文が日本語以外なら日本語訳を返信するBOTです。
スラッシュコマンド `/ping` でBOTの応答速度も確認できます。

## できること

- `twitter.com`、`x.com`、`fxtwitter.com`、`fixupx.com`、`vxtwitter.com` の投稿リンクを検出
- FxTwitter/FxEmbed APIから投稿本文と日本語訳を取得
- 日本語投稿はスキップし、日本語以外の投稿だけ翻訳を返信
- 日本語投稿でも動画付きの場合は `fxtwitter.com` リンクを返信
- `/ping` でWebSocket latencyとInteraction応答時間を表示

## セットアップ

1. Discord Developer PortalでアプリケーションとBOTを作成します。
2. BOT設定で `MESSAGE CONTENT INTENT` を有効にします。
3. OAuth2 URL Generatorで `bot` と `applications.commands` を選び、BOTをサーバーへ招待します。
4. このフォルダで仮想環境を作り、依存関係を入れます。

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

5. `.env.example` を `.env` にコピーして、`DISCORD_TOKEN` を設定します。

```powershell
Copy-Item .env.example .env
```

`DISCORD_GUILD_ID` に開発用サーバーIDを入れると、`/ping` がすぐ同期されます。
空欄の場合はグローバル同期になり、Discord側の反映に時間がかかることがあります。

## 起動

```powershell
python -m src.bot
```

## 無料ホスティング案: Northflank Sandbox

Oracle Cloudが使えない場合は、Northflank Sandboxでコンテナとして動かす方法があります。
NorthflankのPricingページではSandboxに `Always-on-compute`、`2× free services` があると案内されています。

1. GitHubにこのBOTのリポジトリを作成して、このフォルダの中身をpushします。
2. Northflankで `Create service` を選びます。
3. GitHubリポジトリを接続します。
4. Build methodは `Dockerfile` を選びます。
5. Start commandは空欄でOKです。Dockerfileの `CMD ["python", "-m", "src.bot"]` が使われます。
6. Environment variablesに `.env` と同じ値を登録します。

最低限必要な環境変数:

```env
DISCORD_TOKEN=あなたのBOTトークン
TARGET_LANG=ja
LOG_LEVEL=INFO
```

デプロイ後、Northflankのログに `Logged in as ...` が出れば起動成功です。

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

- BOTが通常メッセージを読むには、Discord Developer Portal側の `MESSAGE CONTENT INTENT` と、サーバー内の閲覧・送信権限が必要です。
- 投稿本文と翻訳の取得には公開の FxTwitter/FxEmbed API を使っています。API側の仕様変更やレート制限がある場合はログに警告が出ます。
- 参照: [FxEmbed API - Get status](https://docs.fxembed.com/api/twitter/operations/2statusid/)
