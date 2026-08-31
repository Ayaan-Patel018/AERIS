# Frontend Integration — Status & History

Tracks the gap between what the frontend UI displays and what's actually real backend data. Read this before touching any hook or data file in `frontend/`.

## How this started

Aryan built the entire dashboard UI (`MapArea`, `TimelineSlider`, `ChartsPanel`, `MetricsPanel`, `StatusPanel`, playback controls, landing page) **before the backend's real exports were wired in** — a completely standard frontend-first pattern (build the UI shell against plausible-looking fake data, wire real data in later). The problem: it wasn't flagged as temporary anywhere, so "is the frontend done" looked like a yes/no question when it was actually "the UI shell is done, the data underneath is 100% synthetic."

What was fake, discovered by reading the actual hook code:
- `frontend/src/data/*.json` — `{x, y, t}` point arrays that were placeholder-generated, not real backend exports. Also used the old `ground_truth.json` filename (we'd already renamed this to `reference_trajectory.json` weeks earlier in the backend schema — see DATASET.md — so this was already drifted from the real contract).
- `useGNSSStatus.ts` — every value was a formula based on playback position, not real EKF output: `currentVelocity = 33 + Math.sin(progress * 22) * 9` (literally a sine wave), `confidence`/`drift`/error values were hand-picked arithmetic, `OUTAGE_START = 0.35` / `OUTAGE_END = 0.65` were guessed constants that didn't match our real outage window at all.

## Why Aryan's files needed changing (not just the data)

Two structural bugs in the existing UI code, found while reviewing before wiring real data in:
1. **Index misalignment risk:** `useTrajectoryData.ts` computed one shared index from `gt.length` and used it to index into `gnss[]` and `fused[]` too, assuming all three arrays are the same length. In our real backend schema they're not (`gnss_only` is far sparser than `reference_trajectory`/`fused_output` since raw phone GPS updates ~1 Hz vs. the EKF's 10 Hz). Fixed by building an adapter that aligns all three onto one shared time grid before export, rather than changing the indexing logic itself.
2. **Array `[-1]` crash risk:** `MapArea.tsx`'s heading calculation did `fused[currentIndex - 1]` with no bounds check — at playback start (`currentIndex = 0`) this reads index `-1`, returns `undefined` in JS, and the next line crashes. Real bug, not just a lint nitpick — would have broken the demo the instant someone hit play from the start.

## What actually changed

**Backend (new file):** `backend/export_frontend_data.py` — reads the already-tested, frozen `outage_60s` exports and reshapes them into the `{x, y, t}` point-array format the frontend's existing code expects, in **ENU metres** (not lat/lon degrees — the map is a custom canvas renderer, not Leaflet, so any consistent coordinate system works since it auto-fits a bounding box). Aligns all three arrays to `fused_output`'s time grid so index-based access across `gt`/`gnss`/`fused` is safe. Embeds real `status`/`uncertainty`/`velocity`/`heading` directly onto each `fused_output` point.

**Frontend (rewritten):**
- `useGNSSStatus.ts` — now reads real per-point `status`/`uncertainty`/`velocity`/`heading` from `fused_output.json` instead of formulas. `isOutage` is derived from the real `status` field, not a hardcoded fraction comparison.
- `useTrajectoryData.ts` — extended `TrajectoryPoint` interface with the new optional real-data fields; indexing logic unchanged (now safe because the adapter guarantees equal-length aligned arrays).

**Frontend (small patches to Aryan's files, not rewrites):**
- `MapArea.tsx` — 3 one-line changes: outage-start detection reads real `status` instead of a hardcoded time fraction; `prev[-1]` crash guarded with a null check; uncertainty-circle draw calls guarded against undefined points.
- `TimelineSlider.tsx` — time label format fixed (`formatTime()` helper) since it hardcoded `"0:XX / 1:00"` assuming a 60-second total; real duration is 681.1s (~11 min).

## Bugs found and fixed during this pass (chronological, for the record)
1. Missing `aerisError`/`gnssError` exports after first `useGNSSStatus.ts` rewrite → MapArea broke (9 TS errors)
2. `node_modules` never installed locally → 9 more errors, unrelated to any of our code (fixed with `npm install`)
3. Missing `OUTAGE_START`/`OUTAGE_END` exports → `TimelineSlider.tsx` crashed (blank page)
4. Missing `TOTAL_DURATION` export → same file, second crash
5. Missing `outageTime`/`drift` exports → `StatusPanel.tsx` broke
6. **Real bug, not a crash:** `currentVelocity` was in m/s (backend units) but displayed with a `"km/h"` label unconverted — now multiplied by 3.6 in the hook
7. **Real bug, not a crash:** `currentHeading` could be negative (EKF's `arctan2`-based heading, range -180°→180°) but the UI expects a 0°–360° compass bearing — now normalized

## Still fake — flagged, not yet fixed (don't forget these before the demo)
- **`ChartsPanel.tsx`'s velocity chart** — still a sine wave (`33 + Math.sin(...)`). The position-error chart in the same panel IS real (computed directly from aligned real x/y arrays), so this is the one visibly inconsistent panel left — a sharp judge comparing the two charts could ask why one looks like real telemetry and the other doesn't.
- **`MetricsPanel.tsx`'s "VEL ERROR"** — hardcoded static text `"0.4 m/s"`, not connected to any hook.
- **`StatusPanel.tsx`'s "SATELLITES"** — hardcoded `'11'` / `'0'`, not real satellite count (we do have real `gps_satellites` data in the backend, just not currently carried through the adapter into the exported points).

## Next phase (once the current fix is confirmed working)
Go through the 3 remaining fake spots above and wire them to real data, the same pattern as everything else here: extend `export_frontend_data.py` to carry the additional real fields through, then update the specific hook/component that reads them. No new architectural decisions needed — same playbook, just more fields.
