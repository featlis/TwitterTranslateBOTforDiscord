# TwitterTranslateBOTforDiscord AGENTS MEMO

## ARCH/STACK
- Python 3.12+, discord.py 2.4+, aiohttp, python-dotenv
- Entry: `src/bot.py`, Tools: `src/twitter_tools.py`, Tests: `tests/test_twitter_tools.py`
- Conf: `.env` (init envvars) -> `bot_config.json` (runtime guild settings persistent via `_save_runtime_config`)

## CORE FLOW
- Detect: `extract_tweet_links` scans msg+embeds using `TWEET_URL_RE` (twitter.com, x.com, fxtwitter.com, fixupx.com, vxtwitter.com; handles `/handle/status/<id>`, `/i/status/<id>`, `/i/web/status/<id>`).
- Fetch: `fetch_tweet_status` hits FxTwitter API v2 (`https://api.fxtwitter.com/2/status/<id>?lang=<api_code>`).
- Langs: `ja`, `en`, `zh`, `ko`. Aliases via `LANGUAGE_ALIASES`. Canonical via `canonical_language_code`.
- Auto-reply (`on_message`):
  - If `status_needs_translation` AND `status.translation_text`: reply translated msg + `TranslationLanguageView` buttons.
  - If needs translation but NO `translation_text`: fallback `build_video_link_message` (FxTwitter URL).
  - Else if `status.has_video`: reply `build_video_link_message`.
  - Else: skip.
- Buttons (`TranslationLanguageView`):
  - Excludes `source_lang` button.
  - Callback updates message: if translated -> translation msg; else -> FxTwitter link.
  - CRITICAL: KEEP view instance in callback edit; NEVER set `view=None` on fallback, otherwise buttons vanish permanently.

## SLASH COMMANDS
- `/ping`: WebSocket & interaction latency (ephemeral).
- `/help`: Localized embed help. Note: `/tweet_test` deprecated & deleted. Do not reference.
- `/translate_tweet [url] [lang]`: Fetch & translate. Requires `status.translation_text`; if absent & video -> video link; else -> `no_translation` ephemeral.
- `/set_default_lang [lang]`: Manage guild default translate target.
- `/set_ui_lang [lang]`: Manage guild bot response UI language.

## LOCALIZATION
- `UI_MESSAGES` dict for `ja`, `en`, `zh`, `ko`. Keep all keys identical across languages.
- `DiscordTranslator`: translates slash cmd descriptions (`_desc`) and choices (`lang_name_`). Choice names return `<label> (<code>)`.

## GOTCHAS & RULES
1. NEVER truncate `display_url` in `build_translation_message`. Truncate `quoted_text` only; suffix URL intact.
2. `status_needs_translation` checks language mismatch only. ALWAYS check `bool(status.translation_text)` alongside it.
3. Message length: Discord limit 2000 chars. Internal max default 1900.
4. Security: keep `allowed_mentions=discord.AllowedMentions.none()` on all replies/edits/followups.
5. Unit tests: run `python -m unittest discover tests`.
