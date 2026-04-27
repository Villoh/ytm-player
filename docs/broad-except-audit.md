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

(filled in by Task 1.3)

### `app/_playback.py` (27 sites)

(filled in by Task 1.4)

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
