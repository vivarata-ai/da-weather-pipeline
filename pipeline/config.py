"""Configuration for the DA extra credit pipeline.

All values here are plain settings, not secrets. Cloud credentials are
never stored in this file. They come from the standard AWS or Google
Cloud credential chain when cloud storage is enabled.
"""

import os

API_BASE_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 3

# Small set of US cities. Latitude and longitude are the values the
# Open-Meteo forecast API expects. Timezone names are IANA names so the
# hourly times come back in local time for each city.
CITIES = [
    {"name": "New York", "latitude": 40.71, "longitude": -74.01,
     "timezone": "America/New_York"},
    {"name": "Chicago", "latitude": 41.88, "longitude": -87.63,
     "timezone": "America/Chicago"},
    {"name": "Los Angeles", "latitude": 34.05, "longitude": -118.24,
     "timezone": "America/Los_Angeles"},
    {"name": "Houston", "latitude": 29.76, "longitude": -95.37,
     "timezone": "America/Chicago"},
    {"name": "Seattle", "latitude": 47.61, "longitude": -122.33,
     "timezone": "America/Los_Angeles"},
]

# Daytime hours kept by the filter, in local time. Night hours are
# dropped so the daily summary describes the hours people are awake.
DAY_START_HOUR = 6
DAY_END_HOUR = 21

OUTPUT_DIR = "output"
APP_NAME = "da_extra_credit"


def storage_settings():
    """Read storage settings from the environment.

    STORAGE_BACKEND: local, s3, or gcs. Default is local.
    S3_BUCKET: bucket name used when STORAGE_BACKEND is s3.
    GCS_BUCKET: bucket name used when STORAGE_BACKEND is gcs.
    """
    return {
        "backend": os.environ.get("STORAGE_BACKEND", "local").lower(),
        "s3_bucket": os.environ.get("S3_BUCKET", ""),
        "gcs_bucket": os.environ.get("GCS_BUCKET", ""),
    }
