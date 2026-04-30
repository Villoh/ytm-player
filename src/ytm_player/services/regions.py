"""Curated list of YouTube Music chart-supported regions.

YouTube Music advertises 62 regions via ``get_charts(country).countries.options``,
but in practice most return no daily-chart data even with auth. This list is
the empirically-verified subset where the Charts page actually displays
tracks. Trimmed via manual reproduction across all regions.

Layout: alphabetical by display name.
"""

from __future__ import annotations

CHART_REGIONS: tuple[tuple[str, str], ...] = (
    ("AU", "Australia"),
    ("BR", "Brazil"),
    ("CA", "Canada"),
    ("FR", "France"),
    ("DE", "Germany"),
    ("HK", "Hong Kong"),
    ("JP", "Japan"),
    ("MY", "Malaysia"),
    ("MX", "Mexico"),
    ("SG", "Singapore"),
    ("KR", "South Korea"),
    ("TW", "Taiwan"),
    ("TH", "Thailand"),
    ("AE", "United Arab Emirates"),
    ("GB", "United Kingdom"),
    ("US", "United States"),
    ("VN", "Vietnam"),
)
