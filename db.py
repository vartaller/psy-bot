from __future__ import annotations

import json
import logging
from datetime import date, time as time_type, timedelta

import asyncpg

log = logging.getLogger(__name__)

_lang_cache: dict[int, str] = {}
_activity_cache: dict[str, asyncpg.Record] = {}


# ---------- users ----------

async def upsert_user(pool: asyncpg.Pool, user_id: int, username: str | None, first_name: str | None) -> None:
    await pool.execute(
        """
        INSERT INTO users (id, username, first_name)
        VALUES ($1, $2, $3)
        ON CONFLICT (id) DO UPDATE SET username = $2, first_name = $3
        """,
        user_id, username, first_name,
    )


async def get_lang(pool: asyncpg.Pool, user_id: int) -> str:
    if user_id in _lang_cache:
        return _lang_cache[user_id]
    row = await pool.fetchrow("SELECT language FROM users WHERE id = $1", user_id)
    lang = row["language"] if row else "uk"
    _lang_cache[user_id] = lang
    return lang


async def set_lang(pool: asyncpg.Pool, user_id: int, lang: str) -> None:
    await pool.execute(
        "INSERT INTO users (id, language) VALUES ($1, $2) "
        "ON CONFLICT (id) DO UPDATE SET language = $2",
        user_id, lang,
    )
    _lang_cache[user_id] = lang


# ---------- activity types ----------

async def get_activity_types(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT * FROM activity_types WHERE is_active = TRUE ORDER BY id"
    )


async def get_activity_by_slug(pool: asyncpg.Pool, slug: str) -> asyncpg.Record | None:
    if slug in _activity_cache:
        return _activity_cache[slug]
    row = await pool.fetchrow(
        "SELECT * FROM activity_types WHERE slug = $1 AND is_active = TRUE", slug
    )
    if row:
        _activity_cache[slug] = row
    return row


# ---------- subscriptions ----------

async def get_subscription(pool: asyncpg.Pool, user_id: int, activity_type_id: int) -> asyncpg.Record | None:
    return await pool.fetchrow(
        "SELECT * FROM subscriptions WHERE user_id = $1 AND activity_type_id = $2",
        user_id, activity_type_id,
    )


async def upsert_subscription(
    pool: asyncpg.Pool,
    user_id: int,
    activity_type_id: int,
    reminder_time: str,
    timezone: str,
) -> None:
    h, m = map(int, reminder_time.split(":"))
    t = time_type(h, m)
    await pool.execute(
        """
        INSERT INTO subscriptions (user_id, activity_type_id, reminder_time, timezone, is_active)
        VALUES ($1, $2, $3, $4, TRUE)
        ON CONFLICT (user_id, activity_type_id)
        DO UPDATE SET reminder_time = $3, timezone = $4, is_active = TRUE, subscribed_at = NOW()
        """,
        user_id, activity_type_id, t, timezone,
    )


async def deactivate_subscription(pool: asyncpg.Pool, user_id: int, activity_type_id: int) -> None:
    await pool.execute(
        "UPDATE subscriptions SET is_active = FALSE WHERE user_id = $1 AND activity_type_id = $2",
        user_id, activity_type_id,
    )


async def get_all_active_subscriptions(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT s.*, u.id AS uid
        FROM subscriptions s
        JOIN users u ON u.id = s.user_id
        WHERE s.is_active = TRUE
        """
    )


# ---------- sessions ----------

async def get_session_by_date(
    pool: asyncpg.Pool,
    user_id: int,
    activity_type_id: int,
    session_date: date,
) -> asyncpg.Record | None:
    return await pool.fetchrow(
        "SELECT * FROM sessions WHERE user_id = $1 AND activity_type_id = $2 AND session_date = $3",
        user_id, activity_type_id, session_date,
    )


async def create_session(
    pool: asyncpg.Pool,
    user_id: int,
    activity_type_id: int,
    session_date: date,
) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        INSERT INTO sessions (user_id, activity_type_id, session_date, started_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (user_id, activity_type_id, session_date) DO UPDATE SET started_at = NOW()
        RETURNING *
        """,
        user_id, activity_type_id, session_date,
    )


async def complete_session(
    pool: asyncpg.Pool,
    session_id: str,
    responses: dict,
) -> None:
    await pool.execute(
        """
        UPDATE sessions
        SET is_complete = TRUE, completed_at = NOW(), responses = $2
        WHERE id = $1::uuid
        """,
        session_id, json.dumps(responses),
    )


async def reset_session(pool: asyncpg.Pool, session_id: str) -> None:
    await pool.execute(
        "UPDATE sessions SET is_complete = FALSE, responses = NULL, started_at = NOW() WHERE id = $1::uuid",
        session_id,
    )


async def get_recent_sessions(
    pool: asyncpg.Pool,
    user_id: int,
    activity_type_id: int,
    limit: int = 5,
) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT * FROM sessions
        WHERE user_id = $1 AND activity_type_id = $2
        ORDER BY session_date DESC
        LIMIT $3
        """,
        user_id, activity_type_id, limit,
    )


async def get_stats(
    pool: asyncpg.Pool,
    user_id: int,
    activity_type_id: int,
    subscribed_at,
) -> dict:
    today = date.today()
    sub_date = subscribed_at.date() if hasattr(subscribed_at, "date") else subscribed_at

    week_total  = min((today - sub_date).days + 1, 7)
    month_total = min((today - sub_date).days + 1, 30)
    week_start  = today - timedelta(days=week_total - 1)
    month_start = today - timedelta(days=month_total - 1)

    week_filled = await pool.fetchval(
        """
        SELECT COUNT(*) FROM sessions
        WHERE user_id=$1 AND activity_type_id=$2
          AND is_complete=TRUE AND session_date BETWEEN $3 AND $4
        """,
        user_id, activity_type_id, week_start, today,
    )
    month_filled = await pool.fetchval(
        """
        SELECT COUNT(*) FROM sessions
        WHERE user_id=$1 AND activity_type_id=$2
          AND is_complete=TRUE AND session_date BETWEEN $3 AND $4
        """,
        user_id, activity_type_id, month_start, today,
    )
    return {
        "week_filled": week_filled,
        "week_total": week_total,
        "month_filled": month_filled,
        "month_total": month_total,
    }
