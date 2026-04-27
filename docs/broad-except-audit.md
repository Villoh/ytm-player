# Broad `except Exception:` audit — 2026-04-28

**Status:** In progress.
**Total sites:** 263 across `src/ytm_player/`.

## Executive summary

(filled in at end of audit)

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
| 86 | `_load_theme_toml()` — wraps `path.stat()` + `open(path, "rb")` + `tomllib.load(f)` for `~/.config/ytm-player/theme.toml` | KEEP | Optional user theme override; missing file, malformed TOML, or unreadable file should silently return `{}` so the default theme applies. Bare `pass`-equivalent (`return {}`) is the contract — theme load must never crash startup. Could be marginally narrowed to `(OSError, tomllib.TOMLDecodeError)` but the function is on the cold-startup path and a wider net is defensible. Soft logging-hygiene note: no log at all here — Phase 4 sweep candidate (add `logger.debug(..., exc_info=True)` so a malformed TOML is at least diagnosable). |
| 347 | `_apply_toml_theme()` — wraps the full `ThemeColors(...)` construction + `_apply_toml_overrides()` + `set_theme()` + reactive assignment chain | KEEP | Theme application from user TOML; failure must fall back to the default theme silently. `pass` on failure is correct. Same logging-hygiene note as line 86 — silent swallow on a cold-startup path. Phase 4.4 sweep should add at minimum a debug log. |
| 419 | `on_mount()` — wraps `YTMusicService(...)` + `Player()` + loop bind + `StreamResolver(...)` + `HistoryManager.init()` + `CacheManager.init()` block | KEEP | Outer service-init net. Logs with `logger.exception` (correct), notifies the user with the actual error string, and schedules `self.exit()` after 2 s. Failure here is genuinely fatal (no DB, no cache, no API) — exiting cleanly is the right contract, broad catch is justified because we don't know which service raised. |
| 493 | `on_mount()` — wraps `query_one("#app-header", HeaderBar).set_lyrics_dimmed(True)` for the initial dim state | **NARROW** | Single-call try block, identical pattern to `_playback.py:387` (already flagged in Task 1.4). Expected failure is `textual.css.query.NoMatches` if the header isn't mounted yet during early `on_mount`. Silent `pass` with NO log hides any real bug in `set_lyrics_dimmed` (e.g. a refactor breaks the method). Should narrow to `NoMatches` and add at minimum a debug log. Bundle into Phase 4.5 (trivial single-call narrows). |
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
| 159 | `_save_session_state()` — wraps single `volume = self.player.volume` property read | **NARROW** | Single-line try block on a single attribute access. Expected failure is `mpv.ShutdownError` (mpv died mid-shutdown) or similar bridge-level error. Falls back to `volume = 80` (the default). Silent debug log is fine, but the broad catch is wider than needed — should narrow to the mpv-bridge exceptions. Bundle into Phase 4.5. |
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
| 136 | `_open_actions_for_track._rate()` — wraps single `await ytmusic.rate_song(vid, r)` for the actions popup's `toggle_like` branch | KEEP at this layer | Cascade with `services/ytmusic.py:383` (`rate_song`, already flagged NARROW in Task 1.2 / Phase 4.3). Once `rate_song` returns `bool` and propagates expected error types, this catch can be tightened to branch per-error-type. Currently `rate_song` always returns `None` even on failure, so this catch is the only signal a failure happened — broad-catch + user-visible notify is the correct downstream contract until Phase 4.3 lands. Soft logging-hygiene note: NO `logger.exception` here at all — silent except for the user-visible toast. Phase 4.3 should add a `logger.exception` so the underlying error is in the log too. |
| 160 | `_refresh_queue_page()` — wraps `query_one(QueuePage)` + `_refresh_queue()` for the optional refresh after add-to-queue / play-next | **NARROW** | Single-call-pair try block. Expected failure is `textual.css.query.NoMatches` when the queue page isn't currently mounted (refresh is best-effort — only useful when the queue page is the active page). Silent `pass` with NO log; classic pattern. NARROW to `NoMatches` and add a debug log. Bundle into Phase 4.5. |
| 182 | `_start_radio_for()` — wraps `normalize_tracks(await self.ytmusic.get_radio(video_id))` | KEEP | Radio start is user-visible; logs with `logger.exception` (correct) and notifies the user with `severity="error"`. The underlying `get_radio` is a service-layer KEEP (returns `[]`), so this outer catch is for downstream — `normalize_tracks` raising on a malformed response, or any other unexpected failure. Correct user-facing contract. |

**Summary for app/ other (35 sites):** 24 KEEP, 11 NARROW, 0 PROMOTE. Notable findings:

- **One brand-new high-priority NARROW candidate not yet in any Phase 4 task — and it's a mutation/write path** (matches the pattern Task 1.5 was specifically asked to look for):
  - **`_session.py:211`** (`_save_session_state` outer write catch). Silent loss of the user's queue / current-track / resume position on failure to write `session.json` — the user has no signal anything went wrong unless they tail the log file. Two-step fix in Phase 4: narrow to `(OSError, TypeError)` and add a `self.notify("Could not save session state", severity="warning", timeout=5)` so users know their resume target is stale. Recommend a new dedicated Phase 4 task ("Phase 4.6: session-write failure visibility") rather than rolling into 4.5, because it's both a NARROW *and* a UX-contract change.
- **Six new "trivial single-call NARROW" candidates that fold into Phase 4.5 (currently `auth.py:329`, `spotify_import.py:69`, `player.py:481`, `_playback.py:387`, `_playback.py:601`):**
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
  - All eleven follow the same shape: single-call/single-line try block, expected exception type is obvious (`NoMatches`, mpv `ShutdownError`, or a Textual reactive error), silent `pass` with NO log, fix is a 2-line edit.
- **One cascade observation cross-referencing Phase 4.3:**
  - `_track_actions.py:136` is the secondary call site for `ytmusic.rate_song` (the primary is `_playback.py:558`). Once Phase 4.3 narrows `rate_song` and switches to `bool`, both call sites should be tightened together — the current `_track_actions.py:136` site doesn't even log the exception, only shows a user toast. Phase 4.3 should explicitly cascade here.
- **Logging-hygiene drift (Phase 4.4 sweep candidates):** 11 sites use `logger.debug(..., exc_info=True)` instead of `logger.exception`, against CLAUDE.md guidance. Lines: `_app.py:501` (`_app.py` line 500's catch logs at 501), `_app.py:571`, `_navigation.py:143`, `_navigation.py:201`, `_session.py:30`, `_session.py:77` (multi-line debug call), `_session.py:146`, `_sidebar.py:43`, `_sidebar.py:60`, `_sidebar.py:70`, `_sidebar.py:85`, `_sidebar.py:159`, `_sidebar.py:177`. Plus 5 silent-pass-no-log sites that are also in the 11 NARROW candidates above (`_app.py:493`, `_keys.py:189`, `_session.py:93`, `_session.py:102`, `_sidebar.py:47`, `_sidebar.py:74`, `_sidebar.py:231`, `_track_actions.py:160`) — those get their log added as part of the NARROW fix, not the sweep.
- **Two log-only-no-traceback offenders:**
  - `_app.py:86` and `_app.py:347` — silent swallow with NO log at all on the theme TOML load + apply paths. Phase 4.4 should add a `logger.debug(..., exc_info=True)` so a malformed user theme TOML is at least diagnosable.
- **All multi-call outer-catch sites confirmed KEEP:** `_app.py:419` (service init), `_ipc.py:102` (IPC dispatch outer), `_sidebar.py:141`/`259`/`288` (user-visible mutations), `_track_actions.py:182` (radio start). Each follows the established pattern — `logger.exception` + `self.notify(...)` for the user-visible cases, exit-with-toast for the genuinely fatal init case.

### `ui/pages/` (73 sites)

(filled in by Task 1.6)

### `ui/` other files (46 sites) + `utils/`/`cli.py`/`ipc.py` (10 sites)

(filled in by Task 1.7)

## Cross-cutting observations

(filled in by Task 1.8)

## Cascade map (UI handlers depending on service contracts)

(filled in by Task 1.8)

## Phase plan derived from this audit

(filled in by Task 1.8)
