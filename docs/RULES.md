# Team Rules

Non-negotiable working rules for this repo. Everyone reads this once before their first push. These exist because all three of us generate code with AI tools (Claude/ChatGPT) that each have **different context about the project** — which means code that looks fine in isolation can quietly contradict decisions made elsewhere, use a different JSON schema, or step on the EKF core.

## Rule 1 — Backend code goes through Ayaan before it hits a shared branch
Ayaan owns ~90% of the backend and holds the full context on the processing pipeline. Therefore:
- **No one pushes backend code (INS, EKF, NHC, outage sim, GNSS detector, JSON export) to `main` or to any shared branch without Ayaan reviewing it first.**
- If you generated backend code with an AI tool, send the diff/file to Ayaan. He pre-checks it against the current architecture and merges it himself, or tells you what to change.
- This is specifically because AI tools each carry *different context* — a snippet ChatGPT wrote for Aryan may assume a different state vector, coordinate frame, or field name than the one Ayaan's pipeline actually uses. Precheck catches that before it becomes a merge conflict or a silent bug.

## Rule 2 — Nobody pushes directly to `main`
- Always work on a branch: `git checkout -b feature/short-description`
- Open a Pull Request into `main`; don't merge your own backend PR without Ayaan's sign-off.
- Frontend PRs can be merged once Aryan and one other person have looked, but must not change any backend file or the agreed JSON schema without backend sign-off.

## Rule 3 — The JSON schema is frozen once agreed, and only changed by agreement
The frontend and backend meet at the exported JSON files (`reference_trajectory.json`, `gnss_only.json`, `fused_output.json` — see docs/DATASET.md for schema). Once the schema is agreed (end of backend Part III):
- Neither side changes a field name, unit, or structure unilaterally.
- Any schema change is announced to both tracks and reflected in ARCHITECTURE.md in the same change.
- This is the single most likely place the two parallel tracks break each other — treat it as a contract.

## Rule 4 — Pull before you start, every session
`git checkout main && git pull origin main` before branching. Not once a day — every time you sit down.

## Rule 5 — Never force-push a shared branch
No `git push --force` on `main` or any branch someone else is on. It can silently delete a teammate's commit. If you think you need it, ask first.

## Rule 6 — Small, described commits
Clear messages, frequent commits. `git status` before every commit to confirm you're staging what you think you are. A giant end-of-day commit is hard to review and hard to roll back.

## Rule 7 — Log the session
Whoever does meaningful work updates `docs/PROJECT_LOG.md` with a dated entry (what changed, what was decided, what's still open) before ending the session. This is how the next person — or the next AI tool given this repo as context — knows the real state.

---

### Quick pre-push checklist (backend)
- [ ] Did I branch off an up-to-date `main`?
- [ ] Did I run `git status` and confirm only my intended files are staged?
- [ ] Is this backend code? → sent to Ayaan for precheck **before** the push/merge.
- [ ] Does it touch the JSON schema? → announced to both tracks, ARCHITECTURE.md updated.
- [ ] Did I add a PROJECT_LOG.md entry?
