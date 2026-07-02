"""The unified track-filter mixin (TrackFilterHost).

The five track-list pages share one filter stack via ``TrackFilterHost``.
These tests pin that no page drifts back to a local copy and that the
shared handlers behave identically: ``/`` reveals+focuses the filter input,
Enter hides the input while keeping the filter, and Escape clears the
filter, hides the input and refocuses the table — always stopping the
event so nothing leaks to the app level.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from textual.events import Key

from ytm_player.ui.pages.context import ContextPage
from ytm_player.ui.pages.library import LibraryPage
from ytm_player.ui.pages.liked_songs import LikedSongsPage
from ytm_player.ui.pages.queue import QueuePage
from ytm_player.ui.pages.recently_played import RecentlyPlayedPage
from ytm_player.ui.track_filter import TrackFilterHost

ALL_PAGES = [
    ContextPage,
    LibraryPage,
    QueuePage,
    LikedSongsPage,
    RecentlyPlayedPage,
]


def _make_page(page_cls):
    """Build a page instance whose ``query_one`` returns fake widgets.

    Returns the page plus the fake filter input and fake track table so
    tests can assert against them.
    """
    page = page_cls.__new__(page_cls)
    input_widget = MagicMock(name="track-filter-input")
    table = MagicMock(name="track-table")

    def query_one(selector, *args, **kwargs):
        if selector == "#track-filter":
            return input_widget
        if selector == page._filter_table_id:
            return table
        raise AssertionError(f"unexpected selector {selector!r}")

    object.__setattr__(page, "query_one", query_one)
    return page, input_widget, table


@pytest.mark.parametrize("page_cls", ALL_PAGES)
def test_page_is_track_filter_host(page_cls):
    """Every track-list page must inherit the shared filter stack."""
    assert issubclass(page_cls, TrackFilterHost)


@pytest.mark.parametrize("page_cls", ALL_PAGES)
def test_filter_requested_opens_and_focuses_input(page_cls):
    page, input_widget, _table = _make_page(page_cls)
    event = MagicMock()

    page.on_track_table_filter_requested(event)

    event.stop.assert_called_once()
    assert input_widget.value == ""
    input_widget.add_class.assert_called_once_with("visible")
    input_widget.focus.assert_called_once()


@pytest.mark.parametrize("page_cls", ALL_PAGES)
def test_escape_clears_filter_and_refocuses_table(page_cls):
    page, input_widget, table = _make_page(page_cls)
    input_widget.has_class.return_value = True
    event = MagicMock(spec=Key)
    event.key = "escape"

    page.on_key(event)

    event.stop.assert_called_once()
    event.prevent_default.assert_called_once()
    table.clear_filter.assert_called_once()
    input_widget.remove_class.assert_called_once_with("visible")
    table.focus.assert_called_once()


@pytest.mark.parametrize("page_cls", ALL_PAGES)
def test_escape_ignored_when_filter_hidden(page_cls):
    page, input_widget, table = _make_page(page_cls)
    input_widget.has_class.return_value = False
    event = MagicMock(spec=Key)
    event.key = "escape"

    page.on_key(event)

    event.stop.assert_not_called()
    table.clear_filter.assert_not_called()


@pytest.mark.parametrize("page_cls", ALL_PAGES)
def test_input_submitted_hides_input_keeps_filter(page_cls):
    page, input_widget, table = _make_page(page_cls)
    event = MagicMock()
    event.input.id = "track-filter"

    page.on_input_submitted(event)

    input_widget.remove_class.assert_called_once_with("visible")
    table.focus.assert_called_once()
    # Enter keeps the filter applied — the table must not be cleared.
    table.clear_filter.assert_not_called()


@pytest.mark.parametrize("page_cls", ALL_PAGES)
def test_input_changed_applies_filter(page_cls):
    page, _input, table = _make_page(page_cls)
    event = MagicMock()
    event.input.id = "track-filter"
    event.value = "query"

    page.on_input_changed(event)

    table.apply_filter.assert_called_once_with("query")
