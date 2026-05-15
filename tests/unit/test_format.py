"""
Tests for texts.format_tp_body / format_tp_summary.

These catch:
- Missing-field crashes when responses dict is partial
- Wrong star rendering for scale fields
- Missing block headers
"""
from texts import format_tp_body, format_tp_summary


FULL_RESPONSES = {
    "irritation": 3,
    "excitement": 5,
    "sensation":  "tightness in chest",
    "feeling":    "anxiety",
    "emotion":    "fear",
    "impression": "uncomfortable",
    "meaning":    "warning sign",
    "idea":       "rest more",
}


def test_format_body_contains_all_three_blocks_uk():
    out = format_tp_body("uk", FULL_RESPONSES)
    assert "Блок 1" in out or "Фізіологічний" in out
    assert "Блок 2" in out or "Емоційний" in out
    assert "Блок 3" in out or "Ментальний" in out


def test_format_body_contains_all_three_blocks_ru():
    out = format_tp_body("ru", FULL_RESPONSES)
    assert "Блок 1" in out or "Физиологический" in out
    assert "Блок 2" in out or "Эмоциональный" in out
    assert "Блок 3" in out or "Ментальный" in out


def test_format_body_renders_scale_as_stars():
    out = format_tp_body("uk", FULL_RESPONSES)
    # irritation=3 → 3 filled + 2 empty stars
    assert "⭐⭐⭐☆☆" in out
    # excitement=5 → 5 filled
    assert "⭐⭐⭐⭐⭐" in out


def test_format_body_with_partial_responses_does_not_crash():
    """Missing fields fall back to '—' instead of raising KeyError."""
    partial = {"irritation": 2}
    out = format_tp_body("uk", partial)
    assert "—" in out  # at least one missing field rendered as dash


def test_format_summary_includes_date_and_body():
    out = format_tp_summary("uk", FULL_RESPONSES, "15.05.2026")
    assert "15.05.2026" in out
    assert "tightness in chest" in out
    assert "anxiety" in out
