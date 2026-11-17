"""Plain data functions used by the ADK agents.

These functions do the real work: calling the public API, filtering,
grouping, and aggregating. The agents in agents.py only orchestrate
them, so each function can be tested on its own.

Open-Meteo response shape, verified by a live call on Nov 15, 2026:
the JSON has hourly.time (ISO 8601 strings such as
"2026-11-15T00:00") and hourly.temperature_2m (numbers in the unit
requested, or null when a value is missing), plus hourly_units.
"""

import statistics
import time

import requests

from . import config

REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 1


def fetch_city_forecast(city, session=None):
    """Fetch one city's hourly forecast from Open-Meteo, no API key.

    Returns the raw JSON plus the city name. Retries once on a
    transient failure, then raises so the caller can record the miss.
    """
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": "temperature_2m",
        "forecast_days": config.FORECAST_DAYS,
        "timezone": city["timezone"],
        "temperature_unit": "fahrenheit",
    }
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(
                config.API_BASE_URL, params=params,
                timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
            payload["city"] = city["name"]
            return payload
        except (requests.RequestException, ValueError) as error:
            last_error = error
            time.sleep(1)
    raise RuntimeError(
        "Failed to fetch forecast for %s: %s" % (city["name"], last_error))


def fetch_all_cities(cities):
    """Fetch every city. A city that fails after retry is skipped and
    recorded, so one bad response does not stop the whole batch."""
    payloads = []
    failed = []
    for city in cities:
        try:
            payloads.append(fetch_city_forecast(city))
        except RuntimeError as error:
            failed.append({"city": city["name"], "error": str(error)})
    return payloads, failed


def to_records(payloads):
    """Flatten raw API payloads into one row per city per hour.

    Each row has city, date, hour, temperature_f, and timezone.
    Rows are kept in the order the API returned them.
    """
    records = []
    for payload in payloads:
        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        for timestamp, temp in zip(times, temps):
            date, hour_text = timestamp.split("T")
            records.append({
                "city": payload["city"],
                "date": date,
                "hour": int(hour_text.split(":")[0]),
                "temperature_f": temp,
                "timezone": payload.get("timezone", ""),
            })
    return records


def filter_valid_readings(records):
    """Filter to valid daytime readings.

    Keeps a row only when the temperature is present and the hour is
    between DAY_START_HOUR and DAY_END_HOUR in local time. Returns
    the kept rows plus a summary of what was dropped and why, so the
    filter is visible in the output instead of silent.
    """
    kept = []
    dropped_null = 0
    dropped_night = 0
    for row in records:
        if row["temperature_f"] is None:
            dropped_null += 1
        elif not config.DAY_START_HOUR <= row["hour"] <= config.DAY_END_HOUR:
            dropped_night += 1
        else:
            kept.append(row)
    summary = {
        "received": len(records),
        "kept": len(kept),
        "dropped_null_temperature": dropped_null,
        "dropped_night_hours": dropped_night,
    }
    return kept, summary


def aggregate_daily(records):
    """Group by city and date, then aggregate each group.

    For each city and date, compute the count of hourly readings and
    the mean, min, max, and range of temperature in Fahrenheit. The
    range is max minus min. Results are sorted by date, then city.
    """
    groups = {}
    for row in records:
        key = (row["city"], row["date"])
        groups.setdefault(key, []).append(row["temperature_f"])
    daily = []
    for (city, date), temps in sorted(groups.items()):
        daily.append({
            "city": city,
            "date": date,
            "count": len(temps),
            "mean_f": round(statistics.fmean(temps), 1),
            "min_f": min(temps),
            "max_f": max(temps),
            "range_f": round(max(temps) - min(temps), 1),
        })
    return daily


def build_processed_payload(daily, filter_summary, failed_cities):
    """Wrap the daily summary with the run metadata a reader needs."""
    dates = sorted({row["date"] for row in daily})
    cities = sorted({row["city"] for row in daily})
    return {
        "source": "Open-Meteo forecast API, hourly temperature_2m",
        "unit": "Fahrenheit",
        "cities": cities,
        "dates": dates,
        "filter": filter_summary,
        "failed_cities": failed_cities,
        "daily": daily,
    }
