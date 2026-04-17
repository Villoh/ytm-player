"""Tests for utils.doctor — diagnostic gathering for `ytm doctor`."""

from __future__ import annotations


class TestGatherDiagnostics:
    def test_includes_version(self):
        from ytm_player.utils.doctor import gather_diagnostics

        report = gather_diagnostics()
        from ytm_player import __version__

        assert __version__ in report

    def test_includes_python_version(self):
        from ytm_player.utils.doctor import gather_diagnostics

        report = gather_diagnostics()
        import sys

        assert f"{sys.version_info.major}.{sys.version_info.minor}" in report

    def test_includes_platform(self):
        from ytm_player.utils.doctor import gather_diagnostics

        report = gather_diagnostics()
        import platform

        assert platform.system() in report

    def test_includes_log_path(self):
        from ytm_player.utils.doctor import gather_diagnostics

        from ytm_player.config.paths import LOG_FILE

        report = gather_diagnostics()
        assert str(LOG_FILE) in report

    def test_includes_recent_log_section_header(self):
        from ytm_player.utils.doctor import gather_diagnostics

        report = gather_diagnostics()
        assert "Recent log" in report or "log" in report.lower()

    def test_includes_mpv_version_or_missing_marker(self):
        from ytm_player.utils.doctor import gather_diagnostics

        report = gather_diagnostics()
        # Either the mpv version is present, or the report explicitly says
        # mpv is missing/unavailable.  Don't crash if mpv isn't installed.
        assert "mpv" in report.lower()
