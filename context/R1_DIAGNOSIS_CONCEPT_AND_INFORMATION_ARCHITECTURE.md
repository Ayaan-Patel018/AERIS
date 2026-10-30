# R1 — Diagnosis, concept and information architecture

> **Kickoff for the coding agent (paste first):**
> The files `R1`–`R6` in `/docs/mobile-ui-v2/` redesign the current app. **Where they conflict with the earlier `M01`–`M10` files, R1–R6 win.** Everything else in M01–M10 (honesty rules, tokens, data adapter, privacy, accessibility) still applies.
> `00_VISUAL_REFERENCE_MOCKUP.png` is the visual target. Match its structure, colours and hierarchy; do not copy its placeholder numbers.
> Before writing code: do the verification report from M10 §A **plus** R6 §6. Then show me a build plan. One phase at a time; commit and push after each; send screenshots next to the mockup.

---

## 1. What is wrong with the current screen

From the screenshot of the current build:

| # | Problem | Why it hurts |
|---|---|---|
| 1 | **Media-player vocabulary.** Full-width scrubber, a big play button, `11:21 / 11:21`, a `2.0×` button. | The first thing anyone sees is a video player. A navigation app shows *where you are and what is next*, not a timeline. |
| 2 | **Two clocks disagree.** The scrubber is at the very end (`11:21 / 11:21`) while the status card says `00:01 / 11:21`. | Looks broken. There must be exactly one playback clock (M07 §1). |
| 3 | **Light grey map on a dark app.** Two visual systems on one screen; the map is the loudest thing and fights the data. | The basemap must be designed *for* the theme (R2). |
| 4 | **The sheet covers about 45% of the screen** and the vehicle marker sits on its edge, half hidden. The route disappears under it. | The thing you are tracking must stay visible. |
| 5 | **No way to go anywhere.** No search, no places, no destination, no route. | It cannot behave like a navigation app. |
| 6 | **Control clutter.** `Dash` and gear as floating pills, zoom +/−/layers stacked and clipped by the sheet, a scale bar colliding with the status bar. | Controls have no hierarchy or home. |
| 7 | **ALL-CAPS labels** (`SPEED`, `HEADING`, `UNCERTAINTY (1σ)`). | Breaks the design rules in M02; reads as a template. |
| 8 | **`±0.1 m` uncertainty one second in.** | A one-second-old filter cannot know its position to 10 cm. This is probably the filter's initial covariance. Showing it destroys trust. See R6 §3. |
| 9 | **`291° W`.** | 291° is west-north-west. The cardinal conversion is wrong. See R6 §3. |
| 10 | **"Reference shown" chip is visible.** | The reference track must be off on every cold start (M01 rule 2). Confirm it was toggled on by hand and is not a default or a persisted setting. |

## 2. The concept: a drive-first navigation app

Three ideas:

**A. One position, many sources.** The navigation interface does not care where the position comes from. It consumes a `PositionState` and a `SignalState`. Sources:

| Source | Status | Used by |
|---|---|---|
| `PhoneGnssSource` | Build now (real phone satellite fixes) | Explore, Navigating |
| `TripPlaybackSource` | Build now (recorded AERIS output, played back) | Trip playback |
| `AerisLiveSource` | **Not built** (the filter is Python). Interface exists; the UI shows it disabled. | Future |

```kotlin
data class PositionState(
    val lat: Double, val lon: Double,
    val headingDeg: Double?, val speedMps: Double?,
    val sigma: Sigma?,               // 1σ ellipse if the source provides one
    val signal: SignalState,         // Locked, Lost, Searching, Unknown
    val source: SourceKind,          // PhoneGnss, TripPlayback, AerisLive
    val tSeconds: Double?,           // only for playback
)
interface PositionSource { val state: StateFlow<PositionState?> }
```

The same driving screen renders all of them. That is why playback can feel like driving instead of a video: it is the *same screen*, fed by a recorded source and labelled as such.

**B. Trips, not clips.** A recorded drive is a *trip*: a path with a summary and *moments* (satellite lost, turn, stop, satellite back). You open a trip, press **Play trip**, and watch it as a drive session. Seeking is by tapping a moment or dragging a slim progress rail. There is no full-width media scrubber on any default screen.

**C. Honest by construction.** A genuine navigation app has search, directions and guidance. We build those for real, using the phone's own satellite position and open map data. AERIS itself runs on recorded drives today, so AERIS output appears only in Trips and is always labelled "Playing recorded drive." We never present a recorded AERIS track as live navigation. When the filter is ported to the phone, `AerisLiveSource` slots into the same screen.

## 3. Information architecture

Bottom navigation, three tabs (NavigationRail on large screens):

| Tab | Purpose | Spec |
|---|---|---|
| **Explore** (home) | Map, search, places, saved, recent drives, "where satellites were lost" layer | R3 |
| **Trips** | Recorded and exported drives; trip detail; Play trip | R5 |
| **Record** | Capture a drive's raw sensors for AERIS (M08) | M08 (unchanged) |

Entry points from Explore: search → place → **Directions** → route preview → **Start** → Navigating (R4). From Trips: trip → **Play trip** → Trip playback (R5). Settings opens from the gear inside the search pill (Explore) and from the Trips toolbar. **Library is removed as a tab:** its content moves into Trips; import and storage management move to Trips ▸ overflow menu.

```
Splash ─► Onboarding (first run) ─► Explore
Explore ─ search ─► Results ─► Place ─► Directions ─► Route preview ─► Navigating ─► Arrival
Trips ─► Trip detail ─► Play trip ─► Trip playback ─► Trip finished
Record ─► Recording ─► Recording review ─► (appears in Trips as "Recorded, not yet processed")
```

## 4. Design principles for this redesign

1. **The map is the home screen and the loudest thing is always data.** Basemap is quiet and themed (R2); AERIS cobalt, amber and teal appear nowhere in the basemap.
2. **Sheets never hide the subject.** Camera padding always keeps the vehicle or route start in the visible map area (M05 §1).
3. **One primary action per screen.** Explore: search. Place: Directions. Route preview: Start. Trip detail: Play trip. Playing: Pause.
4. **Words over widgets.** Plain-language labels ("Satellite signal lost"), sentence case, no media jargon.
5. **Honest labels, quietly.** "Playing recorded drive" is a small persistent chip, not a banner. "Satellite fix" is always visible while a source is active.
6. **Colour meaning is fixed.** Cobalt = AERIS/route. Amber = dead reckoning / satellite lost. Teal = satellite fix. Slate = reference/baseline/alternatives. Red = errors only. Do not reuse teal or amber for decoration (for example, the arrival time uses `ink`, not teal).
7. **No fake precision.** Numbers use the formatting rules in R6 §3.

## 5. What to remove from the current build

- Full-width scrubber and large round play button as the default Replay UI.
- `mm:ss / mm:ss` as primary text (time may appear as secondary text; distance is primary).
- Floating `Dash` and gear pills on the map (Dash moves into Trip playback's overflow; gear moves into the search pill).
- Zoom +/− buttons on phones (gestures only; keep on Expanded width).
- The scale bar on the playback screen (show it only while pinching, like other maps).
- ALL-CAPS labels.
- The tall stats sheet that hides the marker.

## 6. Where AERIS stands out (the differentiators, all real)

- **Satellite-loss awareness on a normal navigation app:** a signal chip that is honest about satellites, with an amber state.
- **Where satellites were lost:** an optional Explore layer and a route-preview hint built from the user's own recorded drives (R3 §6, R4 §3). These are computed from stored outage windows, not invented.
- **The confidence corridor** during outages in Trip playback (R5 §3).
- **Results with provenance**, including "Tuned on this drive" vs "Held-out drive" (M06 §7).
- **Record while you navigate:** a switch on route preview starts the sensor recorder so a navigated trip becomes AERIS data (R4 §6).

## Acceptance for R1

- [ ] The default screens contain no full-width scrubber and no `mm:ss / mm:ss` as primary text.
- [ ] Explore, Trips and Record are the only top-level tabs.
- [ ] Every screen names its position source in a way the user can see (signal chip; "Playing recorded drive" chip).
- [ ] The `PositionSource` abstraction exists and `AerisLiveSource` is present as a disabled stub.
