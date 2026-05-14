from __future__ import annotations

from datetime import date, timedelta

import os

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from texts import T, tz_name, activity_name, BTN_ACTIVITIES

WEBAPP_BASE_URL = os.environ.get("WEBAPP_BASE_URL", "https://psy-bot-shy-hill-2279.fly.dev")


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang:uk"),
        InlineKeyboardButton(text="🇷🇺 Русский",    callback_data="lang:ru"),
    ]])


def main_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=T(lang, "btn_activities"))]],
        resize_keyboard=True,
    )


def scale_kb(lang: str, field: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(i), callback_data=f"tp_scale:{field}:{i}") for i in range(1, 6)],
        [InlineKeyboardButton(text=T(lang, "scale_hint"), callback_data="noop")],
        [InlineKeyboardButton(text=T(lang, "cancel_btn"), callback_data="tp_cancel")],
    ])


def choice_kb(lang: str, field: str) -> InlineKeyboardMarkup:
    options: list[str] = T(lang, f"{field}s")  # "feelings" or "emotions"
    rows = []
    row = []
    for i, opt in enumerate(options):
        row.append(InlineKeyboardButton(text=opt, callback_data=f"tp_choice:{field}:{i}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text=T(lang, "custom_option"), callback_data=f"tp_custom:{field}"),
        InlineKeyboardButton(text=T(lang, "cancel_btn"),    callback_data="tp_cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def text_cancel_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=T(lang, "cancel_btn"), callback_data="tp_cancel"),
    ]])


def activities_kb(lang: str, activities, subscribed_slugs: set[str]) -> InlineKeyboardMarkup:
    rows = []
    for act in activities:
        slug = act["slug"]
        name = activity_name(lang, act)
        status = "✅" if slug in subscribed_slugs else "⚪"
        rows.append([InlineKeyboardButton(
            text=f"{status} {name}",
            callback_data=f"act_detail:{slug}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def activity_detail_kb(lang: str, slug: str, subscription) -> InlineKeyboardMarkup:
    rows = []
    if subscription and subscription["is_active"]:
        t = subscription["reminder_time"].strftime("%H:%M")
        tz = tz_name(lang, subscription["timezone"])
        rows.append([InlineKeyboardButton(
            text=T(lang, "btn_start_now"),
            callback_data=f"start_session:{slug}",
        )])
        rows.append([InlineKeyboardButton(
            text=T(lang, "btn_records"),
            callback_data=f"act_history:{slug}",
        )])
        rows.append([InlineKeyboardButton(
            text=T(lang, "btn_change_reminder", time=t, tz=tz),
            callback_data=f"change_time:{slug}",
        )])
        rows.append([InlineKeyboardButton(
            text=T(lang, "btn_unsubscribe"),
            callback_data=f"unsub:{slug}",
        )])
    else:
        rows.append([InlineKeyboardButton(
            text=T(lang, "btn_subscribe"),
            callback_data=f"sub:{slug}",
        )])
    rows.append([InlineKeyboardButton(text=T(lang, "back"), callback_data="act_list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reminder_time_webapp_kb(lang: str, slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=T(lang, "btn_pick_reminder_time"),
            web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/webapp/time-picker.html?mode=reminder"),
        ),
    ]])


def tz_webapp_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=T(lang, "btn_pick_current_time"),
            web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/webapp/time-picker.html?mode=tz"),
        ),
    ]])


def start_analysis_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=T(lang, "btn_start_analysis"),
            callback_data="start_session:thinking_pattern",
        ),
    ]])


def confirm_unsub_kb(lang: str, slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=T(lang, "yes_btn"), callback_data=f"unsub_yes:{slug}"),
        InlineKeyboardButton(text=T(lang, "no_btn"),  callback_data=f"act_detail:{slug}"),
    ]])


def already_done_kb(lang: str, slug: str, session_date: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=T(lang, "tp_btn_view"), callback_data=f"hist_day:{slug}:{session_date}"),
        InlineKeyboardButton(text=T(lang, "tp_btn_redo"), callback_data=f"tp_redo:{slug}:{session_date}"),
    ]])


def history_kb(lang: str, slug: str, recent_sessions: list, today: date) -> InlineKeyboardMarkup:
    rows = []
    for s in recent_sessions:
        d = s["session_date"]
        label = T(lang, "hist_day_done" if s["is_complete"] else "hist_day_miss",
                  date=d.strftime("%d.%m"))
        rows.append([InlineKeyboardButton(
            text=label,
            callback_data=f"hist_day:{slug}:{d.isoformat()}",
        )])

    rows.append([InlineKeyboardButton(
        text=T(lang, "btn_enter_date"),
        callback_data=f"hist_enter_date:{slug}",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_history_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=T(lang, "back"), callback_data="hist_back"),
    ]])
