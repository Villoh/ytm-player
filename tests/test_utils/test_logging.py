"""Tests for utils.logging — file-based logging setup and crash handlers."""

from __future__ import annotations

import logging
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
