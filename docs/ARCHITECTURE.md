# Architecture Reference

Condensed from the full design doc. This is the version to keep updated as the actual source of truth — if implementation deviates from this, update this file in the same PR.

## Pipeline (high level)

```
Accelerometer + Gyroscope + Magnetometer (IMU) + GNSS/NavIC
        ↓
Sensor Sync & Buffering (100 Hz IMU, 1 Hz GNSS)
        ↓
Preprocessing (Butterworth filter, bias removal, gravity estimation)
        ↓
Phone-to-Vehicle Alignment (gravity → pitch/roll, GNSS course → yaw)
        ↓
   ┌────────────────┬─────────────────────┐
   │ AI Velocity     │ Classical Strapdown │
   │ Estimator       │ INS                 │
   │ (CNN + GRU)     │ (quaternion-based)  │
   └────────────────┴─────────────────────┘
        ↓
   AI Bias Corrector (small MLP)
        ↓
   GNSS Quality Detector (threshold + lightweight classifier)
        ↓
   Error-State EKF (15-state: pos, vel, attitude, accel bias, gyro bias)
        ↓
   Non-Holonomic Constraints (lateral/vertical velocity ≈ 0)
        ↓
   Map Matching (HMM + Viterbi, OSM road graph)
        ↓
   Confidence Estimation (covariance + map-match quality)
        ↓
   Output: position, velocity, heading, confidence @ 10 Hz
```

## Module table

| Module | Input | Output | Algorithm | Failure mode if it breaks |
|---|---|---|---|---|
| Sensor sync | Raw sensor events | Synced 100 Hz frames | Timestamp alignment | Timing drift → fall back to interpolation |
| Preprocessing | Synced frames | Cleaned accel/gyro | Butterworth + Madgwick | Noisier downstream signal, not catastrophic |
| Alignment | Cleaned data + GNSS | Phone→vehicle rotation | Complementary filter | **High risk** — wrong "forward" corrupts everything downstream |
| AI velocity estimator | 2s IMU window (200×6) | 2D velocity + confidence | CNN + BiGRU (~2M params) | Fall back to classical integration + aggressive NHC |
| Classical INS | Cleaned IMU, attitude | Position/velocity/attitude | Quaternion strapdown | Must never fail — this is the safety net |
| AI bias corrector | Filter state + IMU stats | Bias correction deltas | MLP (~500K params) | Skip correction, EKF still functions |
| GNSS quality detector | Sat count, SNR, HDOP, IRNSS flag | healthy/degraded/unavailable/anomalous | Threshold + light classifier | Fall back to simple threshold checks |
| ES-EKF | All of the above | Fused state + covariance | Error-state EKF | **Highest silent-failure risk** — bad tuning ≠ visible crash, just bad output |
| NHC | Filter state | Pseudo-measurements | Physics constraint | Cheap, low risk, high payoff — do this before ML |
| Map matching | EKF position, road graph | Road-constrained position | HMM + Viterbi | Fall back to nearest-road matching |
| Confidence | Covariance + map quality | 95% error radius | Heuristic combination | Display "unknown confidence" rather than fake precision |

## Explicitly NOT building (anti-overengineering)
LLMs, cloud inference, end-to-end learned odometry, full turn-by-turn routing, custom hardware, 3D visualization, multi-vehicle/V2V, blockchain, OBD-II integration, pedestrian mode, camera/visual-inertial odometry, transformer architectures, barometer-based vertical positioning.

## MVP definition (what must work for a passable demo)
- Vehicle moving on map with live GNSS
- Simulated GNSS removal → position keeps updating smoothly (no teleport, no freeze)
- IMU + map constraints hold position reasonably during outage
- GNSS returns → smooth correction, no visible jump
- Target: drift < 30 m after 30 s outage, 10 Hz update rate

## Advanced (only after MVP is solid)
AI velocity estimator, bias corrector, GNSS quality classifier, HMM map matching (vs. nearest-road), confidence display, custom smartphone data fine-tuning.

## Known open questions (resolve before committing further design time)
- [ ] Is IO-VNBD actually downloadable and does its format match what's assumed here? — verify in Phase 1, don't assume.
- [ ] Does our target Android test device(s) expose NavIC/IRNSS via `GnssStatus`? — verify early, this affects the whole NavIC-relevance story.
- [ ] Do we have any access to RTK-grade ground truth, or are we explicitly scoping accuracy claims to consumer-GNSS-bounded?

## Presentation Website (MVP) — Tech Stack

**Decision:** given limited time before presentation, the demo is a static web visualization of precomputed trajectories, not a live Android app. No backend, no live sensors — the Python pipeline (Phase 2–4) exports static JSON, the website replays it.

| Layer | Choice |
|---|---|
| Build tool | Vite |
| Framework | React 18, plain JavaScript (no TypeScript) |
| Styling | Tailwind CSS |
| Map | Leaflet.js + react-leaflet, OpenStreetMap tiles (same OSM source as the map-matching module) |
| Charts | Recharts (position error vs. time, velocity comparison) |
| Data | Static JSON exported from the Python EKF/INS pipeline: `ground_truth.json`, `gnss_only.json`, `classical_ins.json`, `ai_enhanced.json`, `map_matched.json` |
| "Live" feel | `requestAnimationFrame` stepping through timestamped points — no real backend needed |
| Hosting | Vercel, auto-deploy from the repo |
| Folder | `/frontend` at repo root (matches AI-Dubbing-Engine convention) |

Setup:
```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install leaflet react-leaflet recharts
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Demo screen = map with overlaid colored trajectories (ground truth / GNSS-only / hybrid system) animated through a simulated outage, plus a live error/confidence chart beside it — this is the single figure Part 18 of the design doc calls the most persuasive visualization.
