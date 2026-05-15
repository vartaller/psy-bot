"""
Tests for texts.py — i18n table integrity and the T() lookup helper.

These catch:
- Missing keys in either language (causes KeyError at runtime)
- Mismatched format placeholders between uk/ru (breaks .format())
- Missing list options (feelings/emotions) that the KB iterates over
"""
from __future__ import annotations

import re

import pytest

from texts import T, TEXTS


REQUIRED_LANGS = ("uk", "ru")


def test_both_languages_present():
    for lang in REQUIRED_LANGS:
        assert lang in TEXTS, f"Missing language: {lang}"


def test_all_keys_exist_in_both_languages():
    """Catches when a new key is added in one lang but forgotten in another."""
    uk_keys = set(TEXTS["uk"].keys())
    ru_keys = set(TEXTS["ru"].keys())
    only_uk = uk_keys - ru_keys
    only_ru = ru_keys - uk_keys
    assert not only_uk, f"Keys present in uk but missing in ru: {only_uk}"
    assert not only_ru, f"Keys present in ru but missing in uk: {only_ru}"


def _placeholders(value) -> set[str]:
    """Extract {name} / {0} placeholders from a string template."""
    if not isinstance(value, str):
        return set()
    # Named placeholders only — positional are intentionally allowed to differ.
    return set(re.findall(r"\{([a-zA-Z_]\w*)\}", value))


def test_format_placeholders_match_across_languages():
    """{tz}, {date}, {name}, etc. must be present in both translations."""
    for key in TEXTS["uk"]:
        uk_val = TEXTS["uk"][key]
        ru_val = TEXTS["ru"][key]
        uk_ph = _placeholders(uk_val)
        ru_ph = _placeholders(ru_val)
        assert uk_ph == ru_ph, (
            f"Placeholder mismatch in key={key!r}: uk={uk_ph}, ru={ru_ph}"
        )


def test_feelings_and_emotions_are_lists():
    """choice_kb() iterates over these; if they're not lists or are empty, KB breaks."""
    for lang in REQUIRED_LANGS:
        assert isinstance(TEXTS[lang]["feelings"], list)
        assert isinstance(TEXTS[lang]["emotions"], list)
        assert len(TEXTS[lang]["feelings"]) >= 4
        assert len(TEXTS[lang]["emotions"]) >= 4


def test_tp_field_labels_is_dict_with_all_fields():
    """format_tp_body() does labels[field] — missing label → KeyError."""
    required_fields = {"irritation", "excitement", "sensation",
                       "feeling", "emotion", "impression", "meaning", "idea"}
    for lang in REQUIRED_LANGS:
        labels = TEXTS[lang]["tp_field_labels"]
        assert isinstance(labels, dict)
        missing = required_fields - set(labels.keys())
        assert not missing, f"Missing labels in {lang}: {missing}"


def test_T_substitutes_named_kwargs():
    out = T("uk", "tz_saved", tz="Europe/Kyiv")
    assert "Europe/Kyiv" in out


def test_T_substitutes_positional_args():
    out = T("uk", "tp_summary_header", "15.05.2026")
    assert "15.05.2026" in out


def test_T_returns_non_string_unchanged():
    """T() returns lists/dicts directly without formatting."""
    feelings = T("uk", "feelings")
    assert isinstance(feelings, list)


def test_btn_activities_and_btn_profile_sets_exposed():
    """menu.py and profile.py filter messages by these sets."""
    from texts import BTN_ACTIVITIES, BTN_HISTORY, BTN_PROFILE
    assert len(BTN_ACTIVITIES) >= 1
    assert len(BTN_HISTORY) >= 1
    assert len(BTN_PROFILE) >= 1
