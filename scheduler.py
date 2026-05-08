from __future__ import annotations

import logging
from datetime import datetime

import asyncpg
import pytz
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import db
from keyboards import start_analysis_kb
from texts import T

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="UTC")


async def _send_reminders(bot: Bot, pool: asyncpg.Pool) -> None:
    now_utc = datetime.now(pytz.UTC)
    subscriptions = await db.get_all_active_subscriptions(pool)

    for sub in subscriptions:
        try:
            tz = pytz.timezone(sub["timezone"])
        except Exception:
            continue

        now_local = now_utc.astimezone(tz)
        rt = sub["reminder_time"]

        if not (now_local.hour == rt.hour and now_local.minute == rt.minute):
            continue

        today = now_local.date()
        user_id = sub["user_id"]
        activity_type_id = sub["activity_type_id"]

        session = await db.get_session_by_date(pool, user_id, activity_type_id, today)
        if session:
            continue  # reminder already sent or session already done today

        await db.create_session(pool, user_id, activity_type_id, today)

        lang = await db.get_lang(pool, user_id)
        try:
            await bot.send_message(
                user_id,
                T(lang, "reminder_text"),
                reply_markup=start_analysis_kb(lang),
                parse_mode="HTML",
            )
            log.info("reminder sent user=%d activity=%d date=%s", user_id, activity_type_id, today)
        except TelegramForbiddenError:
            log.warning("user=%d blocked bot, deactivating subscription", user_id)
            await db.deactivate_subscription(pool, user_id, activity_type_id)
        except Exception as e:
            log.warning("reminder failed user=%d: %s", user_id, e)


def setup_scheduler(bot: Bot, pool: asyncpg.Pool) -> None:
    scheduler.add_job(_send_reminders, "cron", minute="*", args=[bot, pool])
    scheduler.start()
    log.info("Scheduler started")
