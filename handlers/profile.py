import json
import logging

import asyncpg
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

import db
from keyboards import profile_kb, tz_webapp_kb, main_kb
from states import ProfileStates
from texts import T, BTN_PROFILE, find_tz_by_current_time, tz_name

log = logging.getLogger(__name__)
router = Router()


async def _show_profile(target, pool: asyncpg.Pool, lang: str, user_id: int) -> None:
    timezone = await db.get_timezone(pool, user_id)
    tz_display = tz_name(lang, timezone)
    text = T(lang, "profile_title", tz=tz_display)
    kb = profile_kb(lang, tz_display)

    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await target.answer()


# --- Open profile from main menu ---

@router.message(F.text.in_(BTN_PROFILE))
async def cmd_profile(message: Message, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)
    await _show_profile(message, pool, lang, message.from_user.id)


# --- Change timezone: show picker ---

@router.callback_query(F.data == "profile_change_tz")
async def cb_change_tz(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    await state.set_state(ProfileStates.waiting_tz)
    await callback.message.answer(
        T(lang, "profile_ask_tz"),
        reply_markup=tz_webapp_kb(lang),
        parse_mode="HTML",
    )
    await callback.answer()


# --- Timezone picked: save ---

@router.message(StateFilter(ProfileStates.waiting_tz), F.web_app_data)
async def receive_profile_tz(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)

    try:
        payload = json.loads(message.web_app_data.data)
        hour = int(payload["hour"])
        minute = int(payload["minute"])
    except (KeyError, ValueError, TypeError):
        await message.answer(T(lang, "error"))
        return

    timezone = find_tz_by_current_time(hour, minute)
    await db.set_timezone(pool, message.from_user.id, timezone)
    await state.clear()

    tz_display = tz_name(lang, timezone)
    log.info("user=%d action=change_tz tz=%s", message.from_user.id, timezone)

    await message.answer(
        T(lang, "tz_saved", tz=tz_display),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await _show_profile(message, pool, lang, message.from_user.id)
