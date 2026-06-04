# 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.
- Read `system-architecture.md` first to understand repository structure and boundaries before broad grepping/searching across the entire codebase.
- Treat `system-architecture.md` as the source of truth for repository architecture. When a task changes components, boundaries, data flow, key abstractions, integrations, or deployment topology, update it in the same task; otherwise explicitly confirm that no update is needed.
- Before developing this codebase, and whenever a request is too vague, short, or unclear, use the `grill-with-docs` skill to stress-test the plan against the project's domain language and documented decisions (`CONTEXT.md`, ADRs). Ask one question at a time, wait for feedback, check the codebase or docs before asking when possible, and proceed only once intent is clear.
- Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.
- For implementation plans (and especially in plan mode), write directives clearly enough that a small model can execute them: state the goal, assumptions, exact files or symbols to touch, ordered steps, verification commands, and explicit non-goals or constraints.


# 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

# 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

# 4. Constitution, Rules, and Skills

**One artifact owns each piece of guidance. Never duplicate across them.**

Three artifacts carry agent guidance, each owning a distinct slice:

- **Constitution** (this file, `AGENTS.md`): always loaded, applies to every task regardless of which files you touch. Owns global principles only. Keep it thin — when guidance is a procedure, move it into a Skill and point at it from here instead of inlining the steps.
- **Rule** (`.cursor/rules/*.mdc`, `.claude/rules/*.md`): loaded conditionally by file glob or path. Owns constraints tied to a specific file type, directory, or technology — keep these out of the Constitution.
- **Skill** (`SKILL.md` directory): invoked on demand when a task matches. Owns multi-step procedures and workflows. The Constitution and Rules reference Skills; they never inline a Skill's steps.

Placement test:
- Applies to every task → Constitution.
- Applies only when touching certain files → Rule.
- A procedure you run for a kind of task → Skill.

The Constitution loads on every task, so keep it thin and grow it only with genuinely universal principles. If it grows, that's a sign guidance was misclassified — demote it to a Rule or Skill. Moving always-on content into a separate imported file does not help: an `@`-imported file fills context identically. The fix is changing *when* guidance loads, not *where* it lives.

# 5. Be safe, be consistent

**Security is a hard gate. A task is not done until this section is satisfied.**

Always perform a security pass while reading and writing code:
- Treat secrets exposure as critical (API keys, tokens, passwords, credentials, private keys, webhook URLs, `.env` contents).
- Never hardcode secrets in code, tests, docs, examples, commits, PR text, logs, or terminal snippets.
- Do not move secrets into "safe-looking" files (fixtures, sample configs, scripts). If a value is sensitive, keep it out.
- If you detect a leak or high-risk pattern, stop and warn clearly. Do this even when it is outside the original request.

Before declaring completion, run a critical consistency review of your own work:
- Verify the result is consistent with sections 1-4: explicit assumptions, minimal scope, and surgical edits only.
- Confirm every changed line traces directly to the user's request (no speculative features, no side-quest refactors).
- Check that your naming, structure, and behavior align with existing project language and conventions.
- Check consistency with documentation produced by the `/grill-with-docs` process (`CONTEXT.md`, `CONTEXT-MAP.md`, and relevant ADRs). If code and docs disagree, flag it explicitly.
- Challenge your own decisions: "Where did I overreach?" and "What part is inconsistent with the stated principles?"
- If inconsistencies remain, report them explicitly and propose the smallest concrete fix.

Completion rule:
- Do not present the task as complete until all checks are done: (1) secret/leak/security scan, (2) critical consistency self-review, (3) consistency check against `/grill-with-docs` artifacts (`CONTEXT.md`, `CONTEXT-MAP.md`, relevant ADRs).
