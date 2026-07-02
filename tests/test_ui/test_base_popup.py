"""Tests for the shared BasePopup shell.

Pins the three behaviours BasePopup unifies across every modal popup:
Escape cancels with the popup's cancel value, a backdrop click does the
same, a click on the popup body does not dismiss, and the hoisted shell CSS
reaches subclasses without clobbering their per-popup overrides.
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.geometry import Spacing
from textual.widgets import Static

from ytm_player.ui.popups.actions import ActionsPopup
from ytm_player.ui.popups.base import BasePopup
from ytm_player.ui.popups.confirm_popup import ConfirmPopup
from ytm_player.ui.popups.country_picker import CountryPickerModal
from ytm_player.ui.popups.create_playlist_popup import CreatePlaylistPopup
from ytm_player.ui.popups.input_popup import InputPopup
from ytm_player.ui.popups.playlist_picker import PlaylistPicker
from ytm_player.ui.popups.spotify_import import SpotifyImportPopup

_UNSET = object()


def _make_actions() -> ActionsPopup:
    return ActionsPopup(
        {"title": "T", "artists": [{"name": "A", "id": "1"}], "album_id": "a1"},
        "track",
    )


# Each factory paired with the value its cancel path must dismiss with.
_FACTORIES: dict[str, tuple] = {
    "ActionsPopup": (_make_actions, None),
    "ConfirmPopup": (lambda: ConfirmPopup("Sure?"), False),
    "CountryPickerModal": (lambda: CountryPickerModal("US"), None),
    "CreatePlaylistPopup": (CreatePlaylistPopup, None),
    "InputPopup": (lambda: InputPopup("Enter"), None),
    "PlaylistPicker": (lambda: PlaylistPicker(["vid1"]), None),
    "SpotifyImportPopup": (SpotifyImportPopup, None),
}

_POPUP_CLASSES = [
    ActionsPopup,
    ConfirmPopup,
    CountryPickerModal,
    CreatePlaylistPopup,
    InputPopup,
    PlaylistPicker,
    SpotifyImportPopup,
]


class _Host(App):
    def compose(self) -> ComposeResult:
        yield Static("host")


# ── Drift pin ────────────────────────────────────────────────────────


@pytest.mark.parametrize("popup_cls", _POPUP_CLASSES, ids=lambda c: c.__name__)
def test_is_base_popup_subclass(popup_cls):
    """Every migrated popup shares the BasePopup shell."""
    assert issubclass(popup_cls, BasePopup)


# ── Escape cancels with the popup's cancel value ─────────────────────


@pytest.mark.parametrize("name", list(_FACTORIES), ids=list(_FACTORIES))
async def test_escape_dismisses_with_cancel_value(name):
    factory, cancel_value = _FACTORIES[name]
    result = {"value": _UNSET}
    app = _Host()
    async with app.run_test() as pilot:
        await app.push_screen(factory(), lambda v: result.__setitem__("value", v))
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
    # `is` is exact for the None / False singletons — proves ConfirmPopup
    # stays False (never None) and the rest stay None.
    assert result["value"] is cancel_value


async def test_confirm_escape_is_false_not_none():
    """Explicit pin: ConfirmPopup's Escape must yield False, not None."""
    result = {"value": _UNSET}
    app = _Host()
    async with app.run_test() as pilot:
        await app.push_screen(ConfirmPopup("Sure?"), lambda v: result.__setitem__("value", v))
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
    assert result["value"] is False


async def test_confirm_n_key_is_false():
    """ConfirmPopup's `n` binding routes through cancel → False."""
    result = {"value": _UNSET}
    app = _Host()
    async with app.run_test() as pilot:
        await app.push_screen(ConfirmPopup("Sure?"), lambda v: result.__setitem__("value", v))
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
    assert result["value"] is False


# ── Backdrop click cancels; body click does not ──────────────────────


@pytest.mark.parametrize("name", list(_FACTORIES), ids=list(_FACTORIES))
async def test_backdrop_click_dismisses_with_cancel_value(name):
    factory, cancel_value = _FACTORIES[name]
    result = {"value": _UNSET}
    app = _Host()
    async with app.run_test() as pilot:
        await app.push_screen(factory(), lambda v: result.__setitem__("value", v))
        await pilot.pause()
        # (0, 0) is the screen corner, outside the centered box → backdrop.
        await pilot.click(offset=(0, 0))
        await pilot.pause()
    assert result["value"] is cancel_value


async def test_body_click_does_not_dismiss():
    """A click on the popup body (not the backdrop) must not dismiss."""
    result = {"value": _UNSET}
    app = _Host()
    async with app.run_test() as pilot:
        await app.push_screen(ConfirmPopup("Sure?"), lambda v: result.__setitem__("value", v))
        await pilot.pause()
        await pilot.click("#confirm-message")
        await pilot.pause()
        assert result["value"] is _UNSET


# ── Buttons still work under the unconditional event.stop() ──────────


async def test_confirm_yes_button_click_returns_true():
    """The screen-level event.stop() must not swallow button presses."""
    result = {"value": _UNSET}
    app = _Host()
    async with app.run_test() as pilot:
        await app.push_screen(ConfirmPopup("Sure?"), lambda v: result.__setitem__("value", v))
        await pilot.pause()
        await pilot.click("#confirm-yes")
        await pilot.pause()
    assert result["value"] is True


# ── Hoisted CSS reaches subclasses; subclass overrides win ───────────


async def test_hoisted_css_applies_and_subclass_overrides_win():
    app = _Host()
    async with app.run_test() as pilot:
        popup = _make_actions()
        await app.push_screen(popup)
        await pilot.pause()
        box = popup.query_one("Vertical")
        # Subclass-only width survives (base shell rule does not clobber it).
        assert box.styles.width.value == 40
        # Base shell chrome reaches the subclass box.
        assert box.styles.padding == Spacing(1, 2, 1, 2)
        assert box.styles.border.top[0] == "round"
        # Base screen rule (align) reaches the subclass screen.
        assert popup.styles.align == ("center", "middle")
