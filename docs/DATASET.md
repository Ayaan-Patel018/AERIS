# Dataset Reference — IO-VNBD

Source: github.com/onyekpeu/IO-VNBD (Onyekpe et al., Coventry University). CSV format, Python dev tools included. Full paper: `README_1.pdf` (repo root).

## Terminology decision (locked)
We do **not** call the VBOX-derived trajectory "ground truth." We call it **`reference_trajectory`**, because it's a dedicated GPS+CAN logger (Racelogic VBOX, 10 Hz), not RTK-grade. This is more defensible under judge questioning and costs nothing.

- `V-*` files → **reference trajectory** (VBOX GPS + CAN bus, from the vehicle)
- `S-*` files → **our actual pipeline input** (smartphone IMU + smartphone GPS) — this is what a real phone-only system would see, which is exactly our problem statement

Exported JSON files are named accordingly: `reference_trajectory.json`, `gnss_only.json`, `fused_output.json` — never `ground_truth.json`.

## Chosen MVP sequence
**Primary: `V-S3b` / `S-S3b`** (Driver A, Rugby) — 11.4 min, 6,840 points, features: Successive Left-Right Turns (×21), Reverse/U-turn (×1). Short enough to iterate fast; repeated turns are exactly what shows NHC constraints working visibly.

**Backup: `V-Vta2` / `S-Vta2`** (Driver E) — 18.3 min, roundabouts + A-road + country road + hard brake. Use if V-S3b has data-quality issues.

Both are in the `Synchronised V and S datasets` folder (paper: sequences collected simultaneously are manually synced there; unsynced ones aren't).

## V-* format (VBOX, 10 Hz) — 29 columns
| # | Column | Unit | Load-time conversion |
|---|---|---|---|
| 1 | No. of GPS satellites | N/A | — |
| 2 | Time since start of day | seconds | → canonical `timestamp_s` (see below) |
| 3 | Latitude | degrees | — |
| 4 | Longitude | degrees | — |
| 5 | Velocity | km/h | **→ m/s** |
| 6 | Heading | degrees | — |
| 7 | Height | km | — |
| 8 | Vertical velocity | km/h | **→ m/s** |
| 9 | Sample period | seconds | — |
| 10 | Steering angle | degrees | — |
| 11–14 | Wheel speed FL/FR/RL/RR | rad/s | — |
| 15 | Yaw rate | deg/s | — |
| 16 | Indicated vehicle speed | km/h | **→ m/s** |
| 17 | Indicated longitudinal accel | g | **→ m/s²** |
| 18 | Indicated lateral accel | g | **→ m/s²** |
| 19 | Handbrake | 0/1 | — |
| 20–21 | Gear requested / Gear | number | — |
| 22 | Engine speed | rev/min | — |
| 23 | Coolant temp | °C | — |
| 24 | Clutch position | 0/1 | — |
| 25 | Brake pressure | PSI | — |
| 26 | Brake position | 0/1 | — |
| 27 | Battery voltage | V | — |
| 28 | Air temperature | °C | — |
| 29 | Accelerator pedal position | % | — |

## S-* format (AndroSensor smartphone app, IMU ~10 Hz / GPS 1 Hz) — 24 columns
| # | Column | Unit | Load-time conversion |
|---|---|---|---|
| 1 | GPS Latitude | degrees | — |
| 2 | GPS Longitude | degrees | — |
| 3 | GPS Altitude | m | — |
| 4 | GPS Speed | km/h | **→ m/s** |
| 5 | GPS Accuracy | m | — |
| 6 | GPS Orientation | ° | — |
| 7 | GPS Satellites In Range | N/A | — |
| 8 | Time Since Start | ms | → canonical `timestamp_s` |
| 9 | Date | YYYY-MO-DD HH-MI-SS_SSS | keep as-is, secondary reference |
| 10–12 | Accelerometer X/Y/Z | m/s² | already SI — **but includes gravity, see below** |
| 13–15 | Gravity X/Y/Z | m/s² | provided separately by the app |
| 16–18 | Gyroscope Yaw/Roll/Pitch | rad/s | ⚠️ paper's own table lists "Pitch" twice — axis mapping needs confirming against the real CSV header or the dataset's GitHub tools, don't assume |
| 19–21 | Magnetic Field X/Y/Z | μT | — |
| 22–24 | Orientation Yaw/Roll/Pitch | ° | — |

**Gravity is provided as its own set of columns** — meaning `linear_accel = accelerometer − gravity` per axis is a direct subtraction, not something we need to estimate from a stationary window. This simplifies Part II's preprocessing step *if* it holds true in the actual CSV — confirm before relying on it.

## Timestamp canonicalization (mandatory, do this immediately after loading, before anything else)
Both `V-*` and `S-*` use different clocks and units for time. Immediately after loading either file, compute a canonical column:
```
timestamp_s   # float seconds, monotonically increasing, starts at 0 for the sequence
```
while **keeping the original raw timestamp column too** (for traceability/debugging). Do this in the loader itself — nothing downstream (INS, EKF, JSON export) should ever touch the raw per-file timestamp format directly.

## Open items — ALL RESOLVED (confirmed against real S-S3b.csv and V-S3b.csv)
- [x] Header row present in both files — column names can be read directly
- [x] Gyroscope axis order confirmed: **Yaw, Pitch, Roll** (paper had a typo listing Pitch twice)
- [x] Gravity columns confirmed populated in S-S3b (e.g. `GRAVITY Z ≈ 9.8066 m/s²`)
- [x] `GPS SATELLITES IN RANGE` in S-* is a **string** like `"16 / 18"` (visible/in-range) — not a plain integer; parse the first number only
- [x] V-* timestamp: "Time Since Start of Day (seconds)" — float seconds from midnight
- [x] S-* timestamp: "TIME SINCE START (ms)" — integer milliseconds from sequence start
- [x] V-* acceleration: in **g** (e.g. `-0.019 g`) — must convert to m/s² at load time
- [x] S-* acceleration: already in **m/s²** — no conversion needed

## Known discrepancy (non-blocking, investigate when convenient)
`V-S3b`'s first column (paper calls it "No of GPS Satellites Available") produces implausible values when loaded (mean=97.7, max=137 — impossible for real satellite counts). Likely the actual VBOX CSV column order doesn't exactly match the paper's Table 3. **Not renamed to `gps_satellites`** in the loader — kept as `vbox_col1_raw` and unused downstream, so it doesn't propagate bad data into the EKF. Confirm real column identity with `Get-Content ... -First 1` on the raw file when there's spare time; not required for Part II.
