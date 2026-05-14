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


def format_tp_body(lang: str, responses: dict) -> str:
    """Format the three blocks without the header line."""
    labels = T(lang, "tp_field_labels")
    lines = [
        T(lang, "tp_block1_header"),
        f"  {labels['irritation']}: {_stars(responses.get('irritation', 0))} ({responses.get('irritation', '?')}/5)",
        f"  {labels['excitement']}: {_stars(responses.get('excitement', 0))} ({responses.get('excitement', '?')}/5)",
        f"  {labels['sensation']}: {responses.get('sensation', '—')}",
        "",
        T(lang, "tp_block2_header"),
        f"  {labels['feeling']}: {responses.get('feeling', '—')}",
        f"  {labels['emotion']}: {responses.get('emotion', '—')}",
        f"  {labels['impression']}: {responses.get('impression', '—')}",
        "",
        T(lang, "tp_block3_header"),
        f"  {labels['meaning']}: {responses.get('meaning', '—')}",
        f"  {labels['idea']}: {responses.get('idea', '—')}",
    ]
    return "\n".join(lines)


def format_tp_summary(lang: str, responses: dict, date_str: str) -> str:
    """Full completion message: header + body."""
    return T(lang, "tp_summary_header", date_str) + "\n\n" + format_tp_body(lang, responses)
