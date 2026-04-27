# v1.7.2 — README restructure + sweep-fix release

**Date:** 2026-04-27
**Target release:** v1.7.2 (rolls in unreleased v1.7.1 work + this restructure)
**Theme:** Aggressive README split into landing page + 7 docs subdocs, plus stale-info sweep fixes

## Goal

Replace the 655-line monolithic README with a lean landing-page README (~100-120 lines) that is purely an index pointing at 7 dedicated `docs/*.md` subdocs. Each subdoc owns its topic with full detail; the README never duplicates that detail. Apply all stale-info findings from the v1.7.1 audit so the public docs accurately reflect the v1.7.0/v1.7.1 codebase.

## Background

- v1.7.0 + v1.7.1 added: heart toggle (`l` keybinding), `[playback] resume_on_launch` config, lyric title sanitization for LRCLIB, `DEFAULT_LYRIC_CURRENT = "#ff4e45"` constant, `app/_base.py` for Pyright typing, Python 3.10 floor with backport shims (`tomllib`, `typing.Self`, `enum.StrEnum`), the `check-python-versions.yml` watcher.
- Most of these are not surfaced in the existing README, CLAUDE.md, or CONTRIBUTING.md.
- v1.7.1 was committed locally only (master HEAD: 6115dd0 + small housekeeping commit) and never tagged/published. Per user instruction, v1.7.1 + v1.7.2 ship as a single v1.7.2 release.
- The README at 655 lines tries to be both a landing page and a manual; users either skim past everything or get lost. The aggressive split forces single-source-of-truth and shrinks the cognitive surface.

## Scope

### In scope

1. Restructure README → landing page (~100-120 lines).
2. Create 7 subdocs in `docs/`.
3. Apply all v1.7.1 sweep findings (sections 5 below).
4. Bump version 1.7.1 → 1.7.2 (in `__init__.py`, `aur/PKGBUILD`).
5. Rewrite the existing v1.7.1 CHANGELOG entry as a single combined v1.7.2 entry covering both the Python-floor work AND the README restructure.
6. Bump `flake.nix` `python312` → `python313`.
7. Move `screenshot-spotify-import.png` → `docs/screenshot-spotify-import.png` (cleaner relative path from `docs/spotify-import.md`).
8. Single ship cycle: push, tag v1.7.2, PyPI, AUR, GitHub Release, manually trigger watcher.

### Out of scope

- Source code changes beyond 2 stale comments (`pyproject.toml:124`, `src/ytm_player/services/player.py:155`).
- Test additions or modifications.
- New features (heart improvements, lyric matching improvements, etc.).
- Additional screenshots beyond `screenshot-v5.png`.
- README badges, demo GIF.
- Wiki migration (sticking with `docs/*.md` in-repo).
- AUR optdepends additions for `python-tomli`/`python-typing_extensions` (Arch ships modern Python; conditional dep is effectively no-op).
- Further CI matrix changes (lint/watcher already aligned to 3.14).
- mpv release watcher, Ubuntu LTS watcher, Dependabot grouping audit (deferred earlier).
- LRCLIB no-match-on-some-titles bug (separate v1.8 task).
- Memory profiling deep dive (separate v1.8 task).
- `flake.nix` other changes (only the python pin bump).

## Final file structure

```
ytm-player/
├── README.md                         (~100-120 lines — landing page index)
├── CHANGELOG.md                      (untouched history; v1.7.2 entry replaces v1.7.1 entry)
├── CLAUDE.md                         (small additions for 3.10 shims + watcher + DEFAULT_LYRIC_CURRENT)
├── CONTRIBUTING.md                   (small addition: 3.10 shim pattern + Pyright YTMHostBase note)
├── SECURITY.md                       (untouched; already current)
├── screenshot-v5.png                 (hero, repo root, referenced by README)
├── flake.nix                         (python312 → python313 + clarifying comment)
├── aur/PKGBUILD                      (pkgver 1.7.1 → 1.7.2)
├── src/ytm_player/__init__.py        (__version__ "1.7.1" → "1.7.2")
├── src/ytm_player/services/player.py (line 155 comment fix)
├── pyproject.toml                    (line 124 comment fix; past tense)
└── docs/
    ├── installation.md               (per-platform install + extras)
    ├── configuration.md              (full config.toml + theme.toml refs, includes resume_on_launch + corrected lyrics_current)
    ├── keybindings.md                (full keyboard + mouse refs, includes l for like)
    ├── cli-reference.md              (all ytm subcommands grouped)
    ├── spotify-import.md             (deep dive)
    ├── troubleshooting.md            (mpv/auth/MPRIS/macOS/cache/logs)
    ├── architecture.md               (file tree with _base.py + stack)
    └── screenshot-spotify-import.png (moved from repo root)
```

## README content map

Target length: 100-120 lines. Pure index, no duplication.

```
# ytm-player

[1-paragraph hero tagline — what it is, what it runs on]
![ytm-player screenshot](screenshot-v5.png)

## Features

- **Vim-style keybindings** — j/k movement, multi-key sequences (g s for search, g l for library), count prefixes (5j)
- **Synced lyrics** — live-highlighted with LRCLIB fallback for tracks YouTube doesn't have, with title sanitization for better LRCLIB matches
- **mpv backend** — gapless audio, stream prefetching, broad codec support
- **Cross-platform native integrations** — MPRIS (Linux), Now Playing (macOS), media keys (Windows)
- **Theming** — 18+ Textual themes + per-app color overrides in theme.toml
- **Spotify import** — pull playlists in via API or scraper fallback
- **CLI + IPC** — control a running TUI from another terminal (`ytm play`, `ytm pause`, etc.)
- **Free-tier support** — works without YouTube Music Premium
- **Session resume** — last-playing track + queue restored on launch
- **Local cache** — LRU audio cache for offline-like replay of previously heard tracks
- **Discord + Last.fm** — Rich Presence and scrobbling

## Requirements

- **Python 3.10+**
- **mpv** (audio playback backend, must be installed system-wide)
- A YouTube Music account (free or Premium)

## Install

```bash
# Most users (Linux/macOS/Windows)
pip install ytm-player

# Arch / CachyOS / Manjaro
yay -S ytm-player-git
```

For NixOS / Gentoo / Windows (extra mpv DLL setup) / source / optional extras, see [docs/installation.md](docs/installation.md).

## Quickstart

```bash
ytm setup    # one-time auth (auto-detects browser cookies)
ytm          # launch the TUI
```

Windows: replace `ytm` with `py -m ytm_player`.

## Documentation

| Topic | Link |
|-------|------|
| Per-platform install + optional extras | [docs/installation.md](docs/installation.md) |
| `config.toml` + `theme.toml` reference | [docs/configuration.md](docs/configuration.md) |
| Full keyboard + mouse reference | [docs/keybindings.md](docs/keybindings.md) |
| All `ytm` CLI subcommands | [docs/cli-reference.md](docs/cli-reference.md) |
| Spotify playlist import | [docs/spotify-import.md](docs/spotify-import.md) |
| Troubleshooting (mpv / auth / MPRIS / macOS) | [docs/troubleshooting.md](docs/troubleshooting.md) |
| File layout + stack | [docs/architecture.md](docs/architecture.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security policy | [SECURITY.md](SECURITY.md) |

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full release history.
```

## docs/* content map

Brief outline for each subdoc — implementer follows this when authoring the file.

### `docs/installation.md`
- Intro: 1-2 lines.
- mpv install: per-platform table (Arch/Ubuntu/Fedora/NixOS/macOS/Windows; Arch users with `pacman`, Debian with `apt`, etc.).
- ytm-player install: PyPI / AUR / Gentoo / NixOS (flake) / Windows (PyPI + PATH note + pipx alternative) / from source.
- Windows-specific mpv DLL setup (the current README "Windows Setup" section, in full).
- Optional extras (pip): `[spotify]`, `[mpris]`, `[discord]`, `[lastfm]`, `[transliteration]`, `[dev]`.
- Optional extras (AUR): `python-dbus-next`, `python-pylast`, `python-pypresence`, `python-spotipy`/`python-thefuzz`.
- NixOS LD_LIBRARY_PATH note (for users installing via pip rather than flake).

### `docs/configuration.md`
- Intro + config file paths table (config.toml, keymap.toml, theme.toml, auth.json — what each is for, where it lives).
- `ytm config` command pointer (opens config dir).
- Full `config.toml` reference, every section with every option:
  - `[general]` — `startup_page`, `brand_account_id`, `check_for_updates`
  - `[playback]` — `audio_quality`, `default_volume`, `autoplay`, `seek_step`, `api_timeout`, **`resume_on_launch`** (NEW, default true)
  - `[cache]` — `enabled`, `max_size_mb`, `prefetch_next`
  - `[yt_dlp]` — `cookies_file`, `remote_components`, `js_runtimes`
  - `[ui]` — `album_art`, `progress_style`, `sidebar_width`, column widths, `bidi_mode`
  - `[notifications]` — `enabled`, `timeout_seconds`
  - `[mpris]` — `enabled`
  - `[discord]` — `enabled`
  - `[lastfm]` — `enabled`, `api_key`, `api_secret`, `session_key`, `username`
  - `[logging]` — level + rotation
- `theme.toml` reference: full color list with explanations. **Use `lyrics_current = "#ff4e45"`** (the new theme-accent default; the example previously showed `#2ecc71`). Note that lyrics-current defaults to the theme accent if unset.
- `keymap.toml` location pointer + link to `docs/keybindings.md` for the full key list.

### `docs/keybindings.md`
- Intro: 1-2 lines.
- Keyboard reference table (full — the existing 30-key README table PLUS `l` for like-toggle on the playback bar, which is missing).
- Mouse reference table (full — the existing README mouse table).
- Custom keybinding override location + brief example (link to configuration.md).

### `docs/cli-reference.md`
- Intro: 1-2 lines about TUI vs CLI vs IPC.
- Setup / auth: `ytm setup` (modes: auto / browser-specific / manual).
- Search / stats / history: `ytm search`, `ytm stats`, `ytm history`.
- Cache: `ytm cache status`, `ytm cache clear`.
- Playback control (IPC): `ytm play`, `ytm pause`, `ytm next`, `ytm prev`, `ytm seek`.
- Like / dislike (IPC): `ytm like`, `ytm dislike`, `ytm unlike`.
- Status (IPC): `ytm now`, `ytm status`, `ytm queue`, `ytm queue add`, `ytm queue clear`.
- Import: `ytm import`.
- Diagnostics: `ytm doctor`, `ytm config`.

### `docs/spotify-import.md`
- Intro + screenshot (`./screenshot-spotify-import.png`).
- How it works (extract → match → resolve → create).
- Single vs multi mode (table, current README).
- TUI flow.
- CLI flow.
- Extraction methods: Spotify Web API (with API credential setup) + scraper fallback.

### `docs/troubleshooting.md`
- Intro: 1-2 lines.
- "mpv not found" / playback doesn't start.
- Authentication fails.
- No sound / wrong audio device.
- macOS media keys open Apple Music instead of ytm-player.
- MPRIS / media keys not working (Linux).
- Cache taking too much space.
- Logs and diagnostics (`ytm doctor`, `--debug`, log file paths per platform).

### `docs/architecture.md`
- Intro: 1-2 lines (audience: contributors + curious users).
- File tree (full — including `app/_base.py` which the current README tree is missing).
- Stack: Textual / ytmusicapi / yt-dlp / python-mpv / aiosqlite / dbus-next / pypresence / pylast.
- Key patterns: mixin architecture (`YTMHostBase`), event-driven playback, track format, session persistence, prefetching, page navigation, `LC_NUMERIC=C` quirk.
- Pointer to CONTRIBUTING.md for dev workflow.

## Sweep fixes integration

Every audit finding lands in exactly one place:

| Finding | Lands in |
|---------|----------|
| Missing `l` keybinding (added v1.7.0) | `docs/keybindings.md` table |
| Missing `[playback] resume_on_launch` config | `docs/configuration.md` `[playback]` section |
| Stale `lyrics_current = "#2ecc71"` | `docs/configuration.md` (corrected to `#ff4e45`, with note "defaults to theme accent if unset") |
| Architecture tree missing `_base.py` | `docs/architecture.md` file tree |
| Session-resume bullet undersold | README Features bullet rewritten ("last-playing track + queue restored on launch") |
| Missing LRCLIB title sanitization | README Features bullet for synced lyrics ("with title sanitization for better LRCLIB matches") |
| CLI subcommand list incomplete | `docs/cli-reference.md` (comprehensive — all 12+ subcommands grouped) |
| `CLAUDE.md` missing 3.10 shims, watcher, DEFAULT_LYRIC_CURRENT | CLAUDE.md gets 3 short additions |
| `CONTRIBUTING.md` missing 3.10 shim pattern, Pyright YTMHostBase note | CONTRIBUTING.md gets 1 short subsection |
| `pyproject.toml:124` "addressed in v1.7" wording | Tiny edit to past tense |
| `src/ytm_player/services/player.py:155` "Python 3.12+" comment | Tiny edit to clarify |
| `flake.nix:19` `python312` pin | Bump to `python313` + comment explaining the pin |

## Verification

Each task verifies its own outputs (lint, tests, link-check). Pre-ship verification:

1. **Tests**: `.venv/bin/pytest -q` → expect 545 passed.
2. **Lint**: `.venv/bin/ruff format --check && .venv/bin/ruff check src/ tests/` → clean.
3. **Pyright** on the small comment-fix files: 0 new errors.
4. **Link check** on README + every `docs/*.md`: every internal link resolves to a real file. Run via:
   ```bash
   for f in README.md docs/*.md; do
     grep -oP '\[[^\]]+\]\(\K[^)]+(?=\))' "$f" | while read link; do
       case "$link" in
         http*|mailto:*) ;;  # external, skip
         *) [ -e "$(dirname "$f")/$link" ] || [ -e "$link" ] || echo "BROKEN: $f → $link" ;;
       esac
     done
   done
   ```
5. **Manual scan**: README + each subdoc renders correctly on GitHub (preview locally with `glow` or push to a branch).

## Release plan

1. Implementation tasks (subagent-driven-development).
2. Final aggregate code review.
3. Peter QA gate (manual TUI sanity check + browse the new docs).
4. Bump version: 1.7.1 → 1.7.2 in `__init__.py` + `aur/PKGBUILD`.
5. Rewrite CHANGELOG: collapse v1.7.1 entry into v1.7.2 entry covering both Python-floor work and README restructure.
6. Push master, tag `v1.7.2`, push tag.
7. Build artifacts: `.venv/bin/python -m build --wheel --sdist`.
8. PyPI: `.venv/bin/twine upload dist/ytm_player-1.7.2*`.
9. AUR: clone, copy PKGBUILD + bump .SRCINFO pkgver, push.
10. GitHub Release with combined CHANGELOG entry as body.
11. Manually trigger `check-python-versions.yml` workflow once to verify it runs cleanly under the new 3.14 setup-python.

## Risks

- **Risk: stale internal links in docs/*.md** after restructure. Mitigation: link-check step in verification.
- **Risk: a sweep finding gets missed mid-implementation**. Mitigation: implementation plan creates one task per finding so nothing falls through.
- **Risk: implementer over-cuts the README**. Mitigation: spec defines exact length target (100-120 lines) and exact section list.
- **Risk: implementer over-fluffs a docs file**. Mitigation: each docs/*.md outline above defines the sections + scope clearly.
- **Low risk overall** — pure docs/config change, no source behavior change.

## Acceptance criteria

- [ ] README is 100-130 lines (target ~120).
- [ ] All 7 `docs/*.md` files exist and have content per the content map.
- [ ] `screenshot-spotify-import.png` is in `docs/`.
- [ ] Every README link resolves.
- [ ] All sweep findings applied (the 12 in the table above).
- [ ] CLAUDE.md updated for 3.10 shims, watcher, DEFAULT_LYRIC_CURRENT.
- [ ] CONTRIBUTING.md updated for 3.10 shim pattern + YTMHostBase.
- [ ] `__version__` is `"1.7.2"`, `aur/PKGBUILD` is `pkgver=1.7.2`.
- [ ] `flake.nix` uses `python313`.
- [ ] CHANGELOG.md has a single combined v1.7.2 entry (no orphan v1.7.1 entry).
- [ ] PyPI 1.7.2 published.
- [ ] AUR pushed cleanly.
- [ ] GitHub Release v1.7.2 created.
- [ ] 545 tests still pass; ruff clean.
