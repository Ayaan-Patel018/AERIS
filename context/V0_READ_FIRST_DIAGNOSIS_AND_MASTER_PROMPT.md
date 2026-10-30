# V0 — Read first: diagnosis, rules and master prompt (v3)

This pack **extends** the R1–R6 redesign. It fixes four things the latest build still gets wrong:

1. The map is light and cluttered. It must be **dark**, match the app theme, and run on **Mapbox**.
2. The map **can't be touched or zoomed**.
3. The map moves **shakily**, and the trip line **jitters and lags** during playback.
4. The app **isn't useful enough or self-explanatory enough**. Buttons are unclear, and a navigation app's basic jobs are missing or hard to find.

Files in this pack:

| File | Covers |
|---|---|
| V0 (this) | Diagnosis, overrides of earlier files, token handling, rules, kickoff prompt |
| V1 | Mapbox setup, dark/day theme with the Standard style, layers, attribution, terms and privacy |
| V2 | Why touch fails, a single camera owner, gesture settings, bottom-sheet rules, touch tests |
| V3 | Smooth trip playback: no jitter, no lag, no shaky camera; frame budget and measurements |
| V4 | Functionality and controls: every button, every flow, Mapbox Search and Directions, navigation |
| V5 | Phases, acceptance tests, performance numbers, verification report |

## 1. What the latest screenshot shows

Read these as symptoms to confirm in code, not as proven causes.

| Seen | Likely meaning | Where it is handled |
|---|---|---|
| Light map with restaurants, hotels, school, shop icons | The Night style from R2 is not in use. A default light style with all POIs is loaded. | V1 |
| Layers button looks like a menu (three lines) | Wrong icon. Users will expect a menu, not a map-layers sheet. | V4 §3 |
| Chip row sits on top of map labels | Chips have no scrim or background. Labels collide and chips are hard to read. | V1 §6, V4 |
| Both drive cards say "No satellite loss" | The adapter may not map the export's real status values (earlier findings: the committed export marks loss as `unavailable`, not `outage`). Check this against the real export. A card that always says "no loss" is a wrong claim. | V5 §3 |
| Map won't pan, zoom or rotate | See V2. The usual causes are a full-screen overlay eating touches, a modal sheet scrim, or code that keeps setting the camera. | V2 |
| Map moves shakily | Two writers fighting over the camera, or raw heading or position feeding the camera every frame. | V2, V3 |
| Trip line jitters and lags | The whole line is probably rebuilt and re-uploaded every frame, and the vehicle moves in 1 Hz jumps. | V3 |

## 2. What this pack overrides in earlier files

| Earlier file | Old instruction | New instruction |
|---|---|---|
| M01–M10, R2 | MapLibre, OpenFreeMap, style script | **Mapbox Maps SDK for Android v11** (V1). Delete the style-generation script plan. Keep the R2 palette and rules as the design target. |
| R3 | Photon and Nominatim for search | **Mapbox Search Box API** (V4 §5) |
| R4 §1, §5 | OSRM and hand-written maneuver text | **Mapbox Directions API**, using the banner and voice instructions it returns (V4 §6). Guidance logic (progress, reroute, honest satellite-loss) stays as in R4. |
| R6 §3.4 | Remove zoom +/− on compact widths | **Show zoom buttons by default** (setting "Zoom buttons"), until V2's gesture tests pass on a real phone. Then the default may be switched off. |
| R5 §3.4 | Controls row has nothing else | Add small **Previous moment / Next moment** buttons on the moment row (V4 §4). Visible beats hidden gestures. |
| M01, R1 privacy | Everything stays on the device | Update the wording. See §4. |

Unchanged: the R1 concept (Explore / Trips / Record, `PositionSource`), R5 trip structure, colour meanings, typography, and every honesty rule below.

## 3. Mapbox token: how to handle it

The token you pasted is a **public** token (it starts with `pk.`). Mapbox designs these to ship inside apps, so the app needs it. It is still a secret in practice: anyone who finds it can spend your quota.

- **Never write the token into any committed file**, including docs, tests and this pack. In all files refer to it as `MAPBOX_ACCESS_TOKEN`.
- Put it in `local.properties` (git-ignored), read it in Gradle into `BuildConfig`, and set it at runtime (V1 §2). CI reads it from an environment variable.
- Add a repo check that fails the build if a string starting `pk.eyJ` appears in tracked files.
- In the Mapbox dashboard, make a **separate token for this app** with only the scopes it needs, and use a different one for release. Look at whether the dashboard offers restrictions that work for a mobile app. I could not confirm that URL restrictions apply to Android, so don't rely on them.
- Because it appeared in a chat, **rotate it before any public demo or release**.
- Never log the token. Strip it from URLs in error messages and crash reports.

## 4. What leaves the device now

With Mapbox the app is no longer fully offline. Be exact in the privacy screen and in `README`:

- **Leaves the device:** map tile requests (these reveal the area on screen), search text with an approximate location bias (rounded to about 1 km), and the start and end points of a route when the user asks for directions.
- **Never leaves the device:** recorded sensor data, AERIS tracks, the reference track, trip metrics, saved places and drive history.
- Don't send AERIS or reference tracks to any Mapbox API (including Map Matching). It would break the honesty rule below and the privacy promise.
- Mapbox's SDK may send usage telemetry. Find out what it sends and how to switch it off in the current docs, and report it. The app's promise is no analytics, so the default must match that, or the privacy text must say otherwise.

## 5. Honesty rules (unchanged, repeated so they travel with this pack)

- No fabricated telemetry. Unknown shows "—", never 0.
- Reference (VBOX) data is never an input and is hidden by default. When shown it carries the label "Reference — not used by AERIS" and the persistent "Reference shown" chip.
- The AERIS path is the honest export. **Never snap it to roads, never map-match it, never smooth the drawn path geometry.** Smoothing in V3 applies only to how the camera and marker move between recorded frames.
- Metrics come from `metrics.json` with provenance and a "Tuned on this drive" or "Held-out drive" chip.
- No superlatives ("centimetre-level", "survey-grade", "zero drift", "better than GPS").
- Mapbox traffic, ratings or speed limits appear only where Mapbox returns them, labelled with their source. No invented ratings or "less traffic" notes.
- Marker snapping to the route is allowed only in Navigating with phone GNSS, never for AERIS tracks.
- `backend/` and `ins_ekf.py` are read-only for UI work.

## 6. Working method

1. **Verification report first, no feature code.** Do V5 §6 and send it. This includes confirming which map SDK the app uses today and reproducing the touch bug on a real phone.
2. One phase at a time (V5 §1). After each phase: tests, screenshots at 360 × 800 dp in Night and Day, performance numbers, and wait for approval.
3. Test smoothness and touch on a **real phone in a release or profile build**, not in a debug build or the emulator. Debug Compose builds are slow enough to look like jitter.
4. When a name in this pack doesn't exist in the Mapbox version you resolve, trust the SDK's own reference over this pack, and tell me what you changed.

## 7. Kickoff prompt (paste this into Antigravity)

```
You are continuing work on the AERIS Android app (Kotlin, Jetpack Compose). Read every file in
aeris-mobile-v3-mapbox/ (V0–V5) and the earlier aeris-mobile-redesign-v2/ (R1–R6), then do the
following IN ORDER. Do not write feature code until step 1 is approved.

1. Send the verification report from V5 §6: what map SDK is used today, where the camera is
   written, which overlays cover the map, how touches reach the map, how the trip line and
   vehicle marker are updated per frame, and the result of loading the real exports (do drives
   with outages report them?). Reproduce the touch bug and the jitter on a real phone and
   record frame metrics.
2. Phase M0–M7 from V5 §1, one phase at a time, stopping for my approval after each.

Hard rules: Mapbox token is MAPBOX_ACCESS_TOKEN from local.properties — never write it into any
tracked file. The AERIS path is never snapped, map-matched or smoothed in its geometry. Reference
data stays hidden by default and is never an input. No analytics. backend/ and ins_ekf.py are
read-only. The map must be dark in Night and light in Day, with POI clutter removed. The camera
has exactly one writer. Everything on the screen must have a visible label or a long-press tip.
Report differences from these files instead of silently deviating.
```
