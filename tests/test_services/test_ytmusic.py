"""Tests for YTMusicService._call() error handling and client thread-safety.

These tests cover Tasks 4.1 + 4.2 of the audit-driven cleanup:

- 4.1: ``_call()`` narrows its outer ``except`` so that programming-error
  exceptions (TypeError, AttributeError, etc.) propagate without bumping the
  consecutive-failure counter or triggering a spurious client reinit.
- 4.2: ``YTMusicService.client`` lazy init is guarded by a ``threading.Lock``
  with double-checked locking so concurrent first-accesses from
  ``asyncio.to_thread`` workers don't both build a fresh ``YTMusic`` instance.
"""

from __future__ import annotations

import asyncio
import threading
from unittest.mock import MagicMock

import pytest
import requests


@pytest.fixture
def ytmusic_service():
    """Construct YTMusicService with a fake client (bypasses __init__)."""
    from ytm_player.services.ytmusic import YTMusicService

    svc = YTMusicService.__new__(YTMusicService)
    svc._auth_path = MagicMock()
    svc._auth_manager = None
    svc._user = None
    svc._consecutive_api_failures = 0
    svc._client_init_lock = threading.Lock()
    svc._order_lock = asyncio.Lock()
    svc._ytm = MagicMock(name="fake-ytm-client")
    return svc


class TestCallNarrowedCatch:
    """Task 4.1: ``_call()`` outer except is narrowed to expected types."""

    async def test_call_propagates_unexpected_exceptions_unmasked(self, ytmusic_service):
        """A TypeError (programming bug) must propagate without bumping the
        failure counter or clearing _ytm.
        """

        def boom(*_args, **_kwargs):
            raise TypeError("expected str, got None")

        original_client = ytmusic_service._ytm

        with pytest.raises(TypeError, match="expected str"):
            await ytmusic_service._call(boom)

        assert ytmusic_service._consecutive_api_failures == 0, (
            "Programming-error exceptions must NOT increment the failure counter."
        )
        assert ytmusic_service._ytm is original_client, (
            "Programming-error exceptions must NOT trigger a client reinit."
        )

    async def test_call_increments_counter_only_on_expected_api_errors(self, ytmusic_service):
        """A requests.ConnectionError IS expected — it bumps the counter, but
        below threshold the client is NOT cleared.
        """

        def network_failure(*_args, **_kwargs):
            raise requests.ConnectionError("network unreachable")

        original_client = ytmusic_service._ytm

        for _ in range(2):
            with pytest.raises(requests.ConnectionError):
                await ytmusic_service._call(network_failure)

        assert ytmusic_service._consecutive_api_failures == 2
        assert ytmusic_service._ytm is original_client, (
            "Below the reinit threshold, the client must not be cleared."
        )

    async def test_call_reinits_client_after_threshold(self, ytmusic_service):
        """After 3 consecutive expected failures, _ytm is cleared (reinit
        signal) and the counter is reset.
        """

        def timeout_failure(*_args, **_kwargs):
            raise asyncio.TimeoutError("api timed out")

        for _ in range(3):
            with pytest.raises(asyncio.TimeoutError):
                await ytmusic_service._call(timeout_failure)

        assert ytmusic_service._ytm is None, (
            "After the failure threshold, _ytm must be cleared so the next "
            ".client access rebuilds it."
        )
        assert ytmusic_service._consecutive_api_failures == 0, (
            "The failure counter must be reset after a reinit."
        )


class TestClientThreadSafety:
    """Task 4.2: ``client`` property is thread-safe under concurrent first-access."""

    def test_client_property_is_thread_safe_under_concurrent_first_access(self, monkeypatch):
        """Four threads call ``service.client`` simultaneously when ``_ytm`` is
        ``None``. Only one ``YTMusic`` instance must be created and all four
        threads must see the same instance.
        """
        from ytm_player.services.ytmusic import YTMusicService

        construction_count = 0
        construction_lock = threading.Lock()

        def fake_ytmusic_ctor(*_args, **_kwargs):
            nonlocal construction_count
            with construction_lock:
                construction_count += 1
            # Sleep briefly so a second thread is very likely to enter the
            # outer ``if self._ytm is None`` check while the first is still
            # constructing — this is exactly the race the lock prevents.
            import time

            time.sleep(0.05)
            return MagicMock(name=f"ytm-mock-{construction_count}")

        monkeypatch.setattr("ytm_player.services.ytmusic.YTMusic", fake_ytmusic_ctor)

        svc = YTMusicService.__new__(YTMusicService)
        svc._auth_path = MagicMock()
        svc._auth_manager = None
        svc._user = None
        svc._ytm = None
        svc._consecutive_api_failures = 0
        svc._client_init_lock = threading.Lock()
        svc._order_lock = asyncio.Lock()

        n_threads = 4
        barrier = threading.Barrier(n_threads)
        results: list[int] = []
        results_lock = threading.Lock()

        def worker():
            barrier.wait()  # all threads punch through together
            client = svc.client
            with results_lock:
                results.append(id(client))

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == n_threads
        assert len(set(results)) == 1, (
            f"All {n_threads} threads must see the same client instance; "
            f"got {len(set(results))} distinct instances."
        )
        assert construction_count == 1, (
            f"YTMusic constructor must be called exactly once under the lock; "
            f"was called {construction_count} times."
        )
