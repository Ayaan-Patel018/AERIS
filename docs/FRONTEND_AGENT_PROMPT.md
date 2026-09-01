# PROMPT FOR AI AGENT — AERIS Frontend: Real Data + Bug Fixes

*(Copy everything below into the AI agent. Attach the files listed at the bottom. Written to be self-contained.)*

---

## CONTEXT

AERIS (SIH 26168) frontend — React + TypeScript + Vite dashboard replaying a smartphone dead-reckoning navigation drive. **Critical history you must know:** this dashboard was originally built against synthetic/mock data (a sine-wave "velocity," hardcoded outage-window fractions that didn't match the real data, hardcoded status text). That has already been fixed once — `useTrajectoryData.ts`, `useGNSSStatus.ts`, `MapArea.tsx`, `TimelineSlider.tsx`, and `DashboardContext.tsx` currently read REAL backend data. **Do not reintroduce any hardcoded/synthetic values anywhere in this pass.** If you're unsure whether a number is real, check whether it's read from the JSON files in `src/data/` — if not, it's fake and must be fixed, not left alone.

## TASK 1 (highest priority) — Wire in the new 4th trajectory layer, real data only

The backend now also produces an **offline-smoothed** trajectory (RTS+ZARU post-processing) — a real, measured, better result than the real-time output, but it is NOT something a live phone could compute (it uses future information from after a GPS outage). It must be shown as a clearly separate, honestly-labeled 4th line — never merged with or replacing the existing real-time (`fused_output.json` / "AERIS FUSED") line.

**Files (already generated, real data, no fake values):**
```
backend/exports/frontend_data/ground_truth.json      (existing, unchanged)
backend/exports/frontend_data/gnss_only.json          (existing, unchanged)
backend/exports/frontend_data/fused_output.json       (existing, unchanged — the real-time line)
backend/exports/frontend_data/smoothed_output.json    (NEW — offline RTS+ZARU)
```
Copy all 4 into `frontend/src/data/`, replacing the 3 that exist there now and adding the 4th.

**Schema of `smoothed_output.json`** — identical shape to `fused_output.json` (`{x, y, t, status, uncertainty, velocity, heading}[]`, same length, same time-alignment — already handled by the backend adapter, do not re-derive it).

**Steps:**
1. In `useTrajectoryData.ts`: import `smoothed_output.json` the same way `fused_output.json` is imported; expose `smoothed` and `currentSmoothedPos` the same way `fused`/`currentFusedPos` already work.
2. In `DashboardContext.tsx`: extend the `Layers` interface with a `smoothed: boolean` field (default `false` — off until the user opts in, so the primary demo view isn't cluttered).
3. In `MapArea.tsx`: draw the smoothed trajectory as a 4th `drawTrajectory()` call, gated on `layers.smoothed`, in a distinct color not already used (existing: gt=`#26262B`, gnss=`#2DD4BF`, fused=`#F0801E` — pick something clearly different, e.g. a gold/purple, not a shade of the existing three).
4. Add a toggle for it in the Legend & Layers panel, labeled exactly: **"Offline Smoothed (Analysis)"** — not "AI Enhanced," not "Improved," not anything that could sound like a live capability.
5. When the smoothed layer is toggled on, show a small persistent caption near it: *"Post-processed using the complete recorded drive — not available to a live system."* This is the single most important line in the whole UI for judge credibility; do not omit or paraphrase it away.

## TASK 2 — Fix ChartsPanel visibility (can't see it fully at the bottom)

The charts panel (position error / velocity charts) is being cut off / not fully visible in the current layout. Diagnose and fix:
- Check if the panel's container has a fixed height with `overflow: hidden` clipping content that needs `overflow-y: auto` instead, or if it needs a scrollbar
- Check if it's being pushed off-screen by other bottom-bar elements (`BottomBar.tsx`, `TimelineSlider.tsx`) — may need a flex/grid layout adjustment so the charts panel gets guaranteed visible height regardless of window size
- Test at a few window sizes/resolutions, not just one — this needs to work reliably during a live demo, which might be on an unfamiliar projector/resolution

## TASK 3 — Fix layer toggle / button association bugs

Reported symptom: disabling the "AERIS FUSED" layer toggle doesn't cleanly stop things from moving/updating as expected — some buttons feel wrongly associated with unrelated state, and layer visibility is tangled with outage simulation state.

**Diagnosis approach:** in `MapArea.tsx` and `DashboardContext.tsx`, trace every place `layers.fused`, `layers.gnss`, `layers.gt` are read. There is likely coupling where the "current position marker" logic silently falls back between layers in a way that doesn't match what a user expects when toggling a layer off (e.g., disabling "fused" makes the marker jump to reading `gnss` position instead of just disappearing). Decide the correct behavior explicitly: **when a layer is toggled off, both its trajectory line AND anything derived from it (marker, uncertainty circle) should hide — don't silently substitute another layer's data without the user asking for that.** Fix the fallback logic to be explicit and predictable, not implicit.

## TASK 4 — Regression-test the GNSS status logic (already fixed once — verify it still holds)

`DashboardContext.tsx` and `useGNSSStatus.ts` were already fixed for a specific bug: the manual "Simulate Outage" button was showing "SIGNAL LOST — 0.0s elapsed, drift 0.000" (fighting the real recorded status), and "GNSS REACQUIRED" was appearing at the very start of playback before any real outage. The fix added a `manualOutageStart` tracked in context and a `REACQUIRED_WINDOW` bound.

**Do not undo this fix while doing Tasks 1-3.** After your changes, explicitly re-test:
1. Click Play from t=0 — status should read "GNSS AVAILABLE," not "REACQUIRED"
2. Click "Simulate Outage" mid-playback — the Outage Timer must count up from 0 in real-time, not stay frozen
3. Click "Cancel Outage" — status should return to reflecting the real recorded data at that timeline position, not get stuck
4. Confirm the heading readout shows one decimal place (e.g. `168.6°`), not a long floating-point string

## FILES TO GIVE THE AGENT
1. `frontend/src/hooks/useTrajectoryData.ts`
2. `frontend/src/hooks/useGNSSStatus.ts`
3. `frontend/src/context/DashboardContext.tsx`
4. `frontend/src/components/dashboard/MapArea.tsx`
5. `frontend/src/components/dashboard/ChartsPanel.tsx`
6. `frontend/src/components/dashboard/StatusPanel.tsx`
7. `frontend/src/components/dashboard/TimelineSlider.tsx`
8. `frontend/src/components/dashboard/BottomBar.tsx` (for Task 2's layout diagnosis)
9. The 4 JSON files in `backend/exports/frontend_data/` (for schema reference)

## VALIDATION — how this gets accepted
1. `npm run dev`, no console errors
2. All 4 layers toggle independently and correctly, with no unexpected coupling
3. Charts panel fully visible without scrolling issues at normal window size
4. Task 4's 4-point regression check all pass
5. Deliver a short screen recording (15-20s at 1x speed) showing the new 4th layer toggled on next to the existing 3
