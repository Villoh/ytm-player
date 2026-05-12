"""Tests for ytm_player.services.shuffle_prefs.ShufflePreferences."""

from __future__ import annotations

import json
import threading

from ytm_player.services.shuffle_prefs import _MAX_ENTRIES, ShufflePreferences


class TestBasicRoundtrip:
    def test_set_then_get(self, tmp_path):
        prefs = ShufflePreferences(tmp_path / "prefs.json")
        prefs.set("PLABCD", True)
        assert prefs.get("PLABCD") is True

    def test_set_false_then_get(self, tmp_path):
        prefs = ShufflePreferences(tmp_path / "prefs.json")
        prefs.set("MPREb_xyz", False)
        assert prefs.get("MPREb_xyz") is False

    def test_overwrite_existing(self, tmp_path):
        prefs = ShufflePreferences(tmp_path / "prefs.json")
        prefs.set("PLABCD", True)
        prefs.set("PLABCD", False)
        assert prefs.get("PLABCD") is False


class TestMissingKeys:
    def test_unknown_key_returns_none(self, tmp_path):
        prefs = ShufflePreferences(tmp_path / "prefs.json")
        assert prefs.get("never-set") is None

    def test_empty_context_id_returns_none_on_get(self, tmp_path):
        prefs = ShufflePreferences(tmp_path / "prefs.json")
        prefs.set("real", True)
        assert prefs.get("") is None
        assert prefs.get(None) is None

    def test_empty_context_id_no_op_on_set(self, tmp_path):
        prefs = ShufflePreferences(tmp_path / "prefs.json")
        prefs.set("", True)  # should not write anything
        prefs.set(None, True)
        # File should not exist (nothing was ever persisted).
        assert not (tmp_path / "prefs.json").exists()


class TestLRUEviction:
    def test_oldest_entry_evicted_when_over_cap(self, tmp_path):
        prefs = ShufflePreferences(tmp_path / "prefs.json")
        # Insert _MAX_ENTRIES + 5 unique keys.
        for i in range(_MAX_ENTRIES + 5):
            prefs.set(f"key-{i}", i % 2 == 0)

        # The first 5 inserted should have been evicted.
        for i in range(5):
            assert prefs.get(f"key-{i}") is None
        # The last one should still be there.
        assert prefs.get(f"key-{_MAX_ENTRIES + 4}") is not None

    def test_get_promotes_to_most_recent(self, tmp_path):
        prefs = ShufflePreferences(tmp_path / "prefs.json")
        # Fill exactly to capacity.
        for i in range(_MAX_ENTRIES):
            prefs.set(f"key-{i}", True)

        # Touch key-0 with a get — it should now be most-recent.
        assert prefs.get("key-0") is True

        # Insert one more — key-1 should be evicted (now oldest), not key-0.
        prefs.set("new-key", False)
        assert prefs.get("key-0") is True
        assert prefs.get("key-1") is None


class TestPersistence:
    def test_survives_new_instance(self, tmp_path):
        path = tmp_path / "prefs.json"
        a = ShufflePreferences(path)
        a.set("PLABCD", True)
        a.set("PLEFGH", False)

        b = ShufflePreferences(path)
        assert b.get("PLABCD") is True
        assert b.get("PLEFGH") is False

    def test_clear_persists(self, tmp_path):
        path = tmp_path / "prefs.json"
        a = ShufflePreferences(path)
        a.set("PLABCD", True)
        a.clear()

        b = ShufflePreferences(path)
        assert b.get("PLABCD") is None


class TestErrorTolerance:
    def test_missing_file_loads_empty(self, tmp_path):
        path = tmp_path / "does-not-exist.json"
        prefs = ShufflePreferences(path)
        assert prefs.get("anything") is None

    def test_bad_json_tolerated(self, tmp_path, caplog):
        path = tmp_path / "prefs.json"
        path.write_text("{not valid json", encoding="utf-8")
        prefs = ShufflePreferences(path)
        # Should not raise, should start empty.
        assert prefs.get("anything") is None
        # Logger should have surfaced the failure.
        assert any("Failed to load shuffle prefs" in rec.message for rec in caplog.records)

    def test_non_dict_json_tolerated(self, tmp_path):
        path = tmp_path / "prefs.json"
        path.write_text('["not", "a", "dict"]', encoding="utf-8")
        prefs = ShufflePreferences(path)
        assert prefs.get("anything") is None

    def test_non_string_keys_filtered(self, tmp_path):
        # Should never happen in practice (JSON object keys are strings),
        # but defensive filtering keeps the dict typed.
        path = tmp_path / "prefs.json"
        path.write_text(json.dumps({"good": True}), encoding="utf-8")
        prefs = ShufflePreferences(path)
        assert prefs.get("good") is True


class TestConcurrency:
    def test_concurrent_sets_no_corruption(self, tmp_path):
        """Spam set() from many threads; final state must be consistent."""
        prefs = ShufflePreferences(tmp_path / "prefs.json")

        def worker(start: int) -> None:
            for i in range(50):
                prefs.set(f"thread-{start}-key-{i}", i % 2 == 0)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 8 * 50 = 400 keys should be readable with no exceptions.
        for t in range(8):
            for i in range(50):
                assert prefs.get(f"thread-{t}-key-{i}") == (i % 2 == 0)
