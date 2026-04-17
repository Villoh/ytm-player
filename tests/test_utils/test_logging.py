"""Tests for utils.logging — file-based logging setup and crash handlers."""

from __future__ import annotations

import logging
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest


class TestSetupLogging:
    def test_creates_rotating_file_handler(self, tmp_path: Path):
        from ytm_player.utils.logging import setup_logging

        log_file = tmp_path / "ytm.log"
        setup_logging(level="INFO", log_file=log_file, max_bytes=1024, backup_count=2)

        root = logging.getLogger()
        rotating = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(rotating) == 1
        h = rotating[0]
        assert Path(h.baseFilename) == log_file
        assert h.maxBytes == 1024
        assert h.backupCount == 2

    def test_respects_level(self, tmp_path: Path):
        from ytm_player.utils.logging import setup_logging

        setup_logging(level="DEBUG", log_file=tmp_path / "ytm.log")
        assert logging.getLogger().getEffectiveLevel() == logging.DEBUG

    def test_idempotent(self, tmp_path: Path):
        """Calling setup_logging twice must not duplicate handlers."""
        from ytm_player.utils.logging import setup_logging

        log_file = tmp_path / "ytm.log"
        setup_logging(level="INFO", log_file=log_file)
        setup_logging(level="INFO", log_file=log_file)
        rotating = [
            h
            for h in logging.getLogger().handlers
            if isinstance(h, RotatingFileHandler)
        ]
        assert len(rotating) == 1

    def test_writes_to_file(self, tmp_path: Path):
        from ytm_player.utils.logging import setup_logging

        log_file = tmp_path / "ytm.log"
        setup_logging(level="DEBUG", log_file=log_file)
        logging.getLogger("test").error("hello world")
        # Force flush.
        for h in logging.getLogger().handlers:
            h.flush()
        assert log_file.exists()
        assert "hello world" in log_file.read_text()

    @pytest.fixture(autouse=True)
    def _reset_logging(self):
        """Tear down handlers between tests to avoid leakage."""
        yield
        root = logging.getLogger()
        for h in list(root.handlers):
            root.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass


class TestInstallExcepthooks:
    def test_main_thread_excepthook_writes_crash_file(self, tmp_path: Path):
        from ytm_player.utils.logging import install_excepthooks

        crash_dir = tmp_path / "crashes"
        install_excepthooks(crash_dir=crash_dir, keep=5)

        # Simulate an uncaught exception by calling the installed hook directly.
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            sys.excepthook(*sys.exc_info())

        files = sorted(crash_dir.glob("ytm-crash-*.log"))
        assert len(files) == 1
        text = files[0].read_text()
        assert "RuntimeError: boom" in text
        assert "Traceback" in text

    def test_thread_excepthook_writes_crash_file(self, tmp_path: Path):
        from ytm_player.utils.logging import install_excepthooks

        crash_dir = tmp_path / "crashes"
        install_excepthooks(crash_dir=crash_dir, keep=5)

        try:
            raise RuntimeError("thread boom")
        except RuntimeError:
            args = threading.ExceptHookArgs(
                exc_type=type(sys.exc_info()[1]),
                exc_value=sys.exc_info()[1],
                exc_traceback=sys.exc_info()[2],
                thread=threading.current_thread(),
            )
            threading.excepthook(args)

        files = sorted(crash_dir.glob("ytm-crash-*.log"))
        assert len(files) == 1
        assert "thread boom" in files[0].read_text()

    def test_keep_caps_old_crash_files(self, tmp_path: Path):
        from ytm_player.utils.logging import install_excepthooks

        crash_dir = tmp_path / "crashes"
        crash_dir.mkdir()
        # Pre-populate with 5 fake old crash files.
        for i in range(5):
            f = crash_dir / f"ytm-crash-2025010{i}-000000.log"
            f.write_text(f"old crash {i}")

        install_excepthooks(crash_dir=crash_dir, keep=3)

        # Trigger one new crash.
        try:
            raise ValueError("new")
        except ValueError:
            sys.excepthook(*sys.exc_info())

        files = sorted(crash_dir.glob("ytm-crash-*.log"))
        assert len(files) == 3, f"expected 3, got {len(files)}: {files}"

    @pytest.fixture(autouse=True)
    def _reset_excepthooks(self):
        original_sys = sys.excepthook
        original_thread = threading.excepthook
        yield
        sys.excepthook = original_sys
        threading.excepthook = original_thread
