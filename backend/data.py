"""Data access: load the device / test-run CSVs with caching and clear errors.

The loaders translate low-level failures (missing file, unreadable CSV, missing
columns) into the domain exceptions :class:`DataUnavailableError` and
:class:`DataSchemaError`, which the API layer maps to clean HTTP responses
instead of leaking a raw stack trace.

Loading is cached by ``(path, mtime)`` so a static CSV is parsed once, but the
cache transparently refreshes when the file changes (handy for tests and for a
live data refresh).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from backend.config import (
    DEVICE_DATA_FILE,
    REQUIRED_DEVICE_COLUMNS,
    REQUIRED_TEST_RUN_COLUMNS,
    TEST_RUNS_FILE,
)

logger = logging.getLogger(__name__)


class DataUnavailableError(Exception):
    """Raised when a data source cannot be read (missing/unreadable file)."""


class DataSchemaError(Exception):
    """Raised when a data source is readable but missing required columns."""


# Cache keyed by (resolved path, mtime_ns) -> DataFrame.
_cache: dict[tuple[str, int], pd.DataFrame] = {}


def _read_csv_cached(path: Path) -> pd.DataFrame:
    try:
        mtime = path.stat().st_mtime_ns
    except FileNotFoundError as exc:
        logger.error("Data file not found: %s", path)
        raise DataUnavailableError(f"Data file not found: {path.name}") from exc
    except OSError as exc:  # permission / IO error
        logger.error("Data file unreadable: %s (%s)", path, exc)
        raise DataUnavailableError(f"Data file unreadable: {path.name}") from exc

    key = (str(path.resolve()), mtime)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError as exc:
        logger.error("Data file is empty: %s", path)
        raise DataSchemaError(f"Data file is empty: {path.name}") from exc
    except (OSError, ValueError) as exc:
        logger.error("Failed to parse data file %s: %s", path, exc)
        raise DataUnavailableError(f"Could not parse data file: {path.name}") from exc

    # Evict only stale entries for this same path; keep other files cached so the
    # devices and test-run frames can coexist (otherwise the cache never hits).
    for stale in [k for k in _cache if k[0] == key[0]]:
        del _cache[stale]
    _cache[key] = df
    return df


def load_devices(path: Path = DEVICE_DATA_FILE) -> pd.DataFrame:
    """Load and validate the devices snapshot.

    Blank string cells become "" and ``test_duration_sec`` is coerced to int, so a
    readable-but-dirty CSV never breaks the typed ``/devices`` response.
    """
    df = _read_csv_cached(path)
    missing = [col for col in REQUIRED_DEVICE_COLUMNS if col not in df.columns]
    if missing:
        logger.error("Devices CSV missing columns: %s", missing)
        raise DataSchemaError(f"Devices data missing columns: {', '.join(missing)}")

    df = df.copy()
    string_cols = [c for c in df.columns if c != "test_duration_sec"]
    df[string_cols] = df[string_cols].fillna("")
    # A blank/non-numeric duration defaults to 0 rather than crashing serialization.
    df["test_duration_sec"] = (
        pd.to_numeric(df["test_duration_sec"], errors="coerce").fillna(0).astype(int)
    )
    return df


def load_test_runs(path: Path = TEST_RUNS_FILE) -> pd.DataFrame:
    """Load the historical test-run data.

    Trends are an optional feature, so any problem (missing file or missing
    columns) degrades gracefully to an empty frame rather than failing /trends.
    """
    try:
        df = _read_csv_cached(path)
    except DataUnavailableError:
        logger.warning("Test-run history unavailable at %s; trends disabled", path)
        return pd.DataFrame(columns=REQUIRED_TEST_RUN_COLUMNS)

    missing = [col for col in REQUIRED_TEST_RUN_COLUMNS if col not in df.columns]
    if missing:
        logger.warning("Test-run CSV missing columns %s; trends disabled", missing)
        return pd.DataFrame(columns=REQUIRED_TEST_RUN_COLUMNS)
    return df


def clear_cache() -> None:
    """Drop the in-memory cache (used by tests)."""
    _cache.clear()
