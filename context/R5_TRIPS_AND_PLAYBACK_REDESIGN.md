# R5 — Trips and playback (replacing the "video player")

A recorded drive is a **trip**. You browse trips, open one, press **Play trip**, and watch it as a drive session. This replaces the Replay tab, the big play button and the full-width scrubber. See mockup screens 5 and 6.

## 1. Trips tab

Top bar: title "Trips", a search icon (opens the shared search, scoped to Drives and Moments) and an overflow menu: "Import a drive", "Manage storage", "Settings".

Filter chips: `All`, `With satellite loss`, `Recorded on this phone`.

Sections: **From AERIS exports** (bundled and imported) and **Recorded on this phone**.

Trip card (full width, 16 dp radius, `paper`, 1 dp `harbor`, 12 dp padding):
- Left: route thumbnail 72 × 72 dp from the real path; satellite-loss segments dotted amber.
- Right: drive label (title style 18 sp), "11 min · 3.4 km", then a status line:
  - "1 satellite loss" (amber icon + `ink`), or "No satellite loss" (`ink3`);
  - for recordings without an AERIS track: "Recorded on this phone, not yet processed" (slate chip), not playable.
- Optional chip from the manifest's `role` ("Development" / "Sealed validation"). Never inferred.
- Swipe: Share, Delete (not for bundled).
- Empty: "No trips yet. Import an exported drive or record one." with buttons **Import a drive** and **Record a drive**.

## 2. Trip detail (mockup screen 6)

Layout: a header map (top 38% of the screen) and a sheet that fills the rest, above the nav bar.

**Header map:** shows the whole path with the camera fitted and padded; locked segments solid cobalt, outage segments dotted with amber glow, the corridor ribbon at its widest, start marker (white circle, cobalt ring) and end marker (cobalt circle, white ring). Non-interactive until tapped; tapping expands it to full height with normal gestures and a "Done" pill. A circular back button sits top-left.

**Sheet content:**
1. Title: drive label (24 sp, display face), subtitle "Exported drive · AERIS track" or "Recorded on this phone".
2. **Facts row** (three columns separated by 1 dp dividers): distance, duration, satellite losses. Values from the data; omit a column if it can't be computed.
3. Buttons: **Play trip** (filled `ink`, play icon, flex 1.5) and **Share** (tonal).
4. **Moments** list: icon in a 36 dp circle, title ("Satellite signal lost"), detail ("03:20 · lasted 40 s"). Rows for: satellite lost / back, stops ≥ 3 s, turns ≥ 45°. The "satellite back" row's detail includes "AERIS was {d} m from the new fix" (real, M06 §5). Tapping a row opens playback at that moment, paused, 3 s earlier.
5. **How AERIS did** (results card, M06 §7) with the "Tuned on this drive" / "Held-out drive" chip. Hidden if there is no `metrics.json` entry.
6. **If we hadn't tracked** (comparison card, M06 §6) for each outage; each row opens the compare sheet (§6).
7. **How this track was computed** row (trust ledger, M06 §5).

For a recording that has no AERIS track: show the raw satellite track (teal dots, labelled "Raw phone GNSS"), a card "This recording hasn't been processed by AERIS yet", and no Play trip button.

## 3. Trip playback (mockup screen 5)

Pressing **Play trip** opens the playback screen. It uses the same driving surface as Navigating, fed by `TripPlaybackSource` (R1 §2).

### 3.1 Always-visible honesty label
A small chip at the top-left under the status bar: play icon + "Playing recorded drive · {label}" (`paper`, `ink2` text, 32 dp). Tapping it opens Trip detail. It stays visible the whole time, including in Dash view. This is the only "media" signal on the screen, and it is a label, not a control.

### 3.2 Outage banner
When the current frame is in an outage: the amber banner from the mockup (`amberSoft` fill, 1 dp amber stroke at 35%, 22 dp radius): dish-slash icon, "Satellite signal lost", live counter at the right, and "AERIS continues from the last fix." On re-acquisition: teal "Satellite signal back" with "AERIS was {d} m from the new fix", held 4 s. The full signature sequence is in M09 §2.

### 3.3 Map
Flat (pitch 0), heading-up by default (toggle in Layers to north-up), vehicle in the middle third. Camera bottom padding = card height + 24 dp so the vehicle is never under the card. Layers and styling as M05 §3: travelled path cobalt with casing; upcoming path cobalt at 35%; outage portion dotted with amber glow; amber ellipse at the vehicle; corridor ribbon behind it; raw satellite fixes as small teal dots only outside outages. Basemap labels at 70% opacity while playing (R2 §5).

### 3.4 Bottom card (about 226 dp, not a tall sheet)
Top to bottom, 18 dp side padding:
1. **Readout row:** left, speed in the display face (34 sp) with the unit, and under it "heading 291° WNW" (`caption`); right, position uncertainty in the display face, coloured `teal` when locked and `amber` in outage, with "position uncertainty, 1σ" below. Formatting rules in R6 §3. A tap on the uncertainty opens an info tip that explains the shaded area on the map.
2. **Moment cards:** a horizontally scrolling row of compact cards (min width 132 dp, 16 dp radius, 1 dp `harbor` border): icon + title ("Satellite lost", "Left turn", "Satellite back") and the time `03:20`. The current moment (within ±5 s) has an amber border/fill if it is a satellite event, otherwise a cobalt border. The row auto-scrolls to keep the current moment in view; the user scrolling stops auto-scroll for 5 s. Tap a card to jump there (3 s before).
3. **Progress rail:** a 6 dp line: elapsed part `cobalt`, remainder `harbor`, outage portions as an amber dotted segment, a 16 dp thumb with an amber border while in outage and cobalt otherwise. Progress is by **distance driven**, the label beneath reads "Driven 1.4 of 3.4 km". Tapping the label toggles to elapsed time "2:10 of 11:21". The rail grows to 12 dp while touched and supports drag-to-seek with a preview chip above the thumb (shows the signal state at that point). Seeking pauses the clock while dragging.
4. **Controls row:** a speed chip (`1×`; tap cycles 1×, 2×, 4×, 8×; long-press opens a menu) and a 44 dp round **Pause/Play** button on the right. Nothing else. Previous/next moment are available as swipe gestures on the moment row and as TalkBack actions.

### 3.5 Controls elsewhere
- Layers button (top right) opens the layers sheet (M05 §8).
- Overflow (top right, below Layers): "Dash view", "Share this moment", "Show reference track" (only when the Developer option is on).
- Back arrow in the system bar returns to Trip detail and pauses.
- Double-tap on the map toggles follow; any pan switches to Free with a Recenter button.

### 3.6 Start and end
- **Start:** a 1.2 s "pre-roll": the camera shows the whole path, then eases into the vehicle at the trip start (ease-in-out), then the clock starts. Tap anywhere to skip. Reduced motion: no pre-roll, just start.
- **End:** playback pauses on the last frame and a summary card slides up: "Trip finished", distance, duration, satellite losses, and the headline comparison line "AERIS was {y} m from the new fix after the satellite loss; holding the last fix would have left it {x} m away." (only if computable). Buttons **Play again** (filled) and **Back to trip** (text).

## 4. Dash view (changes to M07 §6)

Keep the layout. Replace "Replay" with the persistent chip "Playing recorded drive". Remove the media bar; use the progress rail only, thinner, with the pause button at the lower right. The signal chip, speed and uncertainty remain the large elements.

## 5. State, clocks and data rules

- One `PlaybackClock` is the only source of time (M07 §1). The rail, moment row, map, readouts and the "Driven x of y" label all derive from it. A unit test asserts that after `seek(t)` every derived value corresponds to the same `t`.
- Distance driven at `t` is the cumulative haversine length of the AERIS path up to `t` (pre-computed array); total length is the last element.
- Moment detection is from AERIS output only (M07 §3). Reference data never feeds moments, rail or readouts.
- If speed or heading is missing in the data, those readouts show "—".

## 6. Compare sheet ("If we hadn't tracked")

Opened from the Trip detail comparison row or from an outage moment card's long-press. A bottom sheet with a mini map (fits that outage: AERIS path cobalt, hold-last-fix slate with hollow marker, raw satellite fixes teal dots, first fix after the outage as a ring) and a three-row table (AERIS, Hold last fix, Raw satellite fixes) with the columns defined in M06 §6, then the single plain-language sentence. Hide rows that can't be computed. A **Play this moment** button starts playback 5 s before the outage.

## 7. Processing state for recordings

A recording without an AERIS export shows the "not yet processed" state. If the user imports an AERIS export whose id matches the recording's id, the trip merges: the card loses the chip and Play trip appears. Matching is by id only (never by fuzzy guess).

## 8. Accessibility

- Rail: `role=slider` semantics with `stateDescription` "1.4 of 3.4 kilometres, satellite fix"; increment/decrement actions of 50 m; long-press 250 m.
- Moment cards: each is a button with the full description; custom accessibility actions "Previous moment" / "Next moment" on the row.
- Outage start/end announced politely once (M10 §B).
- All time and distance strings use the device locale.

## Acceptance

- [ ] No full-width scrubber, no large round play button and no `mm:ss / mm:ss` as primary text anywhere in the default flow.
- [ ] The "Playing recorded drive" chip is visible on every playback screen and in Dash view.
- [ ] Scrubbing the rail, tapping a moment card and the pre-roll all keep one clock; unit test for clock consistency passes.
- [ ] Vehicle marker is never covered by the bottom card at any card height or font scale (check at 200%).
- [ ] The trip finished card shows only values that can be computed.
- [ ] Recorded-but-unprocessed trips cannot be played and say why.
