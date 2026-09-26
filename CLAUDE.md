# AERIS — working rules

- Branch: `fix/heading-spin`. Never touch `main`.
- Venv: `nav-env`. Dataset: `./IO-VNBD` (drive roles: see "Drive registry" below; never tune on S1 or S3c).

## Demo behaviour we need (honestly)
- 0–200 s: AERIS tracks GNSS closely and smoothly — no random curves or loops.
- 200 s: GNSS stops. GNSS is hidden on the map for 200–260 s. AERIS continues from exactly
  where GNSS stopped and follows the road using ONLY phone IMU + its own filter.
- 260 s: GNSS returns; both are shown again and AERIS rejoins smoothly.

## HARD RULE
Nothing shown as AERIS may use VBOX (`V-*.csv`) speed, heading, or path as an input.
VBOX is for scoring only. No snapping to the true path.

## Process
- One change at a time.
- Rerun `python backend/check_outage.py [drive]` after every change.
- Log every result (worked / didn't work, with numbers) in `AERIS_FINDINGS.md`.
- Never `git stash pop`.
- Stop and ask before any big redesign.

## Standing rules (from the E0 → D plan; full plan is in `AERIS_FINDINGS.md`)
- Branch `fix/heading-spin` only. Commit per step and PUSH after every commit (`git push origin fix/heading-spin`).
- Every step: (1) sandbox test first (`sim_drive.py`) with an explicit pass criterion, (2) real-data metrics, (3) row appended to the results table in
  `AERIS_FINDINGS.md`, (4) full test suite passes, (5) commit + push. If a step fails its criterion: keep the code behind a flag set to OFF, log why, and move on.
  (This replaces the older "commit only when a result improves" rule.)
- Never use `V-*.csv` or VBOX-derived values as a filter input. VBOX is for scoring only.
- Keep the reply tables compact; put the details in `AERIS_FINDINGS.md`.
- Before any /clear: update the handoff section of `AERIS_FINDINGS.md` (current defaults, flags, latest table, next step), commit, push.

## Drive registry
- S3b: tuning drive. Tune ONLY on data/windows that end before 200 s. The 200–260 s event is reported, never tuned on.
- S2, S4: training drives, ONLY for fitting the I3 vibration model offline. Never report accuracy on them as validation.
- S3c: final validation, untouched until B5 (no looking at its errors before then).
- S1: "previously inspected", secondary report only. S3a: reserve, untouched.
