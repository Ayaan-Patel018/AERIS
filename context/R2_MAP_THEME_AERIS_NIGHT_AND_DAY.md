# R2 — Map theme: "AERIS Night" and "AERIS Day"

The basemap must be designed for the app's theme, not borrowed. Goals: (1) the map looks like part of the app, (2) data colours (cobalt, amber, teal) are the only vivid things on screen, (3) it reads as well as a mainstream navigation map: clear road hierarchy, calm labels, minimal clutter.

## 1. Approach

1. Choose a free **vector** tile source in the OpenMapTiles schema (preferred: **OpenFreeMap**; alternative: another OpenMapTiles-schema provider). **Verify its current terms, style URL and required attribution text before use.** Raster tiles cannot be recoloured, so do not use them for the primary map.
2. Download the provider's base style JSON once and commit it as `tools/base-style.json` (keeps builds reproducible and lets the app run if the provider changes styles).
3. Write a build script `tools/make-map-style.mjs` that reads `base-style.json` and **emits two complete style files**: `app/src/main/assets/styles/aeris-night.json` and `aeris-day.json`. The script re-colours layers by `source-layer` and `class`, not by layer id (ids differ between styles). Commit both outputs and the script. Add a unit test that loads the generated JSON and checks required layers exist.
4. The app loads the style from assets (no network needed for the style itself; tiles still need the network or the cache).
5. Glyphs (map label fonts) come from the provider's `glyphs` URL. Use a font stack the glyph server actually hosts (a Noto Sans family is typical). Do not try to use Hanken Grotesk inside the map.
6. Keep attribution visible (M05 §1) with the text the provider requires, plus "© OpenStreetMap contributors".

## 2. Palette (use these exact values)

| Element | Night | Day |
|---|---|---|
| Background / land | `#0F1A24` | `#EDF0EC` |
| Park, wood, grass | `#12302B` | `#D5E7D8` |
| Water | `#0A2533` | `#C4DEEB` |
| Minor road fill | `#223240` | `#FFFFFF` |
| Secondary/tertiary road fill | `#2D4050` | `#FFFFFF` |
| Primary/trunk road fill | `#3D566A` | `#FFFFFF` |
| Motorway fill | `#4A6A82` | `#FFFFFF` |
| Road casing | `#09111A` | `#CBD4D9` (motorway casing `#B9C3C9`) |
| Railway line | `#26384A` | `#BFC8CE` |
| Building (z ≥ 15 only) | `#13212C` at 60% | `#E4E8E3` |
| Place and road label text | `#8CA0B0` | `#5E6E7A` |
| Major place labels (city, district) | `#B9C8D3` | `#33434F` |
| Label halo | `#0C1319` | `#F5F7F6` |
| Boundary lines | `#26384A` dashed | `#C5CDD2` dashed |

Rules:
- **No saturated blue, amber, teal or red in the basemap.** Water and parks stay desaturated so AERIS data hues are unique.
- **Contrast rule.** AERIS data strokes (path, outage line, ellipse edge, raw fixes) always sit on a casing (Night `#09111A`, Day white) and must reach ≥ 3:1 against both **the casing and the land colour**. Verify with a script using the WCAG formula and print the table in the PR. Measured with the values above:

  | Data colour | vs Night casing | vs Night land | vs Day casing (white) | vs Day land |
  |---|---|---|---|---|
  | Cobalt (`#6D8BFF` Night, `#2D5BFF` Day) | 6.1 | 5.7 | 5.2 | 4.5 |
  | Amber (`#F2A93B` Night) | 9.5 | 8.8 | n/a | n/a |
  | **Amber line (`#B26A00` Day)** | n/a | n/a | 4.2 | 3.7 |
  | Teal (`#2BC4B1` Night, `#0E9F8E` Day) | 8.7 | 8.1 | 3.3 | 2.9 (use only with white casing and a text label) |

- **New token `amberLine`:** Night `#F2A93B` (same as `amber`), Day `#B26A00`. The Day `amber` value `#E8930C` is only 2.4:1 on white, so on light surfaces use `amberLine` for every amber stroke, dotted outage line, icon and amber-coloured text. Keep `amber` for translucent fills and glows (ribbon, ellipse fill, outage veil), where contrast is not the carrier of meaning.
- Day teal on land is 2.9:1, just under 3:1: never draw teal alone; raw fixes always have a white casing and the signal chip carries the label.
- Day roads are white with a grey casing; hierarchy comes from width and casing weight, not colour.

## 3. Road hierarchy and widths (dp, interpolate by zoom)

| Class | z10 | z14 | z17 | z19 |
|---|---|---|---|---|
| Motorway / trunk | 1.5 | 5 | 12 | 22 |
| Primary | 1.2 | 4 | 10 | 19 |
| Secondary / tertiary | 0.8 | 3 | 8 | 15 |
| Minor / service | hidden | 1.5 | 5 | 10 |
| Path / track | hidden | hidden | 1.5 (dashed) | 2.5 |

Casing is 1 dp wider on each side from z14 up. Use `line-cap: round`, `line-join: round`. Hide minor roads below z13 so the map breathes when zoomed out.

## 4. Labels, POIs and clutter policy

- **Road names:** along-line, `text-size` 11 → 13 sp, halo 1.5 dp, `symbol-spacing` large enough that a name repeats at most once per screen.
- **Place names:** city, town, suburb with weights and sizes stepping down; no icons.
- **Highway shields:** hide, except a minimal text-only ref (for example `A426`) on motorways and trunks at z ≥ 12, in the label colour.
- **POIs: hide all by default.** Whitelist at z ≥ 15 with a small 6 dp dot and the name in label colour: fuel, hospital, charging station, parking (large). Everything else is off. Rationale: a navigation map shows what matters for driving; brand-name POIs compete with the AERIS path.
- **One-way arrows:** very faint (`label` colour at 40%) at z ≥ 16.
- **3D buildings:** off.
- **Transit, ferry, aeroway labels:** off, except airport polygons faintly filled.
- **Max labels per tile** controlled by `symbol-sort-key` so important names win collisions.

## 5. Theme switching and states

- Day / Night / Auto follow the app theme (M02 §1). Auto follows the system setting.
- On theme change: swap style with camera preserved, fade in 200 ms, call `installLayers()` (M05 §1) so AERIS layers return.
- **Navigation night mode:** the app may auto-switch to Night after local sunset **only if the user enables "Automatic day and night while navigating"** (computed on-device from latitude, longitude and date; no network). Default off.
- **Dimming during playback:** while a trip plays, reduce basemap label opacity to 70% so the path and ellipse stay dominant. Restore when paused.

## 6. Camera conventions

| Mode | Pitch | Bearing | Zoom | Vehicle position on screen |
|---|---|---|---|---|
| Explore | 0° | north-up | fit or user | n/a |
| Route preview | 0° | north-up | fit route with padding for the top card and sheet | n/a |
| Navigating | 40° (setting: Flat / Tilted) | heading-up | 17 at low speed → 15.5 at highway speed (smooth, speed-based) | lower third |
| Trip playback | 0° (always flat) | heading-up (toggle to north-up) | 16.5–17.5 | middle third, never under the sheet |

Pitch is disabled in Trip playback on purpose: tilting a map distorts how the uncertainty ellipse and corridor read, and those are the point of that screen. Animate camera changes with 300–600 ms ease-out; never snap.

## 7. Implementation checklist

- [ ] `tools/make-map-style.mjs` produces both styles deterministically (run twice, diff is empty).
- [ ] Unit test: every required layer type exists (background, land use, water, road casings and fills per class, rail, labels).
- [ ] A contrast report is generated for AERIS data colours against the basemap colours, in both themes.
- [ ] Style loads offline from assets; tiles load from the network or cache.
- [ ] No POI icons or brand names appear at z ≤ 14; only the whitelisted POIs appear at z ≥ 15.
- [ ] Screenshots of Explore at z12, z15, z17 in both themes match the structure of the mockup.
- [ ] Attribution visible and included in image exports.

## 8. If the vector approach fails

Fallback order: (1) a second OpenMapTiles-schema provider with the same transform script; (2) pre-tinted raster tiles from a provider that offers a dark/light pair with a muted look (you lose road hierarchy control; report this). Do not fall back to a bright default OSM raster.
