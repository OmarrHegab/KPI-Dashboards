"""Tests for the pure frontend formatting helpers (no Streamlit needed)."""

from __future__ import annotations

import pytest

from frontend.formatting import (
    DEVICE_STATUSES,
    PIPELINE_STATUSES,
    render_status_badge,
)


@pytest.mark.parametrize(
    ("value", "expected_color"),
    [
        ("Online", "#22c55e"),
        ("Pass", "#22c55e"),
        ("Success", "#22c55e"),
        ("Offline", "#ff5c5c"),
        ("Fail", "#ff5c5c"),
        ("Failed", "#ff5c5c"),
        ("Maintenance", "#fb923c"),
        ("Warning", "#fb923c"),
    ],
)
def test_badge_uses_expected_color(value, expected_color):
    html = render_status_badge(value)
    assert expected_color in html
    assert value in html


def test_unknown_value_gets_neutral_style():
    html = render_status_badge("Decommissioned")
    assert "#d1d5db" in html  # neutral text color
    assert "Decommissioned" in html


def test_badge_includes_non_color_glyph():
    # Accessibility: a glyph distinguishes states without relying on color.
    assert "✓" in render_status_badge("Pass")
    assert "✕" in render_status_badge("Fail")


def test_badge_handles_non_string():
    assert "5" in render_status_badge(5)


def test_canonical_lists_are_complete():
    assert DEVICE_STATUSES == ["Online", "Offline", "Maintenance"]
    assert PIPELINE_STATUSES == ["Success", "Failed", "Warning"]
