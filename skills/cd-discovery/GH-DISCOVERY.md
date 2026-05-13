# GitHub Repository Posture Sub-Playbook

Use this sub-playbook when the repository is hosted on **GitHub** and the discovery scan needs to see the GitHub-side state that is not visible from `.github/workflows/` alone: branch protection, security alert backlog, workflow execution reality, PR cadence, and repository security feature state.

It produces a **GitHub Repository Posture** section that gets folded into `CD-DISCOVERY.md`, and feeds revisions back into the main capability matrix (Build & CI, Testing, Security, Release Process).

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

**Never store** auth tokens, full alert payloads, or PR body content in agent memory. Only summary counts and specific named findings (e.g., "default-branch has no required status checks") are appropriate for memory.

---

## Tier 1: `gh` REST API Scan

### 1.1 Preflight — identity transparency

```bash
gh auth status
gh repo view --json nameWithOwner,defaultBranchRef,isPrivate,visibility,viewerPermission
```

**Print** the authenticated user and `viewerPermission` to the conversation so the user can confirm the scan identity. If `viewerPermission` is below `READ`, abort the sub-playbook and tag the section `[INSUFFICIENT PERMISSIONS]`.

Resolve repo owner/name from `gh repo view`. Resolve the default branch from `defaultBranchRef.name`.

### 1.2 Branch protection — default branch

```bash
gh api repos/{O}/{R}/branches/{default}/protection
```

Extract:
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

If 404, the branch has no protection. Record as a fact, not yet as a finding (see Framing Rule below).

### 1.4 Rulesets

```bash
gh api repos/{O}/{R}/rulesets
```

The newer ruleset model can supplement or supersede classic branch protection. Often empty; worth checking.

### 1.5 Repository security feature state

```bash
gh api repos/{O}/{R} --jq '.security_and_analysis'
```

Extract per feature: `advanced_security`, `secret_scanning`, `secret_scanning_push_protection`, `secret_scanning_ai_detection`, `secret_scanning_non_provider_patterns`, `secret_scanning_validity_checks`, `dependabot_security_updates`.

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

Each alert query is capped at the first **two paginated pages (200 alerts)**. If the response contains exactly 200 items, append a footnote "200+ — pagination capped" to the count.

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

Aggregate into a single severity table. Do **not** persist raw alert bodies — only counts.

### 1.9 Workflow execution reality

```bash
gh run list --repo {O}/{R} --limit 200 --json status,conclusion,workflowName,createdAt \
  | jq 'group_by(.workflowName) | map({workflow: .[0].workflowName, total: length, success: (map(select(.conclusion=="success")) | length), failure: (map(select(.conclusion=="failure")) | length)}) | sort_by(-.total)'
```

Cross-reference against defined workflows:

```bash
gh api repos/{O}/{R}/actions/workflows --jq '.workflows[] | {name, state, path}'
```

Flag workflows that exist in `.github/workflows/` but have **zero runs** in the 200-run window. For those, fetch their most recent run individually to find the last success date:

```bash
gh run list --repo {O}/{R} --workflow={path} --limit 5 --json conclusion,createdAt,event
```

### 1.10 PR cadence (lead time)

```bash
gh pr list --repo {O}/{R} --state merged --limit 100 \
  --json number,baseRefName,createdAt,mergedAt,author \
  | jq '[.[] | select(.mergedAt != null) | {hours: (((.mergedAt|fromdateiso8601)-(.createdAt|fromdateiso8601))/3600), base: .baseRefName}] | {total: length, by_base: group_by(.base) | map({base: .[0].base, count: length}), lead_time_hours: {p50: (sort_by(.hours)[length/2|floor].hours|floor), p90: (sort_by(.hours)[length*0.9|floor].hours|floor), p99: (sort_by(.hours)[length*0.99|floor].hours|floor), mean: ((map(.hours)|add)/length|floor)}}'
```

Captures lead time distribution AND the base-branch distribution. A divergence between `baseRefName` of merged PRs and the team's documented branching model in `CLAUDE.md` is itself a finding (documentation drift).

### 1.11 Dependabot PR queue

```bash
gh pr list --repo {O}/{R} --author "app/dependabot" --state open --json number --limit 100 | jq 'length'
```

A queue much smaller than the open alert backlog (especially with `dependabot_security_updates: disabled`) is a finding.

### 1.12 CODEOWNERS presence

```bash
gh api repos/{O}/{R}/contents/.github/CODEOWNERS 2>/dev/null \
  || gh api repos/{O}/{R}/contents/CODEOWNERS 2>/dev/null \
  || gh api repos/{O}/{R}/contents/docs/CODEOWNERS 2>/dev/null \
  || echo "missing"
```

If a CODEOWNERS file exists but `require_code_owner_reviews: false` on the default branch, that's a partial-adoption finding worth flagging.

---

## Tier 2: Structured Questionnaire

Triggered when `gh` is unavailable, unauthenticated, or the user opts out of Tier 1 but still wants the section populated. Ask via `AskUserQuestion` in batches of 3-4. Tag every answer with `[USER-REPORTED]` and set confidence to `LOW`.

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

## Framing Rule — interpreting branch protection in context

> **Missing branch protection on a main/default branch is only a finding when the rest of the pipeline has poor or missing feedback loops.**

Trunk-based development legitimately commits directly to main; some teams use short-lived PRs into main with branch protection, others don't. The sub-playbook reports the **state**; the agent must interpret severity by surveying the rest of the pipeline first.

Before classifying any branch-protection finding as HIGH:

- Are there required CI checks at any stage (status checks, pre-commit hooks, deploy-stage smoke gates)?
- Does a failed deploy alert someone within minutes?
- Is there an automated rollback path (canary, blue-green, single-click runbook)?
- Is the deploy frequency high enough that bad commits surface in minutes, not days?
- Is there meaningful post-deploy verification?

If most answers are "yes", missing branch protection is **information**, not a finding.
If most answers are "no", missing branch protection becomes a high-severity gap.

Document the reasoning in the Cross-Stitch section so the reader can audit the severity call.

---

## Output: GitHub Repository Posture block

Insert a section into `CD-DISCOVERY.md` matching the template in `TEMPLATE.md`. Shape:

```markdown
## GitHub Repository Posture

**Discovery source:** gh CLI REST API (Tier 1) | Questionnaire (Tier 2) | N/A
**Confidence:** HIGH | MED | LOW
**Scanned:** YYYY-MM-DD
**Authenticated as:** {gh user} (viewerPermission: {READ | TRIAGE | WRITE | MAINTAIN | ADMIN})

### Branch protection and merge gating
{table}

### Repository-level security feature state
{table}

### Open security alert backlog
{table — counts only, never payloads}

### Workflow execution reality (last N runs)
{per-workflow table}
**Workflows defined but not running:** {list with last-success date}

### PR cadence (last 100 merged PRs)
- Base-branch distribution: …
- Lead time p50/p90/p99/mean: …

### Dependabot PR queue
- N open

### CODEOWNERS
- present at {path} | missing

### Cross-stitch into capability matrix
- Build & CI: {old} → {new} because {reason — explicitly cite Observability/Testing/Deployment state when downgrading on branch-protection state alone}
- Testing: {old} → {new} because {reason}
- Security: {old} → {new} because {reason}
- Release Process: {old} → {new} because {reason — note documentation drift if CLAUDE.md branching model contradicts observed base-branch distribution}
```

---

## Cross-stitch into main capability matrix

Findings from this sub-playbook commonly affect:

- **Build & CI** — required status checks state changes the level (a workflow that doesn't gate is informational, not gating). **Apply the Framing Rule** — weight by feedback-loop quality.
- **Testing** — workflow execution reality reveals whether tests *actually* gate or just *appear to* (e.g., a Playwright workflow that hasn't passed in 3 months and only runs manually).
- **Security** — security feature state shows tooling enablement; alert backlog shows whether the team is acting on it.
- **Release Process** — base-branch distribution and CODEOWNERS presence can reveal documentation drift between CLAUDE.md and reality.

Add an "After GitHub discovery" subsection to each affected dimension's Detailed Findings explaining the before→after level change.

---

## Quality Gate

Before declaring the GitHub sub-playbook complete:

- ✅ Discovery tier recorded (Tier 1 / Tier 2)
- ✅ Authenticated user and `viewerPermission` printed to the user
- ✅ Default branch identified and its protection state recorded
- ✅ Secondary branches in workflow filters checked
- ✅ Security feature state captured (AGS, secret scanning, CodeQL, Dependabot updates)
- ✅ Alert counts summarized by severity (Dependabot + CodeQL + secret scanning)
- ✅ Workflow execution reality captured (success rates + dormant/stale workflows)
- ✅ PR cadence + base-branch distribution captured
- ✅ Framing Rule applied — branch-protection findings interpreted with explicit reference to Observability/Testing/Deployment state
- ❌ **No** auth tokens, alert bodies, or PR content stored in `CD-DISCOVERY.md` or agent memory
