import logging

import asyncpg
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
from keyboards import activities_kb, main_kb
from texts import T, BTN_ACTIVITIES, BTN_HISTORY, activity_name

log = logging.getLogger(__name__)
router = Router()


@router.message(F.text.in_(BTN_ACTIVITIES), StateFilter(None))
async def show_activities(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)
    activities = await db.get_activity_types(pool)
    if not activities:
        await message.answer(T(lang, "activities_empty"), reply_markup=main_kb(lang))
        return

    subs = await pool.fetch(
        "SELECT activity_type_id FROM subscriptions WHERE user_id = $1 AND is_active = TRUE",
        message.from_user.id,
    )
    sub_ids = {s["activity_type_id"] for s in subs}

    # Map activity_type_id → slug to build subscribed_slugs set
    subscribed_slugs = {act["slug"] for act in activities if act["id"] in sub_ids}

    await message.answer(
        T(lang, "activities_title"),
        reply_markup=activities_kb(lang, activities, subscribed_slugs),
        parse_mode="HTML",
    )


@router.message(F.text.in_(BTN_HISTORY), StateFilter(None))
async def show_history_entry(message: Message, pool: asyncpg.Pool) -> None:
    from handlers.history import send_history
    lang = await db.get_lang(pool, message.from_user.id)
    await send_history(message, pool, lang, message.from_user.id)
