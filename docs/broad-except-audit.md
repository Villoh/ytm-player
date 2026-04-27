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
| 86 | `play_track()` — wraps `await self.cache.get(video_id)` for local audio cache lookup | KEEP | Best-effort cache hit check; falls back to yt-dlp resolution on any error. The cache is a `CacheManager` over SQLite + filesystem — a wide failure surface (DB lock, disk error, missing file). Returns `None` so the resolver path runs. Same logging-hygiene note. |
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
| 601 | `_download_track()` — wraps `await self.cache.put_file(video_id, result.file_path, fmt)` to index a downloaded file in the audio cache | **NARROW** | The expected failure modes are `OSError` (file disappeared, perms) and `aiosqlite`/SQLite errors (`sqlite3.Error`). Catching `Exception` here silently hides bugs in `put_file` itself (e.g. a refactor breaks the signature) — the user sees "Downloaded: X" success but the file never gets indexed. Should narrow to `(OSError, sqlite3.Error)` and at minimum upgrade to `logger.exception` so silently-unindexed downloads are diagnosable. |

**Summary for app/_playback.py (27 sites):** 25 KEEP, 2 NARROW, 0 PROMOTE. Notable findings:

- **Two NARROW candidates not in current Phase 4 plan:**
  - **Line 387** (`_on_track_change` — header un-dim): single-call try block with the obvious expected exception type (`textual.css.query.NoMatches`) and a silent `pass` with NO log. Fits cleanly into Phase 4.5 (trivial single-call try blocks). Worst offender of the silent-swallow pattern in this file.
  - **Line 601** (`_download_track` — cache indexing of completed download): swallows `OSError`/`sqlite3.Error` silently, breaking the contract that successful downloads are findable in the cache. User sees "Downloaded: X" but a re-play hits yt-dlp instead of the local file. Bundle into Phase 4.5 or a small new "download-pipeline reliability" task. The download init/UI path itself is not broken, but the post-download indexing step's silent-failure is genuinely user-visible (silently degraded cache hit rate).
- **Indirect cascade with `services/ytmusic.py` line 383 (rate_song NARROW):**
  - Line 558 (`_toggle_like_current`) is the primary call site for `rate_song`. When Phase 4.3 narrows `rate_song` and switches it to return `bool`, the catch here can be tightened to a per-error-type branch (e.g. auth error → "Sign in again", network error → "Check connection", success → flip the heart). Currently the broad catch + notify shows the same "Couldn't update like state" message for every failure mode.
- **Logging-hygiene drift (Phase 4.4 sweep candidates):** 14 of the 27 sites use `logger.debug(..., exc_info=True)` rather than `logger.exception`, against CLAUDE.md guidance ("For caught exceptions you want to surface in bug reports, use `logger.exception` — *not* `logger.debug(..., exc_info=True)`, which silently routes to debug level"). Lines: 78, 86, 111, 153, 187, 324, 338, 373, 380, 397, 411, 417, 443, 451, 574. The `logger.exception` sites (295, 344, 350, 361, 461, 471, 493, 511, 531, 558) are correctly leveled and serve as the in-file template for the sweep. Line 387 is the worst offender — silent `pass` with no log at all.
- **All optional-service fan-out sites confirmed KEEP:** MPRIS (344, 461), macOS Now Playing (350, 471), Discord RPC (493), Last.fm (361). Each follows the pattern from Task 1.2/1.3 — independent subscriber failure must not crash playback. The `logger.exception` usage on these sites is already correct.

### `app/` other files (35 sites)

(filled in by Task 1.5)

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
