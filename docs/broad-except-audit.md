# Broad `except Exception:` audit — 2026-04-28

**Status:** Complete (2026-04-28).
**Total sites:** 263 across `src/ytm_player/`.

## Executive summary

263 broad `except Exception:` sites were audited across 33+ files in `src/ytm_player/`. The final distribution is **176 KEEP / 87 NARROW / 0 PROMOTE**: most broad-catches are intentional graceful-degrade contracts (services return safe defaults like `[]`/`{}`/`None`/`""` on any failure, and UI handlers wrap them assuming services don't raise — a deliberate two-layer safety net), and nothing in the codebase is an outright catch-and-corrupt-state offender. The headline NARROW findings cluster into four areas: (1) the `services/ytmusic.py:_call()` outer catch that drives the failure-counter + reinit logic — the only outer-loop broad-catch in the codebase that actually does anything beyond logging, and currently bumps its counter for any exception including programming bugs; (2) three mutation methods (`rate_song`, `add_playlist_items`, `remove_playlist_items`) that return `None` on silent failure, with UI cascade sinks (`spotify_import.py:900` worst offender — popup claims success on partial-add failures); (3) the `app/_session.py:211` write-path that silently loses the user's queue / current track / resume position with no user-visible signal; and (4) ~82 trivial single-call NARROWs concentrated in UI widgets — repetitive `query_one(...) + act` blocks where the only realistic failure is `NoMatches` and the catch is wider than necessary, masking real bugs. **Bottom line: this is mostly a logging-hygiene sweep + four NARROW clusters with cascade-aware sequencing — NOT a sweeping refactor.** The cascade between service-layer narrowing (4.1, 4.3) and the UI handlers that wrap those calls (Phase 5) is the load-bearing sequencing constraint; everything else commits independently.

## Categorization legend

- **KEEP** — broad-catch is the intentional contract. The handler returns a safe default (empty list, `False`, `None`) and the system depends on no exception propagating.
- **NARROW** — broad-catch is hiding a real bug. Should specify expected exception types and let unexpected propagate.
- **PROMOTE** — should not catch at all. Silent failure leaves state inconsistent.

## Per-file findings

### `services/ytmusic.py` (29 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 65 | `_call()` outer catch — wraps `asyncio.wait_for(asyncio.to_thread(func, ...))` for every ytmusicapi call | **NARROW** | Tracks `_consecutive_api_failures`, reinits client at threshold (3), then re-raises. Should distinguish auth errors (signal to reauth, don't count toward reinit), network errors (`requests.RequestException`, `TimeoutError` — count + retry), and ytmusicapi-specific errors from unexpected exceptions (which should propagate as bugs, not silently bump the failure counter). Bundle with thread-safety on the `client` property in Phase 4. |
| 107 | `search()` — wraps `client.search` via `_call()` | KEEP | Intentional graceful-degrade — returns `[]` on any API error after `TimeoutError` is handled separately. UI assumes search never raises. |
| 115 | `get_search_suggestions()` — wraps `client.get_search_suggestions` | KEEP | Returns `[]` on failure; called on every keystroke during typeahead, must not raise. |
| 127 | `get_library_playlists()` — wraps `client.get_library_playlists` | KEEP | Returns `[]` on failure; library page renders empty rather than crashing. |
| 135 | `get_library_albums()` — wraps `client.get_library_albums` | KEEP | Returns `[]` on failure; same pattern as library playlists. |
| 143 | `get_library_artists()` — wraps `client.get_library_subscriptions` | KEEP | Returns `[]` on failure; same pattern. |
| 154 | `get_liked_songs()` — wraps `client.get_liked_songs`, extracts `tracks` key | KEEP | Returns `[]` on failure; LikedSongs page renders empty rather than crashing. |
| 166 | `get_home()` — wraps `client.get_home` | KEEP | Returns `[]` on failure; home/browse page degrades gracefully. (Uses `exc_info=True` on a `debug` log — note this is a soft violation of the "use `logger.exception`" convention; flag for Phase 4 cleanup.) |
| 174 | `get_mood_categories()` — wraps `client.get_mood_categories` | KEEP | Returns `[]` on failure; browse page degrades gracefully. |
| 182 | `get_mood_playlists()` — wraps `client.get_mood_playlists` | KEEP | Returns `[]` on failure; same pattern. |
| 190 | `get_charts()` — wraps `client.get_charts` | KEEP | Returns `{}` on failure; charts page renders empty rather than crashing. |
| 204 | `get_new_releases()` — wraps `client.get_new_releases` | KEEP | Returns `[]` on failure; degrades gracefully. |
| 216 | `get_album()` — wraps `client.get_album` | KEEP | Returns `{}` on failure; context page renders empty state. |
| 224 | `get_artist()` — wraps `client.get_artist` | KEEP | Returns `{}` on failure; artist page renders empty state. |
| 279 | `get_playlist()` outer catch — wraps `client.get_playlist`, including the `_send_request` monkey-patch path for `order=...` sorts | KEEP | Returns `{}` on failure. Note: the `try/finally` inside the `async with self._order_lock` block correctly restores `_send_request` even if the inner `_call` raises, before bubbling to this outer catch. Worth keeping the patch-restore logic in mind during Phase 4 NARROW-ing of `_call`. |
| 300 | `get_song()` — wraps `client.get_song` | KEEP | Returns `{}` on failure; song-details lookup degrades. |
| 321 | `get_lyrics()` inner catch — timed-lyrics request failure, falls back to plain | KEEP | Deliberate fallback — `get_lyrics(... timestamps=True)` may fail for songs without LRC; the fallback to plain is the contract. Could be marginally narrowed to ytmusicapi-specific errors, but KEEP since the fallback path is a normal recovery, not bug-hiding. |
| 325 | `get_lyrics()` outer catch | KEEP | Returns `None` on any failure, including the watch-playlist lookup that supplies the lyrics browseId. UI handles `None` as "no lyrics available". |
| 353 | `get_watch_playlist()` — wraps `client.get_watch_playlist`, extracts `tracks` | KEEP | Returns `[]` on failure; queue auto-extension degrades. |
| 366 | `get_radio()` — wraps `client.get_watch_playlist(..., radio=True)` | KEEP | Returns `[]` on failure; radio start degrades. |
| 383 | `rate_song()` — mutation, wraps `client.rate_song` | **NARROW** | Returns `None` whether the rating succeeded or failed — caller (`l` keybinding, like-toggle UI) cannot tell if the server-side state actually changed. The like state may visually flip in the UI while the server stays unchanged. Should distinguish auth errors (signal to reauth) from transient errors (caller can retry / surface a toast) from unexpected exceptions (propagate as bugs). Closely related: this method should arguably also return `bool` like `add_to_library` / `unsubscribe_artist` for parity. |
| 390 | `add_playlist_items()` — mutation, wraps `client.add_playlist_items` | **NARROW** | Returns `None` whether successful or not — caller (add-to-playlist popup) shows "added" toast even on silent failure. Same NARROW rationale as `rate_song`: distinguish auth vs network vs unexpected; consider returning `bool` for parity with other mutation methods. |
| 405 | `create_playlist()` — mutation, wraps `client.create_playlist`, returns playlist ID | KEEP | Returns `""` (sentinel) on failure; caller can check `if not playlist_id`. Sentinel is consistent with the rest of the file's contract style. |
| 418 | `delete_playlist()` — mutation, wraps `client.delete_playlist` | KEEP | Returns `bool`; caller can branch on success. Standard mutation contract for this file. |
| 431 | `add_to_library()` — mutation, wraps `client.rate_playlist(..., "LIKE")` | KEEP | Returns `bool`; uses `logger.exception` (correctly) rather than `logger.debug`. Caller can branch on success. |
| 445 | `remove_album_from_library()` — mutation, wraps `client.rate_playlist(..., "INDIFFERENT")` | KEEP | Returns `bool`; same pattern as `add_to_library` (though uses `logger.debug` rather than `logger.exception` — minor inconsistency, flag for Phase 4 logging-pass). |
| 454 | `unsubscribe_artist()` — mutation, wraps `client.unsubscribe_artists` | KEEP | Returns `bool`; standard mutation contract. |
| 468 | `remove_playlist_items()` — mutation, wraps `client.remove_playlist_items` | **NARROW** | Returns `None` whether successful or not — the queue/playlist UI removes the row optimistically and the user can't tell if the server-side delete actually happened. Same NARROW rationale as `rate_song` and `add_playlist_items`; consider returning `bool` for parity. |
| 479 | `get_history()` — wraps `client.get_history` | KEEP | Returns `[]` on failure; recently-played page degrades to empty. |

**Summary for this file:** 25 KEEP, 4 NARROW, 0 PROMOTE. The four NARROWs cluster into two groups:

1. **`_call()` (line 65)** — the outer-loop catch that drives `_consecutive_api_failures`. Currently any exception (including programming errors like `AttributeError`) bumps the counter and can trigger a spurious client reinit. Phase 4 should split into expected (network/auth/ytmusicapi) and unexpected (propagate).
2. **Three mutation methods returning `None` (lines 383, 390, 468):** `rate_song`, `add_playlist_items`, `remove_playlist_items`. These swallow exceptions and return nothing, leaving callers unable to detect failure. Phase 4 should at minimum narrow the catch and ideally return `bool` for parity with the other mutation methods (`delete_playlist`, `add_to_library`, `remove_album_from_library`, `unsubscribe_artist`).

Minor logging-hygiene notes for Phase 4: `get_home` (line 167) uses `logger.debug(..., exc_info=True)` instead of `logger.exception`, and `remove_album_from_library` (line 446) uses `logger.debug` where `logger.exception` would be more consistent with `add_to_library` (line 432).

### `services/` other files (43 sites)

#### `services/auth.py` (7 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 131 | `validate()` — wraps `get_account_info()` after the network-error short-circuit on line 128 | KEEP | Network errors (`ConnectionError`, `Timeout`) already re-raise on line 128. The remaining `Exception` catch correctly covers the credentials-expired path (ytmusicapi raises a generic exception on bad cookies/auth) and returns `False` so callers branch to reauth. The two-step pattern is intentional. |
| 152 | `try_auto_refresh()` — wraps `_extract_and_save(browser)` then `validate()` | KEEP | Best-effort silent refresh on launch — must not crash startup if browser cookie extraction barfs. Returns `False` so the user is prompted to reauth interactively. |
| 227 | `_detect_browser()` — per-browser `extract_cookies_from_browser(browser)` probe | KEEP | Iterates candidate browsers; each may legitimately fail (browser not installed, locked DB, etc.). Catch + `continue` is the contract. |
| 306 | `_extract_and_save()` — outer try wrapping `extract_cookies_from_browser(browser)` import + call | KEEP | Returns `False` on any extraction failure so the caller falls back to the manual paste flow. Logs at warning so users can diagnose. |
| 329 | `_save_youtube_cookies()` — wraps `sapisid_from_cookie(cookie_str)` | **NARROW** | The only thing inside the try is a deterministic helper that should fail with one specific error type when SAPISID is missing (likely `ValueError` or `KeyError`, depending on the helper's contract). Catching `Exception` here masks bugs in `sapisid_from_cookie` itself (e.g. an `AttributeError` from a refactor) and still returns `False` — silently. Should narrow to the actual sentinel that `sapisid_from_cookie` raises on missing cookie. |
| 367 | `_save_youtube_cookies()` inner per-`authuser` probe — wraps `tempfile.mkstemp` + `YTMusic(tmp_path)` + `get_account_info()` | KEEP | Probing five `x-goog-authuser` indices to find which ones the cookie is logged into. Each probe legitimately fails for un-logged-in indices; the `try/finally` correctly cleans up `tmp_path` regardless. Soft logging-hygiene note: `logger.debug(...)` here drops `exc_info` — minor inconsistency, flag for Phase 4 sweep. |
| 490 | `_normalize_and_save_headers()` — wraps `ytmusicapi.setup(filepath=..., headers_raw=...)` for the manual-paste path | KEEP | User-visible interactive setup; surfaces the parse error as a printed message and returns `False` so the caller can re-prompt. Uses `logger.error` (not `exception`) — soft logging-hygiene note for Phase 4 (lose the traceback on a bug-class failure). |

#### `services/discord_rpc.py` (4 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 44 | `connect()` — wraps `AioPresence(_CLIENT_ID).connect()` | KEEP | Optional service. Discord not running, no IPC pipe, etc. — must degrade silently and return `False`. |
| 55 | `disconnect()` — wraps `self._rpc.close()` | KEEP | Bare `pass` on shutdown path. Silencing all close errors is fine here; nothing downstream cares. |
| 91 | `update()` — wraps `self._rpc.update(**kwargs)` per-track | KEEP | Per-track presence update; must never crash playback. Sets `_connected = False` so subsequent calls short-circuit. |
| 101 | `clear()` — wraps `self._rpc.clear()` on pause/stop | KEEP | Same contract as `update()`; degrades to `_connected = False`. |

#### `services/download.py` (1 site)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 96 | `_download_sync()` — wraps the entire yt-dlp `extract_info(... download=True)` pipeline | KEEP | Returns a `DownloadResult` dataclass with `success=False` and the error string for the UI to render. yt-dlp can raise a wide variety of errors (network, format-not-found, postprocessor failure) and the user-facing contract is "tell me what went wrong, don't crash the TUI". |

#### `services/lastfm.py` (3 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 70 | `connect()` — wraps `pylast.LastFMNetwork(...)` constructor | KEEP | Optional service; setup failure (bad creds, network down) must not crash startup. Sets `_connected = False`. |
| 99 | `now_playing()` — wraps `update_now_playing()` per-track | KEEP | Best-effort scrobble notification; per-track failures must not crash playback. |
| 140 | `check_scrobble()` — wraps `network.scrobble()` | KEEP | Same contract as `now_playing()`. Periodic scrobble call. |

#### `services/lrclib.py` (1 site)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 42 | `_fetch()` inner closure — wraps `urllib.request.urlopen(...)` + `json.loads(...)` | KEEP | Optional lyrics fallback; LRCLIB returns 404 for unknown songs, network may be down, JSON may be malformed. Returns `None` so the lyrics sidebar shows the empty state. Could be marginally narrowed to `(urllib.error.URLError, json.JSONDecodeError, OSError)` but the catch-all here is genuinely justified — this is a third-party service with a wide failure surface. |

#### `services/macos_eventtap.py` (4 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 52 | `_event_action()` — wraps `ns_event.subtype()` + `ns_event.data1()` cast | KEEP | NSEvent objects from CoreFoundation can be malformed for non-media subtypes. Returns `None` so the tap callback ignores the event. Mandatory defensive coding around PyObjC bridges. |
| 106 | `stop()` — wraps `Quartz.CGEventTapEnable(self._tap, False)` | KEEP | Lifecycle teardown; tap may already be invalid. Must not raise during shutdown. |
| 111 | `stop()` — wraps `Quartz.CFRunLoopStop(self._run_loop)` | KEEP | Same teardown contract. Run loop may have already exited. |
| 149 | `_run_tap_loop()` — wraps `Quartz.CFMachPortInvalidate(self._tap)` after the run-loop exits | KEEP | Final teardown of the Mach port; happens on the tap thread after `CFRunLoopRun()` returns. Must not raise. |

#### `services/macos_media.py` (3 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 109 | `stop()` — per-target `command.removeTarget_(target)` loop | KEEP | Lifecycle teardown for MPRemoteCommand handlers; one bad target shouldn't skip the rest. Continue-and-log is correct. |
| 115 | `stop()` — `MPNowPlayingInfoCenter.setNowPlayingInfo_(None)` | KEEP | Same teardown contract; clearing Now Playing state on shutdown must not crash. |
| 194 | `_publish_now_playing()` — wraps `setNowPlayingInfo_` + `setPlaybackState_` | KEEP | Per-track publish; PyObjC bridge into a system service. Must not crash playback if the system rejects the dict shape. |

#### `services/mpris.py` (1 site)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 285 | `start()` — wraps `MessageBus().connect()` | KEEP | Optional Linux-only service. Session bus may not exist (headless, container, broken D-Bus session) — must degrade silently with a single warning and return so the rest of the app starts normally. The file's per-method exemptions (`mpris.py` allows `N802, N803, F821, F722` for D-Bus naming) signal this file is intentionally a special-case wrapper. |

#### `services/player.py` (7 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 190 | `_init_mpv()` — wraps `instance["gapless-audio"] = "yes"` for the gapless-playback opt-in | KEEP | Setting an mpv property that may not exist on older mpv versions. Failure to enable gapless is non-fatal; player still works without it. Correct degrade. |
| 276 | `_safe_wrapper()` inside `_dispatch()` — wraps `await coro_fn(*args)` for async callbacks | KEEP | This is the safety net that prevents UI/MPRIS/Discord callback bugs from killing the player thread. Uses `logger.exception` (correct). Removing this catch would let one buggy listener crash playback for everyone. |
| 287 | `_safe_sync()` inside `_dispatch()` — wraps sync callback invocation | KEEP | Same contract as line 276 for synchronous listeners. |
| 305 | `_dispatch()` — outer catch around `loop.call_soon_threadsafe(...)` and direct sync calls | KEEP | Defensive outer net for the dispatcher itself — `call_soon_threadsafe` can raise `RuntimeError` if the loop is closed, and direct `cb(*args)` (no-loop fallback) needs the same protection as the in-loop variant. Uses `logger.exception` (correct). |
| 384 | `play()` — wraps `_play_sync(url)` + `_dispatch(TRACK_CHANGE)` | KEEP | Returns to the caller after dispatching `PlayerEvent.ERROR` (line 388). The error event is the contract — UI listens for it and surfaces "Failed to play …". Uses `logger.error` (no traceback). Soft logging-hygiene note for Phase 4 — `logger.exception` would preserve the traceback for crash reports. |
| 481 | `_try_recover()` inner — wraps `get_settings().playback.default_volume` access + `self._mpv.volume = ...` | **NARROW** | Recovery hot path. The settings object is a singleton dataclass — if `get_settings()` itself raises, we have a config-load bug, not an mpv issue. The `mpv.volume = X` assignment can legitimately fail on a freshly-reinitialized mpv (e.g. `ShutdownError` if mpv died again immediately). Should narrow to `(mpv.ShutdownError, OSError, AttributeError)` and let unexpected propagate to the outer catch on line 486 so we don't silently fall back to volume=80 because of a config bug. |
| 486 | `_try_recover()` outer — wraps `_init_mpv()` + volume restore | KEEP | The outer recovery net. If mpv re-init fails, we genuinely don't know what's wrong (libmpv crash, missing DLL, etc.) and need to return `False` so the caller surfaces "playback unavailable". Uses `logger.exception` (correct). |

#### `services/spotify_import.py` (7 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 69 | `load_spotify_creds()` — wraps `json.loads(SPOTIFY_CREDS_FILE.read_text(...))` | **NARROW** | Two specific failure modes: file unreadable (`OSError`) and malformed JSON (`json.JSONDecodeError`). Catching `Exception` masks bugs in the file-reading path itself. Trivial narrow — already the pattern used in `is_authenticated` (line 109) and `auth.py:351`. |
| 174 | `extract_spotify_tracks()` — wraps `extract_spotify_tracks_spotipy(url)` | KEEP | Intentional fallback to `spotify_scraper` if spotipy fails (creds expired, API rate-limit, etc.). The whole point of the catch is to swallow the spotipy-side error and try the alternative path. User sees a warning. |
| 244 | `_search_and_score()` — wraps `ytmusic.search(query, filter='songs', limit=5)` per Spotify track | KEEP | Per-track YTM search inside a thread pool during a bulk import. One bad track must not abort the whole import — returns empty `search_results` so the track is marked `MatchType.NONE` and the user can pick manually. Soft logging-hygiene note: no log at all here, swallows silently. Phase 4 should add at least a `logger.debug` so silent matching failures are diagnosable. |
| 335 | `import_spotify_playlist()` — wraps the top-level `extract_spotify_tracks(spotify_url)` call | KEEP | User-visible interactive command; surfaces the error to stdout with the actual `exc` text and aborts. The console output IS the user-facing contract. |
| 352 | `import_spotify_playlist()` — wraps `YTMusic(str(auth_file), user=brand_account)` constructor | KEEP | Same user-visible contract — bad auth file or bad brand account ID surfaces a printed error and aborts. |
| 412 | `import_spotify_playlist()` — wraps the manual re-search `ytmusic.search(custom_query, ...)` | KEEP | Same per-track-search degrade as line 244 but in the interactive manual-pick branch. Returns `[]` so the menu shows no candidates. |
| 470 | `import_spotify_playlist()` — wraps `ytmusic.create_playlist(...)` + `video_ids` build | KEEP | Final step — user-visible failure surfaces the actual error. Aborts the import with a printed message. |

#### `services/stream.py` (4 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 104 | `_reset_ydl()` — wraps `self._ydl.close()` during cache invalidation | KEEP | Bare `pass` on the close-and-discard path. The instance is being thrown out either way; close errors don't matter. |
| 180 | `_resolve_sync()` outer — catches anything that isn't `yt_dlp.utils.DownloadError` (handled on line 172) | KEEP | The plan flagged this as a NARROW candidate, but reading in context: line 172 already handles the expected `yt_dlp.utils.DownloadError` (network/format errors). Line 180's catch is the "everything else" net for the resolver retry loop — catches things like `urllib.error.URLError` outside yt-dlp, locale/encoding issues, mpv/yt-dlp version mismatches. Correctly logs at warning with `exc_info=True` and returns `None`. The contract is "resolver always returns `Optional[StreamInfo]`, never raises" because callers (Player, prefetch) cannot recover from a raise. Soft logging-hygiene note: `logger.warning(..., exc_info=True)` could be `logger.exception` for consistency; flag for Phase 4. |
| 272 | `resolve()` — wraps `asyncio.to_thread(_resolve_sync, video_id)` and propagates via `future.set_exception` | KEEP | This catch RE-RAISES after setting the awaiting future's exception. It's not silencing — it's a fan-out so multiple callers awaiting the same `video_id` all see the same error. Correct as written. |
| 290 | `prefetch()` — wraps `await self.resolve(video_id)` | KEEP | Background prefetch of the next track's stream URL. Must not bubble exceptions because there's no awaiter to catch them — would be unhandled task error. Logs at debug since prefetch failure is recoverable (real `resolve()` call will hit the same error visibly). |

#### `services/update_check.py` (1 site)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 74 | `_fetch_latest_pypi_version()` — outer "belt-and-braces" catch after the explicit `(URLError, OSError, JSONDecodeError, ValueError)` handler on line 72 | KEEP | Already-narrowed: the expected failure modes are caught on line 72 and return `None`. Line 74 is the explicit `# pragma: no cover` belt-and-braces net for anything else (e.g. an unexpected SSL exception type or a malformed response shape). Returns `None` so the optional update banner is silently skipped. Correct pattern. |

**Summary for services/ other (43 sites):** 40 KEEP, 3 NARROW, 0 PROMOTE. Notable findings:

- **Two new NARROW candidates not in Phase 4 plan:**
  - `auth.py:329` (`_save_youtube_cookies` SAPISID extraction) — should narrow to whatever `sapisid_from_cookie` raises on missing cookie. Catching `Exception` here masks refactor bugs in the helper. Small fix; bundle into a Phase 4 "trivially-narrowable single-call try blocks" task.
  - `spotify_import.py:69` (`load_spotify_creds`) — should narrow to `(OSError, json.JSONDecodeError)` to match the existing pattern in `auth.py:109`/`auth.py:351`. Pure consistency fix.
- **One NARROW candidate in `player.py`:**
  - `player.py:481` (`_try_recover` volume restore inner catch) — should narrow to `(mpv.ShutdownError, OSError, AttributeError)`. The `get_settings()` lookup inside the try is a config-load path that has no business being silently swallowed inside an mpv-recovery handler. Small refactor; pairs naturally with the broader Player crash-recovery tightening.
- **Optional services confirmed all KEEP:** `discord_rpc.py`, `lastfm.py`, `mpris.py`, `macos_eventtap.py`, `macos_media.py`, `update_check.py`, `lrclib.py`, `download.py`. Every site is genuinely "this feature must not crash the player". The PyObjC/D-Bus boundaries especially benefit from broad catches because the bridges raise wide exception hierarchies.
- **Logging-hygiene drift to roll into Phase 4 (Task 4.4 scope expansion):**
  - `auth.py:368` — `logger.debug(...)` drops `exc_info`, leaving the traceback unrecorded.
  - `auth.py:491` — `logger.error(...)` without `exc_info`; should be `logger.exception` for parser-failure diagnostics.
  - `spotify_import.py:244` (`_search_and_score`) — silent swallow with no log at all. Add `logger.debug(..., exc_info=True)` so users importing playlists with many `MatchType.NONE` rows have a way to diagnose.
  - `stream.py:180` — `logger.warning(..., exc_info=True)` should be `logger.exception` for consistency with the rest of the codebase.
  - `player.py:387` — `logger.error("Failed to play %s: %s", ...)` drops the traceback that crash-report users would want; consider `logger.exception` here too.

### `app/_playback.py` (27 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 78 | `play_track()` — wraps `query_one("#playback-bar", PlaybackBar)` + `update_track()` + `update_playback_state()` for the immediate "show track info before stream resolves" UI update | KEEP | The playback bar may not be mounted yet during early startup; `query_one` raises `NoMatches`. Falling through to stream resolution without the bar update is the correct degrade. Logs at debug. Soft logging-hygiene note: `logger.debug(..., exc_info=True)` should be `logger.exception` per CLAUDE.md. |
| 86 | `play_track()` — wraps `await self.cache.get(video_id)` for local audio cache lookup | KEEP | Best-effort cache hit check; falls back to yt-dlp resolution on any error. The cache is a `CacheManager` over SQLite + filesystem — a wide failure surface (DB lock, disk write error during stale-entry cleanup). Note: `cache.get` handles "missing file" internally by calling `remove()` and returning `None`, so missing-file doesn't propagate. Sets `cache_hit = None` so the resolver path runs. Same logging-hygiene note. |
| 111 | `play_track()` — wraps `await self.stream_resolver.resolve(video_id)` | KEEP | `resolve()` already swallows yt-dlp errors and returns `None` (see `stream.py:180`). This catch is belt-and-braces against the resolver itself raising (e.g. asyncio cancellation propagating through `to_thread`). Sets `stream_info = None` to trigger the auto-advance branch. Same logging-hygiene note. |
| 153 | `play_track()` — wraps `await self.player.play(stream_info.url, track)` | KEEP | mpv `play()` can raise on a wide variety of errors (libmpv shutdown mid-init, invalid URL, codec issues). The error path is the contract: clear debounce, increment failure counter, auto-advance or reset yt-dlp. Same logging-hygiene note (`logger.debug(..., exc_info=True)` should be `logger.exception`). |
| 187 | `play_track()` — wraps `await self.player.seek_absolute(self._pending_resume_position)` for resume-on-launch position seek | KEEP | Best-effort seek to the saved position. If seek fails (e.g. mpv refused the seek because the stream didn't fully load yet), playback continues from track start — non-fatal. Same logging-hygiene note. |
| 295 | `_fetch_and_play_radio()` — wraps `ytmusic.get_radio()` + queue mutation + `play_track()` | KEEP | `get_radio()` is itself a service-layer KEEP that returns `[]` on API failure, so this catch covers downstream failures (queue mutation, `play_track`). Falls through to the "no more suggestions" notify. Uses `logger.exception` (correct). |
| 324 | `_on_track_end()` — outer catch around history logging and `_play_next()` | KEEP | Outer net for the track-end coroutine; `_advancing` flag must be reset in `finally` regardless of failure. Lets the queue keep advancing on next end-file event even if this one threw. Soft logging-hygiene note: `logger.debug(..., exc_info=True)` should be `logger.exception` for crash-report visibility. |
| 338 | `_poll_position()` — wraps `player.position` + `player.duration` reads + `bar.update_position()` for the per-tick UI update | KEEP | Per-tick timer callback — must never raise or it kills the timer. `position`/`duration` reads can raise during mpv state transitions. Same logging-hygiene note. |
| 344 | `_poll_position()` — wraps `mpris.update_position(...)` per-tick | KEEP | Per-tick MPRIS broadcast; D-Bus is the wide-failure-surface optional service. Uses `logger.exception` (correct). |
| 350 | `_poll_position()` — wraps `mac_media.update_position(...)` per-tick | KEEP | Per-tick macOS Now Playing broadcast; PyObjC bridge to MediaPlayer framework. Uses `logger.exception` (correct). |
| 361 | `_poll_position()` — wraps `run_worker(lastfm.check_scrobble(...))` per-tick | KEEP | Per-tick scrobble-threshold check kicked off as a worker. Worker scheduling itself can fail (e.g. shutdown race). Uses `logger.exception` (correct). |
| 373 | `_on_track_change()` — wraps `bar.update_track()` + `bar.update_playback_state()` on track-change event | KEEP | Same pattern as line 78 — bar may be unavailable during early track-change events. Soft logging-hygiene note. |
| 380 | `_on_track_change()` — wraps `bar.update_like_status()` on track-change | KEEP | Same pattern; like-status update is non-critical and the bar may not be ready. Same logging-hygiene note. |
| 387 | `_on_track_change()` — wraps `header.set_lyrics_dimmed(False)` for un-dimming the lyrics toggle | **NARROW** | The expected failure here is `query_one("#app-header")` raising `textual.css.query.NoMatches` if the header isn't mounted (early startup, header not in compose tree). Catching `Exception` and silently `pass`-ing with NO log at all hides any real bug in `set_lyrics_dimmed` (e.g. a refactor breaks the method). Should narrow to `NoMatches` and at minimum add a debug log. Trivial fix for Phase 4 (single-call try block + drop-the-log offender). |
| 397 | `_on_track_change()` — wraps `_get_current_page()` + `page.query(TrackTable)` + `table.set_playing()` for playing-indicator update | KEEP | Page lookup can fail during navigation transitions; `query(TrackTable)` returns iterator that may yield stale widgets being torn down. Per-track UI update must not crash playback. Soft logging-hygiene note. |
| 411 | `_on_track_change()` — wraps the notify-on-track-change block (settings read + `fmt.format(...)` + `self.notify(...)`) | KEEP | The inner `(KeyError, ValueError)` already handles bad format strings (line 408). This outer catch is for the surrounding settings-read + notify path, which can fail if settings is being reloaded or the notification system is in a weird state. Soft logging-hygiene note. |
| 417 | `_on_track_change()` — wraps `_prefetch_next_track()` | KEEP | Prefetch is best-effort optimization; failure has no user-visible impact. Soft logging-hygiene note. |
| 443 | `_on_volume_change()` — wraps `bar.update_volume(volume)` on volume-event | KEEP | Same bar-not-mounted pattern as line 78. mpv volume changes can fire before UI is ready (e.g. during initial volume restore). Soft logging-hygiene note. |
| 451 | `_on_pause_change()` — wraps `bar.update_playback_state()` on pause-event | KEEP | Same bar-not-mounted pattern. Soft logging-hygiene note. |
| 461 | `_on_pause_change()` — wraps `call_later(...)` scheduling for MPRIS playback-status broadcast | KEEP | `call_later` can raise `RuntimeError` if the app is shutting down. Per-event MPRIS broadcast must not crash on shutdown race. Uses `logger.exception` (correct). |
| 471 | `_on_pause_change()` — wraps `call_later(...)` scheduling for macOS Now Playing playback-status broadcast | KEEP | Same shutdown-race contract as line 461. Uses `logger.exception` (correct). |
| 493 | `_on_pause_change()` — wraps `call_later(...)` scheduling for Discord RPC clear/update | KEEP | Same contract; Discord RPC is the optional-service KEEP pattern. Uses `logger.exception` (correct). |
| 511 | `_log_current_listen()` — wraps `await self.history.log_play(...)` mutation | KEEP | History write to SQLite via aiosqlite. Failure here is non-fatal — playback must continue even if the play log can't be written (DB locked, disk full, schema mismatch). Uses `logger.exception` (correct). Note: this is a mutation that returns `None`, but unlike the ytmusic.py mutation NARROWs there's no caller that needs to branch on success — the listen log is fire-and-forget. |
| 531 | `_log_listen_for()` — wraps `await self.history.log_play(...)` mutation for explicit-track variant called from `_on_track_end` | KEEP | Same contract as line 511. Same fire-and-forget pattern. Uses `logger.exception` (correct). |
| 558 | `_toggle_like_current()` — wraps `await self.ytmusic.rate_song(video_id, new_status)` for the `l` keybinding | KEEP at this layer | The underlying `ytmusic.rate_song` is itself flagged NARROW in Task 1.2 (line 383) — once that NARROWs and returns `bool`, the call here can be tightened to branch on the result. At this layer the catch correctly notifies the user and returns without flipping `track["likeStatus"]`. Uses `logger.exception` (correct). Cross-reference: Phase 4.3 will cascade here. |
| 574 | `_toggle_like_current()` — wraps `bar.update_like_status(new_status)` to push the new heart state to the playback bar | KEEP | Same bar-not-mounted pattern as line 78. The `track["likeStatus"]` was already updated, so the in-memory state is correct even if the UI couldn't be refreshed. Soft logging-hygiene note. |
| 601 | `_download_track()` — wraps `await self.cache.put_file(video_id, result.file_path, fmt)` to index a downloaded file in the audio cache | **NARROW** | The expected failure modes are `CacheError` (the public exception `cache.put_file` raises after wrapping `OSError` internally per `services/cache.py:142-144`) and `aiosqlite`/SQLite errors (`sqlite3.Error`). Catching `Exception` here silently hides bugs in `put_file` itself (e.g. a refactor breaks the signature) — the user sees "Downloaded: X" success but the file never gets indexed. Should narrow to `(CacheError, sqlite3.Error)` and at minimum upgrade to `logger.exception` so silently-unindexed downloads are diagnosable. |

**Summary for app/_playback.py (27 sites):** 25 KEEP, 2 NARROW, 0 PROMOTE. Notable findings:

- **Two NARROW candidates not in current Phase 4 plan:**
  - **Line 387** (`_on_track_change` — header un-dim): single-call try block with the obvious expected exception type (`textual.css.query.NoMatches`) and a silent `pass` with NO log. Fits cleanly into Phase 4.5 (trivial single-call try blocks). Worst offender of the silent-swallow pattern in this file.
  - **Line 601** (`_download_track` — cache indexing of completed download): swallows `OSError`/`sqlite3.Error` silently, breaking the contract that successful downloads are findable in the cache. User sees "Downloaded: X" but a re-play hits yt-dlp instead of the local file. Bundle into Phase 4.5 or a small new "download-pipeline reliability" task. The download init/UI path itself is not broken, but the post-download indexing step's silent-failure is genuinely user-visible (silently degraded cache hit rate).
- **Indirect cascade with `services/ytmusic.py` line 383 (rate_song NARROW):**
  - Line 558 (`_toggle_like_current`) is the primary call site for `rate_song`. When Phase 4.3 narrows `rate_song` and switches it to return `bool`, the catch here can be tightened to a per-error-type branch (e.g. auth error → "Sign in again", network error → "Check connection", success → flip the heart). Currently the broad catch + notify shows the same "Couldn't update like state" message for every failure mode.
- **Logging-hygiene drift (Phase 4.4 sweep candidates):** 16 of the 27 sites use `logger.debug(..., exc_info=True)` rather than `logger.exception`, against CLAUDE.md guidance ("For caught exceptions you want to surface in bug reports, use `logger.exception` — *not* `logger.debug(..., exc_info=True)`, which silently routes to debug level"). Lines: 78, 86, 111, 153, 187, 324, 338, 373, 380, 397, 411, 417, 443, 451, 574, 601 (line 601 is also the NARROW row above — its `logger.debug` upgrade is part of the NARROW fix, not a separate sweep item). The `logger.exception` sites (295, 344, 350, 361, 461, 471, 493, 511, 531, 558) are correctly leveled and serve as the in-file template for the sweep. Line 387 is the worst offender — silent `pass` with no log at all.
- **All optional-service fan-out sites confirmed KEEP:** MPRIS (344, 461), macOS Now Playing (350, 471), Discord RPC (493), Last.fm (361). Each follows the pattern from Task 1.2/1.3 — independent subscriber failure must not crash playback. The `logger.exception` usage on these sites is already correct.

### `app/` other files (35 sites)

#### `app/_app.py` (6 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 86 | `_load_theme_toml()` — wraps `path.stat()` + `open(path, "rb")` + `tomllib.load(f)` for `~/.config/ytm-player/theme.toml` | KEEP | Optional user theme override; missing file, malformed TOML, or unreadable file should silently return `{}` so the default theme applies. Bare `pass`-equivalent (`return {}`) is the contract — theme load must never crash startup. Could be cleanly narrowed to `(OSError, tomllib.TOMLDecodeError)` (the complete failure surface — `stat`/`open` raise `OSError`/`FileNotFoundError`-subclass, `tomllib.load` raises `TOMLDecodeError`). Soft logging-hygiene note: no log at all here — Phase 4 sweep candidate (add `logger.debug(..., exc_info=True)` so a malformed TOML is at least diagnosable). |
| 347 | `_apply_toml_theme()` — wraps the full `ThemeColors(...)` construction + `_apply_toml_overrides()` + `set_theme()` + reactive assignment chain | KEEP | Theme application from user TOML; failure must fall back to the default theme silently. `pass` on failure is correct. Same logging-hygiene note as line 86 — silent swallow on a cold-startup path. Phase 4.4 sweep should add at minimum a debug log. |
| 419 | `on_mount()` — wraps `YTMusicService(...)` + `Player()` + loop bind + `StreamResolver(...)` + `HistoryManager.init()` + `CacheManager.init()` block | KEEP | Outer service-init net. Logs with `logger.exception` (correct), notifies the user with the actual error string, and schedules `self.exit()` after 2 s. Failure here is genuinely fatal (no DB, no cache, no API) — exiting cleanly is the right contract, broad catch is justified because we don't know which service raised. |
| 493 | `on_mount()` — wraps `query_one("#app-header", HeaderBar)` + `set_lyrics_dimmed(True)` for the initial dim state | **NARROW** | Two-line query+act try block, identical pattern to `_playback.py:387` (already flagged in Task 1.4). Expected failure is `textual.css.query.NoMatches` if the header isn't mounted yet during early `on_mount`. Silent `pass` with NO log hides any real bug in `set_lyrics_dimmed` (e.g. a refactor breaks the method). Should narrow to `NoMatches` and add at minimum a debug log. Bundle into Phase 4.5 (trivial single-call narrows). |
| 500 | `on_mount()` — wraps `query_one("#playlist-sidebar", PlaylistSidebar).ensure_loaded()` for initial sidebar data load | KEEP | Sidebar data load failure must not crash startup; logs at debug with `exc_info=True`. Soft logging-hygiene note: `logger.debug(..., exc_info=True)` should be `logger.exception` per CLAUDE.md (Phase 4.4 sweep). |
| 570 | `_start_update_check._run()` — wraps `asyncio.to_thread(check_for_update, __version__, UPDATE_CHECK_CACHE)` for the optional update-check toast | KEEP | Update check is best-effort. The underlying `check_for_update` already swallows `(URLError, OSError, JSONDecodeError, ValueError)` and returns `None` (see `update_check.py:74` audit). This catch is the worker-side belt-and-braces against any async/scheduling failure. Soft logging-hygiene note: `logger.debug(..., exc_info=True)` should be `logger.exception` (Phase 4.4 sweep). |

#### `app/_ipc.py` (2 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 102 | `_handle_ipc_command()` outer catch — wraps the entire `match command` dispatch covering `play`/`pause`/`next`/`prev`/`seek`/`now`/`status`/`queue`/`queue_add`/`queue_clear`/`like`/`dislike`/`unlike` | KEEP | IPC is best-effort over Unix-socket / TCP-localhost. Returns `{"ok": False, "error": str(exc)}` so the CLI subcommand surfaces the actual error to the user. Uses `logger.exception` (correct). The contract is "every IPC command always returns a dict, never raises across the socket boundary" — exactly what this catch enforces. |
| 218 | `_ipc_queue_add()` — wraps single `await self.ytmusic.get_watch_playlist(video_id)` call | **NARROW** | Single-call try block. `get_watch_playlist` is itself a service-layer KEEP that returns `[]` on API failure (see `ytmusic.py:353`), so this catch is for the rare case where the service-layer broad-catch fails to neutralise something (e.g. the call itself never reached the wrapper because of a programming error in the IPC path). The downstream behaviour — returning `{"ok": False, "error": f"failed to resolve track: {exc}"}` without logging — silently drops the traceback. Should narrow once `ytmusic._call()` is narrowed in Phase 4.1, and at minimum add a `logger.exception` so failed `queue_add` IPC calls are diagnosable from the log file. |

#### `app/_keys.py` (1 site)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 189 | `_handle_action()` — `Action.TOGGLE_TRANSLITERATION` branch wraps single `query_one("#lyrics-sidebar", LyricsSidebar).toggle_transliteration()` call | **NARROW** | Single-call try block, identical pattern to `_app.py:493` and `_playback.py:387`. Expected failure is `textual.css.query.NoMatches` if the lyrics sidebar isn't mounted (early startup, sidebar unmounted). Silent `pass` with NO log hides any real bug in `toggle_transliteration` (e.g. attribute typo after a refactor). Should narrow to `NoMatches` and add a debug log. Bundle into Phase 4.5 (trivial single-call narrows). |

#### `app/_navigation.py` (2 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 142 | `navigate_to()` — wraps `query_one("#app-footer", FooterBar).set_active_page(page_name)` for the footer active-page indicator | KEEP | Bar/footer-not-mounted pattern (same as `_playback.py:373` etc.); footer may not be in the compose tree on the very first navigation. Logs at debug with `exc_info=True`. Soft logging-hygiene note: `logger.debug(..., exc_info=True)` should be `logger.exception` (Phase 4.4 sweep). |
| 200 | `_get_current_page()` — wraps `query_one("#main-content", Container)` + `list(container.children)` + cast | KEEP | Returns `None` so callers branch to "no current page". Container may not exist during startup or after teardown. Pyright-friendly Protocol cast (`PageWidget`) is intentionally inside the try. Soft logging-hygiene note: `logger.debug(..., exc_info=True)` should be `logger.exception` (Phase 4.4 sweep). |

#### `app/_session.py` (8 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 29 | `_restore_session_state()` — wraps `SESSION_STATE_FILE.read_text(encoding="utf-8")` + `json.loads(...)` for the session JSON load | KEEP | Session restore must never crash startup — corrupted / missing / unreadable session.json falls back to an empty dict and the schema-version check on line 34 normalises the rest. Logs at debug with `exc_info=True`. Could be narrowed to `(OSError, json.JSONDecodeError)` but the read-side broad catch is intentional — any reason we can't read the previous session, we want to start fresh. Soft logging-hygiene note: `logger.debug(..., exc_info=True)` should be `logger.exception` (Phase 4.4 sweep). |
| 76 | `_restore_session_state()` — wraps `query_one("#playback-bar", PlaybackBar).update_volume/repeat/shuffle` triple-call after restore | KEEP | Bar-not-mounted pattern; restore runs from `on_mount` after compose, but the bar may still be in transitional state. Logs at debug. Same Phase 4.4 logging-hygiene drift (debug + `exc_info=True` instead of `logger.exception`). |
| 93 | `_restore_session_state()` — wraps single `self.theme = saved_theme` reactive assignment | **NARROW** | Single-line try block on a Textual reactive setter. Expected failure mode is the saved theme name no longer existing (e.g. user renamed/removed a custom theme between sessions) — that should raise a specific Textual error type, not the universe of exceptions. Silent `pass` with NO log hides any real bug in the reactive setter (e.g. a Textual upgrade changes the contract). Should narrow to the actual Textual exception and add a debug log. Bundle into Phase 4.5. |
| 102 | `_restore_session_state()` — wraps single `query_one("#lyrics-sidebar", LyricsSidebar)._transliteration_enabled = state[...]` assignment | **NARROW** | Single-call try block. Expected failure is `textual.css.query.NoMatches` if the lyrics sidebar isn't mounted yet during early `on_mount`. Silent `pass` with NO log; same pattern as `_app.py:493` and `_keys.py:189`. Should narrow to `NoMatches` and add a debug log. Bundle into Phase 4.5. |
| 145 | `_restore_session_state()` — wraps the resume-restore bar update block (`query_one` + `update_track` + `update_playback_state` + `update_position`) | KEEP | Bar-not-mounted pattern again. Logs at debug. Same Phase 4.4 logging-hygiene drift. |
| 159 | `_save_session_state()` — wraps single `volume = self.player.volume` property read | **NARROW** | Single-line try block on a single attribute access. `Player.volume` (player.py:363-369) already catches `mpv.ShutdownError` internally and returns 0, so the outer broad-except here can only fire on something more unexpected — `AttributeError` on a half-constructed/unmounted player, or an internal mpv-bridge bug that escapes the property. Falls back to `volume = 80` (the default). Silent debug log is fine, but the broad catch is wider than needed — should narrow to `AttributeError` (and any specific bridge exception that escapes `Player.volume`). Bundle into Phase 4.5. |
| 211 | `_save_session_state()` — outer catch wrapping `mkdir(...)` + `write_text(...)` + `secure_chmod(...)` + `os.replace(...)` of session.json | **NARROW** | **Mutation write path.** This is the primary site Task 1.5 was specifically asked to scrutinise. Failure here silently loses the user's queue, current track, and resume position with no user-visible signal — only a `logger.warning(..., exc_info=True)` in the log file the user has to know to check. Expected failure modes: `OSError` / `PermissionError` (disk full, permission denied, EROFS), `TypeError` from `json.dumps` if a track dict somehow became unserialisable. Catching `Exception` here also masks bugs in the inner `secure_chmod` / `os.replace` paths. Two-step fix in Phase 4: (a) narrow to `(OSError, TypeError)`; (b) on caught failure, also `self.notify("Could not save session state", severity="warning", timeout=5)` so the user knows their resume target is stale. Currently the silent-on-failure write contract is the worst broad-except offender in the audited app/ tier. |
| 218 | `_get_transliteration_state()` — wraps single `query_one("#lyrics-sidebar", LyricsSidebar)._transliteration_enabled` read | KEEP | Returns `False` if the sidebar isn't mounted (called during `_save_session_state`, which can fire at unmount when widgets are torn down). Returning the safe default is the contract — could be marginally narrowed to `NoMatches` but the `False` fallback is genuinely the right behaviour for any failure. |

#### `app/_sidebar.py` (13 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 42 | `_apply_playlist_sidebar()` — wraps `query_one("#playlist-sidebar", PlaylistSidebar)` + `add/remove_class("hidden")` | KEEP | Sidebar may not exist during early startup or transient teardown. Logs at debug. Same Phase 4.4 logging-hygiene drift (`debug` + `exc_info=True`). |
| 47 | `_apply_playlist_sidebar()` — wraps `query_one("#app-header", HeaderBar).set_playlist_state(visible)` to sync header indicator | **NARROW** | Single-call try block. Expected failure is `textual.css.query.NoMatches`. Silent `pass` with NO log; same pattern as `_app.py:493`, `_keys.py:189`, etc. Should narrow to `NoMatches` and add a debug log. Bundle into Phase 4.5. |
| 59 | `_apply_lyrics_sidebar()` — wraps `query_one("#lyrics-sidebar", LyricsSidebar)` + class toggle + `activate()` | KEEP | Same sidebar-not-mounted pattern; logs at debug. Phase 4.4 sweep candidate. |
| 69 | `_apply_lyrics_sidebar()` — wraps `self.screen.add/remove_class("lyrics-open")` to drive ToastRack offset CSS | KEEP | Screen may not be available outside the active app context. Logs at debug. Phase 4.4 sweep candidate. |
| 74 | `_apply_lyrics_sidebar()` — wraps `query_one("#app-header", HeaderBar).set_lyrics_state(visible)` | **NARROW** | Single-call try block; identical pattern to line 47. Silent `pass` with NO log. NARROW to `NoMatches` + add debug log. Phase 4.5. |
| 84 | `_toggle_album_art()` — wraps `query_one("#pb-art", AlbumArt)` + `art.display = not art.display` | KEEP | Album art may not be mounted (early startup, or art widget disabled by config). Logs at debug. Phase 4.4 sweep candidate. |
| 141 | `on_playlist_sidebar_playlist_double_clicked()` — wraps `get_playlist(...)` + queue clear/add/jump + `play_track()` + `run_worker(_fetch_remaining_for_queue(...))` | KEEP | The `get_playlist` call inside is itself a service-layer KEEP returning `{}` on failure, so this outer catch is for downstream — queue mutations failing, `play_track` raising, or worker scheduling failing. Logs with `logger.exception` (correct) and notifies the user — the user-visible contract is intact. |
| 158 | `_fetch_remaining_for_queue()` — wraps `get_playlist_remaining(...)` + queue append in a background worker | KEEP | Background fetch must not crash the worker. Append failures are non-fatal (user already has the first batch playing). Logs at debug. Same Phase 4.4 logging-hygiene drift. |
| 176 | `_add_playlist_to_queue()` — wraps `get_playlist(...)` + queue add + notify | KEEP | Logs at debug + `self.notify("Failed to add to queue", severity="error")`. User sees the failure in the toast. Phase 4.4 sweep candidate. |
| 231 | `_open_playlist_context_menu._handle_action()` — `copy_link` branch wraps single `query_one("#playlist-sidebar", PlaylistSidebar).copy_item_link(item)` call | **NARROW** | Single-call try block. Silent `pass` with NO log. Same pattern as the other "missing sidebar widget" silent swallows. NARROW to `NoMatches` + add debug log. Phase 4.5. |
| 259 | `_create_sidebar_playlist()` — outer catch wrapping `create_playlist(...)` + sidebar refresh + notify | KEEP | Mutation flow with user-visible feedback. The underlying `create_playlist` already returns `""` (sentinel) on failure (see `ytmusic.py:405`), so the catch here is for downstream sidebar refresh failures. Logs with `logger.exception` (correct) and notifies the user. |
| 278 | `_delete_sidebar_playlist()` — inner catch wrapping single `delete_playlist(playlist_id)` call, falling back to `remove_album_from_library` | KEEP | **Intentional fallback contract.** `delete_playlist` raises if the user doesn't own the playlist (server returns an error); the fall-back path on line 281 then calls `remove_album_from_library` to handle the "not your playlist, just remove from library" case. The silent `pass` is correct — the failure is the signal to try the alternative. Could be marginally narrowed to whatever ytmusicapi raises for "not the owner", but the broad catch is the simpler and more robust expression of the contract. |
| 288 | `_delete_sidebar_playlist()` — outer catch wrapping the entire delete-or-remove flow | KEEP | User-visible mutation; logs with `logger.exception` (correct) and notifies the user. The outer net for any unexpected failure beyond the inner `delete_playlist`/`remove_album_from_library` pair. |

#### `app/_track_actions.py` (3 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 136 | `_open_actions_for_track._rate()` — wraps `await ytmusic.rate_song(vid, r)` + the success-side `track["likeStatus"] = r` + `self.notify(lbl, timeout=2)` triple, for the actions popup's `toggle_like` branch | KEEP at this layer | Cascade with `services/ytmusic.py:383` (`rate_song`, already flagged NARROW in Task 1.2 / Phase 4.3). Once `rate_song` returns `bool` and propagates expected error types, this catch can be tightened to branch per-error-type. Currently `rate_song` always returns `None` even on failure, so the outer catch is the only signal a failure happened — broad-catch + user-visible notify is the correct downstream contract until Phase 4.3 lands. The `try` actually spans the rate call + likeStatus mutation + notify, so a notify failure or dict mutation bug would also fire this catch; tracking that in Phase 4.3 is worthwhile. Soft logging-hygiene note: NO `logger.exception` here at all — silent except for the user-visible toast. Phase 4.3 should add a `logger.exception` so the underlying error is in the log too. |
| 160 | `_refresh_queue_page()` — wraps `query_one(QueuePage)` + `_refresh_queue()` for the optional refresh after add-to-queue / play-next | **NARROW** | Single-call-pair try block. Expected failure is `textual.css.query.NoMatches` when the queue page isn't currently mounted (refresh is best-effort — only useful when the queue page is the active page). Silent `pass` with NO log; classic pattern. NARROW to `NoMatches` and add a debug log. Bundle into Phase 4.5. |
| 182 | `_start_radio_for()` — wraps `normalize_tracks(await self.ytmusic.get_radio(video_id))` | KEEP | Radio start is user-visible; logs with `logger.exception` (correct) and notifies the user with `severity="error"`. The underlying `get_radio` is a service-layer KEEP (returns `[]`), so this outer catch is for downstream — `normalize_tracks` raising on a malformed response, or any other unexpected failure. Correct user-facing contract. |

**Summary for app/ other (35 sites):** 24 KEEP, 11 NARROW, 0 PROMOTE. Notable findings:

- **One brand-new high-priority NARROW candidate not yet in any Phase 4 task — and it's a mutation/write path** (matches the pattern Task 1.5 was specifically asked to look for):
  - **`_session.py:211`** (`_save_session_state` outer write catch). Silent loss of the user's queue / current-track / resume position on failure to write `session.json` — the user has no signal anything went wrong unless they tail the log file. Two-step fix in Phase 4: narrow to `(OSError, TypeError)` and add a `self.notify("Could not save session state", severity="warning", timeout=5)` so users know their resume target is stale. Recommend a new dedicated Phase 4 task ("Phase 4.6: session-write failure visibility") rather than rolling into 4.5, because it's both a NARROW *and* a UX-contract change.
- **Ten new "trivial single-call NARROW" candidates that fold into Phase 4.5 (currently `auth.py:329`, `spotify_import.py:69`, `player.py:481`, `_playback.py:387`, `_playback.py:601`):**
  - `_app.py:493` (header dim during `on_mount`)
  - `_ipc.py:218` (single `get_watch_playlist` call in `_ipc_queue_add`)
  - `_keys.py:189` (TOGGLE_TRANSLITERATION single call)
  - `_session.py:93` (single `self.theme = ...` reactive assignment)
  - `_session.py:102` (single `_transliteration_enabled` assignment)
  - `_session.py:159` (single `self.player.volume` read)
  - `_sidebar.py:47` (header `set_playlist_state` single call)
  - `_sidebar.py:74` (header `set_lyrics_state` single call)
  - `_sidebar.py:231` (sidebar `copy_item_link` single call)
  - `_track_actions.py:160` (`_refresh_queue_page` single-call pair)
  - All ten follow the same shape: single-call/single-line try block, expected exception type is obvious (`NoMatches`, an `AttributeError` on a half-constructed player, or a Textual reactive error), silent `pass` with NO log, fix is a 2-line edit. (The eleventh NARROW — `_session.py:211` — is the multi-step write path called out in the bullet above; not this trivial-narrow group.)
- **One cascade observation cross-referencing Phase 4.3:**
  - `_track_actions.py:136` is the secondary call site for `ytmusic.rate_song` (the primary is `_playback.py:558`). Once Phase 4.3 narrows `rate_song` and switches to `bool`, both call sites should be tightened together — the current `_track_actions.py:136` site doesn't even log the exception, only shows a user toast. Phase 4.3 should explicitly cascade here.
- **Logging-hygiene drift (Phase 4.4 sweep candidates):** 13 sites use `logger.debug(..., exc_info=True)` instead of `logger.exception`, against CLAUDE.md guidance. Lines: `_app.py:501` (`_app.py` line 500's catch logs at 501), `_app.py:571`, `_navigation.py:143`, `_navigation.py:201`, `_session.py:30`, `_session.py:77` (multi-line debug call), `_session.py:146`, `_sidebar.py:43`, `_sidebar.py:60`, `_sidebar.py:70`, `_sidebar.py:85`, `_sidebar.py:159`, `_sidebar.py:177`. Plus 8 silent-pass-no-log sites that are also in the 11 NARROW candidates above (`_app.py:493`, `_keys.py:189`, `_session.py:93`, `_session.py:102`, `_sidebar.py:47`, `_sidebar.py:74`, `_sidebar.py:231`, `_track_actions.py:160`) — those get their log added as part of the NARROW fix, not the sweep.
- **Two log-only-no-traceback offenders:**
  - `_app.py:86` and `_app.py:347` — silent swallow with NO log at all on the theme TOML load + apply paths. Phase 4.4 should add a `logger.debug(..., exc_info=True)` so a malformed user theme TOML is at least diagnosable.
- **All multi-call outer-catch sites confirmed KEEP:** `_app.py:419` (service init), `_ipc.py:102` (IPC dispatch outer), `_sidebar.py:141`/`259`/`288` (user-visible mutations), `_track_actions.py:182` (radio start). Each follows the established pattern — `logger.exception` + `self.notify(...)` for the user-visible cases, exit-with-toast for the genuinely fatal init case.

### `ui/pages/` (73 sites)

#### `ui/pages/help.py` (1 site)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 265 | `watch_filter_visible()` — wraps `query_one("#help-filter-input", Input)` + `display = visible` + `focus()` / `value = ""` + `self.filter_text = ""` chain on the keybinding-help filter input | **NARROW** | Single-widget try block — same pattern as `_app.py:493`, `_keys.py:189`, `_session.py:102`, `_sidebar.py:47/74/231`, `_track_actions.py:160` (all flagged in Task 1.5 as Phase 4.5 candidates). Expected failure is `textual.css.query.NoMatches` if the filter input isn't mounted yet (reactive watcher can fire before `compose()` finishes). Currently `logger.debug(..., exc_info=True)` — under CLAUDE.md guidance this should be `logger.exception` once the broad catch is narrowed. Bundle into Phase 4.5. |

#### `ui/pages/recently_played.py` (2 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 107 | `_load_history()` — wraps `await history.get_recently_played(limit=100)` | KEEP | Single-call to a `HistoryManager` method, but the failure-handling contract is correct — `logger.exception` (no logging-drift to fix) plus a fall-through that sets `self._tracks = []` so the page renders the empty state. SQLite/aiosqlite has a wide failure surface (DB lock, schema mismatch, file unreadable) and the user must see "no history" rather than crash. |
| 153 | `get_nav_state()` — wraps single `query_one("#recent-table", DataTable)` + `cursor_row` read | **NARROW** | Single-call try block on a `DataTable` access. Expected failure is `NoMatches`. Silent `pass` with NO log; same pattern as `library.py:136`, `liked_songs.py:233`, `search.py:490`. Bundle into Phase 4.5. |

#### `ui/pages/library.py` (7 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 136 | `get_nav_state()` — wraps single `query_one("#library-tracks", TrackTable)` + `cursor_row` read | **NARROW** | Single-call try block (same shape as `recently_played.py:153`, `liked_songs.py:233`, `search.py:490`). Expected failure is `NoMatches`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 207 | `load_playlist()` — outer catch wrapping `get_playlist(...)` + multi-step UI build (header mount/labels/track-table load + cursor restore + `run_worker` for remaining tracks) | KEEP | Multi-call user-visible path. Logs with `logger.exception` (correct) and shows "Failed to load playlist" empty-state. The contract is "user sees an error message, page does not crash". Correct. |
| 232 | `_fetch_remaining()` — wraps `query_one("#library-tracks", TrackTable)` + `append_tracks(tracks)` + `_subtitle_label.update(...)` for background batch append | KEEP | Multi-call background-worker append path; one widget unmounted mid-fetch must not crash the worker. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate (should be `logger.exception` per CLAUDE.md). |
| 277 | `on_track_table_filter_requested()` — wraps `query_one("#track-filter", Input)` + `value = ""` + `add_class("visible")` + `focus()` chain | **NARROW** | Single-widget cluster (one `query_one`, three method calls on the same widget — same shape as `help.py:265`, `_session.py:76`). Expected failure is `NoMatches`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 285 | `on_track_table_filter_closed()` — wraps `query_one("#track-filter", Input)` + `remove_class("visible")` + nested `query_one("#library-tracks", TrackTable).focus()` | **NARROW** | Two-`query_one`-chained try block but still single-widget-per-step; both `query_one` failures are `NoMatches`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 311 | `on_key()` Escape handler — wraps single `query_one("#track-filter", Input)` + `has_class` + nested `query_one("#library-tracks", TrackTable).clear_filter()` | **NARROW** | Same pattern as line 285 — two `query_one` calls in service of one keybinding action; expected exception is `NoMatches`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 342 | `handle_action()` — wraps `query_one("#library-tracks", TrackTable)` + `await table.handle_action(action, count)` for vim-style action delegation | KEEP | Delegation path — `TrackTable.handle_action` itself can raise from any nested keybinding logic. The outer broad-catch is the right contract for "delegation must not crash the page". Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |

#### `ui/pages/queue.py` (9 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 126 | `_unregister_player_events()` — wraps `app.player` access + `player.off(PlayerEvent.TRACK_CHANGE, ...)` for unmount cleanup | KEEP | Lifecycle teardown — same contract as `services/macos_eventtap.py:106/111/149` (KEEP from Task 1.3). The player may already be invalidated during shutdown; `off()` must not crash the unmount path. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |
| 141 | `_on_track_change()` — wraps single `_update_current_track()` call (multi-step internally — header rebuild, two `query_one` calls, two `update_cell` operations) | KEEP | Per-event UI update; widget tree may be in transition during track-change events. Multi-step downstream. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |
| 178 | `_update_current_track()` — wraps single `table.update_cell(self._row_keys[old_index], "index", str(old_index + 1))` for restoring the previous play-indicator row | **NARROW** | Single-call try block. Expected failure is `RowDoesNotExist` / `CellDoesNotExist` (Textual DataTable errors when the underlying row was removed mid-update). Currently `logger.debug(..., exc_info=True)`. Bundle into Phase 4.5. |
| 185 | `_update_current_track()` — wraps single `table.update_cell(self._row_keys[new_index], "index", "▶")` for setting the new play-indicator row | **NARROW** | Mirror of line 178 (paint-the-new-indicator side). Same single-call NARROW pattern. Bundle into Phase 4.5. |
| 257 | `_update_footer()` — wraps single `query_one("#queue-footer", Static)` + `footer.update(footer_text)` | **NARROW** | Single-widget cluster; expected exception is `NoMatches`. Currently `logger.debug(..., exc_info=True)`. Bundle into Phase 4.5. |
| 408 | `_show_filter()` — wraps `query_one("#track-filter", Input)` + `value = ""` + `add_class("visible")` + `focus()` chain | **NARROW** | Identical pattern to `library.py:277`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 416 | `_hide_filter()` — wraps `query_one("#track-filter", Input)` + `remove_class("visible")` + nested `query_one("#queue-table", DataTable).focus()` | **NARROW** | Identical pattern to `library.py:285`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 424 | `_apply_filter()` — wraps single `self._filter_timer.stop()` for debounce-timer cancellation | **NARROW** | Single-call on a Textual `Timer`. Expected failure is `AttributeError` (timer was already stopped/disposed). Silent `pass` with NO log. Bundle into Phase 4.5. |
| 454 | `on_key()` Escape handler — wraps single `query_one("#track-filter", Input)` + `has_class` + nested `_filter_text` clear / `_refresh_queue` / `_hide_filter` | **NARROW** | Same pattern as `library.py:311`. Silent `pass` with NO log. Bundle into Phase 4.5. **Mutation-flow note:** the queue-page mutation paths (`_remove_selected`, `_move_track`, `_resolve_row_idx`, the `DELETE_ITEM`/reorder/`SELECT` branches in `handle_action`) deliberately have no broad-catch — they let exceptions propagate so the user sees a real crash if a queue mutation goes wrong, instead of silently misleading toast UI. That's the right call; no PROMOTE candidates in this file. |

#### `ui/pages/liked_songs.py` (9 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 127 | `_load_liked_songs()` — wraps `await ytmusic.get_liked_songs(limit=_FIRST_BATCH)` + `normalize_tracks(...)` for the initial page load | KEEP | Multi-call user-visible path. Logs with `logger.exception` (correct), falls back to empty state. Same contract as `library.py:207`. |
| 187 | `_update_footer()` — wraps `query_one("#liked-footer", Static)` + count math + `footer.update(text)` | **NARROW** | Single-widget cluster — `query_one` is the only call that can fail. Expected `NoMatches`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 207 | `_fetch_remaining_liked()` — wraps `await ytmusic.get_liked_songs(limit=None, timeout=_LARGE_PLAYLIST_TIMEOUT)` for background pagination | KEEP at this layer | Cascade with `services/ytmusic.py:154` (`get_liked_songs`, KEEP — service-layer broad-catch returns `[]` on API failure). This catch is belt-and-braces against the rare downstream `_call()` failure once Phase 4.1 narrows that. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |
| 223 | `_fetch_remaining_liked()` — wraps single `_refresh_table()` call (multi-step internally: clear, filter rebuild, restore cursor) | KEEP | Multi-step downstream; `_refresh_table` touches several widgets. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |
| 233 | `get_nav_state()` — wraps single `query_one("#liked-table", DataTable)` + `cursor_row` read | **NARROW** | Same pattern as `library.py:136`, `recently_played.py:153`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 317 | `_show_filter()` — wraps `query_one("#track-filter", Input)` + `value` + `add_class` + `focus` chain | **NARROW** | Identical to `library.py:277` and `queue.py:408`. Bundle into Phase 4.5. |
| 325 | `_hide_filter()` — wraps `query_one("#track-filter", Input)` + `remove_class` + nested `query_one("#liked-table", DataTable).focus()` | **NARROW** | Identical to `library.py:285` and `queue.py:416`. Bundle into Phase 4.5. |
| 334 | `_apply_filter()` — wraps single `self._filter_timer.stop()` | **NARROW** | Identical to `queue.py:424`. Bundle into Phase 4.5. |
| 365 | `on_key()` Escape handler — wraps `query_one("#track-filter", Input)` + `has_class` + nested filter-clear/`_refresh_table`/`_hide_filter` chain | **NARROW** | Identical pattern to `library.py:311` and `queue.py:454`. Bundle into Phase 4.5. |

#### `ui/pages/browse.py` (13 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 161 | `ForYouSection.load_data()` — wraps `await self.app.ytmusic.get_home()` for the For You shelves fetch | KEEP at this layer | Cascade with `services/ytmusic.py:166` (`get_home`, KEEP — already returns `[]` on failure). Single-call belt-and-braces. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |
| 169 | `ForYouSection.load_data()` outer — wraps `await self._populate_shelves()` (multi-step: query_one, remove_children, mount Label + ListView per shelf) | KEEP | Multi-call render path. Falls back to "Failed to load recommendations" with cleanup. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |
| 175 | `ForYouSection.load_data()` cleanup nested catch — wraps `query_one("#foryou-shelves", Vertical)` + `await container.remove_children()` for partial-mount cleanup after a render error | **NARROW** | Single-widget single-call try inside the cleanup branch of the outer catch. Expected exception is `NoMatches`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 224 | `ForYouSection._populate_shelves()` per-shelf render loop — wraps `mount(Label)` + `mount(ListView)` + per-item `list_view.append(...)` chain | KEEP | Per-iteration render with `continue`-on-failure semantics — same contract as `services/macos_media.py:109` and `auth.py:227`. One bad shelf must not skip the rest. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |
| 297 | `MoodsGenresSection.load_data()` — wraps `get_mood_categories()` + `_populate_categories()` (multi-call) | KEEP | Multi-call user-visible path. Falls back to "Failed to load moods & genres". Currently `logger.debug("...")` with NO `exc_info` at all — drops the traceback entirely. Phase 4.4 sweep priority (worse than the `debug + exc_info` drift — this loses the traceback for crash reports). |
| 412 | `ChartsSection.on_mount()` — wraps single `query_one("#charts-content").display = False` for initial-hide | **NARROW** | Single-call try block; expected `NoMatches`. Currently `logger.debug(..., exc_info=True)`. Bundle into Phase 4.5. |
| 422 | `ChartsSection.load_data()` — wraps `get_charts(country=country)` + `_populate_charts()` | KEEP | Multi-call user-visible path; falls back to "Failed to load charts". Currently `logger.debug("Failed to load charts for country=%r", country)` with NO `exc_info` — Phase 4.4 sweep priority (drops traceback). |
| 459 | `ChartsSection._show_error()` — wraps single `query_one("#charts-content").display = False` for hide-on-error | **NARROW** | Same pattern as line 412. Bundle into Phase 4.5. |
| 516 | `NewReleasesSection.on_mount()` — wraps single `query_one("#releases-content").display = False` | **NARROW** | Same pattern as line 412 (mirror file). Bundle into Phase 4.5. |
| 525 | `NewReleasesSection.load_data()` — wraps `get_new_releases()` + `_populate_releases()` | KEEP | Same pattern as line 422. Currently `logger.debug("Failed to load new releases")` with NO `exc_info` — Phase 4.4 sweep priority. |
| 569 | `NewReleasesSection._show_error()` — wraps single `query_one("#releases-content").display = False` | **NARROW** | Mirror of line 459. Bundle into Phase 4.5. |
| 678 | `BrowsePage._switch_section()` — per-section CSS toggle loop; wraps `query_one(f"#{sid}")` + `add_class` / `remove_class("active-section")` | KEEP | Per-iteration `query_one` with `continue`-on-failure semantics — one mounted section may legitimately fail while others succeed. Same contract as line 224. Currently `logger.debug("Failed to toggle browse section '%s'", sid, exc_info=True)` — Phase 4.4 sweep candidate. |
| 740 | `BrowsePage._load_mood_playlists()` — wraps `get_mood_playlists(category_params)` + conditional `navigate_to(...)` for the selected mood | KEEP | Multi-step user-visible path; surfaces `self.app.notify("Failed to load mood playlists", severity="error")`. Currently `logger.debug("Failed to load mood playlists")` with NO `exc_info` — Phase 4.4 sweep priority. |

#### `ui/pages/context.py` (17 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 224 | `on_worker_state_changed()` `fetch_remaining` SUCCESS branch — wraps single `query_one("#context-tracks", TrackTable)` + `table.append_tracks(tracks)` | **NARROW** | Single-widget single-call pair. Expected `NoMatches` (page navigated away mid-fetch). Currently `logger.debug(..., exc_info=True)`. Bundle into Phase 4.5. |
| 232 | `watch_loading()` — wraps single `query_one("#context-loading").display = loading` | **NARROW** | Single-call try block; expected `NoMatches`. Reactive watcher can fire before `compose()` finishes. Currently `logger.debug(..., exc_info=True)`. Bundle into Phase 4.5. |
| 240 | `watch_error_message()` — wraps single `query_one("#context-error", Label)` + `error_label.display = bool(msg)` + `update(msg)` chain | **NARROW** | Single-widget cluster; same pattern as `help.py:265`. Currently `logger.debug(..., exc_info=True)`. Bundle into Phase 4.5. |
| 352 | `_fetch_full_artist_songs()` outer — wraps single `await ytmusic.get_playlist(browse_id, limit=_FIRST_BATCH)` for the artist-songs background fetch | KEEP at this layer | Cascade with `services/ytmusic.py:279` (`get_playlist`, KEEP — service-layer broad-catch returns `{}` on failure). Background worker; the task description specifically called this out as a cascade-sink for Phase 4.1. Belt-and-braces single-call. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |
| 363 | `_fetch_full_artist_songs()` — wraps single `table.load_tracks(full_tracks)` for the swap-table-contents step | **NARROW** | Single-call try block on a `TrackTable` method. Expected failure is `AttributeError` (table unmounted between fetch and swap) or `RowDoesNotExist` from the underlying DataTable. Currently `logger.debug(..., exc_info=True)`. Bundle into Phase 4.5. |
| 375 | `_fetch_full_artist_songs()` chained — wraps single `await ytmusic.get_playlist_remaining(browse_id, len(raw_tracks))` for the remaining-tracks fetch | KEEP at this layer | Same cascade as line 352. Background worker, single-call belt-and-braces. Phase 4.4 sweep candidate. |
| 385 | `_fetch_full_artist_songs()` — wraps single `table.append_tracks(remaining_tracks)` for the chained-append step | **NARROW** | Mirror of line 363. Bundle into Phase 4.5. |
| 460 | `_focus_track_table()` — wraps single `query_one("#context-tracks", TrackTable).focus()` | **NARROW** | Single-call try block; expected `NoMatches`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 495 | `_add_to_library()` button-update — wraps single `query_one("#add-to-library-btn", Static).update("[✓ Added to Library]")` | **NARROW** | Single-call try block; expected `NoMatches`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 502 | `_add_to_library()` sidebar-refresh — wraps `from ... import PlaylistSidebar` + `app.query_one("#playlist-sidebar", PlaylistSidebar)` + `await ps.refresh_playlists()` | KEEP | Multi-call (import + query + async refresh). Sidebar may not be mounted; refresh may fail. The user already saw "Added to library" so silent failure here is acceptable, but currently bare `pass` with NO log — Phase 4.4 sweep candidate (add `logger.debug` so silent sidebar-refresh failures are diagnosable). |
| 546 | `on_track_table_filter_requested()` — wraps `query_one("#track-filter", Input)` + `value` + `add_class` + `focus` chain | **NARROW** | Identical to `library.py:277`, `queue.py:408`, `liked_songs.py:317`. Bundle into Phase 4.5. |
| 554 | `on_track_table_filter_closed()` — wraps `query_one("#track-filter", Input)` + `remove_class` + nested `query_one("#context-tracks", TrackTable).focus()` | **NARROW** | Identical to `library.py:285`, `queue.py:416`, `liked_songs.py:325`. Bundle into Phase 4.5. |
| 561 | `on_input_changed()` — wraps single `query_one("#context-tracks", TrackTable).apply_filter(event.value)` | **NARROW** | Single-call try block; expected `NoMatches`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 570 | `on_input_submitted()` — wraps single `query_one("#context-tracks", TrackTable).focus()` | **NARROW** | Single-call try block. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 586 | `on_key()` Escape handler — wraps `query_one("#track-filter", Input)` + `has_class` + nested `query_one("#context-tracks", TrackTable).clear_filter()` | **NARROW** | Identical pattern to `library.py:311`, `queue.py:454`, `liked_songs.py:365`. Bundle into Phase 4.5. |
| 630 | `handle_action()` artist-album branch — wraps `query_one("#context-albums", _ArtistAlbumList)` + multi-action `match` block (cursor up/down, GO_TOP/GO_BOTTOM, SELECT navigate_to) | KEEP | Multi-step delegation + `match` dispatch; expected exceptions vary per branch. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |
| 637 | `handle_action()` default-track-table branch — wraps `query_one("#context-tracks", TrackTable)` + `await table.handle_action(action, count)` | KEEP | Same delegation contract as `library.py:342` — `TrackTable.handle_action` can raise from any nested keybinding handler. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |

#### `ui/pages/search.py` (15 sites)

| Line | Method / context | Category | Rationale |
|---|---|---|---|
| 447 | `on_mount()` — wraps single `query_one("#songs-table", TrackTable)` + `move_cursor(row=...)` for restoring cursor on navigation back | **NARROW** | Single-widget cluster; expected `NoMatches`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 461 | `on_mount()` — wraps single `query_one("#search-input", Input).focus()` for fresh-entry auto-focus | **NARROW** | Single-call try block; expected `NoMatches`. Currently `logger.debug(..., exc_info=True)`. Bundle into Phase 4.5. |
| 490 | `get_nav_state()` — wraps single `query_one("#songs-table", TrackTable)` + `cursor_row` read | **NARROW** | Same pattern as `library.py:136`, `recently_played.py:153`, `liked_songs.py:233`. Silent `pass` with NO log. Bundle into Phase 4.5. |
| 563 | `on_key()` — wraps single `query_one("#suggestion-overlay", SuggestionList)` + `has_class("visible")` to detect suggestion-dropdown visibility | **NARROW** | Single-call try block; expected `NoMatches`. Silent `pass` with NO log (intentional fall-through to `suggestions_visible = False`, but no diagnostic if the overlay genuinely fails to mount). Bundle into Phase 4.5. |
| 581 | `on_key()` Escape — wraps `query_one("#songs-table", TrackTable)` + conditional `focus()` / `set_focus(None)` with **nested catch on line 584** for the focus-clear fallback | KEEP | Two-step contract: try focusing the songs-table; if that fails, fall through to the nested catch and call `set_focus(None)`. The outer broad-catch is the trigger for the inner recovery path — narrowing here would break the recovery contract. |
| 584 | nested `set_focus(None)` fallback inside line 581's `except` | KEEP | Final-resort focus clear; if even `set_focus(None)` raises (during shutdown, app teardown), there's nothing more to do. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |
| 605 | `_load_suggestions()` — wraps `await ytmusic.get_search_suggestions(query)` + `query_one("#suggestion-overlay", SuggestionList)` + `overlay.show_suggestions(suggestions)` | KEEP | Per-keystroke typeahead; the underlying `get_search_suggestions` is itself a service-layer KEEP returning `[]` on failure (`services/ytmusic.py:115`), so this catch is belt-and-braces for the multi-call render chain. Logs with `logger.exception` (correct). |
| 612 | `_hide_suggestions()` — wraps single `query_one("#suggestion-overlay", SuggestionList).hide()` | **NARROW** | Single-call try block; expected `NoMatches`. Currently `logger.debug(..., exc_info=True)`. Bundle into Phase 4.5. |
| 627 | `_load_recent_searches()` — wraps `await history.get_search_history(limit=10)` + `query_one + show_suggestions(...)` | KEEP | Multi-call worker path; `history.get_search_history` reads SQLite (wide failure surface). Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |
| 674 | `_execute_search()` history-log inner catch — wraps single `await history.log_search(query=..., filter_mode=..., result_count=...)` | KEEP | Mutation write to the search-history SQLite table — same fire-and-forget contract as `_playback.py:511/531` (`_log_current_listen`/`_log_listen_for`). Failure must not abort the search-render path. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate (per the convention these mutation writes should use `logger.exception`). |
| 685 | `_execute_search()` outer catch — wraps `_search_music`/`_search_all` + `_populate_results` + history log block; sits **alongside** the `asyncio.CancelledError` handler on line 678 (the v1.7.0 fix for "Searching… stuck forever") | KEEP | Multi-call user-visible path; logs with `logger.exception` (correct), shows "Search failed. Try again." in the loading indicator. The CancelledError handling is correctly placed *outside* the broad catch (above it in source order so cancellation re-raises after clearing the loading indicator) — exactly the pattern the task description called out. Correct as written. |
| 776 | `_clear_stale_results()` — wraps single `_populate_results(self._search_results)` (multi-step internally — populates 4 panels) | KEEP | Multi-step downstream; runs during input-change side-effect. Currently `logger.debug(..., exc_info=True)` — Phase 4.4 sweep candidate. |
| 783 | `_update_loading()` — wraps single `query_one("#loading-msg", Static)` + `label.update(text)` | **NARROW** | Single-widget cluster; expected `NoMatches`. Currently `logger.debug(..., exc_info=True)`. Bundle into Phase 4.5. |
| 801 | `on_click()` mode-toggle hit-test — wraps `widget.id == "search-mode" or query_one("#search-mode", Static) in widget.ancestors` | KEEP | Multi-call hit-test (attribute access on click target + `query_one` + `ancestors` traversal). Click handler must not crash on a malformed widget hit. Currently bare `pass` with NO log — Phase 4.4 sweep priority (silent swallow on click handlers makes click-routing bugs invisible). |
| 955 | `handle_action()` — wraps single `focused.query_one(TrackTable)` to find a TrackTable inside the focused panel | **NARROW** | Single-call try block; expected `NoMatchingNodes` (the focused widget has no TrackTable descendant, e.g. focus is on the Albums/Artists ListView panel). Currently `logger.debug(..., exc_info=True)` and a fall-through to the ListView branch — fall-through is correct, but narrowing the catch surfaces real bugs in `query_one` itself. Bundle into Phase 4.5. |

**Summary for ui/pages/ (73 sites):** 30 KEEP, 43 NARROW, 0 PROMOTE. Notable findings:

- **43 new "trivial single-call NARROW" candidates that fold into Phase 4.5** (currently 15 narrows from prior tasks: `auth.py:329`, `spotify_import.py:69`, `player.py:481`, `_playback.py:387`, `_playback.py:601`, `_app.py:493`, `_ipc.py:218`, `_keys.py:189`, `_session.py:93`, `_session.py:102`, `_session.py:159`, `_sidebar.py:47`, `_sidebar.py:74`, `_sidebar.py:231`, `_track_actions.py:160`). The 43 new ones cluster into a handful of repeated UI patterns (sub-bucket totals all verified to sum to 43):
  - **`get_nav_state()` cursor read** — 4 sites: `library.py:136`, `recently_played.py:153`, `liked_songs.py:233`, `search.py:490`. Single `query_one(table) + cursor_row` reads, all bare `pass` with NO log, all expected `NoMatches`.
  - **Filter-show / hide / escape trio** — 12 sites: `library.py:277/285/311`, `queue.py:408/416/454`, `liked_songs.py:317/325/365`, `context.py:546/554/586`. Each page has near-identical `_show_filter` / `_hide_filter` / `on_key`-Escape blocks with the same single-widget query+method-chain shape.
  - **`on_mount` initial-hide / restore-focus** — 4 sites: `browse.py:412/516`, `search.py:447/461`. Pure `NoMatches` single-call.
  - **`watch_*` reactive setters** — 3 sites: `help.py:265`, `context.py:232/240`. Reactive watchers fire pre-compose; single `query_one` failure is the expected case.
  - **DataTable cell-update (`update_cell`)** — 2 sites: `queue.py:178/185`. `RowDoesNotExist` / `CellDoesNotExist` is the expected exception.
  - **TrackTable swap/append in background workers** — 2 sites: `context.py:363/385`. Single `table.load_tracks` / `table.append_tracks` calls.
  - **Filter timer-stop** — 2 sites: `queue.py:424`, `liked_songs.py:334`. Both `self._filter_timer.stop()` (`AttributeError` expected).
  - **`on_worker_state_changed` single-call** — 1 site: `context.py:224` (`query_one + append_tracks`).
  - **Single-widget footer / loading update** — 3 sites: `queue.py:257`, `liked_songs.py:187`, `search.py:783`. `query_one + Static.update`.
  - **Single-call focus / button-update / input apply_filter / focus** — 4 sites in `context.py` (460, 495, 561, 570).
  - **Single-call suggestion-hide** — 1 site: `search.py:612` (`overlay.hide()`).
  - **Single-call `query_one` for descendant-search** — 1 site: `search.py:955` (`focused.query_one(TrackTable)`).
  - **Single-call cleanup-nested-catch** — 1 site: `browse.py:175` (cleanup inside outer catch).
  - **Single-call `_show_error` display-toggle** — 2 sites: `browse.py:459/569`.
  - **Single-call has_class check** — 1 site: `search.py:563`.

  Total: 4 + 12 + 4 + 3 + 2 + 2 + 2 + 1 + 3 + 4 + 1 + 1 + 1 + 2 + 1 = **43**. All fold cleanly into Phase 4.5.
- **Three indirect cascade sites for Phase 4.1 (`ytmusic._call()` narrow)** — KEEP at this layer until 4.1 lands, then can be tightened together. The task description specifically called these out:
  - `liked_songs.py:207` (`_fetch_remaining_liked` background pagination — `ytmusic.get_liked_songs`).
  - `context.py:352` (`_fetch_full_artist_songs` initial — `ytmusic.get_playlist`).
  - `context.py:375` (`_fetch_full_artist_songs` chained-remaining — `ytmusic.get_playlist_remaining`).
  - These are the "background workers as cascade-sink for service-layer narrowing" sites. Once 4.1 narrows `_call()`, these single-call sites can be tightened to specific exception types (auth / network / unexpected) so background fetches don't silently swallow programming errors in the service layer.
- **No mutation-flow PROMOTE candidates found.** The user-visible mutation paths in these pages — `queue.py` reorder/delete (no broad-catch — propagates), `context.py:472 _add_to_library` (uses `add_to_library` which already returns `bool`), `liked_songs.py` track-add to queue (no broad-catch) — all correctly avoid the silent-failure pattern. The `search.py:674` history-log catch is fire-and-forget (KEEP) and the rest of search's `_execute_search` correctly surfaces failures via the loading indicator + `logger.exception`. Nothing in this tier swallows a user-visible mutation silently.
- **No new Phase 4.x task candidates.** Every NARROW site fits Phase 4.5 (trivial single-call). No high-priority mutation-flow / write-path NARROWs like `_session.py:211` from Task 1.5. No new logging-hygiene patterns beyond what 4.4 already covers.
- **Logging-hygiene drift (Phase 4.4 sweep candidates among KEEP-tier sites only — sites that are *not* also in the NARROW list above):** 18 sites use `logger.debug(..., exc_info=True)` rather than `logger.exception`. Lines (log-line numbers, broad-except is the line above each): `library.py:233/343`, `queue.py:127/142`, `liked_songs.py:208/224`, `browse.py:162/170/225/679`, `context.py:353/376/631/638`, `search.py:585/628/675/777`. Per-file totals: library 2 + queue 2 + liked_songs 2 + browse 4 + context 4 + search 4 = **18**.
- **Logging-hygiene priority cluster — debug log with NO `exc_info` at all** (worse than `debug + exc_info=True` because it drops the traceback entirely): 4 sites in `browse.py`. Lines 298 (`MoodsGenresSection.load_data`), 423 (`ChartsSection.load_data`), 526 (`NewReleasesSection.load_data`), 741 (`BrowsePage._load_mood_playlists`). All user-visible "Failed to load X" handlers where the user sees a notify but the underlying exception is silently lost. Phase 4.4 should prioritise these — "user complains about failure but log shows nothing useful".
- **Silent-pass-no-log offenders** (KEEP-tier broad catches with NO log at all): `context.py:502` (sidebar refresh after add-to-library), `search.py:801` (mode-toggle click hit-test). Both should add at minimum a `logger.debug` so silent failures are diagnosable. Phase 4.4 candidates.

### `ui/` other files (46 sites) + `utils/`/`cli.py`/`ipc.py` (10 sites)

#### `ui/` other files (46 sites)

##### `ui/playback_bar.py` (5 sites)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 168 | `_RepeatButton.on_click` updating bar after `cycle_repeat()` | NARROW | Single block does `query_one + update_repeat + notify`; only `query_one` can plausibly miss. Belongs in Phase 4.5 (trivial single-call). |
| 206 | `_ShuffleButton.on_click` updating bar after `toggle_shuffle()` | NARROW | Same query+update+notify pattern as repeat; Phase 4.5. |
| 245 | `_HeartButton.on_click` running `_toggle_like_current` worker | KEEP | `run_worker` of an attribute that may not exist on every host; defensive against missing app surface. Already logs. |
| 392 | `PlaybackBar.update_like_status` updating heart child | NARROW | Single-call `query_one + assign attribute`; only `NoMatches` realistic. Phase 4.5. |
| 505 | `_FooterBar.set_active_page` updating each footer button | NARROW | Single-call `query_one + assign attribute` per loop iter; Phase 4.5 (per-iter narrow). |

##### `ui/header_bar.py` (2 sites)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 85 | `set_playlist_state` toggling button class | NARROW | Single-call `query_one + add/remove_class`; `NoMatches` only. Phase 4.5. **Logging-hygiene drift** — silent `pass`, no log at all. |
| 104 | `_apply_lyrics_classes` adjusting active/dimmed | NARROW | Same query+class-toggle pattern; Phase 4.5. **Logging-hygiene drift** — silent `pass`, no log at all. |

##### `ui/popups/playlist_picker.py` (5 sites)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 29 | `_load_recent_ids` reading `RECENT_PLAYLISTS_FILE` | KEEP | File-read defensive load — JSON parse / `OSError` / corrupted file all valid; failure is silently graceful (returns `[]`). Already logs at debug. |
| 39 | `_save_recent_ids` writing `RECENT_PLAYLISTS_FILE` | KEEP | File-write defensive save — `OSError` / parent-dir creation / serialization. Already logs at debug. |
| 179 | `_fetch_playlists` calling `ytmusic.get_library_playlists` | KEEP | Async fetch boundary — 4.1 cascade sink; will tighten once `_call()` narrows. Already uses `logger.exception`. |
| 306 | `_create_and_add` creating playlist + add tracks (mutation flow) | KEEP | Multi-call mutation flow (`create_playlist` + `add_playlist_items`) with user-visible notify + status update. Already uses `logger.exception`. **Phase 4.3 cascade** — once `add_playlist_items` returns bool, the inner success path can verify and surface partial-add failures. |
| 334 | `_do_add` adding tracks to chosen playlist (mutation flow) | KEEP | Same shape as 306; user-visible failure surface; Phase 4.3 cascade. Uses `logger.exception`. |

##### `ui/popups/spotify_import.py` (7 sites)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 422 | `on_input_submitted` focus-next-multi-url-input | NARROW | Single-call `query_one + focus`; `NoMatches` only. Phase 4.5. |
| 494 | `_do_match` extracting tracks from Spotify (`extract_spotify_tracks`) | KEEP | Boundary catch around third-party Spotify API call — network/parse/auth errors all valid; user-visible status update. Captures `as exc` for the message. **Logging-hygiene** — no `logger.exception`, only status-update; rendering the exc string to UI is fine but a debug log of the traceback would help support. |
| 521 | `_do_match` per-track YTMusic search inside loop | KEEP | Per-track best-effort match — falling through to `[]` is the intentional contract (one bad query shouldn't kill the whole import). **Logging-hygiene** — no log at all; could lose systemic failure signal across N tracks. Worth a debug log per failure for diagnosability. |
| 612 | `_start_multi_import` validating multi-URL inputs | NARROW | Single-call `query_one + .value.strip()`; `NoMatches` only. Phase 4.5. |
| 659 | `_do_multi_import` per-part Spotify extract | KEEP | Same shape as 494 — third-party API boundary, user-visible status with exc message. **Logging-hygiene** — no traceback logged. |
| 686 | `_do_multi_import` per-track YTMusic search | KEEP | Same shape as 521 — per-track best-effort fallthrough. **Logging-hygiene** — no log at all. |
| 900 | `_do_create` creating playlist + batched `add_playlist_items` (mutation flow) | KEEP | Multi-call mutation outer catch with user-visible status update. **Phase 4.3 cascade — high impact:** `add_playlist_items` currently swallows exceptions and returns `None`, so this outer catch never fires for partial-add failures and the popup happily dismisses with `playlist_id` even if 0 of N tracks were added. Once 4.3 lands and `add_playlist_items` returns bool/raises, this outer catch + a per-batch check can surface "imported X of Y" honestly. |

##### `ui/sidebars/lyrics_sidebar.py` (13 sites)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 200 | `_unregister_player_events` (unmount cleanup) | KEEP | Cleanup-on-unmount across two `player.off` calls; defensive against missing player attribute / already-detached callbacks. Already logs at debug. **Logging-hygiene drift** — `logger.debug(..., exc_info=True)` should be `logger.exception`. |
| 210 | `_on_track_change` event handler | KEEP | Top-level event-handler boundary — must not propagate into the player thread bridge. **Logging-hygiene drift** — `debug + exc_info=True`. |
| 223 | `_on_position_change` event handler (called every position tick) | KEEP | Same — event-handler boundary; runs at high frequency, must not crash. **Logging-hygiene drift.** |
| 249 | `_load_for_current_track` updating header label | NARROW | Single-call `query_one + .update`; `NoMatches` only. Phase 4.5. **Logging-hygiene drift.** |
| 283 | `_fetch_lyrics_for_track` falling back to LRCLIB | KEEP | Third-party network call boundary (LRCLIB) — best-effort fallback; failure should silently fall through to "no lyrics". **Logging-hygiene drift.** |
| 349 | `_get_rtl_wrap_width` reading scroll region width | KEEP | Defensive width read with sensible numeric fallback (35); must not crash text rendering. Silent `pass` is correct here. |
| 403 | `_show_status` updating status label + scroll display | NARROW | Three `query_one` calls in sequence — could split, but each is a single attribute set. Phase 4.5 (compound trivial). **Logging-hygiene drift.** |
| 410 | `_show_scroll` toggling visibility | NARROW | Two `query_one + .display = bool` calls; Phase 4.5. **Logging-hygiene drift.** |
| 418 | `watch_current_line_index` reactive watcher | KEEP | Reactive watcher boundary — Textual swallows exceptions out of watchers anyway, but explicit catch keeps the logged signal. **Logging-hygiene drift.** |
| 464 | `_apply_line_highlight` auto-scroll calculation | NARROW | Single block of `query_one + virtual_region access + scroll_to`; `NoMatches` is the realistic failure. Phase 4.5. **Logging-hygiene drift.** |
| 513 | `manual_scroll` (user-action) scrolling lines | NARROW | Single `query_one + scroll action` loop; Phase 4.5. **Logging-hygiene drift.** |
| 522 | `_scroll_to_top` | NARROW | Single `query_one + scroll_home`; Phase 4.5. **Logging-hygiene drift.** |
| 531 | `_scroll_to_bottom` | NARROW | Single `query_one + scroll_end`; Phase 4.5. **Logging-hygiene drift.** |

##### `ui/sidebars/playlist_sidebar.py` (7 sites)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 217 | `LibraryPanel._set_loading_visible` toggling loading + list | NARROW | Two `query_one + .display = bool`; Phase 4.5. **Logging-hygiene drift.** |
| 289 | `LibraryPanel.show_filter` revealing filter input | NARROW | Single `query_one + add_class + value=' ' + focus`; Phase 4.5. **Logging-hygiene drift.** |
| 299 | `LibraryPanel.hide_filter` hiding filter input | NARROW | Single `query_one + remove_class`; Phase 4.5. **Logging-hygiene drift.** |
| 335 | `on_list_view_highlighted` reading parent sidebar width | KEEP | Defensive read with numeric fallback (30); `pass` correct — must not crash highlight handler. Silent-pass-no-log offender (Phase 4.4 candidate — a debug log would help). |
| 523 | `_load_playlists` worker calling `ytmusic.get_library_playlists` | KEEP | Async fetch boundary — Phase 4.1 cascade sink. Already uses `logger.exception`. |
| 573 | `handle_sidebar_action` looking up the list view | NARROW | Single-call `query_one`; Phase 4.5. **Silent-pass-no-log offender.** |
| 605 | `get_highlighted_item` looking up panel + list-view | NARROW | Two `query_one` calls + index read — could split, single block. Phase 4.5. **Logging-hygiene drift.** |

##### `ui/widgets/track_table.py` (6 sites)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 242 | `_refresh_play_indicator` reading `app.queue.current_track` | KEEP | Defensive read across optional attribute chain; silent `pass` correct (no playing track is normal). **Silent-pass-no-log offender** — minor; rare-path. |
| 279 | `set_playing_index` restoring old row's original number | NARROW | Single `update_cell` call after small dict access; `IndexError` / row-key staleness only. Phase 4.5. |
| 286 | `set_playing_index` setting play indicator on new row | NARROW | Single `update_cell`; Phase 4.5. |
| 308 | `_invalidate_table` recomputing virtual size | KEEP | Defensive geometry calc across columns dict + size attrs; called from layout invalidation paths where partial state is normal. Silent-pass-no-log — Phase 4.4 candidate (debug log). |
| 320 | `_fill_title_column` reading title column | NARROW | Single `self.columns.get("title")` — `KeyError` only realistic, but `.get` already returns None. The catch is essentially dead. Phase 4.5 (or remove). |
| 459 | `apply_filter` stopping previous filter timer | NARROW | Single `self._filter_timer.stop()` — `AttributeError` if the timer object is in a stopped/unset state. Same shape as the existing pages-tier filter-timer-stop cluster (queue.py:424, liked_songs.py:334). Phase 4.5. |

##### `ui/widgets/album_art.py` (1 site)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 119 | `_load_thumbnail` async worker rendering image | KEEP | Worker boundary around HTTP fetch + PIL decode + pixel render — network/IO/decode errors all valid; user sees a missing thumbnail (graceful). Already logs at debug. **Logging-hygiene drift** — `debug + exc_info=True` should be `logger.exception`. |

**Summary for ui/ other (46 sites):** 22 KEEP, 24 NARROW, 0 PROMOTE. Notable findings:
- **Trivial single-call NARROW cluster — 24 sites** dominate this tier and fold cleanly into Phase 4.5. Per-file tally: `playback_bar.py` 4 (168/206/392/505) + `header_bar.py` 2 (85/104) + `spotify_import.py` 2 (422/612 — input-focus) + `lyrics_sidebar.py` 7 (249/403/410/464/513/522/531 — query+update / scroll-action) + `playlist_sidebar.py` 5 (217/289/299/573/605) + `track_table.py` 4 (279/286/320/459 — row-cell-update / filter-timer-stop) + `playlist_picker.py` 0 + `album_art.py` 0 = 4+2+2+7+5+4 = **24**.
- **KEEP per-file tally:** `playback_bar.py` 1 (245 worker) + `header_bar.py` 0 + `playlist_picker.py` 5 (29/39/179/306/334) + `spotify_import.py` 5 (494/521/659/686/900) + `lyrics_sidebar.py` 6 (200/210/223/283/349/418) + `playlist_sidebar.py` 2 (335/523) + `track_table.py` 2 (242/308) + `album_art.py` 1 (119) = 1+0+5+5+6+2+2+1 = **22**. KEEP + NARROW = 22 + 24 = **46** ✓.
- **Mutation-flow cascade for Phase 4.3 — `spotify_import.py:900`** is the highest-impact site in this tier. The popup dismisses with a `playlist_id` claiming success even when `add_playlist_items` swallowed every batch failure (the service-layer catch returns None silently). Same shape but smaller blast radius at `playlist_picker.py:306/334`. All three should be tightened *together with* the 4.3 service-layer fix, not in isolation.
- **Reactive-watcher KEEP** — `lyrics_sidebar.py:418` is the only `watch_*` reactive-watcher boundary in this tier; Textual swallows watcher exceptions anyway, but the explicit catch keeps the log signal.
- **Silent-pass-no-log offenders that remain after 4.5 lands** (Phase 4.4 minor candidates): `header_bar.py:85/104` (2 — fold into 4.5 narrow with a log), `lyrics_sidebar.py:349` (1 — fallback path, debug log only), `playlist_sidebar.py:335/573` (2 — one folds into 4.5, one is the highlight handler), `track_table.py:242/308` (2 KEEP-tier silent-pass). The 4.5 narrows already pull in `track_table.py:320/459` (`pass`-only sites converted to typed catches with logs).
- **Logging-hygiene drift — KEEP-tier `debug + exc_info=True`** (Phase 4.4 sweep candidates, KEEP-tier only — i.e. excluding sites already in the NARROW list above which Phase 4.5 will rewrite): `playlist_picker.py:29/39` (2), `lyrics_sidebar.py:200/210/223/283/418` (5), `playlist_sidebar.py` 0, `album_art.py:119` (1), `playback_bar.py:245` (1). **Total KEEP-tier 4.4 candidates: 2 + 5 + 0 + 1 + 1 = 9 sites.**

#### `utils/` + `cli.py` + `ipc.py` (10 sites)

##### `utils/logging.py` (2 sites)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 53 | `setup_logging` closing prior file handler | KEEP | Cleanup of stale handler — `OSError` on close all valid; intentional belt-and-braces during reconfiguration. Already logs at debug. |
| 110 | `_install_excepthooks._prune_old_crashes` deleting stale crash logs | KEEP | Background housekeeping inside excepthook; must never raise from within the hook. Silent `pass` correct — outer `OSError` per-file is already caught above; this is the directory-scan outer guard. **Silent-pass-no-log offender** — debug log harmless to add. |

##### `utils/bidi.py` (1 site)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 76 | `_resolve_should_reorder` reading bidi_mode from settings | KEEP | Defensive belt-and-braces around `get_settings()` import + attribute access — text-rendering path, must never crash. Falls back to `auto`. Silent fallthrough is correct. |

##### `utils/formatting.py` (3 sites)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 192 | `copy_to_clipboard` PowerShell `Set-Clipboard` (Windows) | KEEP | Subprocess boundary — `FileNotFoundError`, `CalledProcessError`, encoding issues all valid; returns `False` for caller to handle. **Silent-pass-no-log offender** — minor; clipboard failures are usually noisy enough on the calling side. |
| 199 | `copy_to_clipboard` `pbcopy` (macOS) | KEEP | Same shape as 192. |
| 213 | `copy_to_clipboard` `xclip`/`xsel`/`wl-copy` loop (Linux) | KEEP | Same shape — per-tool fallthrough is the intentional contract (try the next tool). |

##### `cli.py` (1 site)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 345 | `cli search` calling `ytm.search` | KEEP | Top-level CLI command boundary — `_error(...)` exits cleanly with stderr message including the exc string. Standard CLI failure surface. **Logging-hygiene** — could log the traceback at debug for `--debug` runs, but `_error` already prints exc. |

##### `ipc.py` (3 sites)

| Line | Method-context | Category | Rationale |
|------|----------------|----------|-----------|
| 227 | `_handle_client` outer dispatch boundary | KEEP | IPC server boundary — same shape as `_ipc.py:102` which Task 1.5 categorised KEEP. Must not let one bad message kill the server. Already logs at debug. **Logging-hygiene drift** — `debug + exc_info=True` should be `logger.exception` so server-side IPC bugs surface in bug reports. |
| 232 | `_handle_client` inner — sending error response after outer failure | KEEP | Last-ditch attempt to send `{"ok": False}` after the outer catch fires; if the writer is already dead, swallow and move on. Silent `pass` correct. |
| 238 | `_handle_client` `writer.wait_closed()` cleanup | KEEP | `finally` block cleanup; client may already be gone. Silent `pass` correct. |

**Summary for utils/ + cli + ipc (10 sites):** 10 KEEP, 0 NARROW, 0 PROMOTE. Notable findings:
- **All KEEP — file is uniform.** Every site is either (a) third-party / OS / subprocess boundary in formatting/clipboard, (b) defensive belt-and-braces in text-rendering / settings-load (`bidi.py`, `logging.py`), (c) top-level CLI handler, or (d) IPC server boundary. This matches the file-specific guidance up front.
- **Logging-hygiene drift — Phase 4.4 candidates:** `ipc.py:227` (`debug + exc_info=True` → should be `logger.exception` so IPC server-side bugs reach bug reports), `cli.py:345` (no log at all — relies on `_error` printing exc string; debug log of traceback would help `--debug` users). **Total: 2 sites.**
- **Silent-pass-no-log offenders** (Phase 4.4 minor candidates): `utils/logging.py:110` (crash-log prune), `utils/formatting.py:192/199/213` (clipboard tools). All debug-log only — low priority. **Total: 4 sites** but very low value to fix.
- **No new Phase 4.x task candidates.** Nothing in this tier is a mutation flow or write-path; nothing should PROMOTE; nothing introduces a pattern not already covered by 4.4 (logging hygiene). Confirms the file-specific guidance: utils + cli + ipc are all defensive-boundary / top-level-handler territory.

## Cross-cutting observations

- **The graceful-degrade contract is the architectural backbone, not the bug.** Services in `services/ytmusic.py`, `services/lrclib.py`, `services/stream.py`, `services/auth.py`, etc. return safe defaults (`[]`, `{}`, `None`, `""`, `False`) on any API/network/parse failure. UI handlers then wrap calls to those services with their own broad-catches, on the assumption that the service's contract holds. This produces a deliberate two-layer safety net: the service swallows the API error and returns the sentinel, and the UI swallows anything that escapes the service (programming bugs, asyncio cancellation, downstream render failures) and renders an empty state. **Narrowing service layers without updating UI cascade sinks in lockstep produces silent regressions** — the UI suddenly receives exceptions it wasn't written to expect. Phase 5 exists specifically to update those cascade sinks once Phase 4.1 / 4.3 land.
- **Optional-service callbacks are uniformly KEEP across every audited file** — Discord RPC (`services/discord_rpc.py` 4 sites), Last.fm (`services/lastfm.py` 3), MPRIS (`services/mpris.py` 1), macOS event-tap (`services/macos_eventtap.py` 4), macOS Now Playing (`services/macos_media.py` 3), update check (`services/update_check.py` 1), LRCLIB (`services/lrclib.py` 1). Each subscriber must fail independently without crashing playback; the per-tick MPRIS/macOS/Discord broadcasts in `app/_playback.py` (lines 344, 350, 361, 461, 471, 493) follow the same pattern. **Don't touch these.**
- **The "bar-not-mounted" pattern is the single most repeated KEEP shape in the codebase.** It appears across `_playback.py` (lines 78, 373, 380, 397, 411, 417, 443, 451), `_session.py` (76, 145), `_app.py` (493, 500), `_keys.py` (189), `_sidebar.py` (42, 47, 59, 69, 74, 84, 231), `lyrics_sidebar.py` (multiple), `track_table.py`, and most `ui/pages/`. Multi-call orchestration sites stay KEEP — `query_one` failure mid-orchestration is a legitimate "widget gone" recovery path. **Single-call query+act sites narrow in Phase 4.5** — the only realistic failure is `textual.css.query.NoMatches` and the broad catch hides bugs in the called method itself.
- **Mutation methods split cleanly along their return type.** `services/ytmusic.py` has 7 mutation methods. The 4 that return `bool` (`delete_playlist`, `add_to_library`, `remove_album_from_library`, `unsubscribe_artist`) are KEEP — the contract is correct; callers can branch on success. The 3 that return `None` (`rate_song`, `add_playlist_items`, `remove_playlist_items`) are NARROW (Phase 4.3) — UI claims success on silent failure. Plus `app/_session.py:211` is a write-path mutation NARROW with a UX-toast fix attached (Phase 4.6). The user-visible mutation flows in `ui/pages/queue.py` (reorder/delete) and `ui/pages/context.py:472` (`_add_to_library`) are correctly designed: queue mutations have no broad-catch (let exceptions propagate), and `_add_to_library` already uses the `bool`-returning service method.
- **`services/ytmusic.py:_call()` is the only outer-loop broad-catch in the codebase that drives state-change behaviour.** It increments `_consecutive_api_failures` and reinitialises `self.client` at threshold (3). Currently any exception — including programming errors like `AttributeError` from a refactor — triggers that counter bump and can spuriously reinit the client. Phase 4.1 narrows it to expected error types (network, auth, ytmusicapi-specific) and lets unexpected propagate as bugs. Phase 4.2 (thread-safety lock on the `client` lazy-init property) is bundled with 4.1 because the same code path is touched.
- **Logging-hygiene drift is widespread but mechanical.** ~58 sites use `logger.debug(..., exc_info=True)` instead of `logger.exception` per CLAUDE.md guidance. Per-section breakdown: services 1 (`ytmusic.py:167`), `_playback.py` 16, app/ other 13, ui/pages KEEP-tier 18, ui/ other KEEP-tier 9, utils/cli/ipc 1. On top of that, 4 priority "no `exc_info` at all" sites in `browse.py` (lines 298, 423, 526, 741 — user-visible "Failed to load X" handlers that drop the traceback entirely), and ~13 silent-pass-no-log sites scattered across the codebase. Phase 4.4 sweeps all of these mechanically.
- **Trivial single-call NARROWs cluster into ~6 repeated UI shapes.** 82 sites total in Phase 4.5: filter-show/hide/escape trios across pages (12 sites), `get_nav_state()` cursor reads (4), `on_mount` / `watch_*` reactive setters / single-widget query+act (20 in ui/pages), background-worker query+update (7), services + app pre-existing trivial narrows (15), and ui/ other widgets (24 across `playback_bar`, `header_bar`, popups, sidebars, `track_table`). The shape is identical: `query_one(selector) + one method call` wrapped in `except Exception: pass` (or `except Exception: logger.debug(...)`). **Highly mechanical sweep — but 82 sites in one commit is unreviewable, so split into 6 sub-clusters per the Phase 4.5 plan below.**

## Cascade map (UI handlers depending on service contracts)

This is the load-bearing reference for Phase 5 sequencing. Each bullet maps a service-layer NARROW landing in Phase 4 to the UI / app handlers that wrap calls to that method and currently rely on the broad-catch contract. When the service-layer call is narrowed, every handler in the cascade list needs review (most can stay KEEP belt-and-braces, but several can be tightened or have their `notify(...)` text differentiated per error type once the service returns typed signals).

- **`services/ytmusic.py:65 _call()` — Phase 4.1 cascade sinks** (every UI/app site that wraps a method which goes through `_call()`):
  - `app/_playback.py:111` — `play_track()`, stream-resolution path (calls `stream_resolver.resolve()` which itself wraps `_call()`-derived data; belt-and-braces).
  - `app/_ipc.py:218` — `_ipc_queue_add()` single-call `await self.ytmusic.get_watch_playlist(video_id)` (also independently flagged NARROW in Phase 4.5e — narrows together).
  - `ui/pages/liked_songs.py:207` — `_fetch_remaining_liked()` background pagination via `get_liked_songs(limit=None, ...)`.
  - `ui/pages/context.py:352` — `_fetch_full_artist_songs()` initial fetch via `get_playlist(browse_id, limit=_FIRST_BATCH)`.
  - `ui/pages/context.py:375` — `_fetch_full_artist_songs()` chained-remaining fetch via `get_playlist_remaining(...)`.
  - `ui/pages/browse.py:161` — `ForYouSection.load_data()` via `get_home()`.
  - `ui/pages/search.py:605` — `_load_suggestions()` typeahead via `get_search_suggestions()`.
  - `ui/popups/playlist_picker.py:179` — `_fetch_playlists()` via `get_library_playlists()`.
  - `ui/sidebars/playlist_sidebar.py:523` — `_load_playlists()` worker via `get_library_playlists()`.

- **`services/ytmusic.py:383 rate_song()` — Phase 4.3 cascade** (mutation narrow + return-bool fix):
  - `app/_playback.py:558` — `_toggle_like_current()`, the `l` keybinding's primary call site. Once `rate_song` returns `bool`, this catch can branch per error-type (auth → "Sign in again", network → "Check connection", success → flip the heart). Currently shows the same generic "Couldn't update like state" toast for every failure mode.
  - `app/_track_actions.py:136` — actions-popup `toggle_like` branch, secondary call site. Same cascade — currently does NOT log the exception at all (only shows a user toast); Phase 4.3 should add `logger.exception` here as part of the cascade fix.

- **`services/ytmusic.py:390 add_playlist_items()` — Phase 4.3 cascade** (mutation narrow + return-bool fix):
  - `ui/popups/spotify_import.py:900` — **worst-impact site in the cascade.** `_do_create()` outer catch wraps the multi-call create-playlist + batched `add_playlist_items` mutation. Today the popup dismisses with `playlist_id` claiming success even when every batch silently failed (because `add_playlist_items` returns `None` on failure). Phase 4.3 + this cascade must surface "imported X of Y" honestly.
  - `ui/popups/playlist_picker.py:306` — `_create_and_add()` multi-call mutation flow. Smaller blast radius (single playlist add, not bulk import) but same silent-success-on-failure shape.
  - `ui/popups/playlist_picker.py:334` — `_do_add()` adding tracks to chosen playlist. Same shape as :306.

- **`services/ytmusic.py:468 remove_playlist_items()` — Phase 4.3 cascade**:
  - **No active UI call sites in the codebase** as of this audit. The method is defined and guarded but not currently invoked from `app/` or `ui/`. Narrowing the service-layer catch and switching to `bool` return is still in scope (parity with the other mutation methods), but Phase 5 has no follow-up cascade work for this method until a UI surface starts using it.

- **`app/_session.py:211 _save_session_state()` write-path — Phase 4.6** (NARROW + UX-toast):
  - This is a self-contained UI-cascade pair, not a service→UI cascade: the NARROW (`OSError`/`TypeError`) and the `self.notify("Could not save session state", severity="warning", timeout=5)` UX fix land in the same commit. No downstream handlers depend on the broad-catch contract.

**Phase 5 cascade-update estimate.** Across the four service-layer narrow events above, ~14 distinct UI/app handlers wrap the affected service calls (9 cascade sinks for `_call()`, 2 for `rate_song`, 3 for `add_playlist_items`, 0 for `remove_playlist_items`). Most stay KEEP-with-tightened-error-types or KEEP-with-better-notify-text; only the three `add_playlist_items` cascade sites materially change behaviour (partial-add reporting). Estimate ~14 sites for Phase 5 once the cascade is fully traced.

## Phase plan derived from this audit

The audit produces four NARROW work-clusters (4.1, 4.3, 4.5, 4.6), one bundled thread-safety task (4.2), one logging-hygiene sweep (4.4), and one cascade-update phase (5). Each Phase 4 sub-task is independently committable except where noted.

### Phase 4.1 — Narrow `services/ytmusic.py:65 _call()` outer catch (1 site)

The only outer-loop broad-catch in the codebase that drives state-change behaviour (failure counter + client reinit). Split caught exceptions into three cohorts:
- **Auth errors** (signal to reauth, don't count toward reinit) — likely `requests.HTTPError` with 401/403, or a ytmusicapi-specific "credentials expired" type.
- **Network/transient errors** — `requests.RequestException`, `TimeoutError`, `OSError` — count toward `_consecutive_api_failures` and trigger reinit at threshold.
- **Unexpected exceptions** — propagate as bugs; do NOT bump the counter.

Mind the `get_playlist()` `_send_request` monkey-patch path (line 279): the inner `try/finally` correctly restores the patch even if `_call()` raises, so this narrowing doesn't break the patch-restore contract.

### Phase 4.2 — Thread-safety lock on `YTMusicService.client` lazy-init (0 NARROW sites — bundled with 4.1)

Add a `threading.Lock` (or `asyncio.Lock`, depending on call-site shape) around the lazy-init of `self.client` so concurrent first-access from background workers doesn't race on construction. Bundled with 4.1 because both touch the same outer-loop code path.

### Phase 4.3 — Mutation methods narrow + return-bool fix (3 service-layer sites + 5 UI cascade sites)

Three service-layer mutation methods currently return `None` whether the API call succeeded or failed, leaving callers unable to detect failure. Fix:
- `services/ytmusic.py:383 rate_song()` — narrow + return `bool`. Cascade to `app/_playback.py:558` and `app/_track_actions.py:136` (the latter currently does NOT log at all — add `logger.exception` as part of the cascade fix).
- `services/ytmusic.py:390 add_playlist_items()` — narrow + return `bool`. Cascade to `ui/popups/spotify_import.py:900` (worst-impact — popup claims success on silent failure), `ui/popups/playlist_picker.py:306`, and `ui/popups/playlist_picker.py:334`.
- `services/ytmusic.py:468 remove_playlist_items()` — narrow + return `bool` for parity. **No active UI cascade sites today.**

The cascade UI sites stay in 4.3 (not deferred to Phase 5) because the service-layer + cascade fix must land together to avoid a window where the popup claims success while the service re-raises into the broad-catch and gets swallowed differently.

### Phase 4.4 — Logging-hygiene sweep (~58 strict + ~17 priority/silent sites)

Codebase-wide sweep, mechanical:
- **Strict `logger.debug(..., exc_info=True)` → `logger.exception(...)` per CLAUDE.md guidance** — ~58 sites. Per-section: `services/ytmusic.py` 1 (`get_home` line 167), `_playback.py` 16, app/ other 13, ui/pages KEEP-tier 18, ui/ other KEEP-tier 9, utils/cli/ipc 1.
- **Priority "no `exc_info` at all" sites in `browse.py`** — 4 sites (lines 298, 423, 526, 741). All user-visible "Failed to load X" handlers; the user sees a notify but the underlying exception is silently lost.
- **Silent-pass-no-log offenders** — ~13 sites scattered (`_app.py:86/347` theme-load, `context.py:502` sidebar refresh, `search.py:801` mode-toggle hit-test, `header_bar.py:85/104`, `lyrics_sidebar.py:349`, `playlist_sidebar.py:335/573`, `track_table.py:242/308`, `utils/logging.py:110`, `utils/formatting.py:192/199/213`). Add at minimum a `logger.debug(..., exc_info=True)` so silent failures are diagnosable. Some of these (e.g. `header_bar.py:85/104`) are also Phase 4.5 NARROW targets — they get their log added as part of the NARROW fix, not double-touched here.
- **`stream.py:180` `logger.warning(..., exc_info=True)` → `logger.exception`** for consistency.
- **`player.py:387` and `auth.py:491` `logger.error(...)` no-traceback** — consider `logger.exception` for parser-failure diagnostics.

Mechanical, low-risk; each per-file commit reviews independently.

### Phase 4.5 — Trivial single-call NARROWs (82 sites — split into 6 sub-clusters)

Same shape across all 82 sites: single `query_one(selector) + one method call` (or single attribute read) wrapped in `except Exception:` with silent `pass` or a debug log. The expected exception is uniformly `textual.css.query.NoMatches` or a small known set (`AttributeError`, `RowDoesNotExist`/`CellDoesNotExist`, Textual reactive errors). Each sub-cluster commits separately for reviewability.

- **4.5a — Filter-show / hide / Escape trio across `ui/pages/` (12 sites):** `library.py:277/285/311`, `queue.py:408/416/454`, `liked_songs.py:317/325/365`, `context.py:546/554/586`. Near-identical `_show_filter` / `_hide_filter` / `on_key`-Escape blocks; one mechanical sweep.
- **4.5b — `get_nav_state()` cursor reads (4 sites):** `library.py:136`, `recently_played.py:153`, `liked_songs.py:233`, `search.py:490`. Single `query_one(table) + cursor_row` read; expected `NoMatches`.
- **4.5c — `on_mount` / `watch_*` reactive setters / single-widget query+act in `ui/pages/` (20 sites):**
  - `on_mount` initial-hide / restore-focus: `browse.py:412`, `browse.py:516`, `search.py:447`, `search.py:461` (4).
  - `watch_*` reactive setters: `help.py:265`, `context.py:232`, `context.py:240` (3).
  - Single-widget footer/loading update: `queue.py:257`, `liked_songs.py:187`, `search.py:783` (3).
  - Single-call focus / button-update / input apply_filter / focus in `context.py`: 460, 495, 561, 570 (4).
  - Single-call suggestion-hide: `search.py:612` (1).
  - Single-call descendant-search query_one: `search.py:955` (1).
  - Single-call cleanup nested-catch: `browse.py:175` (1).
  - Single-call `_show_error` display-toggle: `browse.py:459`, `browse.py:569` (2).
  - Single-call has_class check: `search.py:563` (1).
- **4.5d — Background-worker query+update sites in `ui/pages/` (7 sites):**
  - DataTable cell-update: `queue.py:178`, `queue.py:185` (2 — `RowDoesNotExist` / `CellDoesNotExist`).
  - TrackTable swap/append in workers: `context.py:363`, `context.py:385` (2).
  - Filter timer-stop: `queue.py:424`, `liked_songs.py:334` (2 — `AttributeError`).
  - `on_worker_state_changed` single-call: `context.py:224` (1).
- **4.5e — services + app trivial NARROWs (15 sites):** the pre-Task 1.6 candidates. `auth.py:329`, `spotify_import.py:69`, `player.py:481`, `_playback.py:387`, `_playback.py:601`, `_app.py:493`, `_ipc.py:218`, `_keys.py:189`, `_session.py:93`, `_session.py:102`, `_session.py:159`, `_sidebar.py:47`, `_sidebar.py:74`, `_sidebar.py:231`, `_track_actions.py:160`. Heterogeneous expected exception types per site (mostly `NoMatches`; `auth.py:329` and `spotify_import.py:69` are `(OSError, json.JSONDecodeError)` / `KeyError`-class; `player.py:481` is `(mpv.ShutdownError, OSError, AttributeError)`).
- **4.5f — `ui/` other widgets (24 sites):** `playback_bar.py:168/206/392/505` (4), `header_bar.py:85/104` (2), `ui/popups/spotify_import.py:422/612` (2), `ui/sidebars/lyrics_sidebar.py:249/403/410/464/513/522/531` (7), `ui/sidebars/playlist_sidebar.py:217/289/299/573/605` (5), `ui/widgets/track_table.py:279/286/320/459` (4). All `query_one + assign/method-call` or `cell-update` shapes; expected `NoMatches` / `RowDoesNotExist` / `AttributeError`.

Sub-cluster total: 12 + 4 + 20 + 7 + 15 + 24 = **82**. ✓

### Phase 4.6 — `app/_session.py:211` write-path NARROW + UX-toast (1 site)

Two-step fix in a single commit:
1. Narrow the broad-catch to `(OSError, TypeError)`. `OSError` covers the disk-full / permission-denied / EROFS modes; `TypeError` covers a track dict somehow becoming unserialisable by `json.dumps`.
2. On caught failure, also `self.notify("Could not save session state", severity="warning", timeout=5)` so the user knows their resume target is stale.

Bumped out of Phase 4.5 because it's both a NARROW *and* a UX-contract change — distinct shape from the trivial single-call sweep, deserves its own commit.

### Phase 5 — UI cascade updates following Phase 4 service-layer narrowings (~14 sites)

Specific call sites listed in the **Cascade map** above. Most stay KEEP-with-tightened-error-types or KEEP-with-better-notify-text once the upstream service narrows; the three `add_playlist_items` cascade sites in popups materially change behaviour (partial-add reporting). The `_call()` cascade is the largest: 9 background-fetch / async-render handlers across `_playback.py`, `_ipc.py`, `liked_songs.py`, `context.py`, `browse.py`, `search.py`, `playlist_picker.py`, and `playlist_sidebar.py`. Estimate **~14 sites total** once the cascade is fully traced — could grow if `remove_playlist_items` gets a UI call site before Phase 5 lands.

### Phase 4 + Phase 5 site-count summary

| Phase | Description | NARROW sites touched |
|---|---|---|
| 4.1 | `_call()` outer catch | 1 |
| 4.2 | `client` lazy-init lock | 0 (bundled) |
| 4.3 | Mutation methods + return-bool + cascade | 3 service + 5 UI = 8 |
| 4.4 | Logging-hygiene sweep | ~58 strict + ~17 priority/silent (no NARROW) |
| 4.5 | Trivial single-call NARROWs (a–f) | 82 |
| 4.6 | `_session.py:211` write-path + UX-toast | 1 |
| **Phase 4 NARROW subtotal** | | **92** (sums to >87 because 4.3 includes 5 UI cascade sites that are KEEP at the audit layer but get rewritten as part of the mutation cascade) |
| 5 | UI cascade updates after 4.1 / 4.3 land | ~14 |

Audit NARROW total reconciliation: 1 (4.1) + 3 service-layer (4.3) + 82 (4.5) + 1 (4.6) = **87** ✓.
