# R3 — Explore, search and places

Explore is the home screen. It must open on a real map, let someone find a place in two taps, and make the drives feel like part of the app rather than a separate tool. See mockup screens 1 and 2.

## 1. Explore layout (mockup screen 1)

Top to bottom over the full-bleed map:

1. **Search pill** (fully rounded, 52 dp high, `paper`, e1, 12 dp from the sides, below the status-bar inset). Leading search icon, placeholder "Search places or drives", trailing gear icon (opens Settings). No other controls in this row.
2. **Chip row** (34 dp): `Drives` (selected by default, `cobaltSoft` with a 1.5 dp cobalt stroke), `Saved`, `Fuel`, `Recent`. Horizontally scrollable; chips are filters on the map and the sheet, not navigation.
3. **Signal chip** (left, under the chips): "Satellite fix" (teal), "Searching for satellites" (slate), "Satellite signal lost" (amber) or hidden when location permission is not granted. Source: the phone's GNSS, never a guess (§3).
4. **Layers button** (right, under the chips, 44 dp) opens the layers sheet (M05 §8) with an added layer, "Where satellites were lost" (§6).
5. **Locate button** (right, above the sheet) centres on the phone's position. Teal icon when a fix exists, `ink3` otherwise.
6. **Peek sheet** (about 236 dp above the nav bar): title "Recent drives" and "See all" (opens Trips); two or three drive cards (see §5). Below it, when the user has saved places, a "Saved places" row of up to 4 chips.
7. **Navigation bar:** Explore, Trips, Record.

No zoom buttons on phones. No scale bar unless pinching.

### Opening state rules
- **With location permission and a fix:** camera centres on the phone's position at zoom 14.
- **Without permission or fix:** camera fits the most recent trip's bounds; if none, the last viewed place; if none, a neutral overview. The signal chip shows nothing about satellites until permission is granted. Never show a made-up position.
- Ask for location only when the user taps Locate (pre-permission sheet in M04 §4).

## 2. Search (mockup screen 2)

### Behaviour
- Tapping the pill opens a full-screen search surface (shared-element transition: the pill grows to the top bar, 250 ms). Keyboard opens immediately. Back chevron on the left, clear (×) on the right when text exists.
- Scope chips under the field: `All` (default), `Places`, `Drives`, `Moments`.
- **Debounce 300 ms, minimum 3 characters** for place queries; local searches (drives, moments) start at 1 character and are instant.
- Cancel any in-flight request when the text changes.
- Pressing the keyboard Search key opens a results map view: pins for places on the map, list in the sheet.

### Result sections (grouped, in this order)
| Section | Source | Row |
|---|---|---|
| Places | Photon, biased to the map centre or the phone's position (M08 §4); `limit=8`; request in the device language | Pin icon in a 36 dp `harbor2` circle; name with the matched part in bold; locality and type below. If the phone's position is known, show distance at the right edge. |
| Drives | Local: match on label and id | Route icon; `Drive S3b`; "11 min · 3.4 km · 1 satellite loss" |
| Moments | Local index of events (satellite lost, back, stop, turn) per drive | Satellite icon; "Satellite loss · Drive S3b"; "at 03:20, lasted 40 s". Typing "satellite", "loss", "stop" or "turn" surfaces these. |

- Empty field: **Recent** (up to 5, from DataStore, each with a clock icon and a remove swipe) and **Saved** places.
- Selecting a place: close search, fly the camera there (800 ms), drop the place pin (28 dp, `ink` circle with a white centre dot), open the **Place sheet** (§4).
- Selecting a drive: open Trip detail (R5 §2). Selecting a moment: open that trip at that moment (paused).
- Footer line (caption, `ink3`): "Places from OpenStreetMap contributors." Only text typed in the field is sent to the place-search service; say so under the field the first time.

### States
| State | UI |
|---|---|
| Loading places (> 200 ms) | 3 skeleton rows under "Places" |
| No places | "No places match “{query}”" and "Try a street, landmark or city." Local sections still show if they match |
| Offline | "Place search needs a connection. Drives and moments still work." (inline banner) |
| Service error | "Place search isn't available right now." with Try again |
| Place search disabled in Settings | Section hidden; a one-line hint "Place search is off" with a link to Settings |

### Privacy and policy
- Use Photon for type-ahead. Use Nominatim only on submit (Enter), at most 1 request per second, with a descriptive User-Agent. Do not mix them up: Nominatim forbids type-ahead.
- No analytics. No logging of queries. Recents live only on the device.
- Settings → Privacy: "Place search" switch (default on) with the sentence "Search text is sent to an OpenStreetMap-based search service." 

## 3. The phone's position and the signal chip (real)

Use Android's `LocationManager` with **`GPS_PROVIDER`** (satellite only) for the position shown as "Satellite fix". Do not use fused or network location for this, otherwise a satellite loss is hidden by Wi-Fi/cell positioning and the chip would lie. Request 1 Hz. State machine:

| State | Condition | Chip |
|---|---|---|
| Locked | Last fix newer than `max(5 s, 3 × median fix interval)` | "Satellite fix" (teal) |
| Searching | Permission granted, no fix yet since start | "Searching for satellites" (slate) |
| Lost | Had fixes, then none for longer than that threshold | "Satellite signal lost" (amber), with an elapsed counter |
| Unknown / off | No permission or location services off | hidden, with a "Turn on location" card when the user taps Locate |

The marker uses the raw phone position with its true accuracy circle (`Location.accuracy`), never a smoothed or snapped position outside Navigating (R4 §4). In Record mode the satellite count (`GnssStatus`) may be shown; in Explore keep it out of the chip.

## 4. Place sheet

Half-height sheet over Explore. Contents:
- Title (name), category and address lines. If the data has no address, show coordinates only.
- Coordinates line with Copy (snackbar "Coordinates copied").
- Distance and straight-line direction from the phone, only when a fix exists.
- Primary button **Directions** (filled `ink`); tonal **Save place** (toggles to "Saved", stored on the device); text button **Share** (a `geo:` URI plus a plain-text link through the share sheet).
- No ratings, photos, hours or reviews unless a real source is added later.

Long-press anywhere on the map drops a pin and opens the same sheet. Reverse geocoding (Nominatim `reverse`, ≤ 1 request/s) fills the address if available; otherwise the sheet shows coordinates only, with no placeholder text.

## 5. Drive cards on Explore

Card (158 dp wide, 16 dp radius, `chalk` fill, 1 dp `harbor` stroke): route thumbnail 136 × 64 dp (real path from the data, signal-loss segments dotted amber), drive label, "11 min · 3.4 km", and a third line "1 satellite loss" in amber or "No satellite loss" in `ink3`. Tap opens Trip detail. Long-press shows Share and Delete (not for bundled drives).

Selecting the `Drives` chip also draws the paths of recent drives faintly on the map (cobalt 35%, 2 dp). Tapping a faint path selects that drive.

## 6. Layer: "Where satellites were lost"

An optional layer, off by default, available in Layers and by the `Drives` chip long-press.

- **Data:** the outage windows already derived from the user's stored drives (exported and recorded-and-processed). For each outage, take the path segment between its start and end.
- **Style:** amber dashed ring (dash 6/6, 2 dp stroke, 22% fill) centred on the middle of the segment, sized to the segment's length with a minimum of 24 dp; at zoom ≥ 15 show the actual dotted amber segment instead of the ring.
- **Label:** a caption on tap: "Satellites lost here in Drive S3b, 40 s". Nothing is inferred beyond the stored drives; never say "dead zone" as if it were universal.
- **Empty:** "No satellite loss in your drives yet."
- This layer feeds the route preview hint (R4 §3).

## 7. Saved places

Local only (Room or DataStore). Editable name; delete by swipe. Shown as chips on Explore (up to 4, "See all" → a list sheet) and in search when the field is empty. No sync, no account.

## 8. Accessibility specifics

- The search pill is one button with the label "Search places or drives". The gear is a separate button.
- Each result row is one focus target with a full spoken description: "Millbrook Park, park, Northgate, 1.2 kilometres away".
- Moving the camera with TalkBack: provide "Zoom in", "Zoom out", "Centre on my location" as custom actions on the map.

## Acceptance

- [ ] Explore opens on a map with no permission prompt; Locate triggers the in-context permission flow.
- [ ] Typing "Mill" quickly sends at most one place request per 300 ms and cancels stale requests.
- [ ] Turning airplane mode on keeps drives and moments searchable and shows the offline banner for places.
- [ ] Turning location services off changes the chip to the correct state within the threshold; with Wi-Fi on, the chip still reports satellite loss when GPS has none.
- [ ] With the places switch off in Settings, no network request is made while typing.
- [ ] The "Where satellites were lost" layer draws only from stored drive data.
