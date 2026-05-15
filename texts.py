from __future__ import annotations

import json
import os
from datetime import datetime

import pytz

# (tz_id, display_label) — label is language-neutral (city names are similar in uk/ru)
TIMEZONES: list[tuple[str, str]] = [
    ("Europe/Kyiv",         "🇺🇦 Київ / Киев          UTC+2/+3"),
    ("Europe/Minsk",        "🇧🇾 Мінськ / Минск        UTC+3"),
    ("Europe/Moscow",       "🇷🇺 Москва                UTC+3"),
    ("Europe/Samara",       "🇷🇺 Самара                UTC+4"),
    ("Asia/Yekaterinburg",  "🇷🇺 Єкатеринбург          UTC+5"),
    ("Asia/Omsk",           "🇷🇺 Омськ / Омск          UTC+6"),
    ("Asia/Novosibirsk",    "🇷🇺 Новосибірськ          UTC+7"),
    ("Asia/Krasnoyarsk",    "🇷🇺 Красноярськ           UTC+7"),
    ("Asia/Irkutsk",        "🇷🇺 Іркутськ / Иркутск   UTC+8"),
    ("Asia/Yakutsk",        "🇷🇺 Якутськ / Якутск     UTC+9"),
    ("Asia/Vladivostok",    "🇷🇺 Владивосток           UTC+10"),
    ("Asia/Magadan",        "🇷🇺 Магадан               UTC+11"),
    ("Asia/Kamchatka",      "🇷🇺 Камчатка              UTC+12"),
    ("Asia/Tbilisi",        "🇬🇪 Тбілісі / Тбилиси    UTC+4"),
    ("Asia/Baku",           "🇦🇿 Баку                  UTC+4"),
    ("Asia/Yerevan",        "🇦🇲 Єреван / Ереван       UTC+4"),
    ("Asia/Tashkent",       "🇺🇿 Ташкент               UTC+5"),
    ("Asia/Almaty",         "🇰🇿 Алмати / Алматы       UTC+6"),
    ("Europe/London",       "🇬🇧 Лондон                UTC+0/+1"),
    ("Europe/Berlin",       "🇩🇪 Берлін / Берлин       UTC+1/+2"),
    ("Europe/Paris",        "🇫🇷 Париж                 UTC+1/+2"),
    ("Europe/Istanbul",     "🇹🇷 Стамбул               UTC+3"),
    ("Asia/Dubai",          "🇦🇪 Дубай                 UTC+4"),
    ("Asia/Jerusalem",      "🇮🇱 Єрусалим              UTC+2/+3"),
    ("Asia/Bangkok",        "🇹🇭 Бангкок               UTC+7"),
    ("Asia/Singapore",      "🇸🇬 Сінгапур              UTC+8"),
    ("Asia/Tokyo",          "🇯🇵 Токіо / Токио         UTC+9"),
    ("America/New_York",    "🇺🇸 Нью-Йорк              UTC-5/-4"),
    ("America/Chicago",     "🇺🇸 Чикаго                UTC-6/-5"),
    ("America/Los_Angeles", "🇺🇸 Лос-Анджелес          UTC-8/-7"),
    ("Australia/Sydney",    "🇦🇺 Сідней / Сидней       UTC+10/+11"),
    ("Pacific/Auckland",    "🇳🇿 Окленд                UTC+12/+13"),
]

_TZ_DISPLAY: dict[str, str] = {tz_id: label for tz_id, label in TIMEZONES}

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "texts.json"), encoding="utf-8") as _f:
    TEXTS: dict[str, dict] = json.load(_f)

BTN_ACTIVITIES = {t["btn_activities"] for t in TEXTS.values()}
BTN_HISTORY    = {t["btn_history"]    for t in TEXTS.values()}
BTN_PROFILE    = {t["btn_profile"]    for t in TEXTS.values()}


def T(lang: str, key: str, *args, **kwargs):
    value = TEXTS[lang][key]
    if isinstance(value, str):
        if kwargs:
            return value.format(**kwargs)
        if args:
            return value.format(*args)
    return value


def tz_name(lang: str, tz: str) -> str:
    return _TZ_DISPLAY.get(tz, tz)


def find_tz_by_current_time(user_hour: int, user_minute: int) -> str:
    """Detect timezone by comparing user's current time to UTC."""
    now_utc = datetime.now(pytz.utc)
    user_total = user_hour * 60 + user_minute
    utc_total = now_utc.hour * 60 + now_utc.minute

    diff = user_total - utc_total
    if diff > 780:
        diff -= 1440
    elif diff < -720:
        diff += 1440

    best_tz = TIMEZONES[0][0]
    best_delta = float("inf")
    for tz_id, _ in TIMEZONES:
        tz_offset_min = int(pytz.timezone(tz_id).utcoffset(now_utc.replace(tzinfo=None)).total_seconds() / 60)
        delta = abs(tz_offset_min - diff)
        if delta < best_delta:
            best_delta = delta
            best_tz = tz_id

    return best_tz


def activity_name(lang: str, row) -> str:
    return row[f"name_{lang}"] or row["name_uk"]


def activity_desc(lang: str, row) -> str:
    return row[f"description_{lang}"] or row["description_uk"] or ""


def _stars(n: int) -> str:
    return "⭐" * n + "☆" * (5 - n)


def format_body(slug: str, lang: str, responses: dict) -> str:
    """Schema-driven render of an activity's responses.

    Walks the activity's field schema (see activities.SCHEMAS) and renders each
    field with its label. Inserts block headers wherever a field declares one.
    Scale fields are rendered as star ratings; other fields show their value
    (or — if missing).
    """
    from activities import FieldType, get_schema

    lines: list[str] = []
    for f in get_schema(slug):
        if f.block_header_key:
            if lines:
                lines.append("")  # blank line between blocks
            lines.append(T(lang, f.block_header_key))

        label = T(lang, f.label_key)
        value = responses.get(f.name, "—")

        if f.type == FieldType.SCALE:
            n = value if isinstance(value, int) else 0
            lines.append(f"  {label}: {_stars(n)} ({value if value != '—' else '?'}/5)")
        else:
            lines.append(f"  {label}: {value if value not in (None, '') else '—'}")

    return "\n".join(lines)


def format_summary(slug: str, lang: str, responses: dict, date_str: str) -> str:
    """Full completion message: shared header + schema-driven body."""
    return T(lang, "summary_header", date_str) + "\n\n" + format_body(slug, lang, responses)


# Back-compat shims — keep the old names working for any external callers / tests.
def format_tp_body(lang: str, responses: dict) -> str:
    return format_body("thinking_pattern", lang, responses)


def format_tp_summary(lang: str, responses: dict, date_str: str) -> str:
    return format_summary("thinking_pattern", lang, responses, date_str)
