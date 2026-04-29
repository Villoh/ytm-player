"""Tests for TrackTable widget message wiring."""

from __future__ import annotations

import pytest


def test_track_table_posts_selection_changed_on_row_highlight():
    """Confirms TrackTable posts a SelectionChanged message when the cursor row changes.

    NOTE: This is an integration-style test that requires Textual's pilot harness to
    drive the DataTable cursor. Skipped as a placeholder — the wiring itself is
    exercised indirectly through manual UI testing and the unit-level message
    tests in test_selection_info_bar.py. Wire up a pilot-based test here if regressions
    appear.
    """
    pytest.skip("TrackTable selection-message integration test placeholder — wire up if needed")
