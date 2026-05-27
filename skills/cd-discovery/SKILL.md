---
name: cd-discovery
description: "Automated CI/CD pipeline discovery — scans codebase for deployment artifacts, interviews user about gaps, produces structured input for the continuous-delivery-strategist agent"
argument-hint: "[--skip-interview] [--suggest] [--update [<context-or-path>]] [--skip-github] [--octopus-url <url>] [--octopus-api-key <key>] [--octopus-space <id-or-name>] [--octopus-project <name>]"
allowed-tools:
  - Read
  - Edit
  - Bash
  - Agent
  - AskUserQuestion
---

Thin launcher that spawns the `continuous-delivery-strategist` agent to perform expert-driven CI/CD discovery.

## Parse Arguments

Extract flags from `$ARGUMENTS`:
- `--skip-interview` — skip the interactive gap interview; tag gaps with `[NEEDS CLARIFICATION]`
- `--suggest` — after writing `cd-discovery/summary.md` and `findings.md`, also write `cd-discovery/suggestions.md` with the suggestion-voice framing (resource, not prescription). If `summary.md` and `findings.md` already exist (no `suggestions.md` yet), generate `suggestions.md` only against the existing findings without re-scanning.
- `--update [<context-or-path>]` — apply additional context to an existing `CD-DISCOVERY.md` instead of running a fresh discovery. The optional argument may be (a) an inline string of context, or (b) a path to a file containing the context. If omitted, the agent prompts the user for context interactively. Routes to `UPDATE-PLAYBOOK.md`.
- `--skip-github` — skip the GitHub sub-playbook even if the repo has a github.com remote and `gh` is authenticated. Falls back to env var `GH_DISCOVERY_SKIP=1` if set.
- `--octopus-url <url>` — Octopus Deploy server URL (e.g. `https://octopus.internal`). Falls back to env var `OCTOPUS_URL` if omitted.
- `--octopus-api-key <key>` — Octopus API key (`API-...`). Falls back to env var `OCTOPUS_API_KEY` if omitted. **Never echo to terminal or report.**
- `--octopus-space <id-or-name>` — Octopus space ID (e.g. `Spaces-1`) or display name. Falls back to env var `OCTOPUS_SPACE`, then to the default space.
- `--octopus-project <name>` — restrict Octopus discovery to a specific project name or slug. Falls back to env var `OCTOPUS_PROJECT`. If omitted, the agent infers candidates from the repo name and confirms via `AskUserQuestion`.

### Resolve Octopus mode

After parsing, resolve which Octopus discovery tier to run:
- **Tier 1 (API)** — if both URL and API key are present (flag or env var). The agent will use them via curl with `X-Octopus-ApiKey` headers.
- **Tier 2 (CaC)** — if Tier 1 inputs are not present, the agent looks for `.octopus/**/*.ocl` files in the current repo or asks the user for a CaC repo path.
- **Tier 3 (Questionnaire)** — if neither Tier 1 nor Tier 2 is available, the agent asks the user a structured set of questions via `AskUserQuestion`.
- **Skip** — if the user provides `--octopus-url=none` or answers "we don't use Octopus" when asked, skip the sub-playbook entirely.

If no Octopus inputs are provided and `--skip-interview` is NOT set, the agent should ask once whether the repo is deployed via Octopus before deciding which tier to run.

### Resolve GitHub mode

After parsing, resolve whether to run the GitHub sub-playbook:
1. Detect a GitHub remote: `git remote -v | grep -qE 'github\.com[:/]'`. If no GitHub remote, skip — no section in the output.
2. If `--skip-github` (or `GH_DISCOVERY_SKIP=1`) is set, skip — tag the section `[SKIPPED by user]`.
3. Otherwise check `gh auth status`. If authenticated → run **Tier 1** of `GH-DISCOVERY.md`. If not authenticated → either prompt the user to run `gh auth login` or fall back to **Tier 2** (questionnaire) per the sub-playbook.

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

Use AskUserQuestion with three options:

1. **Regenerate suggestions** — discard `cd-discovery/suggestions.md`, regenerate it against existing findings (no re-scan). Summary and findings are untouched.
2. **Update suggestions** — run the update flow scoped to `suggestions.md` with the user's context.
3. **Cancel** — exit without changes.

### W5 legacy-detection prompt

Use AskUserQuestion with three options:

1. **Migrate** — read `CD-DISCOVERY.md`, split into the new `cd-discovery/` layout, preserve content and revision history, remove the legacy file via `git rm`. If `--suggest` was passed, continue into suggestions generation against the migrated findings.
2. **Fresh** — discard the legacy file (user retains it manually if they want), run W1 or W2.
3. **Cancel** — exit without changes.

## Spawn the Agent

Launch the `continuous-delivery-strategist` agent with `subagent_type: "continuous-delivery-strategist"` and the following prompt structure:

```
<objective>
Execute CI/CD discovery for this repository. Read the discovery playbook, scan the codebase using its methodology, integrate any sub-playbook weave-map output into the relevant dimensions, and write the cd-discovery/ output directory at the project root.

Always write:
- cd-discovery/summary.md (from TEMPLATE-summary.md)
- cd-discovery/findings.md (from TEMPLATE-findings.md)

{If --suggest:}
Additionally write:
- cd-discovery/suggestions.md (from TEMPLATE-suggestions.md)

The suggestions file uses the suggestion voice: lead with tradeoffs (gap → what improving unlocks → cost/disruption), not directives. Express sequence as a dependency map; engineers own sequencing. No time-duration estimates. Do not use the word "roadmap."

{If --skip-interview: "Skip the interactive interview. Tag all gaps with [NEEDS CLARIFICATION] instead."}
{If NOT --skip-interview: "After scanning, present a summary and interview the user about gaps using AskUserQuestion."}

{If incremental suggest (W3): "Do NOT re-scan. Read the existing cd-discovery/summary.md and findings.md and write only cd-discovery/suggestions.md against the existing findings."}
</objective>

<required_reading>
Read these files before starting:
1. ~/.claude/skills/cd-discovery/PLAYBOOK.md — Discovery methodology to execute
2. ~/.claude/skills/cd-discovery/TEMPLATE-summary.md — Template for cd-discovery/summary.md
3. ~/.claude/skills/cd-discovery/TEMPLATE-findings.md — Template for cd-discovery/findings.md
4. ~/.claude/skills/cd-discovery/TEMPLATE-suggestions.md — Template for cd-discovery/suggestions.md (only required when --suggest is in scope)
5. ~/.claude/skills/cd-discovery/OCTOPUS-DISCOVERY.md — Octopus Deploy sub-playbook (only when Octopus is in scope)
6. ~/.claude/skills/cd-discovery/GH-DISCOVERY.md — GitHub sub-playbook (only when the repo is on GitHub)
</required_reading>

<octopus_inputs>
{If Tier 1 resolved:}
  OCTOPUS_URL: {url}
  OCTOPUS_SPACE: {space-or-empty}
  OCTOPUS_PROJECT: {project-or-empty}
  OCTOPUS_API_KEY: provided via env var to subsequent bash calls — do NOT echo, do NOT include in report or memory.
  Run Tier 1 of OCTOPUS-DISCOVERY.md and produce a weave map (evidence-tagged findings to integrate into cd-discovery/findings.md dimensions).
{Elif Tier 2 candidate:}
  No Octopus API credentials provided. Look for .octopus/**/*.ocl in the repo (or sibling repos the user points at) and run Tier 2 of OCTOPUS-DISCOVERY.md to produce a weave map.
{Elif Tier 3 fallback:}
  No Octopus credentials or CaC found. Ask the user once whether this repo is deployed via Octopus. If yes, run the Tier 3 questionnaire from OCTOPUS-DISCOVERY.md and produce a weave map. If no, skip the Octopus sub-playbook.
{Elif user opted out:}
  User has indicated this repo does not use Octopus. Do not run the Octopus sub-playbook.
</octopus_inputs>

<github_inputs>
{If repo has a github.com remote AND gh is authenticated AND NOT --skip-github:}
  Run Tier 1 of GH-DISCOVERY.md against the repo and produce a weave map. Use the existing gh CLI auth; do not echo auth tokens to the report or memory. Print the authenticated gh user and viewerPermission to the conversation as part of the preflight so the user can confirm identity.
{Elif repo has a github.com remote AND --skip-github:}
  Skip the GitHub sub-playbook. Do not write GitHub evidence to the findings.
{Elif repo has a github.com remote AND gh is unauthenticated:}
  Note that gh is not authenticated. Either prompt the user to run `gh auth login` (then resume Tier 1 to produce a weave map) or fall back to Tier 2 (questionnaire) from GH-DISCOVERY.md to produce a weave map.
{Else (no github.com remote):}
  Skip the GitHub sub-playbook silently — not applicable.
</github_inputs>

<framing_rule>
When the GitHub sub-playbook surfaces missing branch protection or missing required status checks on a default branch, do NOT classify that as a high-severity finding in isolation. First survey Observability, Testing, and Deployment Automation. Severity emerges from the combination — trunk-based development legitimately commits directly to main, and what matters is whether bad commits get noticed and rolled back fast enough. Document the reasoning explicitly in the weave-map evidence-tag reasoning so the reader can audit the severity call.
</framing_rule>

<output>
- Write cd-discovery/summary.md and cd-discovery/findings.md.
- If --suggest is in scope, write cd-discovery/suggestions.md.
- Weave GH and Octopus weave-map items into the relevant findings.md dimensions (and into summary.md's Strengths to Protect if tagged [strength-to-protect]). Do not create dedicated "GitHub Repository Posture" or "Deployment Orchestrator" sections.
- Save project findings to your agent memory — record the cd-discovery/ directory path, not CD-DISCOVERY.md. Never store auth tokens (Octopus API key, gh token), secret values, sensitive variable values, full alert payloads, or full PR content.
</output>
```

When invoking the agent's bash steps for Tier 1, pass the API key via the environment, e.g. `env OCTOPUS_API_KEY=$KEY curl -H "X-Octopus-ApiKey: $OCTOPUS_API_KEY" ...`. Never pass it as a CLI argument that would land in shell history or process listings.

## Spawn the Update Agent

Used when the user chose **Update** (either by `--update` flag or by the existing-report prompt). Launch the `continuous-delivery-strategist` agent with `subagent_type: "continuous-delivery-strategist"` and the following prompt structure:

```
<objective>
Update the existing cd-discovery/ directory by folding in additional context the user has supplied. Each claim must be tagged with the file(s) it touches ([summary], [findings], [suggestions], or multi-tag). Multi-file claims (e.g., a dimension level change) must edit both the matrix row in summary.md AND the per-dimension section in findings.md in the same pass. Verify every claim that can be verified against the codebase or live APIs (gh CLI, Octopus REST API); tag the rest [USER-REPORTED] and lower confidence accordingly. Edit each file in place using granular Edit calls — preserve the audit trail by reframing prior findings rather than deleting them. Append a per-file revision log entry to each file the agent touched.
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
{If Octopus Tier 1 is resolved:} OCTOPUS_URL / OCTOPUS_SPACE / OCTOPUS_PROJECT are available; OCTOPUS_API_KEY is in the environment — never echo. Octopus-API claims can be re-verified slice-by-slice.
{If Octopus Tier 1 NOT resolved:} Skip Octopus re-verification — tag Octopus-API claims [USER-REPORTED] and note in the revision header that the Octopus side was not re-scanned this pass.
{If gh is authenticated:} GitHub-API claims can be re-verified slice-by-slice. Print the authenticated gh user and viewerPermission to the conversation before any GitHub call.
{If gh is unauthenticated:} Skip GitHub re-verification — tag GitHub-API claims [USER-REPORTED] and note in the revision header.
</verification_inputs>

<execution>
Execute UPDATE-PLAYBOOK.md Phases 1 through 6 in order:
- Phase 1: Ingest current report into a working memory index
- Phase 2: Capture user context (skip interactive step if inline string / file path supplied)
- Phase 3: Decompose into atomic claims; show the list to the user for confirmation before proceeding
- Phase 4: Targeted verification — re-run only the scan slices the user's claims touch; surface any CONTRADICTED claim to the user before editing
- Phase 5: Edit CD-DISCOVERY.md in place using the Edit tool (granular edits only — no Write of the whole file)
- Phase 6: Prepend a new "### <today> — context refresh" entry to the bottom "Changes from previous report" section

Apply the Quality Gate at the end. Do not declare done if any item is unchecked.
</execution>

<output>
- Edit the relevant file(s) in cd-discovery/ using granular Edit calls (no whole-file rewrites).
- Append a per-file revision log entry to each file the agent touched (## Revision history at the bottom). Files not touched get no entry today.
- Save updated project findings to your agent memory — never store auth tokens, secret values, sensitive variable values, full alert payloads, or full PR content.
- Report which claims verified, which were contradicted (with user resolution), and which remain [USER-REPORTED] and why. Note which file(s) each claim updated.
</output>
```

When invoking the agent's bash steps for Tier 1 Octopus re-verification, pass the API key via the environment as documented above for the fresh-discovery path.

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
7. If --suggest was passed AND step 3 did not produce a suggestions.md (no legacy roadmap content), continue into a fresh suggestions generation against the migrated findings using TEMPLATE-suggestions.md and the suggestion voice.
</procedure>

<sub_playbook_weaving>
When weaving "Deployment Orchestrator" or "GitHub Repository Posture" content into findings.md dimensions, follow the dimension assignment from the legacy file's cross-stitch lines (e.g., "Build & CI: L1 → L2 because ..."). When a cross-stitch row is ambiguous (e.g., mentions multiple dimensions), put the evidence under the most-cited dimension and add "see also" notes referencing the other dimensions.
</sub_playbook_weaving>

<output>
- cd-discovery/summary.md, cd-discovery/findings.md, and (when applicable) cd-discovery/suggestions.md written.
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
- If GitHub discovery ran, mention which tier was used (Tier 1 / Tier 2) and which `gh` identity was authenticated.

**Update path:**
- Display a 3-5 line summary: which dimensions had level/confidence changes, how many claims verified vs. user-reported, whether GitHub / Octopus were re-scanned this pass, and the location of the new bottom-of-file revision entry.
- If any claims were `CONTRADICTED` and the user overrode the codebase/API, surface that explicitly so the user remembers the override exists in the report.
- Remind the user to `git diff cd-discovery/` before committing if they want to review the edits.

**Migration path (W5):**
- Display a 3-5 line summary: which files were written, whether `suggestions.md` was generated this pass (either from legacy roadmap content or from a `--suggest` continuation), and whether the legacy `CD-DISCOVERY.md` was removed via `git rm`.
- Remind the user to `git status` to see the staged deletion + new directory and `git diff --cached` to review the migration before committing.
