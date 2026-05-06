"""Tests for ytm_player.services.auth."""

import json
from pathlib import Path
from unittest import mock

from ytm_player.services.auth import AuthManager, _normalize_raw_headers


class TestStandardFormat:
    """Standard 'Name: Value' per line (Firefox / older Chrome)."""

    def test_standard_headers_preserved(self):
        raw = "cookie: abc=123\nauthorization: Bearer xyz"
        result = _normalize_raw_headers(raw)
        assert "cookie: abc=123" in result
        assert "authorization: Bearer xyz" in result

    def test_pseudo_headers_stripped(self):
        raw = (
            ":authority: music.youtube.com\n"
            ":method: POST\n"
            ":path: /youtubei/v1/browse\n"
            ":scheme: https\n"
            "cookie: abc=123\n"
            "authorization: Bearer xyz"
        )
        result = _normalize_raw_headers(raw)
        assert ":authority" not in result
        assert ":method" not in result
        assert ":path" not in result
        assert ":scheme" not in result
        assert "cookie: abc=123" in result
        assert "authorization: Bearer xyz" in result


class TestAlternatingLines:
    """Chrome 'Copy request headers' alternating name/value lines."""

    def test_alternating_lines_paired(self):
        raw = "cookie\nabc=123\nauthorization\nBearer xyz"
        result = _normalize_raw_headers(raw)
        assert "cookie: abc=123" in result
        assert "authorization: Bearer xyz" in result

    def test_pseudo_headers_stripped_in_alternating(self):
        raw = (
            ":authority\nmusic.youtube.com\n:method\nPOST\ncookie\nabc=123\nuser-agent\nMozilla/5.0"
        )
        result = _normalize_raw_headers(raw)
        assert ":authority" not in result
        assert ":method" not in result
        assert "cookie: abc=123" in result
        assert "user-agent: Mozilla/5.0" in result


class TestEscapeSeparated:
    """Terminal paste with ^[E separators (single line)."""

    def test_caret_escape_separated(self):
        raw = "cookie^[Eabc=123^[Eauthorization^[EBearer xyz"
        result = _normalize_raw_headers(raw)
        assert "cookie: abc=123" in result
        assert "authorization: Bearer xyz" in result

    def test_pseudo_headers_stripped_in_escape_format(self):
        raw = ":authority^[Emusic.youtube.com^[Ecookie^[Eabc=123"
        result = _normalize_raw_headers(raw)
        assert ":authority" not in result
        assert "cookie: abc=123" in result


class TestEdgeCases:
    def test_empty_input_returns_empty(self):
        assert _normalize_raw_headers("") == ""

    def test_single_standard_header(self):
        result = _normalize_raw_headers("cookie: session=abc")
        assert result == "cookie: session=abc"

    def test_whitespace_only_returns_empty(self):
        assert _normalize_raw_headers("   \n   \n  ") == ""


class TestOAuthAuthentication:
    """OAuth authentication detection and client creation."""

    def test_is_oauth_authenticated_missing_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("ytm_player.services.auth.OAUTH_FILE", tmp_path / "oauth.json")
        auth = AuthManager(auth_file=tmp_path / "auth.json")
        assert not auth.is_oauth_authenticated()

    def test_is_oauth_authenticated_with_refresh_token(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("ytm_player.services.auth.OAUTH_FILE", tmp_path / "oauth.json")
        auth = AuthManager(auth_file=tmp_path / "auth.json")
        (tmp_path / "oauth.json").write_text(json.dumps({"refresh_token": "abc123"}))
        assert auth.is_oauth_authenticated()

    def test_is_oauth_authenticated_without_refresh_token(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("ytm_player.services.auth.OAUTH_FILE", tmp_path / "oauth.json")
        auth = AuthManager(auth_file=tmp_path / "auth.json")
        (tmp_path / "oauth.json").write_text(json.dumps({"access_token": "xyz"}))
        assert not auth.is_oauth_authenticated()

    def test_is_authenticated_prefers_oauth(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("ytm_player.services.auth.OAUTH_FILE", tmp_path / "oauth.json")
        auth = AuthManager(auth_file=tmp_path / "auth.json")
        # No cookie auth, no OAuth
        assert not auth.is_authenticated()

        # OAuth present
        (tmp_path / "oauth.json").write_text(json.dumps({"refresh_token": "rt"}))
        assert auth.is_authenticated()

    def test_create_ytmusic_client_prefers_oauth(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("ytm_player.services.auth.OAUTH_FILE", tmp_path / "oauth.json")
        monkeypatch.setattr(
            "ytm_player.services.auth.OAUTH_CREDS_FILE", tmp_path / "creds.json"
        )

        auth = AuthManager(auth_file=tmp_path / "auth.json")
        (tmp_path / "oauth.json").write_text(json.dumps({"refresh_token": "rt"}))
        (tmp_path / "creds.json").write_text(
            json.dumps({"client_id": "id", "client_secret": "sec"})
        )

        with mock.patch("ytm_player.services.auth.YTMusic") as MockYTM:
            auth.create_ytmusic_client(user="test")
            MockYTM.assert_called_once_with(
                str(tmp_path / "oauth.json"),
                user="test",
                oauth_credentials=mock.ANY,
            )

    def test_try_auto_refresh_skips_oauth(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("ytm_player.services.auth.OAUTH_FILE", tmp_path / "oauth.json")
        auth = AuthManager(auth_file=tmp_path / "auth.json")
        (tmp_path / "oauth.json").write_text(json.dumps({"refresh_token": "rt"}))
        # Should return True immediately without attempting browser/cookie refresh
        assert auth.try_auto_refresh() is True
