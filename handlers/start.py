import json
import logging

import asyncpg
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import db
from keyboards import lang_kb, main_kb, tz_webapp_kb
from states import OnboardingStates
from texts import T, find_tz_by_current_time, tz_name

log = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    await state.clear()
    await db.upsert_user(pool, message.from_user.id, message.from_user.username, message.from_user.first_name)
    log.info("user=%d action=start", message.from_user.id)
    await message.answer(T("uk", "choose_lang"), reply_markup=lang_kb())


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = callback.data.split(":")[1]
    await db.set_lang(pool, callback.from_user.id, lang)
    log.info("user=%d action=set_lang lang=%s", callback.from_user.id, lang)
    try:
        await callback.message.edit_text(T(lang, "choose_lang"))
    except TelegramBadRequest:
        pass
    await state.set_state(OnboardingStates.waiting_tz)
    await callback.message.answer(
        T(lang, "onboarding_ask_tz"),
        reply_markup=tz_webapp_kb(lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StateFilter(OnboardingStates.waiting_tz), F.web_app_data)
async def receive_onboarding_tz(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
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
    log.info("user=%d action=set_tz tz=%s", message.from_user.id, timezone)

    await message.answer(
        T(lang, "onboarding_tz_saved", tz=tz_display),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await message.answer(T(lang, "welcome"), reply_markup=main_kb(lang))
