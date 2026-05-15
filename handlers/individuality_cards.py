"""
Individuality Cards activity — 3-step FSM, each step is a choice + custom text.
"""
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
from keyboards import choice_kb, text_cancel_kb
from states import IndividualityCards
from texts import T, format_summary

log = logging.getLogger(__name__)
router = Router()

IC_SLUG = "individuality_cards"
CALLBACK_PREFIX = "ic"
CANCEL_CB = "ic_cancel"

# Each step: (state, next_state, custom_state, prompt_key, options_key, field_name)
STEPS = [
    (IndividualityCards.q1, IndividualityCards.q2, IndividualityCards.q1_custom,
     "ic_step_q1", "ic_q1_options", "q1"),
    (IndividualityCards.q2, IndividualityCards.q3, IndividualityCards.q2_custom,
     "ic_step_q2", "ic_q2_options", "q2"),
    (IndividualityCards.q3, None, IndividualityCards.q3_custom,
     "ic_step_q3", "ic_q3_options", "q3"),
]


def _user_today(timezone: str):
    from datetime import datetime
    return datetime.now(pytz.timezone(timezone)).date()


async def _send_step(target: CallbackQuery | Message, lang: str, idx: int) -> None:
    _, _, _, prompt_key, options_key, field = STEPS[idx]
    text = T(lang, prompt_key)
    kb = choice_kb(lang, field, options_key=options_key,
                   callback_prefix=CALLBACK_PREFIX, cancel_callback=CANCEL_CB)
    if isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == f"start_session:{IC_SLUG}")
async def cb_start_session(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    await state.clear()
    lang = await db.get_lang(pool, callback.from_user.id)
    act = await db.get_activity_by_slug(pool, IC_SLUG)
    if not act:
        return

    sub = await db.get_subscription(pool, callback.from_user.id, act["id"])
    if not sub or not sub["is_active"]:
        await callback.message.answer(T(lang, "ic_no_subscription"))
        await callback.answer()
        return

    tz = await db.get_timezone(pool, callback.from_user.id)
    today = _user_today(tz)
    session = await db.get_session_by_date(pool, callback.from_user.id, act["id"], today)

    if session and session["is_complete"]:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        view_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=T(lang, "tp_btn_view"),
                                 callback_data=f"hist_day:{IC_SLUG}:{today.isoformat()}:view"),
        ]])
        await callback.message.answer(T(lang, "ic_already_done"), reply_markup=view_kb)
        await callback.answer()
        return

    if not session:
        session = await db.create_session(pool, callback.from_user.id, act["id"], today)

    await state.set_state(IndividualityCards.q1)
    await state.update_data(
        session_id=str(session["id"]),
        activity_type_id=act["id"],
        session_date=today.isoformat(),
    )

    await callback.message.answer(T(lang, "ic_intro"), parse_mode="HTML")
    await _send_step(callback, lang, 0)


async def _advance(target: CallbackQuery | Message, state: FSMContext,
                    pool: asyncpg.Pool, lang: str, idx: int, field: str, value: str) -> None:
    """Save value for step idx, move to next step or finish."""
    await state.update_data(**{field: value})
    _, next_state, _, _, _, _ = STEPS[idx]

    if next_state is not None:
        await state.set_state(next_state)
        await _send_step(target, lang, idx + 1)
        return

    # Final step → save and show summary
    data = await state.get_data()
    await state.clear()

    uid = (target.from_user.id if isinstance(target, Message) else target.from_user.id)
    plain = {"q1": data.get("q1", ""), "q2": data.get("q2", ""), "q3": data.get("q3", "")}
    encrypted = {k: config.encrypt(uid, v) for k, v in plain.items()}

    session_id = data.get("session_id")
    if session_id:
        await db.complete_session(pool, session_id, encrypted)
        log.info("user=%d IC session=%s completed", uid, session_id)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    lang = await db.get_lang(pool, uid)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=T(lang, "back"), callback_data=f"act_detail:{IC_SLUG}"),
    ]])
    summary = format_summary(IC_SLUG, lang, plain, data.get("session_date", ""))
    msg = target.message if isinstance(target, CallbackQuery) else target
    await msg.answer(summary, parse_mode="HTML", reply_markup=back_kb)


def _step_index_from_state(state_str: str | None) -> int | None:
    """Map current FSM state string → STEPS index."""
    if not state_str:
        return None
    for i, (s, _, _, _, _, _) in enumerate(STEPS):
        if state_str == s.state:
            return i
    return None


@router.callback_query(F.data.startswith(f"{CALLBACK_PREFIX}_choice:"),
                       StateFilter(IndividualityCards.q1, IndividualityCards.q2, IndividualityCards.q3))
async def cb_choice(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    parts = callback.data.split(":")
    field = parts[1]
    idx_in_options = int(parts[2])

    cur = await state.get_state()
    step_idx = _step_index_from_state(cur)
    if step_idx is None:
        return

    _, _, _, _, options_key, _ = STEPS[step_idx]
    options: list[str] = T(lang, options_key)
    value = options[idx_in_options] if 0 <= idx_in_options < len(options) else options[0]

    await callback.answer()
    await _advance(callback, state, pool, lang, step_idx, field, value)


@router.callback_query(F.data.startswith(f"{CALLBACK_PREFIX}_custom:"),
                       StateFilter(IndividualityCards.q1, IndividualityCards.q2, IndividualityCards.q3))
async def cb_custom(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    cur = await state.get_state()
    step_idx = _step_index_from_state(cur)
    if step_idx is None:
        return
    _, _, custom_state, _, _, _ = STEPS[step_idx]
    await state.set_state(custom_state)
    await callback.message.answer(T(lang, "tp_custom_prompt"), reply_markup=text_cancel_kb(lang))
    await callback.answer()


@router.message(StateFilter(IndividualityCards.q1_custom,
                            IndividualityCards.q2_custom,
                            IndividualityCards.q3_custom))
async def cb_custom_text(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)
    value = (message.text or "").strip()
    if not value:
        return

    cur = await state.get_state()
    # custom state name ends with "_custom" — strip to get the originating step state
    base_state = cur.replace("_custom", "") if cur else None
    step_idx = _step_index_from_state(base_state)
    if step_idx is None:
        return

    _, _, _, _, _, field = STEPS[step_idx]
    await _advance(message, state, pool, lang, step_idx, field, value)


@router.callback_query(F.data == CANCEL_CB,
                       StateFilter(IndividualityCards.q1, IndividualityCards.q2, IndividualityCards.q3,
                                   IndividualityCards.q1_custom, IndividualityCards.q2_custom,
                                   IndividualityCards.q3_custom))
async def cb_cancel(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    lang = await db.get_lang(pool, callback.from_user.id)
    await state.clear()
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=T(lang, "back"), callback_data=f"act_detail:{IC_SLUG}"),
    ]])
    try:
        await callback.message.edit_text(T(lang, "ic_cancelled"), reply_markup=back_kb)
    except TelegramBadRequest:
        await callback.message.answer(T(lang, "ic_cancelled"), reply_markup=back_kb)
    await callback.answer()
