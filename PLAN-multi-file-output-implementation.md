# Multi-File CD Discovery Output — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `/cd-discovery` and the `continuous-delivery-strategist` agent from producing a single `CD-DISCOVERY.md` to producing a `cd-discovery/` directory of focused files (`summary.md`, `findings.md`, optional `suggestions.md`), with the assessment flag renamed `--suggest` and reframed as resource rather than mandate.

**Architecture:** The agent and skill source files stay single-file in structure; only their content changes. Output goes into a directory at the project root. GH and Octopus sub-playbooks emit "weave maps" — lists of evidence items tagged by target dimension — that the strategist integrates into `findings.md`. The launcher dispatches between 5 workflows based on what exists on disk.

**Tech Stack:** Markdown prompt files. No code changes. Verification via `grep`, manual structural review, and final end-to-end skill invocation.

**Spec reference:** `/Users/jwooten/dev/continuous-delivery-discovery/PLAN-multi-file-output.md`

**Commit policy:** The user's global instructions forbid auto-commits. Each task ends with a "commit suggestion" the executor surfaces to the user; the user decides when to actually commit.

**Working directory for all tasks:** `/Users/jwooten/dev/continuous-delivery-discovery/`

---

## Files Touched

**Created:**
- `skills/cd-discovery/TEMPLATE-summary.md`
- `skills/cd-discovery/TEMPLATE-findings.md`
- `skills/cd-discovery/TEMPLATE-suggestions.md`

**Modified:**
- `agents/continuous-delivery-strategist.md`
- `skills/cd-discovery/SKILL.md`
- `skills/cd-discovery/PLAYBOOK.md`
- `skills/cd-discovery/GH-DISCOVERY.md`
- `skills/cd-discovery/OCTOPUS-DISCOVERY.md`
- `skills/cd-discovery/UPDATE-PLAYBOOK.md`
- `README.md`
- `INSTALL.md`

**Deleted:**
- `skills/cd-discovery/TEMPLATE.md`

---

## Execution Order

1. **Task 1:** Create the three new template files
2. **Task 2:** Delete the old TEMPLATE.md
3. **Task 3:** Convert GH-DISCOVERY.md to weave-map output format
4. **Task 4:** Convert OCTOPUS-DISCOVERY.md to weave-map output format
5. **Task 5:** Update PLAYBOOK.md output instruction and sub-playbook integration note
6. **Task 6:** Update agent file (continuous-delivery-strategist.md)
7. **Task 7:** Update UPDATE-PLAYBOOK.md for multi-file flow
8. **Task 8:** Update SKILL.md launcher — argument parsing and existing-report detection
9. **Task 9:** Update SKILL.md launcher — spawn-the-agent prompts
10. **Task 10:** Add SKILL.md launcher — spawn-the-migrate-agent prompt
11. **Task 11:** Update README.md and INSTALL.md
12. **Task 12:** End-to-end smoke test against a fixture repo

---

## Task 1: Create three new template files

**Files:**
- Create: `skills/cd-discovery/TEMPLATE-summary.md`
- Create: `skills/cd-discovery/TEMPLATE-findings.md`
- Create: `skills/cd-discovery/TEMPLATE-suggestions.md`

**Reference:** Source content comes from `skills/cd-discovery/TEMPLATE.md` (the current single-file template). Each section of the existing template goes to exactly one of the three new files per the spec's Output Layout section.

- [ ] **Step 1: Read the current TEMPLATE.md**

Run: `cat skills/cd-discovery/TEMPLATE.md`

Confirm sections present: Executive Summary, Capability Matrix, Capability Levels Reference, Strengths to Protect, Detailed Findings, Deployment Orchestrator, GitHub Repository Posture, Anti-Patterns Detected, Recommended Next Steps.

- [ ] **Step 2: Create TEMPLATE-summary.md**

Write to `skills/cd-discovery/TEMPLATE-summary.md`:

```markdown
# CD Discovery — Summary

> Generated: {date} | Repository: {repo_name}
>
> See also: [findings.md](./findings.md){if suggestions exist: " | [suggestions.md](./suggestions.md)"}

## Executive Summary

{2-3 sentence overview: pipeline maturity, strongest dimension, weakest dimension, highest-leverage improvement}

## Capability Matrix

| Dimension | Level | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Build & CI | L{n} | {HIGH/MED/LOW} | {brief} |
| Testing | L{n} | {HIGH/MED/LOW} | {brief} |
| Deployment | L{n} | {HIGH/MED/LOW} | {brief} |
| Infrastructure as Code | L{n} | {HIGH/MED/LOW} | {brief} |
| Observability | L{n} | {HIGH/MED/LOW} | {brief} |
| Release Process | L{n} | {HIGH/MED/LOW} | {brief} |
| Security | L{n} | {HIGH/MED/LOW} | {brief} |

### Capability Levels Reference

| Level | Description |
|-------|-------------|
| L0 | Manual — infrequent, high-ceremony, high-risk |
| L1 | Automated builds — CI on commit, deployment still manual or gated |
| L2 | Automated delivery — CD to staging, prod is push-button |
| L3 | Continuous deployment — every green commit reaches prod via progressive rollout |
| L4 | Optimized — deployment is a non-event; experimentation and rapid rollback are routine |

## Strengths to Protect

> The load-bearing patterns the team is getting right. Naming these explicitly defends against well-intentioned "improvements" that silently regress them. **If this section is empty, the report is incomplete** — every pipeline has something working. Common entries: build-once-promote (artifact-centricity), immutable image tags, single-source artifact identity, deploy-step reads tag from build (no per-env retag), comprehensive test gating, automated rollback path.

| Strength | Evidence | What would silently regress it |
|---|---|---|
| {pattern name, e.g. "Build-once-promote via docker-tag.txt handoff"} | `{file:line}` | {specific change that regresses it — e.g., "parameterizing image tag per environment in the deploy step"} |

## Anti-Patterns Detected

| Anti-Pattern | Location | Impact |
|-------------|----------|--------|
| {pattern name} | `{file:line}` | {why this matters} |

## Recommended Next Steps

> Three highest-leverage quick wins. For the full suggestion set with tradeoffs and dependency mapping, see `suggestions.md` (generated by `/cd-discovery --suggest`).

1. {highest-leverage quick win}
2. {second priority item}
3. {third priority item}

---

## Revision history

> Append-only audit trail for this file. Each entry: `### YYYY-MM-DD — <event>` (e.g., `context refresh`, `migrated from CD-DISCOVERY.md`).

{revision entries appended here on update}
```

- [ ] **Step 3: Create TEMPLATE-findings.md**

Write to `skills/cd-discovery/TEMPLATE-findings.md`:

```markdown
# CD Discovery — Findings

> Generated: {date} | Repository: {repo_name}
>
> See also: [summary.md](./summary.md){if suggestions exist: " | [suggestions.md](./suggestions.md)"}

> Per-dimension deep dive. GitHub and Octopus evidence is woven into the relevant dimension sections — there are no dedicated "GitHub Repository Posture" or "Deployment Orchestrator" sections. Discovery source for sub-playbook items is noted inline with the evidence (e.g., `[evidence from gh CLI Tier 1, scanned 2026-05-26]`).

{repeat this block per dimension}

## {Dimension Name}

**Estimated Level:** L{n} — {level description}
**Confidence:** {HIGH/MED/LOW} — {why this confidence level}

**Artifacts Found:**
- `{path/to/file}` — {what it does} [{FOUND}]
- `{path/to/file:line}` — {specific finding} [{PARTIAL}]
- `{gh:repo-setting or octopus:project-step}` — {sub-playbook evidence woven in} [evidence from {source}, scanned {date}]

**Gaps Identified:**
- {gap description} [{MISSING}]

**User Context:**
- Q: {question asked}
- A: {user's answer}

{end repeat}

---

## Revision history

> Append-only audit trail for this file. Each entry: `### YYYY-MM-DD — <event>`.

{revision entries appended here on update}
```

- [ ] **Step 4: Create TEMPLATE-suggestions.md**

Write to `skills/cd-discovery/TEMPLATE-suggestions.md`:

```markdown
# CD Discovery — Suggestions

> Generated: {date} | Repository: {repo_name}
>
> See also: [summary.md](./summary.md) | [findings.md](./findings.md)

## How to read this file

This is a resource, not a plan. The suggestions below identify gaps surfaced in `findings.md` and describe what improving each would unlock alongside the cost. Engineers own sequencing decisions — team capacity, parallel work, risk appetite, and stakeholder priorities are not visible to the agent that wrote this file.

Each suggestion uses the same structure:

- **Gap** — what was found
- **What improving unlocks** — the concrete capability or risk reduction
- **Cost / disruption** — what the work requires and what it makes harder

Sequence guidance is expressed as a dependency map ("X unlocks Y"). A dependency edge is a constraint on order, not a schedule. Engineers may legitimately sequence differently based on context.

No time-duration estimates are included. The team owns sizing and scheduling.

## Suggestions

{repeat per suggestion}

### {n}. {Short title — the action, framed as a consideration}

- **Gap:** {what was observed in findings.md, with file:line reference where applicable}
- **What improving unlocks:** {concrete capability — e.g., "rollback in under 5 minutes instead of the current ~45", "blocks the 'works on my machine' class of incident", etc.}
- **Cost / disruption:** {specific cost — e.g., "introduces a new tool the team must learn", "requires changes to N existing pipelines", "adds 2-3 minutes to every CI run"}
- **Depends on:** {list of suggestion numbers this depends on, or "none"}
- **Unlocks:** {list of suggestion numbers this enables, or "none"}

{end repeat}

## Dependency map

```
{suggestion 1} → {suggestion 3} → {suggestion 5}
              ↘
{suggestion 2} → {suggestion 4}
```

> Edges indicate "X unlocks Y" — Y can be done without X, but with reduced effect or higher risk. The team owns final sequencing.

---

## Revision history

> Append-only audit trail for this file. Each entry: `### YYYY-MM-DD — <event>`.

{revision entries appended here on update}
```

- [ ] **Step 5: Verify all three files exist and parse as markdown**

Run:
```bash
ls -la skills/cd-discovery/TEMPLATE-*.md && \
  for f in skills/cd-discovery/TEMPLATE-summary.md \
           skills/cd-discovery/TEMPLATE-findings.md \
           skills/cd-discovery/TEMPLATE-suggestions.md; do
    echo "=== $f ===" && head -3 "$f"
  done
```

Expected: three files listed, each starts with a `# CD Discovery — ...` header.

- [ ] **Step 6: Commit suggestion**

Suggest to user: `git add skills/cd-discovery/TEMPLATE-summary.md skills/cd-discovery/TEMPLATE-findings.md skills/cd-discovery/TEMPLATE-suggestions.md && git commit -m "feat(cd-discovery): split TEMPLATE.md into per-output templates"`

Do not commit without user approval.

---

## Task 2: Delete the old TEMPLATE.md

**Files:**
- Delete: `skills/cd-discovery/TEMPLATE.md`

- [ ] **Step 1: Verify no remaining references to TEMPLATE.md before deletion**

Run: `grep -rnE 'TEMPLATE\.md|skills/cd-discovery/TEMPLATE\b' skills/ agents/ README.md INSTALL.md 2>/dev/null`

Expected: any matches must be the old TEMPLATE.md that we will be updating in subsequent tasks. Note them — they will be replaced when those tasks run. If matches reference TEMPLATE.md as a current-state file (e.g., in SKILL.md's `<required_reading>` block), that is expected and will be replaced in Task 8.

- [ ] **Step 2: Delete the file**

Run: `git rm skills/cd-discovery/TEMPLATE.md`

Expected output: `rm 'skills/cd-discovery/TEMPLATE.md'`

- [ ] **Step 3: Confirm deletion**

Run: `ls skills/cd-discovery/TEMPLATE.md 2>&1 | head -1`

Expected: `ls: skills/cd-discovery/TEMPLATE.md: No such file or directory`

- [ ] **Step 4: Commit suggestion**

Suggest to user: `git commit -m "chore(cd-discovery): remove old TEMPLATE.md (replaced by per-output templates)"`

Note: the `git rm` already staged the deletion; commit-only is enough. Do not commit without user approval.

---

## Task 3: Convert GH-DISCOVERY.md to weave-map output

**Files:**
- Modify: `skills/cd-discovery/GH-DISCOVERY.md`

**Context:** Currently this sub-playbook produces a self-contained "GitHub Repository Posture" section the strategist embeds in CD-DISCOVERY.md. In the new layout, it produces a "weave map" — a structured list of evidence items each tagged with the target dimension(s) in `findings.md` — that the strategist drops into the relevant dimension sections.

- [ ] **Step 1: Locate the current output instruction**

Run: `grep -nE '^##|^###' skills/cd-discovery/GH-DISCOVERY.md`

Identify the section that describes the output format. It will reference "Cross-stitch into capability matrix" or producing a "GitHub Repository Posture" section. Note its line range.

- [ ] **Step 2: Read the output section in detail**

Read `skills/cd-discovery/GH-DISCOVERY.md` lines covering the output format and the "Cross-stitch into capability matrix" section.

- [ ] **Step 3: Replace the output format section**

The output section must now describe the weave-map format. Edit the relevant lines to read:

```markdown
## Output: Weave Map

This sub-playbook does **not** produce a self-contained "GitHub Repository Posture" section. Instead, output a **weave map** — a structured list of evidence items, each tagged with the target dimension(s) in `findings.md`. The strategist will drop each item into the relevant dimension section.

### Weave-map format

Each line:

```
{Dimension}: {file or gh-resource reference} — {one-line finding} [evidence: gh CLI Tier {N}, scanned {YYYY-MM-DD}]
```

Where `{Dimension}` is one of: `Build & CI`, `Testing`, `Deployment`, `Infrastructure as Code`, `Observability`, `Release Process`, `Security`.

A finding that legitimately bears on multiple dimensions can appear on multiple lines, one per dimension, with the same evidence reference. Do not invent dimension assignments — only tag dimensions where the finding has clear bearing.

### Example weave map

```
Testing: .github/workflows/ci.yml:34 — no E2E job runs on the default-branch trigger [evidence: gh CLI Tier 1, scanned 2026-05-26]
Security: branch protection on `main` does not require code scanning to pass [evidence: gh CLI Tier 1, scanned 2026-05-26]
Build & CI: workflow execution reality — 12% failure rate over last 50 runs on `build-and-test` [evidence: gh CLI Tier 1, scanned 2026-05-26]
Release Process: 47 open Dependabot PRs, oldest 134 days [evidence: gh CLI Tier 1, scanned 2026-05-26]
```

### Severity framing rule (preserved from prior version)

When a finding describes missing branch protection or missing required status checks on a default branch, **do not** assign HIGH severity in isolation. First survey Observability, Testing, and Deployment Automation evidence. Severity emerges from the combination — trunk-based development legitimately commits directly to main, and what matters is whether bad commits get noticed and rolled back fast enough. Tag the evidence line with the severity reasoning so the reader can audit the call:

```
Build & CI: default branch `main` has no required status checks [evidence: gh CLI Tier 1; severity weighting: Observability=HIGH (Datadog deploy markers + 5min MTTR), Testing=MED, Deployment=L3 (canary + auto-rollback) — net severity LOW]
```

### Authentication preflight (preserved)

Before any gh CLI call, print the authenticated `gh` user and `viewerPermission` to the conversation so the reader can confirm identity. Do not echo auth tokens to the report, memory, or weave map.
```

If the file has structural sections you need to preserve (tier definitions, glob patterns, severity definitions), keep them unchanged. Only the **Output** section gets the weave-map treatment.

- [ ] **Step 4: Remove the old "Cross-stitch into capability matrix" template block**

If `GH-DISCOVERY.md` includes a template block for the old cross-stitch output (lines like `- Build & CI: {old level} → {new level} because {reason}`), remove that template block — it is superseded by the weave map format.

Search: `grep -n 'Cross-stitch into capability matrix' skills/cd-discovery/GH-DISCOVERY.md`

If found, remove the block.

- [ ] **Step 5: Verify the weave-map example renders correctly**

Run: `grep -nE 'Output: Weave Map|Weave-map format|evidence: gh CLI' skills/cd-discovery/GH-DISCOVERY.md`

Expected: three matches showing the new section headers and example body.

- [ ] **Step 6: Confirm no leftover references to the old "GitHub Repository Posture" section name in this file**

Run: `grep -n 'GitHub Repository Posture' skills/cd-discovery/GH-DISCOVERY.md`

Expected: no matches in GH-DISCOVERY.md. (The string may still exist in TEMPLATE files we already removed and in the agent/SKILL files we have not yet updated — those are handled in their respective tasks.)

- [ ] **Step 7: Commit suggestion**

Suggest: `git add skills/cd-discovery/GH-DISCOVERY.md && git commit -m "feat(cd-discovery): convert GH-DISCOVERY.md output to weave-map format"`

---

## Task 4: Convert OCTOPUS-DISCOVERY.md to weave-map output

**Files:**
- Modify: `skills/cd-discovery/OCTOPUS-DISCOVERY.md`

**Context:** Same conversion as Task 3 but for Octopus. The current sub-playbook produces a self-contained "Deployment Orchestrator" section; the new format is a weave map. Most Octopus findings tag the `Deployment` dimension; some tag `Release Process` (manual gates, lifecycle approvals) or `Observability` (notification gaps).

- [ ] **Step 1: Locate the current output instruction**

Run: `grep -nE '^##|^###' skills/cd-discovery/OCTOPUS-DISCOVERY.md`

Identify the section that describes the output format and any "Cross-stitch into capability matrix" template block.

- [ ] **Step 2: Read the output section in detail**

Read the relevant lines.

- [ ] **Step 3: Replace the output format section**

Edit the relevant lines to read:

```markdown
## Output: Weave Map

This sub-playbook does **not** produce a self-contained "Deployment Orchestrator" section. Instead, output a **weave map** — a structured list of evidence items, each tagged with the target dimension(s) in `findings.md`. The strategist will drop each item into the relevant dimension section.

### Weave-map format

Each line:

```
{Dimension}: {octopus-resource reference} — {one-line finding} [evidence: Octopus {Tier 1 API | Tier 2 CaC | Tier 3 Questionnaire}, scanned {YYYY-MM-DD}]
```

Where `{Dimension}` is one of: `Build & CI`, `Testing`, `Deployment`, `Infrastructure as Code`, `Observability`, `Release Process`, `Security`.

Most Octopus findings tag `Deployment`. Findings about manual lifecycle gates, approval phases, or release-coordination overhead tag `Release Process`. Findings about notification gaps or missing deploy markers tag `Observability`.

A finding that legitimately bears on multiple dimensions can appear on multiple lines, one per dimension. Do not invent dimension assignments.

### Example weave map

```
Deployment: project `web-api`/step 3 "Deploy Web App" — uses immutable build tag from package.json, no per-env retag [evidence: Octopus Tier 1 API, scanned 2026-05-26] [strength-to-protect]
Deployment: project `web-api` lifecycle `Standard` — Dev auto-promotes; Stage and Prod require manual approval [evidence: Octopus Tier 1 API, scanned 2026-05-26]
Release Process: project `web-api`/Prod phase has 2 required approvers; no SLA on approval latency [evidence: Octopus Tier 1 API, scanned 2026-05-26]
Observability: no Slack/Teams notification on prod deploy success or failure [evidence: Octopus Tier 1 API, scanned 2026-05-26]
```

### Strengths-to-Protect tagging

When a finding represents a load-bearing CD pattern the team is getting right (e.g., build-once-promote, immutable image tags, single-source artifact identity), append `[strength-to-protect]` to the line. The strategist will surface these in `summary.md` under Strengths to Protect rather than under the dimension's gap list.

### Artifact-centricity framing rule (preserved from prior version)

Build-once-promote-the-same-artifact is the load-bearing CD principle. When this sub-playbook finds it in place (single build per commit, immutable tag promoted unchanged through environments, deploy step reads the tag from the build rather than constructing it), emit the finding as a `Deployment` line with `[strength-to-protect]` tagged.

When the discovery finds the codebase rebuilds per environment, lets a mutable tag reach prod, or retags at deploy, emit a HIGH-severity `Deployment` line regardless of how green the rest of the pipeline looks.

Build-once-with-config-swap-at-deploy (identical bundle, runtime config swapped) is acceptable but emit the line with an asterisk note in the finding text so future readers understand the nuance.

### Authentication and sensitive-data rules (preserved)

- Tier 1 API: pass `OCTOPUS_API_KEY` via environment variable; never echo to terminal, weave map, memory, or any report file.
- Variable values, alert payloads, and sensitive identifiers must never appear in the weave map. Summary counts and named findings (e.g., "47 deployments to prod in last 90 days", "step 3 references variable `Database.ConnectionString`") are appropriate; raw values are not.
```

Keep all other sections of OCTOPUS-DISCOVERY.md unchanged (tier definitions, glob patterns, API endpoints, questionnaire flow).

- [ ] **Step 4: Remove the old "Cross-stitch into capability matrix" template block**

Search: `grep -n 'Cross-stitch into capability matrix' skills/cd-discovery/OCTOPUS-DISCOVERY.md`

If found, remove the block.

- [ ] **Step 5: Verify the weave-map example renders correctly**

Run: `grep -nE 'Output: Weave Map|evidence: Octopus|\[strength-to-protect\]' skills/cd-discovery/OCTOPUS-DISCOVERY.md`

Expected: matches showing the new section header, evidence-tag format, and strength-to-protect example.

- [ ] **Step 6: Confirm no leftover references to the old "Deployment Orchestrator" section name in this file**

Run: `grep -n 'Deployment Orchestrator' skills/cd-discovery/OCTOPUS-DISCOVERY.md`

Expected: no matches in OCTOPUS-DISCOVERY.md.

- [ ] **Step 7: Commit suggestion**

Suggest: `git add skills/cd-discovery/OCTOPUS-DISCOVERY.md && git commit -m "feat(cd-discovery): convert OCTOPUS-DISCOVERY.md output to weave-map format"`

---

## Task 5: Update PLAYBOOK.md output instruction and sub-playbook integration note

**Files:**
- Modify: `skills/cd-discovery/PLAYBOOK.md`

**Context:** PLAYBOOK.md is the main discovery methodology. Its output instruction must change from "produce CD-DISCOVERY.md" to "produce the cd-discovery/ directory of files." Also add a sub-playbook integration section that documents how weave-map items get woven into findings.md.

- [ ] **Step 1: Locate the current output instruction**

Run: `grep -nE 'CD-DISCOVERY\.md|produce.*\.md|write.*report' skills/cd-discovery/PLAYBOOK.md`

Identify the section(s) that describe what to write. There will likely be a Phase / Step describing the final write.

- [ ] **Step 2: Read the output section in detail**

Read the relevant lines (likely near the end of the file under a "Phase 3" or "Output" or similar header).

- [ ] **Step 3: Replace the output instruction**

Replace text that says "produce CD-DISCOVERY.md" (or equivalent) with:

```markdown
### Output: cd-discovery/ directory

Write three (or two) files under a `cd-discovery/` directory at the project root, following these templates:

| File | Template | When written |
|---|---|---|
| `cd-discovery/summary.md` | `~/.claude/skills/cd-discovery/TEMPLATE-summary.md` | Always |
| `cd-discovery/findings.md` | `~/.claude/skills/cd-discovery/TEMPLATE-findings.md` | Always |
| `cd-discovery/suggestions.md` | `~/.claude/skills/cd-discovery/TEMPLATE-suggestions.md` | Only when `--suggest` is in scope |

Each file is standalone-readable with a short date + repo header and its own bottom-of-file revision log. Cross-link `summary.md ↔ findings.md ↔ suggestions.md` with relative links per the templates.

### Sub-playbook integration (GH, Octopus)

When `GH-DISCOVERY.md` or `OCTOPUS-DISCOVERY.md` run, they emit a **weave map** — a structured list of evidence items tagged with the target dimension(s) in `findings.md`. Do **not** preserve a separate "GitHub Repository Posture" or "Deployment Orchestrator" section in the output. Instead:

1. Read the weave map output from the sub-playbook.
2. For each weave-map line, place the evidence in the matching dimension section of `findings.md` under "Artifacts Found" (or "Gaps Identified" if it's a missing-feature finding).
3. Preserve the evidence-source tag (`[evidence: gh CLI Tier 1, scanned 2026-05-26]`) inline with the item so readers can audit confidence.
4. Items tagged `[strength-to-protect]` go to `summary.md` under Strengths to Protect rather than into a dimension's gap list. Reference the source file and reason.

### Framing rule for branch protection (applies at dimension level)

When the GH weave map surfaces missing branch protection or missing required status checks on a default branch, do **not** classify it HIGH-severity in isolation. The finding sits in `findings.md` under the relevant dimension; weight severity by the team's overall feedback-loop quality (Observability, Testing, Deployment Automation). Document the reasoning inline with the evidence so the reader can audit the call.

### Framing rule for artifact-centricity

Build-once-promote-the-same-artifact is the load-bearing CD principle. When the Octopus weave map (or `PLAYBOOK.md` §1.13 if you find it directly) confirms it, the finding belongs in `summary.md` under Strengths to Protect with file:line / step-reference evidence — not buried as an absent gap in `findings.md`. Tell the reader what would silently regress it (per-env tag parameterization, retag-at-deploy, separate per-env build jobs). When the codebase rebuilds per environment, lets a mutable tag reach prod, or retags at deploy, surface it as a HIGH-severity Deployment finding in `findings.md` regardless of how green the rest of the pipeline looks.
```

If the previous PLAYBOOK.md included a numbered Phase like "Phase 3: Write CD-DISCOVERY.md", rename it to "Phase 3: Write the cd-discovery/ directory" and replace its body with the content above.

- [ ] **Step 4: Update any in-text references to "CD-DISCOVERY.md" within PLAYBOOK.md**

Run: `grep -n 'CD-DISCOVERY\.md' skills/cd-discovery/PLAYBOOK.md`

For each remaining match, decide:
- If it describes the legacy file in a migration or backward-compat context → keep as `CD-DISCOVERY.md` literal.
- If it describes the current output → replace with the appropriate file (`cd-discovery/summary.md`, `cd-discovery/findings.md`, or `cd-discovery/suggestions.md`) or `cd-discovery/` as a directory.

Replace each one inline.

- [ ] **Step 5: Verify the new output section is in place**

Run:
```bash
grep -nE 'Output: cd-discovery/ directory|Sub-playbook integration|TEMPLATE-summary\.md|TEMPLATE-findings\.md|TEMPLATE-suggestions\.md' skills/cd-discovery/PLAYBOOK.md
```

Expected: matches showing the new section header and references to the three templates.

- [ ] **Step 6: Confirm no orphan "CD-DISCOVERY.md" references remain except intentional legacy mentions**

Run: `grep -nC2 'CD-DISCOVERY\.md' skills/cd-discovery/PLAYBOOK.md`

For each match, the surrounding context should make clear it is talking about the legacy file (e.g., migration context, "the file previously known as CD-DISCOVERY.md"). If any match is unintentional, fix it.

- [ ] **Step 7: Commit suggestion**

Suggest: `git add skills/cd-discovery/PLAYBOOK.md && git commit -m "feat(cd-discovery): update PLAYBOOK output to cd-discovery/ directory with weave-map integration"`

---

## Task 6: Update agent file (continuous-delivery-strategist.md)

**Files:**
- Modify: `agents/continuous-delivery-strategist.md`

**Context:** The strategist agent has Discovery Mode bullets that reference the old single-file output and `--assess` flag. It also has a "Sequence Improvements" section that needs to soften from roadmap voice to suggestion voice without losing the no-time-estimates rule.

- [ ] **Step 1: Read the current §6 Discovery Mode block**

Read the discovery mode section of `agents/continuous-delivery-strategist.md`. Locate the numbered bullets (10 of them in the current version) and identify bullets 8, 9, and 10 specifically.

- [ ] **Step 2: Update §6 bullet 8 (output target)**

Find: `Read the template file and produce \`CD-DISCOVERY.md\` in the project root.`

Replace with:

```markdown
Read the template files and produce the `cd-discovery/` output directory. Always write `cd-discovery/summary.md` (from `TEMPLATE-summary.md`) and `cd-discovery/findings.md` (from `TEMPLATE-findings.md`). When `--suggest` is in scope, also write `cd-discovery/suggestions.md` (from `TEMPLATE-suggestions.md`). Each file gets a short date + repo header and an empty Revision history section at the bottom.
```

- [ ] **Step 3: Update §6 bullet 9 (assessment continuation)**

Find: `If "Continue to assessment" mode is set, proceed directly into a full assessment with a phased improvement roadmap after writing the discovery report.`

Replace with:

```markdown
If the launcher signals `--suggest` is in scope, generate `cd-discovery/suggestions.md` after writing summary and findings. Use the suggestion voice defined in §4: lead with tradeoffs (gap → what improving unlocks → cost/disruption), not directives. Express sequence as a dependency map ("X unlocks Y"), not a plan. Engineers own sequencing decisions — your job is to identify gaps and their tradeoffs, not to prescribe a calendar. No time-duration estimates. Do not use the word "roadmap."
```

- [ ] **Step 4: Update §6 bullet 10 (memory protocol) for the new output location**

Find the bullet that describes saving findings to agent memory.

Replace any reference to "where CD-DISCOVERY.md was written" with "where the cd-discovery/ directory was written." The substance of the rule (no auth tokens, no sensitive variable values, no full alert payloads, no full PR content) is preserved.

- [ ] **Step 5: Update §4 Sequence Improvements**

Read the current §4 block. It opens with "When building roadmaps:" and lists rules about leverage, phases, dependencies, time estimates, etc.

Edit the opening line: `When building roadmaps:` → `When suggesting improvements (writing to suggestions.md or advising verbally):`

Preserve every existing rule, with these specific edits:

- The bullet about "phased work" / "phases must leave the system in a better, stable state" — change to: `Suggestions that are sequenced should still each be runnable to a stable, better state on their own. The team owns whether to actually sequence them that way.`
- The no-time-estimates bullet — preserve verbatim. Do not soften the no-estimates rule.
- Any bullet mentioning "the roadmap" — rewrite to "the suggestion set" or "the dependency map" depending on context.

Add this as the **last** bullet of §4:

```markdown
- **Frame as resource, not prescription.** Suggestions live alongside the team's own context (capacity, parallel work, risk appetite, stakeholder priorities) which the agent cannot see. Lead with tradeoffs ("Consider X because Y; the tradeoff is Z"), not directives ("Do X"). The team forms its own opinion and decides. "Roadmap" language is reserved for documents the team actually commits to — the suggestions.md file is not that.
```

- [ ] **Step 6: Update Quality Checks §6**

Find Quality Checks bullet 6 (about Strengths to Protect being named in "the report").

Replace `the report` with `the discovery files (specifically summary.md under Strengths to Protect)`.

- [ ] **Step 7: Verify all updates are in place**

Run:
```bash
grep -nE 'cd-discovery/|--suggest|suggestion voice|TEMPLATE-summary' agents/continuous-delivery-strategist.md
```

Expected: matches confirming references to the new directory, the `--suggest` flag, the suggestion voice principle, and the new templates.

- [ ] **Step 8: Confirm no remaining "--assess" or "produce CD-DISCOVERY.md" references**

Run:
```bash
grep -nE -- '--assess|produce.*CD-DISCOVERY\.md|build.*roadmap' agents/continuous-delivery-strategist.md
```

Expected: no matches. (Any historical references would have come from this agent's prior content.)

- [ ] **Step 9: Commit suggestion**

Suggest: `git add agents/continuous-delivery-strategist.md && git commit -m "feat(strategist): update discovery mode and sequence improvements for multi-file output and suggestion voice"`

---

## Task 7: Update UPDATE-PLAYBOOK.md for multi-file flow

**Files:**
- Modify: `skills/cd-discovery/UPDATE-PLAYBOOK.md`

**Context:** The update playbook currently operates on a single CD-DISCOVERY.md. It needs to operate on the `cd-discovery/` directory, tag claims with target file(s), edit per-file, and append per-file revision logs.

- [ ] **Step 1: Locate the current phase structure**

Run: `grep -nE '^##|^### Phase' skills/cd-discovery/UPDATE-PLAYBOOK.md`

Identify Phases 1, 3, 5, 6 (the ones that change) and the Quality Gate section.

- [ ] **Step 2: Update Phase 1 (Ingest)**

Read the current Phase 1 body. It will say something like "Read CD-DISCOVERY.md into a working memory index."

Replace with:

```markdown
### Phase 1: Ingest current report into a working memory index

Read all markdown files in `cd-discovery/`:

- `cd-discovery/summary.md` — always present
- `cd-discovery/findings.md` — always present
- `cd-discovery/suggestions.md` — present only when `--suggest` was previously run

For each file, build a working memory index that captures:

- Dimensions and their current levels + confidence (from summary.md matrix and findings.md sections)
- Strengths to Protect (from summary.md)
- Anti-patterns (from summary.md)
- Per-dimension artifacts and gaps (from findings.md)
- Suggestion items and their dependency edges (from suggestions.md if present)
- Each file's existing Revision history (so update entries don't duplicate past events)

If `cd-discovery/` does not exist, abort with the message: "No cd-discovery/ directory found — run `/cd-discovery` first to generate the baseline, then re-run with `--update`."
```

- [ ] **Step 3: Update Phase 3 (Decompose into atomic claims)**

Read the current Phase 3 body.

Replace with:

```markdown
### Phase 3: Decompose into atomic claims; tag each with target file(s)

Convert the user's context into a list of atomic claims. Each claim is a single, verifiable assertion (e.g., "Testing is now L2 because we added E2E coverage in CI", not "we improved testing").

For each claim, tag the file(s) it touches:

- `[summary]` — claims that change the capability matrix, Strengths to Protect, anti-patterns, or next steps
- `[findings]` — claims that add or change evidence in a per-dimension section
- `[suggestions]` — claims that add, remove, or supersede a suggestion (only valid when suggestions.md exists)
- Multi-tag — claims that change a dimension's level touch both `[summary]` (matrix row) and `[findings]` (the dimension section). The decomposition step must flag these as multi-file claims so they do not get half-applied.

Show the tagged claim list to the user. The user confirms or amends before any verification or edit runs. If the user removes a claim or adds a new one, re-tag and re-confirm.

#### Multi-file claim propagation rule

When a tagged claim touches multiple files, every file in the tag must be edited in the same pass. The Quality Gate (below) fails if a multi-file claim landed in some but not all of its tagged files.
```

- [ ] **Step 4: Update Phase 5 (Edit in place)**

Read the current Phase 5 body.

Replace with:

```markdown
### Phase 5: Edit in place using granular Edit calls

For each confirmed claim, use the `Edit` tool to make targeted changes to the file(s) listed in the claim's tag. Rules:

- **No whole-file rewrites.** Each `Edit` call replaces a single coherent block (a matrix row, a finding entry, a suggestion item, a section header — never a whole file).
- **Touch only the files the claims affect.** Files not mentioned in any claim's tag must not be edited.
- **Cross-file claims edit each file in turn within the same pass.** Do not commit between the two halves of a multi-file claim; if the executor is committing per-pass, the commit covers all files the claim touched.

If a claim was tagged `CONTRADICTED` in Phase 4 verification, do not apply the user-reported version unless the user explicitly overrides after seeing the contradiction.
```

- [ ] **Step 5: Update Phase 6 (Revision entry)**

Read the current Phase 6 body.

Replace with:

```markdown
### Phase 6: Append per-file revision log entries

For each file the agent touched in Phase 5, append one entry to that file's bottom `## Revision history` section. Files the agent did not touch get no entry today.

Each entry uses this format:

```
### YYYY-MM-DD — context refresh
- {dimension or section}: {change} ({verification status})
- {dimension or section}: {change} ({verification status})
```

Verification status is one of: `verified` (re-confirmed against the codebase / live API), `user-reported` (could not be verified against any source), or `user-override` (codebase / API contradicted the claim but the user overrode after seeing the contradiction).

Examples:

```
### 2026-05-26 — context refresh
- Testing: L1 → L2 (verified via .github/workflows/ci.yml)
- Anti-patterns: removed "manual prod deploy" (user-reported)
```

```
### 2026-05-26 — context refresh
- Suggestion #2: superseded by new approach (user-override; codebase still shows old pattern)
- Dependency map: edge from #2 → #5 removed (user-reported)
```

No global changelog file is written. Each file owns its own revision log.
```

- [ ] **Step 6: Update the Quality Gate**

Locate the Quality Gate section. Update its checks to apply per file:

Replace the checklist with:

```markdown
### Quality Gate

Apply this checklist per file the agent touched. If any item fails, do not declare done.

- [ ] Each claim tagged for this file produced a corresponding edit in this file.
- [ ] Multi-file claims propagated correctly — if this file got a level change, the other tagged file also got the corresponding edit.
- [ ] No whole-file rewrites occurred — every change is a granular Edit.
- [ ] A new entry was appended to this file's `## Revision history` if any edits landed.
- [ ] No auth tokens, raw secret values, full alert payloads, or full PR bodies were written to this file or to agent memory.
- [ ] Strengths to Protect (summary.md) and Anti-patterns Detected (summary.md) were re-checked if any dimension's level changed.

A passed Quality Gate per touched file is required before Phase 6 entries are considered finalized.
```

- [ ] **Step 7: Update any remaining "CD-DISCOVERY.md" references in this file**

Run: `grep -n 'CD-DISCOVERY\.md' skills/cd-discovery/UPDATE-PLAYBOOK.md`

For each remaining match, decide if it should be `cd-discovery/`, a specific file under it, or kept as a legacy reference (rare in this playbook). Replace each one.

- [ ] **Step 8: Verify all phases reflect the new flow**

Run:
```bash
grep -nE '^### Phase|cd-discovery/|\[summary\]|\[findings\]|\[suggestions\]|multi-file claim' skills/cd-discovery/UPDATE-PLAYBOOK.md
```

Expected: matches showing each of the phase headers, the cd-discovery/ directory references, the tag conventions, and the multi-file claim rule.

- [ ] **Step 9: Commit suggestion**

Suggest: `git add skills/cd-discovery/UPDATE-PLAYBOOK.md && git commit -m "feat(cd-discovery): update UPDATE-PLAYBOOK for multi-file directory layout with per-file revision logs"`

---

## Task 8: Update SKILL.md launcher — argument parsing and existing-report detection

**Files:**
- Modify: `skills/cd-discovery/SKILL.md`

**Context:** The launcher needs to (a) rename `--assess` to `--suggest`, (b) detect `cd-discovery/` directory presence, (c) handle the legacy `CD-DISCOVERY.md` migration path, (d) implement incremental `--suggest` against existing findings, and (e) handle the dispatch precedence when both legacy file and new directory exist.

This task handles parts (a)–(c) and (e). Task 9 updates the spawn-the-agent prompts. Task 10 adds the spawn-the-migrate-agent prompt.

- [ ] **Step 1: Read the current "Parse Arguments" section**

Run: `grep -nE '^##|^###' skills/cd-discovery/SKILL.md` to locate sections.

Read the "## Parse Arguments" section.

- [ ] **Step 2: Update the argument-hint frontmatter and "Parse Arguments" body**

In the frontmatter at the top of the file, find:

```
argument-hint: "[--skip-interview] [--assess] [--update [<context-or-path>]] [--skip-github] ..."
```

Replace `[--assess]` with `[--suggest]`.

In the "## Parse Arguments" section body, find the bullet that defines `--assess`:

```
- `--assess` — after writing CD-DISCOVERY.md, continue into a full assessment with improvement roadmap
```

Replace with:

```
- `--suggest` — after writing `cd-discovery/summary.md` and `findings.md`, also write `cd-discovery/suggestions.md` with the suggestion-voice framing (resource, not prescription). If `summary.md` and `findings.md` already exist (no `suggestions.md` yet), generate `suggestions.md` only against the existing findings without re-scanning.
```

Also update any other bullet that says "produce CD-DISCOVERY.md" → "produce the cd-discovery/ directory."

- [ ] **Step 3: Replace the "## Check for Existing Report" section**

The current section detects `CD-DISCOVERY.md` at the project root and offers overwrite / update / cancel.

Replace the entire section with:

```markdown
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
```

- [ ] **Step 4: Verify the new section renders**

Run:
```bash
grep -nE '## Check for Existing Output|Dispatch precedence|W4-scoped prompt|W5 legacy-detection' skills/cd-discovery/SKILL.md
```

Expected: four matches confirming the new section structure.

- [ ] **Step 5: Confirm `--assess` no longer appears in SKILL.md**

Run: `grep -n -- '--assess' skills/cd-discovery/SKILL.md`

Expected: no matches.

- [ ] **Step 6: Commit suggestion**

Suggest: `git add skills/cd-discovery/SKILL.md && git commit -m "feat(cd-discovery): rename --assess to --suggest and dispatch on cd-discovery/ directory state"`

---

## Task 9: Update SKILL.md launcher — spawn-the-agent and spawn-the-update-agent prompts

**Files:**
- Modify: `skills/cd-discovery/SKILL.md`

**Context:** The spawn prompts currently reference CD-DISCOVERY.md, the `--assess` flag, the "Deployment Orchestrator section," and the "GitHub Repository Posture section." Each spawn block needs to be updated to reference the new layout and the weave-map integration.

- [ ] **Step 1: Read the current "## Spawn the Agent" block**

Read the section from `## Spawn the Agent` through the end of its agent prompt template.

- [ ] **Step 2: Update the `<required_reading>` block**

Find:

```
<required_reading>
Read these files before starting:
1. ~/.claude/skills/cd-discovery/PLAYBOOK.md — Discovery methodology to execute
2. ~/.claude/skills/cd-discovery/TEMPLATE.md — Output template for CD-DISCOVERY.md
3. ~/.claude/skills/cd-discovery/OCTOPUS-DISCOVERY.md — ...
4. ~/.claude/skills/cd-discovery/GH-DISCOVERY.md — ...
</required_reading>
```

Replace with:

```
<required_reading>
Read these files before starting:
1. ~/.claude/skills/cd-discovery/PLAYBOOK.md — Discovery methodology to execute
2. ~/.claude/skills/cd-discovery/TEMPLATE-summary.md — Template for cd-discovery/summary.md
3. ~/.claude/skills/cd-discovery/TEMPLATE-findings.md — Template for cd-discovery/findings.md
4. ~/.claude/skills/cd-discovery/TEMPLATE-suggestions.md — Template for cd-discovery/suggestions.md (only required when --suggest is in scope)
5. ~/.claude/skills/cd-discovery/OCTOPUS-DISCOVERY.md — Octopus Deploy sub-playbook (only when Octopus is in scope)
6. ~/.claude/skills/cd-discovery/GH-DISCOVERY.md — GitHub sub-playbook (only when the repo is on GitHub)
</required_reading>
```

- [ ] **Step 3: Update the `<objective>` block**

Find the current `<objective>` block. It will reference writing CD-DISCOVERY.md.

Replace its body with:

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
```

- [ ] **Step 4: Update the `<output>` block**

Find the current `<output>` block in the Spawn the Agent prompt.

Replace with:

```
<output>
- Write cd-discovery/summary.md and cd-discovery/findings.md.
- If --suggest is in scope, write cd-discovery/suggestions.md.
- Weave GH and Octopus weave-map items into the relevant findings.md dimensions (and into summary.md's Strengths to Protect if tagged [strength-to-protect]). Do not create dedicated "GitHub Repository Posture" or "Deployment Orchestrator" sections.
- Save project findings to your agent memory — record the cd-discovery/ directory path, not CD-DISCOVERY.md. Never store auth tokens (Octopus API key, gh token), secret values, sensitive variable values, full alert payloads, or full PR content.
</output>
```

- [ ] **Step 5: Update any sub-playbook context blocks**

Find the `<octopus_inputs>` and `<github_inputs>` blocks. Update any internal language that says "produce the Deployment Orchestrator section" or "produce the GitHub Repository Posture section" to "produce a weave map" and reference the new sub-playbook output format from Tasks 3 and 4.

Find the `<framing_rule>` block. Update any reference to "the cross-stitch lines" to "the weave-map evidence-tag reasoning."

- [ ] **Step 6: Read the current "## Spawn the Update Agent" block**

Read this section in full.

- [ ] **Step 7: Update Spawn the Update Agent — `<required_reading>` and `<objective>`**

In `<required_reading>`:

Find:
```
1. The `CD-DISCOVERY.md` at the project root — current report
```

Replace with:
```
1. All files under cd-discovery/ at the project root — current reports (summary.md, findings.md, and suggestions.md if present)
```

In `<objective>`:

Find any reference to "Update the existing CD-DISCOVERY.md."

Replace with:
```
Update the existing cd-discovery/ directory by folding in additional context the user has supplied. Each claim must be tagged with the file(s) it touches ([summary], [findings], [suggestions], or multi-tag). Multi-file claims (e.g., a dimension level change) must edit both the matrix row in summary.md AND the per-dimension section in findings.md in the same pass. Verify every claim that can be verified against the codebase or live APIs (gh CLI, Octopus REST API); tag the rest [USER-REPORTED] and lower confidence accordingly. Edit each file in place using granular Edit calls — preserve the audit trail by reframing prior findings rather than deleting them. Append a per-file revision log entry to each file the agent touched.
```

- [ ] **Step 8: Update Spawn the Update Agent — `<output>` block**

Find the current `<output>` block.

Replace with:

```
<output>
- Edit the relevant file(s) in cd-discovery/ using granular Edit calls (no whole-file rewrites).
- Append a per-file revision log entry to each file the agent touched (## Revision history at the bottom). Files not touched get no entry today.
- Save updated project findings to your agent memory — never store auth tokens, secret values, sensitive variable values, full alert payloads, or full PR content.
- Report which claims verified, which were contradicted (with user resolution), and which remain [USER-REPORTED] and why. Note which file(s) each claim updated.
</output>
```

- [ ] **Step 9: Verify both spawn blocks render correctly**

Run:
```bash
grep -nE 'TEMPLATE-summary|TEMPLATE-findings|TEMPLATE-suggestions|weave map|weave-map|cd-discovery/summary\.md|cd-discovery/findings\.md|cd-discovery/suggestions\.md' skills/cd-discovery/SKILL.md
```

Expected: multiple matches across both spawn blocks confirming the new references.

- [ ] **Step 10: Confirm no leftover "Deployment Orchestrator section" or "GitHub Repository Posture section" mentions**

Run: `grep -nE '(Deployment Orchestrator|GitHub Repository Posture) section' skills/cd-discovery/SKILL.md`

Expected: no matches.

- [ ] **Step 11: Commit suggestion**

Suggest: `git add skills/cd-discovery/SKILL.md && git commit -m "feat(cd-discovery): update spawn prompts for cd-discovery/ output and weave-map integration"`

---

## Task 10: Add SKILL.md launcher — spawn-the-migrate-agent prompt

**Files:**
- Modify: `skills/cd-discovery/SKILL.md`

**Context:** Workflow W5 (legacy migration) needs its own spawn block. Same `subagent_type: continuous-delivery-strategist`, different `<objective>`.

- [ ] **Step 1: Locate where to insert the new spawn block**

Locate "## Spawn the Update Agent" — the new spawn block goes immediately after it.

- [ ] **Step 2: Add the Spawn the Migrate Agent section**

Insert the following section after the Spawn the Update Agent block and before "## Report Completion" (or wherever the final reporting section lives):

````markdown
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
````

- [ ] **Step 3: Update "## Report Completion" to handle the W5 path**

Locate the Report Completion section. Add a paragraph for the migration outcome:

```markdown
**Migration path (W5):**
- Display a 3-5 line summary: which files were written, whether `suggestions.md` was generated this pass (either from legacy roadmap content or from a `--suggest` continuation), and whether the legacy `CD-DISCOVERY.md` was removed via `git rm`.
- Remind the user to `git status` to see the staged deletion + new directory and `git diff --cached` to review the migration before committing.
```

- [ ] **Step 4: Verify the migrate block is in place**

Run:
```bash
grep -nE '## Spawn the Migrate Agent|Migration path \(W5\)' skills/cd-discovery/SKILL.md
```

Expected: both headers present.

- [ ] **Step 5: Verify the launcher wires W5 to the migrate block**

Run:
```bash
grep -nE 'W5|Migrate|legacy-detection' skills/cd-discovery/SKILL.md
```

Expected: W5 appears in the dispatch table (from Task 8) AND in the new Migrate Agent section AND in the Report Completion section.

- [ ] **Step 6: Commit suggestion**

Suggest: `git add skills/cd-discovery/SKILL.md && git commit -m "feat(cd-discovery): add Spawn the Migrate Agent path for legacy CD-DISCOVERY.md migration"`

---

## Task 11: Update README.md and INSTALL.md

**Files:**
- Modify: `README.md`
- Modify: `README.md` reference table for the `--assess` and output filename mentions
- Modify: `INSTALL.md`

**Context:** Both files reference `--assess` and `CD-DISCOVERY.md` in user-facing documentation. They need to reflect the new flag name, output layout, and suggestion voice.

- [ ] **Step 1: Find all references in user-facing docs**

Run: `grep -nE -- '--assess|CD-DISCOVERY\.md|phased improvement roadmap|improvement roadmap' README.md INSTALL.md`

Note each match.

- [ ] **Step 2: Update README.md command table**

Find this row (or equivalent):

```
| `/cd-discovery --assess` | Discovery + a phased improvement roadmap |
```

Replace with:

```
| `/cd-discovery --suggest` | Discovery + suggestions.md (gaps + tradeoffs + dependency map; a resource, not a plan) |
```

- [ ] **Step 3: Update README.md prose describing `--assess`**

Find prose mentioning "With `--assess`, the agent adds a phased improvement roadmap" (or similar).

Replace with:

```markdown
With `--suggest`, the agent writes a third file (`cd-discovery/suggestions.md`) alongside `summary.md` and `findings.md`. Each suggestion identifies a gap from the findings, names what improving it would unlock, and states the cost. Sequence guidance is expressed as a dependency map — the team owns sequencing. No time-duration estimates. The file is a resource, not a plan: engineers form their own opinion and decide.

If you run `/cd-discovery` first and decide later that you want suggestions, run `/cd-discovery --suggest` against the existing directory — the agent reads your existing findings and writes only `suggestions.md` (no re-scan).
```

- [ ] **Step 4: Update README.md output description**

Find any prose that says the skill produces `CD-DISCOVERY.md`.

Replace with description of the directory layout:

```markdown
The skill produces a `cd-discovery/` directory at the project root:

- `cd-discovery/summary.md` — executive summary, capability matrix (L0–L4 across seven dimensions), Strengths to Protect, anti-patterns, top three quick wins.
- `cd-discovery/findings.md` — per-dimension deep dive. GitHub and Octopus evidence (when those sub-playbooks run) weaves into the relevant dimensions inline — there are no dedicated GitHub or Octopus sections.
- `cd-discovery/suggestions.md` — only when `--suggest` has run. See description above.

Each file is standalone-readable and maintains its own bottom-of-file revision log when you run `/cd-discovery --update`.
```

- [ ] **Step 5: Update INSTALL.md flag list**

Find:

```
- `/cd-discovery --assess` — discovery + improvement roadmap
```

Replace with:

```
- `/cd-discovery --suggest` — discovery + suggestions.md (gaps, tradeoffs, dependency map)
```

- [ ] **Step 6: Add a "Migration from CD-DISCOVERY.md" note in README.md**

After the output description section, add:

```markdown
### Migrating from the previous single-file output

If you ran an earlier version of this skill that wrote `CD-DISCOVERY.md` at the project root, the next `/cd-discovery` run will detect the legacy file and offer three options: **Migrate** (split it into the new layout, preserving content and revision history; removes the legacy file as part of the commit), **Fresh** (discard and run a new discovery), or **Cancel**. Choose Migrate to keep your audit trail intact.
```

- [ ] **Step 7: Verify all user-facing references are updated**

Run: `grep -nE -- '--assess|phased improvement roadmap|improvement roadmap' README.md INSTALL.md`

Expected: no matches.

Run: `grep -nE 'CD-DISCOVERY\.md' README.md INSTALL.md`

Expected: any remaining matches must be in the new "Migrating from..." section as legacy references — confirm contextually.

- [ ] **Step 8: Commit suggestion**

Suggest: `git add README.md INSTALL.md && git commit -m "docs: update README and INSTALL for cd-discovery/ multi-file output and --suggest flag"`

---

## Task 12: End-to-end smoke test against a fixture repo

**Files:**
- No code changes — this task validates the integrated behavior.

**Context:** All file edits are done. The skill needs end-to-end validation. The executor must run `/cd-discovery` against a representative repo and confirm the three-file output appears as designed.

The user owns this task — the executor cannot run the user's slash command from inside a planning session. The executor's responsibility is to surface the test plan and the expected outcomes, so the user can run them and confirm.

- [ ] **Step 1: Surface the smoke test plan to the user**

Present this test matrix:

| Scenario | Command | Expected outcome |
|---|---|---|
| Fresh run on a repo with no existing output | `/cd-discovery` | `cd-discovery/summary.md` + `cd-discovery/findings.md` written; no `suggestions.md`. |
| Fresh + suggest in one shot | `/cd-discovery --suggest` (on a repo with no existing output) | All three files written. `suggestions.md` uses suggestion voice (no "roadmap" language; no time estimates). |
| Incremental suggest | `/cd-discovery --suggest` (on a repo where `cd-discovery/summary.md` and `findings.md` exist, no `suggestions.md`) | Only `suggestions.md` is written; no re-scan; matrix in `summary.md` is unchanged. |
| W4 prompt | `/cd-discovery` (on a repo where `cd-discovery/` already exists) | Existing-report prompt appears with three options (Overwrite / Update / Cancel). |
| W4-scoped prompt | `/cd-discovery --suggest` (on a repo where all three files already exist) | Existing-report prompt scoped to `suggestions.md` only. |
| Legacy migration | `/cd-discovery` (on a repo with `CD-DISCOVERY.md` and no `cd-discovery/`) | W5 prompt offers Migrate / Fresh / Cancel. Migrate splits the file into the new layout, removes the legacy file via `git rm`, and preserves the revision history. |
| Dispatch precedence | `/cd-discovery` (on a repo with BOTH `CD-DISCOVERY.md` AND `cd-discovery/`) | Launcher prints the stale-legacy warning and routes to W4 (cd-discovery/ takes precedence). |
| Update flow | `/cd-discovery --update "Testing is now L2 because we added E2E coverage in CI"` | Claims-confirmation prompt shows the claim tagged `[summary][findings]` (multi-file claim). After confirmation, both files are edited and both get revision log entries. |
| Suggestion voice spot check | Open `cd-discovery/suggestions.md` after any run that wrote it | File does not contain the word "roadmap" or any time-duration estimate. Each suggestion has gap / unlock / cost. A dependency map is present. |

- [ ] **Step 2: Recommend a fixture repo**

Ask the user to choose a small, representative repo for the smoke test. The cd-discovery repo itself works (it has its own CI workflows). Or any other repo that has CI configuration, deployment scripts, or both.

- [ ] **Step 3: For each scenario, record the actual outcome**

The user runs each scenario in order. For each, capture:
- Did the dispatch route to the expected workflow?
- Were the expected files written / not written?
- Did revision logs appear in the right files?
- Did the suggestion voice hold up (no "roadmap" mentions, no time estimates)?

Document any discrepancies and surface them as bugs to fix in a follow-up task. Do not declare the implementation done until every scenario passes.

- [ ] **Step 4: Commit suggestion if smoke tests passed**

If all scenarios passed: suggest `git tag` or a documentation update noting the multi-file output behavior is live. The user decides whether to tag.

If any scenario failed: create follow-up tasks for the specific failures. Do not mark this task complete.

---

## Self-Review

After writing the plan, I reviewed it against the spec and found two items to add:

1. **Spec coverage:** The spec's "Migration" section says "Continue into a fresh `suggestions.md` generation against the migrated findings" when `--suggest` was passed and the legacy file had no roadmap content. Task 10 step 2 handles this in the `<procedure>` block. ✓

2. **Type consistency:** I checked that flag names, file names, dimension names, and tag conventions (`[summary]`, `[findings]`, `[suggestions]`) are consistent across all tasks. The dispatch table in Task 8 uses `HAS_NEW_DIR` / `HAS_LEGACY_FILE` / `HAS_SUGGESTIONS` as state variables; these are used only in that table for clarity and not referenced elsewhere — that's fine since the table is self-contained. ✓

3. **Spec gap fixed:** The spec mentions a `HAS_NEW_DIR + --update + no HAS_LEGACY_FILE` case but the spec's W5 description didn't address what happens if a user runs `--update` against a legacy-only state. I added an abort message in the Task 8 dispatch table covering this case. The user can decide if that abort matches their intent during execution.

---

## Open Items the Executor May Need to Decide

These items the spec deliberately left for implementation:

- **Dimension ordering in matrix** — preserved from current TEMPLATE.md unless reordering is explicitly requested.
- **Discovery-source attestation block** — Task 1's TEMPLATE-summary.md does not include an attestation block at the top. If the user wants one (e.g., "scanned via codebase + gh Tier 1 + Octopus questionnaire"), add it during Task 1 by inserting after the header line.
- **Suggestion-voice preamble wording** — Task 1's TEMPLATE-suggestions.md has a "How to read this file" preamble. The exact wording is the executor's call; the spec only requires the framing principles.
- **Diff preview for migration** — Task 10's spawn-the-migrate-agent block does not surface a diff preview before committing. If the user wants one, add a step to Task 10 between procedure steps 5 and 6 that prints a preview and waits for user confirmation.
