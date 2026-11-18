---
name: cd-discovery
description: "Automated CI/CD pipeline discovery — scans codebase for deployment artifacts, interviews user about gaps, produces structured input for the continuous-delivery-strategist agent"
argument-hint: "[--skip-interview] [--suggest] [--update [<context-or-path>]] [--skip-github] [--octopus-url <url>] [--octopus-space <id-or-name>] [--octopus-project <name>]"
allowed-tools:
  - Read
  - Edit
  - Bash
  - Agent
  - AskUserQuestion
---

Thin launcher that spawns only the `continuous-delivery-strategist` agent to perform expert-driven CI/CD discovery. The strategist owns questions, scope, consent/access setup, assessment, and reporting; it coordinates the `cd-evidence-collector` for source collection and may selectively spawn the three evidence-only analysts after validating the canonical evidence document. Do not launch the collector or analysts directly from this skill.

## Parse Arguments

Extract flags from `$ARGUMENTS`:
- `--skip-interview` — skip the post-scan interview step; leave gaps tagged `[NEEDS CLARIFICATION]` in `findings.md`
- `--suggest` — after writing `cd-discovery/summary.md` and `findings.md`, also write `cd-discovery/suggestions.md` with the suggestion-voice framing (resource, not prescription). If `summary.md` and `findings.md` already exist (no `suggestions.md` yet), generate `suggestions.md` only against the existing findings without re-scanning.
- `--update [<context-or-path>]` — apply additional context to the existing `cd-discovery/` directory instead of running a fresh discovery. The optional argument may be (a) an inline string of context, or (b) a path to a file containing the context. If omitted, the strategist uses the launcher interview flow to obtain context. Routes to `UPDATE-PLAYBOOK.md`.
- `--skip-github` — skip the GitHub sub-playbook even if the repo has a github.com remote and `gh` is authenticated. Falls back to env var `GH_DISCOVERY_SKIP=1` if set.
- `--octopus-url <url>` — Octopus Deploy server URL (e.g. `https://octopus.internal`). Falls back to env var `OCTOPUS_URL` if omitted.
- Octopus API credentials — provide `OCTOPUS_API_KEY` only through an approved runtime secret or environment injection. Do not pass an API key as a command-line flag or prompt argument. The key must never enter strategist/collector prompts, shell history, process arguments, reports, or `evidence.md`.
- `--octopus-space <id-or-name>` — Octopus space ID (e.g. `Spaces-1`) or display name. Falls back to env var `OCTOPUS_SPACE`, then to the default space.
- `--octopus-project <name>` — restrict Octopus discovery to a specific project name or slug. Falls back to env var `OCTOPUS_PROJECT`. If omitted, the strategist asks the user to confirm the intended project scope through the launcher interview flow; do not infer or select an ambiguous project from source scans.

### Resolve Octopus mode

After parsing, resolve which Octopus discovery tier to run:
- **Tier 1 (API)** — if both URL and API key are available through the approved runtime/environment. The strategist authorizes and scopes this access, then passes the collector the URL and approved space/project scope. The collector uses the key only through the existing authorized environment/runtime mechanism and documented curl stdin config; never put the key in an agent prompt, command argument, or evidence document.
- **Tier 2 (CaC)** — if Tier 1 inputs are not present, the collector looks for `.octopus/**/*.ocl` files within the approved target repository or uses an explicitly scoped CaC repo path the strategist obtained from the user.
- **Tier 3 (Questionnaire)** — the collector first checks the explicitly approved repository/CaC scope. If no CaC source is available, it returns a structured clarification handoff; the top-level skill asks the user via `AskUserQuestion`, then resumes a targeted collector pass with sanitized answers. The headless strategist and collector never ask questions themselves.
- **Skip** — if the user provides `--octopus-url=none` or answers "we don't use Octopus" when asked, skip the sub-playbook entirely.

Before asking, check for a retirement or migration doc (e.g. `docs/**/octopus-retirement*`). If the repo documents Octopus as retired, skip the sub-playbook and cite that doc.

If no Octopus inputs are provided, no retirement doc was found, and `--skip-interview` is NOT set, the skill asks once whether the repo is deployed via Octopus before authorizing that source family. Detailed Tier 3 questions or ambiguous-project clarifications are asked only after the collector returns a structured handoff, then passed into a targeted collector continuation. The collector does not interview the user.

### Resolve GitHub mode

After parsing, resolve whether to run the GitHub sub-playbook:
1. Detect a GitHub remote: `git remote -v | grep -qE 'github\.com[:/]'`. If no GitHub remote, skip — no section in the output.
2. If `--skip-github` (or `GH_DISCOVERY_SKIP=1`) is set, skip — tag the section `[SKIPPED by user]`.
3. Otherwise check `gh auth status`. If authenticated → pass approved repository scope and existing `gh` access context for the collector to run **Tier 1** of `GH-DISCOVERY.md`. If not authenticated and the user still wants GitHub evidence → run the collector's Tier 2 clarification handoff, ask the returned questions through the top-level skill, then resume a targeted collector pass with sanitized answers. Alternatively, the user may run `gh auth login` and restart discovery. Never let the collector or headless strategist ask the user directly.

GitHub discovery requires no flags by default — if `gh` is authenticated and the repo is on GitHub, the sub-playbook runs automatically.

## Check for Existing Output

Resolve existing-output state in this order. The first matching condition determines the dispatch path. State variables: `HAS_NEW_DIR` (cd-discovery/ directory exists with at least summary.md), `HAS_LEGACY_FILE` (CD-DISCOVERY.md exists at project root), `HAS_SUGGESTIONS` (cd-discovery/suggestions.md exists).

### Dispatch precedence

If both `HAS_NEW_DIR` and `HAS_LEGACY_FILE` are true, the new directory wins — proceed as if only the directory existed. Print a one-line warning: "Stale `CD-DISCOVERY.md` detected alongside `cd-discovery/`. The new directory takes precedence. Remove the legacy file when convenient." Do not auto-delete the legacy file.

### Workflow dispatch

| Condition | `--update` flag? | `--suggest` flag? | Dispatch |
|---|---|---|---|
| Neither HAS_NEW_DIR nor HAS_LEGACY_FILE | — | no | **W1**: Spawn the agent for fresh discovery (writes summary + findings) |
| Neither HAS_NEW_DIR nor HAS_LEGACY_FILE | — | yes | **W2**: Spawn the agent for fresh discovery + suggestions (writes all three) |
| HAS_NEW_DIR, no HAS_SUGGESTIONS | no | yes | **W3**: Spawn the agent in `suggestions-only` mode — read existing findings, write `suggestions.md`. No re-scan. |
| HAS_NEW_DIR, HAS_SUGGESTIONS | no | yes | **W4-scoped**: Show the existing-report prompt scoped to `suggestions.md` (overwrite / update / cancel). Overwrite regenerates `suggestions.md` only against existing findings. |
| HAS_NEW_DIR | no | no | **W4**: Show the existing-report prompt (overwrite / update / cancel) against the whole directory. |
| HAS_NEW_DIR | yes | — | Skip the prompt; spawn the update agent (see "Spawn the Update Agent" in this file). |
| HAS_LEGACY_FILE, no HAS_NEW_DIR | yes | — | **Abort with**: "Legacy CD-DISCOVERY.md found but no cd-discovery/ directory. Run `/cd-discovery` (without `--update`) and choose Migrate, then re-run with `--update`." |
| HAS_LEGACY_FILE, no HAS_NEW_DIR | no | — | **W5**: Show the legacy-detection prompt (migrate / fresh / cancel). See "Spawn the Migrate Agent" for the migrate path. |

### W4 prompt (whole directory)

Use AskUserQuestion with three options:

1. **Overwrite** — discard `cd-discovery/` and run a fresh discovery (W1 or W2 based on `--suggest`).
2. **Update** — run the update flow (Spawn the Update Agent) with the user's context applied to the directory as a whole.
3. **Cancel** — exit without changes.

Show the modification date of the most-recently-modified file in `cd-discovery/` so the user has freshness context.

### W4-scoped prompt (suggestions only)

Use AskUserQuestion with four options:

1. **Regenerate suggestions** — discard `cd-discovery/suggestions.md`, regenerate it against existing findings (no re-scan). Summary and findings are untouched.
2. **Update suggestions** — run the update flow scoped to `suggestions.md` with the user's context.
3. **Regenerate all** — discard the whole `cd-discovery/` directory and run a fresh discovery with suggestions (W2). Use when findings are stale too.
4. **Cancel** — exit without changes.

### W5 legacy-detection prompt

Use AskUserQuestion with three options:

1. **Migrate** — read `CD-DISCOVERY.md`, split into the new `cd-discovery/` layout, preserve content and revision history, remove the legacy file via `git rm`. If `--suggest` was passed, continue into suggestions generation against the migrated findings.
2. **Fresh** — discard the legacy file (user retains it manually if they want), run W1 or W2.
3. **Cancel** — exit without changes.

## Spawn the Agent

Launch the `continuous-delivery-strategist` agent with `subagent_type: "continuous-delivery-strategist"` and the following prompt structure:

```
<objective>
Execute CI/CD discovery for this repository and write the requested `cd-discovery/` reports. You own discovery questions, scope, consent/access setup, assessment, synthesis, and report authorship, but do not collect source evidence yourself.

For fresh discovery, launch `cd-evidence-collector` with a bounded, read-only request covering the relevant repository categories and any authorized GitHub/Octopus sources. The collector writes `<target-repo>/cd-discovery/evidence.md`, the canonical evidence interface. Validate collection readiness, coverage/dispositions, scope, source references, limitations, and secret-safety before using it. Then selectively launch `ci-artifact-integrity` for a relevant CI/build/test/artifact slice, `release-safety-recovery` for relevant post-handoff deployment/release controls, and `delivery-metrics-flow` only when time-bounded actual evidence exists or the user explicitly requests metric analysis and a defensible scope can be established. Give analysts only bounded sections/source IDs from `evidence.md`; they return CI-/REL-/FLOW- records and must not collect sources, query APIs, interview, assess/score maturity or severity, prioritize, recommend, or write reports. Do not invoke analysts by default or when coordination overhead exceeds evidence benefit.

Read `EVIDENCE-LEDGER.md`. Validate collector coverage and every analyst record's required fields, status, confidence and reason, scope, source attribution, and limitations; check stable IDs, duplicates, and conflicts. Append accepted analyst records under `## Analyst findings` in `evidence.md`; use their IDs with source citations in findings. Reconcile overlapping evidence under one canonical owner/ID, preserve conflicting sources, and keep artifact handoff ownership explicit: CI analyst through handoff, release analyst after handoff. Pass GitHub/Octopus scope and approved access context to the collector, not analysts. Credentials must never be embedded in agent prompts or evidence; preserve existing auth runtime/environment constraints and pass only sanitized evidence to analysts.

For summary/findings-only work against existing reports, use existing reports and evidence; do not recollect unless a material evidence gap requires it. For updates, use the collector only for targeted recollection of source slices needed to verify claims, not a full rescan by default.

Always write:
- cd-discovery/summary.md (from TEMPLATE-summary.md)
- cd-discovery/findings.md (from TEMPLATE-findings.md)

{If --suggest:}
Additionally write:
- cd-discovery/suggestions.md (from TEMPLATE-suggestions.md)

The suggestions file uses the suggestion voice: lead with tradeoffs (gap → what improving unlocks → cost/disruption), not directives. Express sequence as a dependency map; engineers own sequencing. No time-duration estimates. Do not use the word "roadmap."

You are being spawned as a headless subagent for automated discovery — you have no channel back to the user. Do not call AskUserQuestion. Tag every gap per Phase 3 of the playbook, with a specific, targeted question embedded directly in each [NEEDS CLARIFICATION: ...] tag.

{If incremental suggest (W3): "Do NOT re-scan. Read the existing cd-discovery/summary.md and findings.md and write only cd-discovery/suggestions.md against the existing findings."}
</objective>

<required_reading>
Read these files before starting:
1. ~/.claude/skills/cd-discovery/PLAYBOOK.md — Discovery methodology and ownership boundaries
2. ~/.claude/skills/cd-discovery/EVIDENCE-LEDGER.md — Canonical evidence document and analyst record contracts
3. `agents/cd-evidence-collector.md` in this checkout (or the configured `cd-evidence-collector` agent definition) — Collector responsibilities and safe handling
4. ~/.claude/skills/cd-discovery/TEMPLATE-summary.md — Template for cd-discovery/summary.md
5. ~/.claude/skills/cd-discovery/TEMPLATE-findings.md — Template for cd-discovery/findings.md
6. ~/.claude/skills/cd-discovery/TEMPLATE-suggestions.md — Template for cd-discovery/suggestions.md (only required when --suggest is in scope)
7. ~/.claude/skills/cd-discovery/OCTOPUS-DISCOVERY.md — Octopus Deploy source procedure for the collector (only when Octopus is in scope)
8. ~/.claude/skills/cd-discovery/GH-DISCOVERY.md — GitHub source procedure for the collector (only when the repo is on GitHub)
</required_reading>

<octopus_inputs>
{If Tier 1 resolved:}
  OCTOPUS_URL: {url}
  OCTOPUS_SPACE: {space-or-empty}
  OCTOPUS_PROJECT: {project-or-empty}
  API key is available only through the existing authorized environment/runtime mechanism; it is not included in this prompt or evidence document. The strategist passes the collector the URL and approved space/project scope. The collector runs Tier 1 of OCTOPUS-DISCOVERY.md and records sanitized observations in evidence.md.
{Elif Tier 2 candidate:}
  No Octopus API access in scope. The collector looks for explicitly in-scope .octopus/**/*.ocl sources and follows Tier 2 of OCTOPUS-DISCOVERY.md, recording observations in evidence.md.
{Elif Tier 3 fallback:}
  No Octopus API or CaC source is available. The launcher/strategist has obtained any consent and questionnaire answers (tagged [USER-REPORTED]); pass sanitized answers to the collector to record in evidence.md. The collector does not ask users. If none were supplied, preserve the Octopus slice as an explicit limitation for the strategist.
{Elif user opted out:}
  User has indicated this repo does not use Octopus. Do not run the Octopus sub-playbook.
</octopus_inputs>

If the collector returns a structured clarification handoff because the Octopus project/space is ambiguous or questionnaire input is needed, pause strategist execution and return the exact bounded question(s) and sanitized choices to the top-level skill. The skill asks the user, then invokes a targeted strategist/collector continuation with sanitized answers. If `--skip-interview` is set, do not ask; preserve the explicit blocker and [NEEDS CLARIFICATION] tag.

<github_inputs>
{If repo has a github.com remote AND gh is authenticated AND NOT --skip-github:}
  The strategist passes the approved repository scope and existing authenticated `gh` access context to the collector for Tier 1 of GH-DISCOVERY.md. Do not include auth tokens in the prompt or evidence. The collector records sanitized observations in evidence.md; do not print authenticated identities to the report or evidence.
{Elif repo has a github.com remote AND --skip-github:}
  Skip the GitHub sub-playbook. Do not write GitHub evidence to the findings.
{Elif repo has a github.com remote AND gh is unauthenticated:}
  gh is not authenticated and the launcher has handled it: either sanitized Tier 2 questionnaire answers (tagged [USER-REPORTED]) are supplied for the collector to record, or none were and the GitHub slice remains explicitly limited. Do not prompt the user from the headless agent.
{Else (no github.com remote):}
  Skip the GitHub sub-playbook silently — not applicable.
</github_inputs>

<framing_rule>
When collected GitHub observations show missing branch protection or required status checks on a default branch, do NOT classify that as a high-severity finding in isolation. First survey Observability, Testing, and Deployment Automation. Severity emerges from the combination — trunk-based development legitimately commits directly to main, and what matters is whether bad commits get noticed and rolled back fast enough. Document the reasoning with the cited evidence so the reader can audit the severity call.
</framing_rule>

<output>
- Ensure the collector has written and you have validated cd-discovery/evidence.md before writing cd-discovery/summary.md and cd-discovery/findings.md.
- If --suggest is in scope, write cd-discovery/suggestions.md.
- Use GitHub and Octopus observations from evidence.md in the relevant findings.md dimensions and summary.md Strengths to Protect where applicable. Do not create dedicated "GitHub Repository Posture" or "Deployment Orchestrator" sections.
- Save project findings to your agent memory — record the cd-discovery/ directory path, not CD-DISCOVERY.md. Never store auth tokens (Octopus API key, gh token), secret values, sensitive variable values, full alert payloads, or full PR content.
</output>
```

The collector must use the existing authorized runtime/environment mechanism for Tier 1 Octopus calls. Never place the API key in an agent prompt, CLI argument, shell history, process listing, report, or evidence document. The Octopus sub-playbook demonstrates passing it to curl through stdin configuration to avoid process-argument exposure.

## Interview Gaps

Runs after the fresh-discovery agent (W1/W2) returns and `cd-discovery/findings.md` has been written, before Report Completion. The subagent never calls `AskUserQuestion` itself (see "Spawn the Agent" above) — this step is where the interview actually happens, at the top level.

**Write fallback:** if the agent reports it could not write the report files (some harnesses block subagent writes to report paths), it returns the full content of each file in its final message. The launcher then verifies the content is complete, un-escapes any HTML entities (`&gt;`, `&lt;`, `&amp;`), and writes the files itself before continuing. Do not re-spawn the agent just to retry the write.

1. If `--skip-interview` was passed: skip this section entirely. Report completion with gap count only (tags remain in place).
2. Read `cd-discovery/findings.md` and locate every `[NEEDS CLARIFICATION: <question>]` tag, grouped by the dimension section it appears under.
3. If none found: skip to Report Completion.
4. Otherwise, present the dimension-by-dimension summary (level, key findings, gap count per dimension) and use `AskUserQuestion` to ask which dimensions the user wants to discuss: options are each dimension with gaps, plus "all" and "none (leave tagged)".
5. If the user picks "none": skip to Report Completion with tags left in place.
6. For each selected dimension, ask its extracted targeted question(s) via `AskUserQuestion` (2-3 per dimension, batched into as few calls as the tool allows). `AskUserQuestion` takes at most 4 questions per call, so merge related gaps into themed questions. An answer of "unknown" or "don't recall" does NOT resolve a gap: leave that `[NEEDS CLARIFICATION]` tag in place and exclude it from the assembled context.
7. Assemble every question+answer pair into a single context string, one entry per resolved gap:
   ```
   Dimension: <name>
   Q: <the [NEEDS CLARIFICATION] question text>
   A: <user's answer>
   ```
8. Automatically invoke "Spawn the Update Agent" (below) using this assembled string as the `INLINE` context — do not prompt the user again for `--update`-style context; this *is* that context.

## Spawn the Update Agent

Used when the user chose **Update** (either by `--update` flag or by the existing-report prompt), or when the "Interview Gaps" step above auto-invokes it with interview answers. Launch the `continuous-delivery-strategist` agent with `subagent_type: "continuous-delivery-strategist"` and the following prompt structure:

```
<objective>
Update the existing cd-discovery/ directory by folding in additional context the user has supplied. Each claim must be tagged with the file(s) it touches ([summary], [findings], [suggestions], or multi-tag). Multi-file claims (e.g., a dimension level change) must edit both the matrix row in summary.md AND the per-dimension section in findings.md in the same pass. Use existing evidence.md and reports first; only when a claim needs fresh verification, ask `cd-evidence-collector` for targeted recollection of the touched source slices. Do not scan sources or query APIs yourself. Verify every claim that can be verified against collected evidence; tag the rest [USER-REPORTED] and lower confidence accordingly. Edit each file in place using granular Edit calls — preserve the audit trail by reframing prior findings rather than deleting them. Append a per-file revision log entry to each file the agent touched.

{If auto-invoked from the post-scan Interview Gaps step:} This context is answers from the interview immediately following a fresh discovery. Resolve each matching [NEEDS CLARIFICATION] tag directly — replace it with the resolved finding and revised level/confidence. Tags with no matching answer stay as [NEEDS CLARIFICATION].
</objective>

<required_reading>
Read these files before starting:
1. All files under cd-discovery/ at the project root — current reports (summary.md, findings.md, and suggestions.md if present)
2. ~/.claude/skills/cd-discovery/UPDATE-PLAYBOOK.md — update methodology (Phases 1–6 and Quality Gate)

Re-read these only if a user claim needs the corresponding slice re-verified:
3. ~/.claude/skills/cd-discovery/PLAYBOOK.md — for CODEBASE-verifiable claims
4. ~/.claude/skills/cd-discovery/GH-DISCOVERY.md — for GITHUB-API-verifiable claims
5. ~/.claude/skills/cd-discovery/OCTOPUS-DISCOVERY.md — for OCTOPUS-API-verifiable claims
</required_reading>

<user_context>
{If --update was passed with an inline string:}
  INLINE: "{the literal string the user passed}"
{Elif --update was passed with a file path:}
  FILE_PATH: {the path — read its contents before Phase 2}
{Else (interactive capture):}
  No context supplied yet. Run Phase 2 interactive capture from UPDATE-PLAYBOOK.md.
</user_context>

<verification_inputs>
{Reuse the Octopus and GitHub resolution from the Spawn the Agent block above.}
{If Octopus Tier 1 is resolved:} OCTOPUS_URL / OCTOPUS_SPACE / OCTOPUS_PROJECT are available to scope collector requests; the API key remains only in the authorized runtime/environment and is never included in an agent prompt. Octopus-API claims can be re-verified slice-by-slice by the collector.
{If Octopus Tier 1 NOT resolved:} Skip Octopus re-verification — tag Octopus-API claims [USER-REPORTED] and note in the revision header that the Octopus side was not re-scanned this pass.
{If gh is authenticated:} GitHub-API claims can be re-verified slice-by-slice by the collector using existing gh auth. Do not print authenticated identities or include tokens in prompts or evidence.
{If gh is unauthenticated:} Skip GitHub re-verification — tag GitHub-API claims [USER-REPORTED] and note in the revision header.
</verification_inputs>

<execution>
Execute UPDATE-PLAYBOOK.md Phases 1 through 6 in order:
- Phase 1: Ingest current report into a working memory index
- Phase 2: Capture user context (skip interactive step if inline string / file path supplied)
- Phase 3: Decompose into atomic claims; show the list to the user for confirmation before proceeding
- Phase 4: Targeted verification — use existing evidence first; when necessary, have the collector recollect only the source slices the user's claims touch. Surface any CONTRADICTED claim to the user before editing.
- Phase 5: Edit the relevant file(s) under cd-discovery/ in place using the Edit tool (granular edits only — no Write of the whole file). Multi-file claims (e.g., a dimension level change) must touch both summary.md's matrix row AND findings.md's dimension section in the same pass.
- Phase 6: Append a per-file "### <today> — context refresh" entry to each file's bottom "## Revision history" section. Files the agent did not touch get no entry today.

Apply the Quality Gate at the end. Do not declare done if any item is unchecked.
</execution>

<output>
- Edit the relevant file(s) in cd-discovery/ using granular Edit calls (no whole-file rewrites).
- Append a per-file revision log entry to each file the agent touched (## Revision history at the bottom). Files not touched get no entry today.
- Save updated project findings to your agent memory — never store auth tokens, secret values, sensitive variable values, full alert payloads, or full PR content.
- Report which claims verified, which were contradicted (with user resolution), and which remain [USER-REPORTED] and why. Note which file(s) each claim updated.
</output>
```

The collector uses the existing authorized runtime/environment mechanism for Tier 1 Octopus re-verification; never pass the API key in its prompt or as a CLI argument.

## Spawn the Migrate Agent

Used when the user chose **Migrate** in the W5 legacy-detection prompt. Launch the `continuous-delivery-strategist` agent with `subagent_type: "continuous-delivery-strategist"` and the following prompt structure:

```
<objective>
A legacy CD-DISCOVERY.md exists at the project root and the user has chosen to migrate it to the new cd-discovery/ directory layout. Split the legacy file into cd-discovery/summary.md, cd-discovery/findings.md, and (if the legacy file contained roadmap content) cd-discovery/suggestions.md. Preserve all content. Preserve the revision history. Remove the legacy file via `git rm` once the new files are written so the migration lands as a single reviewable commit.

{If --suggest was also passed AND the legacy file had no roadmap content:}
After migration, continue into suggestions generation against the migrated findings (write cd-discovery/suggestions.md using TEMPLATE-suggestions.md and the suggestion voice).
</objective>

<required_reading>
1. CD-DISCOVERY.md at the project root — the legacy file to migrate
2. ~/.claude/skills/cd-discovery/TEMPLATE-summary.md — target template
3. ~/.claude/skills/cd-discovery/TEMPLATE-findings.md — target template
4. ~/.claude/skills/cd-discovery/TEMPLATE-suggestions.md — target template (only required if migrating roadmap content or running --suggest after migration)
</required_reading>

<procedure>
1. Read the legacy file end-to-end.
2. Validate parseability: the legacy file must contain at least an Executive Summary, Capability Matrix, and one Detailed Findings dimension. If not, abort migration and report the validation failure to the launcher so it can offer Fresh as a fallback.
3. Split by section:
   - Executive Summary, Capability Matrix, Strengths to Protect, Anti-Patterns Detected, Recommended Next Steps → cd-discovery/summary.md
   - Detailed Findings (per dimension) → cd-discovery/findings.md
   - "Deployment Orchestrator" section content → woven into the Deployment dimension of cd-discovery/findings.md
   - "GitHub Repository Posture" section content → woven into Build & CI / Security / Release Process dimensions per the legacy file's cross-stitch lines
   - Pre-existing roadmap content (from prior --assess runs) → cd-discovery/suggestions.md, reframed from directive voice to suggestion voice (gap → what improving unlocks → cost/disruption; sequence as dependency map)
4. Preserve revision history: if the legacy file has a "Changes from previous report" or revision section, copy entries into each new file's revision log by topic. Entries that cannot be cleanly assigned go to cd-discovery/summary.md's log with a note.
5. Prepend a migration entry to each new file's revision log:

   ### YYYY-MM-DD — migrated from CD-DISCOVERY.md
   - Content split into new layout; see git history for the source file.

6. Remove the legacy file via `git rm CD-DISCOVERY.md`.
7. Create `cd-discovery/evidence.md` with `State: PARTIAL`, `Ready: no`, a migration-only run, and a `SKIPPED` source inventory entry explaining that legacy findings were not re-verified. Do not represent legacy claims as current collection evidence.
8. If --suggest was passed AND step 3 did not produce a suggestions.md (no legacy roadmap content), continue into suggestions generation using TEMPLATE-suggestions.md.
</procedure>

<sub_playbook_weaving>
When weaving "Deployment Orchestrator" or "GitHub Repository Posture" content into findings.md dimensions, follow the dimension assignment from the legacy file's cross-stitch lines (e.g., "Build & CI: L1 → L2 because ..."). When a cross-stitch row is ambiguous (e.g., mentions multiple dimensions), put the evidence under the most-cited dimension and add "see also" notes referencing the other dimensions.
</sub_playbook_weaving>

<output>
- cd-discovery/summary.md, cd-discovery/findings.md, and (when applicable) cd-discovery/suggestions.md written.
- cd-discovery/evidence.md records migration provenance and explicitly remains not-ready until a fresh collection.
- CD-DISCOVERY.md removed via git rm.
- Each new file has a migration entry at the top of its Revision history.
- Save findings to agent memory under the new cd-discovery/ path; if memory previously referenced CD-DISCOVERY.md for this repo, update the reference.
- Report a short summary: which files were written, whether suggestions.md was generated this pass, and whether any cross-stitch ambiguity required a "see also" note.
</output>
```

## Report Completion

After the agent returns:

**Fresh-discovery path:**
- If `--suggest` was NOT set: display that `cd-discovery/summary.md` and `cd-discovery/findings.md` have been written. Mention that the user can run `/cd-discovery --suggest` to generate a `suggestions.md` file with gap analysis, tradeoffs, and a dependency map.
- If `--suggest` was set: the agent will have produced all three files. Display the summary.
- If Octopus discovery ran, mention which tier was used (API / CaC / Questionnaire) so the user understands the confidence level.
- If GitHub discovery ran, mention which tier was used (Tier 1 / Tier 2); do not expose authenticated identity details in the report or evidence document.
- If the Interview Gaps step ran: report how many gaps were found, how many were resolved via interview, and how many remain `[NEEDS CLARIFICATION]`. Remind the user to `git diff cd-discovery/` before committing, same as the Update path.

**Update path:**
- Display a 3-5 line summary: which dimensions had level/confidence changes, how many claims verified vs. user-reported, whether GitHub / Octopus were re-scanned this pass, and the location of the new bottom-of-file revision entry.
- If any claims were `CONTRADICTED` and the user overrode the codebase/API, surface that explicitly so the user remembers the override exists in the report.
- Remind the user to `git diff cd-discovery/` before committing if they want to review the edits.

**Migration path (W5):**
- Display a 3-5 line summary: which files were written, whether `suggestions.md` was generated this pass (either from legacy roadmap content or from a `--suggest` continuation), and whether the legacy `CD-DISCOVERY.md` was removed via `git rm`.
- Remind the user to `git status` to see the staged deletion + new directory and `git diff --cached` to review the migration before committing.
