"""Shared base for the app's modal popups.

Provides the common popup shell (centered bordered box on a dimmed screen)
and unifies cancel semantics: Escape and a backdrop click both dismiss with
``_CANCEL_RESULT``. Clicks anywhere on the popup are swallowed so they never
leak through to widgets beneath the modal.

Subclasses stay parametrized over their result type (e.g.
``class ConfirmPopup(BasePopup[bool])``) and override ``_CANCEL_RESULT`` when
their cancel value isn't ``None``.
"""

from __future__ import annotations

from typing import Any, ClassVar, TypeVar

from textual.binding import Binding
from textual.events import Click
from textual.screen import ModalScreen

_ResultT = TypeVar("_ResultT")


class BasePopup(ModalScreen[_ResultT]):
    """Centered modal shell with unified Escape / backdrop-click cancel.

    Escape (and, for ``ConfirmPopup``, ``n``) route through ``action_cancel``,
    which dismisses with ``_CANCEL_RESULT``. A backdrop click has the same
    semantics as Escape. The unconditional ``event.stop()`` in ``on_click`` is
    load-bearing: it keeps clicks from leaking to widgets under the modal.
    """

    # Value passed to ``dismiss`` when the popup is cancelled. ``ClassVar``
    # (not the ``_ResultT`` TypeVar, which class vars may not reference) so
    # subclasses can override it — ``ConfirmPopup`` sets it to ``False``.
    _CANCEL_RESULT: ClassVar[Any] = None

    BINDINGS = [
        Binding("escape", "cancel", "Close", show=False),
    ]

    DEFAULT_CSS = """
    BasePopup {
        align: center middle;
    }

    BasePopup > Vertical {
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }
    """

    def action_cancel(self) -> None:
        """Dismiss with the popup's cancel value."""
        self.dismiss(self._CANCEL_RESULT)

    def on_click(self, event: Click) -> None:
        """Swallow clicks; a backdrop click (on the screen itself) cancels."""
        event.stop()
        if event.widget is self:
            self.action_cancel()
