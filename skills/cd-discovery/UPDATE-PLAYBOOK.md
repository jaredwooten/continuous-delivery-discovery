# CI/CD Discovery — Update Sub-Playbook

Use this sub-playbook when the user has additional context to fold into an existing `cd-discovery/` directory that the automatic scan can't see — e.g., "the Groovy integration tests are abandoned, Octopus invokes Playwright post-Stage instead" or "Prod deploys are human-attended so failure emails are low-value."

The goal: use the existing report and canonical `cd-discovery/evidence.md`, request targeted recollection when needed, then update the report to reflect the new understanding — without losing collection or report audit trails.

## When to run

Triggered by:
- `/cd-discovery --update [<context-or-path>]` from the launcher.
- Or: launcher detects an existing `cd-discovery/` directory and the user chooses **Update** from the overwrite/update/cancel prompt.

If `cd-discovery/` does not exist, abort and tell the user to run `/cd-discovery` first to generate the baseline. The update path edits an existing report; it does not create one.

## Inputs

| Input | Source |
|-------|--------|
| Path to existing `cd-discovery/` directory | repo root |
| User context | inline string, file path, or interactive `AskUserQuestion` capture |
| Existing `cd-discovery/evidence.md` | prior source inventory, dated collection runs, `SRC-` records, and analyst findings; create the canonical document if absent |
| Fresh `gh` auth (optional) | `gh auth status` — needed for GitHub-side re-verification |
| Fresh Octopus API access (optional) | `OCTOPUS_URL` and `OCTOPUS_API_KEY` supplied through approved runtime/environment secret injection — needed for Octopus-side re-verification; never pass the key as a CLI flag or in a prompt |

The update path **does not** re-run the full PLAYBOOK / GH-DISCOVERY / OCTOPUS-DISCOVERY scans. Reuse prior evidence and request only the slices needed to verify the user's specific claims. The strategist owns scope, consent, interview, and synthesis; it never collects evidence itself. The `cd-evidence-collector` alone performs any targeted recollection and updates `evidence.md`.

---

## Phase 1 — Ingest current report into a working memory index

Read all markdown files in `cd-discovery/`:

- `cd-discovery/summary.md` — always present
- `cd-discovery/findings.md` — always present
- `cd-discovery/suggestions.md` — present only when `--suggest` was previously run
- `cd-discovery/evidence.md` — prior source inventory/runs and existing source and analyst records; preserve its history

For each file, build a working memory index that captures:

- Dimensions and their current levels + confidence (from summary.md matrix and findings.md sections)
- Strengths to Protect (from summary.md)
- Anti-patterns (from summary.md)
- Per-dimension artifacts and gaps (from findings.md)
- Suggestion items and their dependency edges (from suggestions.md if present)
- Each file's existing Revision history (so update entries don't duplicate past events)
- Existing `SRC-` IDs, source freshness/limitations, and analyst finding-to-source references from `evidence.md`

If `cd-discovery/` does not exist, abort with the message: "No cd-discovery/ directory found — run `/cd-discovery` first to generate the baseline, then re-run with `--update`."

---

## Phase 2 — Capture user context

If the launcher passed `--update "<inline string>"` or `--update <path-to-file>`, use that as-is and skip the interactive capture.

Otherwise:
1. Ask via `AskUserQuestion`: *"What context should I fold into the report? (corrections, clarifications, downgrades, new findings)"* with options:
   - "I'll paste it now" (free text follow-up)
   - "It's in a file — I'll give you the path"
   - "Cancel"
2. After capturing the raw context, ask **one** batch of up to 4 clarifying questions:
   - Which dimensions does this touch? (multi-select: Build & CI / Testing / Deployment / IaC / Observability / Release Process / Security / external deployment evidence / GitHub evidence woven into dimensions)
   - Is any claim time-sensitive — should I record a specific date in the revision header?
   - Should I downgrade or remove any current findings explicitly, or only add new context?
   - Is fresh `gh` auth or a current Octopus API key available so I can re-verify?

Do not ask more than one batch — interview fatigue degrades quality.

---

## Phase 3 — Decompose into atomic claims; tag each with target file(s)

Convert the user's context into a list of atomic claims. Each claim is a single, verifiable assertion (e.g., "Testing is now L2 because we added E2E coverage in CI", not "we improved testing").

For each claim, tag the file(s) it touches:

- `[summary]` — claims that change the capability matrix, Strengths to Protect, anti-patterns, or next steps
- `[findings]` — claims that add or change evidence in a per-dimension section
- `[suggestions]` — claims that add, remove, or supersede a suggestion (only valid when suggestions.md exists)
- Multi-tag — claims that change a dimension's level touch both `[summary]` (matrix row) and `[findings]` (the dimension section). The decomposition step must flag these as multi-file claims so they do not get half-applied.

Show the tagged claim list to the user. The user confirms or amends before any verification or edit runs. If the user removes a claim or adds a new one, re-tag and re-confirm.

#### Multi-file claim propagation rule

When a tagged claim touches multiple files, every file in the tag must be edited in the same pass. The Quality Gate (below) fails if a multi-file claim landed in some but not all of its tagged files.

---

## Phase 4 — Targeted verification

For each claim, first check whether existing `evidence.md` contains relevant, sufficiently fresh evidence. When new source evidence is required, define the exact requested slice and disposition any out-of-scope or inaccessible source. Send a bounded recollection request to `cd-evidence-collector`, including the target/ref, user-approved systems and scope, relevant paths/claims, exclusions, and applicable playbook procedures. The collector alone performs read-only collection and appends a dated run and source inventory/records to `evidence.md`; the strategist does not run queries or collect sources. Reuse stable `SRC-` IDs for the same enduring claim and scope. Preserve prior evidence and set its separate `Freshness` metadata to `STALE` or `SUPERSEDED` with the replacing `SRC-` ID; retain the evidence `Status` from the allowed enum. Keep conflicting evidence and mark the claim `CONFLICTED` until resolved. If collection is blocked or incomplete, retain that disposition and limitation rather than implying absence.

For each claim, the collector uses the matching slice:

### CODEBASE claims — collector only
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

### GITHUB-API claims — collector only
Re-run the relevant slice from `~/.claude/skills/cd-discovery/GH-DISCOVERY.md`. Only the specific endpoint needed — not the full Tier 1 sweep. Examples:
- Branch protection claim → `gh api repos/{O}/{R}/branches/{B}/protection`
- CodeQL alert count → `gh api "repos/{O}/{R}/code-scanning/alerts?state=open&per_page=100" --paginate | jq -s 'add | length'`
- Dependabot updates toggle → `gh api repos/{O}/{R} --jq '.security_and_analysis.dependabot_security_updates'`

Follow the GitHub sub-playbook's read-only preflight and scope rules. If authorization or access is unavailable, the collector records a safe `BLOCKED`/`SKIPPED` disposition and limitation; do not broaden access. User statements remain identified as user-reported unless independently verified.

### OCTOPUS-API claims — collector only
Re-run the relevant slice from `~/.claude/skills/cd-discovery/OCTOPUS-DISCOVERY.md` Tier 1. Examples:
- "Step 6 invokes Playwright not Groovy" → re-pull the deployment process for the named project (`deploymentprocesses/{id}`)
- "Subscription state changed" → re-pull `subscriptions/all`
- "Variable renamed" → re-pull `variables/{variableSetId}`

If the key is unavailable, the collector does not request or search for it; it records the API tier as `BLOCKED` and may continue only with an explicitly in-scope, readable CaC source or strategist-supplied user-reported evidence. Preserve prior Octopus evidence as historical, with its observation date and freshness limitation.

The collector never echoes the Octopus API key and sends it only via the `X-Octopus-ApiKey` request header as permitted by the Octopus sub-playbook.

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

## Phase 5 — Edit in place using granular Edit calls

For each confirmed claim, use the `Edit` tool to make targeted changes to the file(s) listed in the claim's tag. Rules:

- **No whole-file rewrites.** Each `Edit` call replaces a single coherent block (a matrix row, a finding entry, a suggestion item, a section header — never a whole file).
- **Touch only the files the claims affect.** Files not mentioned in any claim's tag must not be edited.
- **Cross-file claims edit each file in turn within the same pass.** Do not commit between the two halves of a multi-file claim; if the executor is committing per-pass, the commit covers all files the claim touched.

If a claim was tagged `CONTRADICTED` in Phase 4 verification, do not apply the user-reported version unless the user explicitly overrides after seeing the contradiction.

**No time-duration estimates on roadmap phases or items.** When applying updates, do not introduce weeks, days, sprints, quarter targets, or dates onto roadmap phases — even if the user's context phrases improvements in time-bound language, translate to sequence/dependency framing. If the user explicitly asks for a date or duration in the roadmap, surface it as out of scope for this report and let them place it in their own planning tool. (DORA windows and other observed-state durations elsewhere in the report are unaffected.)

---

## Phase 6 — Append per-file revision log entries

For each report file touched in Phase 5, append one entry to that file's bottom `## Revision history` section. Files not touched get no entry. For `evidence.md`, retain the collector's append-only dated run and source records; the strategist appends or updates analyst findings without deleting prior runs, records, or findings. Mark superseded source evidence with `Freshness: STALE` or `Freshness: SUPERSEDED`, include its replacement `SRC-` ID, and preserve the original evidence status and limitations.

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

---

## Quality Gate

Apply this checklist per file the agent touched. If any item fails, do not declare done.

- [ ] Each claim tagged for this file produced a corresponding edit in this file.
- [ ] Multi-file claims propagated correctly — if this file got a level change, the other tagged file also got the corresponding edit.
- [ ] No whole-file rewrites occurred — every change is a granular Edit.
- [ ] A new entry was appended to this file's `## Revision history` if any edits landed.
- [ ] No auth tokens, raw secret values, full alert payloads, or full PR bodies were written to this file or to agent memory.
- [ ] `evidence.md` retains prior collection runs and records; any replaced source record has `Freshness: STALE` or `Freshness: SUPERSEDED` and is linked to its replacement `SRC-` ID without changing its evidence status.
- [ ] New recollection, if any, was performed only by `cd-evidence-collector`; strategist and specialists did not repeat collection queries.
- [ ] Strengths to Protect (summary.md) and Anti-patterns Detected (summary.md) were re-checked if any dimension's level changed.

A passed Quality Gate per touched file is required before Phase 6 entries are considered finalized.
