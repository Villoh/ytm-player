"""Shared track-filter wiring for track-list pages.

``TrackFilterHost`` is a plain mixin (no ``__init__``, no ``super()``
calls) providing the ``/``-to-filter behaviour that every track-list page
shares: pressing ``/`` reveals a docked filter input, typing filters the
table live, Enter hides the input while keeping the filter, and Escape
clears the filter and refocuses the table.

Each host page declares ``_filter_table_id`` (the ``#id`` selector of its
``TrackTable``) and embeds :data:`TRACK_FILTER_CSS` in its ``DEFAULT_CSS``.
Textual only collects ``DEFAULT_CSS`` from ``DOMNode`` bases along a
widget's inheritance chain, so a plain ``object`` mixin's ``DEFAULT_CSS``
is ignored — hence the CSS lives in a module constant the pages concatenate
rather than on the mixin.

Under ``TYPE_CHECKING`` the mixin inherits from ``Widget`` so Pyright can
resolve ``query_one`` etc.; at runtime it inherits from ``object`` so it
stays a genuine mixin. Pages must list it BEFORE the Textual base class.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.events import Key
from textual.widgets import Input

from ytm_player.ui.widgets.track_table import TrackTable

if TYPE_CHECKING:
    from textual.widget import Widget

    _MixinBase = Widget
else:
    _MixinBase = object


TRACK_FILTER_CSS = """
.track-filter {
    dock: bottom;
    display: none;
}
.track-filter.visible {
    display: block;
}
"""


class TrackFilterHost(_MixinBase):
    """Mixin wiring the ``/`` track filter for track-list pages."""

    # ``#id`` selector of the host page's TrackTable. Set by each page.
    _filter_table_id: str

    def on_track_table_filter_requested(self, event: TrackTable.FilterRequested) -> None:
        event.stop()
        try:
            f = self.query_one("#track-filter", Input)
            f.value = ""
            f.add_class("visible")
            f.focus()
        except Exception:
            pass

    def on_track_table_filter_closed(self, event: TrackTable.FilterClosed) -> None:
        event.stop()
        try:
            f = self.query_one("#track-filter", Input)
            f.remove_class("visible")
            self.query_one(self._filter_table_id, TrackTable).focus()
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "track-filter":
            try:
                self.query_one(self._filter_table_id, TrackTable).apply_filter(event.value)
            except Exception:
                pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "track-filter":
            try:
                f = self.query_one("#track-filter", Input)
                f.remove_class("visible")
                self.query_one(self._filter_table_id, TrackTable).focus()
            except Exception:
                pass

    def on_key(self, event: object) -> None:
        """Clear the filter, hide the input and refocus the table on Escape."""
        if not isinstance(event, Key):
            return
        if event.key == "escape":
            try:
                f = self.query_one("#track-filter", Input)
                if f.has_class("visible"):
                    event.stop()
                    event.prevent_default()
                    table = self.query_one(self._filter_table_id, TrackTable)
                    table.clear_filter()
                    f.remove_class("visible")
                    table.focus()
            except Exception:
                pass
