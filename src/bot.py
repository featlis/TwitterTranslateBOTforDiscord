from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

if __package__ in {None, ""}:
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from src.twitter_tools import (  # type: ignore[no-redef]
        DEFAULT_FXTWITTER_API_BASE,
        TweetLink,
        TweetFetchError,
        TweetStatus,
        build_translation_message,
        build_video_link_message,
        extract_tweet_links,
        fetch_tweet_status,
        status_needs_translation,
    )
else:
    from .twitter_tools import (
        DEFAULT_FXTWITTER_API_BASE,
        TweetLink,
        TweetFetchError,
        TweetStatus,
        build_translation_message,
        build_video_link_message,
        extract_tweet_links,
        fetch_tweet_status,
        status_needs_translation,
    )


@dataclass(frozen=True)
class Settings:
    discord_token: str
    guild_id: int | None
    target_lang: str
    fxtwitter_api_base: str
    request_timeout_seconds: float
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise RuntimeError("DISCORD_TOKEN is not set. Copy .env.example to .env and set your bot token.")

        guild_id_raw = os.getenv("DISCORD_GUILD_ID", "").strip()
        guild_id = int(guild_id_raw) if guild_id_raw else None

        return cls(
            discord_token=token,
            guild_id=guild_id,
            target_lang=os.getenv("TARGET_LANG", "ja").strip() or "ja",
            fxtwitter_api_base=os.getenv("FXTWITTER_API_BASE", DEFAULT_FXTWITTER_API_BASE).strip()
            or DEFAULT_FXTWITTER_API_BASE,
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
        )


class TwitterTranslateBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.settings = settings
        self.http_session: aiohttp.ClientSession | None = None
        self._commands_synced_to_joined_guilds = False

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession()
        register_commands(self)

        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logging.info("Synced slash commands to guild %s.", self.settings.guild_id)
        else:
            await self.tree.sync()
            logging.info("Synced slash commands globally.")

    async def close(self) -> None:
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
        await super().close()

    async def on_ready(self) -> None:
        logging.info("Logged in as %s (ID: %s).", self.user, self.user.id if self.user else "unknown")
        if self.settings.guild_id or self._commands_synced_to_joined_guilds:
            return

        self._commands_synced_to_joined_guilds = True
        for guild in self.guilds:
            discord_guild = discord.Object(id=guild.id)
            self.tree.copy_global_to(guild=discord_guild)
            await self.tree.sync(guild=discord_guild)
            logging.info("Synced slash commands to joined guild %s (%s).", guild.name, guild.id)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        content = "\n".join(_message_text_candidates(message))
        if not content.strip():
            logging.debug(
                "Received a message with empty content in channel %s. "
                "If this was a normal message, check the MESSAGE CONTENT INTENT setting.",
                getattr(message.channel, "id", "unknown"),
            )
            return

        links = extract_tweet_links(content)
        if not links:
            logging.debug("No Twitter/X status links detected in message %s.", message.id)
            return

        logging.info("Received message %s with %s Twitter/X status link(s).", message.id, len(links))

        if self.http_session is None:
            logging.warning("HTTP session is not ready yet.")
            return

        for link in links:
            logging.info("Detected Twitter/X status link: tweet_id=%s url=%s", link.tweet_id, link.url)
            try:
                status = await self.fetch_tweet(link)
            except TweetFetchError as exc:
                logging.warning("Could not fetch tweet %s: %s", link.tweet_id, exc)
                continue
            except Exception:
                logging.exception("Unexpected error while fetching tweet %s.", link.tweet_id)
                continue

            response_text: str | None = None
            response_kind = "translation"

            if status_needs_translation(status, self.settings.target_lang):
                response_text = build_translation_message(status, link.url, target_lang=self.settings.target_lang)
            elif status.has_video:
                response_text = build_video_link_message(link.url)
                response_kind = "video link"
            else:
                logging.info(
                    "Skipped tweet %s. source_lang=%s translation_present=%s text_present=%s has_video=%s",
                    link.tweet_id,
                    status.source_lang or status.translation_source_lang,
                    bool(status.translation_text),
                    bool(status.text),
                    status.has_video,
                )
                continue

            try:
                await message.reply(
                    response_text,
                    mention_author=False,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                logging.info("Replied with %s for tweet %s.", response_kind, link.tweet_id)
            except discord.Forbidden:
                logging.warning("Could not reply in channel %s because the bot lacks permission.", message.channel.id)
            except discord.HTTPException:
                logging.exception("Discord rejected the reply for tweet %s.", link.tweet_id)

    async def fetch_tweet(self, link: TweetLink) -> TweetStatus:
        if self.http_session is None:
            raise RuntimeError("HTTP session is not ready yet.")

        return await fetch_tweet_status(
            self.http_session,
            link.tweet_id,
            target_lang=self.settings.target_lang,
            api_base=self.settings.fxtwitter_api_base,
            timeout_seconds=self.settings.request_timeout_seconds,
        )


def register_commands(bot: TwitterTranslateBot) -> None:
    @bot.tree.command(name="ping", description="BOTの応答速度を測定します。")
    async def ping(interaction: discord.Interaction) -> None:
        started_at = time.perf_counter()
        await interaction.response.defer(ephemeral=True, thinking=True)
        interaction_ms = round((time.perf_counter() - started_at) * 1000)
        websocket_ms = round(bot.latency * 1000)

        await interaction.followup.send(
            f"Pong! WebSocket: `{websocket_ms}ms` / Interaction: `{interaction_ms}ms`",
            ephemeral=True,
        )

    @bot.tree.command(name="tweet_test", description="Twitter/Xリンクの翻訳取得をテストします。")
    @app_commands.describe(url="確認したいTwitter/Xの投稿URL")
    async def tweet_test(interaction: discord.Interaction, url: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        links = extract_tweet_links(url)
        if not links:
            await interaction.followup.send(
                "Twitter/Xの投稿URLとして認識できませんでした。`https://x.com/user/status/123...` の形式で試してください。",
                ephemeral=True,
            )
            return

        link = links[0]
        try:
            status = await bot.fetch_tweet(link)
        except TweetFetchError as exc:
            await interaction.followup.send(f"投稿を取得できませんでした: `{exc}`", ephemeral=True)
            return
        except Exception as exc:
            logging.exception("Unexpected error during /tweet_test for %s.", link.tweet_id)
            await interaction.followup.send(f"確認中にエラーが出ました: `{type(exc).__name__}`", ephemeral=True)
            return

        source_lang = status.source_lang or status.translation_source_lang or "unknown"
        has_translation = bool(status.translation_text)

        if status_needs_translation(status, bot.settings.target_lang):
            await interaction.followup.send(
                "取得と翻訳に成功しました。\n\n"
                + build_translation_message(status, link.url, target_lang=bot.settings.target_lang),
                ephemeral=True,
            )
            return

        if status.has_video:
            await interaction.followup.send(
                "投稿は翻訳対象ではありませんが、動画付きなので通常投稿ではFxTwitterリンクを返信します。\n\n"
                + build_video_link_message(link.url),
                ephemeral=True,
            )
            return

        reason = "翻訳文がAPIから返っていません。"
        if source_lang.split("-", 1)[0] == bot.settings.target_lang:
            reason = "投稿が翻訳先の言語として判定されたためスキップされます。"

        await interaction.followup.send(
            "\n".join(
                [
                    "投稿は取得できましたが、通常投稿では返信しません。",
                    f"理由: {reason}",
                    f"tweet_id: `{status.tweet_id}`",
                    f"source_lang: `{source_lang}`",
                    f"translation_present: `{has_translation}`",
                ]
            ),
            ephemeral=True,
        )


def _message_text_candidates(message: discord.Message) -> list[str]:
    parts: list[str] = []
    if message.content:
        parts.append(message.content)

    for embed in message.embeds:
        for value in (embed.url, embed.title, embed.description):
            if value:
                parts.append(value)

    return parts


def main() -> None:
    load_dotenv()
    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    bot = TwitterTranslateBot(settings)
    bot.run(settings.discord_token)


if __name__ == "__main__":
    main()
