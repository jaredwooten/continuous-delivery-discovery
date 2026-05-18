# CI/CD Discovery — Update Sub-Playbook

Use this sub-playbook when the user has additional context to fold into an existing `CD-DISCOVERY.md` that the automatic scan can't see — e.g., "the Groovy integration tests are abandoned, Octopus invokes Playwright post-Stage instead" or "Prod deploys are human-attended so failure emails are low-value."

The goal: verify everything that can be verified against the codebase and live APIs, then edit the report in place so the capability matrix, detailed findings, anti-patterns, recommendations, and roadmap reflect the new understanding — without losing the audit trail.

## When to run

Triggered by:
- `/cd-discovery --update [<context-or-path>]` from the launcher.
- Or: launcher detects an existing `CD-DISCOVERY.md` and the user chooses **Update** from the overwrite/update/cancel prompt.

If `CD-DISCOVERY.md` does not exist, abort and tell the user to run `/cd-discovery` first to generate the baseline. The update path edits an existing report; it does not create one.

## Inputs

| Input | Source |
|-------|--------|
| Path to existing `CD-DISCOVERY.md` | repo root |
| User context | inline string, file path, or interactive `AskUserQuestion` capture |
| Fresh `gh` auth (optional) | `gh auth status` — needed for GitHub-side re-verification |
| Fresh Octopus API key (optional) | `--octopus-api-key` / `OCTOPUS_API_KEY` — needed for Octopus-side re-verification |

The update path **does not** re-run the full PLAYBOOK / GH-DISCOVERY / OCTOPUS-DISCOVERY scans. It re-uses only the slices needed to verify the user's specific claims.

---

## Phase 1 — Ingest current report

Read `CD-DISCOVERY.md` end-to-end. Build a working index in agent memory (no scratch file) covering:

- Capability matrix row per dimension — `(dimension, level, confidence, key_evidence)`
- Detailed findings — section name, list of bullet items with FOUND/PARTIAL/MISSING/USER-REPORTED tags
- After-discovery subsections present (e.g., "After Octopus discovery", "After GitHub API discovery") — these are the precedent for the new "After <date> context refresh" subsection
- Anti-Patterns table — row per pattern with location and impact text
- Recommended Next Steps — ordered list
- Phased Improvement Roadmap — phase titles and item lists
- Existing revision-history header lines and bottom-of-file "Changes from previous report" entries

This index is your working set for Phase 5 edits. Do not write it to disk.

---

## Phase 2 — Capture user context

If the launcher passed `--update "<inline string>"` or `--update <path-to-file>`, use that as-is and skip the interactive capture.

Otherwise:
1. Ask via `AskUserQuestion`: *"What context should I fold into the report? (corrections, clarifications, downgrades, new findings)"* with options:
   - "I'll paste it now" (free text follow-up)
   - "It's in a file — I'll give you the path"
   - "Cancel"
2. After capturing the raw context, ask **one** batch of up to 4 clarifying questions:
   - Which dimensions does this touch? (multi-select: Build & CI / Testing / Deployment / IaC / Observability / Release Process / Security / Deployment Orchestrator / GitHub Posture)
   - Is any claim time-sensitive — should I record a specific date in the revision header?
   - Should I downgrade or remove any current findings explicitly, or only add new context?
   - Is fresh `gh` auth or a current Octopus API key available so I can re-verify?

Do not ask more than one batch — interview fatigue degrades quality.

---

## Phase 3 — Decompose into atomic claims

Break the user's context into a numbered list. Each claim has:

```
[N] Claim: <one-sentence summary>
    Affects: <dimension(s) + section(s)>
    Verifiability: CODEBASE | GITHUB-API | OCTOPUS-API | EXTERNAL
    Implied action: add finding | downgrade finding | remove finding | reframe finding | rename anti-pattern | update level | update confidence | reorder roadmap | add roadmap item
    Source phrase: "<verbatim snippet from user context>"
```

**Verifiability rules:**
- `CODEBASE` — anything that can be confirmed by reading a file, running `grep`, or checking `git log` in the current repo.
- `GITHUB-API` — branch protection, security alerts, workflow runs, PR cadence, repository settings. Requires `gh auth status` success.
- `OCTOPUS-API` — deployment processes, lifecycles, runbooks, variables, subscriptions, recent deployments. Requires a fresh API key.
- `EXTERNAL` — only the user / team knows. Examples: "Prod deploys are human-attended", "this code is no longer executed by any pipeline", "we abandoned X six months ago".

**Show the user the decomposed list** via a single `AskUserQuestion`:
- "Decomposition looks right — proceed to verification"
- "Let me revise — I'll re-paste"
- "Cancel"

Do not proceed to Phase 4 without confirmation. Decomposition mistakes propagate into edits; surface them while they're cheap to fix.

---

## Phase 4 — Targeted verification

For each claim, attempt verification using the matching slice:

### CODEBASE claims
Re-run the relevant scan slice from `~/.claude/skills/cd-discovery/PLAYBOOK.md` (Phase 1 sections 1.1–1.13). Examples:
- "Groovy pack is abandoned" → `grep -rn "IntegrationTests" .github/workflows/ api/ webapp/`
- "Healthcheck still no-op" → `grep -rn "HealthCheckController" api/`
- "build_properties.json version bumped" → `git log --oneline -- .github/workflows/build_properties.json`
- "We use `npm ci` not `npm install`" → `grep -nE '\bnpm (ci|install)\b' .github/workflows/webapp-build.yaml` (verify exact line in the file; do not trust prior report claims)

**Worked example — artifact-centricity claim.**

> User context: *"Our images are built once in CI and the same tag is promoted unchanged through dev → stage → prod."*
>
> Decomposition:
>
> ```
> [1] Claim: Single build per commit (no per-env rebuild)
>     Affects: Deployment Automation, Build & CI
>     Verifiability: CODEBASE
>     Verification: grep -cE 'docker build' in the relevant workflow; confirm exactly one build step, not one per env
>     Source phrase: "built once in CI"
>
> [2] Claim: Same immutable tag travels through promotion
>     Affects: Deployment Automation, Release Process
>     Verifiability: CODEBASE
>     Verification: grep deploy scripts for tag construction; confirm the tag is **read from** a file/output produced by the build (e.g., `cat *tag*.txt`, `${{ needs.build.outputs.tag }}`), not constructed in the deploy step per env
>     Source phrase: "same tag is promoted unchanged"
>
> [3] Claim: Tag never mutated post-push
>     Affects: Deployment Automation, Security
>     Verifiability: PARTIAL (CODEBASE + EXTERNAL)
>     Verification: grep workflows for `docker tag` after the prod push (CODEBASE); check registry immutability policy (EXTERNAL — ask user)
>     Source phrase: "unchanged"
> ```
>
> Implied action when verified: raise confidence on Deployment Automation; **add a Strengths to Protect entry** naming the specific file:line that implements the build → deploy tag handoff (the load-bearing line) and listing what would silently regress it (parameterizing the tag per env, retag-at-deploy, separate per-env build jobs). Do **not** treat this as a routine "found" — it's the single most defensible asset in the pipeline.

### GITHUB-API claims
Re-run the relevant slice from `~/.claude/skills/cd-discovery/GH-DISCOVERY.md`. Only the specific endpoint needed — not the full Tier 1 sweep. Examples:
- Branch protection claim → `gh api repos/{O}/{R}/branches/{B}/protection`
- CodeQL alert count → `gh api "repos/{O}/{R}/code-scanning/alerts?state=open&per_page=100" --paginate | jq -s 'add | length'`
- Dependabot updates toggle → `gh api repos/{O}/{R} --jq '.security_and_analysis.dependabot_security_updates'`

Print the authenticated `gh` user before running so the user can confirm identity. If `gh auth status` fails, skip GitHub verification — tag affected claims `[USER-REPORTED]` and note in the revision header that GitHub-side was not re-scanned.

### OCTOPUS-API claims
Re-run the relevant slice from `~/.claude/skills/cd-discovery/OCTOPUS-DISCOVERY.md` Tier 1. Examples:
- "Step 6 invokes Playwright not Groovy" → re-pull the deployment process for the named project (`deploymentprocesses/{id}`)
- "Subscription state changed" → re-pull `subscriptions/all`
- "Variable renamed" → re-pull `variables/{variableSetId}`

If no fresh API key is available, skip Octopus verification — tag affected claims `[USER-REPORTED]`, note in the revision header that the Octopus side was not re-scanned, and preserve any prior Octopus operational metrics as vintage data with an explicit date.

**Never echo the Octopus API key. Pass it via `X-Octopus-ApiKey` header only.**

### EXTERNAL claims
Mark `[USER-REPORTED]` immediately. Cap the affected dimension's confidence at MED — drop to LOW only if the user explicitly says they're unsure.

### Capture per-claim outcome
For each claim, record exactly one of:
- `VERIFIED` — evidence agrees with the user
- `CONTRADICTED` — evidence disagrees
- `UNVERIFIABLE — USER-REPORTED` — couldn't be checked from available sources

If any claim is `CONTRADICTED`, surface to the user via `AskUserQuestion` before editing:
- "Codebase / API still shows X — proceed with the claim anyway (mark `[USER-REPORTED]`, your call overrides)"
- "Drop this claim"
- "Pause for investigation — I'll dig deeper"

The user's call here is final. Record their choice so the revision-history entry can document any override.

---

## Phase 5 — Edit `CD-DISCOVERY.md` in place

Use the `Edit` tool exclusively — never `Write`. The audit trail in the report is load-bearing; replace text granularly, do not rewrite whole sections.

### 5.1 Update file header
- Prepend a new top-line revision header immediately after the `> Generated: ...` line:
  ```
  > Last revised: <YYYY-MM-DD> (<one-sentence reason — corrections from <source>, downgrades to <topic>, new finding on <topic>>)
  ```
- Push the existing top `Last revised` line down to `Prior revision` position. Keep at most 3 `Prior revision` lines in the header — older ones live only in the bottom "Changes from previous report" section.
- If Octopus or GitHub was not re-scanned this pass, add a brief note immediately below the new header explaining which vintage the unrefreshed section reflects.

### 5.2 Update Capability Matrix
For each affected dimension:
- Update Level cell if the user's claims shift the dimension up or down. Use the ranges seen in the existing report (e.g., `L1-L2`, `L2`).
- Update Confidence cell. Floor: MED for any user-reported-only delta. HIGH only if there's matching codebase/API verification.
- Update Key Evidence cell to one-sentence summary of the new state, referencing the new context.

### 5.3 Detailed Findings
For each affected dimension, **add a new subsection** following the existing pattern:
```
**After <YYYY-MM-DD> context refresh:**
- <revised understanding tied explicitly to the user's claim>
- <verification outcome and source — "verified via grep on X", "user-reported, no fresh Octopus API key available", etc.>
- <impact on this dimension's level and confidence — old → new>
```

**Do not delete prior findings.** Reframe them in place where needed. If a prior bullet is now wrong, edit its text to add a `**Updated <date>:**` annotation explaining the correction rather than removing the bullet. The existing 2026-05-12 entries in the file are the model — they keep the old framing visible and explain the downgrade.

### 5.4 Anti-Patterns table
- Downgrade: keep the row, annotate the Impact column with `Downgraded from <old severity> (<old reason>) → <new severity> (<new reason>) per <YYYY-MM-DD>`. Do not remove.
- Remove: only if the claim is `VERIFIED` and the anti-pattern is provably absent now. Move the removed row to the bottom-of-file "Changes from previous report" entry for the audit trail.
- Add: insert new rows at the end of the table. Tag with `[USER-REPORTED]` in the Impact column if unverified.

### 5.5 Recommended Next Steps & Phased Improvement Roadmap
Re-order so the highest-leverage item is still #1. Add new items inline. Remove items only if the user explicitly says they're no longer relevant — otherwise reframe.

When editing roadmap phases, prefer in-place updates of phase items to wholesale phase rewrites. The phase titles ("Phase 1 — Deploys can no longer fail silently...") should remain stable unless the user's context invalidates the phase's premise.

### 5.6 Cross-stitch consistency
After all per-dimension edits, scan the cross-stitch entries in the Deployment Orchestrator and GitHub Repository Posture sections (where they exist). If any cross-stitch contradicts a Phase 5.2 capability-matrix update, edit the cross-stitch to match — and note the change in the bottom-of-file revision entry.

---

## Phase 6 — Append revision summary

At the bottom of `CD-DISCOVERY.md`, **prepend** a new entry to the "Changes from previous report" section (newest first, matching the existing order in the file):

```markdown
### <YYYY-MM-DD> — context refresh

Triggered by: <one-line summary of user-supplied context>

**Verification posture this pass:**
- Codebase slices re-run: <list>
- GitHub-API slices re-run: <list — or "skipped, gh unauthenticated">
- Octopus-API slices re-run: <list — or "skipped, no fresh API key; Octopus section reflects <prior-scan-date> vintage">

**Per-claim outcomes:**
- [1] <claim summary> — VERIFIED via <source>
- [2] <claim summary> — CONTRADICTED by <source>; user overrode and marked [USER-REPORTED]
- [3] <claim summary> — UNVERIFIABLE — [USER-REPORTED]
- ...

**Capability matrix deltas:**
- <Dimension>: <old level/conf> → <new level/conf> because <one-line reason>
- ...

**Anti-Patterns table deltas:**
- Downgraded: <pattern name> (<old sev> → <new sev>) because <reason>
- Added: <pattern name>
- Removed: <pattern name> (relocated here for audit trail): <original row contents>

**Roadmap deltas:**
- <Phase N>: <change summary>
- ...

**Framing rule applied:** <if any branch-protection or feedback-loop framing was revisited this pass, document it here>
```

---

## Quality Gate

Before considering an update complete, verify:

- ✅ User-supplied context was decomposed into atomic claims and shown to the user for confirmation
- ✅ Each claim was attempted-verified via the most authoritative source available
- ✅ Any `CONTRADICTED` claim was surfaced to the user and their override recorded
- ✅ File header has a new `Last revised` line; prior revisions pushed down (≤3 in header)
- ✅ Each affected dimension has an `**After <date> context refresh:**` subsection in Detailed Findings
- ✅ Capability matrix rows, anti-pattern rows, recommendations, and roadmap reflect the new context
- ✅ No prior findings were silently deleted — downgrades are annotated in place
- ✅ Bottom-of-file "Changes from previous report" has a new entry summarizing verification posture, per-claim outcomes, and deltas
- ✅ No fresh API keys, secret values, full alert payloads, or PR content present in the report or agent memory
- ✅ If `gh` or Octopus were skipped, the report explicitly states which sections reflect prior-vintage data
