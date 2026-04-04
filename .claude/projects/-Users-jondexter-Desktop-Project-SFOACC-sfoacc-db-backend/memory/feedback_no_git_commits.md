---
name: no_git_commits
description: Never run git commit commands — user handles all commits manually
type: feedback
---

Never run `git commit` or `git push` commands. The user commits manually.

**Why:** User explicitly instructed this. Running commits without permission was rejected.

**How to apply:** After making file changes, stop and tell the user what was done. Never stage or commit on their behalf. Staging (`git add`) is also best avoided unless explicitly asked.
