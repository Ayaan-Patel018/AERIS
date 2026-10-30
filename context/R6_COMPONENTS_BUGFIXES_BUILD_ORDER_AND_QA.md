# R6 — Components, bug fixes, build order and QA

## 1. New or changed components

| Component | Spec summary | Used in |
|---|---|---|
| `SearchPill` | 52 dp, fully rounded, `paper`, e1; search icon, placeholder, gear | Explore |
| `ScopeChip`, `FilterChip` | 34 dp, fully rounded; selected = `cobaltSoft` + 1.5 dp cobalt stroke | Explore, Search, Trips |
| `SignalChip` | 32 dp; Satellite fix (teal), Searching (slate), Lost (amber, with counter), Unknown (hidden) | Explore, Navigating, Playback |
| `PlaybackLabelChip` | 32 dp, `paper`, play icon + "Playing recorded drive · {label}" | Playback, Dash |
| `PlaceRow` | 56 dp; pin icon in 36 dp circle; name with bold match; secondary line; distance | Search |
| `PlaceSheet` | Half sheet; Directions (filled), Save (tonal), Share (text) | Explore |
| `RouteRow` | Time in display face 22 sp; distance and note; optional amber satellite-loss hint | Route preview |
| `RouteTimeBubble` | Map label on a route (selected = cobalt) | Route preview |
| `GuidanceBanner` | `cobaltSoft`, 1 dp cobalt stroke, 20 dp radius; 46 dp icon; distance 34 sp | Navigating |
| `ThenPill` | Next maneuver preview | Navigating |
| `SpeedBubble` | 76 dp circle; speed 28 sp; unit caption | Navigating |
| `EtaBar` | 92 dp bar; end ×, remaining time 26 sp in `ink`, distance and arrival; overview button | Navigating |
| `TripCard` | See R5 §1 | Trips, Explore |
| `FactsRow` | Three stats with dividers | Trip detail |
| `MomentCard` / `MomentRow` | R5 §3.4 and §2 | Playback, Trip detail |
| `ProgressRail` | 6 dp (12 dp touched), distance-based, outage dotted | Playback |
| `PreRollCamera` | 1.2 s fit-then-follow camera move | Playback |
| `CompareSheet` | R5 §6 | Trip detail, Playback |

Use the M02 tokens only, plus one addition: **`amberLine`** (Night `#F2A93B`, Day `#B26A00`) for amber strokes, icons and text on light surfaces (see R2 §2 for the contrast reasoning). Add it to `AerisColors` and the Day/Night schemes. The guidance banner is the one place where a coloured container (`cobaltSoft`) is large; do not repeat that treatment elsewhere. Teal is only for satellite state and the "locked" uncertainty colour. Amber is only for dead-reckoning/satellite-loss. The arrival time and remaining time use `ink`.

## 2. Strings to add (put in `strings.xml`, sentence case)

Search places or drives · Recent · Saved · Fuel · Drives · Places · Moments · Satellite fix · Searching for satellites · Satellite signal lost · Satellite signal back · Directions · Save place · Saved · Share · Coordinates copied · Driving · Avoid tolls · Avoid highways · Fastest route · Fewer turns · Start · Steps · End navigation · Rerouting… · Last position · You've arrived · Done · Open trip · Record sensors for AERIS · Recording sensors · Passes {n} satellite-loss spot from your drives (plural) · Where satellites were lost · Playing recorded drive · Play trip · Play again · Back to trip · Trip finished · Moments · How AERIS did · If we hadn't tracked · How this track was computed · Recorded on this phone, not yet processed · AERIS positioning isn't running in this build.

## 3. Bug fixes from the screenshot (do these first, Phase 0)

### 3.1 One clock
The scrubber showed the end while the card showed `00:01`. Remove all duplicate time state. Everything reads the single `PlaybackClock`. Add a test: seek to 40%, assert every displayed value derives from that time.

### 3.2 Cardinal directions
`291° W` is wrong; 291° is WNW. Replace the conversion with a 16-point rose and test the boundaries.

```kotlin
private val ROSE = listOf("N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW")
fun cardinal16(deg: Double): String {
    val d = ((deg % 360.0) + 360.0) % 360.0
    return ROSE[(((d + 11.25) / 22.5).toInt()) % 16]
}
```
Tests: 0→N, 11.24→N, 11.25→NNE, 90→E, 180→S, 270→W, 281.24→W, 281.25→WNW, 291→WNW, 348.75→N, 359.9→N, 720→N, −10→N.

### 3.3 Uncertainty formatting and the `±0.1 m` problem
Formatting (display only; never clamp or change the value used for the ellipse):

```kotlin
fun formatMeters(m: Double?): String = when {
    m == null -> "—"
    m < 1.0   -> "<1 m"
    m < 10.0  -> String.format(Locale.getDefault(), "%.1f m", m)
    else      -> "${m.roundToInt()} m"
}
```
Use it for every metre readout. Separately, `±0.1 m` one second into a drive is almost certainly the filter's initial covariance, not a real estimate. **Do not hide or alter it in the UI.** Add it to the "backend items still needed" list: the export should mark a warm-up period (for example a `warmupSeconds` field in `meta`, or a per-frame flag). If the export provides it, show "Warming up" and "—" instead of the number during that period. If it doesn't, leave the real number and flag it in the report.

### 3.4 Defaults and clutter
- "Reference shown": confirm the reference layer is off on cold start and that the toggle is not persisted. Add a test.
- Remove ALL-CAPS labels; use sentence case ("Speed", "Heading", "Position uncertainty").
- Remove the always-visible scale bar on playback; show it during pinch only.
- Remove zoom +/− on compact widths.
- Move Dash into the playback overflow; move the gear into the search pill (Explore) and the Trips toolbar.

## 4. Build order (one phase = one commit group; push after each)

| Phase | Work | Mockup screens to match |
|---|---|---|
| **P0** | Bug fixes (§3), single clock, formatters, defaults, tests | — |
| **P1** | Map theme (R2): style script, Night/Day styles, contrast report, camera conventions | all map backgrounds |
| **P2** | Shell: Explore/Trips/Record tabs, `PositionSource` abstraction, `PhoneGnssSource`, `SignalChip`, SearchPill, Explore with peek sheet and drive cards | 1 |
| **P3** | Search (R3): pill → surface, Photon places, local drives and moments, recents, place sheet, saved places, "Where satellites were lost" layer | 2 |
| **P4** | Directions and route preview (R4 §1–3), time bubbles, route rows, satellite-loss hint | 3 |
| **P5** | Navigating (R4 §4–10), TTS, rerouting, arrival, record-while-navigating, honest GNSS-loss behaviour | 4 |
| **P6** | Trips (R5): list, detail, Play trip, playback screen, moment cards, progress rail, compare sheet, end card, Dash update | 5, 6 |
| **P7** | Polish: motion and haptics (M09), states, accessibility and performance (M10), screenshots, final report | all |

After each phase: unit tests, screenshots at 360 × 800 dp in Night and Day beside the matching mockup screen, and a short note on differences. Don't continue until I approve the phase.

Testing note: GNSS behaviour needs a physical phone outdoors (and, for loss, a covered area or a car). The emulator can inject mock locations, which is fine for UI states but must not be described as satellite testing.

## 5. Quality bars

- **Video-player smell test:** hand a stranger the app on the playback screen. They should say "driving screen", not "video". If a full-width scrubber, a big play button, or `mm:ss / mm:ss` is the main thing, the phase fails.
- **Map-fit test:** at 360 × 800 dp, the vehicle (or route start) is visible, not covered by any sheet or banner, in every screen.
- **Colour meaning test:** search the code for teal and amber uses; each must correspond to satellite state or signal loss.
- **Honesty test:** with the phone's GPS off, Navigating shows no estimated movement; Trip playback always shows the "Playing recorded drive" chip.
- **Performance:** frame metrics jank < 5% while panning and while playing at 4×; style loads under 500 ms from assets.

## 6. Verification report: additions to M10 §A

In addition to the M10 §A items, report:
1. Which tile provider and style you plan to use, its current terms, required attribution text, and whether it works offline from the cache.
2. Whether Photon, Nominatim and OSRM are reachable from the build environment and what base URLs you will configure (and that the OSRM demo server is not for production).
3. How the existing app obtains location today (provider type), and whether it already holds a foreground service.
4. Whether the exported data includes `meta` (filter, `referenceUsed`, commit), `warmupSeconds` or any warm-up flag, per-frame covariance and heading uncertainty.
5. The current state of the PlaybackClock and every place time is stored.

## 7. Final report format

A one-screen summary of what was built, the files added and removed, side-by-side screenshots against the mockup (Night and Day), performance numbers, the QA list with ticks, and **backend items still needed**: `meta.referenceUsed`, `metrics.json`, per-frame covariance, outage flags, warm-up flag, recording file format alignment, and (for later) a path to an on-phone filter.

## 8. Anti-patterns for this redesign

A media-player control bar as the main control; a tall sheet that hides the vehicle; a light basemap on a dark app; saturated hues in the basemap; showing AERIS output as if it were live; growing circles or extrapolated positions during a satellite loss without an estimate behind them; snapping an AERIS track to roads; fabricated ratings, traffic, speed limits or "less traffic" notes; text input while driving; teal or amber used decoratively; ALL-CAPS labels; Google Maps SDK, icons or colours.
