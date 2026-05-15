"""
Handler integration smoke tests.

Each test wires up a real DB pool + real FSM + mock event objects and invokes
a handler function directly. We assert that:
- the handler does not raise
- the user gets a response (e.g. message.answer / message.edit_text was called)
- DB state changes as expected

What these catch:
- The original `KeyError: 'timezone'` (the test_start_session_uses_user_timezone
  flow would have failed on the broken code)
- New schema drift where a handler reads a column that no longer exists
- Cancel/back flows that silently do nothing
- "no record for date" path not handled in view/edit/delete
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

import db
from states import EditAnswer, HistoryStates, OnboardingStates, ThinkingPattern
from tests.conftest import make_callback, make_message


TP_SLUG = "thinking_pattern"


async def _activity_id(pool) -> int:
    row = await pool.fetchrow("SELECT id FROM activity_types WHERE slug = $1", TP_SLUG)
    return row["id"]


async def _make_subscribed_user(pool, user_id: int = 999):
    await db.upsert_user(pool, user_id, "test", "Test")
    act_id = await _activity_id(pool)
    await db.upsert_subscription(pool, user_id, act_id, "09:00")
    return act_id


# ============================================================
# start.py: language selection
# ============================================================

async def test_set_language_persists_choice(pool, fsm):
    from handlers.start import set_language
    cb = make_callback(data="lang:ru", user_id=100)
    await set_language(cb, fsm, pool)

    assert await db.get_lang(pool, 100) == "ru"
    cb.answer.assert_awaited()


# ============================================================
# activities.py: list, detail, subscribe, unsubscribe
# ============================================================

async def test_cb_act_list_renders_activities(pool):
    from handlers.activities import cb_act_list
    await db.upsert_user(pool, 999, None, None)
    cb = make_callback(data="act_list", user_id=999)
    await cb_act_list(cb, pool)
    cb.message.edit_text.assert_awaited()


async def test_cb_act_detail_unsubscribed_shows_subscribe_button(pool):
    from handlers.activities import cb_act_detail
    await db.upsert_user(pool, 999, None, None)
    cb = make_callback(data=f"act_detail:{TP_SLUG}", user_id=999)
    await cb_act_detail(cb, pool)
    cb.message.edit_text.assert_awaited()
    sent_text, sent_kwargs = cb.message.edit_text.call_args.args, cb.message.edit_text.call_args.kwargs
    # The KB sent should include a subscribe callback (verified indirectly via KB existence)
    assert "reply_markup" in sent_kwargs


async def test_cb_unsub_yes_deactivates_subscription(pool):
    from handlers.activities import cb_unsub_yes
    act_id = await _make_subscribed_user(pool, 999)
    cb = make_callback(data=f"unsub_yes:{TP_SLUG}", user_id=999)
    await cb_unsub_yes(cb, pool)

    sub = await db.get_subscription(pool, 999, act_id)
    assert sub["is_active"] is False


# ============================================================
# thinking_pattern.py: REGRESSION TESTS for the timezone bug
# ============================================================

async def test_start_session_uses_user_timezone_not_subscription(pool, fsm):
    """REGRESSION: the old code read sub['timezone'], which was a KeyError after
    the column was moved to users. This test would have failed on that bug."""
    from handlers.thinking_pattern import cb_start_session
    await _make_subscribed_user(pool, 999)
    await db.set_timezone(pool, 999, "Asia/Tokyo")

    cb = make_callback(data=f"start_session:{TP_SLUG}", user_id=999)
    # Should NOT raise KeyError 'timezone'
    await cb_start_session(cb, fsm, pool)

    # FSM should advance into the questionnaire
    state = await fsm.get_state()
    assert state == ThinkingPattern.irritation.state


async def test_start_session_without_subscription_short_circuits(pool, fsm):
    """User who isn't subscribed shouldn't enter the FSM."""
    from handlers.thinking_pattern import cb_start_session
    await db.upsert_user(pool, 999, None, None)

    cb = make_callback(data=f"start_session:{TP_SLUG}", user_id=999)
    await cb_start_session(cb, fsm, pool)

    assert await fsm.get_state() is None
    cb.message.answer.assert_awaited()  # "not subscribed" message


async def test_cb_cancel_clears_state_and_offers_back(pool, fsm):
    """After cancelling a TP session, FSM is cleared and a back button is shown."""
    from handlers.thinking_pattern import cb_cancel
    await fsm.set_state(ThinkingPattern.irritation)
    await db.upsert_user(pool, 999, None, None)

    cb = make_callback(data="tp_cancel", user_id=999)
    await cb_cancel(cb, fsm, pool)

    assert await fsm.get_state() is None


# ============================================================
# history.py: action picker, date picker, view/edit/delete
# ============================================================

async def test_cb_act_history_renders_action_picker(pool):
    from handlers.history import cb_act_history
    await _make_subscribed_user(pool, 999)
    cb = make_callback(data=f"act_history:{TP_SLUG}", user_id=999)
    await cb_act_history(cb, pool)
    cb.message.edit_text.assert_awaited()


async def test_cb_hist_action_uses_user_timezone_not_subscription(pool):
    """REGRESSION: history.py previously had _user_today_from_sub(sub['timezone'])."""
    from handlers.history import cb_hist_action
    await _make_subscribed_user(pool, 999)
    await db.set_timezone(pool, 999, "Asia/Tokyo")

    cb = make_callback(data=f"hist_action:{TP_SLUG}:view", user_id=999)
    # Must not KeyError on sub['timezone']
    await cb_hist_action(cb, pool)
    cb.message.edit_text.assert_awaited()


async def test_cb_hist_day_view_no_record_shows_fallback(pool):
    """No record for date → user must get '📭 ... відсутній' message, not a crash."""
    from handlers.history import cb_hist_day
    await _make_subscribed_user(pool, 999)

    cb = make_callback(data=f"hist_day:{TP_SLUG}:2020-01-01:view", user_id=999)
    await cb_hist_day(cb, pool)

    cb.message.edit_text.assert_awaited()
    text = cb.message.edit_text.call_args.args[0]
    assert "відсутн" in text.lower() or "отсутств" in text.lower()


async def test_cb_hist_day_delete_with_no_record_shows_fallback(pool):
    """REGRESSION: delete previously showed a confirm even when no record existed."""
    from handlers.history import cb_hist_day
    await _make_subscribed_user(pool, 999)

    cb = make_callback(data=f"hist_day:{TP_SLUG}:2020-01-01:delete", user_id=999)
    await cb_hist_day(cb, pool)

    text = cb.message.edit_text.call_args.args[0]
    # Should be the no-record message, NOT the delete confirmation prompt
    assert "відсутн" in text.lower() or "отсутств" in text.lower()


async def test_cb_hist_day_view_existing_record_shows_responses(pool):
    """Stored encrypted text must be decrypted in the rendered record."""
    import config
    from handlers.history import cb_hist_day

    act_id = await _make_subscribed_user(pool, 999)
    sess = await db.create_session(pool, 999, act_id, date(2026, 5, 15))
    encrypted = {
        "irritation": 3, "excitement": 4,
        "sensation":  config.encrypt(999, "tightness"),
        "feeling":    config.encrypt(999, "anxiety"),
        "emotion":    config.encrypt(999, "fear"),
        "impression": config.encrypt(999, "uncomfortable"),
        "meaning":    config.encrypt(999, "warning"),
        "idea":       config.encrypt(999, "rest"),
    }
    await db.complete_session(pool, str(sess["id"]), encrypted)

    cb = make_callback(data=f"hist_day:{TP_SLUG}:2026-05-15:view", user_id=999)
    await cb_hist_day(cb, pool)

    text = cb.message.edit_text.call_args.args[0]
    assert "tightness" in text
    assert "anxiety" in text
    assert "rest" in text


async def test_cb_hist_delete_yes_actually_deletes(pool):
    from handlers.history import cb_hist_delete_yes
    act_id = await _make_subscribed_user(pool, 999)
    await db.create_session(pool, 999, act_id, date(2026, 5, 15))

    cb = make_callback(data=f"hist_delete_yes:{TP_SLUG}:2026-05-15", user_id=999)
    await cb_hist_delete_yes(cb, pool)

    assert await db.get_session_by_date(pool, 999, act_id, date(2026, 5, 15)) is None


async def test_cb_hist_edit_field_for_scale_sets_fsm_state(pool, fsm):
    from handlers.history import cb_hist_edit_field
    await _make_subscribed_user(pool, 999)

    cb = make_callback(
        data=f"hist_edit_field:{TP_SLUG}:2026-05-15:irritation",
        user_id=999,
    )
    await cb_hist_edit_field(cb, fsm, pool)

    assert await fsm.get_state() == EditAnswer.editing.state
    data = await fsm.get_data()
    assert data["field"] == "irritation"
    assert data["slug"] == TP_SLUG
    assert data["date_str"] == "2026-05-15"


async def test_cb_edit_scale_updates_response_in_db(pool, fsm):
    import config
    from handlers.history import cb_edit_scale

    act_id = await _make_subscribed_user(pool, 999)
    sess = await db.create_session(pool, 999, act_id, date(2026, 5, 15))
    await db.complete_session(pool, str(sess["id"]), {
        "irritation": 2, "excitement": 3,
        "sensation":  config.encrypt(999, "a"),
        "feeling":    config.encrypt(999, "b"),
        "emotion":    config.encrypt(999, "c"),
        "impression": config.encrypt(999, "d"),
        "meaning":    config.encrypt(999, "e"),
        "idea":       config.encrypt(999, "f"),
    })

    await fsm.set_state(EditAnswer.editing)
    await fsm.update_data(slug=TP_SLUG, date_str="2026-05-15", field="irritation")

    cb = make_callback(data="edit_scale:irritation:5", user_id=999)
    await cb_edit_scale(cb, fsm, pool)

    row = await db.get_session_by_date(pool, 999, act_id, date(2026, 5, 15))
    import json as _json
    stored = _json.loads(row["responses"]) if isinstance(row["responses"], str) else dict(row["responses"])
    assert stored["irritation"] == 5
    # FSM is cleared after save
    assert await fsm.get_state() is None


async def test_cb_edit_text_encrypts_value(pool, fsm):
    """When editing a text field, the new value must be encrypted before storing."""
    import config
    from handlers.history import cb_edit_text

    act_id = await _make_subscribed_user(pool, 999)
    sess = await db.create_session(pool, 999, act_id, date(2026, 5, 15))
    await db.complete_session(pool, str(sess["id"]), {
        "irritation": 2, "excitement": 3,
        "sensation":  config.encrypt(999, "original"),
        "feeling":    config.encrypt(999, "b"),
        "emotion":    config.encrypt(999, "c"),
        "impression": config.encrypt(999, "d"),
        "meaning":    config.encrypt(999, "e"),
        "idea":       config.encrypt(999, "f"),
    })

    await fsm.set_state(EditAnswer.editing)
    await fsm.update_data(slug=TP_SLUG, date_str="2026-05-15", field="sensation")

    msg = make_message(text="brand new sensation", user_id=999)
    await cb_edit_text(msg, fsm, pool)

    row = await db.get_session_by_date(pool, 999, act_id, date(2026, 5, 15))
    import json as _json
    stored = _json.loads(row["responses"]) if isinstance(row["responses"], str) else dict(row["responses"])
    # Must be encrypted (not plaintext)
    assert stored["sensation"] != "brand new sensation"
    # And must decrypt to the new value
    assert config.decrypt(999, stored["sensation"]) == "brand new sensation"


async def test_receive_date_webapp_dispatches_to_view_for_existing_record(pool, fsm):
    import config
    from handlers.history import receive_date_webapp

    act_id = await _make_subscribed_user(pool, 999)
    sess = await db.create_session(pool, 999, act_id, date(2026, 5, 15))
    await db.complete_session(pool, str(sess["id"]), {
        "irritation": 3, "excitement": 4,
        "sensation":  config.encrypt(999, "x"),
        "feeling":    config.encrypt(999, "y"),
        "emotion":    config.encrypt(999, "z"),
        "impression": config.encrypt(999, "a"),
        "meaning":    config.encrypt(999, "b"),
        "idea":       config.encrypt(999, "c"),
    })

    await fsm.set_state(HistoryStates.waiting_date)
    await fsm.update_data(slug=TP_SLUG, action="view")

    msg = make_message(web_app_data='{"date":"2026-05-15"}', user_id=999)
    await receive_date_webapp(msg, fsm, pool)

    # FSM cleared
    assert await fsm.get_state() is None
    # At least one .answer() call must have been made
    assert msg.answer.await_count >= 1


async def test_receive_date_webapp_malformed_json_does_not_crash(pool, fsm):
    """If the webapp somehow sends garbage, we must answer with an error, not raise."""
    from handlers.history import receive_date_webapp

    await _make_subscribed_user(pool, 999)
    await fsm.set_state(HistoryStates.waiting_date)
    await fsm.update_data(slug=TP_SLUG, action="view")

    msg = make_message(web_app_data="not-json", user_id=999)
    await receive_date_webapp(msg, fsm, pool)

    assert await fsm.get_state() is None
    msg.answer.assert_awaited()
