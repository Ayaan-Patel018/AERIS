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
