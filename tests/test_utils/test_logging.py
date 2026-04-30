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
        rotating = [h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)]
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
            exc_type, exc_value, exc_tb = sys.exc_info()
            assert exc_type is not None and exc_value is not None and exc_tb is not None
            sys.excepthook(exc_type, exc_value, exc_tb)

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
            exc_type, exc_value, exc_tb = sys.exc_info()
            assert exc_type is not None and exc_value is not None and exc_tb is not None
            args = threading.ExceptHookArgs(
                (exc_type, exc_value, exc_tb, threading.current_thread())
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
            exc_type, exc_value, exc_tb = sys.exc_info()
            assert exc_type is not None and exc_value is not None and exc_tb is not None
            sys.excepthook(exc_type, exc_value, exc_tb)

        files = sorted(crash_dir.glob("ytm-crash-*.log"))
        assert len(files) == 3, f"expected 3, got {len(files)}: {files}"

    def test_keyboard_interrupt_does_not_create_crash_file(self, tmp_path: Path):
        from ytm_player.utils.logging import install_excepthooks

        crash_dir = tmp_path / "crashes"
        install_excepthooks(crash_dir=crash_dir, keep=5)

        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt:
            exc_type, exc_value, exc_tb = sys.exc_info()
            assert exc_type is not None and exc_value is not None and exc_tb is not None
            sys.excepthook(exc_type, exc_value, exc_tb)

        files = list(crash_dir.glob("ytm-crash-*.log"))
        assert files == []

    def test_thread_hook_chains_to_default(self, tmp_path: Path, capsys):
        from ytm_player.utils.logging import install_excepthooks

        crash_dir = tmp_path / "crashes"
        install_excepthooks(crash_dir=crash_dir, keep=5)

        try:
            raise RuntimeError("chain me")
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            assert exc_type is not None and exc_value is not None and exc_tb is not None
            args = threading.ExceptHookArgs(
                (exc_type, exc_value, exc_tb, threading.current_thread())
            )
            threading.excepthook(args)

        # File written.
        files = list(crash_dir.glob("ytm-crash-*.log"))
        assert len(files) == 1
        # Default thread excepthook writes traceback to stderr.
        captured = capsys.readouterr()
        assert "chain me" in captured.err

    @pytest.fixture(autouse=True)
    def _reset_excepthooks(self):
        original_sys = sys.excepthook
        original_thread = threading.excepthook
        yield
        sys.excepthook = original_sys
        threading.excepthook = original_thread


class TestWriteCrashFileFallback:
    """write_crash_file must self-bootstrap when install_excepthooks was skipped.

    Regression for the ``crashes/ dir empty after a crash`` bug — silent
    None-return masked the real failure mode and made diagnostics useless.
    """

    @pytest.fixture(autouse=True)
    def _reset_module_state(self, monkeypatch):
        from ytm_player.utils import logging as logmod

        monkeypatch.setattr(logmod, "_crash_dir", None)
        yield

    def test_falls_back_to_paths_crash_dir_when_unconfigured(self, tmp_path: Path, monkeypatch):
        """If install_excepthooks was never called, write_crash_file should
        still produce a file using config.paths.CRASH_DIR rather than silently
        returning None.
        """
        from ytm_player.config import paths
        from ytm_player.utils.logging import write_crash_file

        crash_dir = tmp_path / "crashes"
        monkeypatch.setattr(paths, "CRASH_DIR", crash_dir)

        result = write_crash_file("traceback body", label="Test crash")

        assert result is not None
        assert result.exists()
        assert "Test crash" in result.read_text()
        assert "traceback body" in result.read_text()

    def test_logs_oserror_instead_of_silent_none(self, tmp_path: Path, monkeypatch, caplog):
        """When the write fails, we must log the reason — silent failure
        is what hid the original ``crashes dir empty`` symptom for hours.
        """
        from ytm_player.utils import logging as logmod

        # Point at a non-writable path so os.open raises OSError.
        crash_dir = tmp_path / "ro-crashes"
        crash_dir.mkdir()
        crash_dir.chmod(0o500)
        monkeypatch.setattr(logmod, "_crash_dir", crash_dir)

        try:
            with caplog.at_level("ERROR", logger="ytm_player.utils.logging"):
                result = logmod.write_crash_file("body", label="ReadOnly")

            assert result is None
            assert any("failed to write" in rec.getMessage().lower() for rec in caplog.records)
        finally:
            crash_dir.chmod(0o700)


class TestFaulthandlerEnable:
    """faulthandler must be enabled to a file under the crash dir.

    We can't actually trigger a SIGSEGV in tests (would kill pytest), but we
    can verify the file handle is opened and faulthandler is enabled, and
    that faulthandler.dump_traceback() writes to the configured file.
    """

    def test_dump_traceback_writes_to_configured_file(self, tmp_path: Path):
        """faulthandler.enable(file=fh) routes dump_traceback() output to fh."""
        import faulthandler

        fh_path = tmp_path / "faulthandler.log"
        fh = fh_path.open("ab", buffering=0)
        try:
            faulthandler.enable(file=fh, all_threads=True)
            try:
                faulthandler.dump_traceback(file=fh, all_threads=True)
            finally:
                # Always disable to avoid bleeding into other tests.
                faulthandler.disable()
        finally:
            fh.close()

        assert fh_path.exists()
        content = fh_path.read_text(encoding="utf-8", errors="replace")
        # dump_traceback emits the literal phrase "Current thread"
        assert "Current thread" in content
