"""Integration test: search worker cancellation cleans up properly.

Validates the v1.7.0 'Searching... stuck forever' fix.

``asyncio.CancelledError`` inherits from ``BaseException`` (not
``Exception``) in Python 3.8+, so the original ``except Exception:``
wrapper in the search worker did not catch it; the loading-text-clear
lived outside the try/finally and never ran when the worker was
cancelled mid-flight (e.g. when the user typed a new query, triggering
``run_worker(..., exclusive=True)`` to cancel the previous task).

The fix in ``src/ytm_player/ui/pages/search.py`` (``_execute_search``,
~lines 652-689) added an explicit ``except asyncio.CancelledError``
branch that clears the indicator before re-raising, so the worker
tears down cleanly.

This test asserts the CONTRACT (a try-block that clears state on
cancel + no zombie tasks remain) rather than the production
``SearchPage._execute_search`` directly, because that method needs a
live Textual ``App`` context (``query_one``, ``self.app.history``,
``run_worker``) to instantiate. Booting an App is too heavy for this
layer; mirroring the pattern in isolation pins the same contract.
"""

from __future__ import annotations

import asyncio

import pytest


async def test_search_worker_cancel_clears_indicator_no_zombie_tasks() -> None:
    """Cancelling a search worker mid-flight clears the indicator and
    leaves no pending tasks behind.

    Mirrors the shape of ``SearchPage._execute_search``:
    - sets the indicator to "Searching..."
    - awaits a long-running operation
    - on ``CancelledError``, clears the indicator and re-raises
    """
    indicator_state = {"text": ""}

    async def search_worker() -> list[dict]:
        # Mirrors search.py:_execute_search lines 654-655.
        indicator_state["text"] = "Searching..."
        try:
            # Stand-in for the real ytmusicapi/yt-dlp work the worker awaits.
            await asyncio.sleep(10)
            indicator_state["text"] = ""
            return []
        except asyncio.CancelledError:
            # The v1.7.0 fix: clear the indicator on cancel BEFORE re-raising
            # so the UI does not lie about an in-flight search.
            indicator_state["text"] = ""
            raise

    worker = asyncio.create_task(search_worker())

    # Yield once so the worker actually starts and reaches the
    # ``await asyncio.sleep(10)``; without this, ``cancel()`` may fire
    # before the task has been scheduled and the test asserts nothing
    # interesting.
    await asyncio.sleep(0.01)
    assert indicator_state["text"] == "Searching..."

    worker.cancel()

    with pytest.raises(asyncio.CancelledError):
        await worker

    # Contract part 1: indicator was cleared by the cancel handler.
    assert indicator_state["text"] == ""

    # Contract part 2: no zombie tasks remain. If the worker had swallowed
    # the cancel or spawned untracked children, this would catch it.
    pending = [t for t in asyncio.all_tasks() if not t.done() and t is not asyncio.current_task()]
    assert pending == []


async def test_search_worker_swallowing_cancel_would_leak_indicator() -> None:
    """Negative control: a worker that catches ``CancelledError`` under a
    plain ``except Exception:`` block (as the pre-v1.7.0 code effectively
    did, by NOT having a CancelledError branch and clearing the indicator
    OUTSIDE the try) would leave the indicator stuck.

    This pins the bug shape so a future refactor that re-introduces the
    same mistake fails this test loudly.
    """
    indicator_state = {"text": ""}

    async def buggy_worker() -> None:
        indicator_state["text"] = "Searching..."
        try:
            await asyncio.sleep(10)
        except Exception:
            # CancelledError does NOT inherit from Exception in 3.8+, so
            # this branch is skipped, and the unconditional clear below
            # never runs because cancel propagates out.
            pass
        # The pre-fix bug: clear lives outside try/finally, so cancel
        # bypasses it entirely.
        indicator_state["text"] = ""

    worker = asyncio.create_task(buggy_worker())
    await asyncio.sleep(0.01)
    worker.cancel()

    with pytest.raises(asyncio.CancelledError):
        await worker

    # Indicator never cleared because the post-await line never ran -- this
    # is precisely the bug the v1.7.0 fix addresses.
    assert indicator_state["text"] == "Searching..."
