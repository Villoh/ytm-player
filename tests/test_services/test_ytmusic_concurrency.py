"""Concurrency tests for YTMusicService.

The get_playlist(order=...) path monkey-patches client._send_request to
inject sort params.  Two concurrent calls would stack patches and fail to
fully restore the original — meaning a third call could see a stale
patched _send_request.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def ytmusic_service():
    """Construct YTMusicService with a fake client (bypasses __init__)."""
    from ytm_player.services.ytmusic import YTMusicService

    svc = YTMusicService.__new__(YTMusicService)
    svc._auth_path = MagicMock()
    svc._auth_manager = None
    svc._user = None
    svc._consecutive_api_failures = 0

    fake_client = MagicMock()
    # Real send_request impl we want to be restored.
    fake_client._original_send = lambda endpoint, body, *a, **kw: {"contents": []}
    fake_client._send_request = fake_client._original_send

    # get_playlist returns minimal valid response.
    def fake_get_playlist(playlist_id, **kwargs):
        return {"tracks": []}

    fake_client.get_playlist = fake_get_playlist
    svc._ytm = fake_client
    return svc


class TestSendRequestRaceCondition:
    """C3: concurrent get_playlist(order=...) must not corrupt _send_request."""

    async def test_concurrent_order_calls_restore_original_send_request(
        self, ytmusic_service
    ):
        """Run two get_playlist(order=...) calls concurrently and assert
        client._send_request is the ORIGINAL function after both complete.

        The bug: each call captures original_send = client._send_request
        BEFORE patching.  If call A patches first, call B captures the
        patched function as 'original'.  When both finish, the restore
        in B's finally block sets _send_request to A's patched function,
        not the true original.
        """
        client = ytmusic_service._ytm
        true_original = client._send_request

        # Make get_playlist take a measurable amount of time so calls overlap.
        async def fake_call(func, *args, **kwargs):
            # Simulate the work the real _call would do on a thread.
            await asyncio.sleep(0.05)
            return {"tracks": []}

        with patch.object(ytmusic_service, "_call", side_effect=fake_call):
            # Run two concurrent calls with order= so both trigger the
            # monkey-patch path.
            await asyncio.gather(
                ytmusic_service.get_playlist("PL1", order="a_to_z"),
                ytmusic_service.get_playlist("PL2", order="recently_added"),
            )

        assert client._send_request is true_original, (
            "After concurrent get_playlist(order=...) calls, client._send_request "
            "must be restored to the true original. Got a stacked/leaked patch instead."
        )
