"""Unit tests for the processing functions. No network needed.

Run: python tests/test_processing.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.tools import aggregate_daily, filter_valid_readings, to_records


def test_to_records_flattens_api_payload():
    payloads = [{
        "city": "Test City",
        "timezone": "America/New_York",
        "hourly": {
            "time": ["2026-11-15T08:00", "2026-11-15T09:00"],
            "temperature_2m": [50.0, 52.0],
        },
    }]
    records = to_records(payloads)
    assert len(records) == 2
    assert records[0] == {
        "city": "Test City", "date": "2026-11-15", "hour": 8,
        "temperature_f": 50.0, "timezone": "America/New_York",
    }


def test_filter_drops_nulls_and_night_hours():
    records = [
        {"city": "A", "date": "2026-11-15", "hour": 2,
         "temperature_f": 40.0, "timezone": "X"},
        {"city": "A", "date": "2026-11-15", "hour": 8,
         "temperature_f": None, "timezone": "X"},
        {"city": "A", "date": "2026-11-15", "hour": 8,
         "temperature_f": 50.0, "timezone": "X"},
    ]
    kept, summary = filter_valid_readings(records)
    assert len(kept) == 1
    assert summary["dropped_null_temperature"] == 1
    assert summary["dropped_night_hours"] == 1


def test_aggregate_daily_groups_and_aggregates():
    records = [
        {"city": "A", "date": "2026-11-15", "hour": 8,
         "temperature_f": 50.0, "timezone": "X"},
        {"city": "A", "date": "2026-11-15", "hour": 9,
         "temperature_f": 60.0, "timezone": "X"},
        {"city": "B", "date": "2026-11-15", "hour": 8,
         "temperature_f": 70.0, "timezone": "X"},
    ]
    daily = aggregate_daily(records)
    assert len(daily) == 2
    first = daily[0]
    assert first["city"] == "A"
    assert first["count"] == 2
    assert first["mean_f"] == 55.0
    assert first["min_f"] == 50.0
    assert first["max_f"] == 60.0
    assert first["range_f"] == 10.0


if __name__ == "__main__":
    test_to_records_flattens_api_payload()
    test_filter_drops_nulls_and_night_hours()
    test_aggregate_daily_groups_and_aggregates()
    print("All 3 processing tests passed.")
