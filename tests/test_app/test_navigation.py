"""Tests for NavigationMixin invariants.

The two bugs we're guarding against:
1. Back-navigation must NOT push current page onto stack — the stack
   would ping-pong between two pages forever.
2. Forward navigation should restore cached page state (cursor row,
   active tab, search query) when no explicit kwargs are passed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from ytm_player.app._navigation import PAGE_NAMES, NavigationMixin


def _fresh_nav_host() -> NavigationMixin:
    """Build a NavigationMixin instance with the state attrs it reads."""
    nav = NavigationMixin()
    nav._current_page = ""
    nav._current_page_kwargs = {}
    nav._nav_stack = []
    nav._forward_stack = []
    nav._page_state_cache = {}
    nav._sidebar_per_page = {}
    nav._sidebar_default = True
    nav._lyrics_sidebar_open = False

    # Stub the methods navigate_to calls on self.
    container = MagicMock()
    container.remove_children = AsyncMock()
    container.mount = AsyncMock()
    container.children = []

    # query_one is called with (#main-content, Container) and (#app-footer, FooterBar).
    # The footer call is inside a try/except so raising is fine; we return the
    # container for the first call and raise for the footer.
    def _query_one(selector, *args, **kwargs):
        if "#main-content" in selector:
            return container
        raise Exception("no footer in tests")

    nav.query_one = MagicMock(side_effect=_query_one)
    nav._create_page = MagicMock(side_effect=lambda name, **kw: MagicMock(_name=name, _kw=kw))
    nav._apply_playlist_sidebar = MagicMock()
    nav._apply_lyrics_sidebar = MagicMock()
    return nav


class TestNavigateTo:
    async def test_unknown_page_rejected_silently(self):
        nav = _fresh_nav_host()
        await nav.navigate_to("nonsense")
        assert nav._current_page == ""
        nav._create_page.assert_not_called()

    async def test_navigates_to_valid_page(self):
        nav = _fresh_nav_host()
        await nav.navigate_to("library")
        assert nav._current_page == "library"
        assert nav._nav_stack == []  # Nothing to push (no previous page)

    async def test_forward_nav_pushes_current_onto_stack(self):
        nav = _fresh_nav_host()
        await nav.navigate_to("library")
        await nav.navigate_to("search")
        assert nav._current_page == "search"
        assert nav._nav_stack == [("library", {})]

    async def test_back_nav_does_not_push_current_onto_stack(self):
        """Regression: pushing on back creates infinite ping-pong."""
        nav = _fresh_nav_host()
        await nav.navigate_to("library")
        await nav.navigate_to("search")
        # Stack: [library], current: search
        await nav.navigate_to("back")
        # After back: current is library, stack is empty (we popped + did not push search).
        assert nav._current_page == "library"
        assert nav._nav_stack == []

    async def test_back_with_empty_stack_goes_to_library(self):
        nav = _fresh_nav_host()
        await nav.navigate_to("back")
        assert nav._current_page == "library"

    async def test_state_cache_round_trip(self):
        """Forward nav with no kwargs restores cached state from prior visit."""
        nav = _fresh_nav_host()
        # First visit to library — pretend page reports state.
        await nav.navigate_to("library")
        page = nav._create_page.return_value
        page.get_nav_state = MagicMock(return_value={"playlist_id": "PL1", "cursor_row": 5})
        # Simulate _get_current_page returning that page.
        nav._get_current_page = MagicMock(return_value=page)
        # Navigate away — state should be cached.
        await nav.navigate_to("search")
        assert nav._page_state_cache.get("library") == {
            "playlist_id": "PL1",
            "cursor_row": 5,
        }
        # Navigate back to library with no explicit kwargs — state restored.
        await nav.navigate_to("library")
        # _create_page receives the cached kwargs.
        last_call = nav._create_page.call_args
        assert last_call.kwargs.get("playlist_id") == "PL1"
        assert last_call.kwargs.get("cursor_row") == 5

    async def test_nav_stack_capped_at_20(self):
        nav = _fresh_nav_host()
        # Navigate through 25 page changes — alternating to force pushes.
        names = ["library", "search"]
        for i in range(25):
            await nav.navigate_to(names[i % 2])
        assert len(nav._nav_stack) <= 20


class TestPageNames:
    def test_no_duplicates(self):
        assert len(PAGE_NAMES) == len(set(PAGE_NAMES))

    def test_library_is_a_valid_page(self):
        """library is the back-navigation fallback — must be valid."""
        assert "library" in PAGE_NAMES
