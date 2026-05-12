"""Tests for the _ArtistAlbumList table inside ContextPage."""

from __future__ import annotations

from textual.app import App, ComposeResult

from ytm_player.ui.pages.context import _ArtistAlbumList


class _Host(App):
    """Minimal host that provides the theme variables _ArtistAlbumList's CSS needs."""

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        variables["selected-item"] = "#3a3a3a"
        return variables


async def test_load_albums_immediately_after_construction():
    """Regression: see context._build_artist nested-mount path.

    Before the option-C fix on _ArtistAlbumList, this widget set up its
    columns inside on_mount. _build_artist mounts the album table inside
    a 3-deep nested-mount chain (container.mount(columns) →
    columns.mount(right) → right.mount(album_table)) and immediately
    calls load_albums synchronously — on_mount hasn't fired yet, so the
    table has 0 columns and add_row crashes with
    "More values provided than there are columns".

    This test reproduces that exact scenario: load_albums runs during
    compose, before on_mount fires. With columns set up in __init__, it
    succeeds.
    """

    captured: dict[str, int] = {}

    class _LoadDuringCompose(_Host):
        def compose(self) -> ComposeResult:
            table = _ArtistAlbumList()
            table.load_albums(
                [
                    {"title": "Album One", "year": "2024", "browseId": "MPREb_1"},
                    {"title": "Album Two", "year": "2023", "browseId": "MPREb_2"},
                ]
            )
            captured["row_count"] = table.row_count
            yield table

    app = _LoadDuringCompose()
    async with app.run_test():
        assert captured["row_count"] == 2


async def test_columns_set_up_at_construction_time():
    """Columns must exist immediately after __init__, before on_mount fires."""

    captured: dict[str, set[str]] = {}

    class _CaptureColumns(_Host):
        def compose(self) -> ComposeResult:
            table = _ArtistAlbumList()
            captured["keys"] = {c.value for c in table.columns if c.value is not None}
            yield table

    app = _CaptureColumns()
    async with app.run_test():
        assert captured["keys"] == {"title", "year"}
