# Context

The shared language of the `siesta` CLI: how its write-oriented commands are structured, how it installs agent assets across providers, and the agent workflow that governs changes to the repo.

## Language

### Command execution model

**Mutation**:
An operation that changes project state, including filesystem writes and external side effects.
_Avoid_: write, change, side effect (as the canonical noun)

**Validation Phase**:
Fail-fast, non-mutating checks that run before prompt collection to reject invalid command contexts.

**Prompt Collection Phase**:
The command phase where all user decisions are gathered before any Mutation is allowed.

**Execution Phase**:
The phase that starts after prompt collection and performs only the Mutations selected by the user.

**Ordering Contract**:
The guarantee that decision collection completes before the first mutating operation starts.

**Non-Interactive Resolution**:
Mode where no prompts are shown and decisions are resolved from explicit flags first, then CLI defaults.

**Input Precedence**:
The rule that explicit CLI flags are authoritative and prompts only resolve unspecified decisions.

**Decision Ownership**:
The principle that the top-level invoked command owns prompt collection and passes explicit decisions to downstream helper or nested command calls.

**No-Op Selection**:
A valid outcome where the user selects no actions and the command exits successfully without Mutation.

**Cancellation**:
User interruption during prompt collection that exits with code 130 at the CLI entrypoint, before any Mutation.
_Avoid_: abort, quit

**Conflict**:
An existing artifact on disk that a Mutation would overwrite or corrupt if run unconditionally.

**Conflict Resolution**:
The sub-process within the Prompt Collection Phase where each detected Conflict is surfaced to the user, who declares skip, overwrite, or abort. All Conflict Resolutions are collected before the first Mutation — guaranteeing that Abort leaves the project state identical to its pre-run state.
_Avoid_: guard, check, validation (those are Validation Phase terms)

**Abort**:
A deliberate user choice during Conflict Resolution that exits before any Mutation, leaving project state identical to its pre-run state. Distinguished from Cancellation (which is an unintentional interrupt, exit code 130) and from error exits triggered by the CLI itself.
_Avoid_: cancel, quit

### CLI structure

**CLI Domain Module**:
A module that owns one command group and its command implementations (for example documentation, project, self-management, or agents commands).

**CLI Executable Contract**:
The stable public surface for running `siesta` as a command, where behavior and command names must remain compatible but Python import paths are not part of the contract.

### Agent assets

**Agent Asset**:
An installable unit of agent guidance shipped by siesta — a Skill, a Rule, or a Constitution.
_Avoid_: template, plugin, config

**Agent Asset Catalog**:
The collection of Agent Assets bundled inside the siesta package, used as the only install source.
_Avoid_: registry, store, remote assets

**Detected Agent Asset**:
An Agent Asset already present on disk under a Provider directory for a given Asset Scope — the set `siesta agents remove` operates on.
_Avoid_: available (that term is reserved for the Catalog on `add` commands)

**Provider**:
A target agent tool whose on-disk conventions siesta installs into — Cursor or Claude.
_Avoid_: vendor, tool, platform, client

**Skill**:
An Agent Asset packaged as a directory (a `SKILL.md` plus supporting files) that an agent loads on demand.
_Avoid_: command, macro, workflow

**Rule**:
An Agent Asset that is a single instruction file applied by file globs/paths, authored canonically as a Cursor `.mdc`.
_Avoid_: Always-on rule, lint rule, guideline

**Constitution**:
A Provider's top-level, always-loaded project instructions, with `AGENTS.md` as the source of truth and `CLAUDE.md` an `@AGENTS.md` import stub.
_Avoid_: AGENTS.md (that file is one rendering of it), charter, manifest

**Provider Mirroring**:
The guarantee that an Agent Asset stays equivalent across Providers, differing only in vendor-required format.
_Avoid_: syncing, duplication

**Asset Scope**:
Whether an Agent Asset is installed for the current repository (local) or the user's home directory (global).
_Avoid_: location, target

**Quickstart Config**:
The bundled declaration (`agents_assets/quickstart.yaml`) listing which Agent Assets `siesta agents quickstart` installs by default — the curated default subset of the Agent Asset Catalog. It is NOT an Agent Asset itself, so the "avoid: config" guidance on **Agent Asset** still applies to Skills/Rules/Constitutions.

### Security

**Secret Handling Policy**:
The rules governing how credential material may enter and leave the CLI: secrets are not accepted via command-line arguments, and plaintext secret output requires explicit interactive confirmation.

### Agent workflow

**Wrap-Up Phase**:
The post-commit, pre-close phase where branch work is finalized through PR validation and merge while the issue remains in an active building state.

**Builder Grill Gate**:
The required pre-build checkpoint where the builder runs `/grill-with-docs`, records grill outcomes and open questions, then requests explicit build authorization; the issue stays `agent:blocked` until then.

**Build Authorization Language**:
The canonical approval vocabulary, where `build` is the canonical verb and `implement` an accepted synonym, recognized only in explicitly affirmative messages.

**Approval Ambiguity Fallback**:
The rule that if approval text is not clearly affirmative, the builder asks one direct confirmation question and keeps the issue `agent:blocked` until explicit authorization.

**Post-Merge Finalization**:
The mandatory issue-close sequence that runs only after merge succeeds: publish final issue status, transition to `agent:done`, and close the issue.

**Issue Reference Convention**:
The rule that branch commits and PR context use `Refs #<num>` for linkage, while issue closure remains an explicit workflow step rather than an auto-close keyword.

## Relationships

- An **Agent Asset Catalog** contains **Skills**, **Rules**, and **Constitutions**; it is the only install source (bundled, no network).
- The **Quickstart Config** selects a subset of the **Agent Asset Catalog**; running `siesta agents quickstart` is equivalent to running the individual `agents add` commands for each listed asset.
- A **Constitution** is rendered as `AGENTS.md` (source of truth) plus, for the Claude **Provider**, a `CLAUDE.md` `@AGENTS.md` stub.
- A **Rule** has exactly one canonical `.mdc` source and is **Provider Mirrored** to a translated Claude `.md`.
- Every Agent Asset install resolves to a **Provider** × **Asset Scope** destination.
- Installing an Agent Asset is a **Mutation**, and therefore obeys the **Ordering Contract** (decisions in the Prompt Collection Phase, writes in the Execution Phase).

## Example dialogue

> **Dev:** "When I run `agents add constitution --claude`, does it only write `CLAUDE.md`?"
> **Maintainer:** "No — a **Constitution**'s source of truth is `AGENTS.md`, so we always write it; `CLAUDE.md` is just the `@AGENTS.md` stub. `AGENTS.md` is there for Cursor compatibility, not because Claude needs it."
> **Dev:** "And the **Rules**?"
> **Maintainer:** "Each is authored once as `.mdc`. The Claude copy is **Provider Mirrored** — same intent, vendor-translated frontmatter."

## Flagged ambiguities

- "rule" was used for both an installable **Rule** asset and the AGENTS.md "Always-on rules" of the agent workflow — resolved: **Rule** (capitalized) is the Agent Asset; the workflow constraints remain "Always-on rules" and are not Agent Assets.
- "constitution" was a new word for what AGENTS.md content was informally called — resolved: **Constitution** is the concept; `AGENTS.md` and `CLAUDE.md` are its Provider renderings.
- "provider" vs "tool"/"vendor" — resolved: **Provider** is canonical, and currently means Cursor or Claude.
