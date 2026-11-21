import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from src.bot import (
    DiscordTranslator,
    Settings,
    TranslationLanguageButton,
    TranslationLanguageView,
    TwitterTranslateBot,
    register_commands,
)
from src.twitter_tools import TweetFetchError, TweetLink, TweetStatus


def _make_settings(config_path: Path, **overrides) -> Settings:
    data = {
        "discord_token": "dummy-token",
        "guild_id": None,
        "target_lang": "ja",
        "ui_lang": "ja",
        "fxtwitter_api_base": "https://api.fxtwitter.com/2/status",
        "request_timeout_seconds": 10.0,
        "log_level": "INFO",
        "config_path": config_path,
    }
    data.update(overrides)
    return Settings(**data)


class SettingsTest(unittest.TestCase):
    def test_from_env_handles_empty_optional_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = Path(tmpdir) / "missing.json"
            env = {
                "DISCORD_TOKEN": "token-123",
                "DISCORD_GUILD_ID": "",
                "TARGET_LANG": "  ",
                "UI_LANG": "",
                "REQUEST_TIMEOUT_SECONDS": "",
                "BOT_CONFIG_PATH": str(cfg),
            }
            with patch.dict(os.environ, env, clear=True):
                settings = Settings.from_env()

        self.assertEqual(settings.target_lang, "ja")
        self.assertEqual(settings.ui_lang, "ja")
        self.assertEqual(settings.request_timeout_seconds, 10.0)
        self.assertIsNone(settings.guild_id)

    def test_from_env_rejects_non_positive_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "DISCORD_TOKEN": "token-123",
                "REQUEST_TIMEOUT_SECONDS": "0",
                "BOT_CONFIG_PATH": str(Path(tmpdir) / "missing.json"),
            }
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaises(RuntimeError):
                    Settings.from_env()


class BotBehaviorTest(unittest.IsolatedAsyncioTestCase):
    async def test_config_save_failure_does_not_mutate_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bot = TwitterTranslateBot(_make_settings(Path(tmpdir) / "bot_config.json"))
            with patch.object(bot, "_save_runtime_config", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    bot.set_default_target_lang("en")
                with self.assertRaises(OSError):
                    bot.set_ui_lang("ko")

            self.assertEqual(bot.default_target_lang, "ja")
            self.assertEqual(bot.ui_lang, "ja")

    async def test_config_save_persists_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = Path(tmpdir) / "bot_config.json"
            bot = TwitterTranslateBot(_make_settings(cfg))
            bot.set_default_target_lang("en")
            bot.set_ui_lang("ko")

            saved = json.loads(cfg.read_text(encoding="utf-8"))
            self.assertEqual(saved, {"default_target_lang": "en", "ui_lang": "ko"})

    async def test_translator_uses_human_readable_defaults_and_localizations(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bot = TwitterTranslateBot(_make_settings(Path(tmpdir) / "bot_config.json"))
            await bot.tree.set_translator(DiscordTranslator())
            register_commands(bot)

            cmd = bot.tree.get_command("translate_tweet")
            self.assertIsNotNone(cmd)
            payload = await cmd.get_translated_payload(bot.tree, bot.tree.translator)
            self.assertNotEqual(payload["description"], "translate_tweet_desc")
            self.assertEqual(
                payload["description_localizations"]["ja"],
                "Twitter/Xリンクを指定した言語へ翻訳します。",
            )
            lang_opt = next(opt for opt in payload["options"] if opt["name"] == "lang")
            ja_choice = next(ch for ch in lang_opt["choices"] if ch["value"] == "ja")
            self.assertEqual(ja_choice["name"], "Japanese (ja)")
            self.assertEqual(ja_choice["name_localizations"]["ja"], "日本語 (ja)")

    async def test_admin_commands_are_guild_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bot = TwitterTranslateBot(_make_settings(Path(tmpdir) / "bot_config.json"))
            register_commands(bot)

            for name in ("set_default_lang", "set_ui_lang"):
                cmd = bot.tree.get_command(name)
                self.assertIsNotNone(cmd)
                self.assertTrue(cmd.guild_only, f"/{name} must be guild_only")

    async def test_ping_handles_nan_latency(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bot = TwitterTranslateBot(_make_settings(Path(tmpdir) / "bot_config.json", ui_lang="ko"))
            register_commands(bot)
            ping_cmd = bot.tree.get_command("ping")

            interaction = MagicMock()
            interaction.locale = discord.Locale.french  # unsupported -> should fall back to bot.ui_lang ("ko")
            interaction.response.defer = AsyncMock()
            interaction.followup.send = AsyncMock()

            with patch.object(TwitterTranslateBot, "latency", new=float("nan")):
                await ping_cmd.callback(interaction)

            interaction.followup.send.assert_awaited_once()
            args, kwargs = interaction.followup.send.call_args
            self.assertIn("`?ms`", args[0])
            self.assertTrue(kwargs["ephemeral"])
            self.assertIsNotNone(kwargs["allowed_mentions"])

    async def test_translate_tweet_video_does_not_pass_view_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bot = TwitterTranslateBot(_make_settings(Path(tmpdir) / "bot_config.json"))
            register_commands(bot)
            cmd = bot.tree.get_command("translate_tweet")

            bot.fetch_tweet = AsyncMock(
                return_value=TweetStatus(
                    tweet_id="12345",
                    text="こんにちは",
                    source_lang="ja",
                    author_handle="author_handle",
                    has_video=True,
                )
            )

            interaction = MagicMock()
            interaction.locale = discord.Locale.japanese
            interaction.response.defer = AsyncMock()
            interaction.followup.send = AsyncMock()

            await cmd.callback(interaction, "https://x.com/i/status/12345", "ja")

            interaction.followup.send.assert_awaited_once()
            args, kwargs = interaction.followup.send.call_args
            self.assertEqual(args[0], "https://fxtwitter.com/author_handle/status/12345")
            self.assertNotIn("view", kwargs)
            self.assertIsNotNone(kwargs["allowed_mentions"])

    async def test_translate_tweet_invalid_url_replies_ephemeral_without_defer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bot = TwitterTranslateBot(_make_settings(Path(tmpdir) / "bot_config.json"))
            register_commands(bot)
            cmd = bot.tree.get_command("translate_tweet")

            interaction = MagicMock()
            interaction.locale = discord.Locale.american_english
            interaction.response.defer = AsyncMock()
            interaction.response.send_message = AsyncMock()

            await cmd.callback(interaction, "not-a-url", "ja")

            interaction.response.defer.assert_not_awaited()
            interaction.response.send_message.assert_awaited_once()
            _, kwargs = interaction.response.send_message.call_args
            self.assertTrue(kwargs["ephemeral"])
            self.assertIsNotNone(kwargs["allowed_mentions"])

    async def test_translate_tweet_fetch_error_deletes_public_defer_and_sends_ephemeral(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bot = TwitterTranslateBot(_make_settings(Path(tmpdir) / "bot_config.json"))
            register_commands(bot)
            cmd = bot.tree.get_command("translate_tweet")
            bot.fetch_tweet = AsyncMock(side_effect=TweetFetchError("boom"))

            interaction = MagicMock()
            interaction.locale = discord.Locale.japanese
            interaction.response.defer = AsyncMock()
            interaction.delete_original_response = AsyncMock()
            interaction.followup.send = AsyncMock()

            await cmd.callback(interaction, "https://x.com/user/status/12345", "ja")

            interaction.delete_original_response.assert_awaited_once()
            interaction.followup.send.assert_awaited_once()
            _, kwargs = interaction.followup.send.call_args
            self.assertTrue(kwargs["ephemeral"])
            self.assertIsNotNone(kwargs["allowed_mentions"])

    async def test_on_message_uses_author_handle_fallback_for_i_status_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bot = TwitterTranslateBot(_make_settings(Path(tmpdir) / "bot_config.json"))
            bot.http_session = SimpleNamespace(closed=False)
            bot.fetch_tweet = AsyncMock(
                return_value=TweetStatus(
                    tweet_id="98765",
                    text="Video post",
                    source_lang="ja",
                    author_handle="realuser",
                    has_video=True,
                )
            )

            message = MagicMock()
            message.id = 1
            message.author.bot = False
            message.content = "https://x.com/i/web/status/98765"
            message.embeds = []
            message.reply = AsyncMock()

            await bot.on_message(message)

            message.reply.assert_awaited_once()
            args, kwargs = message.reply.call_args
            self.assertEqual(args[0], "https://fxtwitter.com/realuser/status/98765")
            self.assertIsNone(kwargs["view"])

    async def test_dynamic_translation_button_keeps_view_on_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bot = TwitterTranslateBot(_make_settings(Path(tmpdir) / "bot_config.json"))
            bot.fetch_tweet = AsyncMock(
                return_value=TweetStatus(
                    tweet_id="555",
                    text="Hello",
                    source_lang="en",
                    author_handle="alice",
                    translation_text=None,
                )
            )

            match = re.fullmatch(TranslationLanguageButton.__discord_ui_compiled_template__, "translate:555:ja")
            self.assertIsNotNone(match)

            interaction = MagicMock()
            interaction.client = bot
            interaction.message = SimpleNamespace(content="https://fxtwitter.com/alice/status/555")
            interaction.response.defer = AsyncMock()
            interaction.edit_original_response = AsyncMock()

            button = await TranslationLanguageButton.from_custom_id(interaction, MagicMock(), match)
            await button.callback(interaction)

            interaction.edit_original_response.assert_awaited_once()
            _, kwargs = interaction.edit_original_response.call_args
            self.assertEqual(kwargs["content"], "https://fxtwitter.com/alice/status/555")
            self.assertIsInstance(kwargs["view"], TranslationLanguageView)
            custom_ids = [item.custom_id for item in kwargs["view"].children]
            self.assertNotIn("translate:555:en", custom_ids)
            self.assertIn("translate:555:ja", custom_ids)
            self.assertIsNotNone(kwargs["allowed_mentions"])

    async def test_fetch_tweet_caches_translated_results_and_skips_caching_failed_translations(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bot = TwitterTranslateBot(
                _make_settings(Path(tmpdir) / "bot_config.json", deepl_api_key="key:fx")
            )
            bot.http_session = SimpleNamespace(closed=False)
            link = TweetLink(tweet_id="777", url="https://x.com/u/status/777", handle="u")

            failed_status = TweetStatus(tweet_id="777", text="Hello", source_lang="en", translation_text=None)
            ok_status = TweetStatus(tweet_id="777", text="Hello", source_lang="en", translation_text="こんにちは")

            with patch(
                "src.bot.fetch_tweet_status",
                new=AsyncMock(side_effect=[failed_status, ok_status]),
            ) as fetch_mock:
                first = await bot.fetch_tweet(link, "ja")
                self.assertIsNone(first.translation_text)
                second = await bot.fetch_tweet(link, "ja")
                self.assertEqual(second.translation_text, "こんにちは")
                third = await bot.fetch_tweet(link, "ja")
                self.assertEqual(third.translation_text, "こんにちは")

            self.assertEqual(fetch_mock.await_count, 2)
            self.assertEqual(fetch_mock.call_args.kwargs["deepl_api_key"], "key:fx")


if __name__ == "__main__":
    unittest.main()
