"""Queue management page showing the playback queue."""

from __future__ import annotations

import logging
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable, Input, Label, Static
from textual.widgets.data_table import RowKey

from ytm_player.config.keymap import Action
from ytm_player.services.player import PlayerEvent
from ytm_player.services.queue import RepeatMode
from ytm_player.utils.formatting import extract_artist, extract_duration, format_duration

logger = logging.getLogger(__name__)


class QueuePage(Widget):
    """Displays and manages the playback queue.

    Shows the currently playing track at the top, the upcoming queue in a
    table, and repeat/shuffle state in a footer bar. Supports reordering,
    removal, and jumping to tracks.
    """

    DEFAULT_CSS = """
    QueuePage {
        layout: vertical;
        width: 1fr;
        height: 1fr;
    }
    .queue-now-playing {
        height: auto;
        max-height: 3;
        padding: 1 2;
        background: $surface;
    }
    .queue-now-playing-title {
        text-style: bold;
        color: $success;
    }
    .queue-now-playing-artist {
        color: $text-muted;
    }
    .queue-table {
        height: 1fr;
        width: 1fr;
    }
    .queue-table > .datatable--cursor {
        background: $selected-item;
    }
    .queue-footer {
        height: 1;
        padding: 0 2;
        color: $text-muted;
        dock: bottom;
    }
    .queue-empty {
        width: 1fr;
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
    }
    .track-filter {
        dock: bottom;
        display: none;
    }
    .track-filter.visible {
        display: block;
    }
    """

    queue_length: reactive[int] = reactive(0)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._row_keys: list[RowKey] = []
        self._track_change_callback: Any = None
        # Filter state — maps visible row index → real queue index.
        self._filter_text: str = ""
        self._filtered_indices: list[int] = []
        self._filter_timer: Any = None

    def compose(self) -> ComposeResult:
        yield Vertical(id="queue-header", classes="queue-now-playing")
        yield Label("Queue is empty.", id="queue-empty", classes="queue-empty")
        yield DataTable(
            cursor_type="row",
            zebra_stripes=True,
            id="queue-table",
            classes="queue-table",
        )
        yield Static("", id="queue-footer", classes="queue-footer")
        yield Input(placeholder="/ Filter tracks...", id="track-filter", classes="track-filter")

    def on_mount(self) -> None:
        table = self.query_one("#queue-table", DataTable)
        table.add_column("#", width=4, key="index")
        table.add_column("Title", width=None, key="title")
        table.add_column("Artist", width=None, key="artist")
        table.add_column("Duration", width=8, key="duration")

        self._register_player_events()
        self._refresh_queue()

    def on_unmount(self) -> None:
        self._unregister_player_events()

    # ── Player event integration ──────────────────────────────────────

    def _register_player_events(self) -> None:
        player = self.app.player  # type: ignore[attr-defined]
        self._track_change_callback = self._on_track_change
        player.on(PlayerEvent.TRACK_CHANGE, self._track_change_callback)

    def _unregister_player_events(self) -> None:
        try:
            player = self.app.player  # type: ignore[attr-defined]
            if self._track_change_callback:
                player.off(PlayerEvent.TRACK_CHANGE, self._track_change_callback)
        except Exception:
            logger.debug("Failed to unregister player events in queue page", exc_info=True)

    def _on_track_change(self, _track_info: dict) -> None:
        """Update the queue display when the track changes.

        Does a lightweight update (header + play indicator) instead of
        rebuilding the entire DataTable.

        Player events are dispatched onto the asyncio loop via
        ``call_soon_threadsafe`` (see services/player.py), so this
        callback already runs on the main thread — call directly.
        """
        try:
            self._update_current_track()
        except Exception:
            logger.debug("Failed to update queue page on track change", exc_info=True)

    def _update_current_track(self) -> None:
        """Lightweight update: refresh header and play indicator without rebuilding the table."""
        queue = self.app.queue  # type: ignore[attr-defined]
        current_index = queue.current_index
        current_track = queue.current_track

        # Update the "Now Playing" header.
        header = self.query_one("#queue-header", Vertical)
        header.remove_children()
        if current_track:
            title = current_track.get("title", "Unknown")
            artist = current_track.get("artist", "Unknown")
            header.mount(Label(f"Now Playing: {title}", classes="queue-now-playing-title"))
            header.mount(Label(artist, classes="queue-now-playing-artist"))
            header.display = True
        else:
            header.display = False

        # Update the play indicator column without clearing/rebuilding rows.
        table = self.query_one("#queue-table", DataTable)
        for i, row_key in enumerate(self._row_keys):
            indicator = "\u25b6" if i == current_index else str(i + 1)
            try:
                table.update_cell(row_key, "index", indicator)
            except Exception:
                # Row may have been removed; fall back to full refresh.
                self._refresh_queue()
                return

    # ── Queue rendering ───────────────────────────────────────────────

    def _refresh_queue(self) -> None:
        """Rebuild the entire queue display from the QueueManager state."""
        queue = self.app.queue  # type: ignore[attr-defined]
        tracks = queue.tracks
        current_index = queue.current_index
        current_track = queue.current_track

        # Update the "Now Playing" header.
        header = self.query_one("#queue-header", Vertical)
        header.remove_children()
        if current_track:
            title = current_track.get("title", "Unknown")
            artist = current_track.get("artist", "Unknown")
            header.mount(Label(f"Now Playing: {title}", classes="queue-now-playing-title"))
            header.mount(Label(artist, classes="queue-now-playing-artist"))
            header.display = True
        else:
            header.display = False

        # Build the queue table with upcoming tracks (everything except current).
        table = self.query_one("#queue-table", DataTable)
        table.clear()
        self._row_keys = []
        self._filtered_indices = []

        # Show all tracks; the current one gets a play indicator.
        if not tracks:
            table.display = False
            self.query_one("#queue-empty").display = True
        else:
            table.display = True
            self.query_one("#queue-empty").display = False

            for i, track in enumerate(tracks):
                if self._filter_text and not self._matches_filter(track, self._filter_text):
                    continue
                self._filtered_indices.append(i)
                title = track.get("title", "Unknown")
                artist = extract_artist(track)
                dur = extract_duration(track)
                dur_str = format_duration(dur) if dur else "--:--"
                indicator = "\u25b6" if i == current_index else str(i + 1)

                row_key = table.add_row(
                    indicator,
                    title,
                    artist,
                    dur_str,
                    key=f"q_{i}",
                )
                self._row_keys.append(row_key)

        self.queue_length = len(tracks)
        self._update_footer()

    def _update_footer(self) -> None:
        """Update the footer bar with repeat, shuffle, and track count info."""
        queue = self.app.queue  # type: ignore[attr-defined]
        repeat = queue.repeat_mode
        shuffle = queue.shuffle_enabled
        count = queue.length

        repeat_label = {
            RepeatMode.OFF: "Off",
            RepeatMode.ALL: "All",
            RepeatMode.ONE: "One",
        }.get(repeat, "Off")

        shuffle_label = "On" if shuffle else "Off"
        footer_text = f"Repeat: {repeat_label}  Shuffle: {shuffle_label}  Tracks: {count}"

        try:
            footer = self.query_one("#queue-footer", Static)
            footer.update(footer_text)
        except Exception:
            logger.debug("Failed to update queue footer", exc_info=True)

    # ── DataTable events ──────────────────────────────────────────────

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Jump to and play the selected track."""
        event.stop()
        idx = self._resolve_row_idx(event.cursor_row)
        if idx is None:
            return
        queue = self.app.queue  # type: ignore[attr-defined]
        track = queue.jump_to(idx)
        if track:
            await self.app.play_track(track)  # type: ignore[attr-defined]
            self._refresh_queue()

    # ── Action handling ───────────────────────────────────────────────

    async def handle_action(self, action: Action, count: int = 1) -> None:
        """Process vim-style navigation and queue management actions."""
        table = self.query_one("#queue-table", DataTable)
        queue = self.app.queue  # type: ignore[attr-defined]

        match action:
            case Action.MOVE_DOWN:
                for _ in range(count):
                    table.action_cursor_down()

            case Action.MOVE_UP:
                for _ in range(count):
                    table.action_cursor_up()

            case Action.PAGE_DOWN:
                table.action_scroll_down()

            case Action.PAGE_UP:
                table.action_scroll_up()

            case Action.GO_TOP:
                if table.row_count > 0:
                    table.move_cursor(row=0)

            case Action.GO_BOTTOM:
                if table.row_count > 0:
                    table.move_cursor(row=table.row_count - 1)

            case Action.JUMP_TO_CURRENT:
                # Find the current queue index in the visible (filtered) rows.
                cur = queue.current_index
                if cur is not None:
                    if self._filter_text:
                        for visible_row, real_idx in enumerate(self._filtered_indices):
                            if real_idx == cur:
                                table.move_cursor(row=visible_row)
                                break
                    elif 0 <= cur < table.row_count:
                        table.move_cursor(row=cur)

            case Action.SELECT:
                idx = self._resolve_row_idx(table.cursor_row)
                if idx is not None:
                    track = queue.jump_to(idx)
                    if track:
                        await self.app.play_track(track)  # type: ignore[attr-defined]
                        self._refresh_queue()

            # Remove selected track from queue (d d / delete key).
            case Action.DELETE_ITEM:
                self._remove_selected(table, queue)

            case Action.FILTER:
                self._show_filter()

            # Reorder: move track up (C-k).
            case Action.FOCUS_PREV if self._is_reorder_context():
                self._move_track(table, queue, direction=-1)

            # Reorder: move track down (C-j).
            case Action.FOCUS_NEXT if self._is_reorder_context():
                self._move_track(table, queue, direction=1)

            case Action.CYCLE_REPEAT:
                queue.cycle_repeat()
                self._update_footer()

            case Action.TOGGLE_SHUFFLE:
                queue.toggle_shuffle()
                self._refresh_queue()

    def _is_reorder_context(self) -> bool:
        """Always allow reorder in the queue page."""
        return True

    def _remove_selected(self, table: DataTable, queue: Any) -> None:
        """Remove the currently highlighted track from the queue."""
        idx = self._resolve_row_idx(table.cursor_row)
        if idx is None:
            return
        if 0 <= idx < queue.length:
            queue.remove(idx)
            self._refresh_queue()
            # Keep cursor in bounds after removal.
            if table.row_count > 0:
                visible_row = table.cursor_row
                if visible_row is not None:
                    new_row = min(visible_row, table.row_count - 1)
                    table.move_cursor(row=new_row)

    def _move_track(self, table: DataTable, queue: Any, direction: int) -> None:
        """Move the highlighted track up or down in the queue."""
        from_idx = self._resolve_row_idx(table.cursor_row)
        if from_idx is None:
            return
        to_idx = from_idx + direction
        if not (0 <= to_idx < queue.length):
            return
        queue.move(from_idx, to_idx)
        self._refresh_queue()
        # When unfiltered, the cursor follows the moved row; when filtered,
        # the visible position may not match — keep cursor where it was.
        if not self._filter_text:
            table.move_cursor(row=to_idx)

    # ── Filter helpers ───────────────────────────────────────────────

    def _resolve_row_idx(self, row: int | None) -> int | None:
        """Map a visible row index to the real queue index."""
        if row is None:
            return None
        if self._filter_text:
            if 0 <= row < len(self._filtered_indices):
                return self._filtered_indices[row]
            return None
        queue = self.app.queue  # type: ignore[attr-defined]
        if 0 <= row < queue.length:
            return row
        return None

    @staticmethod
    def _matches_filter(track: dict, query: str) -> bool:
        title = (track.get("title") or "").lower()
        artist = extract_artist(track).lower()
        return query in title or query in artist

    def _show_filter(self) -> None:
        try:
            f = self.query_one("#track-filter", Input)
            f.value = ""
            f.add_class("visible")
            f.focus()
        except Exception:
            pass

    def _hide_filter(self) -> None:
        try:
            f = self.query_one("#track-filter", Input)
            f.remove_class("visible")
            self.query_one("#queue-table", DataTable).focus()
        except Exception:
            pass

    def _apply_filter(self, query: str) -> None:
        self._filter_text = query.strip().lower()
        if self._filter_timer is not None:
            try:
                self._filter_timer.stop()
            except Exception:
                pass
            self._filter_timer = None
        if not self._filter_text:
            self._refresh_queue()
            return
        self._filter_timer = self.set_timer(0.15, self._refresh_queue)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "track-filter":
            self._apply_filter(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "track-filter":
            self._hide_filter()

    def on_key(self, event: object) -> None:
        from textual.events import Key

        if not isinstance(event, Key):
            return
        if event.key == "escape":
            try:
                f = self.query_one("#track-filter", Input)
                if f.has_class("visible"):
                    event.stop()
                    event.prevent_default()
                    self._filter_text = ""
                    self._refresh_queue()
                    self._hide_filter()
            except Exception:
                pass
