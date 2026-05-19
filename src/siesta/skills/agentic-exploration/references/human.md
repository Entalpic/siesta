# `Human.md`: researcher manifesto

`Human.md` is your **researcher's manifesto** for the repo. It is the canonical statement of the philosophy you're working under: what you own, what the agent owns, why the discipline matters, the document hierarchy that holds everything together, and the rituals that keep the project from regressing to ad-hoc. The agent reads it at high-stakes / long-session moments to ground its judgment; you read it once at project start, then re-read at every phase boundary and once a week as part of hygiene.

This file is *yours*. The operational protocol the agent enforces lives separately, in the `agentic-exploration` skill — the skill loads the rules; `Human.md` carries the philosophy those rules rest on. If they ever drift, the skill is operational truth and `Human.md` is conceptual truth; reconcile both before moving forward.

## How to use this template

1. Read the manifesto end-to-end.
2. Fill in the `[🙋 …]`-marked placeholders across this file.
3. Don't let the agent edit this file without your sign-off. It's your manifesto, not its protocol.

## What does *not* go in `Human.md`

- Project-specific rules for the agent (→ `AGENT.md`).
- The research question, approach, methodology, success criteria (→ `research_plan.md`).
- Today's task or work-in-flight (→ `TODO.md` / `handoff.md`).
- Library quirks, debugging diagnostics, failed experiments (→ `notes.md`).
- Per-layer maintenance details (→ [`.claude/skills/agentic-exploration/doc-hierarchy.md`](.claude/skills/agentic-exploration/doc-hierarchy.md)).
- Operational rules for the agent (→ the `agentic-exploration` skill at `.claude/skills/agentic-exploration/SKILL.md`).

If `Human.md` starts looking like a second `CLAUDE.md`, or like a duplicate of the skill, you've lost the split. The fix: re-read [`AGENT.md`](AGENT.md), this file, and the skill side-by-side; whatever overlaps probably belongs in only one of them.

---

# [🙋 Project name]

[🙋 One sentence: what this project is investigating, and what would count as success.]

## What this file is, and why it's here

This is your orientation in this repo. The philosophy you've signed up for by working in an agent-augmented way: what you own, what the agent owns, why the discipline matters, how the project's documents compose. When the agent enforces a rule (refuses a vague task, asks for a contract, prompts the discipline check), the reasoning behind that rule lives here — not in the skill that loads the rule.

The agent does not edit this file without your sign-off. The agent *reads* it once at session start if you instruct it to, and uses it to ground judgment in high-stakes moments. The operational protocol — what the agent actually does, step by step — lives in the `agentic-exploration` skill at `.claude/skills/agentic-exploration/SKILL.md`. That's where the rules live. This is where they're explained.

When in doubt: this file is canonical philosophy; the skill is canonical operational. Re-read this file when the workflow feels off.

## What you own; what the agent owns

This is the load-bearing idea. Get this wrong and nothing else helps.

**You own:**

- The question. What are we trying to learn or settle?
- The success criterion. What result, with what confidence, would answer the question?
- The scope. What's in, what's out, why.
- The judgment of whether a result is believable. Tests passing is necessary, not sufficient.
- Every commit that touches data, conclusions, or anything destructive.
- Every claim in the eventual delivery.

**The agent handles:**

- Implementation *inside a contract you wrote* — tests, types, acceptance criteria.
- Mechanical refactors and consistency sweeps.
- Search and retrieval (literature, prior code, library docs).
- Scaffolding — directory layout, boilerplate, test harness.
- Debugging mechanics — reproduce, bisect, narrow down — then surface to you.
- Drafts of docs you will revise.

**The contract is your tool of control.** Tests, type signatures, docstrings, explicit DO-NOTs, acceptance criteria — you write these *before* the agent generates. The agent works inside them. Without a contract, you have not delegated *labour*; you have delegated *meaning*, and the agent will fill the meaning in for you, plausibly and potentially wrongly.

**Never delegate** the research question, the success criterion, the scope, the judgment call on a result, or anything irreversible. The agent can help you *think* about these — surface options, name trade-offs — but the decision is yours, every time. If you catch yourself asking "is this result good?", that's the signal you're about to delegate something you shouldn't. Take it back.

## Why the discipline matters

Five principles drive everything below. They are stated tersely; the rest of this file is their elaboration.

1. **You own the *what* and *why*; the agent handles the *how*.** The contract is where you encode meaning. Everything else is mechanics.
2. **Your docs are your thinking tools first, agent inputs second.** Externalizing the project structure is how you stay coherent across sessions. The agent gets rehydrated from these docs each time — but the docs exist for you.
3. **Generations become your context.** Sloppy agent output contaminates *your* thinking on the next session, not just the next agent's. A hundred bad lines from one unclear prompt cost you long after the prompt is forgotten. Keep the bar high.
4. **Stabilize at the top, mutate at the bottom.** Project documents have different mutation rates. Anchor the high-stability things (question, approach, architecture, philosophy) so the low-stability things (today's TODO, current diff) can mutate quickly without losing the plot.
5. **Drift is the default; discipline is a verb.** Without active maintenance, every project regresses to ad-hoc. Setup is one-time; hygiene is forever. The agent in each session is your accomplice in enforcing the pattern — including against your own short-term-pressure self. Welcome the pushback.

## The document hierarchy

Layer your project across documents organized by how often each changes. Each layer answers a different question.

| Layer | File(s) | Mutation rate | Answers |
|---|---|---|---|
| Anchor | `research_plan.md` (or `design_doc.md`), external refs | rarely | *What question are we answering, and how?* |
| Researcher manifesto | `Human.md` (this file) | rarely | *What philosophy am I, the researcher, signed up for in this repo?* |
| Architecture | `AGENT.md` / `CLAUDE.md`, `README.md` | occasionally | *How do we work in this repo?* |
| Roadmap | `plan.md`, `TODO.md` | weekly-ish | *What's the next chunk of work?* |
| Discoveries | `notes.md` | continuously | *What did we learn the hard way?* |
| Handoff | `handoff.md` | per-session | *What does future-me (or a teammate) need to know to pick up?* |
| Code + tests | the actual repo | continuously | the implementation |

The trap to avoid: dumping everything into one giant `CLAUDE.md`. It bloats, drifts, and gets ignored. Keep each layer focused and link between them.

For per-layer details — what goes where, what the trap is, what the maintenance rhythm looks like — see the deep-dive appendix at `.claude/skills/agentic-exploration/doc-hierarchy.md`. Come back to it during weekly compaction or when a layer feels wrong.

For a starting `AGENT.md`, see `.claude/skills/agentic-exploration/references/agent.md`.

## Scoping a task — linearizing the roadmap

The biggest single lever on agent productivity is task scoping. Most "the agent did a bad job" outcomes trace back to a task that was too big, too vague, or under-constrained.

A well-scoped TODO has:

- **Landmarks.** Concrete file paths, function names, line numbers the agent can navigate to. Not "improve the dataloader" — "extend `load_batch` in `src/data/loader.py:42` to support the new shard layout described in plan.md §3".
- **Constraints written first.** Tests, type signatures, docstrings, and explicit DO-NOTs *before* the implementation prompt. Pre-specifying the contract reduces the space of generations and prevents the agent from reimplementing things you already have.
- **Single responsibility.** One TODO = one commit. If you can't summarize what the commit will do in one line, the TODO is too big — split it.
- **Verifiable acceptance.** How will you know it's done? A passing test, a specific output, a generated figure. If it's "looks good to me", you'll iterate forever.

Why this matters: an under-constrained task lets the agent fill context with guesses. Those guesses become code. That code becomes the context for the *next* task. The cost compounds.

Scoping is **your** judgment call. The agent can suggest splits and propose drafts, but you decide what a single commit looks like. The agent will refuse vague tasks until you write the contract — that's working as intended.

## The inner loop — your discipline practice

For each TODO, walk through this loop. Every step has an owner. The agent will hold you to this — these eight steps are also the agent's enforcement checklist (in the skill). What looks like the agent "blocking" you is the agent doing the job you configured.

1. **Explore.** You direct what to read; the agent fetches and summarizes for your review into `notes.md`. Don't let it grep the whole repo.
2. **Plan.** You sketch the approach in a paragraph. The agent can expand it for your sign-off, but the load-bearing decision is yours.
3. **Constrain.** You write the contract: the test that must pass, the type signature, the docstring, the explicit DO-NOTs. This is where you keep ownership of meaning. **Don't skip this step under time pressure** — skipping it once is how the pattern erodes.
4. **Generate.** The agent implements inside the contract.
5. **Verify.** The agent runs tests; **you read the diff and judge**. Tests are necessary, not sufficient. Your eyes are the last gate.
6. **Commit.** You approve. **One TODO = one commit** — no drive-by edits, no bundled unrelated changes. Atomic commits make `git bisect` and `git log -S` useful tools instead of archaeology. Use **Conventional Commits** style for the message — `<type>(scope): <imperative description>` (e.g. `fix(loader): off-by-one in load_batch shard boundary`, not `fixes`). Common types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`. The agent can draft the message; you sign off. Future-you and future agents will read these to localize regressions — write for them.
7. **Handoff.** If you're stopping mid-roadmap, write `handoff.md` for future-you. An agent draft is fine as a starting point; you revise.
8. **Discipline check.** The small step that keeps the workflow alive. Before closing the iteration, three questions (the agent will prompt you with these):
   - Did any new pattern emerge that should live in `AGENT.md` rather than be relearned next session?
   - Did any learning surface that should be promoted from `notes.md` into `research_plan.md`?
   - Did this iteration require *you* to make a judgment call worth remembering?

   Two minutes per TODO. This is not paperwork — it is the discipline that compounds. Skipping it once is fine; skipping it for ten TODOs in a row is how projects rot.

## Maintaining the pattern — the continuous loop

Setup is one chapter. The rest is hygiene. Without active maintenance, every project regresses to ad-hoc — and you won't notice until three months in, when `research_plan.md` doesn't describe what you're doing and `notes.md` is 1200 lines no one reads.

**Three cadences of maintenance.** Different docs decay at different rates and need different rituals.

- **Per-iteration** (every TODO): the discipline check at step 8 above. Two minutes. The cheapest ritual; the highest compounded value.
- **Per-phase** (every time you finish a milestone in `plan.md`): re-read `research_plan.md` and `Human.md` front-to-back. Has the approach in the doc kept up with the approach in the code? Has anything in the philosophy actually changed? If yes, edit; if no, you've just re-grounded yourself for the next phase. Fifteen minutes.
- **Per-week** (or per-N sessions): audit. Compact `notes.md` — promote what's stable into `AGENT.md` or `research_plan.md`, prune what's stale. Check `AGENT.md` against the agent mistakes you've actually been catching this week: is there a missing rule? Re-read your last three `handoff.md` files: are they still useful, or are they getting skipped? Half an hour; one hour if `notes.md` is overdue.

**Drift signals — learn to spot them.** Each one is a leading indicator that the workflow is eroding:

- You catch yourself prompting an agent for something vague because writing the contract felt slow.
- The agent makes the same kind of mistake twice in a week and `AGENT.md` is unchanged.
- `notes.md` is longer than ~400 lines and you can't remember when you last re-read it end-to-end.
- `research_plan.md` doesn't mention the thing you've been working on for two weeks.
- A new session of yours can't be picked up from `handoff.md` alone — you need to scroll back through history.
- Commits are landing without a corresponding TODO line item.
- You're tempted to "just do this one outside the workflow because it's small". Especially this one.

When you see any of these, fix the discipline *before* the next TODO. Drift compounds.

**The agent is your accomplice in the discipline.** When the agent refuses a vague task, pushes back on skipping the constrain step, surfaces a diff-vs-intent mismatch at verify time, suggests writing a handoff when you mention context-switching, flags `notes.md` getting unreadable, or refuses to merge a commit without a TODO line item — that pushback is *your* pre-committed discipline working against your in-the-moment shortcut self. Welcome it.

## Independence between implementation and verification

**You are the irreducible verifier.** Tests written by an independent agent are good practice — they reduce blind-spot overlap — but no test suite signs off on whether a result is believable. You do.

- **Write tests in a separate session** from implementation. Different context, different blind spots.
- **External review** by you, or by an agent that didn't see the implementation, against the research plan and external references — useful, but a complement to your judgment, not a substitute.
- **Constraints from outside.** Specs, examples to copy from, and failure-mode lists come from you or from a literature / prior-work session, not from the implementing session.

In exploratory work there's no production traffic to surface mistakes for you. The bugs you ship are the bugs in your conclusions — whether those conclusions land in a paper, a report, a notebook, or a Slack thread.

## Git as a savegame system

The agent can do the git mechanics for you cleanly — let it, but you remain the one who decides what gets committed and when to push. The rules:

- One TODO, one commit. No drive-by edits.
- Descriptive commit messages in Conventional Commits style (see step 6 of the inner loop). Future-you and agents read these to localize regressions.
- Use worktrees for parallel streams (different sessions on different experiments, syncing via `notes.md` and `plan.md`).
- Don't hand-edit history just to clean things up — the messy commits are evidence.
- When something breaks, bisect or `git log -S` *before* asking the agent to "fix it". You'll find the cause faster than re-prompting.
- **Never** let an agent execute irreversible git operations (force push, hard reset, branch delete) without your explicit confirmation. This is a human-only zone.

## Fail loud over silent fallbacks

Exploratory code's job is to be correct, not robust. A silent fallback (`try/except: pass`, default values for missing config, fallback model paths, silently-skipped rows) hides exactly the bugs that make your conclusions wrong. Tell the agent — in `AGENT.md` and per-task — to raise on unexpected state, avoid `try/except` unless specifically needed, assert preconditions explicitly, and prefer crashing in unit tests over `pytest.warns`.

Loud failures are the agent's main way of surfacing problems to your attention. A silent agent is a dangerous agent. The cost of a loud failure is annoyance; the cost of a silent one is a wrong answer you'll act on.

## Context economy and parallelism

Long context degrades performance — keep effective context lean even when the model technically supports more. You manage the budget:

- Aim to stay well under the model's stated context limit; performance drops well before the hard limit.
- Compact `notes.md` periodically — promote stable learnings into `AGENT.md` or `research_plan.md` and delete the scratch.
- Use cheaper/faster models for execution once the plan is locked; reserve thinking models for planning and review.
- Reset sessions between unrelated TODOs. The handoff doc is the bridge.

Parallel agent streams are *your* tool. They don't coordinate with each other — they work in isolation, against docs you maintain, and you reconcile the merge. The synchronization layer is your shared `plan.md`, your shared `notes.md`, and the codebase itself — not any kind of agent-to-agent protocol. Use worktrees for parallel branches. Run them in isolation, then merge. If streams need to talk to each other, you've split the work wrong.

## Anti-patterns

If you catch yourself doing any of these, fix the discipline before continuing.

**Ownership anti-patterns:**

- **Over-delegating meaning.** Asking the agent to come up with the research question, decide what counts as success, or judge whether a result is good enough. These are yours.
- **Auto-approving diffs.** If you didn't read the diff, you didn't make the change. Trusting "tests passed" as a proxy for correctness lets confidently-wrong code into the codebase.
- **Treating agent output as the answer.** The agent's job is to produce *evidence*; yours is to evaluate it.

**Drift anti-patterns:**

- **"Just this once" shortcuts.** Skipping the constrain step because the task is small. Committing without a corresponding TODO. Writing code without a test because "I'll add the test after". Each one is fine in isolation; the *habit* of allowing them is how the pattern dies.
- **Treating `AGENT.md` as written-in-stone.** It was a draft on day one. If the agent keeps making the same mistake and `AGENT.md` is unchanged, that's a missing rule, not an agent problem.
- **Letting `research_plan.md` lie.** Pivots that aren't reflected in the anchor doc become invisible decisions. Re-read weekly; edit before the next TODO.

**Structural anti-patterns:**

- **One mega-`CLAUDE.md`** containing personality, repo structure, every convention, and the project plan. It bloats and gets ignored. Split into the hierarchy above.
- **"Just figure it out" tasks** with no landmarks or acceptance criteria. The agent will fill context with guesses.
- **Empty-repo cold starts.** Warm start from a reference or stubs (`siesta project quickstart --explo`).
- **Same agent writes code and tests.** Separate them.
- **Try/except as a programming style.** It's hiding bugs.
- **Refactor sprees not tied to a TODO.** Surgical changes only.

## Project-specific notes

[🙋 who else works in this repo, and what conventions have you personally committed to with them?]

[🙋 anything weird about your collaboration setup — preferred working hours, blockers on irreversible operations, parallel-stream policies, anything that surprised a past collaborator and is worth surfacing.]

[🙋 any local rituals beyond the defaults above — e.g. you do a Friday compaction of `notes.md`, you require a written `handoff.md` before context-switching, you require a literature-search session before any modeling decision.]
