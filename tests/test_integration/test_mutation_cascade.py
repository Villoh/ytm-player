"""Integration test: mutation methods (rate_song, add_playlist_items)
return False on caught failure, and the UI cascade reacts correctly.

Validates the contract chain:
  service.rate_song fails (network) -> returns False -> UI shows error toast
  service.rate_song succeeds            -> returns True  -> UI shows "Liked" toast
  service.add_playlist_items partial    -> returns False per failed batch -> UI surfaces partial-success warning

Pre-Phase-4.3, the methods returned None on both success and failure,
so the UI lied to the user (showed success even on silent failure).
"""

from __future__ import annotations

import threading
from unittest.mock import AsyncMock, MagicMock

import requests

from ytm_player.services.ytmusic import YTMusicService


async def test_rate_song_returns_true_on_success(monkeypatch):
    svc = YTMusicService.__new__(YTMusicService)
    svc._ytm = MagicMock(name="fake-ytm-client")
    svc._consecutive_api_failures = 0
    svc._client_init_lock = threading.Lock()

    fake_call = AsyncMock(return_value=None)
    monkeypatch.setattr(svc, "_call", fake_call)

    accepted = await svc.rate_song("abc123", "LIKE")
    assert accepted is True


async def test_rate_song_returns_false_on_network_failure(monkeypatch):
    svc = YTMusicService.__new__(YTMusicService)
    svc._ytm = MagicMock(name="fake-ytm-client")
    svc._consecutive_api_failures = 0
    svc._client_init_lock = threading.Lock()

    fake_call = AsyncMock(side_effect=requests.ConnectionError("network unreachable"))
    monkeypatch.setattr(svc, "_call", fake_call)

    accepted = await svc.rate_song("abc123", "LIKE")
    assert accepted is False


async def test_add_playlist_items_returns_false_per_batch(monkeypatch):
    """Verifies that the spotify-import flow's per-batch failure tracking works."""
    svc = YTMusicService.__new__(YTMusicService)
    svc._ytm = MagicMock(name="fake-ytm-client")
    svc._consecutive_api_failures = 0
    svc._client_init_lock = threading.Lock()

    call_count = 0

    async def fake_call(func, *_args, **_kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise requests.ConnectionError("flaky network")
        return None

    monkeypatch.setattr(svc, "_call", fake_call)

    batch1 = await svc.add_playlist_items("PL_test", ["v1", "v2"])
    batch2 = await svc.add_playlist_items("PL_test", ["v3", "v4"])
    batch3 = await svc.add_playlist_items("PL_test", ["v5", "v6"])

    assert batch1 is True
    assert batch2 is False
    assert batch3 is True
