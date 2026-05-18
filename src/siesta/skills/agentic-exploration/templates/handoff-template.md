# `handoff.md`: session baton

`handoff.md` is the **handoff layer** — a short, cold-start-friendly note that tells future-you (or a teammate, or an agent in the next session) what to know to pick up where this session left off. It is written per-session, overwritten by the next session, and lives or dies on whether it can be read by someone with **zero prior context**.

The trap: writing it as a private journal that only makes sense to you in the moment. The test: imagine reading this in three weeks after working on something else. Would you know what branch you're on, what file to open, what the last failure was? If not, rewrite — explicit file paths, branch names, commit SHAs.

It costs 60 seconds to write and saves the next session 10+ minutes. This is one of the cheapest rituals with the highest compounded payoff.

## How to use this template

1. Copy the fenced block below into your project root as `handoff.md`.
2. **Overwrite it at the end of every session** that's not obviously wrapping up cleanly. An empty / "nothing in flight" handoff is also useful — it tells the next session there's no in-progress state to recover.
3. The next session reads this *before* `TODO.md` to know what's actually live vs. what's just-on-the-list.
4. If you're working in worktrees / parallel streams, each branch gets its own `handoff.md` — the file is local to the branch's session continuity.

## What does *not* go in `handoff.md`

- Discoveries that should outlive this session (→ `notes.md`).
- Project conventions (→ `AGENT.md`).
- Big-picture plan or phase reasoning (→ `plan.md` / `research_plan.md`).
- Anything that's already on `TODO.md` and not in flight — don't duplicate the roadmap.

---

```markdown
# Handoff — [🙋 YYYY-MM-DD HH:MM]

**Branch:** [🙋 branch name]
**Last commit:** [🙋 short SHA + one-line message — `git log -1 --oneline`]
**Working tree:** [🙋 clean / staged changes / dirty — describe what's not committed and why]
**Active TODO:** [🙋 TODO-XXXX from `TODO.md`, or "none — finished cleanly"]

## What got done this session

- [🙋 TODO-XXXX — one-line summary — commit SHA]
- [🙋 ...]

## What's in flight

[🙋 If you stopped mid-TODO, describe the state precisely. Cover:
- Which TODO
- What was tried (briefly)
- What worked / what failed
- The next concrete step — a file path, a function, a test to run, a hypothesis to check
- Any uncommitted changes and why they're not committed yet (don't leave the next session guessing whether a dirty file is intentional or forgotten)]

[🙋 If nothing is in flight, write "Nothing in flight — session closed cleanly." and delete the bullet template above.]

## What's blocked

- [🙋 Blocker — what's needed to unblock — who or what owns the unblock]

## Where to start next session

Read in this order:

1. [🙋 The specific file path most relevant to the in-flight work, with line number if applicable]
2. [🙋 The relevant `notes.md` section if any live diagnoses are still open]
3. [🙋 `TODO.md` → TODO-XXXX if a fresh TODO is up next]

## Weird stuff / warnings

[🙋 Anything the next session should be warned about:
- A test that's failing in a way that isn't yet diagnosed
- Flaky behavior that came and went this session
- A dependency that needed a workaround
- A decision being deferred — what the options are, what would tip it
- Anything that surprised you and you didn't have time to log into `notes.md`]

[🙋 If nothing weird, delete this section.]
```
