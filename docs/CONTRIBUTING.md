# Git Workflow — Collaborator (not repo owner)

You've been added as a collaborator on `Codewiz-cpp/Intelligent_Dead_Reckoning_Navigation_System`, not the owner. This means you likely have push access, but you should still work on branches, not directly on `main`, so nobody's work gets overwritten.

## One-time setup

```bash
git clone https://github.com/Codewiz-cpp/Intelligent_Dead_Reckoning_Navigation_System.git
cd Intelligent_Dead_Reckoning_Navigation_System
```

If you were only invited but haven't accepted yet — check your GitHub notifications/email for the collaborator invite first; `git push` will fail with a permissions error until you accept it.

## Every time you start working

```bash
git checkout main
git pull origin main          # always pull before starting new work
git checkout -b feature/short-description   # e.g. feature/ekf-baseline
```

## While working

```bash
git add <files>               # stage only what you actually changed
git status                    # confirm what's staged before committing
git commit -m "clear, specific message"
```

## Pushing your branch

```bash
git push -u origin feature/short-description
```

First push on a new branch needs `-u` (sets upstream); after that, plain `git push` works.

## Getting your work into main
Open a Pull Request on GitHub from your branch into `main`, even on a small team — it gives the others a chance to see what changed before it's merged, and keeps a clean history of decisions (useful alongside PROJECT_LOG.md). Merge once at least one other teammate has looked at it, if the team agrees that's the norm.

## Keeping your branch up to date if `main` moves on while you're working

```bash
git checkout main
git pull origin main
git checkout feature/short-description
git merge main                # or: git rebase main, if the team prefers a linear history
```

Resolve any conflicts locally, test, then continue committing/pushing on your branch as before.

## Quick rules to avoid stepping on teammates
- Never `git push --force` on `main`, and avoid it on shared branches entirely.
- Pull before you start each session, not just once.
- Small, frequent commits with clear messages beat one giant commit at the end.
- If `git status` shows changes you don't recognize, stop and check with the team before committing — someone else's uncommitted work may be in your working directory only if you copied files manually; normal `git pull` won't cause this.
