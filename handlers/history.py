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
from keyboards import (
    back_to_hist_action_kb,
    back_to_history_kb,
    confirm_delete_kb,
    edit_choice_kb,
    edit_record_kb,
    edit_scale_kb,
    edit_text_cancel_kb,
    history_action_kb,
    history_kb,
)
from states import EditAnswer, HistoryStates
from texts import T, activity_name, format_tp_body, tz_name

log = logging.getLogger(__name__)
router = Router()

TP_SLUG = "thinking_pattern"

SCALE_FIELDS  = {"irritation", "excitement"}
CHOICE_FIELDS = {"feeling", "emotion"}
TEXT_FIELDS   = {"sensation", "impression", "meaning", "idea"}


async def _user_today_for(pool, user_id: int) -> date:
    from datetime import datetime
    tz_str = await db.get_timezone(pool, user_id)
    tz = pytz.timezone(tz_str)
    return datetime.now(tz).date()


async def _get_session_and_responses(
    pool: asyncpg.Pool,
    user_id: int,
    act_id: int,
    session_date: date,
) -> tuple | None:
    session = await db.get_session_by_date(pool, user_id, act_id, session_date)
    if not session or not session["is_complete"] or not session["responses"]:
        return None
    raw = session["responses"]
    responses = json.loads(raw) if isinstance(raw, str) else dict(raw)
    for field in TEXT_FIELDS | CHOICE_FIELDS:
        if field in responses and isinstance(responses[field], str):
            responses[field] = config.safe_decrypt(user_id, responses[field])
    return session, responses


# ---------- Action picker ----------

async def send_action_picker(
    target: CallbackQuery,
    pool: asyncpg.Pool,
    lang: str,
    user_id: int,
    slug: str,
) -> None:
    act = await db.get_activity_by_slug(pool, slug)
    if not act:
        await target.answer()
        return
    sub = await db.get_subscription(pool, user_id, act["id"])
    if not sub or not sub["is_active"]:
        await target.message.answer(T(lang, "history_no_subs"))
        await target.answer()
        return

    name = activity_name(lang, act)
    text = T(lang, "history_title", name=name) + "\n\n" + T(lang, "hist_action_title")
    kb = history_action_kb(lang, slug)
    try:
        await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await target.answer()


# ---------- Date picker ----------

async def send_history(
    target: Message | CallbackQuery,
    pool: asyncpg.Pool,
    lang: str,
    user_id: int,
    slug: str = TP_SLUG,
    action: str = "view",
) -> None:
    act = await db.get_activity_by_slug(pool, slug)
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

    today = await _user_today_for(pool, user_id)
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
    kb = history_kb(lang, act["slug"], recent, today, action)

    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        try:
            await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest:
            await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await target.answer()


# ---------- Edit record screen ----------

async def send_edit_record(
    target: CallbackQuery | Message,
    pool: asyncpg.Pool,
    lang: str,
    user_id: int,
    slug: str,
    date_str: str,
) -> None:
    act = await db.get_activity_by_slug(pool, slug)
    if not act:
        if isinstance(target, CallbackQuery):
            await target.answer()
        return

    session_date = date.fromisoformat(date_str)
    result = await _get_session_and_responses(pool, user_id, act["id"], session_date)
    display_date = session_date.strftime("%d.%m.%Y")

    if not result:
        text = T(lang, "no_record_for_date", date=display_date)
        kb = back_to_hist_action_kb(lang, slug, "edit")
        if isinstance(target, CallbackQuery):
            try:
                await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except TelegramBadRequest:
                await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
            await target.answer()
        else:
            await target.answer(text, reply_markup=kb, parse_mode="HTML")
        return

    _, responses = result
    text = T(lang, "hist_edit_title", date=display_date)
    kb = edit_record_kb(lang, slug, date_str, responses)

    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest:
            await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


# ============================================================
# Route: Мої записи → action picker
# ============================================================

@router.callback_query(F.data.startswith("act_history:"))
async def cb_act_history(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    slug = callback.data.split(":", 1)[1]
    await send_action_picker(callback, pool, lang, callback.from_user.id, slug)


# ============================================================
# Route: action selected → date picker
# ============================================================

@router.callback_query(F.data.startswith("hist_action:"))
async def cb_hist_action(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    parts = callback.data.split(":")
    slug = parts[1]
    action = parts[2]
    await send_history(callback, pool, lang, callback.from_user.id, slug, action)


# ============================================================
# Route: back button from day record (old-style)
# ============================================================

@router.callback_query(F.data == "hist_back")
async def cb_hist_back(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    await send_action_picker(callback, pool, lang, callback.from_user.id, TP_SLUG)


# ============================================================
# Route: day selected
# ============================================================

@router.callback_query(F.data.startswith("hist_day:"))
async def cb_hist_day(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    parts = callback.data.split(":")
    slug = parts[1]
    date_str = parts[2]
    action = parts[3] if len(parts) > 3 else "view"

    act = await db.get_activity_by_slug(pool, slug)
    if not act:
        await callback.answer()
        return

    session_date = date.fromisoformat(date_str)
    display_date = session_date.strftime("%d.%m.%Y")

    if action == "delete":
        text = T(lang, "hist_confirm_delete", date=display_date)
        kb = confirm_delete_kb(lang, slug, date_str)
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest:
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return

    if action == "edit":
        await send_edit_record(callback, pool, lang, callback.from_user.id, slug, date_str)
        return

    # view
    result = await _get_session_and_responses(pool, callback.from_user.id, act["id"], session_date)
    if not result:
        text = T(lang, "no_record_for_date", date=display_date)
        kb = back_to_hist_action_kb(lang, slug, "view")
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest:
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return

    _, responses = result
    full_text = T(lang, "record_header", date=display_date) + "\n\n" + format_tp_body(lang, responses)
    kb = back_to_hist_action_kb(lang, slug, "view")
    try:
        await callback.message.edit_text(full_text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        await callback.message.answer(full_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ============================================================
# Route: delete confirmed
# ============================================================

@router.callback_query(F.data.startswith("hist_delete_yes:"))
async def cb_hist_delete_yes(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    parts = callback.data.split(":")
    slug = parts[1]
    date_str = parts[2]

    act = await db.get_activity_by_slug(pool, slug)
    if act:
        session_date = date.fromisoformat(date_str)
        await db.delete_session(pool, callback.from_user.id, act["id"], session_date)

    text = T(lang, "hist_deleted")
    kb = back_to_hist_action_kb(lang, slug, "delete")
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ============================================================
# Route: edit field selected → show appropriate input KB
# ============================================================

@router.callback_query(F.data.startswith("hist_edit_field:"))
async def cb_hist_edit_field(
    callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool
) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    parts = callback.data.split(":")
    slug = parts[1]
    date_str = parts[2]
    field = parts[3]

    await state.set_state(EditAnswer.editing)
    await state.update_data(slug=slug, date_str=date_str, field=field, is_custom=False)

    if field in SCALE_FIELDS:
        kb = edit_scale_kb(lang, field)
        await callback.message.answer(T(lang, "hist_edit_field_ask"), reply_markup=kb)
    elif field in CHOICE_FIELDS:
        kb = edit_choice_kb(lang, field)
        await callback.message.answer(T(lang, "hist_edit_field_ask"), reply_markup=kb)
    else:
        kb = edit_text_cancel_kb(lang)
        await callback.message.answer(T(lang, "hist_edit_field_ask"), reply_markup=kb)
    await callback.answer()


# ============================================================
# Route: scale value selected during edit
# ============================================================

@router.callback_query(F.data.startswith("edit_scale:"), StateFilter(EditAnswer.editing))
async def cb_edit_scale(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    parts = callback.data.split(":")
    field = parts[1]
    value = int(parts[2])

    data = await state.get_data()
    await state.clear()
    await _save_field(callback, pool, lang, callback.from_user.id, data, field, value)


# ============================================================
# Route: choice selected during edit
# ============================================================

@router.callback_query(F.data.startswith("edit_choice:"), StateFilter(EditAnswer.editing))
async def cb_edit_choice(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    parts = callback.data.split(":")
    field = parts[1]
    idx = int(parts[2])
    options: list[str] = T(lang, f"{field}s")
    value = options[idx] if idx < len(options) else options[0]

    data = await state.get_data()
    await state.clear()
    await _save_field(callback, pool, lang, callback.from_user.id, data, field, value)


# ============================================================
# Route: "custom option" pressed → wait for text
# ============================================================

@router.callback_query(F.data.startswith("edit_custom:"), StateFilter(EditAnswer.editing))
async def cb_edit_custom(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    await state.update_data(is_custom=True)
    kb = edit_text_cancel_kb(lang)
    await callback.message.answer(T(lang, "tp_custom_prompt"), reply_markup=kb)
    await callback.answer()


# ============================================================
# Route: text message received during edit
# ============================================================

@router.message(StateFilter(EditAnswer.editing))
async def cb_edit_text(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)
    data = await state.get_data()
    field = data.get("field", "")

    if field not in TEXT_FIELDS and not data.get("is_custom"):
        return

    value = (message.text or "").strip()
    if not value:
        return

    await state.clear()
    await _save_field(message, pool, lang, message.from_user.id, data, field, value)


# ============================================================
# Route: cancel edit
# ============================================================

@router.callback_query(F.data == "edit_cancel", StateFilter(EditAnswer.editing))
async def cb_edit_cancel(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    data = await state.get_data()
    await state.clear()
    slug = data.get("slug", TP_SLUG)
    date_str = data.get("date_str", "")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await send_edit_record(callback, pool, lang, callback.from_user.id, slug, date_str)


# ============================================================
# Shared: save one field and refresh edit screen
# ============================================================

async def _save_field(
    target: CallbackQuery | Message,
    pool: asyncpg.Pool,
    lang: str,
    user_id: int,
    state_data: dict,
    field: str,
    value,
) -> None:
    slug = state_data.get("slug", TP_SLUG)
    date_str = state_data.get("date_str", "")

    act = await db.get_activity_by_slug(pool, slug)
    if not act:
        return

    session_date = date.fromisoformat(date_str)
    session = await db.get_session_by_date(pool, user_id, act["id"], session_date)
    if not session:
        return

    raw = session["responses"]
    responses = json.loads(raw) if isinstance(raw, str) else dict(raw)

    if field in TEXT_FIELDS | CHOICE_FIELDS and isinstance(value, str):
        responses[field] = config.encrypt(user_id, value)
    else:
        responses[field] = value

    await db.update_session_responses(pool, str(session["id"]), responses)

    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        await target.answer(T(lang, "hist_edit_saved"))

    await send_edit_record(target, pool, lang, user_id, slug, date_str)


# ============================================================
# Route: enter date manually
# ============================================================

@router.callback_query(F.data.startswith("hist_enter_date:"))
async def cb_enter_date(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    parts = callback.data.split(":")
    slug = parts[1]
    action = parts[2] if len(parts) > 2 else "view"
    await state.set_state(HistoryStates.waiting_date)
    await state.update_data(slug=slug, action=action)
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
    action = data.get("action", "view")
    date_str = session_date.isoformat()
    display_date = session_date.strftime("%d.%m.%Y")

    act = await db.get_activity_by_slug(pool, slug)
    if not act:
        return

    if action == "delete":
        text = T(lang, "hist_confirm_delete", date=display_date)
        kb = confirm_delete_kb(lang, slug, date_str)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
        return

    if action == "edit":
        await send_edit_record(message, pool, lang, message.from_user.id, slug, date_str)
        return

    # view
    result = await _get_session_and_responses(pool, message.from_user.id, act["id"], session_date)
    if not result:
        await message.answer(
            T(lang, "no_record_for_date", date=display_date),
            reply_markup=back_to_hist_action_kb(lang, slug, "view"),
            parse_mode="HTML",
        )
        return

    _, responses = result
    full_text = T(lang, "record_header", date=display_date) + "\n\n" + format_tp_body(lang, responses)
    await message.answer(
        full_text,
        reply_markup=back_to_hist_action_kb(lang, slug, "view"),
        parse_mode="HTML",
    )
