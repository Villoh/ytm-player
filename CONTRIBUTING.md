# Contributing to ytm-player

Thanks for considering a contribution! This document covers what you need
to know to get a PR merged.

## Development setup

```bash
git clone https://github.com/peternaame-boop/ytm-player.git
cd ytm-player
python -m venv .venv
source .venv/bin/activate
pip install -e ".[spotify,mpris,discord,lastfm,transliteration,dev]"
```

System dependency: `mpv` must be installed system-wide (`sudo pacman -S mpv` on Arch, `brew install mpv` on macOS).

## Pre-commit checklist

**MANDATORY before every commit — run BOTH in this order:**

```bash
ruff format src/ tests/
ruff check src/ tests/
```

`ruff check` alone is NOT enough. `ruff format` catches line-length and
style issues `ruff check` does not.

## Testing

```bash
pytest                                           # full suite
pytest --cov=ytm_player --cov-report=term-missing  # with coverage
pytest tests/test_services/test_queue.py         # one file
pytest tests/test_services/test_queue.py::test_add_track -v  # one test
```

UI code (`src/ytm_player/ui/*`) is excluded from coverage; services and
config are covered.

## Logging

Logs go to `~/.config/ytm-player/logs/ytm.log`. **Never use `print()`**
in non-CLI code — Textual's alt-screen swallows stderr.

For caught exceptions you want to surface in bug reports, use
`logger.exception("descriptive message")` — *not* `logger.debug(...,
exc_info=True)`, which silently routes to debug.

## Track dict

All services use a standardised track dict: `video_id`, `title`, `artist`,
`artists` (list of `{name, id}` dicts), `album`, `album_id`, `duration`
(seconds, int or None), `thumbnail_url`, `is_video`. Use
`normalize_tracks()` from `utils/formatting.py` when ingesting raw
ytmusicapi data.

## RTL text

Any user-supplied text fragment concatenated into a line with other
fragments (table cells, playback bar widgets) MUST be wrapped with
`isolate_bidi()` from `utils/bidi.py` AFTER `truncate()`. Otherwise RTL
text bleeds across visual boundaries on some terminals. There's a
regression test (`TestIsolateBidiCallSites`) that fails CI if a render
site stops calling `isolate_bidi`.

## Feature requests

Feature requests are welcome. The most useful ones describe the
problem or preference, not the fix — what you were trying to do, what
got in your way, what would feel better. Suggested solutions are fine
as context, but final scope and design decisions follow the overall direction of the project.

If a suggestion doesn't match a stated problem, I'll usually ask
"what's the underlying friction?" before deciding anything. Not
because I'm dismissing the idea — because I want to make sure I build
the right thing for you, not just the thing you asked for.

Bundling multiple ideas into one issue is fine and encouraged.
Bundling bugs with feature requests isn't — file bugs separately so
they don't get buried.

## PR norms

- One concern per PR. Don't bundle "fix bug + add feature + refactor".
- Reference the issue in the PR description (`Closes #123`).
- Update `CHANGELOG.md` if your change is user-visible.
- The CI matrix runs Ubuntu + macOS + Windows on Python 3.12 and 3.13. Make sure all green before requesting review.

## Architecture pointers

- `app/` — main app split into mixins (lifecycle, playback, navigation, etc.)
- `services/` — backend singletons (Player, QueueManager, YTMusicService, etc.)
- `ui/` — Textual widgets (pages, sidebars, popups, widgets)
- `config/` — settings, keymap, theme, paths

For deeper context, read `CLAUDE.md` in the repo root — it's the
project's living architecture doc.
