from __future__ import annotations

from dataclasses import dataclass
import html
import re
from typing import Any


DEFAULT_FXTWITTER_API_BASE = "https://api.fxtwitter.com/2/status"

TWEET_URL_RE = re.compile(
    r"https?://(?:www\.|mobile\.)?"
    r"(?P<domain>twitter\.com|x\.com|fxtwitter\.com|fixupx\.com|vxtwitter\.com)"
    r"/(?P<handle>[A-Za-z0-9_]{1,15}|i)/status(?:es)?/(?P<tweet_id>\d+)"
    r"(?:[/?#][^\s<>]*)?",
    re.IGNORECASE,
)

JAPANESE_SCRIPT_RE = re.compile(r"[\u3040-\u30ff]")


@dataclass(frozen=True)
class TweetLink:
    tweet_id: str
    url: str
    handle: str | None = None


@dataclass(frozen=True)
class TweetStatus:
    tweet_id: str
    text: str
    source_lang: str | None = None
    author_name: str | None = None
    author_handle: str | None = None
    translation_text: str | None = None
    translation_source_lang: str | None = None
    translation_target_lang: str | None = None
    has_video: bool = False


class TweetFetchError(Exception):
    """Raised when a tweet cannot be fetched from the public FxTwitter API."""


def extract_tweet_links(text: str) -> list[TweetLink]:
    """Extract unique Twitter/X status links from message text in appearance order."""
    links: list[TweetLink] = []
    seen_ids: set[str] = set()

    for match in TWEET_URL_RE.finditer(text):
        tweet_id = match.group("tweet_id")
        if tweet_id in seen_ids:
            continue
        seen_ids.add(tweet_id)

        handle = match.group("handle")
        links.append(
            TweetLink(
                tweet_id=tweet_id,
                url=match.group(0),
                handle=None if handle.lower() == "i" else handle,
            )
        )

    return links


def normalize_lang_code(lang: str | None) -> str | None:
    if not lang:
        return None
    return lang.strip().lower().replace("_", "-") or None


def is_target_language(lang: str | None, target_lang: str = "ja") -> bool:
    normalized_lang = normalize_lang_code(lang)
    normalized_target = normalize_lang_code(target_lang)
    if not normalized_lang or not normalized_target:
        return False
    return normalized_lang.split("-", 1)[0] == normalized_target.split("-", 1)[0]


def text_looks_japanese(text: str) -> bool:
    return bool(JAPANESE_SCRIPT_RE.search(text))


def status_needs_translation(status: TweetStatus, target_lang: str = "ja") -> bool:
    source_lang = status.source_lang or status.translation_source_lang
    if is_target_language(source_lang, target_lang):
        return False
    if not source_lang and text_looks_japanese(status.text):
        return False
    return bool(status.translation_text and status.translation_text.strip())


def to_fxtwitter_url(url: str) -> str:
    match = TWEET_URL_RE.search(url)
    if not match:
        return url
    return f"https://fxtwitter.com/{match.group('handle')}/status/{match.group('tweet_id')}"


def build_video_link_message(original_url: str) -> str:
    return to_fxtwitter_url(original_url)


async def fetch_tweet_status(
    session: Any,
    tweet_id: str,
    *,
    target_lang: str = "ja",
    api_base: str = DEFAULT_FXTWITTER_API_BASE,
    timeout_seconds: float = 10,
) -> TweetStatus:
    """Fetch a tweet and request a translation from FxTwitter/FxEmbed."""
    try:
        import aiohttp
    except ImportError as exc:  # pragma: no cover - setup guard
        raise RuntimeError("aiohttp is required. Install dependencies from requirements.txt.") from exc

    request_url = f"{api_base.rstrip('/')}/{tweet_id}"
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async with session.get(
        request_url,
        params={"lang": target_lang},
        timeout=timeout,
    ) as response:
        try:
            payload = await response.json(content_type=None)
        except Exception as exc:
            raise TweetFetchError(f"FxTwitter returned a non-JSON response for {tweet_id}.") from exc

        if response.status >= 400:
            message = payload.get("message") if isinstance(payload, dict) else None
            raise TweetFetchError(message or f"FxTwitter returned HTTP {response.status} for {tweet_id}.")

    if not isinstance(payload, dict):
        raise TweetFetchError(f"FxTwitter returned an unexpected response for {tweet_id}.")

    status_payload = payload.get("status") or payload.get("tweet")
    if not isinstance(status_payload, dict):
        message = payload.get("message")
        raise TweetFetchError(message or f"FxTwitter response did not include tweet data for {tweet_id}.")

    return parse_tweet_status(tweet_id, status_payload)


def parse_tweet_status(tweet_id: str, status_payload: dict[str, Any]) -> TweetStatus:
    author_payload = status_payload.get("author")
    if not isinstance(author_payload, dict):
        author_payload = {}

    raw_text_payload = status_payload.get("raw_text")
    if not isinstance(raw_text_payload, dict):
        raw_text_payload = {}

    translation_payload = status_payload.get("translation")
    if not isinstance(translation_payload, dict):
        translation_payload = {}

    text = (
        status_payload.get("text")
        or raw_text_payload.get("text")
        or status_payload.get("full_text")
        or status_payload.get("description")
        or ""
    )

    return TweetStatus(
        tweet_id=tweet_id,
        text=html.unescape(str(text)).strip(),
        source_lang=normalize_lang_code(status_payload.get("lang")),
        author_name=_string_or_none(author_payload.get("name")),
        author_handle=_string_or_none(
            author_payload.get("screen_name")
            or author_payload.get("screenName")
            or author_payload.get("username")
        ),
        translation_text=_string_or_none(
            translation_payload.get("text")
            or translation_payload.get("translated_text")
            or translation_payload.get("translatedText")
        ),
        translation_source_lang=normalize_lang_code(
            translation_payload.get("source_lang")
            or translation_payload.get("sourceLang")
            or translation_payload.get("source_language")
        ),
        translation_target_lang=normalize_lang_code(
            translation_payload.get("target_lang")
            or translation_payload.get("targetLang")
            or translation_payload.get("target_language")
        ),
        has_video=payload_has_video_media(status_payload),
    )


def payload_has_video_media(status_payload: Any) -> bool:
    if not isinstance(status_payload, dict):
        return False

    if _media_payload_has_video(status_payload.get("media")):
        return True

    quote_payload = status_payload.get("quote")
    return payload_has_video_media(quote_payload)


def _media_payload_has_video(media_payload: Any) -> bool:
    if not isinstance(media_payload, dict):
        return False

    external_payload = media_payload.get("external")
    if isinstance(external_payload, dict) and str(external_payload.get("type", "")).lower() == "video":
        return True

    videos = media_payload.get("videos")
    if isinstance(videos, list) and any(isinstance(item, dict) for item in videos):
        return True

    photos = media_payload.get("photos")
    if isinstance(photos, list):
        return any(isinstance(item, dict) and str(item.get("type", "")).lower() == "gif" for item in photos)

    return False


def build_translation_message(
    status: TweetStatus,
    original_url: str,
    *,
    target_lang: str = "ja",
    max_length: int = 1900,
) -> str:
    source_lang = status.source_lang or status.translation_source_lang or "unknown"
    target = status.translation_target_lang or target_lang
    author = f"@{status.author_handle}" if status.author_handle else "Twitter/X"

    translated_text = (status.translation_text or "").strip()
    translated_text = html.unescape(translated_text)
    translated_text = _truncate(translated_text, max(200, max_length - 320))
    quoted_text = "\n".join(f"> {line}" if line else ">" for line in translated_text.splitlines())
    display_url = to_fxtwitter_url(original_url)

    message = (
        f"**{author} の投稿を翻訳しました ({source_lang} -> {target})**\n"
        f"{quoted_text}\n"
        f"{display_url}"
    )
    return _truncate(message, max_length)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
