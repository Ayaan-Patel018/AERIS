# Intelligent Dead Reckoning Navigation System

Smartphone-based vehicle navigation that keeps working through GNSS/NavIC outages (tunnels, urban canyons, jamming) using IMU sensor fusion, a hybrid classical + AI approach, and map-constrained positioning.

Built for SIH — ISRO problem statement on ground vehicle positioning without OBD-II.

## Docs
- [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md) — problem, approach, team, current status
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — full pipeline, module breakdown, MVP scope, presentation website stack
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — 3-day MVP sprint + full production arc
- [`docs/PROJECT_LOG.md`](docs/PROJECT_LOG.md) — running decision log, updated every session
- [`docs/RULES.md`](docs/RULES.md) — team working rules; **read before your first push** (AI-generated backend code must be prechecked by Ayaan)
- [`docs/DATASET.md`](docs/DATASET.md) — IO-VNBD V-*/S-* column reference, terminology (`reference_trajectory` not `ground_truth`), chosen MVP sequence, timestamp canonicalization rule
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — git workflow for collaborators
- [`requirements.txt`](requirements.txt) — backend Python dependencies

## Status
Pre-code — architecture and presentation-MVP scope decided, kickoff (Phase 0/1) not yet started. See PROJECT_LOG.md for the latest.

## License
MIT — see [LICENSE](LICENSE).
