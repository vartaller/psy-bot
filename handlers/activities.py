import json
import logging

import asyncpg
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
from keyboards import (
    activities_kb,
    activity_detail_kb,
    confirm_unsub_kb,
    reminder_time_webapp_kb,
    tz_webapp_kb,
)
from states import SubscribeStates
from texts import T, activity_name, activity_desc, tz_name, find_tz_by_current_time

log = logging.getLogger(__name__)
router = Router()


async def _show_activity_detail(target, pool: asyncpg.Pool, lang: str, slug: str, user_id: int) -> None:
    act = await db.get_activity_by_slug(pool, slug)
    if not act:
        return
    sub = await db.get_subscription(pool, user_id, act["id"])
    name = activity_name(lang, act)
    desc = activity_desc(lang, act)

    if sub and sub["is_active"]:
        t = sub["reminder_time"].strftime("%H:%M")
        tz = tz_name(lang, sub["timezone"])
        status = T(lang, "status_subscribed")
        reminder = "\n" + T(lang, "reminder_info", time=t, tz=tz)
    else:
        status = T(lang, "status_not_subscribed")
        reminder = ""

    text = f"<b>{name}</b>\n\n{desc}\n\n{status}{reminder}"
    kb = activity_detail_kb(lang, slug, sub)

    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest:
            await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


# --- Activities list ---

@router.callback_query(F.data == "act_list")
async def cb_act_list(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    activities = await db.get_activity_types(pool)
    subs = await pool.fetch(
        "SELECT activity_type_id FROM subscriptions WHERE user_id = $1 AND is_active = TRUE",
        callback.from_user.id,
    )
    sub_ids = {s["activity_type_id"] for s in subs}
    subscribed_slugs = {act["slug"] for act in activities if act["id"] in sub_ids}
    try:
        await callback.message.edit_text(
            T(lang, "activities_title"),
            reply_markup=activities_kb(lang, activities, subscribed_slugs),
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


# --- Activity detail ---

@router.callback_query(F.data.startswith("act_detail:"))
async def cb_act_detail(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    slug = callback.data.split(":", 1)[1]
    await _show_activity_detail(callback, pool, lang, slug, callback.from_user.id)


# --- Subscribe: show reminder time picker ---

@router.callback_query(F.data.startswith("sub:"))
async def cb_subscribe(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    slug = callback.data.split(":", 1)[1]
    await state.set_state(SubscribeStates.waiting_time)
    await state.update_data(slug=slug)
    await callback.message.answer(
        T(lang, "sub_ask_time"),
        reply_markup=reminder_time_webapp_kb(lang, slug),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("change_time:"))
async def cb_change_time(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    slug = callback.data.split(":", 1)[1]
    await state.set_state(SubscribeStates.waiting_time)
    await state.update_data(slug=slug)
    await callback.message.answer(
        T(lang, "sub_ask_time"),
        reply_markup=reminder_time_webapp_kb(lang, slug),
        parse_mode="HTML",
    )
    await callback.answer()


# --- Reminder time picked via Web App: ask current time for timezone ---

@router.message(StateFilter(SubscribeStates.waiting_time), F.web_app_data)
async def receive_reminder_time(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)

    try:
        payload = json.loads(message.web_app_data.data)
        hour = int(payload["hour"])
        minute = int(payload["minute"])
    except (KeyError, ValueError, TypeError):
        await message.answer(T(lang, "error"))
        return

    time_str = f"{hour:02d}:{minute:02d}"
    await state.update_data(time_str=time_str)
    await state.set_state(SubscribeStates.waiting_tz)

    await message.answer(
        T(lang, "sub_ask_tz_webapp"),
        reply_markup=tz_webapp_kb(lang),
        parse_mode="HTML",
    )


# --- Web App data received: detect timezone, save subscription ---

@router.message(StateFilter(SubscribeStates.waiting_tz), F.web_app_data)
async def receive_current_time(message: Message, state: FSMContext, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, message.from_user.id)

    try:
        payload = json.loads(message.web_app_data.data)
        hour = int(payload["hour"])
        minute = int(payload["minute"])
    except (KeyError, ValueError, TypeError):
        await message.answer(T(lang, "error"))
        return

    data = await state.get_data()
    slug = data.get("slug")
    time_str = data.get("time_str")
    await state.clear()

    if not slug or not time_str:
        await message.answer(T(lang, "error"))
        return

    timezone = find_tz_by_current_time(hour, minute)
    act = await db.get_activity_by_slug(pool, slug)
    if not act:
        return

    await db.upsert_subscription(pool, message.from_user.id, act["id"], time_str, timezone)
    tz_display = tz_name(lang, timezone)
    log.info("user=%d subscribed slug=%s time=%s tz=%s", message.from_user.id, slug, time_str, timezone)

    await message.answer(
        T(lang, "sub_tz_detected", tz=tz_display) + "\n\n" + T(lang, "sub_done", time=time_str, tz=tz_display),
        parse_mode="HTML",
    )
    await _show_activity_detail(message, pool, lang, slug, message.from_user.id)


# --- Unsubscribe ---

@router.callback_query(F.data.startswith("unsub:"))
async def cb_unsub(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    slug = callback.data.split(":", 1)[1]
    act = await db.get_activity_by_slug(pool, slug)
    name = activity_name(lang, act) if act else slug
    try:
        await callback.message.edit_text(
            T(lang, "unsub_confirm", name=name),
            reply_markup=confirm_unsub_kb(lang, slug),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("unsub_yes:"))
async def cb_unsub_yes(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    lang = await db.get_lang(pool, callback.from_user.id)
    slug = callback.data.split(":", 1)[1]
    act = await db.get_activity_by_slug(pool, slug)
    if act:
        await db.deactivate_subscription(pool, callback.from_user.id, act["id"])
    log.info("user=%d unsubscribed slug=%s", callback.from_user.id, slug)
    try:
        await callback.message.edit_text(T(lang, "unsub_done"))
    except TelegramBadRequest:
        pass
    await callback.answer()
    await _show_activity_detail(callback, pool, lang, slug, callback.from_user.id)
