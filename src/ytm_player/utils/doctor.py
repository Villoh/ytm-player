"""Diagnostic gathering for the `ytm doctor` command.

Produces a single-string report users can paste directly into a GitHub
issue.  Includes ytm-player version, Python version, OS, mpv version,
config file paths, last 50 log lines, and the most recent crash trace
(if any).
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys


def _mpv_version() -> str:
    """Return mpv version string, or a clear missing marker."""
    mpv_bin = shutil.which("mpv")
    if not mpv_bin:
        return "mpv: NOT FOUND in PATH"
    try:
        out = subprocess.run(
            [mpv_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        first_line = (out.stdout or out.stderr or "").splitlines()[0:1]
        return f"mpv: {first_line[0] if first_line else 'unknown'}"
    except (OSError, subprocess.SubprocessError):
        return "mpv: failed to execute"


def gather_diagnostics() -> str:
    """Return a multi-section text report describing the install."""
    from ytm_player import __version__
    from ytm_player.config.paths import (
        CONFIG_FILE,
        CRASH_DIR,
        LOG_FILE,
        SESSION_STATE_FILE,
        THEME_FILE,
    )
    from ytm_player.utils.logging import get_recent_crash, get_recent_log_lines

    sections: list[str] = []

    sections.append("=== ytm-player diagnostics ===")
    sections.append(f"Version: {__version__}")
    sections.append(
        f"Python:  {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    sections.append(f"OS:      {platform.system()} {platform.release()}")
    sections.append(f"Machine: {platform.machine()}")
    sections.append(_mpv_version())

    sections.append("")
    sections.append("=== Paths ===")
    sections.append(f"config:   {CONFIG_FILE}")
    sections.append(f"theme:    {THEME_FILE}")
    sections.append(f"session:  {SESSION_STATE_FILE}")
    sections.append(f"log:      {LOG_FILE}")
    sections.append(f"crashes:  {CRASH_DIR}")

    sections.append("")
    sections.append("=== Recent log (last 50 lines) ===")
    log_text = get_recent_log_lines(LOG_FILE, n=50)
    sections.append(log_text if log_text else "(log file is empty or missing)")

    sections.append("")
    sections.append("=== Most recent crash ===")
    crash = get_recent_crash(CRASH_DIR)
    if crash is None:
        sections.append("(no crash files found)")
    else:
        path, content = crash
        sections.append(f"From: {path}")
        sections.append(content)

    return "\n".join(sections)
