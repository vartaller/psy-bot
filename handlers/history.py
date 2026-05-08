from __future__ import annotations

import json
import logging
from datetime import date

import asyncpg
import pytz
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import config
import db
from keyboards import back_to_history_kb, history_kb
from states import HistoryStates
from texts import T, activity_name, format_tp_body, tz_name

log = logging.getLogger(__name__)
router = Router()

TP_SLUG = "thinking_pattern"


def _user_today_from_sub(sub) -> date:
    try:
        tz = pytz.timezone(sub["timezone"])
        from datetime import datetime
        return datetime.now(tz).date()
    except Exception:
        return date.today()


async def send_history(
    target: Message | CallbackQuery,
    pool: asyncpg.Pool,
    lang: str,
    user_id: int,
) -> None:
    act = await db.get_activity_by_slug(pool, TP_SLUG)
    if not act:
        text = T(lang, "history_no_subs")
        if isinstance(target, Message):
            await target.answer(text)
        else:
            await target.message.answer(text)
            await target.answer()
        return

    sub = await db.get_subscription(pool, user_id, act["id"])
    if not sub or not sub["is_active"]:
        text = T(lang, "history_no_subs")
        if isinstance(target, Message):
            await target.answer(text)
        else:
            await target.message.answer(text)
            await target.answer()
        return

    today = _user_today_from_sub(sub)
    recent = await db.get_recent_sessions(pool, user_id, act["id"], limit=5)
    stats = await db.get_stats(pool, user_id, act["id"], sub["subscribed_at"])

    name = activity_name(lang, act)

    def pct(filled, total):
        return round(filled / total * 100) if total else 0

    stats_text = (
        T(lang, "week_stats",
          filled=stats["week_filled"], total=stats["week_total"],
          pct=pct(stats["week_filled"], stats["week_total"])) + "\n"
        + T(lang, "month_stats",
            filled=stats["month_filled"], total=stats["month_total"],
            pct=pct(stats["month_filled"], stats["month_total"]))
    )
    text = T(lang, "history_title", name=name) + "\n\n" + stats_text + T(lang, "history_select")
    kb = history_kb(lang, act["slug"], recent, today)

    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        try:
            await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest:
            await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await target.answer()


# --- History entry from activity detail screen ---

@router.callback_query(F.data.startswith("act_history:"))
async def cb_act_history(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    await send_history(callback, pool, lang, callback.from_user.id)


# --- History entry from callback (back button) ---

@router.callback_query(F.data == "hist_back")
async def cb_hist_back(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    await send_history(callback, pool, lang, callback.from_user.id)


# --- Day selected from history ---

@router.callback_query(F.data.startswith("hist_day:"))
async def cb_hist_day(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    parts = callback.data.split(":")
    slug = parts[1]
    date_str = parts[2]

    act = await db.get_activity_by_slug(pool, slug)
    if not act:
        await callback.answer()
        return

    session_date = date.fromisoformat(date_str)
    session = await db.get_session_by_date(pool, callback.from_user.id, act["id"], session_date)

    display_date = session_date.strftime("%d.%m.%Y")
    if not session or not session["is_complete"] or not session["responses"]:
        text = T(lang, "no_record_for_date", date=display_date)
        try:
            await callback.message.edit_text(
                text, reply_markup=back_to_history_kb(lang), parse_mode="HTML"
            )
        except TelegramBadRequest:
            await callback.message.answer(text, reply_markup=back_to_history_kb(lang), parse_mode="HTML")
        await callback.answer()
        return

    raw = session["responses"]
    responses = json.loads(raw) if isinstance(raw, str) else dict(raw)
    text_fields = ("sensation", "feeling", "emotion", "impression", "meaning", "idea")
    uid = callback.from_user.id
    for field in text_fields:
        if field in responses and isinstance(responses[field], str):
            responses[field] = config.safe_decrypt(uid, responses[field])

    full_text = T(lang, "record_header", date=display_date) + "\n\n" + format_tp_body(lang, responses)

    try:
        await callback.message.edit_text(
            full_text, reply_markup=back_to_history_kb(lang), parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback.message.answer(full_text, reply_markup=back_to_history_kb(lang), parse_mode="HTML")
    await callback.answer()


# --- Enter date manually ---

@router.callback_query(F.data.startswith("hist_enter_date:"))
async def cb_enter_date(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    slug = callback.data.split(":", 1)[1]
    await state.set_state(HistoryStates.waiting_date)
    await state.update_data(slug=slug)
    await callback.message.answer(T(lang, "date_ask"), parse_mode="HTML")
    await callback.answer()


@router.message(StateFilter(HistoryStates.waiting_date))
async def receive_date(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)
    text = (message.text or "").strip()

    try:
        day, month, year = text.split(".")
        session_date = date(int(year), int(month), int(day))
    except Exception:
        await message.answer(T(lang, "date_invalid"), parse_mode="HTML")
        return

    data = await state.get_data()
    await state.clear()
    slug = data.get("slug", TP_SLUG)

    # Reuse day callback logic
    fake_cb_data = f"hist_day:{slug}:{session_date.isoformat()}"

    act = await db.get_activity_by_slug(pool, slug)
    if not act:
        return

    session = await db.get_session_by_date(pool, message.from_user.id, act["id"], session_date)
    display_date = session_date.strftime("%d.%m.%Y")

    if not session or not session["is_complete"] or not session["responses"]:
        await message.answer(
            T(lang, "no_record_for_date", date=display_date),
            reply_markup=back_to_history_kb(lang),
            parse_mode="HTML",
        )
        return

    raw = session["responses"]
    responses = json.loads(raw) if isinstance(raw, str) else dict(raw)
    text_fields = ("sensation", "feeling", "emotion", "impression", "meaning", "idea")
    uid = message.from_user.id
    for field in text_fields:
        if field in responses and isinstance(responses[field], str):
            responses[field] = config.safe_decrypt(uid, responses[field])

    header = T(lang, "record_header", date=display_date)
    body = format_tp_summary(lang, responses, display_date)
    full_text = header + "\n\n" + body.split("\n", 1)[-1]

    await message.answer(full_text, reply_markup=back_to_history_kb(lang), parse_mode="HTML")
