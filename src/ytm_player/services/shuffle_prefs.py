"""Per-collection shuffle preferences, persisted to disk.

Keys are the collection's stable ID (playlistId, browseId, channelId).
Value is a bool: True = shuffle on, False = shuffle off.
LRU-capped at 1000 entries to prevent unbounded growth.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import OrderedDict
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_ENTRIES = 1000


class ShufflePreferences:
    """Thread-safe persistent dict of {context_id: shuffle_enabled}."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._prefs: OrderedDict[str, bool] = OrderedDict()
        self._load()

    def get(self, context_id: str | None) -> bool | None:
        """Return saved shuffle state, or None if no preference / no context."""
        if not context_id:
            return None
        with self._lock:
            value = self._prefs.get(context_id)
            if value is not None:
                self._prefs.move_to_end(context_id)
            return value

    def set(self, context_id: str | None, shuffle: bool) -> None:
        """Persist shuffle state for *context_id*. No-op if context_id is None."""
        if not context_id:
            return
        with self._lock:
            self._prefs[context_id] = shuffle
            self._prefs.move_to_end(context_id)
            while len(self._prefs) > _MAX_ENTRIES:
                self._prefs.popitem(last=False)
        self._save()

    def clear(self) -> None:
        with self._lock:
            self._prefs.clear()
        self._save()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._prefs = OrderedDict(
                    (k, bool(v)) for k, v in data.items() if isinstance(k, str)
                )
        except Exception:
            logger.exception("Failed to load shuffle prefs from %s", self._path)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(self._path.suffix + ".tmp")
            tmp.write_text(json.dumps(dict(self._prefs), indent=2), encoding="utf-8")
            tmp.replace(self._path)
        except Exception:
            logger.exception("Failed to save shuffle prefs to %s", self._path)
