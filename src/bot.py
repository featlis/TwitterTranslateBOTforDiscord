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
        LANGUAGE_OPTIONS,
        get_ui_message,
        UI_MESSAGES,
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
        LANGUAGE_OPTIONS,
        get_ui_message,
        UI_MESSAGES,
        is_target_language,
        language_label,
        status_needs_translation,
        supported_language_codes,
    )


def _load_config_lang(config_path: Path, key: str, env_value: str) -> str:
    configured_value = env_value
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get(key):
                configured_value = str(data[key])
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
    ui_lang: str
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
            target_lang=_load_config_lang(config_path, "default_target_lang", os.getenv("TARGET_LANG", "ja")),
            ui_lang=_load_config_lang(config_path, "ui_lang", os.getenv("UI_LANG", "ja")),
            fxtwitter_api_base=os.getenv("FXTWITTER_API_BASE", DEFAULT_FXTWITTER_API_BASE).strip()
            or DEFAULT_FXTWITTER_API_BASE,
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
            config_path=config_path,
        )


class DiscordTranslator(app_commands.Translator):
    """Discordのクライアント言語に合わせてコマンドの説明文などを翻訳するクラス"""
    async def translate(
        self,
        string: app_commands.locale_str,
        locale: discord.Locale,
        context: app_commands.TranslationContext
    ) -> str | None:
        # ロケールから先頭の言語コードを取得 (en-US -> en)
        lang_key = locale.value.split('-')[0]

        # 指定の4か国語（ja, zh, ko, en）に含まれない場合は英語(en)に倒す
        if lang_key not in UI_MESSAGES:
            lang_key = "en"

        key = string.message

        # コマンドの説明文(_desc)と言語選択肢(lang_name_)のみを翻訳対象とする。
        # これにより、コマンド名(ping, help等)がUI_MESSAGES内の応答メッセージと衝突して
        # 長さ制限エラー(HTTP 400 50035)を起こすのを防ぐ。
        if not (key.endswith("_desc") or key.startswith("lang_name_")):
            return None

        # 指定した言語の辞書にキーがない場合は、英語の辞書から取得を試みる
        translated = UI_MESSAGES[lang_key].get(key) or UI_MESSAGES["en"].get(key)

        # キーが辞書に存在し、かつ言語選択肢（lang_name_xx）の場合は "(code)" を付与
        if translated is not None and key.startswith("lang_name_"):
            # 言語選択肢の場合、"日本語 (ja)" の形式にする
            code = key.split("_")[-1]
            return f"{translated} ({code})"

        return translated


class TwitterTranslateBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.settings = settings
        self.default_target_lang = settings.target_lang
        self.ui_lang = settings.ui_lang
        self.http_session: aiohttp.ClientSession | None = None
        self._commands_synced_to_joined_guilds = False

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession()
        # 翻訳クラスを登録
        await self.tree.set_translator(DiscordTranslator())

        register_commands(self)

        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logging.info("Successfully synced slash commands to guild %s.", self.settings.guild_id)
        else:
            await self.tree.sync()
            logging.info("Successfully synced slash commands globally.")

    async def close(self) -> None:
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
        await super().close()

    async def on_ready(self) -> None:
        logging.info("Logged in as %s (ID: %s).", self.user, self.user.id if self.user else "unknown")

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
                response_text = build_translation_message(
                    status,
                    link.url,
                    target_lang=self.default_target_lang,
                    ui_lang=self.ui_lang,
                )
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
        
    def set_ui_lang(self, ui_lang: str) -> str:
        target = canonical_language_code(ui_lang)
        self.ui_lang = target
        self._save_runtime_config()
        return target

    def _save_runtime_config(self) -> None:
        payload = {
            "default_target_lang": self.default_target_lang,
            "ui_lang": self.ui_lang,
        }
        self.settings.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings.config_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


class TranslationLanguageView(discord.ui.View):
    def __init__(
        self,
        bot: TwitterTranslateBot,
        link: TweetLink,
        *,
        selected_lang: str | None = None,
    ) -> None:
        super().__init__(timeout=None)
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
                await interaction.followup.send(
                    get_ui_message("fetch_error", ui_lang=self.bot.ui_lang, exc=exc),
                    ephemeral=True,
                )
                return
            except Exception as exc:
                logging.exception("Unexpected error while translating tweet %s.", self.link.tweet_id)
                await interaction.followup.send(
                    get_ui_message(
                        "unexpected_error", ui_lang=self.bot.ui_lang, type=type(exc).__name__
                    ),
                    ephemeral=True,
                )
                return

            if status_needs_translation(status, target_lang):
                content = build_translation_message(
                    status, self.link.url, target_lang=target_lang, ui_lang=self.bot.ui_lang
                )
            elif status.has_video:
                content = build_video_link_message(self.link.url)
            else:
                await interaction.followup.send(
                    get_ui_message(
                        "no_translation",
                        ui_lang=self.bot.ui_lang,
                        lang=language_label(target_lang),
                    ),
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
    def get_interaction_lang(interaction: discord.Interaction) -> str:
        """ユーザーのクライアント言語を判定して、対応していればそのコードを、そうでなければBOTのデフォルトUI言語を返します。"""
        user_lang = interaction.locale.value.split('-')[0]
        return user_lang if user_lang in ["ja", "zh", "ko"] else "en"

    # 翻訳用キーを使用した選択肢の作成
    localized_choices = [
        app_commands.Choice(name=app_commands.locale_str(f"lang_name_{code}"), value=code)
        for code in supported_language_codes()
    ]

    @bot.tree.command(
        name="help",
        description=app_commands.locale_str("help_desc"),
    )
    async def help_command(interaction: discord.Interaction) -> None:
        lang = get_interaction_lang(interaction)
        embed = discord.Embed(
            title=get_ui_message("help_title", ui_lang=lang),
            description=get_ui_message("help_body", ui_lang=lang).replace("\\n", "\n"),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(
        name="ping",
        description=app_commands.locale_str("ping_desc"),
    )
    async def ping(interaction: discord.Interaction) -> None:
        lang = get_interaction_lang(interaction)
        started_at = time.perf_counter()
        await interaction.response.defer(ephemeral=True, thinking=True)
        interaction_ms = round((time.perf_counter() - started_at) * 1000)
        websocket_ms = round(bot.latency * 1000)

        await interaction.followup.send(
            get_ui_message(
                "ping",
                ui_lang=lang,
                websocket_ms=websocket_ms,
                interaction_ms=interaction_ms,
            ),
            ephemeral=True,
        )

    @bot.tree.command(
        name="translate_tweet",
        description=app_commands.locale_str("translate_tweet_desc"),
    )
    @app_commands.describe(
        url=app_commands.locale_str("url_param_desc"),
        lang=app_commands.locale_str("lang_param_desc")
    )
    @app_commands.choices(lang=localized_choices)
    async def translate_tweet(interaction: discord.Interaction, url: str, lang: str) -> None:
        ui_lang = get_interaction_lang(interaction)
        await interaction.response.defer(thinking=True)

        links = extract_tweet_links(url)
        if not links:
            await interaction.followup.send(
                get_ui_message("invalid_url", ui_lang=ui_lang),
                ephemeral=True,
            )
            return

        target_lang = canonical_language_code(lang)
        link = links[0]
        try:
            status = await bot.fetch_tweet(link, target_lang)
        except TweetFetchError as exc:
            await interaction.followup.send(
                get_ui_message("fetch_error", ui_lang=ui_lang, exc=exc),
                ephemeral=True,
            )
            return
        except Exception as exc:
            logging.exception("Unexpected error during /translate_tweet for %s.", link.tweet_id)
            await interaction.followup.send(
                get_ui_message(
                    "unexpected_error", ui_lang=ui_lang, type=type(exc).__name__
                ),
                ephemeral=True,
            )
            return

        if status_needs_translation(status, target_lang):
            await interaction.followup.send(
                build_translation_message(status, link.url, target_lang=target_lang, ui_lang=ui_lang),
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
            get_ui_message(
                "no_translation",
                ui_lang=ui_lang,
                lang=language_label(target_lang),
            ),
            ephemeral=True,
        )

    @bot.tree.command(
        name="set_default_lang",
        description=app_commands.locale_str("set_default_lang_desc"),
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(lang=app_commands.locale_str("lang_param_desc"))
    @app_commands.choices(lang=localized_choices)
    async def set_default_lang(interaction: discord.Interaction, lang: str) -> None:
        ui_lang = get_interaction_lang(interaction)
        try:
            target_lang = bot.set_default_target_lang(lang)
        except Exception as exc:
            logging.exception("Could not update default language.")
            await interaction.response.send_message(
                get_ui_message(
                    "config_save_error", ui_lang=ui_lang, type=type(exc).__name__
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            get_ui_message(
                "set_default_lang",
                ui_lang=ui_lang,
                label=language_label(target_lang),
                code=target_lang,
            ),
            ephemeral=True,
        )

    @bot.tree.command(
        name="set_ui_lang",
        description=app_commands.locale_str("set_ui_lang_desc"),
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(lang=app_commands.locale_str("lang_param_desc"))
    @app_commands.choices(lang=localized_choices)
    async def set_ui_lang(interaction: discord.Interaction, lang: str) -> None:
        current_ui_lang = get_interaction_lang(interaction)
        try:
            target_lang = bot.set_ui_lang(lang)
        except Exception as exc:
            logging.exception("Could not update UI language.")
            await interaction.response.send_message(
                get_ui_message(
                    "config_save_error", ui_lang=current_ui_lang, type=type(exc).__name__
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            get_ui_message(
                "set_ui_lang",
                ui_lang=target_lang,
                label=language_label(target_lang),
                code=target_lang,
            ),
            ephemeral=False,
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
