"""Theme system integrating Textual's native theming with app-specific colors."""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path

from textual.theme import Theme

from ytm_player.config.paths import THEMES_DIR

logger = logging.getLogger(__name__)

# ── YTM dark theme — YouTube Music-inspired defaults ──────────────────

YTM_DARK = Theme(
    name="ytm-dark",
    primary="#ff0000",
    secondary="#aaaaaa",
    accent="#ff4e45",
    success="#2ecc71",
    warning="#f39c12",
    error="#e74c3c",
    foreground="#ffffff",
    background="#0f0f0f",
    surface="#1a1a1a",
    dark=True,
    variables={
        "playback-bar-bg": "#1a1a1a",
        "active-tab": "#ffffff",
        "inactive-tab": "#999999",
        "selected-item": "#2a2a2a",
        "progress-filled": "#ff0000",
        "progress-empty": "#555555",
        "lyrics-played": "#999999",
        "lyrics-current": "#2ecc71",
        "lyrics-upcoming": "#aaaaaa",
    },
)


@dataclass
class ThemeColors:
    """Resolved color values for Rich Text rendering in widget render() methods.

    Populated from the active Textual theme via watch_theme.  App-specific
    variables (playback bar, lyrics, etc.) are read from the theme's
    ``variables`` dict, which user themes can set in their ``[variables]``
    section.
    """

    # Base colors (populated from Textual theme at runtime).
    background: str = "#0f0f0f"
    foreground: str = "#ffffff"
    primary: str = "#ff0000"
    secondary: str = "#aaaaaa"
    accent: str = "#ff4e45"
    success: str = "#2ecc71"
    warning: str = "#f39c12"
    error: str = "#e74c3c"
    surface: str = "#1a1a1a"
    border: str = "#333333"
    muted_text: str = "#999999"
    text: str = "#ffffff"

    # App-specific colors (set from theme variables dict).
    playback_bar_bg: str = "#1a1a1a"
    active_tab: str = "#ffffff"
    inactive_tab: str = "#999999"
    selected_item: str = "#2a2a2a"
    progress_filled: str = "#ff0000"
    progress_empty: str = "#555555"
    lyrics_played: str = "#999999"
    lyrics_current: str = "#2ecc71"
    lyrics_upcoming: str = "#aaaaaa"


def load_user_themes(themes_dir: Path = THEMES_DIR) -> list[Theme]:
    """Load user-defined themes from the themes/ config directory.

    Each TOML file must have at least ``name`` and ``primary``.  An optional
    ``[variables]`` section maps directly to Textual CSS variables, which is
    where ytm-player-specific colors (playback bar, lyrics, etc.) can be set.

    Example theme file::

        name = "my-theme"
        primary = "#ff6b6b"
        background = "#1a1a2e"
        dark = true

        [variables]
        playback-bar-bg = "#0f3460"
        lyrics-current = "#ff6b6b"
    """
    if not themes_dir.exists():
        return []

    themes: list[Theme] = []
    for toml_file in sorted(themes_dir.glob("*.toml")):
        try:
            with open(toml_file, "rb") as f:
                data = tomllib.load(f)
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            logger.warning("Could not load user theme %s — skipping", toml_file.name)
            continue

        if "name" not in data or "primary" not in data:
            logger.warning(
                "User theme %s is missing required fields 'name' and/or 'primary' — skipping",
                toml_file.name,
            )
            continue

        try:
            theme = Theme(
                name=data["name"],
                primary=data["primary"],
                secondary=data.get("secondary"),
                warning=data.get("warning"),
                error=data.get("error"),
                success=data.get("success"),
                accent=data.get("accent"),
                foreground=data.get("foreground"),
                background=data.get("background"),
                surface=data.get("surface"),
                panel=data.get("panel"),
                dark=data.get("dark", True),
                variables=data.get("variables", {}),
            )
            themes.append(theme)
        except Exception:
            logger.warning(
                "Failed to build Theme from %s — skipping", toml_file.name, exc_info=True
            )

    return themes


_theme: ThemeColors | None = None


def get_theme() -> ThemeColors:
    global _theme
    if _theme is None:
        _theme = ThemeColors()
    return _theme


def set_theme(theme: ThemeColors) -> None:
    """Replace the cached ThemeColors (called when the Textual theme changes)."""
    global _theme
    _theme = theme


def reset_theme() -> None:
    """Invalidate the cached ThemeColors so it's rebuilt on next access."""
    global _theme
    _theme = None
