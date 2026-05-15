"""
DB integration tests — run against a real Postgres with schema.sql applied.

These catch:
- Column/schema drift (e.g. moving timezone from subscriptions to users)
- Broken upsert/conflict logic
- Stats arithmetic bugs around week/month windows
- JSON serialization in sessions.responses
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import pytest

import db


TP_SLUG = "thinking_pattern"


async def _activity_id(pool) -> int:
    row = await pool.fetchrow("SELECT id FROM activity_types WHERE slug = $1", TP_SLUG)
    return row["id"]


# ============================================================
# users
# ============================================================

async def test_upsert_user_creates_row(pool):
    await db.upsert_user(pool, 1, "alice", "Alice")
    row = await pool.fetchrow("SELECT * FROM users WHERE id = 1")
    assert row["username"] == "alice"
    assert row["first_name"] == "Alice"
    assert row["language"] == "uk"
    assert row["timezone"] == "Europe/Kyiv"


async def test_upsert_user_updates_existing(pool):
    await db.upsert_user(pool, 1, "alice", "Alice")
    await db.upsert_user(pool, 1, "alice2", "Alice 2")
    row = await pool.fetchrow("SELECT * FROM users WHERE id = 1")
    assert row["username"] == "alice2"
    assert row["first_name"] == "Alice 2"


async def test_set_and_get_lang(pool):
    await db.upsert_user(pool, 1, None, None)
    await db.set_lang(pool, 1, "ru")
    assert await db.get_lang(pool, 1) == "ru"


async def test_get_lang_defaults_to_uk_for_unknown_user(pool):
    assert await db.get_lang(pool, 9999) == "uk"


async def test_set_and_get_timezone(pool):
    await db.upsert_user(pool, 1, None, None)
    await db.set_timezone(pool, 1, "Europe/Moscow")
    assert await db.get_timezone(pool, 1) == "Europe/Moscow"


async def test_get_timezone_defaults_for_unknown_user(pool):
    assert await db.get_timezone(pool, 9999) == "Europe/Kyiv"


async def test_set_timezone_creates_user_if_missing(pool):
    """set_timezone uses INSERT … ON CONFLICT — must work for new users."""
    await db.set_timezone(pool, 42, "Europe/Berlin")
    assert await db.get_timezone(pool, 42) == "Europe/Berlin"


# ============================================================
# activities
# ============================================================

async def test_get_activity_types_returns_seeded_thinking_pattern(pool):
    rows = await db.get_activity_types(pool)
    slugs = [r["slug"] for r in rows]
    assert TP_SLUG in slugs


async def test_get_activity_by_slug_returns_record(pool):
    row = await db.get_activity_by_slug(pool, TP_SLUG)
    assert row is not None
    assert row["slug"] == TP_SLUG
    assert row["name_uk"]
    assert row["name_ru"]


async def test_get_activity_by_slug_unknown_returns_none(pool):
    row = await db.get_activity_by_slug(pool, "no_such_slug")
    assert row is None


# ============================================================
# subscriptions
# ============================================================

async def test_subscription_record_does_NOT_have_timezone_column(pool):
    """REGRESSION: timezone was moved from subscriptions to users. If a future
    refactor adds it back to subscriptions, this test fires — and any handler
    that grew used to sub['timezone'] starts being audited."""
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    await db.upsert_subscription(pool, 1, act_id, "09:00")
    sub = await db.get_subscription(pool, 1, act_id)
    assert sub is not None
    assert "timezone" not in sub.keys(), \
        "subscriptions.timezone reappeared — verify all callers were updated"


async def test_upsert_subscription_creates_active(pool):
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    await db.upsert_subscription(pool, 1, act_id, "09:30")
    sub = await db.get_subscription(pool, 1, act_id)
    assert sub["is_active"] is True
    assert sub["reminder_time"].strftime("%H:%M") == "09:30"


async def test_upsert_subscription_reactivates_after_unsub(pool):
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    await db.upsert_subscription(pool, 1, act_id, "09:00")
    await db.deactivate_subscription(pool, 1, act_id)
    await db.upsert_subscription(pool, 1, act_id, "10:00")
    sub = await db.get_subscription(pool, 1, act_id)
    assert sub["is_active"] is True
    assert sub["reminder_time"].strftime("%H:%M") == "10:00"


async def test_get_subscription_returns_none_when_absent(pool):
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    assert await db.get_subscription(pool, 1, act_id) is None


async def test_get_all_active_subscriptions_joins_user_timezone(pool):
    """Scheduler reads sub['timezone'] from THIS query (which joins users).
    REGRESSION-guard: the JOIN must stay or scheduler breaks."""
    await db.upsert_user(pool, 1, None, None)
    await db.set_timezone(pool, 1, "Asia/Tokyo")
    act_id = await _activity_id(pool)
    await db.upsert_subscription(pool, 1, act_id, "08:00")
    rows = await db.get_all_active_subscriptions(pool)
    assert len(rows) == 1
    assert rows[0]["timezone"] == "Asia/Tokyo"  # via JOIN


async def test_deactivate_filters_out_inactive_from_scheduler_query(pool):
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    await db.upsert_subscription(pool, 1, act_id, "08:00")
    await db.deactivate_subscription(pool, 1, act_id)
    rows = await db.get_all_active_subscriptions(pool)
    assert rows == []


# ============================================================
# sessions
# ============================================================

async def test_create_session_starts_incomplete(pool):
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    sess = await db.create_session(pool, 1, act_id, date(2026, 5, 15))
    assert sess["is_complete"] is False
    assert sess["responses"] is None


async def test_complete_session_stores_responses(pool):
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    sess = await db.create_session(pool, 1, act_id, date(2026, 5, 15))
    payload = {"irritation": 3, "idea": "rest"}
    await db.complete_session(pool, str(sess["id"]), payload)
    row = await db.get_session_by_date(pool, 1, act_id, date(2026, 5, 15))
    assert row["is_complete"] is True
    stored = json.loads(row["responses"]) if isinstance(row["responses"], str) else dict(row["responses"])
    assert stored == payload


async def test_update_session_responses_replaces_payload(pool):
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    sess = await db.create_session(pool, 1, act_id, date(2026, 5, 15))
    await db.complete_session(pool, str(sess["id"]), {"idea": "old"})
    await db.update_session_responses(pool, str(sess["id"]), {"idea": "new"})
    row = await db.get_session_by_date(pool, 1, act_id, date(2026, 5, 15))
    stored = json.loads(row["responses"]) if isinstance(row["responses"], str) else dict(row["responses"])
    assert stored == {"idea": "new"}


async def test_delete_session_removes_row(pool):
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    await db.create_session(pool, 1, act_id, date(2026, 5, 15))
    await db.delete_session(pool, 1, act_id, date(2026, 5, 15))
    assert await db.get_session_by_date(pool, 1, act_id, date(2026, 5, 15)) is None


async def test_delete_session_idempotent_for_missing_date(pool):
    """Should not raise even if there's nothing to delete."""
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    await db.delete_session(pool, 1, act_id, date(2026, 5, 15))  # no-op


async def test_reset_session_clears_responses_and_flag(pool):
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    sess = await db.create_session(pool, 1, act_id, date(2026, 5, 15))
    await db.complete_session(pool, str(sess["id"]), {"idea": "x"})
    await db.reset_session(pool, str(sess["id"]))
    row = await db.get_session_by_date(pool, 1, act_id, date(2026, 5, 15))
    assert row["is_complete"] is False
    assert row["responses"] is None


async def test_get_recent_sessions_orders_by_date_desc(pool):
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    for d in (date(2026, 5, 10), date(2026, 5, 13), date(2026, 5, 11)):
        await db.create_session(pool, 1, act_id, d)
    rows = await db.get_recent_sessions(pool, 1, act_id, limit=5)
    assert [r["session_date"] for r in rows] == [date(2026, 5, 13), date(2026, 5, 11), date(2026, 5, 10)]


async def test_get_recent_sessions_limit_respected(pool):
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    for i in range(10):
        await db.create_session(pool, 1, act_id, date(2026, 5, 1) + timedelta(days=i))
    rows = await db.get_recent_sessions(pool, 1, act_id, limit=3)
    assert len(rows) == 3


# ============================================================
# stats
# ============================================================

async def test_get_stats_returns_required_keys(pool):
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    await db.upsert_subscription(pool, 1, act_id, "09:00")
    stats = await db.get_stats(pool, 1, act_id, subscribed_at=datetime.utcnow())
    assert set(stats.keys()) == {"week_filled", "week_total", "month_filled", "month_total"}


async def test_get_stats_counts_completed_only(pool):
    """Incomplete sessions must NOT count toward filled stats."""
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    sub_at = datetime.utcnow() - timedelta(days=10)
    await db.upsert_subscription(pool, 1, act_id, "09:00")

    today = date.today()
    # 2 complete + 1 incomplete in last week
    s1 = await db.create_session(pool, 1, act_id, today - timedelta(days=1))
    s2 = await db.create_session(pool, 1, act_id, today - timedelta(days=2))
    await db.create_session(pool, 1, act_id, today - timedelta(days=3))
    await db.complete_session(pool, str(s1["id"]), {"x": 1})
    await db.complete_session(pool, str(s2["id"]), {"x": 1})

    stats = await db.get_stats(pool, 1, act_id, subscribed_at=sub_at)
    assert stats["week_filled"] == 2  # only the 2 completed
    assert stats["week_total"] == 7   # full week since sub older than week


async def test_get_stats_clamps_total_to_days_since_sub(pool):
    """If user just subscribed today, totals should be 1, not 7/30."""
    await db.upsert_user(pool, 1, None, None)
    act_id = await _activity_id(pool)
    sub_at = datetime.utcnow()
    stats = await db.get_stats(pool, 1, act_id, subscribed_at=sub_at)
    assert stats["week_total"] == 1
    assert stats["month_total"] == 1
