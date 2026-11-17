# GitHub Repository Posture Sub-Playbook

Use when GitHub-side state is needed beyond the `.github/workflows/` scan: branch protection, security alerts/features, workflow execution, and PR cadence. This is the collector's single read-only GitHub protocol; write sanitized source observations to `evidence.md` under the `EVIDENCE-LEDGER.md` contract.

## When to run

The launcher (`SKILL.md`) decides. The sub-playbook is in scope when:
- The repo has a `github.com` git remote (`git remote -v` matches `github.com:`)
- The user has not passed `--skip-github`
- One of:
  - `gh auth status` succeeds (run **Tier 1**)
  - `gh auth status` fails (offer **Tier 2 questionnaire** or skip)

Suppress `gh auth status` output; use its exit status only.

Tier 1 is GET-only. If the destructive-action guard blocks a request, stop and reconsider.

```
Tier 1: gh CLI authenticated (highest fidelity)
   ↓ (if gh unavailable or unauthenticated)
Tier 2: Structured questionnaire (lowest fidelity, human memory)
```

There is no Tier 3: GitHub config-as-code is covered by the main playbook scan.

## Inputs

Inputs come from the launcher / environment, in priority order: flag → env var → omit:

| Input | Flag | Env var | Default behavior |
|-------|------|---------|------------------|
| Skip GitHub discovery | `--skip-github` | `GH_DISCOVERY_SKIP=1` | run if gh authenticated |
| Override repo identity | `--gh-repo <owner/name>` | `GH_DISCOVERY_REPO` | infer from `git remote get-url origin` |

Never store auth tokens, full alert payloads, or PR body content.

---

## Tier 1: `gh` REST API Scan

### 1.1 Preflight — identity transparency

```bash
gh auth status >/dev/null 2>&1
gh repo view --json nameWithOwner,defaultBranchRef,isPrivate,visibility,viewerPermission
```

Check `viewerPermission`; below `READ`, stop and mark the source `BLOCKED` (`[INSUFFICIENT PERMISSIONS]`). Report sanitized access status only; never disclose or persist the authenticated username.

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

Fetch only pages 1 and 2, then aggregate their arrays:

```bash
gh_alert_pages() {
  for page in 1 2; do gh api "$1&per_page=100&page=$page"; done
}

# Dependabot
gh_alert_pages "repos/{O}/{R}/dependabot/alerts?state=open" \
  | jq -s 'add | limit(200; .[]) | .security_advisory.severity' \
  | sort | uniq -c
```

```bash
# Code scanning
gh_alert_pages "repos/{O}/{R}/code-scanning/alerts?state=open" \
  | jq -s 'add | limit(200; .[]) | (.rule.security_severity_level // .rule.severity)' \
  | sort | uniq -c
```

```bash
# Secret scanning
gh_alert_pages "repos/{O}/{R}/secret-scanning/alerts?state=open" \
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

## Evidence handoff

Run each applicable query once. Record source inventory and neutral `SRC-` observations using `EVIDENCE-LEDGER.md`; metrics include time/sample bounds, population, and calculation/denominator. Specialists use these records without re-querying; absent facts remain bounded gaps for strategist synthesis.

---

## Tier 2: Structured Questionnaire

If `gh` is unavailable or unauthenticated and GitHub evidence is still requested, return the exact questions below to the top-level skill as a clarification handoff; do not interview the user. The top-level skill asks in batches of 3–4 and invokes a targeted continuation with sanitized answers. In headless/skip-interview runs, leave the source `BLOCKED` or `SKIPPED` and unresolved. Record answers as concise `USER-REPORTED` observations, sourced to the question and date.

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

## Strategist interpretation

Missing default-branch protection is a finding only when feedback loops are weak elsewhere. Trunk-based development may legitimately commit directly to main; assess required checks, deploy alerts, rollback, deploy frequency, and post-deploy verification before assigning severity. Document the reasoning in synthesis (see `PLAYBOOK.md`).

Artifact-centricity is strategist synthesis: build once and promote the same immutable artifact; per-environment rebuilds, mutable production tags, or retagging at deploy are concerns. Identical artifact bytes with runtime config swapped at deploy are acceptable with that qualification. See `PLAYBOOK.md` §1.13.

---

## Evidence output

Write sanitized source facts, aggregate alert counts, and inventory rows to `<target-repo>/cd-discovery/evidence.md` using `EVIDENCE-LEDGER.md`. Do not persist credentials, alert details, or full PR content; interpretation and assessment belong to strategist synthesis.
