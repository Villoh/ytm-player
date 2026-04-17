"""File-based logging setup for ytm-player.

Why this exists: ytm-player runs inside Textual's alt-screen, which hides
stderr.  Calling logging.basicConfig() (which targets stderr by default)
means every logger.* call is silently lost — making bug reports
unactionable.  This module routes logs to a rotating file under
~/.config/ytm-player/logs/ytm.log and installs sys.excepthook /
threading.excepthook so unhandled crashes leave a paper trail under
~/.config/ytm-player/crashes/.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Module-level handle so setup_logging can be safely called twice.
_file_handler: RotatingFileHandler | None = None


def setup_logging(
    *,
    level: str = "WARNING",
    log_file: Path,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> None:
    """Install a rotating file handler on the root logger.

    Idempotent — calling twice replaces the existing file handler rather
    than stacking duplicates.  Other handlers (e.g. an existing stderr
    handler from logging.basicConfig) are left in place; the caller is
    responsible for removing them if Textual is taking over the screen.
    """
    global _file_handler

    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    if _file_handler is not None and _file_handler in root.handlers:
        root.removeHandler(_file_handler)
        try:
            _file_handler.close()
        except Exception:
            logging.getLogger(__name__).debug(
                "Failed to close prior file handler", exc_info=True
            )
        _file_handler = None

    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    numeric_level = getattr(logging, level.upper(), logging.WARNING)
    root.setLevel(numeric_level)
    handler.setLevel(numeric_level)
    root.addHandler(handler)

    _file_handler = handler
