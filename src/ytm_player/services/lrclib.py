"""LRCLIB.net fallback for synced lyrics when YouTube Music doesn't provide them."""

from __future__ import annotations

import asyncio
import logging

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://lrclib.net/api/get"
_TIMEOUT = 5


async def get_synced_lyrics(
    title: str, artist: str, duration_seconds: float | None = None
) -> str | None:
    """Fetch synced LRC lyrics from LRCLIB.net.

    Returns the LRC-format string if available, or None.
    """
    from ytm_player.utils.formatting import sanitize_title_for_lyric_lookup

    clean_title = sanitize_title_for_lyric_lookup(title, artist)
    params: dict[str, str] = {
        "track_name": clean_title,
        "artist_name": artist,
    }
    if duration_seconds is not None:
        params["duration"] = str(int(duration_seconds))

    def _fetch() -> str | None:
        try:
            resp = requests.get(
                _BASE_URL,
                params=params,
                headers={"User-Agent": "ytm-player/1.0"},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("syncedLyrics") or None
        except Exception:
            logger.debug("LRCLIB request failed for %r by %r", title, artist, exc_info=True)
            return None

    return await asyncio.to_thread(_fetch)
