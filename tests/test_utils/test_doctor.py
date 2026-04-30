"""Tests for utils.doctor — diagnostic gathering for `ytm doctor`."""

from __future__ import annotations

from pathlib import Path


class TestGatherDiagnosticsExisting:
    """v1 sections must still work."""

    def test_includes_version(self):
        from ytm_player.utils.doctor import gather_diagnostics

        report = gather_diagnostics()
        from ytm_player import __version__

        assert __version__ in report

    def test_includes_python_version(self):
        import sys

        from ytm_player.utils.doctor import gather_diagnostics

        report = gather_diagnostics()
        assert f"{sys.version_info.major}.{sys.version_info.minor}" in report

    def test_includes_platform(self):
        import platform

        from ytm_player.utils.doctor import gather_diagnostics

        report = gather_diagnostics()
        assert platform.system() in report


class TestGatherDiagnosticsV2:
    """v2 must include 8 sections in order, with redaction."""

    def test_section_headers_present(self):
        from ytm_player.utils.doctor import gather_diagnostics

        report = gather_diagnostics()
        assert "=== ytm-player diagnostics ===" in report
        assert "=== Paths ===" in report
        assert "=== Process status ===" in report
        assert "=== Recent ERROR/WARNING (last 20) ===" in report
        assert "=== Recent mpv warnings/errors ===" in report
        assert "=== Most recent faulthandler trace ===" in report
        assert "=== Most recent crash file ===" in report
        assert "=== Active hooks ===" in report

    def test_section_order(self):
        from ytm_player.utils.doctor import gather_diagnostics

        report = gather_diagnostics()
        order = [
            "=== ytm-player diagnostics ===",
            "=== Paths ===",
            "=== Process status ===",
            "=== Recent ERROR/WARNING (last 20) ===",
            "=== Recent mpv warnings/errors ===",
            "=== Most recent faulthandler trace ===",
            "=== Most recent crash file ===",
            "=== Active hooks ===",
        ]
        positions = [report.index(h) for h in order]
        assert positions == sorted(positions), f"Sections out of order: {positions}"

    def test_redacts_authorization_header(self, monkeypatch, tmp_path: Path):
        from ytm_player.config import paths
        from ytm_player.utils.doctor import gather_diagnostics

        log = tmp_path / "ytm.log"
        log.write_text("2026-04-30 [WARNING] foo: Authorization: Bearer abc123secret\n")
        monkeypatch.setattr(paths, "LOG_FILE", log)

        report = gather_diagnostics()
        assert "abc123secret" not in report
        assert "[REDACTED]" in report

    def test_redacts_cookie_header(self, monkeypatch, tmp_path: Path):
        from ytm_player.config import paths
        from ytm_player.utils.doctor import gather_diagnostics

        log = tmp_path / "ytm.log"
        log.write_text("2026-04-30 [WARNING] foo: Cookie: SAPISID=secret\n")
        monkeypatch.setattr(paths, "LOG_FILE", log)

        report = gather_diagnostics()
        assert "SAPISID=secret" not in report

    def test_mpv_section_filters_for_mpv_prefix(self, monkeypatch, tmp_path: Path):
        from ytm_player.config import paths
        from ytm_player.utils.doctor import gather_diagnostics

        log = tmp_path / "ytm.log"
        log.write_text(
            "2026-04-30 [WARNING] ytm_player: regular warning\n"
            "2026-04-30 [WARNING] ytm_player.services.player: mpv[ao]: format mismatch\n"
            "2026-04-30 [ERROR] ytm_player.services.player: mpv[file]: cannot open\n"
        )
        monkeypatch.setattr(paths, "LOG_FILE", log)

        report = gather_diagnostics()
        start = report.index("=== Recent mpv warnings/errors ===")
        end = report.index("=== Most recent faulthandler trace ===")
        mpv_section = report[start:end]
        assert "mpv[ao]: format mismatch" in mpv_section
        assert "mpv[file]: cannot open" in mpv_section
        assert "regular warning" not in mpv_section

    def test_faulthandler_section_shows_last_block_when_present(self, monkeypatch, tmp_path: Path):
        from ytm_player.config import paths
        from ytm_player.utils.doctor import gather_diagnostics

        crash_dir = tmp_path / "crashes"
        crash_dir.mkdir()
        fh = crash_dir / "faulthandler.log"
        fh.write_text(
            "Fatal Python error: Segmentation fault\n\n"
            "Current thread 0x0 (most recent call first):\n"
            "  File 'a.py', line 1 in foo\n"
        )
        monkeypatch.setattr(paths, "CRASH_DIR", crash_dir)

        report = gather_diagnostics()
        start = report.index("=== Most recent faulthandler trace ===")
        end = report.index("=== Most recent crash file ===")
        section = report[start:end]
        assert "Fatal Python error: Segmentation fault" in section

    def test_faulthandler_section_when_absent(self, monkeypatch, tmp_path: Path):
        from ytm_player.config import paths
        from ytm_player.utils.doctor import gather_diagnostics

        crash_dir = tmp_path / "crashes"
        crash_dir.mkdir()
        monkeypatch.setattr(paths, "CRASH_DIR", crash_dir)

        report = gather_diagnostics()
        start = report.index("=== Most recent faulthandler trace ===")
        end = report.index("=== Most recent crash file ===")
        section = report[start:end]
        body = section.lower()
        assert "no faulthandler trace" in body or "(empty" in body

    def test_active_hooks_section_lists_all(self):
        from ytm_player.utils.doctor import gather_diagnostics

        report = gather_diagnostics()
        start = report.index("=== Active hooks ===")
        section = report[start:]
        assert "sys.excepthook" in section
        assert "threading.excepthook" in section
        assert "sys.unraisablehook" in section
        assert "faulthandler" in section
