"""Tests for SelectionInfoBar widget."""

from __future__ import annotations

from ytm_player.ui.selection_info_bar import SelectionChanged, SelectionInfoBar


def test_selection_changed_message_carries_text():
    msg = SelectionChanged("My Long Playlist Name")
    assert msg.text == "My Long Playlist Name"


def test_selection_changed_empty_text_means_no_selection():
    msg = SelectionChanged("")
    assert msg.text == ""


def test_selection_info_bar_initial_text_empty():
    bar = SelectionInfoBar()
    assert bar.text == ""


def test_selection_info_bar_text_reactive_updates():
    bar = SelectionInfoBar()
    bar.text = "Hello"
    assert bar.text == "Hello"
