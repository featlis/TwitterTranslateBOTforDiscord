from __future__ import annotations

from dataclasses import dataclass, replace
import html
import logging
import re
from typing import Any


DEFAULT_FXTWITTER_API_BASE = "https://api.fxtwitter.com/2/status"
DEFAULT_GOOGLE_CLIENTS5_URL = "https://clients5.google.com/translate_a/t"
DEFAULT_GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
DEFAULT_MYMEMORY_TRANSLATE_URL = "https://api.mymemory.translated.net/get"
DEEPL_FREE_API_URL = "https://api-free.deepl.com/v2/translate"
DEEPL_PRO_API_URL = "https://api.deepl.com/v2/translate"

GOOGLE_TRANSLATE_LANG_CODES: dict[str, str] = {
    "ja": "ja",
    "en": "en",
    "zh": "zh-CN",
    "ko": "ko",
}

DEEPL_TARGET_LANG_CODES: dict[str, str] = {
    "ja": "JA",
    "en": "EN-US",
    "zh": "ZH-HANS",
    "ko": "KO",
}

INVALID_TRANSLATION_MARKERS: tuple[str, ...] = (
    "you're using an older version of deepl",
    "deeplの古いバージョンをご利用中です",
    "sie verwenden eine ältere version von deepl",
    "vous utilisez une ancienne version de deepl",
    "вы используете старую версию deepl",
    "您正在使用旧版本的 deepl",
    "estás usando una versión antigua de deepl",
    "stai utilizzando una versione precedente di deepl",
    "deepl'in eski bir sürümünü kullanıyorsun",
    "korzystasz ze starszej wersji deepl",
    "está a utilizar uma versão mais antiga do deepl",
    "u gebruikt een oudere versie van deepl",
    "anda menggunakan deepl versi lama",
    "používáte starší verzi deepl",
    "ти використовуєш стару версію deepl",
)

PROVIDER_ERROR_MARKERS: tuple[str, ...] = (
    "mymemory warning:",
    "query length limit exceeded",
)

NON_LINGUISTIC_LANG_CODES: frozenset[str] = frozenset({"qme", "qht", "qam", "zxx"})

TWEET_URL_RE = re.compile(
    r"https?://(?:www\.|mobile\.)?"
    r"(?P<domain>twitter\.com|x\.com|fxtwitter\.com|fixupx\.com|vxtwitter\.com)"
    r"/(?:(?P<handle>[A-Za-z0-9_]{1,15})|i(?:/web)?)/status(?:es)?/(?P<tweet_id>\d+)"
    r"(?:[/?#][^\s<>]*)?",
    re.IGNORECASE,
)

JAPANESE_SCRIPT_RE = re.compile(r"[\u3040-\u30ff]")
NON_TEXT_TOKEN_RE = re.compile(r"https?://\S+|@[A-Za-z0-9_]+")

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
        "help_desc": "BOTの使いかたとコマンド一覧を表示します。",
        "help_title": "ヘルプ: コマンド一覧",
        "help_body": "このBOTは、Twitter/Xのリンクが投稿された際に自動的に翻訳文を返信します。\n\n**コマンド:**\n• **/ping**: 応答速度を測定します。\n• **/translate_tweet [url] [lang]**: 指定した言語へ翻訳します。\n• **/set_default_lang [lang]**: 自動翻訳のデフォルト言語を設定します。\n• **/set_ui_lang [lang]**: BOTの応答言語を設定します。",
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
        "help_desc": "Show bot usage and command list.",
        "help_title": "Help: Command List",
        "help_body": "This bot automatically translates Twitter/X links posted in messages.\n\n**Commands:**\n• **/ping**: Measure the bot's response latency.\n• **/translate_tweet [url] [lang]**: Translate a tweet to a specific language.\n• **/set_default_lang [lang]**: Set default translation language.\n• **/set_ui_lang [lang]**: Set bot response language.",
    },
    "zh": {
        "translated_header": "**翻译了 {author} 的推文 ({source} -> {target})**",
        "fetch_error": "无法获取推文: `{exc}`",
        "unexpected_error": "发生错误: `{type}`",
        "no_translation": "无法获取 {lang} 的翻译。推文可能已经是该语言，或者翻译 API 未返回内容。",
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
        "help_desc": "显示 BOT 的用法和命令列表。",
        "help_title": "帮助: 命令列表",
        "help_body": "该 BOT 在发布 Twitter/X 链接时会自动回复翻译文本。\n\n**命令:**\n• **/ping**: 检查 BOT 的响应速度。\n• **/translate_tweet [url] [lang]**: 将推文翻译成指定语言。\n• **/set_default_lang [lang]**: 设置自动翻译的默认语言。\n• **/set_ui_lang [lang]**: 设置 BOT 的响应语言。",
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
        "help_desc": "BOT 사용법과 명령어 목록을 표시합니다.",
        "help_title": "도움말: 명령어 목록",
        "help_body": "이 봇은 Twitter/X 링크가 게시될 때 자동으로 번역문을 회신합니다.\n\n**명령어:**\n• **/ping**: BOT의 응답 속도를 확인합니다.\n• **/translate_tweet [url] [lang]**: 지정한 언어로 트윗을 번역합니다.\n• **/set_default_lang [lang]**: 자동 번역의 기본 언어를 설정합니다.\n• **/set_ui_lang [lang]**: BOT의 응답 언어를 설정합니다.",
    }
}


def get_ui_message(key: str, ui_lang: str = "ja", **kwargs) -> str:
    """Get a localized UI message."""
    try:
        lang = canonical_language_code(ui_lang)
    except ValueError:
        lang = "ja"
    if lang not in UI_MESSAGES:
        lang = "ja"
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
                handle=None if (not handle or handle.lower() == "i") else handle,
            )
        )

    return links


def normalize_lang_code(lang: str | None) -> str | None:
    if not isinstance(lang, str):
        return None
    normalized = lang.strip().lower().replace("_", "-")
    return normalized or None


def _meaningful_lang_code(lang: str | None) -> str | None:
    normalized = normalize_lang_code(lang)
    if not normalized or normalized == "und":
        return None
    return normalized


def is_invalid_translation_text(translation_text: str | None, original_text: str = "") -> bool:
    """Detect upstream provider error/deprecation notices masquerading as translations."""
    if not translation_text or not translation_text.strip():
        return True

    unescaped = html.unescape(translation_text).strip()
    lowered = unescaped.lower()
    orig_lower = html.unescape(original_text or "").lower()

    if (lowered.startswith("<!doctype html") or lowered.startswith("<html")) and "<html" not in orig_lower:
        return True

    if any(marker in lowered and marker not in orig_lower for marker in PROVIDER_ERROR_MARKERS):
        return True

    marker_hits = sum(1 for marker in INVALID_TRANSLATION_MARKERS if marker in lowered)
    if marker_hits >= 2:
        return True
    if marker_hits == 1 and "deepl" not in orig_lower:
        return True

    return False


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
    canonical_target = canonical_language_code(target_lang)
    source_lang = _meaningful_lang_code(status.source_lang) or _meaningful_lang_code(
        status.translation_source_lang
    )
    if is_target_language(source_lang, canonical_target):
        return False
    if not source_lang and canonical_target == "ja" and text_looks_japanese(status.text):
        return False
    return True


def to_fxtwitter_url(url: str, fallback_handle: str | None = None) -> str:
    match = TWEET_URL_RE.search(url)
    if not match:
        return url
    handle = match.group("handle") or fallback_handle or "i"
    if handle.lower() == "i" and fallback_handle:
        handle = fallback_handle
    return f"https://fxtwitter.com/{handle}/status/{match.group('tweet_id')}"


def build_video_link_message(original_url: str, fallback_handle: str | None = None) -> str:
    return to_fxtwitter_url(original_url, fallback_handle=fallback_handle)


def _prepare_fallback_query_text(text: str, max_chars: int = 4500) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rsplit(" ", 1)[0].strip() or cleaned[:max_chars]


def _has_translatable_text(text: str) -> bool:
    stripped = NON_TEXT_TOKEN_RE.sub("", text)
    return any(ch.isalpha() for ch in stripped)


async def translate_text_deepl(
    session: Any,
    text: str,
    *,
    api_key: str,
    target_lang: str = "ja",
    timeout_seconds: float = 10,
) -> tuple[str | None, str | None]:
    """Translate text via the official DeepL REST API v2."""
    query_text = _prepare_fallback_query_text(text)
    if not query_text or not api_key.strip():
        return None, None

    try:
        import aiohttp
    except ImportError as exc:  # pragma: no cover - setup guard
        raise RuntimeError("aiohttp is required. Install dependencies from requirements.txt.") from exc

    canonical_target = canonical_language_code(target_lang)
    deepl_target = DEEPL_TARGET_LANG_CODES[canonical_target]
    api_url = DEEPL_FREE_API_URL if api_key.strip().endswith(":fx") else DEEPL_PRO_API_URL
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    try:
        async with session.post(
            api_url,
            headers={
                "Authorization": f"DeepL-Auth-Key {api_key.strip()}",
                "Content-Type": "application/json",
            },
            json={"text": [query_text], "target_lang": deepl_target},
            timeout=timeout,
        ) as response:
            if response.status >= 400:
                logging.warning("Official DeepL API returned HTTP %s.", response.status)
                return None, None
            payload = await response.json(content_type=None)
    except Exception as exc:
        logging.warning("Official DeepL API request failed: %s", exc)
        return None, None

    if not isinstance(payload, dict):
        return None, None
    translations = payload.get("translations")
    if not isinstance(translations, list) or not translations or not isinstance(translations[0], dict):
        return None, None

    translated_text = html.unescape(str(translations[0].get("text") or "")).strip()
    detected_source = _meaningful_lang_code(translations[0].get("detected_source_language"))

    if not translated_text or is_invalid_translation_text(translated_text, query_text):
        return None, detected_source
    if translated_text == query_text:
        return None, detected_source
    return translated_text, detected_source


async def translate_text_google_clients5(
    session: Any,
    text: str,
    *,
    target_lang: str = "ja",
    timeout_seconds: float = 10,
    api_url: str = DEFAULT_GOOGLE_CLIENTS5_URL,
) -> tuple[str | None, str | None]:
    """Translate text via Google Translate's clients5 endpoint."""
    query_text = _prepare_fallback_query_text(text)
    if not query_text:
        return None, None

    try:
        import aiohttp
    except ImportError as exc:  # pragma: no cover - setup guard
        raise RuntimeError("aiohttp is required. Install dependencies from requirements.txt.") from exc

    canonical_target = canonical_language_code(target_lang)
    google_target = GOOGLE_TRANSLATE_LANG_CODES[canonical_target]
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    try:
        async with session.post(
            api_url,
            params={"client": "dict-chrome-ex", "sl": "auto", "tl": google_target},
            data={"q": query_text},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout,
        ) as response:
            if response.status >= 400:
                logging.warning("Fallback Google clients5 returned HTTP %s.", response.status)
                return None, None
            payload = await response.json(content_type=None)
    except Exception as exc:
        logging.warning("Fallback Google clients5 failed: %s", exc)
        return None, None

    if not isinstance(payload, list) or not payload:
        return None, None

    first = payload[0]
    if isinstance(first, list) and first and first[0] is not None:
        raw_translated = str(first[0])
        detected_source = _meaningful_lang_code(first[1]) if len(first) > 1 else None
    elif isinstance(first, str):
        raw_translated = first
        detected_source = None
    else:
        return None, None

    translated_text = html.unescape(raw_translated).strip()
    if not translated_text or is_invalid_translation_text(translated_text, query_text):
        return None, detected_source
    if translated_text == query_text:
        return None, detected_source
    return translated_text, detected_source


async def translate_text_google(
    session: Any,
    text: str,
    *,
    target_lang: str = "ja",
    timeout_seconds: float = 10,
    api_url: str = DEFAULT_GOOGLE_TRANSLATE_URL,
) -> tuple[str | None, str | None]:
    """Translate text via Google Translate's gtx endpoint as a fallback.

    Returns ``(translated_text, detected_source_lang)``. Returns ``(None, None)`` on failure.
    """
    query_text = _prepare_fallback_query_text(text)
    if not query_text:
        return None, None

    try:
        import aiohttp
    except ImportError as exc:  # pragma: no cover - setup guard
        raise RuntimeError("aiohttp is required. Install dependencies from requirements.txt.") from exc

    canonical_target = canonical_language_code(target_lang)
    google_target = GOOGLE_TRANSLATE_LANG_CODES[canonical_target]
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    try:
        async with session.post(
            api_url,
            params={"client": "gtx", "sl": "auto", "tl": google_target, "dt": "t"},
            data={"q": query_text},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout,
        ) as response:
            if response.status >= 400:
                logging.warning("Fallback Google Translate returned HTTP %s.", response.status)
                return None, None
            payload = await response.json(content_type=None)
    except Exception as exc:
        logging.warning("Fallback Google Translate failed: %s", exc)
        return None, None

    if not isinstance(payload, list) or not payload or not isinstance(payload[0], list):
        return None, None

    segments = [
        str(segment[0])
        for segment in payload[0]
        if isinstance(segment, list) and segment and segment[0] is not None
    ]
    translated_text = html.unescape("".join(segments)).strip()
    detected_source = _meaningful_lang_code(payload[2]) if len(payload) > 2 else None

    if not translated_text or is_invalid_translation_text(translated_text, query_text):
        return None, detected_source

    if translated_text == query_text:
        return None, detected_source

    return translated_text, detected_source


async def translate_text_mymemory(
    session: Any,
    text: str,
    *,
    source_lang: str | None,
    target_lang: str = "ja",
    timeout_seconds: float = 10,
    api_url: str = DEFAULT_MYMEMORY_TRANSLATE_URL,
) -> tuple[str | None, str | None]:
    """Translate short text via MyMemory's free public REST API as a last-resort fallback."""
    cleaned = text.strip()
    normalized_source = _meaningful_lang_code(source_lang)
    if not cleaned or not normalized_source or normalized_source in NON_LINGUISTIC_LANG_CODES:
        return None, None
    if len(cleaned.encode("utf-8")) > 500:
        return None, None

    try:
        import aiohttp
    except ImportError as exc:  # pragma: no cover - setup guard
        raise RuntimeError("aiohttp is required. Install dependencies from requirements.txt.") from exc

    canonical_target = canonical_language_code(target_lang)
    target_code = GOOGLE_TRANSLATE_LANG_CODES[canonical_target]
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    try:
        async with session.get(
            api_url,
            params={"q": cleaned, "langpair": f"{normalized_source}|{target_code}"},
            headers={"User-Agent": "TwitterTranslateBOTforDiscord/1.0"},
            timeout=timeout,
        ) as response:
            if response.status >= 400:
                logging.warning("Fallback MyMemory returned HTTP %s.", response.status)
                return None, None
            payload = await response.json(content_type=None)
    except Exception as exc:
        logging.warning("Fallback MyMemory failed: %s", exc)
        return None, None

    if not isinstance(payload, dict) or payload.get("responseStatus") != 200:
        return None, None

    response_data = payload.get("responseData")
    if not isinstance(response_data, dict):
        return None, None

    translated_text = html.unescape(str(response_data.get("translatedText") or "")).strip()
    if not translated_text or is_invalid_translation_text(translated_text, cleaned):
        return None, normalized_source
    if translated_text == cleaned:
        return None, normalized_source
    return translated_text, normalized_source


async def translate_text_fallback(
    session: Any,
    text: str,
    *,
    target_lang: str = "ja",
    source_lang: str | None = None,
    timeout_seconds: float = 10,
    deepl_api_key: str | None = None,
) -> tuple[str | None, str | None]:
    """Try fallback translation providers in priority order."""
    canonical_target = canonical_language_code(target_lang)
    detected_source: str | None = None

    if deepl_api_key:
        translated, detected = await translate_text_deepl(
            session,
            text,
            api_key=deepl_api_key,
            target_lang=canonical_target,
            timeout_seconds=timeout_seconds,
        )
        detected_source = detected_source or detected
        if translated or (detected and is_target_language(detected, canonical_target)):
            return translated, detected_source

    for provider in (translate_text_google_clients5, translate_text_google):
        translated, detected = await provider(
            session,
            text,
            target_lang=canonical_target,
            timeout_seconds=timeout_seconds,
        )
        detected_source = detected_source or detected
        if translated or (detected and is_target_language(detected, canonical_target)):
            return translated, detected_source

    translated, detected = await translate_text_mymemory(
        session,
        text,
        source_lang=source_lang or detected_source,
        target_lang=canonical_target,
        timeout_seconds=timeout_seconds,
    )
    return translated, detected_source or detected


async def fetch_tweet_status(
    session: Any,
    tweet_id: str,
    *,
    target_lang: str = "ja",
    api_base: str = DEFAULT_FXTWITTER_API_BASE,
    timeout_seconds: float = 10,
    enable_fallback_translation: bool = True,
    deepl_api_key: str | None = None,
) -> TweetStatus:
    """Fetch a tweet and request a translation from FxTwitter/FxEmbed, falling back to external translators."""
    try:
        import aiohttp
    except ImportError as exc:  # pragma: no cover - setup guard
        raise RuntimeError("aiohttp is required. Install dependencies from requirements.txt.") from exc

    canonical_target = canonical_language_code(target_lang)
    request_url = f"{api_base.rstrip('/')}/{tweet_id}"
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    try:
        async with session.get(
            request_url,
            params={"lang": to_api_language_code(canonical_target)},
            headers={"User-Agent": "TwitterTranslateBOTforDiscord/1.0"},
            timeout=timeout,
        ) as response:
            try:
                payload = await response.json(content_type=None)
            except Exception as exc:
                if response.status >= 400:
                    raise TweetFetchError(
                        f"FxTwitter returned HTTP {response.status} for {tweet_id}."
                    ) from exc
                raise TweetFetchError(f"FxTwitter returned a non-JSON response for {tweet_id}.") from exc

            if response.status >= 400:
                message = payload.get("message") if isinstance(payload, dict) else None
                raise TweetFetchError(message or f"FxTwitter returned HTTP {response.status} for {tweet_id}.")
    except TweetFetchError:
        raise
    except (aiohttp.ClientError, TimeoutError) as exc:
        raise TweetFetchError(f"Failed to connect to FxTwitter for {tweet_id}: {exc}") from exc

    if not isinstance(payload, dict):
        raise TweetFetchError(f"FxTwitter returned an unexpected response for {tweet_id}.")

    status_payload = payload.get("status") or payload.get("tweet")
    if not isinstance(status_payload, dict):
        message = payload.get("message")
        raise TweetFetchError(message or f"FxTwitter response did not include tweet data for {tweet_id}.")

    status = parse_tweet_status(tweet_id, status_payload)

    if (
        enable_fallback_translation
        and not status.translation_text
        and status.text
        and _has_translatable_text(status.text)
        and status.source_lang not in NON_LINGUISTIC_LANG_CODES
        and status_needs_translation(status, canonical_target)
    ):
        translated_text, detected_source = await translate_text_fallback(
            session,
            status.text,
            target_lang=canonical_target,
            source_lang=status.source_lang or status.translation_source_lang,
            timeout_seconds=timeout_seconds,
            deepl_api_key=deepl_api_key,
        )
        effective_source = status.source_lang or detected_source
        if detected_source and is_target_language(detected_source, canonical_target):
            return replace(
                status,
                source_lang=effective_source,
                translation_text=None,
                translation_source_lang=status.translation_source_lang or detected_source,
                translation_target_lang=None,
            )
        if translated_text:
            return replace(
                status,
                source_lang=effective_source,
                translation_text=translated_text,
                translation_source_lang=status.translation_source_lang or detected_source,
                translation_target_lang=canonical_target,
            )

    return status


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
    cleaned_text = html.unescape(str(text)).strip()

    raw_translation_text = _string_or_none(
        translation_payload.get("text")
        or translation_payload.get("translated_text")
        or translation_payload.get("translatedText")
    )
    translation_valid = bool(
        raw_translation_text and not is_invalid_translation_text(raw_translation_text, cleaned_text)
    )
    translation_text = raw_translation_text if translation_valid else None
    translation_target_lang = (
        _meaningful_lang_code(
            translation_payload.get("target_lang")
            or translation_payload.get("targetLang")
            or translation_payload.get("target_language")
        )
        if translation_valid
        else None
    )

    return TweetStatus(
        tweet_id=tweet_id,
        text=cleaned_text,
        source_lang=_meaningful_lang_code(status_payload.get("lang")),
        author_name=_string_or_none(author_payload.get("name")),
        author_handle=_string_or_none(
            author_payload.get("screen_name")
            or author_payload.get("screenName")
            or author_payload.get("username")
        ),
        translation_text=translation_text,
        translation_source_lang=_meaningful_lang_code(
            translation_payload.get("source_lang")
            or translation_payload.get("sourceLang")
            or translation_payload.get("source_language")
        ),
        translation_target_lang=translation_target_lang,
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

    all_media = media_payload.get("all")
    if isinstance(all_media, list) and any(
        isinstance(item, dict) and str(item.get("type", "")).lower() in {"video", "gif"}
        for item in all_media
    ):
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

    display_url = to_fxtwitter_url(original_url, fallback_handle=status.author_handle)
    header = get_ui_message(
        "translated_header",
        ui_lang=ui_lang,
        author=author,
        source=source_lang,
        target=target,
    )

    translated_text = html.unescape(status.translation_text or "").strip()

    prefix = f"{header}\n"
    suffix = f"\n{display_url}"
    max_quote_len = max_length - len(prefix) - len(suffix)

    if not translated_text or is_invalid_translation_text(translated_text, status.text) or max_quote_len <= 0:
        return f"{header}\n{display_url}"

    quoted_lines = [f"> {line}" if line else ">" for line in translated_text.splitlines()]
    quoted_text = "\n".join(quoted_lines)

    if len(quoted_text) > max_quote_len:
        quoted_text = _truncate(quoted_text, max_quote_len)

    return f"{prefix}{quoted_text}{suffix}"


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _truncate(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= 3:
        return "." * limit
    return text[: limit - 3].rstrip() + "..."
