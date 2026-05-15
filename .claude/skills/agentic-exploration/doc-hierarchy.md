# Document hierarchy: what goes where

An exploratory project that's friendly to agent-augmented work spreads its context across several files, each with a different mutation rate. This file explains what each layer is for, what belongs in it, the traps to avoid, and the rhythm that keeps it healthy as the project ages.

The principle behind the split: high-stability docs anchor the project so low-stability docs (and the codebase) can mutate quickly without losing the plot. A single bloated `CLAUDE.md` buries the signal in noise; a hierarchy that drills from `research_plan.md` → `plan.md` → `TODO.md` → `notes.md` lets you (and any agent you pair with) recover context cheaply at the right level of detail.

The hierarchy is **yours to maintain**. An agent reads from it and appends to it under your direction, but you own what gets promoted, pruned, or rewritten. The hierarchy survives only if you actively curate it; without curation, every layer slowly decays toward the others (the plan creeps into notes; the notes creep into the plan; the agent rules go stale) and you end up back at one bloated file or no docs at all.

The deliverable might be a paper, a report, a notebook, a recommendation, a launch decision, or just an answer to a question — the structure is the same. Where this file says `research_plan.md`, you can equivalently use `design_doc.md`, `investigation.md`, `proposal.md`, or whatever name fits your team's vocabulary. Pick one and stick with it across the project.

## Anchor layer: `research_plan.md`

**Mutation rate:** rarely (weeks-to-months between meaningful edits).

**Answers:** What question are we trying to answer? What's the approach? What's the architecture? What does success look like? What are we *not* doing and why?

**Contains:**

- The question or hypothesis, framed for the intended audience (a teammate, a reviewer, your future self, a decision-maker). Name the comparison or baseline if there is one.
- Approach — the actual idea, written for someone with relevant background. If you can't write this clearly, the project isn't ready to start.
- Architecture sketch — the modules / data flow / training loop / analysis pipeline / evaluation harness at a level above code.
- Roadmap at the milestone level (not the TODO level): "phase 1, baseline reproduction; phase 2, ablations; phase 3, the new thing". Or: "phase 1, get the data clean; phase 2, fit candidate models; phase 3, write up findings".
- Out-of-scope list. What you're explicitly *not* building or investigating.
- Pointers to external references (papers, codebases, datasets, internal docs, prior experiments) the project depends on.

Every line here is something you can defend in a meeting. If an agent drafted a line you can't justify, delete it.

**Trap:** writing this as a draft of the final write-up *prose* and then never updating it. Treat it as a living plan. When the approach changes in the code but not here, you've started lying to yourself silently. The fix is the per-phase ritual: re-read this file front-to-back at every milestone and edit it before starting the next TODO.

**For agents:** this is the file the agent reads when it needs to make a *judgment call about scope* — but the judgment call itself is yours. The agent surfaces the question; you answer it. Without this anchor, every scoping decision becomes ad-hoc and the agent will fill in plausible-but-wrong defaults.

See [research-plan-template.md](templates/research-plan-template.md) for a starting template the agent uses when materializing `research_plan.md`.

## Researcher manifesto layer: `Human.md`

**Mutation rate:** rarely (project-lifetime; edits only when your relationship with the agent workflow changes).

**Answers:** What philosophy am I, the researcher, signed up for by working this way? What do I own; what does the agent own?

**Contains:**

- The full division-of-labour statement: you own the *what* and *why*; agents handle the *how* inside contracts you wrote.
- The five core principles, the document hierarchy, the inner loop (your discipline practice), maintenance rhythms, anti-patterns.
- A pointer to the operational protocol: the `agentic-exploration` skill in `.claude/skills/` — what the agent actually does, step by step.
- `[🙋 …]` placeholders for project-specific researcher notes — e.g. who else uses this repo, what conventions you've personally committed to. The 🙋 emoji marks every bracket the researcher must author by hand.

This is **your** file — the canonical statement of philosophy for this project — and the agent does not edit it without sign-off. It exists so that when you (or a collaborator) open the project root, the philosophy is one click away, not buried in `.claude/skills/`. It is also what the agent reads at high-stakes / long-session moments to ground its judgment.

**Trap:** letting `Human.md` and the skill drift apart. `Human.md` is canonical philosophy; the skill is canonical operational. If you notice a rule in the skill that doesn't match what's written here, the most likely cause is `Human.md` is stale — bring it into line. The opposite (skill stale, `Human.md` ahead) is rare but possible after a conceptual pivot; in that case, update the skill's rules to match the new philosophy.

**For agents:** read this once at session start if it exists; reread in full when the task is high-stakes (irreversible, data-touching, multi-step, judgment-heavy) or when starting a long session. Do not treat it as a source of operational rules — those live in the skill and `AGENT.md`. `Human.md`'s job is to keep the *researcher* oriented and to ground *your* judgment in deeper context when the rules alone aren't enough.

## Architecture layer: `AGENT.md` / `CLAUDE.md`

**Mutation rate:** occasionally (when conventions change, or after a recurring agent mistake).

**Answers:** How do we work in *this* repo? What conventions matter? What should the agent never assume?

**Contains:**

- Repo-specific conventions: directory layout, naming, where things go.
- Tooling: how to run tests, lint, train, evaluate. Exact commands.
- Style: error handling philosophy (fail loud), commenting, docstrings.
- Hard rules: things the agent must not do (e.g., never modify the raw data, never delete checkpoints, never push to main).
- Pointers into the docs hierarchy: "read `research_plan.md` before reasoning about the approach; read `plan.md` for the current phase; read `notes.md` for the latest discoveries".
- A short list of skills/subagents this project knows about, if any.

**Trap:** stuffing the project plan, the current TODO, and the latest debug notes in here. That's what the other files are for. Keep this layer about *how we work*, not *what we're working on right now*.

Keep it short — a few hundred lines max. If it grows beyond that, the agent's effective context shrinks for every other task.

This is your **rulebook for the agent**. You write the rules; the agent follows them. When a rule is missing because an agent did something you didn't want, *you* add the rule — once, here — rather than repeating the correction in every prompt. That's how the file earns its keep over time.

See [references/agent.md](references/agent.md) for the starting `AGENT.md` siesta copies into the project root at init.

## Roadmap layer: `plan.md` and `TODO.md`

**Mutation rate:** weekly-ish.

**Answers:** What's the next chunk of work? In what order? With what acceptance criteria?

`plan.md` is the medium-grained view — the next 5-20 things that need to happen, grouped by theme or phase. It's where you reason about ordering, dependencies, and risk.

`TODO.md` is the linearized view — the next N items each scoped to be completable in a single commit. Each TODO has:

- A one-line summary that will become the commit message.
- Concrete landmarks (files, functions, line numbers).
- Constraints written *before* implementation: the test that must pass, the type signature, the docstring, explicit DO-NOTs.
- Acceptance criteria — what proves it's done.
- (Optional) An estimate of difficulty / agent-vs-human.

An agent can *draft* a TODO from a vague goal, but you sign off on scope and acceptance criteria. The drafting is mechanical; the decision is yours.

You can keep these as separate files or use one file with two sections. Both are fine.

**Trap:** vague TODOs. "Improve the dataloader" is not a TODO; it's a wish. A good TODO names the file, the function, the new behavior, and the test that proves it. Re-read each TODO and ask: could a fresh agent with no other context do this correctly? If no, refine it.

See [plan-template.md](templates/plan-template.md) and [todo-template.md](templates/todo-template.md) for starting templates the agent uses when materializing `plan.md` / `TODO.md`.

## Discovery layer: `notes.md`

**Mutation rate:** continuously (every session adds to it).

**Answers:** What did we learn the hard way?

**Contains:**

- Library quirks ("HuggingFace tokenizer Y silently truncates inputs over N tokens").
- Cluster / environment gotchas ("the A100 nodes need CUDA_VISIBLE_DEVICES set or torch picks the wrong GPU").
- Data oddities ("class 14 in the labels is mislabeled — see [issue-tracker-link]"; "the timestamp column flips timezones at row 4017").
- Failed experiments or attempts and why they failed.
- Diagnostic results — when a test fails or an analysis surprises you, the diagnosis goes here, not just the fix.

**Trap:** treating this as a journal that grows unbounded. Periodically promote stable learnings into `AGENT.md` or `research_plan.md` and prune the scratch. A `notes.md` over a few hundred lines starts being skipped — by you and by every agent session.

Curation is **your** job. Agents can append (and should — every diagnosis they perform should be logged), but you decide what gets promoted into `AGENT.md` / `research_plan.md` and what gets pruned. Build the weekly compaction into your rhythm before it becomes overwhelming.

**For agents:** this is the highest-leverage file for cross-session continuity. A fresh agent that reads `notes.md` first avoids relearning every lesson the previous session paid for.

See [notes-template.md](templates/notes-template.md) for a starting template the agent uses when materializing `notes.md`.

## Handoff layer: `handoff.md`

**Mutation rate:** per-session.

**Answers:** What does future-you (or a teammate, or an agent you're about to pair with) need to know to pick up where this session left off?

**Contains:**

- What's done — the TODO(s) completed this session.
- What's in flight — a TODO that's started but incomplete, with the state preserved (what was tried, what failed, what's next).
- What's blocked — anything waiting on a human decision.
- Pointer to the right files to read first.
- Anything weird the next session should be warned about.

**Trap:** writing it as a private journal that only makes sense to you in the moment. Write it for someone with *zero* prior context, because that's what you'll effectively be in three days. Be explicit about file paths, current branch, last commit SHA. It costs you 60 seconds and saves the next session 10 minutes.

**When to write it:** at the end of any session you're not sure will continue with the same context (which is most of them), when context is about to be reset, or when a different person / session is about to take over.

This file is short-lived and often overwritten — that's fine. It's a baton, passed between *your sessions* (and the agents you pair with in each), not an archive.

See [handoff-template.md](templates/handoff-template.md) for a starting template the agent uses when drafting `handoff.md`.

## How the layers compose

These docs are shared between you (the researcher) and any agent joining a session. Reading order:

1. **You:** `Human.md` → orient: philosophy you're working under. **Agent:** `AGENT.md` → orient: hard rules and conventions.
2. `handoff.md` → what's the most recent context?
3. `plan.md` / `TODO.md` → what's the next chunk?
4. `notes.md` → what's known about the area I'm about to touch?
5. `research_plan.md` → if a judgment call comes up, what's the project trying to do?
6. The code itself.

The split at step 1 is intentional: `Human.md` is your orientation, not the agent's protocol. The agent's protocol is the `agentic-exploration` skill, loaded on invocation.

That's the order. A session structured this way feels like working with a senior collaborator who happens to have no memory between days.

## How the layers fail — and the counter-ritual for each

Common failure modes, and the cheapest practice that prevents each:

- **Everything in `CLAUDE.md`.** Bloat, gets ignored. Counter-ritual: split when the file crosses a few hundred lines, regardless of how well-organized it feels. The discipline is the size limit, not whether you think you can manage more.
- **`research_plan.md` never updated after the approach changed.** Lying anchor. Counter-ritual: re-read at every phase boundary; edit before the next TODO starts.
- **`TODO.md` items are wishes, not tasks.** Vague TODOs lead to filler generations. Counter-ritual: the per-iteration discipline check at the end of the inner loop catches this — if a TODO closed without acceptance criteria, the next one starts vague unless you flag it.
- **`notes.md` is stream-of-consciousness no one re-reads.** Counter-ritual: weekly compaction. Promote, prune, restructure — don't grow.
- **No `handoff.md`, every session pays a context-restoration tax.** Counter-ritual: write one at the end of every session you're not sure will continue (most of them). Cheap to write, expensive to skip.

## Lifecycle and maintenance of the hierarchy

The hierarchy is not "set up once and forget". It is a living system that decays without active care. Each doc has its own maintenance rhythm:

| Doc | Per-iteration | Per-phase | Per-week |
|---|---|---|---|
| `research_plan.md` | nothing (or a one-line tweak if a pivot happened mid-TODO) | full re-read; edit any drift; update milestone roadmap | nothing extra |
| `Human.md` | nothing | nothing | nothing (re-skim only if you suspect philosophy drift; edit only if your workflow philosophy actually changed) |
| `AGENT.md` | nothing | nothing | audit against actual agent mistakes this week; add missing rule(s) |
| `plan.md` / `TODO.md` | mark done; scope next | re-scope; archive completed phase | check for orphan TODOs |
| `notes.md` | append diagnoses | promote stable learnings into anchor docs | compact — promote, prune, restructure |
| `handoff.md` | overwrite at session end if relevant | (often replaced by phase transition) | verify last three handoffs were actually useful; adjust template if not |

These rhythms are not bureaucracy. They are the cheapest thing you can do that keeps the project from regressing to ad-hoc.

If a rhythm slips for a single week, no problem — life happens. If it slips for a month, the project is no longer agent-augmented exploration; it's a repo with some leftover docs in it. The fix at that point is one focused half-day of audit, not a rewrite. Catch it early.
