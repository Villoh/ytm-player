# v1.7.2 — README Restructure + Sweep-Fix Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 655-line monolithic README with a ~120-line landing-page index, create 7 dedicated docs in `docs/`, apply all v1.7.1 sweep findings, and ship as v1.7.2 (rolls in unreleased v1.7.1 work).

**Architecture:** Pure docs/config restructure. No source code logic changes. Each new doc file owns its topic with full detail; the README links to all of them and never duplicates content. Sweep findings (stale `lyrics_current` color, missing `l` keybinding, missing `_base.py` in tree, etc.) are absorbed by the new doc files at their natural homes.

**Tech Stack:** Markdown, GitHub-flavoured tables, no source code.

**Working directory:** `/home/wiz/AI/ytm-player` (master branch). Current HEAD when this plan was written: `3f857ec` (the spec doc commit).

---

## File Structure

| File | Action | Owner |
|------|--------|-------|
| `pyproject.toml` | Modify (line ~124 comment fix) | Pre-restructure housekeeping |
| `src/ytm_player/services/player.py` | Modify (line ~155 comment fix) | Pre-restructure housekeeping |
| `flake.nix` | Modify (`python312` → `python313` + comment) | Pre-restructure housekeeping |
| `docs/screenshot-spotify-import.png` | Move from repo root | Pre-restructure housekeeping |
| `docs/installation.md` | **Create** | Per-platform install + extras |
| `docs/configuration.md` | **Create** | Full config reference |
| `docs/keybindings.md` | **Create** | Full keyboard + mouse |
| `docs/cli-reference.md` | **Create** | All `ytm` subcommands |
| `docs/spotify-import.md` | **Create** | Spotify deep dive |
| `docs/troubleshooting.md` | **Create** | All troubleshooting |
| `docs/architecture.md` | **Create** | File tree + stack |
| `CLAUDE.md` | Modify | Add 3 short notes (3.10 shims, watcher, DEFAULT_LYRIC_CURRENT) |
| `CONTRIBUTING.md` | Modify | Add 1 short subsection on 3.10 shim pattern + Pyright YTMHostBase |
| `README.md` | **Replace** | Lean landing page (~120 lines) |
| `CHANGELOG.md` | Modify (collapse v1.7.1 entry into v1.7.2) | Release prep |
| `src/ytm_player/__init__.py` | Modify (`1.7.1` → `1.7.2`) | Release prep |
| `aur/PKGBUILD` | Modify (`pkgver=1.7.1` → `pkgver=1.7.2`) | Release prep |

---

## Task 1: Pre-restructure housekeeping

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/ytm_player/services/player.py`
- Modify: `flake.nix`
- Move: `screenshot-spotify-import.png` → `docs/screenshot-spotify-import.png`

Five tiny mechanical changes that get cruft out of the way before the bigger restructure.

- [ ] **Step 1: Fix `pyproject.toml:124` comment**

Read the current `[tool.pyright]` block. The line currently reads:
```
# errors. Mixin-attribute typing is addressed in v1.7 via app/_base.py —
```

Change to:
```
# errors. Mixin-attribute typing was addressed in v1.7 via app/_base.py —
```

(Past tense — v1.7 has shipped, "is addressed" reads as future-perfect.)

- [ ] **Step 2: Fix `src/ytm_player/services/player.py:155` comment**

Find the line that reads:
```
# On Windows, Python 3.12+ links ucrtbase.dll — calling setlocale on
```

Change to:
```
# On Windows, Python (3.5+) links ucrtbase.dll — calling setlocale on
```

(The 3.12+ claim was stale; ucrtbase has been the default since Python 3.5.)

- [ ] **Step 3: Bump `flake.nix` `python312` → `python313`**

Find the line:
```
        python = pkgs.python312;
```

Change to:
```
        # Pinned to a stable middle of the supported range (3.10..3.14).
        # Bump along with nixpkgs releases.
        python = pkgs.python313;
```

- [ ] **Step 4: Move spotify screenshot into `docs/`**

```bash
mkdir -p docs
git mv screenshot-spotify-import.png docs/screenshot-spotify-import.png
```

(Note: at this point the README still references `screenshot-spotify-import.png` at the root path. Step 5 commits anyway because Task 9 — the README replace — will fix the reference. Linkcheck in Task 12 confirms.)

- [ ] **Step 5: Verify**

```bash
.venv/bin/pytest -q 2>&1 | tail -3
.venv/bin/ruff format --check src/ tests/
.venv/bin/ruff check src/ tests/
```

Expected: 545 passed, ruff clean.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/ytm_player/services/player.py flake.nix docs/screenshot-spotify-import.png screenshot-spotify-import.png
git commit -m "chore: pre-restructure housekeeping (stale comments, flake bump, move spotify screenshot)"
```

---

## Task 2: Create `docs/installation.md`

**Files:**
- Create: `docs/installation.md`

The doc absorbs the current README's "Installation" + "Windows Setup" + "Optional extras" sections in full.

- [ ] **Step 1: Create the file with the following content**

```markdown
# Installation

This guide covers installing ytm-player on every supported platform.

## Step 1: Install mpv

mpv is required for audio playback. Install it with your system package manager:

| Platform | Command |
|----------|---------|
| Arch / CachyOS / Manjaro | `sudo pacman -S mpv` |
| Ubuntu / Debian | `sudo apt install mpv` |
| Fedora | `sudo dnf install mpv` |
| macOS (Homebrew) | `brew install mpv` |
| Windows (Scoop) | `scoop install mpv` (then see [Windows Setup](#windows-setup) for the libmpv DLL) |
| NixOS | Handled by the flake — see the NixOS section below |

## Step 2: Install ytm-player

### PyPI (Linux / macOS)

```bash
pip install ytm-player
```

### Arch Linux / CachyOS / EndeavourOS / Manjaro (AUR)

```bash
yay -S ytm-player-git
```

(Or any other AUR helper.) Package: [ytm-player-git](https://aur.archlinux.org/packages/ytm-player-git).

### Gentoo (GURU)

Enable the [GURU repository](https://wiki.gentoo.org/wiki/Project:GURU/Information_for_End_Users) then:

```bash
emerge --ask media-sound/ytm-player
```

### Windows

```powershell
pip install ytm-player
```

Launch with:

```powershell
py -m ytm_player
```

> `pip install` on Windows does not add the `ytm` command to PATH. Use `py -m ytm_player`, or install with [pipx](https://pipx.pypa.io/) which handles PATH automatically: `pipx install ytm-player`.

> **Important:** Windows requires extra mpv setup — see [Windows Setup](#windows-setup) below.

### NixOS (Flake)

ytm-player provides a `flake.nix` with two packages, a dev shell, and an overlay.

**Try it without installing:**

```bash
nix run github:peternaame-boop/ytm-player
```

**Add to your system flake:**

```nix
{
  inputs.ytm-player.url = "github:peternaame-boop/ytm-player";

  outputs = { nixpkgs, ytm-player, ... }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      modules = [
        {
          nixpkgs.overlays = [ ytm-player.overlays.default ];
          environment.systemPackages = with pkgs; [
            ytm-player          # core (MPRIS + album art included)
            # ytm-player-full   # all features (Discord, Last.fm, Spotify import)
          ];
        }
      ];
    };
  };
}
```

**Or install imperatively:**

```bash
nix profile install github:peternaame-boop/ytm-player
nix profile install github:peternaame-boop/ytm-player#ytm-player-full
```

**Dev shell** (for contributors):

```bash
git clone https://github.com/peternaame-boop/ytm-player.git
cd ytm-player
nix develop
```

> **Note for pip-on-NixOS users:** if you install via `pip` instead of the flake, NixOS doesn't expose `libmpv.so` in standard library paths. Add to your shell config:
> ```fish
> # Fish
> set -gx LD_LIBRARY_PATH /run/current-system/sw/lib $LD_LIBRARY_PATH
> ```
> ```bash
> # Bash/Zsh
> export LD_LIBRARY_PATH="/run/current-system/sw/lib:$LD_LIBRARY_PATH"
> ```
> The flake handles this automatically.

### From source

```bash
git clone https://github.com/peternaame-boop/ytm-player.git
cd ytm-player
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Optional extras

### pip

```bash
pip install "ytm-player[spotify]"          # Spotify playlist import
pip install "ytm-player[mpris]"            # Linux media key support (D-Bus)
pip install "ytm-player[discord]"          # Discord Rich Presence
pip install "ytm-player[lastfm]"           # Last.fm scrobbling
pip install "ytm-player[transliteration]"  # Non-Latin lyric → ASCII
pip install "ytm-player[spotify,mpris,discord,lastfm,transliteration]"  # all
pip install -e ".[dev]"                    # Development tools (pytest, ruff)
```

### AUR

If you installed via AUR, install optional dependencies with pacman/yay — **not** pip (Arch enforces [PEP 668](https://peps.python.org/pep-0668/)):

```bash
sudo pacman -S python-dbus-next            # MPRIS media keys
yay -S python-pylast                       # Last.fm scrobbling
yay -S python-pypresence                   # Discord Rich Presence
yay -S python-spotipy python-thefuzz       # Spotify playlist import
```

## Windows Setup

On Linux and macOS, `mpv` packages include the shared library that ytm-player needs. On Windows, `scoop install mpv` (and most other installers) only ship the **player executable** — the `libmpv-2.dll` library must be downloaded separately.

**Steps:**

1. Install mpv: `scoop install mpv` (or [download from mpv.io](https://mpv.io/installation/))
2. Install 7zip if you don't have it: `scoop install 7zip`
3. Download the latest **`mpv-dev-x86_64-*.7z`** from [shinchiro's mpv builds](https://github.com/shinchiro/mpv-winbuild-cmake/releases) (the file starting with `mpv-dev`, not just `mpv`)
4. Extract `libmpv-2.dll` into your mpv directory:

```powershell
7z e "$env:TEMP\mpv-dev-x86_64-*.7z" -o"$env:USERPROFILE\scoop\apps\mpv\current" libmpv-2.dll -y
```

If you installed mpv a different way, place `libmpv-2.dll` next to `mpv.exe` or anywhere on `%PATH%`.

ytm-player automatically searches common install locations (scoop, chocolatey, Program Files) for the DLL.

## Authenticate

```bash
ytm setup                    # Auto-detect browser cookies
ytm setup --browser firefox  # Target a specific browser
ytm setup --manual           # Skip detection, paste headers directly
```

Windows: replace `ytm` with `py -m ytm_player`.

The setup wizard has three modes — see the inline help for details (`ytm setup --help`).

Credentials are stored in `~/.config/ytm-player/auth.json` with `0o600` permissions.

> ⚠️ The `[yt_dlp].remote_components` setting allows fetching external JS components (npm/GitHub). Enable it only if you trust the source and network path.
```

- [ ] **Step 2: Verify the file is well-formed Markdown**

```bash
.venv/bin/python -c "
import re
with open('docs/installation.md') as f:
    content = f.read()
# Check for unbalanced code fences
fences = content.count('\`\`\`')
assert fences % 2 == 0, f'Unbalanced code fences: {fences}'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add docs/installation.md
git commit -m "docs(installation): create dedicated install guide"
```

---

## Task 3: Create `docs/configuration.md`

**Files:**
- Create: `docs/configuration.md`

This doc owns the full `config.toml` + `theme.toml` reference. It MUST include the new v1.7.0 `[playback] resume_on_launch` setting and MUST use `lyrics_current = "#ff4e45"` (NOT the stale `#2ecc71` from the old README).

- [ ] **Step 1: Create the file with the following content**

```markdown
# Configuration

ytm-player reads configuration from TOML files in `~/.config/ytm-player/` (respects `$XDG_CONFIG_HOME`):

| File | Purpose |
|------|---------|
| `config.toml` | General settings, playback, cache, UI, integrations |
| `keymap.toml` | Custom keybinding overrides (full key list: [docs/keybindings.md](keybindings.md)) |
| `theme.toml` | App-specific color overrides on top of the active Textual theme |
| `auth.json` | YouTube Music credentials (auto-generated by `ytm setup`) |

Open the config directory in your editor:

```bash
ytm config
```

## `config.toml`

Every section is optional — anything you don't set falls back to defaults.

### `[general]`

```toml
[general]
startup_page = "library"     # library, search, browse
brand_account_id = ""        # YouTube Brand Account ID (21-digit; find at myaccount.google.com/brandaccounts)
check_for_updates = true     # check PyPI once per 24h, surface a one-time toast on new version
```

### `[playback]`

```toml
[playback]
audio_quality = "high"       # high, medium, low
default_volume = 80          # 0-100
autoplay = true              # auto-play next on track end
seek_step = 5                # seconds per +/- seek
api_timeout = 15             # seconds for ytmusicapi calls before failover
resume_on_launch = true      # restore last-playing track + position on app start; press space to continue
```

> `resume_on_launch` (added v1.7.0) stages the last-playing track + position into the playback bar on startup. Press space to continue from where you were. Set to `false` to start fresh every time.

### `[cache]`

```toml
[cache]
enabled = true
max_size_mb = 1024           # 1GB default LRU audio cache
prefetch_next = true         # resolve next track's stream URL in background for instant skip
```

### `[yt_dlp]`

```toml
[yt_dlp]
cookies_file = ""            # Optional: path to yt-dlp Netscape cookies.txt
remote_components = ""       # Optional: ejs:npm/ejs:github (enables remote JS component downloads)
js_runtimes = ""             # Optional: bun, bun:/path/to/bun, node, quickjs, etc.
```

### `[ui]`

```toml
[ui]
album_art = true             # show colored half-block album art in playback bar
progress_style = "block"     # block or line
sidebar_width = 30
col_index = 4                # 0 = auto-fill width
col_title = 0                # 0 = auto-fill
col_artist = 30
col_album = 25
col_duration = 8
bidi_mode = "auto"           # auto, reorder, passthrough — RTL text handling
```

### `[notifications]`

```toml
[notifications]
enabled = true
timeout_seconds = 5
```

### `[mpris]`

```toml
[mpris]
enabled = true
```

### `[discord]`

```toml
[discord]
enabled = false              # requires `pip install ytm-player[discord]`
```

### `[lastfm]`

```toml
[lastfm]
enabled = false              # requires `pip install ytm-player[lastfm]`
api_key = ""
api_secret = ""
session_key = ""
username = ""
```

### `[logging]`

```toml
[logging]
level = "INFO"               # DEBUG, INFO, WARNING, ERROR
max_bytes = 1048576          # 1 MB per log file before rotation
backup_count = 5             # number of rotated logs to keep
```

## `theme.toml`

Base colors (primary, background, etc.) come from the active Textual theme — switch themes with `Ctrl+P`. The `theme.toml` file overrides app-specific colors only:

```toml
[colors]
playback_bar_bg = "#1a1a1a"
selected_item = "#2a2a2a"
progress_filled = "#ff0000"
progress_empty = "#555555"
lyrics_played = "#999999"
lyrics_current = "#ff4e45"   # defaults to the theme accent if unset
lyrics_upcoming = "#aaaaaa"
active_tab = "#ffffff"
inactive_tab = "#999999"
```

> The `lyrics_current` color falls back to the active theme's accent (and then to `#ff4e45` red as the absolute last-resort default). Override only if you want something different from your theme's accent.

## `keymap.toml`

For custom keybinding overrides, see [docs/keybindings.md](keybindings.md) for the full key list and the customization syntax.
```

- [ ] **Step 2: Verify the file is well-formed**

```bash
.venv/bin/python -c "
with open('docs/configuration.md') as f:
    content = f.read()
fences = content.count('\`\`\`')
assert fences % 2 == 0, f'Unbalanced code fences: {fences}'
# Verify the corrected lyrics_current default appears
assert '#ff4e45' in content, 'Missing #ff4e45 (corrected default)'
assert '#2ecc71' not in content, 'Stale #2ecc71 still present'
# Verify resume_on_launch is documented
assert 'resume_on_launch' in content, 'Missing resume_on_launch'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add docs/configuration.md
git commit -m "docs(configuration): create full config reference"
```

---

## Task 4: Create `docs/keybindings.md`

**Files:**
- Create: `docs/keybindings.md`

Owns the full keyboard + mouse reference. Must include `l` (added v1.7.0) for the like-toggle.

- [ ] **Step 1: Create the file with the following content**

```markdown
# Keybindings

## Keyboard

| Key | Action |
|-----|--------|
| `space` | Play/Pause |
| `n` | Next track |
| `p` | Previous track |
| `l` | Toggle like on currently playing track |
| `+` / `-` | Volume up/down |
| `j` / `k` | Move down/up |
| `enter` | Select / play |
| `g l` | Go to Library |
| `g s` | Go to Search |
| `g b` | Go to Browse |
| `g y` | Go to Liked Songs |
| `g r` | Go to Recently Played |
| `z` | Go to Queue |
| `g L` | Toggle lyrics sidebar |
| `Ctrl+e` | Toggle playlist sidebar |
| `Ctrl+a` | Toggle album art in playback bar |
| `Ctrl+p` | Change theme |
| `?` | Help (full keybinding reference inside the app) |
| `tab` | Focus next panel |
| `a` | Track actions menu |
| `/` | Filter current list |
| `Ctrl+r` | Cycle repeat mode (off → all → one) |
| `Ctrl+s` | Toggle shuffle |
| `T` | Toggle lyrics transliteration (ASCII) |
| `s t` / `s a` / `s A` / `s d` | Sort by Title / Artist / Album / Duration |
| `s r` | Reverse current sort |
| `backspace` | Go back |
| `q` | Quit |

## Mouse

| Action | Where | Effect |
|--------|-------|--------|
| Click | Progress bar | Seek to position |
| Scroll up/down | Progress bar | Scrub forward/backward (commits after 0.6s pause) |
| Scroll up/down | Volume display | Adjust volume by 5% |
| Click | Repeat button | Cycle repeat mode (off → all → one) |
| Click | Shuffle button | Toggle shuffle on/off |
| Click | Heart button | Toggle like on currently playing track |
| Click | Footer buttons | Navigate pages, play/pause, prev/next |
| Right-click | Track row | Open context menu (play, queue, add to playlist, etc.) |

## Custom keybindings

To rebind keys, edit `~/.config/ytm-player/keymap.toml`. The file maps action names to lists of keys. Example — change like-toggle from `l` to `Ctrl+l`:

```toml
[keys]
like_toggle = ["ctrl+l"]
```

Multi-key sequences use space separation (e.g. `["g s"]` for "press g then s").

A complete list of action names is shown in the in-app help (`?`).
```

- [ ] **Step 2: Verify**

```bash
.venv/bin/python -c "
with open('docs/keybindings.md') as f:
    content = f.read()
assert 'l' in content and 'like' in content.lower(), 'Missing like keybinding'
assert 'g s' in content, 'Missing search shortcut'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add docs/keybindings.md
git commit -m "docs(keybindings): create full keyboard + mouse reference"
```

---

## Task 5: Create `docs/cli-reference.md`

**Files:**
- Create: `docs/cli-reference.md`

Comprehensive — every `ytm` subcommand. The current README's "Usage" section is incomplete (missing several commands).

- [ ] **Step 1: Create the file with the following content**

```markdown
# CLI Reference

ytm-player has three modes:
- **TUI** (default) — `ytm` launches the interactive terminal UI.
- **CLI** — headless subcommands that work without the TUI running (search, stats, history, cache).
- **IPC** — control a running TUI from another terminal (play, pause, next, queue control).

Windows: replace `ytm` with `py -m ytm_player` in any of the commands below.

## Setup

```bash
ytm setup                    # Auto-detect browser cookies
ytm setup --browser firefox  # Target a specific browser (chrome, firefox, brave, edge, chromium, vivaldi, opera, helium)
ytm setup --manual           # Skip detection, paste raw request headers
```

## Search

```bash
ytm search "daft punk"
ytm search "bohemian rhapsody" --filter songs --json
```

Available filters: `songs`, `videos`, `albums`, `artists`, `playlists`, `community_playlists`, `featured_playlists`.

## Stats and history

```bash
ytm stats                    # Listening stats summary
ytm stats --json             # Machine-readable
ytm history                  # Recent play history
ytm history search           # Recent search history
```

## Cache management

```bash
ytm cache status             # Cache size + entry count
ytm cache clear              # Wipe all cached audio
```

## Playback control (IPC, requires TUI running)

```bash
ytm play                     # Resume playback
ytm pause                    # Pause playback
ytm next                     # Skip to next track
ytm prev                     # Previous track
ytm seek +10                 # Seek forward 10 seconds
ytm seek -5                  # Seek backward 5 seconds
ytm seek 1:30                # Seek to 1:30 (m:ss or h:mm:ss)
```

## Like / dislike (IPC)

```bash
ytm like                     # Like current track
ytm dislike                  # Dislike current track
ytm unlike                   # Remove like/dislike (sets to INDIFFERENT)
```

## Status (IPC)

```bash
ytm now                      # Current track info (JSON)
ytm status                   # Player status (JSON)
ytm queue                    # Queue contents (JSON)
ytm queue add VIDEO_ID       # Add track by video ID
ytm queue clear              # Clear queue
```

## Spotify import

```bash
ytm import "https://open.spotify.com/playlist/..."
```

Interactive flow — see [docs/spotify-import.md](spotify-import.md).

## Diagnostics

```bash
ytm doctor                   # Version, paths, log tail, recent crash trace
ytm config                   # Open config dir in your editor
ytm --debug                  # Launch with verbose logging
```
```

- [ ] **Step 2: Verify**

```bash
.venv/bin/python -c "
with open('docs/cli-reference.md') as f:
    content = f.read()
for cmd in ['ytm setup', 'ytm search', 'ytm play', 'ytm pause', 'ytm like', 'ytm dislike', 'ytm now', 'ytm doctor', 'ytm config', 'ytm import']:
    assert cmd in content, f'Missing: {cmd}'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add docs/cli-reference.md
git commit -m "docs(cli-reference): create comprehensive CLI subcommand reference"
```

---

## Task 6: Create `docs/spotify-import.md`

**Files:**
- Create: `docs/spotify-import.md`

References `screenshot-spotify-import.png` (now at `docs/screenshot-spotify-import.png`, so the relative path is just the filename).

- [ ] **Step 1: Create the file with the following content**

```markdown
# Spotify Import

Import your Spotify playlists into YouTube Music — from the TUI or CLI.

![Spotify import popup](screenshot-spotify-import.png)

## How it works

1. **Extract** — Reads track names and artists from the Spotify playlist.
2. **Match** — Searches YouTube Music for each track using fuzzy matching (title 60% + artist 40% weighted score).
3. **Resolve** — Tracks scoring 85%+ are auto-matched. Lower scores prompt you to pick from candidates or skip.
4. **Create** — Creates a new private playlist on your YouTube Music account with all matched tracks.

## Two modes

| Mode | Use case | How |
|------|----------|-----|
| **Single** (≤100 tracks) | Most playlists | Paste one Spotify URL |
| **Multi** (100+ tracks) | Large playlists split across parts | Enter a name + number of parts, paste a URL for each |

## From the TUI

Click **Import** in the footer bar (or press the import button). A popup lets you paste URLs, choose single/multi mode, and watch progress in real time.

## From the CLI

```bash
ytm import "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
```

Interactive flow: fetches tracks, shows match results, lets you resolve ambiguous/missing tracks, name the playlist, then creates it.

## Extraction methods

The importer tries two approaches in order:

1. **Spotify Web API** (full pagination, handles any playlist size) — requires a free [Spotify Developer](https://developer.spotify.com/) app. On first use, you'll be prompted for your `client_id` and `client_secret`, which are stored in `~/.config/ytm-player/spotify.json`.
2. **Scraper fallback** (no credentials needed, limited to ~100 tracks) — used automatically if API credentials aren't configured.

For playlists over 100 tracks, set up the API credentials.
```

- [ ] **Step 2: Verify**

```bash
.venv/bin/python -c "
import os
with open('docs/spotify-import.md') as f:
    content = f.read()
assert 'screenshot-spotify-import.png' in content, 'Missing screenshot reference'
assert os.path.exists('docs/screenshot-spotify-import.png'), 'Screenshot file missing from docs/'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add docs/spotify-import.md
git commit -m "docs(spotify-import): create Spotify playlist import guide"
```

---

## Task 7: Create `docs/troubleshooting.md`

**Files:**
- Create: `docs/troubleshooting.md`

- [ ] **Step 1: Create the file with the following content**

```markdown
# Troubleshooting

## "mpv not found" or playback doesn't start

Ensure mpv is installed and in your `$PATH`:

```bash
mpv --version
```

If installed but not found, check that the `libmpv` shared library is available:

```bash
# Arch
pacman -Qs mpv

# Ubuntu/Debian — you may need the dev package
sudo apt install libmpv-dev
```

For Windows-specific libmpv setup, see [docs/installation.md#windows-setup](installation.md#windows-setup).

## Authentication fails

- Make sure you're signed in to YouTube Music (free or Premium) in your browser.
- Try a different browser: `ytm setup` auto-detects Chrome, Firefox, Brave, Edge, Chromium, Vivaldi, Opera, Helium.
- If auto-detection fails, use the manual paste method: `ytm setup --manual`.
- Re-run `ytm setup` to re-authenticate.
- For multi-account or Brand Account setups: `ytm setup` will detect multiple Google accounts and prompt you to pick. Brand Accounts can also be configured via `[general] brand_account_id` in `config.toml`.

## No sound / wrong audio device

mpv uses your system's default audio output. To change it, create `~/.config/mpv/mpv.conf`:

```
audio-device=pulse/your-device-name
```

List available devices with `mpv --audio-device=help`.

## macOS media keys open Apple Music instead of ytm-player

- ytm-player registers with macOS Now Playing while running, so media keys should target it.
- Start playback in `ytm` first; macOS routes media keys to the active Now Playing app.
- Grant Accessibility and Input Monitoring permission to your terminal app (Terminal, Ghostty, iTerm) in System Settings → Privacy & Security.
- If Apple Music still steals keys, fully quit Music.app and press play/pause once in ytm.

## MPRIS / media keys not working (Linux)

Install the optional MPRIS dependency:

```bash
pip install -e ".[mpris]"
# or, on Arch:
sudo pacman -S python-dbus-next
```

Requires D-Bus (standard on most Linux desktops). Verify with:

```bash
dbus-send --session --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames
```

## Cache taking too much space

```bash
ytm cache status   # Check cache size
ytm cache clear    # Wipe all cached audio
```

Or reduce the limit in `config.toml`:

```toml
[cache]
max_size_mb = 512
```

## Logs and diagnostics

ytm-player writes a rotating log file to:

- Linux/macOS: `~/.config/ytm-player/logs/ytm.log`
- Windows: `%APPDATA%\ytm-player\logs\ytm.log`

Crash tracebacks for any unhandled exception (main thread or background thread) are saved to the `crashes/` directory next to the log file.

For verbose logs, launch with `--debug`:

```bash
ytm --debug
```

When reporting a bug, please run:

```bash
ytm doctor
```

and paste the output into your GitHub issue. It includes the version, your Python and mpv versions, paths, the last 50 log lines, and the most recent crash trace if any.
```

- [ ] **Step 2: Verify**

```bash
.venv/bin/python -c "
with open('docs/troubleshooting.md') as f:
    content = f.read()
fences = content.count('\`\`\`')
assert fences % 2 == 0, f'Unbalanced code fences: {fences}'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add docs/troubleshooting.md
git commit -m "docs(troubleshooting): create dedicated troubleshooting guide"
```

---

## Task 8: Create `docs/architecture.md`

**Files:**
- Create: `docs/architecture.md`

The file tree MUST include `app/_base.py` (added v1.7.0) — the current README tree is missing it.

- [ ] **Step 1: Create the file with the following content**

```markdown
# Architecture

For users curious about how the app is organized, and contributors getting started. For dev workflow (lint, test, ruff order, etc.) see [CONTRIBUTING.md](../CONTRIBUTING.md).

## File tree

```
src/ytm_player/
├── app/                # Main Textual application (mixin package)
│   ├── _app.py         #   Class def, __init__, compose, lifecycle
│   ├── _base.py        #   YTMHostBase TYPE_CHECKING stub for Pyright (mixin attrs)
│   ├── _playback.py    #   play_track, player events, history, download
│   ├── _keys.py        #   Key handling and action dispatch
│   ├── _sidebar.py     #   Sidebar toggling and playlist sidebar events
│   ├── _navigation.py  #   Page navigation and nav stack
│   ├── _ipc.py         #   IPC command handling for CLI
│   ├── _track_actions.py  # Track selection, actions popup, radio
│   ├── _session.py     #   Session save/restore (queue, volume, last-playing track)
│   └── _mpris.py       #   MPRIS/media key callbacks
├── cli.py              # Click CLI entry point
├── ipc.py              # Unix socket IPC for CLI ↔ TUI
├── config/             # Settings, keymap, theme (TOML)
├── services/           # Backend services
│   ├── auth.py         #   Browser cookie auth (multi-account aware)
│   ├── ytmusic.py      #   YouTube Music API wrapper
│   ├── player.py       #   mpv audio playback
│   ├── stream.py       #   yt-dlp stream URL resolution
│   ├── queue.py        #   Playback queue with shuffle/repeat
│   ├── history.py      #   SQLite play/search history
│   ├── cache.py        #   LRU audio file cache
│   ├── lrclib.py       #   LRCLIB.net synced lyrics fallback (with title sanitization)
│   ├── mpris.py        #   D-Bus MPRIS media controls (Linux)
│   ├── macos_media.py  #   macOS Now Playing integration
│   ├── macos_eventtap.py  # macOS hardware media key interception
│   ├── mediakeys.py    #   Cross-platform media key service
│   ├── download.py     #   Offline audio downloads
│   ├── discord_rpc.py  #   Discord Rich Presence
│   ├── lastfm.py       #   Last.fm scrobbling
│   ├── yt_dlp_options.py  # yt-dlp config/cookie handling
│   └── spotify_import.py  # Spotify playlist import
├── ui/
│   ├── header_bar.py   # Top bar with sidebar toggle buttons
│   ├── playback_bar.py # Persistent bottom bar (track info, progress, controls, heart)
│   ├── theme.py        # Textual theme integration + app-specific color overrides
│   ├── sidebars/       # Persistent playlist sidebar (left) and lyrics sidebar (right)
│   ├── pages/          # Library, Search, Browse, Context, Queue, Liked Songs, Recently Played, Help
│   ├── popups/         # Actions menu, playlist picker, Spotify import
│   └── widgets/        # TrackTable, PlaybackProgress, AlbumArt
└── utils/              # Terminal detection, formatting, BiDi text, transliteration
```

## Stack

| Library | Purpose |
|---------|---------|
| [Textual](https://textual.textualize.io/) | TUI framework |
| [ytmusicapi](https://github.com/sigma67/ytmusicapi) | YouTube Music HTTP API |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Stream URL resolution + offline downloads |
| [python-mpv](https://github.com/jaseg/python-mpv) | mpv playback (libmpv wrapper) |
| [aiosqlite](https://github.com/omnilib/aiosqlite) | Async SQLite for history + cache index |
| [click](https://click.palletsprojects.com/) | CLI framework |
| [Pillow](https://python-pillow.org/) | Album art rendering (downscaled to terminal half-blocks) |
| [dbus-next](https://github.com/altdesktop/python-dbus-next) | MPRIS D-Bus (Linux) — optional |
| [pypresence](https://github.com/qwertyquerty/pypresence) | Discord Rich Presence — optional |
| [pylast](https://github.com/pylast/pylast) | Last.fm scrobbling — optional |

## Key patterns

- **Mixin architecture** — `YTMPlayerApp` is composed from 8 mixins (Playback, Session, Keys, Navigation, Sidebar, TrackActions, MPRIS, IPC). Each mixin extends `YTMHostBase` (in `app/_base.py`), a `TYPE_CHECKING`-only stub class that mirrors the runtime instance attribute surface so Pyright doesn't emit `Cannot access attribute X for class FooMixin` noise. At runtime `YTMHostBase = object` — zero behaviour change.
- **Event-driven playback** — `Player` emits `PlayerEvent` enums (`TRACK_END`, `TRACK_CHANGE`, etc.) dispatched to the Textual event loop via `call_soon_threadsafe`. The app registers callbacks to update the UI.
- **Thread safety** — `Player` and `QueueManager` are singletons with `threading.Lock`. Player events bridge from mpv's callback thread to asyncio.
- **Track format** — All services use a standardized track dict (`video_id`, `title`, `artist`, `artists`, `album`, `album_id`, `duration`, `thumbnail_url`, `is_video`). The `normalize_tracks()` helper in `utils/formatting.py` converts inconsistent ytmusicapi response shapes into this format.
- **Session persistence** — Volume, queue, shuffle/repeat, theme, and the last-playing track + position are saved on every exit. When `[playback] resume_on_launch` is true (default), the last-playing track + position are staged into the playback bar at launch and consumed the first time the user presses play.
- **Playback bar keybindings** — Standard transport keys plus `l` to toggle the like state of the currently playing track.
- **Prefetching** — Next track's stream URL is resolved in the background for instant skip.
- **Page navigation** — `app/_navigation.py` manages a nav stack (max 20). Each page implements `handle_action(action, count)` for vim-style keybinding dispatch and `get_nav_state()` for state preservation across navigation.
- **LC_NUMERIC quirk** — `cli.py` forces `LC_NUMERIC=C` at import time — mpv segfaults without it.
```

- [ ] **Step 2: Verify the file tree mentions `_base.py`**

```bash
.venv/bin/python -c "
with open('docs/architecture.md') as f:
    content = f.read()
assert '_base.py' in content, 'Missing _base.py in architecture file tree'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add docs/architecture.md
git commit -m "docs(architecture): create file tree + stack reference (incl. _base.py)"
```

---

## Task 9: Update `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

Add three short additions covering v1.7.x changes that aren't yet documented in CLAUDE.md.

- [ ] **Step 1: Read the current CLAUDE.md**

Note the current content. Specifically the `## Architecture` section (where the mixin pattern is described).

- [ ] **Step 2: Find the "Key patterns" bullet list (under Architecture)**

The bullet list currently includes: Event-driven playback, Thread safety, Track format, Session persistence, Playback bar keybindings, Prefetching, Page navigation, LC_NUMERIC quirk.

Add a new bullet AFTER "Page navigation" and BEFORE "LC_NUMERIC quirk":

```
- **Lyric current colour:** `theme.py` exports `DEFAULT_LYRIC_CURRENT = "#ff4e45"` as the absolute fallback for the synced-lyrics current-line colour. The fallback chain is `theme.accent` → `theme.primary` → `DEFAULT_LYRIC_CURRENT`, identical across `theme.from_css_variables`, `_app.py:get_css_variables`, and `_app.py:watch_theme`.
- **Python 3.10 compatibility shims:** Three stdlib symbols added in 3.11+ are backported via `sys.version_info >= (3, 11)` checks (which Pyright narrows correctly): `tomllib` (in `config/keymap.py`, `config/settings.py`, `ui/theme.py`, `app/_app.py`, `tests/test_config/test_settings.py`) falls back to `tomli`; `typing.Self` (in the first three of those files) falls back to `typing_extensions.Self`; `enum.StrEnum` (in `services/queue.py`, `services/player.py`) falls back to a small `(str, Enum)` polyfill mirroring stdlib's `auto()` lowercase-name behaviour. `tomli` and `typing_extensions` are conditional dependencies (`python_version < "3.11"`) so 3.11+ users don't pull them.
```

- [ ] **Step 3: Find the "## Distribution" section (or similar near the end)**

Add a new section BEFORE Distribution (or wherever it fits — between "## AUR Package" and "## Distribution" works):

```markdown
## CI Workflows

Two GitHub Actions workflows live in `.github/workflows/`:

- `ci.yml` — runs ruff lint + format check, then pytest on the matrix `[3.10, 3.14]` × `[ubuntu, macos, windows]` (6 jobs total).
- `check-python-versions.yml` — runs monthly (1st of each month, 09:00 UTC) and opens a maintenance issue when CPython releases a new stable major.minor version newer than our matrix ceiling. Idempotent — won't reopen if an issue is already open. Uses pyyaml to parse the matrix robustly.
```

- [ ] **Step 4: Verify the updates landed**

```bash
.venv/bin/python -c "
with open('CLAUDE.md') as f:
    content = f.read()
assert 'DEFAULT_LYRIC_CURRENT' in content, 'Missing DEFAULT_LYRIC_CURRENT note'
assert 'tomllib' in content, 'Missing tomllib shim note'
assert 'check-python-versions.yml' in content, 'Missing watcher workflow note'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(CLAUDE): note 3.10 shims, watcher workflow, DEFAULT_LYRIC_CURRENT"
```

---

## Task 10: Update `CONTRIBUTING.md`

**Files:**
- Modify: `CONTRIBUTING.md`

Add one short subsection on Python version compatibility for new contributors editing files that import 3.11+ stdlib symbols, plus a note about the Pyright YTMHostBase pattern for new mixins.

- [ ] **Step 1: Read the current CONTRIBUTING.md**

- [ ] **Step 2: Find the "## PR norms" section**

Insert a NEW section AFTER PR norms and BEFORE "## Architecture pointers":

```markdown
## Python version compatibility

The project supports Python 3.10+. Two compatibility patterns matter when editing source:

**3.11+ stdlib symbols** — if you need `tomllib`, `typing.Self`, or `enum.StrEnum`, use a `sys.version_info` shim instead of importing directly:

```python
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    # Python 3.10 backport via PyPI
    import tomli as tomllib  # pyright: ignore[reportMissingImports]
```

Pyright narrows on `sys.version_info` correctly, so the `# pyright: ignore` only needs to sit on the else branch. `tomli` and `typing_extensions` are already declared as conditional deps in `pyproject.toml` (`python_version < "3.11"`).

**Mixin attribute typing** — mixins in `src/ytm_player/app/_*.py` (PlaybackMixin, SessionMixin, etc.) extend `YTMHostBase` from `app/_base.py`, a `TYPE_CHECKING`-only stub class that mirrors the runtime instance attribute surface. At runtime `YTMHostBase = object` — zero behaviour change. If you add a new instance attribute to `YTMPlayerApp.__init__` and reference it from a mixin, also declare it on `YTMHostBase` so Pyright doesn't emit "Cannot access attribute X" noise.
```

- [ ] **Step 3: Verify**

```bash
.venv/bin/python -c "
with open('CONTRIBUTING.md') as f:
    content = f.read()
assert 'sys.version_info' in content, 'Missing version_info shim note'
assert 'YTMHostBase' in content, 'Missing YTMHostBase note'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs(CONTRIBUTING): add Python version compatibility section"
```

---

## Task 11: Replace `README.md` with the lean landing page

**Files:**
- Modify: `README.md` (full replace)

This is the headline change. The new README is purely a landing-page index.

- [ ] **Step 1: Replace `README.md` with this exact content**

```markdown
# ytm-player

A full-featured YouTube Music player for the terminal. Browse your library, search, queue tracks, and control playback — all from a TUI with vim-style keybindings. Runs on Linux, macOS, and Windows.

![ytm-player screenshot](https://raw.githubusercontent.com/peternaame-boop/ytm-player/master/screenshot-v5.png)

## Features

- **Vim-style keybindings** — j/k movement, multi-key sequences (`g s` for search, `g l` for library), count prefixes (`5j`)
- **Synced lyrics** — live-highlighted with LRCLIB fallback for tracks YouTube doesn't have, with title sanitization for better LRCLIB matches
- **mpv backend** — gapless audio, stream prefetching, broad codec support
- **Cross-platform native integrations** — MPRIS (Linux), Now Playing (macOS), media keys (Windows)
- **Theming** — 18+ Textual themes plus per-app color overrides in `theme.toml`
- **Spotify import** — pull playlists in via API or scraper fallback
- **CLI + IPC** — control a running TUI from another terminal (`ytm play`, `ytm pause`, etc.)
- **Free-tier support** — works without YouTube Music Premium
- **Session resume** — last-playing track + queue restored on launch
- **Local cache** — LRU audio cache for offline-like replay of previously heard tracks
- **Discord + Last.fm** — Rich Presence and scrobbling

## Requirements

- **Python 3.10+**
- **[mpv](https://mpv.io/)** (audio playback backend, must be installed system-wide)
- A YouTube Music account (free or Premium)

## Install

```bash
# PyPI (Linux / macOS / Windows)
pip install ytm-player

# Arch / CachyOS / Manjaro (AUR)
yay -S ytm-player-git
```

For NixOS, Gentoo, Windows-specific mpv DLL setup, source builds, and optional extras (Discord, Last.fm, Spotify import, etc.), see [docs/installation.md](docs/installation.md).

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
| Full keyboard + mouse keybindings | [docs/keybindings.md](docs/keybindings.md) |
| All `ytm` CLI subcommands | [docs/cli-reference.md](docs/cli-reference.md) |
| Spotify playlist import | [docs/spotify-import.md](docs/spotify-import.md) |
| Troubleshooting (mpv / auth / MPRIS / macOS / cache) | [docs/troubleshooting.md](docs/troubleshooting.md) |
| File layout + stack | [docs/architecture.md](docs/architecture.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security policy | [SECURITY.md](SECURITY.md) |

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full release history.
```

- [ ] **Step 2: Verify the new README is between 100 and 130 lines**

```bash
wc -l README.md
```

Expected: 100-130 lines.

- [ ] **Step 3: Verify essential elements**

```bash
.venv/bin/python -c "
with open('README.md') as f:
    content = f.read()
assert 'screenshot-v5.png' in content, 'Wrong screenshot reference'
assert 'docs/installation.md' in content, 'Missing installation link'
assert 'docs/configuration.md' in content, 'Missing configuration link'
assert 'docs/keybindings.md' in content, 'Missing keybindings link'
assert 'docs/cli-reference.md' in content, 'Missing CLI link'
assert 'docs/spotify-import.md' in content, 'Missing Spotify link'
assert 'docs/troubleshooting.md' in content, 'Missing troubleshooting link'
assert 'docs/architecture.md' in content, 'Missing architecture link'
assert 'Python 3.10+' in content, 'Wrong Python version'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(README): rewrite as lean landing-page index"
```

---

## Task 12: Link-check verification

**Files:** None modified (verification only).

Verify every internal link in README.md and docs/*.md resolves to a real file.

- [ ] **Step 1: Run the link checker**

```bash
for f in README.md docs/*.md; do
  grep -oP '\[[^\]]+\]\(\K[^)]+(?=\))' "$f" | while read link; do
    case "$link" in
      http*|mailto:*|\#*) ;;  # external or anchor, skip
      *)
        # Strip any anchor fragment
        path="${link%%#*}"
        # Resolve relative to the file's directory
        if [ -e "$(dirname "$f")/$path" ] || [ -e "$path" ]; then
          :  # OK
        else
          echo "BROKEN: $f → $link"
        fi
        ;;
    esac
  done
done
echo "Link check complete."
```

Expected: only the line `Link check complete.` — no `BROKEN:` entries.

- [ ] **Step 2: Run pytest, ruff, pyright as full sanity check**

```bash
.venv/bin/pytest -q 2>&1 | tail -3
.venv/bin/ruff format --check src/ tests/
.venv/bin/ruff check src/ tests/
pyright src/ytm_player/services/player.py 2>&1 | tail -3
```

Expected: 545 passed, ruff clean, pyright on player.py shows the same baseline (1 pre-existing error around line 142).

- [ ] **Step 3: No commit (verification only)**

If any link is broken, fix it inline (likely a typo) then re-run. Once clean, proceed to Task 13.

---

## Task 13: Bump version + rewrite CHANGELOG entry

**Files:**
- Modify: `src/ytm_player/__init__.py` (`__version__`)
- Modify: `aur/PKGBUILD` (`pkgver`)
- Modify: `CHANGELOG.md` (collapse v1.7.1 entry into combined v1.7.2 entry)

- [ ] **Step 1: Bump `__version__` to "1.7.2"**

In `src/ytm_player/__init__.py`, change:
```python
__version__ = "1.7.1"
```
to:
```python
__version__ = "1.7.2"
```

- [ ] **Step 2: Bump `aur/PKGBUILD` pkgver to 1.7.2**

In `aur/PKGBUILD`, change `pkgver=1.7.1` to `pkgver=1.7.2`.

- [ ] **Step 3: Rewrite the CHANGELOG entry**

In `CHANGELOG.md`, find the existing `### v1.7.1 (2026-04-27)` entry and the `---` separator above it. REPLACE the entire v1.7.1 entry (everything between the `---` separator before it and the `---` separator before v1.7.0) with:

```markdown
### v1.7.2 (2026-04-27)

A docs and compatibility release. Lowers Python floor to 3.10 (Ubuntu 22.04 stock support), restructures the README into a lean landing page with seven dedicated docs files in `docs/`, and adds a monthly Python release watcher.

**New**

- README has been split into a 120-line landing page plus seven dedicated docs (`docs/installation.md`, `docs/configuration.md`, `docs/keybindings.md`, `docs/cli-reference.md`, `docs/spotify-import.md`, `docs/troubleshooting.md`, `docs/architecture.md`). The README is now purely an index — every topic lives in exactly one file with full detail.

**Project**

- Python floor lowered from 3.12 to 3.10. Ubuntu 22.04 LTS users can now `pip install ytm-player` against the system `python3` without installing a newer Python first. Verified locally on Python 3.10 (545/545 tests passing) and via the new CI matrix `[3.10, 3.14]`.
- Note on Python 3.10 lifecycle: CPython 3.10 reaches end-of-life October 2026. Ubuntu 22.04 keeps shipping 3.10 until April 2027 (standard support) or 2032 (Pro), so 22.04 users stay covered well past CPython's EOL. We'll bump the floor when usage data shows nobody on 3.10.
- CI matrix shifted from `[3.12, 3.13]` to `[3.10, 3.14]` — testing the supported floor + the latest stable. Same 6 jobs as before (3 OSes × 2 Pythons), better-targeted coverage.
- New monthly workflow `check-python-versions.yml` opens a maintenance issue when CPython releases a new stable major.minor version newer than our CI matrix ceiling. Idempotent — won't reopen if an issue is already open. Defensive regex guard rejects RC/beta strings to avoid bogus issues.
- Pyright + ruff configured to type-check and lint against `py310` so accidentally-introduced 3.11+ syntax fails locally and in CI.
- Lint job + Python release watcher updated to use Python 3.14 (was 3.12), aligning auxiliary tooling with the test matrix ceiling.
- Classifiers updated: now lists Python 3.10, 3.11, 3.12, 3.13, 3.14.
- `flake.nix` Python pin bumped from 3.12 to 3.13 (a stable middle of the supported range).
- AUR PKGBUILD maintainer email replaced (was a placeholder).
- Replaced hero screenshot (v4 → v5).

**Fixes**

- Theme cache (`_read_theme_toml_cached`) was silently returning `{}` on Python 3.10 because its function-local `import tomllib` was caught by a broad except clause. The bug was masked on 3.12 (where tomllib is stdlib) but would have shipped a non-functional theme cache to 3.10 users. Caught during the 3.10 verification gate; fixed by moving the import to module-level with a `sys.version_info` shim.

**Compatibility shims**

To support Python 3.10 (where several stdlib symbols don't exist), backport shims were added using `sys.version_info >= (3, 11)` checks (which type-checkers narrow correctly):

- `tomllib` (3.11+) → falls back to `tomli` (PyPI) on 3.10. Files: `config/keymap.py`, `config/settings.py`, `ui/theme.py`, `app/_app.py`, `tests/test_config/test_settings.py`.
- `typing.Self` (3.11+) → falls back to `typing_extensions.Self` on 3.10. Same first 3 files.
- `enum.StrEnum` (3.11+) → falls back to a `(str, Enum)` polyfill that mirrors stdlib's `auto()` lowercase-name behavior. Files: `services/queue.py`, `services/player.py`.
- `tomli` and `typing_extensions` added as conditional dependencies (`python_version < "3.11"` markers) so 3.11+ users don't pull them.
```

(Note: the resulting CHANGELOG.md should have the v1.7.2 entry above v1.7.0. There should be NO v1.7.1 entry left.)

- [ ] **Step 4: Verify everything still passes**

```bash
.venv/bin/pytest -q 2>&1 | tail -3
.venv/bin/ruff format --check src/ tests/
.venv/bin/ruff check src/ tests/
```

Expected: 545 passed, ruff clean.

- [ ] **Step 5: Confirm CHANGELOG has no orphan v1.7.1 entry**

```bash
grep -c "^### v1\.7\.1" CHANGELOG.md
```

Expected: `0`.

```bash
grep -c "^### v1\.7\.2" CHANGELOG.md
```

Expected: `1`.

- [ ] **Step 6: Commit**

```bash
git add src/ytm_player/__init__.py aur/PKGBUILD CHANGELOG.md
git commit -m "chore(release): v1.7.2"
```

---

## Task 14: Ship sequence (controller-led)

**Files:** None modified — orchestration only.

This task touches external systems (PyPI, AUR, GitHub Releases) and runs after Peter's QA gate. The controller (not a subagent) executes these steps and confirms each result before proceeding to the next.

- [ ] **Step 1: Push master**

```bash
git push origin master
```

- [ ] **Step 2: Watch CI go green**

Wait ~3-5 minutes, then:

```bash
gh run list --branch master --limit 4
```

Expected: latest CI run shows `completed success` for all jobs.

If anything fails, STOP. Diagnose locally, push a fix commit, watch again. Do not tag until CI is green.

- [ ] **Step 3: Tag and push**

```bash
git tag v1.7.2
git push origin v1.7.2
```

- [ ] **Step 4: Build artifacts**

```bash
rm -rf dist/ build/
.venv/bin/python -m build --wheel --sdist
```

Expected: `Successfully built ytm_player-1.7.2-py3-none-any.whl and ytm_player-1.7.2.tar.gz`.

- [ ] **Step 5: Upload to PyPI**

```bash
.venv/bin/twine upload dist/ytm_player-1.7.2*
```

Expected: `View at: https://pypi.org/project/ytm-player/1.7.2/`.

- [ ] **Step 6: Update AUR**

```bash
rm -rf /tmp/ytm-player-aur
git clone ssh://aur@aur.archlinux.org/ytm-player-git.git /tmp/ytm-player-aur
cp aur/PKGBUILD /tmp/ytm-player-aur/PKGBUILD
sed -i 's/pkgver = 1\.7\.1/pkgver = 1.7.2/' /tmp/ytm-player-aur/.SRCINFO
cd /tmp/ytm-player-aur
git add PKGBUILD .SRCINFO
git commit -m "Update to v1.7.2"
git push
cd /home/wiz/AI/ytm-player
rm -rf /tmp/ytm-player-aur
```

Expected: AUR push succeeds with no `.SRCINFO unchanged` warning.

- [ ] **Step 7: Create GitHub Release**

Use the v1.7.2 CHANGELOG entry as the release body:

```bash
gh release create v1.7.2 --title "v1.7.2" --notes-file <(awk '/^### v1\.7\.2/,/^---$/' CHANGELOG.md | sed '$d')
```

(The awk extracts the v1.7.2 entry; the `sed '$d'` drops the trailing `---` separator.)

Expected: release URL printed.

- [ ] **Step 8: Manually trigger the watcher workflow**

```bash
gh workflow run check-python-versions.yml
sleep 30
gh run list --workflow=check-python-versions.yml --limit 1
```

Expected: most recent run shows `completed success`. Since the matrix ceiling is `3.14` and current upstream stable is also `3.14`, the workflow should detect parity and skip issue creation.

---

## Acceptance criteria (final checklist)

- [ ] README.md is 100-130 lines, pure landing page with `screenshot-v5.png` reference and links to all 7 docs.
- [ ] All 7 `docs/*.md` files exist with content per the content map in the spec.
- [ ] `docs/screenshot-spotify-import.png` exists; root-level copy is gone.
- [ ] All sweep findings applied:
  - `l` keybinding in `docs/keybindings.md`
  - `resume_on_launch` in `docs/configuration.md`
  - `lyrics_current = "#ff4e45"` (NOT `#2ecc71`) in `docs/configuration.md`
  - `app/_base.py` in `docs/architecture.md` file tree
  - LRCLIB title sanitization mentioned in README Features bullet
  - Full CLI reference in `docs/cli-reference.md`
  - CLAUDE.md additions for shims + watcher + DEFAULT_LYRIC_CURRENT
  - CONTRIBUTING.md additions for shim pattern + YTMHostBase
  - `pyproject.toml:124` past tense
  - `src/ytm_player/services/player.py:155` updated
  - `flake.nix` uses `python313`
- [ ] `__version__` is `"1.7.2"`, `aur/PKGBUILD` is `pkgver=1.7.2`.
- [ ] CHANGELOG.md has a single combined v1.7.2 entry; no orphan v1.7.1 entry.
- [ ] All internal links in README + docs/*.md resolve.
- [ ] 545 tests pass; ruff clean.
- [ ] PyPI 1.7.2 published; AUR pushed; GitHub Release v1.7.2 created.
- [ ] check-python-versions watcher manually triggered once and ran cleanly.
