"""Tests for LibraryPanel.update_item_count."""

from __future__ import annotations

from ytm_player.ui.sidebars.playlist_sidebar import LibraryPanel


def _make_item(playlist_id: str, count: int | None, title: str = "Test"):
    return {"playlistId": playlist_id, "title": title, "count": count}


def test_update_item_count_increments_existing():
    panel = LibraryPanel.__new__(LibraryPanel)
    panel._items = [_make_item("PL1", 5)]
    panel._filtered_items = list(panel._items)
    panel.update_item_count("PL1", +3)
    assert panel._items[0]["count"] == 8


def test_update_item_count_decrements_existing():
    panel = LibraryPanel.__new__(LibraryPanel)
    panel._items = [_make_item("PL1", 10)]
    panel._filtered_items = list(panel._items)
    panel.update_item_count("PL1", -2)
    assert panel._items[0]["count"] == 8


def test_update_item_count_handles_vl_prefix():
    """playlist_id with VL prefix matches against item without it (and vice versa)."""
    panel = LibraryPanel.__new__(LibraryPanel)
    panel._items = [_make_item("PL1", 5)]
    panel._filtered_items = list(panel._items)
    panel.update_item_count("VLPL1", +2)
    assert panel._items[0]["count"] == 7


def test_update_item_count_none_count_stays_none():
    """If count is None (unknown), don't fabricate a value — leave None."""
    panel = LibraryPanel.__new__(LibraryPanel)
    panel._items = [_make_item("PL1", None)]
    panel._filtered_items = list(panel._items)
    panel.update_item_count("PL1", +3)
    assert panel._items[0]["count"] is None


def test_update_item_count_unknown_playlist_is_noop():
    """Unknown playlist ID is silently ignored."""
    panel = LibraryPanel.__new__(LibraryPanel)
    panel._items = [_make_item("PL1", 5)]
    panel._filtered_items = list(panel._items)
    panel.update_item_count("PLnonexistent", +3)
    assert panel._items[0]["count"] == 5
