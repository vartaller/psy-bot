from __future__ import annotations

import logging

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
    already_done_kb,
    choice_kb,
    scale_kb,
    text_cancel_kb,
)
from states import ThinkingPattern
from texts import T, format_tp_summary

log = logging.getLogger(__name__)
router = Router()

TP_SLUG = "thinking_pattern"


def _user_today(timezone: str):
    from datetime import datetime
    tz = pytz.timezone(timezone)
    return datetime.now(tz).date()


async def _start_tp_session(
    target: CallbackQuery | Message,
    state: FSMContext,
    pool: asyncpg.Pool,
    lang: str,
    user_id: int,
) -> None:
    act = await db.get_activity_by_slug(pool, TP_SLUG)
    if not act:
        return

    sub = await db.get_subscription(pool, user_id, act["id"])
    if not sub or not sub["is_active"]:
        text = T(lang, "tp_no_subscription")
        if isinstance(target, CallbackQuery):
            await target.message.answer(text)
            await target.answer()
        else:
            await target.answer(text)
        return

    tz = await db.get_timezone(pool, user_id)
    today = _user_today(tz)
    session = await db.get_session_by_date(pool, user_id, act["id"], today)

    if session and session["is_complete"]:
        text = T(lang, "tp_already_done")
        kb = already_done_kb(lang, TP_SLUG, today.isoformat())
        if isinstance(target, CallbackQuery):
            await target.message.answer(text, reply_markup=kb)
            await target.answer()
        else:
            await target.answer(text, reply_markup=kb)
        return

    if not session:
        session = await db.create_session(pool, user_id, act["id"], today)

    await state.set_state(ThinkingPattern.irritation)
    await state.update_data(
        session_id=str(session["id"]),
        activity_type_id=act["id"],
        session_date=today.isoformat(),
    )

    intro_text = T(lang, "tp_intro")
    step_text = T(lang, "tp_step_irritation")
    kb = scale_kb(lang, "irritation")

    if isinstance(target, CallbackQuery):
        await target.message.answer(intro_text, parse_mode="HTML")
        msg = await target.message.answer(step_text, reply_markup=kb, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(intro_text, parse_mode="HTML")
        msg = await target.answer(step_text, reply_markup=kb, parse_mode="HTML")

    await state.update_data(last_msg_id=msg.message_id)


# --- Entry points ---

@router.callback_query(F.data == f"start_session:{TP_SLUG}")
async def cb_start_session(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    await state.clear()
    lang = await db.get_lang(pool, callback.from_user.id)
    await _start_tp_session(callback, state, pool, lang, callback.from_user.id)


@router.callback_query(F.data.startswith(f"tp_redo:{TP_SLUG}:"))
async def cb_redo(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    date_str = callback.data.split(":")[-1]
    act = await db.get_activity_by_slug(pool, TP_SLUG)
    if act:
        from datetime import date
        session_date = date.fromisoformat(date_str)
        session = await db.get_session_by_date(pool, callback.from_user.id, act["id"], session_date)
        if session:
            await db.reset_session(pool, str(session["id"]))
    await state.clear()
    await _start_tp_session(callback, state, pool, lang, callback.from_user.id)


# --- Cancel (any TP state) ---

@router.callback_query(F.data == "tp_cancel", StateFilter(ThinkingPattern))
async def cb_cancel(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from texts import T as _T
    lang = await db.get_lang(pool, callback.from_user.id)
    await state.clear()
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=_T(lang, "back"), callback_data=f"act_detail:{TP_SLUG}"),
    ]])
    try:
        await callback.message.edit_text(T(lang, "tp_cancelled"), reply_markup=back_kb)
    except TelegramBadRequest:
        await callback.message.answer(T(lang, "tp_cancelled"), reply_markup=back_kb)
    await callback.answer()


# --- Helpers ---

async def _remove_last_kb(callback_or_msg, state: FSMContext) -> None:
    data = await state.get_data()
    last_id = data.get("last_msg_id")
    if last_id:
        try:
            await callback_or_msg.bot.edit_message_reply_markup(
                chat_id=callback_or_msg.chat.id
                if isinstance(callback_or_msg, Message)
                else callback_or_msg.message.chat.id,
                message_id=last_id,
                reply_markup=None,
            )
        except Exception:
            pass


async def _send_next(target: CallbackQuery | Message, state, lang: str, text: str, kb) -> None:
    if isinstance(target, CallbackQuery):
        msg = await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        msg = await target.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id)


# --- Step 1: Irritation (scale) ---

@router.callback_query(F.data.startswith("tp_scale:irritation:"), StateFilter(ThinkingPattern.irritation))
async def step_irritation(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    value = int(callback.data.split(":")[-1])
    lang = await db.get_lang(pool, callback.from_user.id)
    await state.update_data(irritation=value)
    try:
        await callback.message.edit_text(
            T(lang, "tp_step_irritation") + f"\n\n✅ {value}/5",
            reply_markup=None, parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await state.set_state(ThinkingPattern.excitement)
    await _send_next(callback, state, lang, T(lang, "tp_step_excitement"), scale_kb(lang, "excitement"))
    await callback.answer()


# --- Step 2: Excitement (scale) ---

@router.callback_query(F.data.startswith("tp_scale:excitement:"), StateFilter(ThinkingPattern.excitement))
async def step_excitement(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    value = int(callback.data.split(":")[-1])
    lang = await db.get_lang(pool, callback.from_user.id)
    await state.update_data(excitement=value)
    try:
        await callback.message.edit_text(
            T(lang, "tp_step_excitement") + f"\n\n✅ {value}/5",
            reply_markup=None, parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await state.set_state(ThinkingPattern.sensation)
    await _send_next(callback, state, lang, T(lang, "tp_step_sensation"), text_cancel_kb(lang))
    await callback.answer()


# --- Step 3: Sensation (text) ---

@router.message(StateFilter(ThinkingPattern.sensation))
async def step_sensation(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)
    await _remove_last_kb(message, state)
    await state.update_data(sensation=message.text)
    await state.set_state(ThinkingPattern.feeling)
    await _send_next(message, state, lang, T(lang, "tp_step_feeling"), choice_kb(lang, "feeling"))


# --- Step 4: Feeling (choice or custom) ---

@router.callback_query(F.data.startswith("tp_choice:feeling:"), StateFilter(ThinkingPattern.feeling))
async def step_feeling_choice(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    index = int(callback.data.split(":")[-1])
    options: list[str] = T(lang, "feelings")
    value = options[index] if index < len(options) else "—"
    await state.update_data(feeling=value)
    try:
        await callback.message.edit_text(
            T(lang, "tp_step_feeling") + f"\n\n✅ {value}",
            reply_markup=None, parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await state.set_state(ThinkingPattern.emotion)
    await _send_next(callback, state, lang, T(lang, "tp_step_emotion"), choice_kb(lang, "emotion"))
    await callback.answer()


@router.callback_query(F.data == "tp_custom:feeling", StateFilter(ThinkingPattern.feeling))
async def step_feeling_custom_start(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await state.set_state(ThinkingPattern.feeling_custom)
    await _send_next(callback, state, lang, T(lang, "tp_custom_prompt"), text_cancel_kb(lang))
    await callback.answer()


@router.message(StateFilter(ThinkingPattern.feeling_custom))
async def step_feeling_custom(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)
    await _remove_last_kb(message, state)
    await state.update_data(feeling=message.text)
    await state.set_state(ThinkingPattern.emotion)
    await _send_next(message, state, lang, T(lang, "tp_step_emotion"), choice_kb(lang, "emotion"))


# --- Step 5: Emotion (choice or custom) ---

@router.callback_query(F.data.startswith("tp_choice:emotion:"), StateFilter(ThinkingPattern.emotion))
async def step_emotion_choice(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    index = int(callback.data.split(":")[-1])
    options: list[str] = T(lang, "emotions")
    value = options[index] if index < len(options) else "—"
    await state.update_data(emotion=value)
    try:
        await callback.message.edit_text(
            T(lang, "tp_step_emotion") + f"\n\n✅ {value}",
            reply_markup=None, parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await state.set_state(ThinkingPattern.impression)
    await _send_next(callback, state, lang, T(lang, "tp_step_impression"), text_cancel_kb(lang))
    await callback.answer()


@router.callback_query(F.data == "tp_custom:emotion", StateFilter(ThinkingPattern.emotion))
async def step_emotion_custom_start(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await state.set_state(ThinkingPattern.emotion_custom)
    await _send_next(callback, state, lang, T(lang, "tp_custom_prompt"), text_cancel_kb(lang))
    await callback.answer()


@router.message(StateFilter(ThinkingPattern.emotion_custom))
async def step_emotion_custom(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)
    await _remove_last_kb(message, state)
    await state.update_data(emotion=message.text)
    await state.set_state(ThinkingPattern.impression)
    await _send_next(message, state, lang, T(lang, "tp_step_impression"), text_cancel_kb(lang))


# --- Step 6: Impression (text) ---

@router.message(StateFilter(ThinkingPattern.impression))
async def step_impression(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)
    await _remove_last_kb(message, state)
    await state.update_data(impression=message.text)
    await state.set_state(ThinkingPattern.meaning)
    await _send_next(message, state, lang, T(lang, "tp_step_meaning"), text_cancel_kb(lang))


# --- Step 7: Meaning (text) ---

@router.message(StateFilter(ThinkingPattern.meaning))
async def step_meaning(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)
    await _remove_last_kb(message, state)
    await state.update_data(meaning=message.text)
    await state.set_state(ThinkingPattern.idea)
    await _send_next(message, state, lang, T(lang, "tp_step_idea"), text_cancel_kb(lang))


# --- Step 8: Idea (text) — final step ---

@router.message(StateFilter(ThinkingPattern.idea))
async def step_idea(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)
    await _remove_last_kb(message, state)
    await state.update_data(idea=message.text)

    data = await state.get_data()
    await state.clear()

    plain = {
        "irritation": data["irritation"],
        "excitement": data["excitement"],
        "sensation":  data.get("sensation", ""),
        "feeling":    data.get("feeling", ""),
        "emotion":    data.get("emotion", ""),
        "impression": data.get("impression", ""),
        "meaning":    data.get("meaning", ""),
        "idea":       data.get("idea", ""),
    }

    # Encrypt all text fields before persisting
    uid = message.from_user.id
    encrypted = {
        "irritation": plain["irritation"],
        "excitement": plain["excitement"],
        "sensation":  config.encrypt(uid, plain["sensation"]),
        "feeling":    config.encrypt(uid, plain["feeling"]),
        "emotion":    config.encrypt(uid, plain["emotion"]),
        "impression": config.encrypt(uid, plain["impression"]),
        "meaning":    config.encrypt(uid, plain["meaning"]),
        "idea":       config.encrypt(uid, plain["idea"]),
    }

    session_id = data.get("session_id")
    if session_id:
        await db.complete_session(pool, session_id, encrypted)
        log.info("user=%d session=%s completed", uid, session_id)

    summary = format_tp_summary(lang, plain, data.get("session_date", ""))
    await message.answer(summary, parse_mode="HTML")


# --- noop for hint button ---

@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()
