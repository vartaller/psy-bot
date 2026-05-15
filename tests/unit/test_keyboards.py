"""
Tests for keyboards.py — callback_data shape and structure.

These catch:
- callback_data over Telegram's 64-byte limit
- accidentally broken callbacks (e.g. spaces, mismatched prefixes)
- structural KB regressions (missing back button, wrong number of options)
"""
from __future__ import annotations

from datetime import date

import pytest

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

import keyboards


MAX_CALLBACK_LEN = 64


def _all_callback_data(kb: InlineKeyboardMarkup) -> list[str]:
    out = []
    for row in kb.inline_keyboard:
        for btn in row:
            if btn.callback_data is not None:
                out.append(btn.callback_data)
    return out


def _validate_callbacks(kb: InlineKeyboardMarkup):
    """Every callback must encode in <=64 UTF-8 bytes (Telegram limit)."""
    for cd in _all_callback_data(kb):
        encoded = cd.encode("utf-8")
        assert len(encoded) <= MAX_CALLBACK_LEN, (
            f"callback_data {cd!r} is {len(encoded)} bytes (limit {MAX_CALLBACK_LEN})"
        )
        assert " " not in cd, f"callback_data contains space: {cd!r}"


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_lang_kb(lang):
    kb = keyboards.lang_kb()
    _validate_callbacks(kb)
    assert _all_callback_data(kb) == ["lang:uk", "lang:ru"]


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_main_kb_has_two_rows(lang):
    kb = keyboards.main_kb(lang)
    assert isinstance(kb, ReplyKeyboardMarkup)
    assert len(kb.keyboard) == 2


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_scale_kb_has_five_values_and_cancel(lang):
    kb = keyboards.scale_kb(lang, "irritation")
    _validate_callbacks(kb)
    callbacks = _all_callback_data(kb)
    for i in range(1, 6):
        assert f"tp_scale:irritation:{i}" in callbacks
    assert "tp_cancel" in callbacks


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_choice_kb_has_custom_and_cancel(lang):
    kb = keyboards.choice_kb(lang, "feeling")
    _validate_callbacks(kb)
    callbacks = _all_callback_data(kb)
    assert "tp_custom:feeling" in callbacks
    assert "tp_cancel" in callbacks


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_history_kb_includes_action_in_callbacks(lang):
    sessions = [
        {"session_date": date(2026, 5, 10), "is_complete": True},
        {"session_date": date(2026, 5, 11), "is_complete": False},
    ]
    kb = keyboards.history_kb(lang, "thinking_pattern", sessions, date(2026, 5, 15), action="edit")
    _validate_callbacks(kb)
    callbacks = _all_callback_data(kb)
    assert any(c == "hist_day:thinking_pattern:2026-05-10:edit" for c in callbacks)
    assert any(c == "hist_day:thinking_pattern:2026-05-11:edit" for c in callbacks)
    assert "hist_enter_date:thinking_pattern:edit" in callbacks
    assert "hist_action:thinking_pattern:edit" in callbacks  # back button


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_history_action_kb_has_three_actions(lang):
    kb = keyboards.history_action_kb(lang, "thinking_pattern")
    _validate_callbacks(kb)
    callbacks = _all_callback_data(kb)
    assert "hist_action:thinking_pattern:view"   in callbacks
    assert "hist_action:thinking_pattern:edit"   in callbacks
    assert "hist_action:thinking_pattern:delete" in callbacks


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_edit_record_kb_has_button_per_field(lang):
    responses = {
        "irritation": 3, "excitement": 4,
        "sensation": "x", "feeling": "y", "emotion": "z",
        "impression": "a", "meaning": "b", "idea": "c",
    }
    kb = keyboards.edit_record_kb(lang, "thinking_pattern", "2026-05-15", responses)
    _validate_callbacks(kb)
    callbacks = _all_callback_data(kb)
    for field in ("irritation", "excitement", "sensation", "feeling",
                  "emotion", "impression", "meaning", "idea"):
        assert f"hist_edit_field:thinking_pattern:2026-05-15:{field}" in callbacks


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_confirm_delete_kb_yes_no(lang):
    kb = keyboards.confirm_delete_kb(lang, "thinking_pattern", "2026-05-15")
    _validate_callbacks(kb)
    callbacks = _all_callback_data(kb)
    assert "hist_delete_yes:thinking_pattern:2026-05-15" in callbacks
    # "No" goes back to delete date picker
    assert "hist_action:thinking_pattern:delete" in callbacks


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_edit_record_kb_truncates_long_text(lang):
    """Long answer text in the button label must not blow the 64-byte limit
    (callback_data is bounded; button text is bounded by Telegram client UI)."""
    responses = {f: "x" * 500 for f in ("sensation", "feeling", "emotion",
                                         "impression", "meaning", "idea")}
    responses["irritation"] = 3
    responses["excitement"] = 3
    kb = keyboards.edit_record_kb(lang, "thinking_pattern", "2026-05-15", responses)
    _validate_callbacks(kb)
    # button text should be capped
    for row in kb.inline_keyboard:
        for btn in row:
            assert len(btn.text) < 100


def test_activity_detail_kb_subscribed_shows_full_set():
    """Subscribed user sees Start Now + Records + Change Reminder + Unsubscribe + Back."""
    from datetime import time as time_type

    sub = {"is_active": True, "reminder_time": time_type(9, 0)}
    kb = keyboards.activity_detail_kb("uk", "thinking_pattern", sub)
    callbacks = _all_callback_data(kb)
    assert "start_session:thinking_pattern" in callbacks
    assert "act_history:thinking_pattern" in callbacks
    assert "change_time:thinking_pattern" in callbacks
    assert "unsub:thinking_pattern" in callbacks
    assert "act_list" in callbacks


def test_activity_detail_kb_unsubscribed_shows_subscribe():
    kb = keyboards.activity_detail_kb("uk", "thinking_pattern", None)
    callbacks = _all_callback_data(kb)
    assert "sub:thinking_pattern" in callbacks
    assert "act_list" in callbacks


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_edit_record_kb_for_individuality_cards(lang):
    """Schema-driven edit KB must produce one row per field for a different activity."""
    responses = {"q1": "Відповідь 1", "q2": "своє", "q3": "Відповідь 2"}
    kb = keyboards.edit_record_kb(lang, "individuality_cards", "2026-05-15", responses)
    _validate_callbacks(kb)
    callbacks = _all_callback_data(kb)
    for q in ("q1", "q2", "q3"):
        assert f"hist_edit_field:individuality_cards:2026-05-15:{q}" in callbacks
    assert "hist_action:individuality_cards:edit" in callbacks


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_choice_kb_with_explicit_options_key_and_prefix(lang):
    """New activity uses non-legacy options key + custom callback prefix."""
    kb = keyboards.choice_kb(lang, "q1", options_key="ic_q1_options",
                             callback_prefix="ic", cancel_callback="ic_cancel")
    _validate_callbacks(kb)
    callbacks = _all_callback_data(kb)
    assert any(c.startswith("ic_choice:q1:") for c in callbacks)
    assert "ic_custom:q1" in callbacks
    assert "ic_cancel" in callbacks
