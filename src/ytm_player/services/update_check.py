"""Check PyPI for a newer ytm-player release.

The check runs in a background worker on app startup. Results are
cached for 24 hours in CONFIG_DIR/update_check.json so we don't hit
PyPI more than once a day. Network failures are silent — being offline
is not an error worth surfacing to the user.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

_PYPI_URL = "https://pypi.org/pypi/ytm-player/json"
_CHECK_INTERVAL_SECONDS = 24 * 60 * 60  # 24h
_REQUEST_TIMEOUT = 5.0


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse 'X.Y.Z' (or longer) into a comparable tuple of ints.

    Trailing non-numeric suffixes (e.g. 'rc1', 'dev0') sort BEFORE the
    plain release — so '1.6.0rc1' < '1.6.0'. This matches PEP 440 for
    the common cases without pulling in packaging.version.

    Returns an empty tuple on parse failure (treated as oldest).
    """
    parts: list[int] = []
    for chunk in v.strip().split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            return ()
        parts.append(int(digits))
        # Stop on the first chunk with a non-numeric suffix — this gives
        # a pre-release the same prefix but no further chunks, so it
        # compares as less-than the corresponding release.
        if len(digits) != len(chunk):
            break
    return tuple(parts)


def _is_newer(latest: str, current: str) -> bool:
    """True when *latest* is strictly newer than *current* (by PEP-440-ish parse)."""
    lp = _parse_version(latest)
    cp = _parse_version(current)
    if not lp or not cp:
        return False
    return lp > cp


def _fetch_latest_from_pypi() -> str | None:
    """Hit PyPI for the latest ytm-player version. None on any failure."""
    try:
        req = urllib.request.Request(
            _PYPI_URL,
            headers={"User-Agent": "ytm-player update-check"},
        )
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("info", {}).get("version")
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
        return None
    except Exception:  # pragma: no cover — belt-and-braces
        logger.debug("Unexpected PyPI fetch failure", exc_info=True)
        return None


def _read_cache(cache_file: Path) -> dict:
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_cache(cache_file: Path, latest: str) -> None:
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"checked_at": time.time(), "latest": latest}
        cache_file.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        logger.debug("Failed to write update-check cache", exc_info=True)


def check_for_update(current_version: str, cache_file: Path) -> str | None:
    """Return the latest PyPI version string IF strictly newer than current.

    Returns None if:
    - The cache says we checked within the last 24h.
    - PyPI is unreachable.
    - The latest version is not newer than *current_version*.
    """
    cache = _read_cache(cache_file)
    last_checked = float(cache.get("checked_at", 0) or 0)
    elapsed = time.time() - last_checked
    # Negative elapsed (clock went backwards) → treat as stale and re-fetch.
    if 0 <= elapsed < _CHECK_INTERVAL_SECONDS:
        latest = cache.get("latest")
        if latest and _is_newer(latest, current_version):
            return latest
        return None

    latest = _fetch_latest_from_pypi()
    if latest is None:
        return None
    _write_cache(cache_file, latest)
    if _is_newer(latest, current_version):
        return latest
    return None
