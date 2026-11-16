# GitHub Repository Posture Sub-Playbook

Use this sub-playbook when the repository is hosted on **GitHub** and the discovery scan needs GitHub-side state not visible from `.github/workflows/` alone: branch protection, security alert backlog, workflow execution reality, PR cadence, and repository security feature state.

This is the single GitHub collection protocol, owned and executed by
`cd-evidence-collector`. It writes sanitized, attributable raw source
observations and a source inventory to the canonical
`<target-repo>/cd-discovery/evidence.md`, following `EVIDENCE-LEDGER.md`.
Use stable `SRC-` IDs for source observations; do not use analyst finding IDs
(`CI-`, `REL-`, `FLOW-`) for collected facts. Specialists consume the collected
evidence and must not repeat queries or broaden the scan. After specialist
results return, the strategist appends the separate analyst findings section
to the same `evidence.md` and performs assessment and report synthesis.

## When to run

The launcher (`SKILL.md`) decides. The sub-playbook is in scope when:
- The repo has a `github.com` git remote (`git remote -v` matches `github.com:`)
- The user has not passed `--skip-github`
- One of:
  - `gh auth status` succeeds (run **Tier 1**)
  - `gh auth status` fails (offer **Tier 2 questionnaire** or skip)

The destructive-action guard `~/.claude/hooks/github-destructive-guard.sh` is active and will block any non-GET `gh api`, any mutating `gh` subcommand, and any non-GET curl against `api.github.com` / `uploads.github.com`. Tier 1 below is GET-only by design, so the guard should not fire. If it does, stop and reconsider.

```
Tier 1: gh CLI authenticated (highest fidelity)
   ↓ (if gh unavailable or unauthenticated)
Tier 2: Structured questionnaire (lowest fidelity, human memory)
```

There is no Tier 3 because GitHub's "config-as-code" surface (`.github/workflows/`, `.github/dependabot.yml`, `CODEOWNERS`) is already covered by the main playbook's codebase scan.

## Inputs

Inputs come from the launcher / environment, in priority order: flag → env var → omit:

| Input | Flag | Env var | Default behavior |
|-------|------|---------|------------------|
| Skip GitHub discovery | `--skip-github` | `GH_DISCOVERY_SKIP=1` | run if gh authenticated |
| Override repo identity | `--gh-repo <owner/name>` | `GH_DISCOVERY_REPO` | infer from `git remote get-url origin` |

**Never store** auth tokens, full alert payloads, or PR body content in agent memory or `evidence.md`. The collector records sanitized source observations in `evidence.md`; it does not persist conclusions or findings in memory.

---

## Tier 1: `gh` REST API Scan

### 1.1 Preflight — identity transparency

```bash
gh auth status
gh repo view --json nameWithOwner,defaultBranchRef,isPrivate,visibility,viewerPermission
```

Check `viewerPermission` before continuing. If it is below `READ`, abort collection and record the source as `BLOCKED` with `[INSUFFICIENT PERMISSIONS]` in the evidence document. The collector reports a sanitized authentication/access status to the strategist; do not disclose the authenticated username or persist it in reports/evidence.

Resolve repo owner/name from `gh repo view`. Resolve the default branch from `defaultBranchRef.name`.

### 1.2 Branch protection — default branch

```bash
gh api repos/{O}/{R}/branches/{default}/protection
```

Record the returned settings as source observations, without classifying their
impact:
- `required_pull_request_reviews.required_approving_review_count`
- `required_pull_request_reviews.dismiss_stale_reviews`
- `required_pull_request_reviews.require_code_owner_reviews`
- `required_pull_request_reviews.require_last_push_approval`
- `required_status_checks` — **the single biggest signal**. If absent (HTTP 404 on `/required_status_checks` sub-resource), checks are not required at all
- `required_signatures.enabled`
- `enforce_admins.enabled`
- `required_conversation_resolution.enabled`
- `required_linear_history.enabled`
- `allow_force_pushes.enabled`
- `allow_deletions.enabled`

### 1.3 Branch protection — secondary branches

For each branch named in workflow `on:` filters (e.g. `develop`, `main`, `release`) that differs from the default branch:

```bash
gh api repos/{O}/{R}/branches/{branch}/protection
```

If 404, record that the queried branch protection resource returned 404 for
that branch. This is a source fact, not a finding (see the strategist framing
rule below).

### 1.4 Rulesets

```bash
gh api repos/{O}/{R}/rulesets
```

The newer ruleset model can supplement or supersede classic branch protection. Often empty; worth checking.

### 1.5 Repository security feature state

```bash
gh api repos/{O}/{R} --jq '.security_and_analysis'
```

Record per-feature states for `advanced_security`, `secret_scanning`, `secret_scanning_push_protection`, `secret_scanning_ai_detection`, `secret_scanning_non_provider_patterns`, `secret_scanning_validity_checks`, and `dependabot_security_updates`.

Also pull merge-mode config:
```bash
gh api repos/{O}/{R} --jq '{delete_branch_on_merge, allow_squash_merge, allow_merge_commit, allow_rebase_merge, allow_auto_merge}'
```

### 1.6 Workflow permissions

```bash
gh api repos/{O}/{R}/actions/permissions/workflow
```

Capture `default_workflow_permissions` (`read` is best practice; `write` is a broader blast radius). Capture `can_approve_pull_request_reviews`.

### 1.7 Code scanning default setup

```bash
gh api repos/{O}/{R}/code-scanning/default-setup
```

Captures whether CodeQL default-setup is configured, which languages, the schedule, and the query suite.

### 1.8 Open security alert counts (capped)

Each alert query is capped at the first **two paginated pages (200 alerts)**. If the response contains exactly 200 items, record "200+ — pagination capped" with the count. Record aggregate counts only, the query cap, and observation date; do not retain alert details or classify the backlog. Build the aggregate in the query pipeline; never write intermediate raw alert responses to disk or memory.

**Note on `jq` + `--paginate`:** `gh api --paginate` emits **one JSON array per page** (concatenated, not merged). So `jq 'limit(200; .[])'` applied directly fails — it only sees the first page's array. The fix is `jq --slurp 'add | limit(200; .[])'` (or `-s 'add | ...'`), which first reads all pages into a single outer array, then `add` concatenates the inner arrays into one flat list before `limit` runs.

```bash
# Dependabot
gh api "repos/{O}/{R}/dependabot/alerts?state=open&per_page=100" --paginate \
  | jq -s 'add | limit(200; .[]) | .security_advisory.severity' \
  | sort | uniq -c
```

```bash
# Code scanning
gh api "repos/{O}/{R}/code-scanning/alerts?state=open&per_page=100" --paginate \
  | jq -s 'add | limit(200; .[]) | (.rule.security_severity_level // .rule.severity)' \
  | sort | uniq -c
```

```bash
# Secret scanning
gh api "repos/{O}/{R}/secret-scanning/alerts?state=open&per_page=100" --paginate \
      | jq -s 'add | limit(200; .[]) | .secret_type' \
  | wc -l
```

Aggregate into counts by severity/type as available. Do **not** persist raw alert bodies — only bounded counts.

### 1.9 Workflow execution reality

```bash
gh run list --repo {O}/{R} --limit 200 --json status,conclusion,workflowName,createdAt \
  | jq 'group_by(.workflowName) | map({workflow: .[0].workflowName, returned: length, completed: (map(select(.conclusion=="success" or .conclusion=="failure")) | length), success: (map(select(.conclusion=="success")) | length), failure: (map(select(.conclusion=="failure")) | length), other_or_incomplete: (map(select(.conclusion!="success" and .conclusion!="failure")) | length)}) | sort_by(-.returned)'
```

This is the latest-200 returned runs, not a calendar window. Cross-reference
against defined workflows and record execution data neutrally, including
observation date, the returned population, and the number of completed runs
with `success`/`failure` conclusions. If calculating a failure fraction, use
`failure / (success + failure)` and report other/incomplete statuses separately;
do not use all returned runs as the denominator.

```bash
gh api repos/{O}/{R}/actions/workflows --jq '.workflows[] | {name, state, path}'
```

For workflows that exist in `.github/workflows/` but have **zero runs** in the returned 200-run window, fetch their most recent run individually to record the last run and conclusion date:

```bash
gh run list --repo {O}/{R} --workflow={path} --limit 5 --json conclusion,createdAt,event
```

### 1.10 PR cadence (lead time)

```bash
gh pr list --repo {O}/{R} --state merged --limit 100 \
  --json number,baseRefName,createdAt,mergedAt \
  | jq '[.[] | select(.mergedAt != null) | {hours: (((.mergedAt|fromdateiso8601)-(.createdAt|fromdateiso8601))/3600), base: .baseRefName}] | {total: length, by_base: group_by(.base) | map({base: .[0].base, count: length}), lead_time_hours: {p50: (sort_by(.hours)[length/2|floor].hours|floor), p90: (sort_by(.hours)[length*0.9|floor].hours|floor), p99: (sort_by(.hours)[length*0.99|floor].hours|floor), mean: ((map(.hours)|add)/length|floor)}}'
```

This query describes up to the latest 100 merged PRs returned, not a fixed calendar window. Record the observed date, actual merged-PR population, base-branch distribution, and calculation method for lead-time statistics. The shown quantiles use the sorted-value index `floor(p * n)` (clamped to the last index) with no interpolation; state this method and the mean's rounding method. Note if no valid merged records are available. Comparison to documented branching policy is strategist analysis, not a collector conclusion.

### 1.11 Dependabot PR queue

```bash
gh pr list --repo {O}/{R} --author "app/dependabot" --state open --json number --limit 100 | jq 'length'
```

Record the returned open-PR count and query date. Comparisons with alert counts or settings are strategist analysis.

### 1.12 CODEOWNERS presence

```bash
gh api repos/{O}/{R}/contents/.github/CODEOWNERS 2>/dev/null \
  || gh api repos/{O}/{R}/contents/CODEOWNERS 2>/dev/null \
  || gh api repos/{O}/{R}/contents/docs/CODEOWNERS 2>/dev/null \
  || echo "missing"
```

Record file presence and the queried `require_code_owner_reviews` setting as separate source facts. Their relationship is for strategist analysis.

### 1.13 Artifact provenance and supply-chain posture

Grep the workflows for the supply-chain and artifact-identity signals that don't show up in `repos/{O}/{R}/security_and_analysis`. These feed §1.13 of the main playbook and the Strengths to Protect / Anti-Patterns sections of the report.

**Provenance, signing, SBOM:**

```bash
grep -rEn 'cosign|sigstore|actions/attest-build-provenance|anchore/sbom-action|slsa-framework|syft|grype' .github/workflows/
```

**Dependency cache coverage on the main build path:**

```bash
grep -rEn 'actions/cache|cache:[[:space:]]*(npm|yarn|pnpm|pip|maven|gradle)|cache-from|cache-to' .github/workflows/
```

Record matching cache configuration and the inspected workflow paths as source facts. Whether the observed configuration affects feedback loops is strategist analysis.

**Install command hygiene:**

```bash
grep -rEn '\bnpm install\b|\byarn install\b|\bpip install\b' .github/workflows/
```

Cross-check each match against surrounding context. Record the actual install command and its file/line; `npm ci`, `yarn install --frozen-lockfile`, and `pip install --require-hashes` differ from raw `npm install`, `yarn install`, and `pip install`. Whether the command constitutes a finding is strategist analysis. Verify the actual command in the file — do not trust prior reports.

**Build-once-promote signals:**

```bash
# Count distinct build invocations per workflow (heuristic; verify by reading)
grep -rcEn '^\s*-\s*(name:.*[Bb]uild|run:.*docker build|run:.*dotnet publish|run:.*npm run build)' .github/workflows/
```

Record the build-invocation observations and workflow path. Pair with the deploy-script evidence from main playbook §1.13 for strategist analysis; do not infer per-environment rebuilds from this heuristic alone.

Record relevant matches as source observations in `evidence.md` with file/line references. Dimension mapping and assessment belong to strategist synthesis.

---

## Collection ownership and handoff

`cd-evidence-collector` performs every applicable GitHub CLI/API query in this
protocol once, then records the result in `<target-repo>/cd-discovery/evidence.md`.
The source inventory records each source family as `COMPLETE`, `PARTIAL`,
`BLOCKED`, `SKIPPED`, `NOT_APPLICABLE`, or `MISSING`, with attempted scope,
sanitized access context, and limitation/reason. User answers are `USER-REPORTED`
source records, not inventory statuses. Use the record schema in
`EVIDENCE-LEDGER.md`; each source observation must cite a narrow
resource/query or file reference and include observed date, access context,
scope, and limitations. For metrics, scope the time window, population, and
calculation method (including numerator/denominator) explicitly. Do not record
interpretations, maturity, severity, recommendations, or a dimension-tagged
weave map.

Specialists receive only the relevant sanitized evidence and `SRC-` references
from this document. They do not call GitHub or rerun collection. If a necessary
fact is absent, mark it as a bounded gap for the strategist; do not broaden the
query independently. The strategist later validates and appends specialist
`CI-`, `REL-`, and `FLOW-` analyst records under `## Analyst findings` in the
same `evidence.md`, reusing the source references and avoiding duplicate
claims. GitHub alert counts may be assessed by the strategist after collection;
the collector records counts and limits only.

---

## Tier 2: Structured Questionnaire

Triggered when `gh` is unavailable or unauthenticated but the user still wants GitHub evidence. The collector returns the exact questionnaire as a structured clarification handoff and does not ask the user. The top-level skill presents it via `AskUserQuestion` in batches of 3–4, then invokes a targeted collector continuation with sanitized answers. A headless/skip-interview run leaves the source family `BLOCKED` or `SKIPPED` as appropriate, with the unresolved question recorded. Record each supplied answer as a concise, sanitized `USER-REPORTED` source observation in `evidence.md`, with the question as the source reference and observed date; avoid unnecessary personal or sensitive details.

### Batch A — Gating

1. "Does merging to your default branch require any required CI checks? If yes, which workflows?"
2. "Are pull request reviews required? How many approvers, and is CODEOWNERS enforced?"
3. "Can admins bypass branch protection? Are stale reviews dismissed on new commits?"
4. "Is direct push to the default branch allowed?"

### Batch B — Security tooling

5. "Is GitHub Advanced Security enabled? Secret scanning? Push protection? CodeQL default setup?"
6. "Is Dependabot enabled? Are auto-PRs for security updates enabled (the `dependabot_security_updates` toggle)?"
7. "Roughly how many open security alerts do you have right now? (Dependabot + CodeQL + secret scanning combined is fine.)"
8. "Are any of those alerts blocking merges, or are they purely informational?"

### Batch C — Workflows and cadence

9. "What CI workflows do you have that run on PRs? Roughly what's the success rate?"
10. "Do any workflows exist but don't actually run (manual-only, scheduled-and-stale, or otherwise dormant)?"
11. "Where do most merged PRs target — main, develop, release, something else? Roughly what's the median PR open-to-merged time?"
12. "Is the default `GITHUB_TOKEN` permission `read` or `write` in your workflows?"

---

## Strategist framing rule — interpreting branch protection in context

> **Missing branch protection on a main/default branch is only a finding when the rest of the pipeline has poor or missing feedback loops.**

Trunk-based development legitimately commits directly to main; some teams use short-lived PRs into main with branch protection, others don't. The collector records the **state**; the strategist interprets severity by surveying the rest of the pipeline first.

Before classifying any branch-protection finding as HIGH:

- Are there required CI checks at any stage (status checks, pre-commit hooks, deploy-stage smoke gates)?
- Does a failed deploy alert someone within minutes?
- Is there an automated rollback path (canary, blue-green, single-click runbook)?
- Is the deploy frequency high enough that bad commits surface in minutes, not days?
- Is there meaningful post-deploy verification?

If most answers are "yes", missing branch protection is **information**, not a finding.
If most answers are "no", missing branch protection becomes a high-severity gap.

The strategist documents the reasoning in the Cross-Stitch section so the reader can audit the severity call.

### Strategist framing rule — artifact-centricity (parallel)

Parallel to the branch-protection rule: build-once-promote-the-same-artifact is the load-bearing CD principle. When §1.13 of the main playbook verifies it is in place (single image build per commit, immutable tag, deploy step reads tag from the build rather than constructing it), the strategist may name it as a **Strength to Protect** in the Cross-stitch section, with explicit warnings about what would regress it (per-env tag parameterization, retag-at-deploy, separate per-env build jobs). When it is absent, the strategist weighs it as a Deployment Automation concern — re-testing per environment defeats the confidence model that CD depends on.

Build-once-with-config-swap-at-deploy (identical artifact bytes; runtime config swapped by the deploy step) is acceptable but must be framed as an asterisk so future readers don't confuse it with a full violation.

---

## Output: source evidence in `evidence.md`

Write all collected GitHub observations and source inventory rows to
`<target-repo>/cd-discovery/evidence.md`, following the canonical structure and
`SRC-` schema in `EVIDENCE-LEDGER.md`. Do not emit a weave map, dimension-tagged
findings, maturity levels, severity, or recommendations. Preserve only the raw
evidence minimum needed for attributable analysis; summarize counts and
configuration states rather than copying full alert, workflow-run, or PR
payloads. For alert data, record bounded aggregate counts and the query cap,
without alert bodies or identifying alert details.

Example source observation (illustrative; use actual observed values and date):

```markdown
### SRC-gh-required-checks-main
#### SRC-gh-required-checks-main — required status check configuration
- Status: VERIFIED
- Scope: `acme/payments`, default branch `main`; required status checks.
- Source: api — `GET repos/acme/payments/branches/main/protection`; required status checks.
- Observed: 2026-11-13
- Access context: GitHub CLI Tier 1, authenticated read-only repository access.
- Supports: true
- Limitations: Only the default branch was examined for this observation.
- Related IDs: none
```

The framing rules below remain synthesis guidance for the strategist, not
collector output. A missing protection setting is a state observation; whether
it is a gap and its severity depend on the wider feedback loops. Likewise,
artifact-centricity conclusions and Strengths to Protect belong to strategist
synthesis after the relevant source evidence has been reviewed.

### Authentication preflight (preserved)

Before any `gh` CLI call, check authenticated access and `viewerPermission`.
Report only a sanitized access status and permission sufficiency to the
strategist. Do not print or persist the authenticated username, and never echo
auth tokens to `evidence.md`, memory, or terminal output.

---

## Strategist synthesis notes

Collected GitHub evidence commonly informs Build & CI, Testing, Security, and
Release Process. The strategist integrates it into the capability matrix after
specialist results, applies the branch-protection and artifact-centricity
framing rules above, and records analyst findings in the separate analyst
section of `evidence.md`. Do not ask specialists to revisit GitHub sources that
this protocol already collected.

---

## Quality Gate

Before declaring GitHub source collection complete:

- ✅ Every applicable GitHub source family recorded in `<target-repo>/cd-discovery/evidence.md` inventory with status, attempted scope, sanitized access context, and limitation/reason
- ✅ Source observations use stable `SRC-` IDs and the `EVIDENCE-LEDGER.md` source-record schema
- ✅ Authentication and sufficient `viewerPermission` checked; only sanitized access status recorded
- ✅ Default branch identified and its protection state recorded
- ✅ Secondary branches in workflow filters checked
- ✅ Security feature state captured (AGS, secret scanning, CodeQL, Dependabot updates)
- ✅ Alert counts summarized by severity (Dependabot + CodeQL + secret scanning)
- ✅ Workflow execution reality captured (success rates + dormant/stale workflows)
- ✅ PR cadence + base-branch distribution captured
- ✅ Branch-protection and artifact-centricity source facts are recorded neutrally; framing belongs to strategist synthesis
- ✅ Artifact-provenance greps executed (cosign / SBOM / attestation, dependency cache coverage, install-command hygiene, build-once signals)
- ✅ Metrics record the time window, population, and calculation method, including denominators and sampling/cap limits
- ✅ Specialist handoff uses only existing sanitized observations and `SRC-` IDs; no GitHub source is queried twice
- ❌ **No** auth tokens, alert bodies, full PR content, or sensitive values are stored in `evidence.md` or agent memory
- ❌ **No** final maturity, severity, recommendations, or dimension-tagged weave map is emitted by the collector
