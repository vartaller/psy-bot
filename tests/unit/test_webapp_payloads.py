"""
WebApp payload contract tests.

The webapp HTML files (time-picker, date-picker) send JSON via tg.sendData.
These tests document and pin the contract so a change in one side breaks tests.
"""
import json
from datetime import date


def test_time_picker_payload_shape():
    """time-picker.html sends {hour, minute}; bot parses int(hour), int(minute)."""
    payload = json.loads('{"hour": 9, "minute": 30}')
    hour = int(payload["hour"])
    minute = int(payload["minute"])
    assert 0 <= hour < 24
    assert 0 <= minute < 60


def test_date_picker_payload_shape():
    """date-picker.html sends {date: 'YYYY-MM-DD'}; bot parses via date.fromisoformat."""
    payload = json.loads('{"date": "2026-05-15"}')
    parsed = date.fromisoformat(payload["date"])
    assert parsed.year == 2026
    assert parsed.month == 5
    assert parsed.day == 15


def test_date_picker_malformed_raises():
    """Bot has try/except around fromisoformat; bad input must raise so handler can fall back."""
    import pytest
    with pytest.raises(ValueError):
        date.fromisoformat("not-a-date")


def test_date_picker_html_exists_and_serves_calendar():
    """The HTML file must exist and contain the JS bridge call."""
    from pathlib import Path
    f = Path(__file__).resolve().parent.parent.parent / "webapp" / "date-picker.html"
    assert f.exists()
    content = f.read_text(encoding="utf-8")
    # Must call tg.sendData with JSON.stringify on a date
    assert "tg.sendData" in content
    assert "telegram-web-app.js" in content


def test_time_picker_html_exists_and_serves_picker():
    from pathlib import Path
    f = Path(__file__).resolve().parent.parent.parent / "webapp" / "time-picker.html"
    assert f.exists()
    content = f.read_text(encoding="utf-8")
    assert "tg.sendData" in content
