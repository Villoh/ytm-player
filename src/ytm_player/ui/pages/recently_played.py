"""Recently Played page showing play history from local SQLite database."""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING, Any, cast

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Click
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, Label, Static

from ytm_player.config.keymap import Action
from ytm_player.ui.track_filter import TRACK_FILTER_CSS, TrackFilterHost
from ytm_player.ui.widgets.track_table import TrackTable

if TYPE_CHECKING:
    from ytm_player.app._base import YTMHostBase

logger = logging.getLogger(__name__)

# Shown when the local history DB read fails (file unreadable, locked,
# corrupt schema, etc.). Distinct from the genuine empty-state message
# below so users don't see "No play history yet" when actually a disk
# error happened.
_HISTORY_LOAD_FAILED_MSG = (
    "Couldn't load history. Check the log at ~/.config/ytm-player/logs/ytm.log for details."
)


class RecentlyPlayedPage(TrackFilterHost, Widget):
    """Displays recently played tracks from the local history database."""

    _filter_table_id = "#recent-table"

    DEFAULT_CSS = (
        """
    RecentlyPlayedPage {
        layout: vertical;
        width: 1fr;
        height: 1fr;
    }
    .recent-header {
        height: auto;
        max-height: 3;
        padding: 1 2;
        background: $surface;
    }
    .recent-header-row {
        height: auto;
        width: 1fr;
    }
    .recent-header-row Label {
        width: auto;
    }
    .recent-header-title {
        text-style: bold;
        color: $primary;
    }
    #start-radio-btn {
        width: auto;
        min-width: 14;
        height: 1;
        margin: 0 0 0 1;
        padding: 0 1;
        color: $primary;
    }
    #start-radio-btn:hover {
        background: $primary 30%;
    }
    .recent-footer {
        height: 1;
        padding: 0 2;
        color: $text-muted;
        dock: bottom;
    }
    .recent-loading {
        width: 1fr;
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
    }
    """
        + TRACK_FILTER_CSS
    )

    track_count: reactive[int] = reactive(0)
    _load_failed: bool

    def __init__(self, *, cursor_row: int | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._restore_cursor_row = cursor_row
        # Set when ``_load_history`` catches an expected disk-side
        # failure so ``_display_tracks`` can render the failure message
        # instead of the genuine empty-state copy.
        self._load_failed = False

    def compose(self) -> ComposeResult:
        with Vertical(id="recent-header", classes="recent-header"):
            with Horizontal(classes="recent-header-row"):
                yield Label("Recently Played", classes="recent-header-title")
                yield Static("[▶ Start Radio]", id="start-radio-btn", markup=True)
        yield Label("Loading history...", id="recent-loading", classes="recent-loading")
        yield TrackTable(show_album=False, id="recent-table")
        yield Static("", id="recent-footer", classes="recent-footer")
        yield Input(placeholder="/ Filter tracks...", id="track-filter", classes="track-filter")

    def on_mount(self) -> None:
        self.query_one("#recent-table", TrackTable).display = False
        self.run_worker(self._load_history(), group="recent-load")

    async def _load_history(self) -> None:
        history = self.app.history  # type: ignore[attr-defined]
        if not history:
            self.query_one("#recent-loading", Label).update("History not available.")
            return

        try:
            tracks = await history.get_recently_played(limit=100)
            self._load_failed = False
        except (OSError, sqlite3.Error):
            # Local DB failure: file unreadable, disk full, DB locked,
            # schema mismatch, corrupt page, etc. Programming errors
            # (TypeError, AttributeError) are NOT caught here — they
            # must propagate so bugs surface in development per the
            # error-handling architecture in CLAUDE.md.
            logger.exception("Failed to load play history")
            tracks = []
            self._load_failed = True

        self._display_tracks(tracks)

    def _display_tracks(self, tracks: list[dict]) -> None:
        table = self.query_one("#recent-table", TrackTable)
        loading = self.query_one("#recent-loading", Label)

        if not tracks:
            table.display = False
            if self._load_failed:
                loading.update(_HISTORY_LOAD_FAILED_MSG)
            else:
                loading.update("No play history yet. Start listening!")
            loading.display = True
            return

        loading.display = False
        table.display = True
        table.load_tracks(tracks)

        self.track_count = len(tracks)
        footer = self.query_one("#recent-footer", Static)
        footer.update(f"{len(tracks)} recently played tracks")

        # Restore cursor position from navigation state.
        row = self._restore_cursor_row
        self._restore_cursor_row = None
        if row is not None and 0 <= row < table.row_count:
            table.move_cursor(row=row)

        # Land keyboard focus on the table so Tab / j / k have a starting point.
        table.focus()

    def get_nav_state(self) -> dict[str, Any]:
        """Return state to preserve when navigating away."""
        state: dict[str, Any] = {}
        try:
            table = self.query_one("#recent-table", TrackTable)
            if table.cursor_row is not None and table.cursor_row > 0:
                state["cursor_row"] = table.cursor_row
        except Exception:
            pass
        return state

    _CONTEXT_ID = "__RECENTLY_PLAYED__"

    async def on_track_table_track_selected(self, event: TrackTable.TrackSelected) -> None:
        """Replace the queue with the history list and play the selection.

        Replacing (not appending) matches every other page — appending made
        repeated selections pile up duplicates in the live queue.
        """
        event.stop()
        table = self.query_one("#recent-table", TrackTable)
        host = cast("YTMHostBase", self.app)
        await host._replace_queue_and_play(
            table.tracks,
            entity_id=self._CONTEXT_ID,
            start_index=event.index,
            autoplay=False,
        )
        await host.play_track(event.track)

    async def handle_action(self, action: Action, count: int = 1) -> None:
        table = self.query_one("#recent-table", TrackTable)

        match action:
            case _:
                await table.handle_action(action, count)

    def on_click(self, event: Click) -> None:
        if event.widget is not None and event.widget.id == "start-radio-btn":
            event.stop()
            self.run_worker(self._start_radio(), name="start_radio", exclusive=True)

    async def _start_radio(self) -> None:
        import random

        table = self.query_one("#recent-table", TrackTable)
        tracks = table.tracks
        if not tracks:
            return
        seeds = random.sample(tracks, min(5, len(tracks)))
        host = cast("YTMHostBase", self.app)
        await host._fetch_and_play_radio(seeds, label="Radio: Recently Played")
