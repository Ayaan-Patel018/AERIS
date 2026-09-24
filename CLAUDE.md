# AERIS — working rules

- Branch: `fix/heading-spin`. Never touch `main`.
- Venv: `nav-env`. Dataset: `./IO-VNBD` (S3b = main drive, S1 = unseen validation — run S1 once, never tune on it).

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
- Commit only when a result improves; revert and log why when it gets worse.
- Never `git stash pop`.
- Stop and ask before any big redesign.
