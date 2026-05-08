import logging

import asyncpg
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
from keyboards import lang_kb, main_kb
from texts import T

log = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    await state.clear()
    await db.upsert_user(pool, message.from_user.id, message.from_user.username, message.from_user.first_name)
    log.info("user=%d action=start", message.from_user.id)
    await message.answer(T("uk", "choose_lang"), reply_markup=lang_kb())


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = callback.data.split(":")[1]
    await db.set_lang(pool, callback.from_user.id, lang)
    log.info("user=%d action=set_lang lang=%s", callback.from_user.id, lang)
    try:
        await callback.message.edit_text(T(lang, "choose_lang"))
    except TelegramBadRequest:
        pass
    await callback.message.answer(T(lang, "welcome"), reply_markup=main_kb(lang))
    await callback.answer()
