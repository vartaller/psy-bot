"""
Tests for texts.find_tz_by_current_time and tz_name.

These catch:
- Offset math errors (UTC wraparound)
- Detection that returns a city outside the user's actual offset
"""
from datetime import datetime

import pytest
import pytz

from texts import find_tz_by_current_time, tz_name, TIMEZONES


def _user_clock_for(tz_id: str) -> tuple[int, int]:
    now = datetime.now(pytz.timezone(tz_id))
    return now.hour, now.minute


@pytest.mark.parametrize("tz_id", [
    "Europe/Kyiv", "Europe/Moscow", "Asia/Tokyo",
    "America/New_York", "America/Los_Angeles",
])
def test_detected_tz_has_same_offset_as_real(tz_id):
    """If the user reports the current local time for tz X, detection should
    return some tz with the SAME UTC offset (not necessarily the same name)."""
    h, m = _user_clock_for(tz_id)
    detected = find_tz_by_current_time(h, m)
    now_utc = datetime.now(pytz.utc).replace(tzinfo=None)
    actual_off = pytz.timezone(tz_id).utcoffset(now_utc).total_seconds()
    detected_off = pytz.timezone(detected).utcoffset(now_utc).total_seconds()
    assert actual_off == detected_off, (
        f"Reported {h:02d}:{m:02d} for {tz_id} but got {detected} "
        f"(offset {detected_off / 3600}h vs expected {actual_off / 3600}h)"
    )


def test_tz_name_returns_label_for_known_tz():
    assert "Київ" in tz_name("uk", "Europe/Kyiv") or "Киев" in tz_name("uk", "Europe/Kyiv")


def test_tz_name_returns_passthrough_for_unknown_tz():
    assert tz_name("uk", "Mars/Olympus") == "Mars/Olympus"


def test_all_timezones_have_unique_ids():
    ids = [tz_id for tz_id, _ in TIMEZONES]
    assert len(ids) == len(set(ids)), "Duplicate timezone IDs in TIMEZONES list"
