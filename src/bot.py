from __future__ import annotations

import logging
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

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
        canonical_language_code,
        extract_tweet_links,
        fetch_tweet_status,
        is_target_language,
        language_label,
        status_needs_translation,
        supported_language_codes,
    )
else:
    from .twitter_tools import (
        DEFAULT_FXTWITTER_API_BASE,
        TweetLink,
        TweetFetchError,
        TweetStatus,
        build_translation_message,
        build_video_link_message,
        canonical_language_code,
        extract_tweet_links,
        fetch_tweet_status,
        is_target_language,
        language_label,
        status_needs_translation,
        supported_language_codes,
    )


def _load_default_target_lang(config_path: Path, env_value: str) -> str:
    configured_value = env_value
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("default_target_lang"):
                configured_value = str(data["default_target_lang"])
        except Exception as exc:
            raise RuntimeError(f"Could not read bot config file: {config_path}") from exc

    try:
        return canonical_language_code(configured_value)
    except ValueError as exc:
        supported = ", ".join(supported_language_codes())
        raise RuntimeError(f"TARGET_LANG must be one of: {supported}") from exc


@dataclass(frozen=True)
class Settings:
    discord_token: str
    guild_id: int | None
    target_lang: str
    fxtwitter_api_base: str
    request_timeout_seconds: float
    log_level: str
    config_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise RuntimeError("DISCORD_TOKEN is not set. Copy .env.example to .env and set your bot token.")

        guild_id_raw = os.getenv("DISCORD_GUILD_ID", "").strip()
        guild_id = int(guild_id_raw) if guild_id_raw else None
        config_path = Path(os.getenv("BOT_CONFIG_PATH", "bot_config.json").strip() or "bot_config.json")

        return cls(
            discord_token=token,
            guild_id=guild_id,
            target_lang=_load_default_target_lang(config_path, os.getenv("TARGET_LANG", "ja")),
            fxtwitter_api_base=os.getenv("FXTWITTER_API_BASE", DEFAULT_FXTWITTER_API_BASE).strip()
            or DEFAULT_FXTWITTER_API_BASE,
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
            config_path=config_path,
        )


class TwitterTranslateBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.settings = settings
        self.default_target_lang = settings.target_lang
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

            if status_needs_translation(status, self.default_target_lang):
                response_text = build_translation_message(status, link.url, target_lang=self.default_target_lang)
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
                    view=TranslationLanguageView(self, link, selected_lang=self.default_target_lang),
                    mention_author=False,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                logging.info("Replied with %s for tweet %s.", response_kind, link.tweet_id)
            except discord.Forbidden:
                logging.warning("Could not reply in channel %s because the bot lacks permission.", message.channel.id)
            except discord.HTTPException:
                logging.exception("Discord rejected the reply for tweet %s.", link.tweet_id)

    async def fetch_tweet(self, link: TweetLink, target_lang: str | None = None) -> TweetStatus:
        if self.http_session is None:
            raise RuntimeError("HTTP session is not ready yet.")

        target = canonical_language_code(target_lang or self.default_target_lang)
        return await fetch_tweet_status(
            self.http_session,
            link.tweet_id,
            target_lang=target,
            api_base=self.settings.fxtwitter_api_base,
            timeout_seconds=self.settings.request_timeout_seconds,
        )

    def set_default_target_lang(self, target_lang: str) -> str:
        target = canonical_language_code(target_lang)
        self.default_target_lang = target
        self._save_runtime_config()
        return target

    def _save_runtime_config(self) -> None:
        payload = {"default_target_lang": self.default_target_lang}
        self.settings.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings.config_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


LANGUAGE_CHOICES = [
    app_commands.Choice(name=f"{language_label(code)} ({code})", value=code)
    for code in supported_language_codes()
]


class TranslationLanguageView(discord.ui.View):
    def __init__(
        self,
        bot: TwitterTranslateBot,
        link: TweetLink,
        *,
        selected_lang: str | None = None,
    ) -> None:
        super().__init__(timeout=900)
        self.bot = bot
        self.link = link
        selected = canonical_language_code(selected_lang) if selected_lang else None

        for lang in supported_language_codes():
            button = discord.ui.Button(
                label=language_label(lang),
                style=discord.ButtonStyle.primary if lang == selected else discord.ButtonStyle.secondary,
                custom_id=f"translate:{link.tweet_id}:{lang}",
            )
            button.callback = self._build_callback(lang)
            self.add_item(button)

    def _build_callback(self, target_lang: str):
        async def callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()

            try:
                status = await self.bot.fetch_tweet(self.link, target_lang)
            except TweetFetchError as exc:
                await interaction.followup.send(f"投稿を取得できませんでした: `{exc}`", ephemeral=True)
                return
            except Exception as exc:
                logging.exception("Unexpected error while translating tweet %s.", self.link.tweet_id)
                await interaction.followup.send(f"翻訳中にエラーが出ました: `{type(exc).__name__}`", ephemeral=True)
                return

            if status_needs_translation(status, target_lang):
                content = build_translation_message(status, self.link.url, target_lang=target_lang)
            elif status.has_video:
                content = build_video_link_message(self.link.url)
            else:
                await interaction.followup.send(
                    f"{language_label(target_lang)}への翻訳文を取得できませんでした。"
                    "投稿がすでに同じ言語か、翻訳APIから翻訳文が返っていません。",
                    ephemeral=True,
                )
                return

            if interaction.message is None:
                await interaction.followup.send(content, ephemeral=True)
                return

            await interaction.message.edit(
                content=content,
                view=TranslationLanguageView(self.bot, self.link, selected_lang=target_lang),
                allowed_mentions=discord.AllowedMentions.none(),
            )

        return callback


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

        if status_needs_translation(status, bot.default_target_lang):
            await interaction.followup.send(
                "取得と翻訳に成功しました。\n\n"
                + build_translation_message(status, link.url, target_lang=bot.default_target_lang),
                view=TranslationLanguageView(bot, link, selected_lang=bot.default_target_lang),
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
        if is_target_language(source_lang, bot.default_target_lang):
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

    @bot.tree.command(name="translate_tweet", description="Twitter/Xリンクを指定した言語へ翻訳します。")
    @app_commands.describe(url="翻訳したいTwitter/Xの投稿URL", lang="翻訳先の言語")
    @app_commands.choices(lang=LANGUAGE_CHOICES)
    async def translate_tweet(interaction: discord.Interaction, url: str, lang: str) -> None:
        await interaction.response.defer(thinking=True)

        links = extract_tweet_links(url)
        if not links:
            await interaction.followup.send(
                "Twitter/Xの投稿URLとして認識できませんでした。`https://x.com/user/status/123...` の形式で試してください。",
                ephemeral=True,
            )
            return

        target_lang = canonical_language_code(lang)
        link = links[0]
        try:
            status = await bot.fetch_tweet(link, target_lang)
        except TweetFetchError as exc:
            await interaction.followup.send(f"投稿を取得できませんでした: `{exc}`", ephemeral=True)
            return
        except Exception as exc:
            logging.exception("Unexpected error during /translate_tweet for %s.", link.tweet_id)
            await interaction.followup.send(f"翻訳中にエラーが出ました: `{type(exc).__name__}`", ephemeral=True)
            return

        if status_needs_translation(status, target_lang):
            await interaction.followup.send(
                build_translation_message(status, link.url, target_lang=target_lang),
                view=TranslationLanguageView(bot, link, selected_lang=target_lang),
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        if status.has_video:
            await interaction.followup.send(
                build_video_link_message(link.url),
                view=TranslationLanguageView(bot, link, selected_lang=target_lang),
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        await interaction.followup.send(
            f"{language_label(target_lang)}への翻訳文を取得できませんでした。"
            "投稿がすでに同じ言語か、翻訳APIから翻訳文が返っていません。",
            ephemeral=True,
        )

    @bot.tree.command(name="set_default_lang", description="自動翻訳のデフォルト言語を変更します。")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(lang="新しいデフォルト翻訳先")
    @app_commands.choices(lang=LANGUAGE_CHOICES)
    async def set_default_lang(interaction: discord.Interaction, lang: str) -> None:
        try:
            target_lang = bot.set_default_target_lang(lang)
        except Exception as exc:
            logging.exception("Could not update default language.")
            await interaction.response.send_message(
                f"デフォルト言語を保存できませんでした: `{type(exc).__name__}`",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"自動翻訳のデフォルト言語を {language_label(target_lang)} (`{target_lang}`) に変更しました。",
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
