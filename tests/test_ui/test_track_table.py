"""Tests for TrackTable widget."""

from __future__ import annotations

from textual.app import App, ComposeResult

from ytm_player.ui.widgets.track_table import TrackTable


class _Host(App):
    """Minimal host that provides the theme variables TrackTable's CSS needs."""

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        variables["selected-item"] = "#3a3a3a"
        return variables


def _column_keys(table: TrackTable) -> set[str]:
    return {c.value for c in table.columns if c.value is not None}


async def test_load_tracks_immediately_after_construction():
    """Regression: see context._build_artist nested-mount path.

    Before option C (column setup moved from on_mount to __init__), a
    caller that constructed a TrackTable and called load_tracks
    synchronously — before on_mount fired — hit add_row with 0 columns
    and raised "More values provided than there are columns".

    This test reproduces that scenario: load_tracks runs during compose,
    so on_mount has not yet fired. With option C in place, columns exist
    at construction time and load_tracks succeeds.
    """

    captured: dict[str, int] = {}

    class _LoadDuringCompose(_Host):
        def compose(self) -> ComposeResult:
            table = TrackTable(show_index=True, show_album=False)
            table.load_tracks(
                [
                    {
                        "video_id": "abc",
                        "title": "Test Track",
                        "artist": "Test Artist",
                        "duration": 60,
                    }
                ]
            )
            captured["count"] = table.track_count
            yield table

    app = _LoadDuringCompose()
    async with app.run_test():
        assert captured["count"] == 1


async def test_columns_match_show_album_show_index_flags():
    """Column set tracks the show_album / show_index flags from __init__."""

    captured: dict[str, set[str]] = {}

    class _CaptureColumns(_Host):
        def compose(self) -> ComposeResult:
            no_album_no_index = TrackTable(show_index=False, show_album=False)
            captured["minimal"] = _column_keys(no_album_no_index)

            full = TrackTable(show_index=True, show_album=True)
            captured["full"] = _column_keys(full)

            yield no_album_no_index
            yield full

    app = _CaptureColumns()
    async with app.run_test():
        assert captured["minimal"] == {"title", "artist", "duration"}
        assert captured["full"] == {"index", "title", "artist", "album", "duration"}
