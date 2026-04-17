"""Help page must document every Action enum member.

Drift guard: when someone adds a new Action to config/keymap.py they
must also add a description (ACTION_DESCRIPTIONS) and put it in a
category (ACTION_CATEGORIES) so the keybind shows up in the in-app
help page. This test fails CI if either side is missing.

Some actions are intentionally excluded — internal-only or app-level
actions that aren't user-facing keybinds. Add them to ``_EXCLUDED``
with a one-line comment explaining why.
"""

from __future__ import annotations

from ytm_player.config.keymap import Action
from ytm_player.ui.pages.help import ACTION_CATEGORIES, ACTION_DESCRIPTIONS

# Actions that intentionally don't appear in the help page.
# Add new exclusions sparingly — most actions SHOULD be documented.
_EXCLUDED: set[Action] = {
    Action.QUIT,  # Not bindable from the help page; documented elsewhere.
    Action.TOGGLE_SIDEBAR,  # Sidebar-internal, app-level toggle.
    Action.TOGGLE_ALBUM_ART,  # App-level layout toggle.
    Action.TOGGLE_TRANSLITERATION,  # Lyrics-sidebar-internal toggle.
}


def _categorised_actions() -> set[Action]:
    """Flatten ACTION_CATEGORIES into a set of Actions."""
    out: set[Action] = set()
    for actions in ACTION_CATEGORIES.values():
        out.update(actions)
    return out


def test_every_action_has_a_description():
    """Every non-excluded Action must have a human-readable description."""
    documented = set(ACTION_DESCRIPTIONS.keys())
    expected = set(Action) - _EXCLUDED
    missing = expected - documented
    assert not missing, (
        f"These Actions need a description in help.py ACTION_DESCRIPTIONS: "
        f"{sorted(a.value for a in missing)}"
    )


def test_every_action_is_in_a_category():
    """Every non-excluded Action must appear in some ACTION_CATEGORIES bucket."""
    in_category = _categorised_actions()
    expected = set(Action) - _EXCLUDED
    missing = expected - in_category
    assert not missing, (
        f"These Actions need to be added to a category in help.py ACTION_CATEGORIES: "
        f"{sorted(a.value for a in missing)}"
    )


def test_no_unknown_actions_in_descriptions():
    """ACTION_DESCRIPTIONS keys must all be valid Action members."""
    # This test is structural — typed as dict[Action, str], so a wrong
    # key would already be a type error. Asserting at runtime catches
    # someone bypassing the annotation with `# type: ignore`.
    for key in ACTION_DESCRIPTIONS:
        assert isinstance(key, Action), f"{key!r} is not an Action"


def test_no_unknown_actions_in_categories():
    """ACTION_CATEGORIES values must all be Action members."""
    for category, actions in ACTION_CATEGORIES.items():
        for a in actions:
            assert isinstance(a, Action), f"{a!r} in category {category!r} is not an Action"


def test_no_duplicate_action_in_categories():
    """Each Action should appear in at most one category."""
    seen: dict[Action, str] = {}
    for category, actions in ACTION_CATEGORIES.items():
        for a in actions:
            if a in seen:
                raise AssertionError(f"Action {a.value!r} is in both {seen[a]!r} and {category!r}")
            seen[a] = category
