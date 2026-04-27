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

(filled in by Task 1.2)

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
