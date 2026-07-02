"""Queue page d/J/K must act on the queue index, not the visible row.

After the user sorts (header click / SORT_* actions) or filters the
table, ``cursor_row`` is a visible-row index that no longer matches the
queue position. Selection already maps through the table's view — these
tests pin the same mapping for the mutation paths (remove/move).
"""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult

from ytm_player.config.keymap import Action
from ytm_player.services.queue import QueueManager
from ytm_player.ui.pages.queue import QueuePage
from ytm_player.ui.widgets.track_table import TrackTable


class _FakePlayer:
    """Just enough Player surface for QueuePage/TrackTable mounting."""

    current_track: dict | None = None

    def on(self, *_args: Any) -> None: ...

    def off(self, *_args: Any) -> None: ...


class _QueueHost(App):
    """Minimal host app exposing the attributes QueuePage reads."""

    def __init__(self, queue: QueueManager) -> None:
        super().__init__()
        self.queue = queue
        self.player = _FakePlayer()

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        variables["selected-item"] = "#3a3a3a"
        return variables

    def compose(self) -> ComposeResult:
        yield QueuePage()


def _track(video_id: str, title: str) -> dict:
    return {
        "video_id": video_id,
        "title": title,
        "artist": "A",
        "artists": [{"name": "A", "id": "1"}],
        "album": "",
        "album_id": None,
        "duration": 120,
        "thumbnail_url": None,
        "is_video": False,
    }


def _make_queue() -> QueueManager:
    queue = QueueManager()
    # Queue order t1..t4; titles reverse-alphabetical so a title sort
    # visibly diverges from queue order.
    queue.add_multiple(
        [
            _track("t1", "d-song"),
            _track("t2", "c-song"),
            _track("t3", "b-song"),
            _track("t4", "a-song"),
        ]
    )
    return queue


def _ids(queue: QueueManager) -> list[str]:
    return [t["video_id"] for t in queue.tracks]


async def test_delete_removes_highlighted_track_after_sort():
    queue = _make_queue()
    app = _QueueHost(queue)
    async with app.run_test() as pilot:
        page = app.query_one(QueuePage)
        table = app.query_one("#queue-table", TrackTable)
        table.sort_by("title")  # visible: a,b,c,d = queue index 3,2,1,0
        table.move_cursor(row=0)  # highlight "a-song" (queue index 3)
        await pilot.pause()

        await page.handle_action(Action.DELETE_ITEM)

        # Pre-fix this removed queue index 0 ("d-song"), the positional twin.
        assert _ids(queue) == ["t1", "t2", "t3"]


async def test_delete_removes_highlighted_track_in_filtered_view():
    queue = _make_queue()
    app = _QueueHost(queue)
    async with app.run_test() as pilot:
        page = app.query_one(QueuePage)
        table = app.query_one("#queue-table", TrackTable)
        # Bypass apply_filter's debounce timer for determinism.
        table._filter_text = "b-song"
        table._execute_filter()  # visible: only "b-song" (queue index 2)
        table.move_cursor(row=0)
        await pilot.pause()

        await page.handle_action(Action.DELETE_ITEM)

        assert _ids(queue) == ["t1", "t2", "t4"]


async def test_move_up_moves_highlighted_track_after_sort():
    queue = _make_queue()
    app = _QueueHost(queue)
    async with app.run_test() as pilot:
        page = app.query_one(QueuePage)
        table = app.query_one("#queue-table", TrackTable)
        table.sort_by("title")  # visible: a,b,c,d = queue index 3,2,1,0
        table.move_cursor(row=1)  # highlight "b-song" (queue index 2)
        await pilot.pause()

        await page.handle_action(Action.REORDER_UP)

        # b-song moves one QUEUE position earlier. Pre-fix this moved
        # visible row 1 to row 0 → t2,t1,t3,t4 (wrong track).
        assert _ids(queue) == ["t1", "t3", "t2", "t4"]
        # The refresh resets the view to queue order with the cursor
        # following the moved track.
        assert table.cursor_row == 1


async def test_move_down_still_works_without_sort_or_filter():
    queue = _make_queue()
    app = _QueueHost(queue)
    async with app.run_test() as pilot:
        page = app.query_one(QueuePage)
        table = app.query_one("#queue-table", TrackTable)
        table.move_cursor(row=0)
        await pilot.pause()

        await page.handle_action(Action.REORDER_DOWN)

        assert _ids(queue) == ["t2", "t1", "t3", "t4"]
        assert table.cursor_row == 1


async def test_delete_after_sort_in_shuffle_mode():
    """The table shows playback (shuffle) order and queue.remove() takes a
    playback-order index, so the mapping must hold under shuffle too."""
    queue = _make_queue()
    # Force a deterministic shuffle order instead of toggle_shuffle()'s
    # random one: playback order t3, t1, t4, t2.
    queue._shuffle = True
    queue._shuffle_order = [2, 0, 3, 1]
    queue._shuffle_position = -1
    assert _ids(queue) == ["t3", "t1", "t4", "t2"]

    app = _QueueHost(queue)
    async with app.run_test() as pilot:
        page = app.query_one(QueuePage)
        table = app.query_one("#queue-table", TrackTable)
        table.sort_by("title")  # visible: a(t4), b(t3), c(t2), d(t1)
        table.move_cursor(row=0)  # highlight "a-song" (t4, playback index 2)
        await pilot.pause()

        await page.handle_action(Action.DELETE_ITEM)

        assert _ids(queue) == ["t3", "t1", "t2"]


async def test_delete_is_noop_when_filter_matches_nothing():
    queue = _make_queue()
    app = _QueueHost(queue)
    async with app.run_test() as pilot:
        page = app.query_one(QueuePage)
        table = app.query_one("#queue-table", TrackTable)
        table._filter_text = "no-match"
        table._execute_filter()  # zero visible rows
        await pilot.pause()

        await page.handle_action(Action.DELETE_ITEM)

        assert _ids(queue) == ["t1", "t2", "t3", "t4"]


async def test_delete_last_track_shows_empty_state():
    queue = QueueManager()
    queue.add_multiple([_track("t1", "only-song")])
    app = _QueueHost(queue)
    async with app.run_test() as pilot:
        page = app.query_one(QueuePage)
        table = app.query_one("#queue-table", TrackTable)
        table.move_cursor(row=0)
        await pilot.pause()

        await page.handle_action(Action.DELETE_ITEM)

        assert queue.length == 0
        assert table.display is False
        assert app.query_one("#queue-empty").display is True
