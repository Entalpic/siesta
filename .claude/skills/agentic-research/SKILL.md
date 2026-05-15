---
name: agentic-research
description: Structure an exploratory or research project so coding agents can work on it productively — choosing what goes in AGENT.md vs research_plan.md vs design_doc.md vs plan.md vs notes.md, linearizing roadmaps into TODOs an agent can complete in one shot, writing handoff docs between agent sessions, keeping git history as a savegame, and separating implementation from verification. Use this skill whenever the user is starting a research, exploration, or investigation codebase (ML experiments, scientific simulation, data analysis, prototyping, ad-hoc investigations), retrofitting one for agentic work, drafting an AGENT.md / CLAUDE.md / research_plan.md / design_doc.md / plan.md / TODO.md / handoff.md, organizing multi-agent research workflows, deciding how to scope a task for an agent, complaining that an agent "did too much" or "got lost", or asking how a researcher or explorer should collaborate with Claude — even if there is no paper involved and even if they don't use the word "agentic".
---

# Agentic research workflows

Exploratory code — research experiments, scientific simulation, data analysis, prototypes, ad-hoc investigations — has different priorities from production engineering. It optimizes for portability, intelligibility, and tight alignment between code, tests, comments, and whatever the project is trying to learn or show. Abstraction and defensive hardening, which pay off in long-lived production systems, mostly get in the way here. The deliverable might be a paper, a report, a notebook, a decision, a launch recommendation, or just an answer to a question — the structure below works the same regardless. The point of organizing things well is that with a coherent project, an agent can move 2-10x faster on idea iteration. With an incoherent one, every session pays a tax to rebuild context.

This skill is the playbook for setting up and running exploratory projects so agents stay productive across sessions, hand off cleanly to each other, and don't quietly contaminate the codebase. Use it as a menu — not every project needs every piece, but the principles compose.

## When to apply this

Apply this skill when the user is doing any of:

- Starting a new exploratory codebase (ML experiments, scientific simulation, data analysis, theorem proving, prototyping, investigation of a question) where agents will write most of the code.
- Retrofitting an existing research / exploration repo to be agent-friendly.
- Drafting or revising an `AGENT.md` / `CLAUDE.md` / `research_plan.md` / `design_doc.md` / `plan.md` / `TODO.md` / `notes.md` / `handoff.md`.
- Scoping work for an agent — deciding how big a task should be, what constraints to write down first, what to leave the agent to figure out.
- Diagnosing why an agent "did too much", "got lost", "reimplemented something that already existed", "filled context with junk", or "broke an unrelated thing".
- Coordinating multiple agents (worktrees, parallel streams) or handing a project between researchers.

Do **not** apply this for production engineering tasks (microservices, SaaS, frontend apps). The tradeoffs are different there — production code rewards abstraction and defensive programming; exploratory code punishes them.

## Core mental model

Three ideas drive everything below.

**1. Agent context is your context, and your colleague's context.** Whatever you offload from your head into structured docs is recoverable by any future you, any future agent, and any teammate. The docs are not bureaucracy — they're the persistent layer of a stateless system.

**2. Generations become context.** The code an agent writes today is the context an agent reads tomorrow. Sloppy generation compounds. A hundred bad lines from one unclear prompt contaminate every later session in that area of the codebase. Keep the bar high.

**3. Stabilize at the top, mutate at the bottom.** Project documents have different mutation rates. Anchor the high-stability things (problem statement, methods, architecture) so the agent can re-derive the low-stability things (today's TODO, current diff) without losing the plot.

## The document hierarchy

Layer projects across documents organized by how often they change. Each layer answers a different question.

| Layer | File(s) | Mutation rate | Answers |
|---|---|---|---|
| Anchor | `research_plan.md` (or `design_doc.md`), external refs | rarely | *What question are we answering, and how?* |
| Architecture | `AGENT.md` / `CLAUDE.md`, `README.md` | occasionally | *How do we work in this repo?* |
| Roadmap | `plan.md`, `TODO.md` | weekly-ish | *What's the next chunk of work?* |
| Discoveries | `notes.md` | continuously | *What did we learn the hard way?* |
| Handoff | `handoff.md` (per session/agent) | per-session | *What does the next agent need to know right now?* |
| Code + tests | the actual repo | continuously | the implementation |

The trap to avoid: dumping everything into one giant `CLAUDE.md`. It bloats, drifts, and gets ignored. Keep each layer focused and link between them.

For details on what goes in each file and how to write them, see [references/doc-hierarchy.md](references/doc-hierarchy.md).
For a starting `AGENT.md`, see [references/agent.md](references/agent.md).

## Linearizing the roadmap

The biggest single lever on agent productivity is task scoping. Most "the agent did a bad job" outcomes trace back to a task that was too big, too vague, or under-constrained.

A well-scoped TODO has:

- **Landmarks.** Concrete file paths, function names, line numbers the agent can navigate to. Not "improve the dataloader" — "extend `load_batch` in [src/data/loader.py:42](../../src/data/loader.py#L42) to support the new shard layout described in plan.md §3".
- **Constraints written first.** Tests, type signatures, docstrings, and explicit DO-NOTs *before* the implementation prompt. Pre-specifying the contract reduces the space of generations and prevents the agent from reimplementing things you already have.
- **Single responsibility.** One TODO = one commit. If you can't summarize what the commit will do in one line, the TODO is too big — split it.
- **Verifiable acceptance.** How will you know it's done? A passing test, a specific output, a generated figure. If it's "looks good to me", you'll iterate forever.

Why this matters: an under-constrained task lets the agent fill context with guesses. Those guesses become code. That code becomes the context for the *next* task. The cost compounds.

## The inner loop

For each TODO, follow this loop:

1. **Explore.** Have the agent read just the files that matter and record findings in `notes.md`. Don't let it grep the whole repo.
2. **Plan.** Get a high-level approach written down before any code. One paragraph is fine.
3. **Constrain.** Write the test, the type signature, the docstring, and the explicit DO-NOTs. This is where exploratory projects gain most of their leverage — the codebase is small enough that test-first is actually tractable.
4. **Generate.** Ask for the implementation.
5. **Verify.** Run the test. If it fails, diagnose into `notes.md` — don't just retry. The diagnosis becomes part of the persistent record.
6. **Commit.** One TODO, one commit, descriptive message. Git is your savegame system.
7. **Handoff (if stopping).** If you're ending a session mid-roadmap, write `handoff.md` with: what's done, what's in-flight, what's blocked, what the next agent should read first.

## Independence between implementation and verification

Tests written by the same agent that wrote the code are partially test-cheating — the agent has already absorbed all the assumptions, blind spots, and shortcuts. Fix this by separating roles:

- **Write tests in a separate session/agent** from implementation. Different context, different blind spots.
- **External review** — you, or an agent uninvolved in the implementation — checks correctness against the research plan, the design doc, and external references.
- **Constraints from outside.** Specs, examples to copy from, and failure-mode lists come from you or from a literature / prior-work subagent, not from the implementing agent.

This is more important in exploratory work than in engineering because there's no production traffic to surface mistakes for you. The bugs you ship are the bugs in your conclusions — whether those conclusions land in a paper, a report, a notebook, or a Slack thread.

## Git discipline as a savegame system

Agents can use git more professionally than most researchers and explorers — *let them*. The rules:

- One TODO, one commit. No drive-by edits.
- Descriptive messages. Future-you and future-agents read these to localize regressions.
- Use worktrees for parallel streams (different agents on different experiments, syncing via `notes.md` and `plan.md`).
- Don't hand-edit history just to clean things up — the messy commits are evidence.
- When something breaks, bisect or `git log -S` *before* asking the agent to "fix it". You'll find the cause faster than re-prompting.

## Warm-start, never cold-start

Never ask an agent to build a project from scratch in an empty directory. The space of plausible generations is too large; you'll get an arbitrary one. Instead:

- Start from a reference codebase: your own old project, a public repo doing something similar, an open-source reference implementation, or a related team's prototype.
- Or: write architectural stubs by hand — `module.py` files with class skeletons, function signatures, and TODO-comments — before asking for implementation.
- For docs: start from the templates in this skill (see references/), don't ask the agent to invent the structure.

## Fail-loud over silent fallbacks

Exploratory code's job is to be correct, not robust. A silent fallback (`try/except: pass`, default values for missing config, fallback model paths, silently-skipped rows) hides exactly the bugs that make your conclusions wrong. Tell the agent — in `AGENT.md` and per-task — to:

- Raise on unexpected state rather than logging-and-continuing.
- Avoid try/except unless you specifically need the recovery and know what's recoverable.
- Assert preconditions explicitly.
- Prefer crashing in unit tests over `pytest.warns`.

The cost of a loud failure is annoyance. The cost of a silent one is a wrong answer you'll act on.

## Context economy

Long context degrades performance — keep effective context lean even when the model technically supports more.

- Aim to stay well under the model's stated context limit; performance drops well before the hard limit.
- Compact `notes.md` periodically — promote stable learnings into `AGENT.md` or `research_plan.md` and delete the scratch.
- Use cheaper/faster models for execution once the plan is locked; reserve thinking models for planning and review.
- Reset sessions between unrelated TODOs. The handoff doc is the bridge.

## Parallelism

Multiple agents can run in parallel via git worktrees, each on a separate branch or experiment. They synchronize through:

- The shared `plan.md` (what each stream is responsible for).
- The shared `notes.md` (discoveries any of them might need).
- The codebase itself (one source of truth).

Don't try to coordinate them in real time — let them run, then merge. The point of parallelism is independence; if they need to talk to each other, you've split the work wrong.

Beyond worktree-level parallelism, single tasks can fan out into subagents — e.g., a correctness review that runs one subagent per module, a literature search that runs one subagent per related paper or prior project, a plan-vs-code audit that compares each section independently. Use this when the work is genuinely parallelizable; don't fake it for things that are sequential.

## Anti-patterns to call out

If you see the user doing any of these, push back:

- **One mega-`CLAUDE.md`** containing personality, repo structure, every convention, and the project plan. It bloats and gets ignored. Split into the hierarchy above.
- **"Just figure it out" tasks** with no landmarks or acceptance criteria. The agent will fill context with guesses.
- **Trusting agent output blindly**, especially around git operations, deletes, or anything that touches data files. "Agents have no regrets about irreversible mistakes" — humans need to gate destructive things.
- **Empty-repo cold starts.** Warm start from a reference or stubs.
- **Same agent writes code and tests.** Separate them.
- **Try/except as a programming style.** It's hiding bugs.
- **Refactor sprees not tied to a TODO.** Surgical changes only — exploratory code rewards minimal diffs.

## What this skill produces

When you apply this skill, the outputs are usually one or more of:

- A drafted `AGENT.md` / `CLAUDE.md` tailored to the user's project (see template).
- A `research_plan.md` (or `design_doc.md`) outline for a new project.
- A linearized `TODO.md` derived from a vague goal the user described.
- A `handoff.md` for ending a session.
- Specific advice on a scoping / structure question, grounded in the principles above.

Match the form to the request. Don't generate all of these artifacts when the user asked one question.

## How to behave when this skill is active

- Ask the user where in the lifecycle they are (new project? mid-project? stuck on something specific?) before generating boilerplate.
- Prefer editing the user's existing docs over creating new ones.
- When proposing a TODO list, show landmarks and acceptance criteria for each item — that's the differentiator from a normal todo list.
- Be willing to tell the user their task is too big and needs splitting. That's the highest-value feedback this skill provides.
- Don't lecture. Reference the principles when they're load-bearing for a specific choice; otherwise just do the work.
