"""Tests for LibraryPanel.update_item_count."""

from __future__ import annotations

from textual.message_pump import active_message_pump

from ytm_player.ui.sidebars.playlist_sidebar import LibraryPanel, PlaylistSidebar


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


def test_on_click_posts_create_button_message():
    sidebar = PlaylistSidebar.__new__(PlaylistSidebar)
    posted = []

    def fake_post_message(message):
        posted.append(message)

    class _Target:
        id = "ps-playlists-create"

    class _Event:
        widget = _Target()
        button = 1

        def stop(self):
            self.stopped = True

    event = _Event()
    sidebar.post_message = fake_post_message

    token = active_message_pump.set(sidebar)
    try:
        sidebar.on_click(event)
    finally:
        active_message_pump.reset(token)

    assert len(posted) == 1
    assert isinstance(posted[0], PlaylistSidebar.CreateButtonClicked)
    assert getattr(event, "stopped", False) is True
