import unittest
from unittest.mock import MagicMock

import aiohttp

from src.twitter_tools import (
    TweetFetchError,
    TweetStatus,
    _truncate,
    build_translation_message,
    build_video_link_message,
    canonical_language_code,
    extract_tweet_links,
    fetch_tweet_status,
    get_ui_message,
    normalize_lang_code,
    payload_has_video_media,
    parse_tweet_status,
    status_needs_translation,
    to_api_language_code,
    to_fxtwitter_url,
)


class TwitterToolsTest(unittest.TestCase):
    def test_extract_tweet_links_supports_x_and_twitter_domains(self) -> None:
        links = extract_tweet_links(
            "x https://x.com/example/status/12345?s=20 and https://twitter.com/example/status/67890"
        )

        self.assertEqual([link.tweet_id for link in links], ["12345", "67890"])
        self.assertEqual(links[0].handle, "example")

    def test_extract_tweet_links_deduplicates_by_tweet_id(self) -> None:
        links = extract_tweet_links(
            "https://x.com/a/status/123 https://twitter.com/b/status/123?ref=test"
        )

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].tweet_id, "123")

    def test_to_fxtwitter_url_normalizes_twitter_domains(self) -> None:
        self.assertEqual(
            to_fxtwitter_url("https://x.com/example/status/12345?s=20"),
            "https://fxtwitter.com/example/status/12345",
        )
        self.assertEqual(
            to_fxtwitter_url("https://mobile.twitter.com/example/status/67890"),
            "https://fxtwitter.com/example/status/67890",
        )

    def test_build_video_link_message_returns_fxtwitter_url(self) -> None:
        self.assertEqual(
            build_video_link_message("https://twitter.com/example/status/12345"),
            "https://fxtwitter.com/example/status/12345",
        )

    def test_language_codes_accept_user_aliases(self) -> None:
        self.assertEqual(canonical_language_code("ja"), "ja")
        self.assertEqual(canonical_language_code("zh"), "zh")
        self.assertEqual(canonical_language_code("ko"), "ko")
        self.assertEqual(canonical_language_code("ch"), "zh")
        self.assertEqual(canonical_language_code("kr"), "ko")
        self.assertEqual(to_api_language_code("zh"), "zh")
        self.assertEqual(to_api_language_code("ko"), "ko")

    def test_status_needs_translation_skips_japanese_source(self) -> None:
        status = TweetStatus(
            tweet_id="1",
            text="こんにちは",
            source_lang="ja",
            translation_text="Hello",
        )

        self.assertFalse(status_needs_translation(status))

    def test_status_needs_translation_skips_chinese_source_for_zh_target(self) -> None:
        status = TweetStatus(
            tweet_id="1",
            text="你好",
            source_lang="zh-cn",
            translation_text="Hello",
        )

        self.assertFalse(status_needs_translation(status, target_lang="zh"))

    def test_status_needs_translation_uses_translation_text(self) -> None:
        status = TweetStatus(
            tweet_id="1",
            text="Hello",
            source_lang="en",
            translation_text="こんにちは",
        )

        self.assertTrue(status_needs_translation(status))

    def test_extract_tweet_links_supports_i_web_status(self) -> None:
        links = extract_tweet_links(
            "Check https://twitter.com/i/web/status/9876543210 and https://x.com/i/status/11223344"
        )
        self.assertEqual([link.tweet_id for link in links], ["9876543210", "11223344"])
        self.assertIsNone(links[0].handle)
        self.assertIsNone(links[1].handle)
        self.assertEqual(to_fxtwitter_url(links[0].url), "https://fxtwitter.com/i/status/9876543210")
        self.assertEqual(
            to_fxtwitter_url(links[0].url, fallback_handle="author"),
            "https://fxtwitter.com/author/status/9876543210",
        )

    def test_build_translation_message_quotes_translation(self) -> None:
        status = TweetStatus(
            tweet_id="1",
            text="Hello",
            source_lang="en",
            author_handle="example",
            translation_text="こんにちは\n世界",
            translation_target_lang="ja",
        )

        message = build_translation_message(status, "https://x.com/example/status/1")

        self.assertIn("@example", message)
        self.assertIn("> こんにちは", message)
        self.assertIn("> 世界", message)
        self.assertIn("https://fxtwitter.com/example/status/1", message)
        self.assertNotIn("https://x.com/example/status/1", message)

    def test_build_translation_message_preserves_display_url_on_long_text(self) -> None:
        long_text = "\n".join([f"Long line number {i}" for i in range(200)])
        status = TweetStatus(
            tweet_id="12345",
            text="Original tweet",
            source_lang="en",
            author_handle="longauthor",
            translation_text=long_text,
            translation_target_lang="ja",
        )

        msg = build_translation_message(
            status,
            "https://x.com/longauthor/status/12345",
            target_lang="ja",
            max_length=1900,
        )

        self.assertLessEqual(len(msg), 1900)
        self.assertTrue(msg.endswith("https://fxtwitter.com/longauthor/status/12345"))
        self.assertIn("...", msg)


    def test_parse_tweet_status_reads_raw_text_payload(self) -> None:
        status = parse_tweet_status(
            "1",
            {
                "raw_text": {"text": "Hello from raw_text"},
                "lang": "en",
                "translation": {
                    "text": "Translated text",
                    "source_lang": "en",
                    "target_lang": "ja",
                },
            },
        )

        self.assertEqual(status.text, "Hello from raw_text")
        self.assertEqual(status.translation_text, "Translated text")

    def test_parse_tweet_status_detects_video_media(self) -> None:
        status = parse_tweet_status(
            "1",
            {
                "text": "Japanese post with video",
                "lang": "ja",
                "media": {"videos": [{"url": "https://video.twimg.com/example.mp4"}]},
            },
        )

        self.assertTrue(status.has_video)

    def test_payload_has_video_media_checks_quoted_status(self) -> None:
        self.assertTrue(
            payload_has_video_media(
                {
                    "text": "Quote post",
                    "media": {"photos": []},
                    "quote": {"media": {"external": {"type": "video"}}},
                }
            )
        )

    def test_payload_has_video_media_checks_all_media_list(self) -> None:
        self.assertTrue(
            payload_has_video_media(
                {
                    "text": "GIF post",
                    "media": {"all": [{"type": "gif", "url": "https://video.twimg.com/example.mp4"}]},
                }
            )
        )

    def test_status_needs_translation_handles_ja_alias_when_source_unknown(self) -> None:
        status = TweetStatus(tweet_id="1", text="こんにちは", source_lang=None)
        self.assertFalse(status_needs_translation(status, target_lang="jp"))

    def test_get_ui_message_normalizes_language_aliases(self) -> None:
        self.assertEqual(
            get_ui_message("help_title", ui_lang="en-US"),
            get_ui_message("help_title", ui_lang="en"),
        )
        self.assertEqual(
            get_ui_message("help_title", ui_lang="zh-CN"),
            get_ui_message("help_title", ui_lang="zh"),
        )

    def test_normalize_lang_code_handles_non_string(self) -> None:
        self.assertIsNone(normalize_lang_code(None))
        self.assertIsNone(normalize_lang_code(123))  # type: ignore[arg-type]

    def test_truncate_respects_small_limits(self) -> None:
        self.assertEqual(_truncate("abcdef", 0), "")
        self.assertEqual(_truncate("abcdef", 1), ".")
        self.assertEqual(_truncate("abcdef", 2), "..")
        self.assertEqual(_truncate("abcdef", 3), "...")
        self.assertEqual(_truncate("abcdef", 5), "ab...")

    def test_build_translation_message_handles_tiny_max_length_without_truncating_url(self) -> None:
        status = TweetStatus(
            tweet_id="12345",
            text="Hello",
            source_lang="en",
            author_handle="example",
            translation_text="こんにちは世界",
        )
        url = "https://x.com/example/status/12345"
        msg = build_translation_message(status, url, max_length=50)
        self.assertTrue(msg.endswith("https://fxtwitter.com/example/status/12345"))
        self.assertNotIn("...", msg)


class FetchTweetStatusTest(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_tweet_status_wraps_client_error(self) -> None:
        session = MagicMock()
        session.get.side_effect = aiohttp.ClientError("connection reset")

        with self.assertRaises(TweetFetchError):
            await fetch_tweet_status(session, "12345")

    async def test_fetch_tweet_status_reports_http_status_on_non_json_error(self) -> None:
        class _FakeResponse:
            status = 502

            async def json(self, content_type=None):
                raise ValueError("not json")

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        session = MagicMock()
        session.get.return_value = _FakeResponse()

        with self.assertRaises(TweetFetchError) as ctx:
            await fetch_tweet_status(session, "12345")
        self.assertIn("HTTP 502", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
