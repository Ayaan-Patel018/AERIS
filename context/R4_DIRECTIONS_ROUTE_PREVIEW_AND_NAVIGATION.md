# R4 — Directions, route preview and navigation

This makes the app a real navigation app: choose a place, see routes, start guidance, get turn-by-turn using the phone's satellite position, reroute if needed, arrive. Everything here uses the phone's own GNSS and open map data. **AERIS's filter is not running live**, so this feature does not claim AERIS positioning; it is honest about satellites and ready to accept `AerisLiveSource` later (R1 §2). See mockup screens 3 and 4.

Feature flag: `FEATURE_ROUTING` (default **true** in debug builds for this redesign; keep the flag so it can be switched off for any build).

## 1. Services

| Need | Service | Notes |
|---|---|---|
| Route calculation | **OSRM** `route` API (`/route/v1/driving/{lon,lat};{lon,lat}`) with `alternatives=3&steps=true&geometries=geojson&overview=full` | `router.project-osrm.org` is a demo server only. Make the base URL a build config value, show "Demo routing service" in Settings → About when it is the demo server, and note in the report that production needs a self-hosted instance. |
| Place search | Photon / Nominatim as in R3 | |
| Map | Vector tiles as in R2 | |

Cache the last route in memory (and on disk for an active navigation) so a brief signal drop doesn't end guidance. Timeouts 8 s; one automatic retry. All coordinates leaving the device go only to the routing service, only when the user requests directions.

## 2. Directions entry and route preview (mockup screen 3)

Opened from the Place sheet's **Directions** button.

**Top card** (over the map, `paper`, 20 dp radius, e2): two rows, From and To, joined by a dotted connector, with a swap button.
- From defaults to **Your location** (only if a recent satellite fix exists; otherwise "Choose start" and the field is focused).
- To is the chosen place. Both fields open the search surface when tapped. Adding stops is out of scope.
- Under the card: chips `Driving` (selected, the only mode) and `Avoid tolls`, `Avoid highways` as toggles if the routing server supports `exclude`.

**Map:** all routes drawn with white (Day) or dark (Night) casing. Selected = cobalt, 6 dp; alternatives = slate, 5 dp, 100% opacity; selected route on top. A time bubble sits on each route at its midpoint (selected = cobalt fill with white text; others = `paper` with `ink` text). Tapping an alternative selects it. Start marker: white circle with an `ink` ring. Destination: `ink` teardrop pin. Camera fits all routes with padding for the top card and the sheet.

**Sheet (≈ 296 dp):** route rows, each with remaining time in the display face (22 sp), then distance and a note:
- "Fastest route" for the quickest; "Fewer turns" if it has the least maneuvers by at least 20%; no note otherwise. Do not invent notes such as "Less traffic": there is no traffic data.
- Selected row: `cobaltSoft` fill with a 3 dp cobalt start edge.
- Buttons: **Start** (filled `ink`, 48 dp, with a turn icon) and **Steps** (tonal).
- Under the buttons, a switch row **Record sensors for AERIS** (default off, remembered). See §6.

**Steps:** a full-height sheet listing steps: maneuver icon, instruction, distance. Tapping a step flies the camera to it. Instruction text is generated from OSRM maneuver data (§5), in the device language where supported, English otherwise.

## 3. Hint: passes places where satellites were lost

On route rows, if the route comes within 40 m of a stored outage segment (R3 §6), show a single line with the amber signal-loss icon: "Passes 1 satellite-loss spot from your drives" (plural when more). Tapping it highlights those spots on the map. Compute from stored drives only; never claim anything about places not in the data. If there are no stored outages, show nothing.

## 4. Navigating (mockup screen 4)

Pressing **Start** begins guidance and keeps the screen on. Position source is `PhoneGnssSource` (R3 §3).

### Layout
- **Guidance banner** (top, full width minus 10 dp margins, `cobaltSoft` fill, 1 dp cobalt stroke, 20 dp radius, e2): a 46 dp maneuver icon, the distance to the maneuver in the display face (34 sp), and the instruction in 15 sp ("Turn right onto Mill Road"). Distances read "300 m" under 1 km and "1.2 km" above; rounded to 50 m steps below 500 m, 100 m up to 1 km.
- **"Then" pill** under the banner: next maneuver icon and distance, only if it is within 600 m.
- **Signal chip** under that (same as Explore). It is the app's honesty anchor: it must always be visible while navigating.
- **Layers button** right side. No other buttons on the map.
- **Speed bubble** bottom-left above the bar, 76 dp circle: speed from the phone's GNSS (`Location.speed`) in the user's unit. If no speed is available, show "—". No speed-limit sign (no data).
- **Bottom bar** (92 dp): end button (×) on the left, centre: remaining time in the display face (26 sp, `ink`, **not teal**), then "5.4 km · 14:32 arrival" in `ink2`; route overview button on the right. Tapping the bar expands remaining distance, ETA, and steps.
- **Recenter** appears when the user pans away, with a 10 s auto-return to following.

### Map behaviour
- Heading-up, pitch 40° (setting: Flat / Tilted), vehicle in the lower third, speed-based zoom (R2 §6).
- The route ahead is cobalt with casing; the part already driven fades to a muted slate-blue (`#4C5F78` Night / `#9BB0F0` Day).
- **Marker snapping (display only):** while Navigating with the phone's GNSS, the marker may be drawn snapped to the route when the position is within `max(15 m, accuracy)` of it, because every navigation app does this and this position is not an AERIS estimate. The accuracy circle always shows the true `Location.accuracy`. **Never snap in Trip playback or anywhere an AERIS track is shown.**
- Progress along the route is the projection of the position onto the route polyline (pure function `projectOnRoute`, unit-tested). ETA = remaining distance ÷ a blend of current speed and route-average speed, floored at a minimum speed so it never divides by near zero.

### Rerouting
Off route when the distance to the route exceeds `max(50 m, 3 × accuracy)` for more than 5 s. Banner changes to "Rerouting…" (with a progress sliver), calls the routing service from the current position to the destination, and swaps the route in with a 300 ms crossfade. If the call fails: "Can't reroute right now. Showing your last route." and retry every 10 s.

### Voice guidance
Android `TextToSpeech`, on-device, switch in Settings → Navigation (default on) and a quick mute in the bottom bar's overflow. Announce at about 500 m, 200 m and at the maneuver, plus "Rerouting" and "You have arrived". Request transient audio focus with ducking. No sounds besides speech.

### Arrival
Banner becomes "You've arrived" and a card slides up: place name, total distance, total time, buttons **Done** and (if recording) **Open trip**. Keep the screen on for 10 more seconds then release.

## 5. Maneuver text and icons (from OSRM `maneuver.type` + `modifier`)

| type / modifier | Icon | Instruction (with road name `{n}` if present) |
|---|---|---|
| depart | arrow-up | "Head {bearing} on {n}" |
| turn / left | corner-up-left | "Turn left onto {n}" |
| turn / right | corner-up-right | "Turn right onto {n}" |
| turn / slight left, slight right | arrow-up-left, arrow-up-right | "Bear left/right onto {n}" |
| turn / sharp left, sharp right | corner-down-left, corner-down-right | "Make a sharp left/right onto {n}" |
| turn / uturn | rotate-ccw | "Make a U-turn" |
| continue / straight | arrow-up | "Continue on {n}" |
| merge | merge | "Merge onto {n}" |
| fork / left, right | git-fork variants | "Keep left/right onto {n}" |
| roundabout, rotary | rotate-cw | "At the roundabout, take exit {exit}" |
| on ramp / off ramp | arrow variants | "Take the ramp onto {n}" |
| arrive | flag | "Arrive at your destination" |

If a road name is missing, drop "onto {n}". Never invent names.

## 6. Record sensors while navigating (the AERIS bridge)

The switch on route preview starts the sensor recorder (M08) when guidance starts, using the same foreground service. The navigation bottom bar shows a small `ink2` dot with the text "Recording sensors" in `caption` (not red, because red means errors only). On arrival or end, the recording is saved and the arrival card offers **Open trip**. The trip appears in Trips as "Recorded on this phone, not yet processed" until the backend produces an AERIS track. This turns every test drive into AERIS data without a second step. Default off; the first time it's switched on, show the privacy note (drives stay on the device).

## 7. When satellites are lost during navigation (honest behaviour)

This build has no live AERIS filter, so it must not pretend. When the state becomes **Lost** (R3 §3):
- Chip turns amber: "Satellite signal lost" with a counter.
- A banner (amber, below the guidance banner): "AERIS positioning isn't running in this build." (This line is a build-time string; remove it when `AerisLiveSource` is enabled.)
- The vehicle marker stays at the last position, drawn dimmed with a dashed ring, and a label "Last position". **No growing circle and no extrapolation**, because there is no estimate behind them.
- Guidance holds the last instruction; ETA shows "—". Voice says nothing new.
- When satellites return: chip back to teal, banner "Satellite signal back", marker resumes, the app recomputes progress and ETA, and reroutes if off route.
- If `AerisLiveSource` exists and is enabled, replace the dimmed marker with the AERIS estimate, the ellipse and the corridor (R5 §3), and show the signal chip as "Dead reckoning".

## 8. Safety and ergonomics

- First time navigation starts, show a one-time sheet: "Set your destination before you drive. Don't use the phone while driving." with **Got it**.
- While moving faster than 5 m/s, disable text entry and hide the search entry points; show "Pull over to search" if tapped.
- Touch targets ≥ 56 dp for navigation controls. Text sizes in the banner follow system font scale but cap at 130% for the banner distance to avoid overflow.
- Battery: show a card "Navigation uses more battery" only if battery saver is on.

## 9. Permissions and services

`ACCESS_FINE_LOCATION`, foreground service of type `location`, `POST_NOTIFICATIONS` (for the ongoing-navigation notification with the next maneuver and an End action). No background location permission (the foreground service covers a locked screen when started in the foreground).

## 10. Failure states

| Situation | UI |
|---|---|
| No fix when pressing Start | "Waiting for satellites" screen with the route shown; Start becomes enabled when a fix arrives, or "Start anyway" |
| No route found | "We couldn't find a driving route between these places." Try different places |
| Routing service unreachable | "Directions aren't available right now." Try again |
| Destination too far for the server | "This trip is too long for the routing service." |
| Location permission denied | Card in the From field: "Turn on location to start from here", or choose a start point manually |
| App killed during navigation | Restore on next launch with "Resume navigation?" if the trip ended less than 30 minutes ago |

## Acceptance

- [ ] From Explore: search → place → Directions → route preview → Start works end to end on a device with a real fix.
- [ ] `projectOnRoute` has unit tests (on-route, off-route, loops, endpoints).
- [ ] Rerouting triggers only after the off-route threshold and 5 s.
- [ ] With GPS blocked (indoors or a Faraday-style test) the chip turns amber, the marker dims, and no estimate is drawn.
- [ ] No growing circles, extrapolated positions or "AERIS" claims appear in Navigating while the source is phone GNSS.
- [ ] Route preview shows the satellite-loss hint only when stored drives justify it.
- [ ] Speed, ETA and distance come from real data; there are no hard-coded numbers.
