# aeris-trip/1 — trip export for the AERIS mobile app (**DRAFT**)

Status: **DRAFT** (C1, 2026-10-30). Field names and rules may still change; the app must check `meta.schema == "aeris-trip/1"`
and `meta.schema_status`. Producer: `backend/export_vdr.py` (filter `vehicle_dr`). Scorer: `backend/score_export.py`.

## The file

`backend/exports/<drive>_aeris_trip_v1.json` — ONE JSON object (not an array), strict JSON (no NaN/Infinity; a missing
value is `null`), compact separators, UTF-8. Five top-level keys: `meta`, `outages`, `frames`, `gnss`, `corrections`.

Conventions used everywhere:

| quantity | unit / convention | rounding |
|---|---|---|
| time `t_s` | seconds since the FIRST ROW of the phone CSV (phone wall clock; see `meta.t_zero`). Absolute seconds, never normalised. | 3 dp |
| position | WGS-84 `lat`, `lon` in degrees | 7 dp |
| lengths | metres | 2 dp |
| angles | degrees, **clockwise from North** (compass convention) | 1 dp |
| speed | m/s | 2 dp |
| covariance | m², East/North | 2 dp |

## `meta`

| field | meaning |
|---|---|
| `schema` | `"aeris-trip/1"` |
| `schema_status` | `"DRAFT"` |
| `drive` | drive id, e.g. `"S3b"` |
| `filter` | `"vehicle_dr"` |
| `git_commit`, `dirty` | backend commit the file was produced from; `dirty` = export_vdr.py or vehicle_dr.py differ from that commit (or are untracked) |
| `sha256` | `{"export_vdr.py": ..., "vehicle_dr.py": ...}` of the exact source files used |
| `params` | every `VDRParams` field used (the filter's defaults unless stated) |
| `origin` | `{lat, lon, source}`: first phone row with a finite fix (vehicle_dr.py:515-516). Only needed to reproduce the filter's local frame; frames already carry lat/lon. |
| `t_zero` | definition of `t_s = 0` with its code citation (data_loader.py:66, :128 — the loader check_outage uses), plus `wall_clock_start_time_of_day_s` |
| `duration_s` | `t_s` of the last frame |
| `referenceUsed` | always `false`: no VBOX/reference data was an input (the app should refuse a file where this is not `false`) |
| `note` | `"development drive, tuned on S3b/S2, not validation"` |
| `sigma` | `{"calibrated": false, "definition": "1-sigma ellipse, Mahalanobis<=1, expect 39% in 2D"}`: the ellipse is the filter's own 1-sigma; it is NOT calibrated (S3b 200-260 s: only 14.7 % of truth positions fall inside it, vs 39 % expected) |
| `status_rule`, `correction_rule` | the rules below, in words, with code citations |
| `replays` | `{count, rewritten_rows_not_shown}`: S1d replays that fired, and how many already-emitted rows they rewrote internally (those rewrites are NOT in `frames`) |
| `generated_at` | UTC ISO-8601 |

## `outages`

One entry per GNSS outage window: `{start_s, end_s, kind, last_fix_s, first_fix_after_s, withheld_fix_count}`.
`kind` is `"simulated"` (the phone had fixes; the export deleted them). `last_fix_s` / `first_fix_after_s` are the last
phone fix before `start_s` and the first after `end_s` — the real GNSS gap can be longer than the window (S3b: last fix
184.0 s, first fix after 262.1 s, 5 fixes withheld). The windows come from one source (`export_vdr.py --outage`,
default 200:260); every fix inside a window is deleted from the input BEFORE the filter runs.

## `frames` (one per IMU row, ~10 Hz)

Frames are the rows **as first emitted** (causal): `frame[t]` is exactly what a live app would have shown at `t`.
vehicle_dr's replay can later rewrite its internal past; that never changes an emitted frame (its effect appears as a
step at the replay's trigger time, listed in `corrections`).

| field | unit | meaning |
|---|---|---|
| `t_s` | s | time (see conventions) |
| `lat`, `lon` | deg | AERIS position |
| `bearing_deg` | deg, [0, 360), clockwise from North | vehicle course. (vehicle_dr's internal ψ is ENU, counter-clockwise from East; bearing = (90 − ψ) mod 360.) |
| `speed_mps` | m/s | forward speed estimate (can be −0.00 at a standstill) |
| `sigma_major_m`, `sigma_minor_m` | m | 1-sigma ellipse semi-axes = √eigenvalues of the 2×2 East/North covariance |
| `ellipse_angle_deg` | deg, [0, 180), clockwise from North | direction of the MAJOR axis |
| `cov_en_m2` | m² | `[ee, nn, en]` = [var East, var North, cov East-North] — the full covariance; the ellipse fields are derived from it |
| `fix_age_s` | s | time since the last usable phone fix (new fix, ≥ 6 satellites); `null` before the first fix |
| `status` | — | `"warmup"`: before the first GNSS course initialises the heading (vehicle_dr.py:609, :794-796) or between an IMU release and the end of its launch calibration (evaluated `launch_n_after` samples after the release, vehicle_dr.py:707-725); else `"gnss"` if `fix_age_s <= 2`; else `"dr"` (dead reckoning) |
| `stationary` | bool | the filter's IMU standstill flag (ZUPT/ZARU active) |

Example frame (S3b, inside the outage):

```json
{"t_s":230.027,"lat":52.3730973,"lon":-1.2554414,"bearing_deg":310.3,"speed_mps":2.59,"sigma_major_m":18.22,"sigma_minor_m":16.94,"ellipse_angle_deg":23.2,"cov_en_m2":[293.99,325.09,16.3],"fix_age_s":46.03,"status":"dr","stationary":false}
```

## `gnss`

The phone's own fixes, for drawing the GNSS layer: `{t_s, lat, lon, accuracy_m}` for every NEW fix (lat/lon changed).
**None inside an outage window.** Match to frames **by `t_s`, never by index** (there are ~100× more frames than fixes,
and the first fix is at `t_s = 0`, before the first frame).

## `corrections`

Every displayed step larger than 5 m between consecutive frames: `{t_s, from:[lat,lon], to:[lat,lon], jump_m, cause}`
(+ `replaced_span_s:[t_enter, t]` for a replay). The app draws these segments dashed (never as driving).

| cause | meaning |
|---|---|
| `gnss_rejoin` | a GNSS update at this frame (a fix after a dead-reckoning stretch, incl. the first fix after an outage) |
| `launch_cal` | a launch calibration was accepted at this frame (vehicle_dr.py:711-722 moves position by the distance already driven) |
| `replay` | an S1d replay fired: the filter re-ran `replaced_span_s` without a false standstill; the frame jumps to the corrected state |
| `other` | none of the above. On S3b this is the IMU standstill entry at 224.7 s (7.1 m): the ungated ZUPT moves position through the speed/position cross-covariance. |

S3b (outage 200-260 s): 47 corrections — 44 gnss_rejoin, 1 launch_cal (91.9 s, 5.3 m), 1 replay (271.0 s, 159.5 m), 1 other.
The rejoin is two steps: at 262.1 s the first fix's position is gate-rejected (d² = 9.9 > 9.21; only its speed update is
accepted, 38.2 m step), and at 271.0 s the replay accepts the next fix's position (159.5 m step).

## Scoring (not part of the app contract)

`backend/score_export.py <export>` scores ONLY the export's frames against VBOX with check_outage's method and writes
`<drive>_metrics.json` (`reference_role: "scoring_only"`, `in_sample: true`). The app may show these numbers, labelled
as in-sample development results; it must never compute its own error from a bundled reference track.

## What the mobile app must change (branch `mobile` @ c32c145, read-only review)

Paths are relative to `mobile/app/src/main/java/com/aeris/mobile/` unless they start with `mobile/`.

1. **One object, not arrays.** `DriveAdapter.parseTrajectoryPoints` reads each asset as a top-level array
   (`domain/adapter/DriveAdapter.kt:97` `JSONArray(jsonString)`; files at `:27`, `:29`, `:34`). aeris-trip/1 is one
   object: read `frames`, `gnss`, `outages`, `corrections`, `meta`.
2. **Time is absolute.** `t_normalized` defaults to `true` (`DriveAdapter.kt:25`), with a 681.1 s fallback
   (`:24`) and `tSec = rawT * totalDurationSec` (`:106`). Use `t_s` directly; there is no `t`, and no duration
   multiplication.
3. **Status values.** `GnssStatus.fromString` (`domain/model/Drive.kt:13-18`) knows only healthy / outage / unavailable /
   degraded; `"gnss"`, `"dr"`, `"warmup"` all become `UNKNOWN`. Add them (gnss → locked, dr → dead reckoning,
   warmup → initialising). Outage shading must come from `outages[]`, not be inferred from frame status
   (`DriveAdapter.kt:52`, `EventDetector.detectOutagesAndEvents`).
4. **Ellipse angle convention.** `EllipseMath.computeEllipse` uses `orientation = 0.5·atan2(2·covXY, covXX − covYY)`
   = major axis in **radians counter-clockwise from East**, range (−π/2, π/2] (`domain/math/EllipseMath.kt:57-58`;
   used at `:81-91`). Ours is **degrees clockwise from North**, [0, 180). Conversion:
   `orientationRad = Math.toRadians(90.0 - ellipse_angle_deg)` (equivalent modulo π). Simplest: pass
   `covXX = cov_en_m2[0]`, `covYY = cov_en_m2[1]`, `covXY = cov_en_m2[2]` to `computeEllipse` unchanged. Note it also
   clamps both semi-axes to ≥ 0.5 m (`:61-62`).
5. **Pair by time, never by index.** `SimulationEngine` pairs `fusedData[i]` with `gnssData[i]`
   (`core/simulation/SimulationEngine.kt:106-110`), and `DriveAdapter.calculateMetrics` pairs `fused[i]` with
   `groundTruth[i]` (`DriveAdapter.kt:182-185`). GNSS must be matched by `t_s` (latest fix with `t_s <= frame.t_s`),
   and in-app metrics must come from `<drive>_metrics.json`, not from comparing against a bundled reference.
6. **Invented ellipse.** `PlaybackAndLiveSources.kt:37-42` builds the ellipse as `semiMajor = sigma`,
   `semiMinor = 0.75 × sigma`, `orientation = heading` — none of that is filter output (and `sigma` is read from
   `uncertainty`, `DriveAdapter.kt:108`, which in the old exports is a covariance TRACE in m², not metres). Use
   `sigma_major_m`, `sigma_minor_m`, `ellipse_angle_deg` (or `cov_en_m2`).
7. **Remove the VBOX-derived assets.** `mobile/app/src/main/assets/fused_output.json` (byte-identical to main's
   `frontend/src/data/fused_output.json`, the `--sim-aided` export snapped onto the VBOX track: median 0.14 m from it,
   4 m mean outage error), `mobile/app/src/main/assets/metadata.json` (identical to main's, hand-made from that file)
   and `mobile/app/src/main/assets/reference_trajectory.json` (the VBOX track itself, identical to
   `backend/exports/evaluation/outage_60s/reference_trajectory.json`) must be deleted and replaced by
   `S3b_aeris_trip_v1.json` (+ optionally `S3b_metrics.json`). `gnss_only.json` (also identical to main's) is superseded
   by `gnss[]`.
