# Architecture Reference

Condensed from the full design doc. This is the version to keep updated as the actual source of truth — if implementation deviates from this, update this file in the same PR.

## Pipeline (high level)

Note: the 100 Hz rate below is the *original design-doc target*. The actual IO-VNBD dataset (and the AndroSensor smartphone capture it used) samples at **~10 Hz, GPS 1 Hz** — so for the MVP, IMU-window sample counts scale accordingly (a 2-second window is ~20 samples, not 200).

```
                        SMARTPHONE SENSORS
        ┌───────────────┬───────────────┬───────────────┐
        │ Accelerometer │   Gyroscope   │  Magnetometer │   + GNSS/NavIC
        │   (100 Hz)    │   (100 Hz)    │   (50 Hz)     │   (1 Hz pos+vel)
        └───────┬───────┴───────┬───────┴───────┬───────┘
                └───────────────┼───────────────┘
                                ▼
                 MODULE 1: SENSOR SYNC & BUFFERING
                 timestamp align, interpolate, 2s sliding window
                                ▼
                 MODULE 2: PREPROCESSING & CALIBRATION
                 Butterworth low-pass, DC bias removal,
                 gravity estimation (Madgwick/Mahony)
                                ▼
                 MODULE 3: PHONE-TO-VEHICLE ALIGNMENT
                 gravity → pitch/roll, GNSS course → yaw,
                 gyro integration for tracking through turns
                                ▼
         ┌──────────────────────┴──────────────────────┐
         ▼                                              ▼
 MODULE 4: AI VELOCITY ESTIMATOR         MODULE 5: CLASSICAL STRAPDOWN INS
 CNN + BiGRU, 2s IMU window →            quaternion attitude propagation,
 2D velocity (N,E) + confidence          gravity subtraction, double integration
         │                                              │
         ▼                                              │
 MODULE 6: AI BIAS CORRECTOR                            │
 small MLP → accel/gyro bias deltas                     │
         └──────────────────────┬──────────────────────┘
                                ▼
                 MODULE 7: GNSS QUALITY DETECTOR
                 sat count, SNR, HDOP/VDOP, IRNSS flag,
                 position-jump, INS-consistency →
                 HEALTHY / DEGRADED / UNAVAILABLE / ANOMALOUS
                                ▼
                 MODULE 8: ERROR-STATE EKF (15-state)
                 [δpos(3), δvel(3), δattitude(3), δaccel_bias(3), δgyro_bias(3)]
                 predict via INS; update with GNSS + AI velocity +
                 NHC + map-match + ZUPT measurements
                                ▼
                 MODULE 9: VEHICLE KINEMATIC CONSTRAINTS (NHC)
                 lateral vel ≈ 0, vertical vel ≈ 0,
                 turn-rate / acceleration limits
                                ▼
                 MODULE 10: MAP MATCHING (HMM + Viterbi)
                 OSM road graph, emission (dist+heading) +
                 transition (connectivity) probabilities
                                ▼
                 MODULE 11: CONFIDENCE ESTIMATION
                 EKF covariance + map-match quality →
                 95% error ellipse / confidence score
                                ▼
                 MODULE 12: OUTPUT / UI
                 position + velocity + heading + confidence @ 10 Hz;
                 blue dot, uncertainty circle, GNSS status badge
```

### Compact text version (for quick reference)
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

## What is AI vs. what is classical (defend this to judges)
The single most-asked question will be "where is the AI, and why isn't it just AI end-to-end?" This table is the answer.

| Component | AI/ML? | Classical? | Why |
|---|---|---|---|
| Coordinate transforms, gravity subtraction | No | Yes | Pure math — nothing to learn |
| Vibration/noise filtering | No | Yes | Butterworth frequency filtering is sufficient |
| Inertial propagation (INS) | No | Yes | Exact physics — must not be "learned" |
| Sensor fusion | No | Yes (EKF) | EKF is mathematically optimal here |
| Map matching | No | Yes (HMM) | Well-understood probabilistic algorithm |
| Kinematic constraints (NHC) | No | Yes | Direct physics constraint |
| Velocity estimation | **Yes** | fallback = integration | ML extracts speed from noisy IMU better than naive integration (deferred for MVP) |
| Bias estimation | Yes (complement) | Yes (EKF state) | EKF is primary; ML learns residual patterns (deferred for MVP) |
| GNSS quality / anomaly detection | **Yes** | partial thresholds | ML catches multipath/degradation patterns simple thresholds miss — **this is the MVP's AI component** |

Rule of thumb: AI is used only where the signal is too complex for hand-crafted features (velocity from IMU) or patterns too subtle for thresholds (GNSS quality). Everywhere physics is exact or math is optimal, classical wins.

## Why errors grow (the core physics, for the pitch)
Integrating a constant accelerometer bias twice makes position error grow with the **square of time**. A tiny 0.01 m/s² residual bias → ~0.5 m error after 10 s, ~18 m after 60 s, ~450 m after 5 min. Real smartphone biases are several times larger. This is *why* naive integration fails and why external corrections (GNSS, NHC, map, ZUPT) that periodically reset error growth are mandatory — no filter cleverness escapes this. This one fact justifies the entire architecture.

## EKF vs UKF vs Particle Filter (why we chose ES-EKF)
- **ES-EKF (chosen):** tracks *errors* not full state; avoids attitude singularities, numerically stable for small error angles, computationally cheap, industry standard for GNSS/INS. Best real-time fit.
- **UKF:** better on strong nonlinearity but 2–3× the compute and harder to debug — not worth it here.
- **Particle filter:** handles multi-modal cases (e.g. intersection ambiguity) but far too expensive for a 15-D state in real time.

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

## Failure modes worth naming (for the pitch / judge Q&A)
Condensed from the full failure analysis. Detection + mitigation in one line each.

| Failure | Mitigation |
|---|---|
| Phone moved/rotated in mount mid-drive | Sudden accel spike / new gravity direction → re-estimate alignment (for MVP, alignment is fixed, so note this as a known limitation) |
| Vehicle reverses / U-turns | Reverse detection in velocity + map-matching heading; increase heading uncertainty during sharp yaw |
| Heavy braking / speed bumps | Increase covariance during high-acceleration events; low-pass filter vertical spikes |
| Traffic stop-and-go | Zero-velocity update (ZUPT) when stationary — corrects velocity drift for free |
| GNSS multipath (urban canyon) | Quality detector flags degraded; increase GNSS measurement noise |
| GNSS spoofing / jamming | Reject GNSS inconsistent with inertial prediction; navigate inertially |
| Stale offline cache (production) | Label "offline verified, last synced X" — never fake full confidence |
| Android sensor rate inconsistency | Timestamp-based sync + interpolation; never assume exact 100/10 Hz |

## Seamless mode switching (the demo's smoothness depends on this)
The EKF has no explicit "modes." It simply uses whatever measurements are available each step. When GNSS is lost, its measurement weight drops to zero and covariance grows smoothly (no reset → no visible jump). When GNSS returns, the correction pulls the estimate back gradually, weighted by relative uncertainty — strong but continuous. **Never snap position to a fresh GNSS fix; let the filter blend.** This is what makes the tunnel entry/exit look seamless instead of teleporting.

## Presentation Website (MVP) — Tech Stack

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
