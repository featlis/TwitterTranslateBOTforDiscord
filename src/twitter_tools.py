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

LANGUAGE_OPTIONS: dict[str, dict[str, str]] = {
    "ja": {"api_code": "ja", "label": "日本語"},
    "en": {"api_code": "en", "label": "English"},
    "zh": {"api_code": "zh", "label": "中文"},
    "ko": {"api_code": "ko", "label": "한국어"},
}

LANGUAGE_ALIASES = {
    "ja": "ja",
    "jp": "ja",
    "en": "en",
    "ch": "zh",
    "cn": "zh",
    "zh": "zh",
    "zh-cn": "zh",
    "zh-hans": "zh",
    "kr": "ko",
    "ko": "ko",
    "kor": "ko",
}

UI_MESSAGES = {
    "ja": {
        "translated_header": "**{author} の投稿を翻訳しました ({source} -> {target})**",
        "fetch_error": "投稿を取得できませんでした: `{exc}`",
        "unexpected_error": "エラーが出ました: `{type}`",
        "no_translation": "{lang}への翻訳文を取得できませんでした。投稿がすでに同じ言語か、翻訳APIから翻訳文が返っていません。",
        "invalid_url": "Twitter/Xの投稿URLとして認識できませんでした。`https://x.com/user/status/123...` の形式で試してください。",
        "ping": "Pong! WebSocket: `{websocket_ms}ms` / Interaction: `{interaction_ms}ms`",
        "test_success": "取得と翻訳に成功しました。",
        "test_video": "投稿は翻訳対象ではありませんが、動画付きなので通常投稿ではFxTwitterリンクを返信します。",
        "test_skipped": "投稿は取得できましたが、通常投稿では返信しません。",
        "reason_api": "翻訳文がAPIから返っていません。",
        "reason_lang": "投稿が翻訳先の言語として判定されたためスキップされます。",
        "set_default_lang": "自動翻訳のデフォルト言語を {label} (`{code}`) に変更しました。",
        "set_ui_lang": "BOTの応答言語を {label} (`{code}`) に変更しました。",
        "config_save_error": "設定を保存できませんでした: `{type}`",
        "ping_desc": "BOTの応答速度を測定します。",
        "tweet_test_desc": "Twitter/Xリンクの翻訳取得をテストします。",
        "translate_tweet_desc": "Twitter/Xリンクを指定した言語へ翻訳します。",
        "set_default_lang_desc": "自動翻訳のデフォルト言語を変更します。",
        "set_ui_lang_desc": "BOTの応答言語を変更します。",
        "url_param_desc": "確認・翻訳したいTwitter/Xの投稿URL",
        "lang_param_desc": "翻訳先の言語、またはBOTの応答言語",
        "lang_name_ja": "日本語",
        "lang_name_en": "英語",
        "lang_name_zh": "中国語",
        "lang_name_ko": "韓国語",
    },
    "en": {
        "translated_header": "**Translated {author}'s post ({source} -> {target})**",
        "fetch_error": "Could not fetch post: `{exc}`",
        "unexpected_error": "An error occurred: `{type}`",
        "no_translation": "Could not get translation for {lang}. The post might be in that language or API didn't return text.",
        "invalid_url": "Invalid Twitter/X URL. Try `https://x.com/user/status/123...`.",
        "ping": "Pong! WebSocket: `{websocket_ms}ms` / Interaction: `{interaction_ms}ms`",
        "test_success": "Successfully fetched and translated.",
        "test_video": "Post doesn't need translation, but contains video so FxTwitter link is used.",
        "test_skipped": "Fetched the post, but it won't be sent automatically.",
        "reason_api": "Translation text was not returned by API.",
        "reason_lang": "Post is already in the target language.",
        "set_default_lang": "Changed default translation language to {label} (`{code}`).",
        "set_ui_lang": "Changed bot's response language to {label} (`{code}`).",
        "config_save_error": "Could not save settings: `{type}`",
        "ping_desc": "Measure the bot's response latency.",
        "tweet_test_desc": "Test fetching and translating a Twitter/X link.",
        "translate_tweet_desc": "Translate a Twitter/X link to a specified language.",
        "set_default_lang_desc": "Change the default target language for automatic translation.",
        "set_ui_lang_desc": "Change the bot's response language.",
        "url_param_desc": "The Twitter/X post URL to check or translate",
        "lang_param_desc": "The target language or bot response language",
        "lang_name_ja": "Japanese",
        "lang_name_en": "English",
        "lang_name_zh": "Chinese",
        "lang_name_ko": "Korean",
    },
    "zh": {
        "translated_header": "**翻译了 {author} 的推文 ({source} -> {target})**",
        "fetch_error": "无法获取推文: `{exc}`",
        "unexpected_error": "发生错误: `{type}`",
        "no_translation": "无法获取 {lang} 的翻译推文可能已经是该语言，或者翻译 API 未返回内容。",
        "invalid_url": "无法识别为 Twitter/X 链接。请尝试 `https://x.com/user/status/123...`。",
        "ping": "Pong! WebSocket: `{websocket_ms}ms` / Interaction: `{interaction_ms}ms`",
        "test_success": "获取并翻译成功。",
        "test_video": "推文不需要翻译，但由于包含视频，将返回 FxTwitter 链接。",
        "test_skipped": "推文已获取，但在普通消息中不会自动回复。",
        "reason_api": "翻译 API 未返回翻译文本。",
        "reason_lang": "推文已被判定为目标语言。",
        "set_default_lang": "已将默认翻译语言更改为 {label} (`{code}`)。",
        "set_ui_lang": "已将 BOT 响应语言更改为 {label} (`{code}`)。",
        "config_save_error": "无法保存设置: `{type}`",
        "ping_desc": "测量 BOT 的响应速度。",
        "tweet_test_desc": "测试 Twitter/X 链接的获取和翻译。",
        "translate_tweet_desc": "将 Twitter/X 链接翻译成指定语言。",
        "set_default_lang_desc": "更改自动翻译的默认目标语言。",
        "set_ui_lang_desc": "更改 BOT 的响应语言。",
        "url_param_desc": "要检查或翻译的 Twitter/X 推文链接",
        "lang_param_desc": "目标语言或 BOT 响应语言",
        "lang_name_ja": "日语",
        "lang_name_en": "英语",
        "lang_name_zh": "中文",
        "lang_name_ko": "韩语",
    },
    "ko": {
        "translated_header": "**{author} 님의 게시물을 번역했습니다 ({source} -> {target})**",
        "fetch_error": "게시물을 가져올 수 없습니다: `{exc}`",
        "unexpected_error": "오류가 발생했습니다: `{type}`",
        "no_translation": "{lang} 번역문을 가져올 수 없습니다. 이미 해당 언어이거나 API에서 번역문을 반환하지 않았습니다.",
        "invalid_url": "Twitter/X URL을 인식할 수 없습니다. `https://x.com/user/status/123...` 형식으로 시도해 주세요.",
        "ping": "Pong! WebSocket: `{websocket_ms}ms` / Interaction: `{interaction_ms}ms`",
        "test_success": "게시물 가져오기 및 번역에 성공했습니다.",
        "test_video": "번역 대상은 아니지만, 동영상이 포함되어 있어 FxTwitter 링크를 반환합니다.",
        "test_skipped": "게시물을 가져왔지만, 일반 메시지에서는 회신하지 않습니다.",
        "reason_api": "API에서 번역문을 반환하지 않았습니다.",
        "reason_lang": "게시물이 이미 대상 언어로 판정되어 건너뜁니다.",
        "set_default_lang": "기본 번역 언어를 {label} (`{code}`)(으)로 변경했습니다.",
        "set_ui_lang": "봇 응답 언어를 {label} (`{code}`)(으)로 변경했습니다.",
        "config_save_error": "설정을 저장할 수 없습니다: `{type}`",
        "ping_desc": "BOT의 응답 속도를 측정합니다.",
        "tweet_test_desc": "Twitter/X 링크의 번역 가져오기를 테스트합니다.",
        "translate_tweet_desc": "Twitter/X 링크를 지정한 언어로 번역합니다.",
        "set_default_lang_desc": "자동 번역의 기본 대상 언어를 변경합니다.",
        "set_ui_lang_desc": "봇의 응답 언어를 변경합니다.",
        "url_param_desc": "확인 또는 번역할 Twitter/X 게시물 URL",
        "lang_param_desc": "대상 언어 또는 봇 응답 언어",
        "lang_name_ja": "일본어",
        "lang_name_en": "영어",
        "lang_name_zh": "중국어",
        "lang_name_ko": "한국어",
    }
}


def get_ui_message(key: str, ui_lang: str = "ja", **kwargs) -> str:
    """Get a localized UI message."""
    lang = ui_lang if ui_lang in UI_MESSAGES else "ja"
    template = UI_MESSAGES[lang].get(key, UI_MESSAGES["ja"].get(key, key))
    return template.format(**kwargs)


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


def supported_language_codes() -> tuple[str, ...]:
    return tuple(LANGUAGE_OPTIONS)


def canonical_language_code(lang: str | None) -> str:
    normalized = normalize_lang_code(lang)
    if not normalized:
        raise ValueError("Language code is empty.")

    canonical = LANGUAGE_ALIASES.get(normalized) or LANGUAGE_ALIASES.get(normalized.split("-", 1)[0])
    if canonical not in LANGUAGE_OPTIONS:
        supported = ", ".join(supported_language_codes())
        raise ValueError(f"Unsupported language '{lang}'. Use one of: {supported}.")
    return canonical


def to_api_language_code(lang: str | None) -> str:
    return LANGUAGE_OPTIONS[canonical_language_code(lang)]["api_code"]


def language_label(lang: str | None) -> str:
    return LANGUAGE_OPTIONS[canonical_language_code(lang)]["label"]


def is_target_language(lang: str | None, target_lang: str = "ja") -> bool:
    normalized_lang = normalize_lang_code(lang)
    if not normalized_lang:
        return False
    normalized_target = to_api_language_code(target_lang)
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
        params={"lang": to_api_language_code(target_lang)},
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
    ui_lang: str = "ja",
    max_length: int = 1900,
) -> str:
    source_lang = status.source_lang or status.translation_source_lang or "unknown"
    target = language_label(target_lang)
    author = f"@{status.author_handle}" if status.author_handle else "Twitter/X"

    translated_text = (status.translation_text or "").strip()
    translated_text = html.unescape(translated_text)
    translated_text = _truncate(translated_text, max(200, max_length - 320))
    quoted_text = "\n".join(f"> {line}" if line else ">" for line in translated_text.splitlines())
    display_url = to_fxtwitter_url(original_url)

    header = get_ui_message(
        "translated_header",
        ui_lang=ui_lang,
        author=author,
        source=source_lang,
        target=target,
    )
    return _truncate(f"{header}\n{quoted_text}\n{display_url}", max_length)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
