"""Shared fixtures for integration tests.

Pattern: real services wired together, mocked at the outermost boundary.

- HTTP via `responses` (replaces requests.Session calls inside ytmusicapi)
- mpv at the FFI boundary via existing test stubs
- Disk via tmp_path
- Singletons reset between tests so parallel runs don't collide

Why this layer exists: unit tests in tests/test_services/ mock at the
service boundary (e.g., they pass a fake YTMusic to the service). Integration
tests at this layer build real services wired together and only mock the
external systems (HTTP, FFI, disk) so the cross-service contracts are
exercised end-to-end.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
import responses as _responses_lib

from ytm_player.services.player import Player
from ytm_player.services.queue import QueueManager
from ytm_player.services.ytmusic import YTMusicService


@pytest.fixture(autouse=True)
def _reset_singletons() -> Iterator[None]:
    """Reset class-level singleton state between integration tests.

    Player has a class-level ``_instance`` singleton; QueueManager has its
    own singleton in newer versions. Without this, parallel test runs
    collide on shared state.
    """
    yield
    if getattr(Player, "_instance", None) is not None:
        Player._instance = None
    # YTMusicService is per-instance, but its consecutive-failures state
    # can leak across tests via fixture reuse. Defensive reset.
    YTMusicService._consecutive_api_failures = 0


@pytest.fixture
def fresh_ytmusic(monkeypatch: pytest.MonkeyPatch) -> YTMusicService:
    """A YTMusicService with its lazy `_ytm` cleared so tests can stub.

    Tests typically follow this pattern:

        def test_something(fresh_ytmusic, monkeypatch):
            monkeypatch.setattr(fresh_ytmusic, "search", lambda *a, **kw: [...])
            # ...

    Or for HTTP-level mocking via responses, leave fresh_ytmusic alone and
    use the `mocked_http` fixture to stage HTTP responses.
    """
    svc = YTMusicService()
    svc._ytm = None
    return svc


@pytest.fixture
def fresh_queue() -> QueueManager:
    """A clean QueueManager instance per test."""
    qm = QueueManager()
    qm.clear()
    return qm


@pytest.fixture
def mocked_http() -> Iterator[_responses_lib.RequestsMock]:
    """Yield a `responses.RequestsMock` that patches `requests.Session`.

    Use in tests that exercise ytmusicapi paths — register expected HTTP
    responses, call the service, assert the call shape.

    `assert_all_requests_are_fired=False` because some integration tests
    don't care about every URL the service might hit; they assert on the
    behavior, not the HTTP traffic shape.
    """
    with _responses_lib.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


@pytest.fixture
def mock_mpv(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace ``services.player.mpv`` with a MagicMock for tests that
    exercise Player. Player's services.player module already substitutes
    a stub at import time when libmpv is missing; this fixture is for
    tests that want to assert specific mpv calls were made.
    """
    fake = MagicMock(name="fake_mpv_module")
    fake.MPV.return_value = MagicMock(name="fake_MPV_instance")
    monkeypatch.setattr("ytm_player.services.player.mpv", fake)
    return fake
