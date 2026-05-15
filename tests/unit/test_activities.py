"""
Tests for activities.py — schema registry integrity.

These catch:
- Schema declares a label_key / options_key / block_header_key that doesn't
  exist in texts.json (would crash at render time)
- CHOICE fields missing options_key
- Mismatched field types vs storage encryption decisions
"""
from __future__ import annotations

import pytest

from activities import (
    FieldType,
    SCHEMAS,
    get_field,
    get_schema,
    is_encrypted_type,
)
from texts import TEXTS


SLUGS = list(SCHEMAS.keys())
LANGS = ("uk", "ru")


def test_at_least_two_activities_registered():
    assert "thinking_pattern" in SCHEMAS
    assert "individuality_cards" in SCHEMAS


@pytest.mark.parametrize("slug", SLUGS)
@pytest.mark.parametrize("lang", LANGS)
def test_every_field_label_key_exists_in_texts(slug, lang):
    for f in get_schema(slug):
        assert f.label_key in TEXTS[lang], (
            f"Schema field {slug}.{f.name} declares label_key={f.label_key!r} "
            f"but no such key in {lang}"
        )


@pytest.mark.parametrize("slug", SLUGS)
@pytest.mark.parametrize("lang", LANGS)
def test_block_header_keys_exist_in_texts(slug, lang):
    for f in get_schema(slug):
        if f.block_header_key:
            assert f.block_header_key in TEXTS[lang]


@pytest.mark.parametrize("slug", SLUGS)
@pytest.mark.parametrize("lang", LANGS)
def test_choice_field_options_key_exists_and_is_list(slug, lang):
    for f in get_schema(slug):
        if f.type == FieldType.CHOICE:
            assert f.options_key, f"CHOICE field {slug}.{f.name} missing options_key"
            opts = TEXTS[lang].get(f.options_key)
            assert isinstance(opts, list) and len(opts) >= 2, (
                f"options_key {f.options_key!r} for {slug}.{f.name} in {lang} "
                f"must be a list of >=2 strings"
            )


def test_get_field_returns_field_or_none():
    assert get_field("thinking_pattern", "irritation").name == "irritation"
    assert get_field("thinking_pattern", "no_such_field") is None
    assert get_field("no_such_slug", "irritation") is None


def test_is_encrypted_type_covers_text_and_choice():
    assert is_encrypted_type(FieldType.TEXT)
    assert is_encrypted_type(FieldType.CHOICE)
    assert not is_encrypted_type(FieldType.SCALE)


def test_thinking_pattern_field_names_match_legacy():
    """Existing prod data uses these exact field names — must not drift."""
    names = [f.name for f in get_schema("thinking_pattern")]
    assert names == ["irritation", "excitement", "sensation", "feeling",
                     "emotion", "impression", "meaning", "idea"]


def test_individuality_cards_has_three_choice_fields():
    schema = get_schema("individuality_cards")
    assert len(schema) == 3
    for f in schema:
        assert f.type == FieldType.CHOICE
