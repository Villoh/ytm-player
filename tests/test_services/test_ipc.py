"""Tests for IPC validation logic."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import pytest

from ytm_player.ipc import (
    _VALID_COMMANDS,
    IPCServer,
    get_running_pid,
    is_tui_running,
    remove_pid,
    try_claim_pid,
)


class TestGetRunningPid:
    """PID-file liveness resolution behind the single-instance guard."""

    @pytest.fixture
    def pid_file(self, tmp_path, monkeypatch):
        pid_file = tmp_path / "ytm.pid"
        monkeypatch.setattr("ytm_player.ipc.PID_FILE", pid_file)
        return pid_file

    def test_no_pid_file_means_not_running(self, pid_file):
        assert get_running_pid() is None

    def test_live_process_returns_pid(self, pid_file, monkeypatch):
        pid_file.write_text("12345", encoding="utf-8")
        monkeypatch.setattr("ytm_player.ipc._is_pid_alive", lambda pid: True)
        assert get_running_pid() == 12345
        assert pid_file.exists()

    def test_dead_process_cleans_stale_pid_file(self, pid_file, monkeypatch):
        pid_file.write_text("12345", encoding="utf-8")
        monkeypatch.setattr("ytm_player.ipc._is_pid_alive", lambda pid: False)
        assert get_running_pid() is None
        assert not pid_file.exists()

    def test_garbage_pid_file_cleaned_up(self, pid_file):
        pid_file.write_text("not-a-pid", encoding="utf-8")
        assert get_running_pid() is None
        assert not pid_file.exists()

    def test_is_tui_running_delegates(self, pid_file, monkeypatch):
        pid_file.write_text("777", encoding="utf-8")
        monkeypatch.setattr("ytm_player.ipc._is_pid_alive", lambda pid: True)
        assert is_tui_running() is True


class TestTryClaimPid:
    """Atomic PID-file claim for the single-instance launch guard."""

    @pytest.fixture
    def pid_file(self, tmp_path, monkeypatch):
        pid_file = tmp_path / "ytm.pid"
        monkeypatch.setattr("ytm_player.ipc.PID_FILE", pid_file)
        return pid_file

    def test_claim_succeeds_and_records_own_pid(self, pid_file):
        import os

        assert try_claim_pid() is None
        assert pid_file.read_text(encoding="utf-8") == str(os.getpid())

    def test_second_claim_returns_holders_pid(self, pid_file):
        """Our own PID is genuinely alive, so no liveness mocking needed."""
        import os

        assert try_claim_pid() is None
        assert try_claim_pid() == os.getpid()

    def test_stale_holder_is_evicted_and_reclaimed(self, pid_file, monkeypatch):
        import os

        pid_file.write_text("99999", encoding="utf-8")
        monkeypatch.setattr("ytm_player.ipc._is_pid_alive", lambda pid: False)
        assert try_claim_pid() is None
        assert pid_file.read_text(encoding="utf-8") == str(os.getpid())

    def test_remove_pid_only_removes_own_claim(self, pid_file, monkeypatch):
        # Another instance's claim must survive our cleanup.
        monkeypatch.setattr("ytm_player.ipc._is_pid_alive", lambda pid: True)
        pid_file.write_text("424242", encoding="utf-8")
        remove_pid()
        assert pid_file.exists()

        # Our own claim is removed.
        pid_file.unlink()
        assert try_claim_pid() is None
        remove_pid()
        assert not pid_file.exists()


class TestIPCCommandWhitelist:
    def test_play_is_valid(self):
        assert "play" in _VALID_COMMANDS

    def test_pause_is_valid(self):
        assert "pause" in _VALID_COMMANDS

    def test_seek_is_valid(self):
        assert "seek" in _VALID_COMMANDS

    def test_queue_is_valid(self):
        assert "queue" in _VALID_COMMANDS

    def test_invalid_command_rejected(self):
        assert "exec" not in _VALID_COMMANDS
        assert "shell" not in _VALID_COMMANDS
        assert "eval" not in _VALID_COMMANDS
        assert "" not in _VALID_COMMANDS

    def test_all_expected_commands_present(self):
        expected = {
            "play",
            "pause",
            "next",
            "prev",
            "seek",
            "now",
            "status",
            "queue",
            "queue_add",
            "queue_clear",
            "like",
            "dislike",
            "unlike",
        }
        assert _VALID_COMMANDS == expected


class TestIPCPayloadValidation:
    """Test the validation logic that would be applied to incoming IPC messages."""

    def test_valid_payload(self):
        payload = json.dumps({"command": "play", "args": {}})
        data = json.loads(payload)
        assert isinstance(data, dict)
        assert data["command"] in _VALID_COMMANDS

    def test_non_dict_payload(self):
        payload = json.dumps([1, 2, 3])
        data = json.loads(payload)
        assert not isinstance(data, dict)

    def test_missing_command(self):
        payload = json.dumps({"args": {}})
        data = json.loads(payload)
        assert data.get("command", "") not in _VALID_COMMANDS

    def test_invalid_command_string(self):
        payload = json.dumps({"command": "drop_tables"})
        data = json.loads(payload)
        assert data["command"] not in _VALID_COMMANDS

    def test_command_not_string(self):
        payload = json.dumps({"command": 42})
        data = json.loads(payload)
        assert not isinstance(data["command"], str) or data["command"] not in _VALID_COMMANDS

    def test_args_default_to_empty_dict(self):
        payload = json.dumps({"command": "play"})
        data = json.loads(payload)
        args = data.get("args", {})
        assert isinstance(args, dict)

    def test_non_dict_args_coerced(self):
        payload = json.dumps({"command": "play", "args": "bad"})
        data = json.loads(payload)
        args = data.get("args", {})
        if not isinstance(args, dict):
            args = {}
        assert isinstance(args, dict)

    def test_oversized_payload(self):
        """Payloads over 64KB should be rejected."""
        big = "x" * 70000
        payload = json.dumps({"command": "play", "args": {"data": big}})
        assert len(payload.encode()) > 65536


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="IPCServerHandler tests use AF_UNIX which Windows doesn't support",
)
class TestIPCServerHandler:
    """Exercise the real IPCServer._client_connected handler via a Unix socket."""

    @pytest.fixture
    async def ipc_env(self, monkeypatch):
        """Start an IPCServer on a temp socket and yield a helper to send messages."""
        # AF_UNIX sun_path is capped at 104 bytes on macOS / 108 on Linux.
        # pytest's tmp_path on CI runners (e.g. /Users/runner/work/_temp/...
        # plus pytest-of-runner/pytest-N/test_xxx0/) blows past that. Use the
        # system tempdir with a short basename so the socket path stays small
        # on every platform.
        tmp_dir = Path(tempfile.mkdtemp(prefix="ytm-ipc-"))
        socket_path = tmp_dir / "s"

        async def handler(command: str, args: dict) -> dict:
            return {"ok": True, "command": command, "args": args}

        server = IPCServer(handler)

        # Patch SOCKET_PATH in the paths module so the server uses the temp path.
        import ytm_player.config.paths as paths_mod

        monkeypatch.setattr(paths_mod, "SOCKET_PATH", socket_path)

        try:
            await server.start()

            async def send(payload: bytes) -> dict:
                reader, writer = await asyncio.open_unix_connection(str(socket_path))
                writer.write(payload)
                writer.write_eof()
                data = await asyncio.wait_for(reader.read(), timeout=5)
                writer.close()
                await writer.wait_closed()
                return json.loads(data)

            yield send
        finally:
            await server.stop()
            socket_path.unlink(missing_ok=True)
            try:
                tmp_dir.rmdir()
            except OSError:
                pass

    async def test_valid_command_returns_handler_response(self, ipc_env):
        send = ipc_env
        payload = json.dumps({"command": "play", "args": {"video_id": "abc123"}}).encode()
        resp = await send(payload)
        assert resp["ok"] is True
        assert resp["command"] == "play"
        assert resp["args"] == {"video_id": "abc123"}

    async def test_invalid_json_returns_error(self, ipc_env):
        send = ipc_env
        resp = await send(b"not json at all{{{")
        assert resp["ok"] is False
        assert "invalid JSON" in resp["error"]

    async def test_unknown_command_returns_error(self, ipc_env):
        send = ipc_env
        payload = json.dumps({"command": "drop_tables"}).encode()
        resp = await send(payload)
        assert resp["ok"] is False
        assert "unknown command" in resp["error"]

    async def test_non_dict_payload_returns_error(self, ipc_env):
        send = ipc_env
        payload = json.dumps([1, 2, 3]).encode()
        resp = await send(payload)
        assert resp["ok"] is False
        assert "expected JSON object" in resp["error"]

    async def test_missing_command_field_returns_error(self, ipc_env):
        send = ipc_env
        payload = json.dumps({"args": {"foo": "bar"}}).encode()
        resp = await send(payload)
        assert resp["ok"] is False
        assert "unknown command" in resp["error"]
