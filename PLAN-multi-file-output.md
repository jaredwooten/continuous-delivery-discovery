# PLAN: Multi-file CD Discovery Output

Status: Design — pending implementation
Authored: 2026-05-26

## Problem

Today the `cd-discovery` skill and `continuous-delivery-strategist` agent produce a single `CD-DISCOVERY.md` at the project root. Three issues with this:

1. **Length.** The single file is hard to review in one pass — readers skim past the sections they need.
2. **Lifecycle mismatch.** With `--suggest`, the phased roadmap mixes with the point-in-time discovery snapshot. Discovery is a state report; the roadmap is a working artifact. They change at different rates.
3. **Roadmap framing.** "Roadmap" implies an endorsed plan. The artifact should be a resource that engineers consult and adapt to their own context, not a directive from the agent.

## Goals

- Split the single CD-DISCOVERY.md into a `cd-discovery/` directory of focused files.
- Reframe the `--suggest` output from prescriptive roadmap to optional suggestions, leading with tradeoffs.
- Let `--suggest` run incrementally against existing findings without re-scanning.
- Preserve update/revision audit trails per file.
- Migrate existing legacy `CD-DISCOVERY.md` files into the new layout when the user opts in.

## Non-Goals

- Restructuring `continuous-delivery-strategist.md` or `cd-discovery/SKILL.md` themselves into multiple files. Source files stay as-is in structure; only their content changes.
- Producing dedicated GitHub or Octopus report files. GH/Octopus evidence weaves into the relevant dimensions in `findings.md`.
- Adding time-duration estimates to suggestions (existing rule preserved).
- One-file-per-dimension granularity. Per-dimension content lives in a single `findings.md`.

## Output Layout

All output lives under a `cd-discovery/` directory at the project root:

```
project-root/
  cd-discovery/
    summary.md         (always)
    findings.md        (always)
    suggestions.md     (only when --suggest has been run)
```

### summary.md — the headline

The leadership-readable overview. Contains:

- Date + repository header
- Executive summary (2–3 sentence overview: pipeline maturity, strongest dimension, weakest dimension, highest-leverage improvement)
- Capability matrix (L0–L4 per dimension with confidence)
- Strengths to Protect (load-bearing patterns the team is getting right, with file:line evidence)
- Anti-Patterns Detected
- Recommended Next Steps (3 quick wins teaser)
- Links to `findings.md` and `suggestions.md` (if present)
- Revision log at bottom

Strengths to Protect lives here, not in `findings.md`, because it is a headline view.

### findings.md — the deep dive

Per-dimension detail. Contains:

- Date + repository header (lightweight, may reference summary.md)
- One section per capability dimension (Build & CI, Testing, Deployment, IaC, Observability, Release Process, Security)
- Each section: estimated level, confidence with reason, artifacts found, gaps identified, user context
- **GitHub and Octopus evidence is woven into the relevant dimension sections** — no dedicated "GitHub Repository Posture" or "Deployment Orchestrator" sections
- Discovery source notes inline (e.g., "evidence from gh CLI Tier 1, scanned 2026-05-26") rather than as their own structural section
- Revision log at bottom

### suggestions.md — the resource (when `--suggest` has run)

Optional, generated only when `--suggest` is invoked. Contains:

- Date + repository header
- Framing preamble: this is a resource, not a plan. Engineers form their own opinion and own sequencing decisions based on team capacity, parallel work, and risk appetite.
- Suggestions list. Each suggestion structured as:
  - **Gap** — what was found
  - **What improving unlocks** — concrete capability or risk reduction
  - **Cost / disruption** — what the work requires and what it makes harder
- Sequence guidance expressed as a dependency map ("X unlocks Y"), not as a sequential plan. Each dependency edge is justified.
- No time-duration estimates (existing rule preserved).
- "Roadmap" language is not used.
- Revision log at bottom

## Voice and Tone — suggestions.md

The voice change is structural, not cosmetic. Specific rules:

1. **Lead with tradeoffs, not directives.** Phrasing leans "Consider X because Y; the tradeoff is Z" over "Do X."
2. **Decouple sequence from prescription.** A dependency edge ("X unlocks Y") is a constraint on order, not a schedule. State explicitly that engineers may sequence differently. Sequence is a resource, not a plan.
3. **Drop "roadmap" language entirely.** The file is `suggestions.md`, the section headers do not say "roadmap" or "plan," and items are "suggestions" not "phases."

The existing strategist principle that "every phase must leave the system in a better, stable state" is preserved but reframed as guidance for whoever sequences the work, not as a mandate from the agent.

## Skill Workflows

The launcher in `SKILL.md` routes between five workflows.

### W1: Fresh `/cd-discovery` (no existing dir, no legacy file)

Agent scans, writes `cd-discovery/summary.md` and `cd-discovery/findings.md`. No `suggestions.md`.

### W2: Fresh `/cd-discovery --suggest` (no existing dir, no legacy file)

Agent scans, writes all three files in one run.

### W3: `/cd-discovery --suggest` when summary.md + findings.md already exist (no suggestions.md yet)

**No re-scan.** Agent reads existing findings and writes `suggestions.md` only. This is the incremental path: users can decide later whether they want suggestions.

If `suggestions.md` already exists, dispatch goes to W4 with the prompt scoped to `suggestions.md` only — overwrite regenerates just `suggestions.md` (no rescan), update runs the update flow targeted at suggestions, cancel exits.

### W4: `/cd-discovery` or `/cd-discovery --suggest` when `cd-discovery/` already exists

Launcher shows the existing-report prompt with three options:

- **Overwrite** — discard the directory, fresh discovery (W1 or W2 path).
- **Update** — run the update flow (see Update Flow below).
- **Cancel** — exit without changes.

### W5: Legacy `CD-DISCOVERY.md` detected, no `cd-discovery/` dir

Launcher shows three options:

- **Migrate** — agent reads legacy file, splits it into the new 3-file layout, preserves content and revision history, removes the legacy file, optionally continues into `--suggest` if that flag was set. See Migration below.
- **Fresh** — discard legacy (user retains it manually if they want), write new layout (W1 or W2 path).
- **Cancel** — exit without changes.

### Dispatch precedence

If both a legacy `CD-DISCOVERY.md` and a `cd-discovery/` directory exist, the directory wins — dispatch goes to W4. The launcher prints a one-line warning noting the stale legacy file and recommends removing it. It does not auto-delete.

## Update Flow

`/cd-discovery --update [context]` operates on the `cd-discovery/` directory as a whole. The launcher routes to the update agent path; the agent decides which files to edit based on what each claim affects.

Adapted from the existing UPDATE-PLAYBOOK phases:

1. **Ingest** — read all files in `cd-discovery/` into a working memory index.
2. **Capture context** — inline string (`--update "..."`), file path (`--update path/to/notes.md`), or interactive prompt. Same options as today.
3. **Decompose into atomic claims** — show the list to the user for confirmation before proceeding. Each claim is tagged with the file(s) it touches: `[summary]`, `[findings]`, `[suggestions]`, or multiple.
4. **Targeted verification** — re-run only the scan slices the claims touch. Surface any `CONTRADICTED` claim to the user before editing.
5. **Edit in place** — granular `Edit` tool calls only, no whole-file rewrites. Touch only the files the claims affect.
6. **Per-file revision logs** — for each file the agent touched, append one entry to that file's bottom revision log. Files the agent did not touch get no entry that day.

### Multi-File Claim Propagation Rule

If a claim changes a dimension's level (for example, Testing L1 → L2), the agent **must** propagate the change to both:

- `findings.md` — the per-dimension section
- `summary.md` — the matrix row

…in the same pass. The decomposition step flags these as multi-file claims so they do not get half-applied. The claims-confirmation list shown to the user in step 3 makes the propagation visible.

### Revision Log Format (per file)

```
## Revision history

### 2026-05-26 — context refresh
- Testing: L1 → L2 (verified via .github/workflows/ci.yml)
- Suggestion #2: superseded ([USER-REPORTED])
```

The Quality Gate from the existing UPDATE-PLAYBOOK applies per file the agent touched.

## Migration

When the launcher detects a legacy `CD-DISCOVERY.md` and the user chooses **Migrate**, the agent (not a strict parser) performs the conversion. Agent-driven migration handles edge cases like custom sections, partial reports, or merged content.

Procedure:

1. **Read legacy file end-to-end.**
2. **Validate parseability.** Legacy file must have at least an Executive Summary, Capability Matrix, and one Detailed Findings dimension. If not, abort migration and offer Fresh instead.
3. **Split by section:**
   - Executive Summary, Capability Matrix, Strengths to Protect, Anti-Patterns Detected, Recommended Next Steps → `cd-discovery/summary.md`
   - Detailed Findings (per dimension) → `cd-discovery/findings.md`
   - "Deployment Orchestrator" section content → woven into the Deployment dimension of `findings.md`
   - "GitHub Repository Posture" section content → woven into Build & CI / Security / Release Process dimensions per the legacy file's cross-stitch lines
   - Any pre-existing roadmap content (from prior `--suggest` runs) → `cd-discovery/suggestions.md`, reframed from directive voice to suggestion voice (lead with tradeoffs, decouple sequence from prescription)
4. **Preserve revision history.** If the legacy file has a "Changes from previous report" or revision section, copy entries into each new file's revision log by topic. Entries that cannot be cleanly assigned go to `summary.md`'s log with a note.
5. **Prepend a migration entry** to each new file's revision log:
   ```
   ### 2026-05-26 — migrated from CD-DISCOVERY.md
   - Content split into new layout; see git history for the source file.
   ```
6. **Remove the legacy file** via `git rm CD-DISCOVERY.md` so the conversion is a single reviewable commit (deletion + new directory).
7. **If `--suggest` was passed AND the legacy file had no roadmap content:** continue into a fresh `suggestions.md` generation against the migrated findings.

### Sub-Playbook Section Weaving Rule

GH and Octopus content from the legacy file weaves into the dimension where its cross-stitch row says it landed. If a cross-stitch row is ambiguous, the agent puts the evidence under the most-cited dimension and notes the others as "see also."

## Source File Changes

The agent and skill files stay single-file. Their content changes as follows.

### `agents/continuous-delivery-strategist.md`

- §6 Discovery Mode, bullet 8 — change "produce `CD-DISCOVERY.md` in the project root" to "produce `cd-discovery/summary.md` and `cd-discovery/findings.md`; if `--suggest` is in scope, also write `cd-discovery/suggestions.md`."
- §6 Discovery Mode, bullet 9 — update the `--suggest` description to use the suggestion voice: tradeoffs not directives, sequence decoupled from prescription, no "roadmap" language.
- §4 Sequence Improvements — soften "When building roadmaps" to "When suggesting improvements." Preserve the no-time-estimates rule. Preserve the "phases must leave the system in a better, stable state" rule but reframe as guidance for whoever sequences the work.
- Quality Checks §6 — update "the report" references to "the discovery files."
- Agent memory protocol — when recording where the report was written, record the `cd-discovery/` directory path, not `CD-DISCOVERY.md`.

### `skills/cd-discovery/SKILL.md`

- **Existing-report detection** — check for `cd-discovery/` directory first, then legacy `CD-DISCOVERY.md`. The dispatch routes to W3 (incremental suggest), W4 (existing dir prompt), or W5 (legacy migration) based on what is found.
- **`--suggest` incremental branch** — if `cd-discovery/summary.md` and `findings.md` exist but no `suggestions.md`, skip to "generate suggestions only" without re-scanning.
- **Spawn-the-Agent prompt** — update `<output>` block to reference the three target files. Remove the "Deployment Orchestrator section" and "GitHub Repository Posture section" wording. Replace with: "weave GH/Octopus findings into the relevant dimensions in findings.md per the weave-map output from the sub-playbooks."
- **Spawn-the-Update-Agent prompt** — update to reference per-file revision logs and the multi-file-claim propagation rule.
- **New spawn path: "Spawn the Migrate Agent"** — implements the migration procedure above. Same `subagent_type: continuous-delivery-strategist`; different `<objective>` block.

### `skills/cd-discovery/PLAYBOOK.md`

- Output instruction changes from "produce `CD-DISCOVERY.md`" to the three-file layout under `cd-discovery/`.
- Add a sub-playbook integration note: when GH or Octopus discovery runs, evidence is woven into the relevant `findings.md` dimensions; no separate sections.
- The L0–L4 framing rule for branch protection (current §6 of the agent's discovery mode) applies at the dimension level in `findings.md`. The cross-stitch reasoning lives inline with the dimension evidence.

### `skills/cd-discovery/TEMPLATE.md`

Replaced by three template files in the same directory:

- `TEMPLATE-summary.md` — header, exec summary, capability matrix, strengths to protect, anti-patterns, next steps, links to other files, revision log placeholder
- `TEMPLATE-findings.md` — header, per-dimension block, weave-in placeholders for GH/Octopus evidence, revision log placeholder
- `TEMPLATE-suggestions.md` — framing preamble, suggestion block using `gap → unlock → cost`, dependency-map sequence rule, revision log placeholder

Each template includes the file's revision log section at the bottom so the format is consistent across files.

The `TEMPLATE.md` file is removed.

### `skills/cd-discovery/GH-DISCOVERY.md`

- Output instruction changes from "produce a 'GitHub Repository Posture' section" to "produce a weave map."
- **Weave map format** — a structured list of evidence items, each tagged with the target dimension(s) in `findings.md`. Example:
  ```
  Testing: .github/workflows/ci.yml:34 — no E2E job runs on the default-branch trigger
  Security: branch protection on `main` does not require code scanning to pass
  Build & CI: workflow execution reality — 12% failure rate over last 50 runs on `build-and-test`
  ```
- The "Cross-stitch into capability matrix" section becomes the weave map (same idea, different consumption pattern). The strategist drops items into `findings.md` rather than reading a self-contained section and re-interpreting it.

### `skills/cd-discovery/OCTOPUS-DISCOVERY.md`

- Output instruction changes from "produce a 'Deployment Orchestrator' section" to "produce a weave map" — same format as GH above.
- Items tag the relevant dimensions (most will tag Deployment Automation; some will tag Release Process or Observability).

### `skills/cd-discovery/UPDATE-PLAYBOOK.md`

- Phase 1 (Ingest) — read all files in `cd-discovery/` (two or three), not a single file.
- Phase 3 (Decompose into atomic claims) — each claim is tagged with target file(s).
- Phase 5 (Edit in place) — `Edit` calls target the relevant files; no whole-file rewrites.
- Phase 6 (Revision entry) — appends a per-file revision entry to each file the agent touched.
- Quality Gate — applied per file the agent touched.

### User-facing docs (`README.md`, `INSTALL.md`)

- Replace `--assess` references with `--suggest`.
- Update output filename references (`CD-DISCOVERY.md` → `cd-discovery/summary.md`, `findings.md`, `suggestions.md`) where the docs describe the artifact location.
- Update the `--suggest` description to drop "phased improvement roadmap" language in favor of the suggestion voice (resource, not plan).

## Cross-File Conventions

- **Cross-links** — `summary.md` links to `findings.md` (always) and `suggestions.md` (when present) using relative paths. `findings.md` may link back to `summary.md` for the matrix view. `suggestions.md` may link to `findings.md` for the gap evidence.
- **Standalone-readable** — each file has a date + repository header so a reader who arrives via a direct link knows which scan it is from. The headers are short (one line is enough).
- **Revision log section header** — `## Revision history` at the bottom of each file. Entries use `### YYYY-MM-DD — <event>` format. The migration entry uses `### YYYY-MM-DD — migrated from CD-DISCOVERY.md`. Update entries use `### YYYY-MM-DD — context refresh`.
- **No global changelog file** — there is no `cd-discovery/CHANGELOG.md`. Each file owns its own audit trail.

## Open Items for Implementation

Items deliberately left for the implementation plan to resolve:

- Exact ordering of dimensions in `summary.md` matrix and `findings.md` (preserve current template order unless implementer finds a reason to change).
- Whether `summary.md` includes a one-line discovery-source attestation block ("scanned via codebase + gh Tier 1 + Octopus questionnaire") at the top, or only inline.
- The exact wording of the suggestion-voice preamble in `suggestions.md` and `TEMPLATE-suggestions.md`.
- Whether the legacy-detection prompt offers a "diff preview" of what migration would do before committing.

## Out of Scope

- Source-file decomposition of `continuous-delivery-strategist.md` or `SKILL.md` (those stay single-file).
- A separate sub-command for suggestions (the `--suggest` flag stays on `/cd-discovery`, not a new top-level command).
- One-file-per-dimension granularity (per-dimension content stays in `findings.md`).
- Time-duration estimates in suggestions (the existing no-estimates rule is preserved).
