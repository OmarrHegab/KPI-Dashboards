"""Pure presentation helpers for the dashboard.

Kept free of any Streamlit import so they can be unit-tested without a running
Streamlit server.
"""

from __future__ import annotations

# Canonical category lists -> stable, complete filter options regardless of
# which values happen to be present in the current data slice.
DEVICE_STATUSES = ["Online", "Offline", "Maintenance"]
PIPELINE_STATUSES = ["Success", "Failed", "Warning"]

_GREEN = "background:#052e16;color:#22c55e;border:1px solid #14532d;"
_RED = "background:#3f1010;color:#ff5c5c;border:1px solid #7f1d1d;"
_ORANGE = "background:#4a2506;color:#fb923c;border:1px solid #9a3412;"
_NEUTRAL = "background:#111827;color:#d1d5db;border:1px solid #374151;"

_BADGE_STYLES = {
    "Online": _GREEN,
    "Offline": _RED,
    "Maintenance": _ORANGE,
    "Pass": _GREEN,
    "Fail": _RED,
    "Success": _GREEN,
    "Failed": _RED,
    "Warning": _ORANGE,
}

# A non-colour cue per state so meaning survives for colour-blind readers.
_BADGE_GLYPHS = {
    "Online": "●",
    "Offline": "✕",
    "Maintenance": "!",
    "Pass": "✓",
    "Fail": "✕",
    "Success": "✓",
    "Failed": "✕",
    "Warning": "!",
}


def render_status_badge(value) -> str:
    """Return an HTML span styling a status/result value as a coloured badge.

    Includes a glyph alongside the colour so the state is distinguishable
    without relying on colour alone (accessibility).
    """
    text = str(value)
    style = _BADGE_STYLES.get(text, _NEUTRAL)
    glyph = _BADGE_GLYPHS.get(text, "")
    label = f"{glyph} {text}".strip()
    return (
        f'<span style="{style} padding:4px 10px;border-radius:8px;'
        f'font-weight:700;font-size:13px;white-space:nowrap;">{label}</span>'
    )
