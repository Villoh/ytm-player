"""Tests for MPRIS volume wiring and the Seeked signal (T10).

The Volume D-Bus property must forward writes to the player via the
``set_volume`` callback, ``update_volume`` must push app-side changes to
D-Bus listeners (skipping echoes of D-Bus-initiated sets), and
``emit_seeked`` must fire the Seeked signal so clients resync position.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mpris_mod():
    """Import (reload) the mpris module, skipping if dbus-fast unavailable."""
    try:
        import importlib

        from dbus_fast import Variant  # noqa: F401

        import ytm_player.services.mpris as mpris_mod

        importlib.reload(mpris_mod)
        if getattr(mpris_mod, "_PlayerInterface", None) is None:
            pytest.skip("_PlayerInterface not available")
        return mpris_mod
    except ImportError:
        pytest.skip("dbus-fast not installed")


class TestVolumeSetter:
    async def test_setter_forwards_clamped_value_to_player_callback(self, mpris_mod):
        received: list[float] = []

        async def set_volume(value: float) -> None:
            received.append(value)

        iface = mpris_mod._PlayerInterface(callbacks={"set_volume": set_volume})
        iface.Volume = 1.5  # a D-Bus client write lands on the property setter
        await asyncio.sleep(0)  # let the scheduled callback task run

        assert received == [1.0]
        assert iface.Volume == 1.0

    async def test_setter_without_callback_still_stores_value(self, mpris_mod):
        iface = mpris_mod._PlayerInterface(callbacks={})
        iface.Volume = 0.25
        assert iface.Volume == 0.25


class TestUpdateVolume:
    def _service(self, mpris_mod):
        svc = mpris_mod.MPRISService()
        iface = mpris_mod._PlayerInterface(callbacks={})
        iface.emit_properties_changed = MagicMock()
        svc._player_iface = iface
        svc._running = True
        return svc, iface

    def test_pushes_changed_volume_and_emits(self, mpris_mod):
        svc, iface = self._service(mpris_mod)

        svc.update_volume(0.55)

        assert iface._volume == 0.55
        iface.emit_properties_changed.assert_called_once_with({"Volume": 0.55})

    def test_skips_echo_of_dbus_initiated_set(self, mpris_mod):
        svc, iface = self._service(mpris_mod)
        iface._volume = 0.5

        svc.update_volume(0.5)

        iface.emit_properties_changed.assert_not_called()

    def test_clamps_out_of_range_values(self, mpris_mod):
        svc, iface = self._service(mpris_mod)

        svc.update_volume(1.7)

        assert iface._volume == 1.0

    def test_noop_when_not_running(self, mpris_mod):
        svc = mpris_mod.MPRISService()
        svc.update_volume(0.3)  # must not raise


class TestEmitSeeked:
    def test_updates_position_and_fires_signal(self, mpris_mod):
        svc = mpris_mod.MPRISService()
        iface = mpris_mod._PlayerInterface(callbacks={})
        iface.Seeked = MagicMock()
        svc._player_iface = iface
        svc._running = True

        svc.emit_seeked(42_000_000)

        assert iface._position_us == 42_000_000
        iface.Seeked.assert_called_once_with()

    def test_noop_when_not_running(self, mpris_mod):
        svc = mpris_mod.MPRISService()
        svc.emit_seeked(1)  # must not raise
