# Project Log

Timestamped, append-only. One entry per working session: what changed, what was decided, what's still open. Keep entries short — this is a decision trail, not a diary.

---

## 2026-08-28 — Kickoff / doc setup
**Did:** Set up PROJECT_BRIEF.md, ARCHITECTURE.md, ROADMAP.md, CONTRIBUTING.md as the carried-forward reference set for this project (mirroring the doc pattern used on AI-Dubbing-Engine).
**Decided:** Going with Architecture C (hybrid classical+AI), per the earlier architecture comparison. Build order starts with minimal classical EKF before any ML training, to de-risk EKF tuning early.
**Open:**
- Team roles not yet finalized
- IO-VNBD dataset access unverified
- NavIC/IRNSS constellation exposure on target Android devices unverified
- No demo-level fallback plan yet (module fallbacks only)

**Next session should start with:** Phase 0 checklist in ROADMAP.md.

---

## 2026-08-28 (later) — Presentation MVP pivot
**Did:** Decided the presentation demo will be a static web visualization instead of a live Android app, given limited time. Locked exact tech stack (Vite + React + Tailwind + Leaflet/react-leaflet + Recharts, static JSON from the Python pipeline, no backend, Vercel hosting). Updated ARCHITECTURE.md, ROADMAP.md (new Phase 6b), and PROJECT_BRIEF.md accordingly.
**Decided:** Native Android build stays on the roadmap but is not presentation-critical.
**Open:** Repo push access for Ayaan not yet confirmed (see below) — verify before Phase 6b work starts, since it needs to land in `/frontend` on the shared repo.

---

## 2026-08-29 — MVP sprint locked, roles + rules + requirements added
**Did:**
- Confirmed the 3-day MVP plan (SIH_26168 web-app plan): EKF+NHC core, one AI component (GNSS quality detector), no DL training, no Android, static-JSON web demo. Deadline Sept 4; sprint scoped Aug 29–31 with Sept 1–3 as buffer/rehearsal.
- Verified IO-VNBD is real and public: github.com/onyekpeu/IO-VNBD, CSV format + Python tools. **Correction logged:** dataset samples at ~10 Hz (GPS 1 Hz), NOT the 100 Hz assumed in the original architecture doc. Window/sample-count math must use 10 Hz.
- Reassigned roles for the MVP: Ayaan = backend lead (~90% of pipeline) + frontend secondary; Anurag = EKF core support + deployment; Aryan = frontend lead. Updated PROJECT_BRIEF.md.
- Added `RULES.md` (mandatory Ayaan precheck of AI-generated backend code before any shared-branch push; frozen JSON schema; no direct pushes to main).
- Added `requirements.txt` (numpy, pandas, scipy, scikit-learn, matplotlib optional, flask optional).
- Added `MVP_PLAN` PDF as the hour-by-hour sprint reference.

**Decided:** Static JSON export over live API for the MVP. GNSS quality detector is the single AI component. Map matching optional/nearest-road only.

**VVIP — doc maintenance rule:** All 7 markdown docs + requirements.txt are living files, updated over time (same practice as the AI-Dubbing-Engine project). Claude updates them proactively when new decisions/info land, and Ayaan flags updates too. Every meaningful session ends with a PROJECT_LOG.md entry.

**Open:**
- Confirm Node.js/npm present on Ayaan's machine
- Agree + freeze JSON schema at end of backend Part III (before frontend wires real data)
- Pick the specific IO-VNBD sequence(s) for the demo

**Next session should start with:** backend Part I (load one IO-VNBD sequence, confirm real shapes at 10 Hz) and frontend scaffold in parallel.

---

## 2026-08-29 (later) — Architecture doc enriched from full design source
**Did:** Re-read the full 27-part design doc and pulled in everything viable that the condensed version had dropped:
- Replaced the small pipeline sketch with the full 12-module block diagram (ARCHITECTURE.md), with a note that 100 Hz was the design target but IO-VNBD is ~10 Hz.
- Added "AI vs classical" defense table, the error-growth physics (bias → time² drift), and the EKF-vs-UKF-vs-particle-filter rationale — the three things judges probe hardest.
- Added condensed failure-modes table + the "seamless mode switching" explanation (why the tunnel transition looks smooth, not teleporting).
- Added the 15-concept learning list to PROJECT_BRIEF.md for the backend lead.
**Decided:** ARCHITECTURE.md is now the single richest reference; the original DeepSeek doc is archival only.
**Open:** unchanged from prior entry (Node.js check, JSON schema freeze, demo sequence pick).
