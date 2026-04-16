"""Liked Songs page showing the user's liked music."""

from __future__ import annotations

import logging
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Click, MouseDown
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable, Input, Label, Static
from textual.widgets.data_table import RowKey

from ytm_player.config.keymap import Action
from ytm_player.config.settings import get_settings
from ytm_player.utils.formatting import (
    extract_artist,
    extract_duration,
    format_duration,
    normalize_tracks,
)

logger = logging.getLogger(__name__)


class LikedSongsPage(Widget):
    """Displays the user's Liked Music playlist."""

    DEFAULT_CSS = """
    LikedSongsPage {
        layout: vertical;
        width: 1fr;
        height: 1fr;
    }
    .liked-header {
        height: auto;
        max-height: 3;
        padding: 1 2;
        background: $surface;
    }
    .liked-header-title {
        text-style: bold;
        color: $primary;
    }
    .liked-table {
        height: 1fr;
        width: 1fr;
    }
    .liked-table > .datatable--cursor {
        background: $selected-item;
    }
    .liked-footer {
        height: 1;
        padding: 0 2;
        color: $text-muted;
        dock: bottom;
    }
    .liked-loading {
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

    track_count: reactive[int] = reactive(0)

    def __init__(self, *, cursor_row: int | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._row_keys: list[RowKey] = []
        self._tracks: list[dict] = []
        self._filtered_indices: list[int] = []
        self._filter_text: str = ""
        self._filter_timer: Any = None
        self._restore_cursor_row = cursor_row
        self._right_clicked: bool = False
        self._suppress_select_on_refocus: bool = False

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Liked Songs", classes="liked-header-title"),
            id="liked-header",
            classes="liked-header",
        )
        yield Label("Loading liked songs...", id="liked-loading", classes="liked-loading")
        yield DataTable(
            cursor_type="row",
            zebra_stripes=True,
            id="liked-table",
            classes="liked-table",
        )
        yield Static("", id="liked-footer", classes="liked-footer")
        yield Input(placeholder="/ Filter tracks...", id="track-filter", classes="track-filter")

    def on_mount(self) -> None:
        table = self.query_one("#liked-table", DataTable)
        ui = get_settings().ui

        def w(v: int) -> int | None:
            return v if v > 0 else None

        table.add_column("#", width=w(ui.col_index), key="index")
        table.add_column("Title", width=w(ui.col_title), key="title")
        table.add_column("Artist", width=w(ui.col_artist), key="artist")
        table.add_column("Duration", width=w(ui.col_duration), key="duration")
        table.display = False
        self.run_worker(self._load_liked_songs(), group="liked-load")

    # First batch size for progressive loading.
    _FIRST_BATCH = 300

    async def _load_liked_songs(self) -> None:
        ytmusic = self.app.ytmusic  # type: ignore[attr-defined]
        if not ytmusic:
            self.query_one("#liked-loading", Label).update("YouTube Music not connected.")
            return

        try:
            raw_tracks = await ytmusic.get_liked_songs(limit=self._FIRST_BATCH)
            self._tracks = normalize_tracks(raw_tracks)
        except Exception:
            logger.exception("Failed to load liked songs")
            self._tracks = []

        self._refresh_table()

        # Kick off background fetch if the first batch was full (likely more tracks).
        if len(self._tracks) >= self._FIRST_BATCH:
            self._update_footer(loading_more=True)
            self.run_worker(self._fetch_remaining_liked(), group="liked-remaining")

    def _refresh_table(self, loading_more: bool = False) -> None:
        table = self.query_one("#liked-table", DataTable)
        loading = self.query_one("#liked-loading", Label)
        table.clear()
        self._row_keys = []

        if not self._tracks:
            table.display = False
            loading.update("No liked songs found.")
            loading.display = True
            return

        loading.display = False
        table.display = True

        # Build the visible (possibly filtered) list and index map.
        self._filtered_indices = []
        for i, track in enumerate(self._tracks):
            if self._filter_text and not self._matches_filter(track, self._filter_text):
                continue
            self._filtered_indices.append(i)
            title = track.get("title", "Unknown")
            artist = extract_artist(track)
            dur = extract_duration(track)
            dur_str = format_duration(dur) if dur else "--:--"
            row_key = table.add_row(str(i + 1), title, artist, dur_str, key=f"liked_{i}")
            self._row_keys.append(row_key)

        self.track_count = len(self._tracks)
        self._update_footer(loading_more=loading_more)

        # Restore cursor position from navigation state.
        row = self._restore_cursor_row
        self._restore_cursor_row = None
        if row is not None and 0 <= row < table.row_count:
            table.move_cursor(row=row)

    def _update_footer(self, loading_more: bool = False) -> None:
        try:
            footer = self.query_one("#liked-footer", Static)
            total = len(self._tracks)
            shown = len(self._filtered_indices) if self._filter_text else total
            if self._filter_text:
                text = f"{shown}/{total} liked songs"
            else:
                text = f"{total} liked songs"
            if loading_more:
                text += " (loading more…)"
            footer.update(text)
        except Exception:
            pass

    @staticmethod
    def _matches_filter(track: dict, query: str) -> bool:
        title = (track.get("title") or "").lower()
        artist = extract_artist(track).lower()
        return query in title or query in artist

    async def _fetch_remaining_liked(self) -> None:
        """Background fetch for liked songs beyond the first batch."""
        from ytm_player.services.ytmusic import YTMusicService

        ytmusic = self.app.ytmusic  # type: ignore[attr-defined]
        if not ytmusic:
            return
        try:
            remaining_raw = await ytmusic.get_liked_songs(
                limit=None, timeout=YTMusicService._LARGE_PLAYLIST_TIMEOUT
            )
        except Exception:
            logger.debug("Background fetch for remaining liked songs failed", exc_info=True)
            self._update_footer()
            return

        # Slice off the tracks we already have.
        remaining_raw = remaining_raw[len(self._tracks) :]
        if not remaining_raw:
            self._update_footer()
            return

        remaining = normalize_tracks(remaining_raw)
        self._tracks.extend(remaining)
        # Rebuild table to honor any active filter while keeping current scroll/cursor.
        try:
            self._refresh_table()
        except Exception:
            logger.debug("Failed to append remaining liked songs", exc_info=True)

    def get_selected_track(self) -> dict | None:
        """Return the track at the cursor position (used by the context menu)."""
        try:
            table = self.query_one("#liked-table", DataTable)
            idx = self._resolve_row_idx(table.cursor_row)
            if idx is not None:
                return self._tracks[idx]
        except Exception:
            pass
        return None

    def get_nav_state(self) -> dict[str, Any]:
        """Return state to preserve when navigating away."""
        state: dict[str, Any] = {}
        try:
            table = self.query_one("#liked-table", DataTable)
            if table.cursor_row is not None and table.cursor_row > 0:
                state["cursor_row"] = table.cursor_row
        except Exception:
            pass
        return state

    def on_mouse_down(self, event: MouseDown) -> None:
        """Handle right-click on liked songs rows to open the context menu."""
        if event.button != 3:
            return
        meta = event.style.meta
        row_idx = meta.get("row") if meta else None
        idx = self._resolve_row_idx(row_idx) if row_idx is not None else None
        if idx is None:
            return
        event.stop()
        event.prevent_default()
        self._right_clicked = True
        self._suppress_select_on_refocus = True
        self.app._open_actions_for_track(self._tracks[idx])  # type: ignore[attr-defined]

    def on_click(self, event: Click) -> None:
        """Suppress right-click Click events to prevent spurious row selection."""
        if event.button == 3:
            event.stop()
            event.prevent_default()

    def _resolve_row_idx(self, row: int | None) -> int | None:
        """Map a visible row index to the original index in self._tracks."""
        if row is None:
            return None
        if self._filter_text:
            if 0 <= row < len(self._filtered_indices):
                return self._filtered_indices[row]
            return None
        if 0 <= row < len(self._tracks):
            return row
        return None

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        if self._right_clicked:
            self._right_clicked = False
            return
        if self._suppress_select_on_refocus:
            self._suppress_select_on_refocus = False
            return
        idx = self._resolve_row_idx(event.cursor_row)
        if idx is not None:
            queue = self.app.queue  # type: ignore[attr-defined]
            queue.clear()
            queue.add_multiple(self._tracks)
            queue.jump_to_real(idx)
            await self.app.play_track(self._tracks[idx])  # type: ignore[attr-defined]

    async def handle_action(self, action: Action, count: int = 1) -> None:
        table = self.query_one("#liked-table", DataTable)

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
                queue = self.app.queue  # type: ignore[attr-defined]
                current = queue.current_track if queue else None
                if current and current.get("video_id"):
                    vid = current["video_id"]
                    # Find in visible (possibly filtered) rows.
                    visible = (
                        [self._tracks[i] for i in self._filtered_indices]
                        if self._filter_text
                        else self._tracks
                    )
                    for i, t in enumerate(visible):
                        if t.get("video_id") == vid:
                            table.move_cursor(row=i)
                            break
            case Action.SELECT:
                idx = self._resolve_row_idx(table.cursor_row)
                if idx is not None:
                    queue = self.app.queue  # type: ignore[attr-defined]
                    queue.clear()
                    queue.add_multiple(self._tracks)
                    queue.jump_to_real(idx)
                    await self.app.play_track(self._tracks[idx])  # type: ignore[attr-defined]
            case Action.ADD_TO_QUEUE:
                idx = self._resolve_row_idx(table.cursor_row)
                if idx is not None:
                    queue = self.app.queue  # type: ignore[attr-defined]
                    queue.add(self._tracks[idx])
                    self.app.notify("Added to queue", timeout=2)
            case Action.FILTER:
                self._show_filter()

    # ── Filter wiring ────────────────────────────────────────────────

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
            self.query_one("#liked-table", DataTable).focus()
        except Exception:
            pass

    def _apply_filter(self, query: str) -> None:
        self._filter_text = query.strip().lower()
        # Cancel any pending debounce timer.
        if self._filter_timer is not None:
            try:
                self._filter_timer.stop()
            except Exception:
                pass
            self._filter_timer = None
        # Empty query: refresh immediately.
        if not self._filter_text:
            self._refresh_table()
            return
        self._filter_timer = self.set_timer(0.15, self._refresh_table)

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
                    self._refresh_table()
                    self._hide_filter()
            except Exception:
                pass
