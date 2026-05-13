# CI/CD Discovery Playbook

Execute this playbook to scan a repository for CI/CD and deployment artifacts, analyze findings against the L0-L4 capability model, and produce `CD-DISCOVERY.md`.

---

## Phase 1: Automated Codebase Research

Scan the repository for CI/CD and deployment artifacts across 10 categories. Accumulate findings in memory — do not write files yet.

### 1.1 Detect CI Platform

Glob for pipeline config files to determine the primary CI platform:

```
.github/workflows/*.yml, .github/workflows/*.yaml
Jenkinsfile, jenkins/**
.gitlab-ci.yml
.circleci/config.yml
buildspec.yml, buildspec.yaml
azure-pipelines.yml, .azure-pipelines/**
bitbucket-pipelines.yml
```

Read each found config. Extract:
- **Trigger events** (push, PR, manual/workflow_dispatch, schedule)
- **Job structure** (build, test, deploy stages and their dependencies)
- **Enforcement** — are checks blocking or advisory? Look for `continue-on-error: true`, `allow_failure: true`, `|| true` in shell steps
- **Deploy targets** — environment names, AWS accounts, k8s clusters, URLs
- **Secret/environment references** — `${{ secrets.* }}`, env var names (names only, never values)
- **Reusable workflows or shared actions** — `uses:` references, orb imports

If no CI platform is found, note `[MISSING: No CI pipeline configuration detected]` and continue.

### 1.2 Container & Orchestration

```
Dockerfile*, .dockerignore
docker-compose*.yml, compose*.yml
k8s/**, kubernetes/**
helm/**, charts/**
**/task-definition*.json, **/ecs-*.json, **/appspec.yml
```

For Dockerfiles: note base images, multi-stage builds, health checks.
For compose files: note services, networking, volume mounts.
For orchestration: note deployment strategy (rolling, blue-green, canary), replica counts, health checks, resource limits.

### 1.3 Infrastructure as Code

```
**/*.tf (exclude .terraform/**)
terraform/**, infra/**
cloudformation/**, cfn/**
cdk.json, cdk.out/**
pulumi/**
serverless.yml, serverless.ts
sam-template.yml, template.yaml (SAM)
```

Note: IaC tool in use, what resources are managed, environment separation (dev/staging/prod), module reuse.

### 1.4 Build & Package

```
Makefile
package.json (read "scripts" block only)
build.gradle*, settings.gradle*
pom.xml
pyproject.toml, setup.py, setup.cfg
Cargo.toml
go.mod
*.csproj, *.sln
```

Extract: build commands, deploy-related scripts, test commands, lint commands. Note build tool and whether there are separate build/test/deploy targets.

### 1.5 Environment Configuration

```
.env*, env.sample, *.env.template, *.env.example
```

**CRITICAL: Only check for existence of these files. NEVER read their contents.** Note which environment templates exist and whether there's a clear dev/staging/prod separation pattern.

### 1.6 Deployment Scripts

```
deploy/**, .deploy/**
scripts/deploy*, scripts/release*
bin/deploy*, bin/release*
```

Also grep for `deploy` targets in Makefiles and package.json scripts.

Read found scripts. Note: what they deploy, to where, whether they have rollback logic, whether they're called from CI or run manually.

### 1.7 Monitoring & Observability

Glob:
```
**/alerting*, **/alerts*
**/healthcheck*, **/health.*
datadog*.yml, datadog*.yaml
newrelic*, .newrelic*
.lightstep*, honeycomb*
**/prometheus*, **/grafana*
```

Grep in source files (limit to first 20 matches):
```
healthCheck, /health, /ready, /live
metrics, prometheus, statsd
tracing, opentelemetry, datadog
structured.*log, winston, pino, bunyan, serilog
sentry, bugsnag, rollbar
```

Note: what's instrumented, what's not, whether health checks exist for all services.

### 1.8 Feature Flags

Glob:
```
**/launchdarkly*, **/feature-flag*, **/flags*
**/unleash*, **/flagsmith*, **/split*
```

Grep in source (limit to first 10 matches):
```
LaunchDarkly, feature_flag, FeatureFlag, featureFlag
unleash, flagsmith, split\.io
```

Note: whether progressive delivery is possible, which services use flags.

### 1.9 Testing

Glob:
```
test/**, tests/**, __tests__/**, spec/**, *_test.go
jest.config*, vitest.config*, pytest.ini, .pytest*
.nycrc*, codecov.yml, .coveragerc, coverage/**
sonar-project.properties, .sonarcloud*
cypress/**, playwright/**, e2e/**
```

Grep in CI configs:
```
coverage, --coverage, pytest-cov, jest --coverage
e2e, end-to-end, integration, contract
```

Note: test types present (unit, integration, e2e, contract), coverage enforcement, whether tests gate deployment.

### 1.10 Release Management

```
.releaserc*, release.config*
CHANGELOG.md, CHANGES.md
.changeset/**, .standard-version*
VERSION, version.txt
lerna.json (for monorepo versioning)
```

Grep in CI configs:
```
semantic-release, standard-version, changeset
tag, release, version bump
```

Note: versioning strategy, changelog generation, whether releases are automated or manual.

### 1.11 External Deployment Orchestrators

CI may build and publish artifacts, but actual deployment is often delegated to an external orchestrator (Octopus Deploy, Spinnaker, Argo CD, Harness, etc.). Look for handoff signals:

```
.octopus/**, OctopusDeploy*, **/octopack*
spinnaker.yml, .spinnaker/**
argocd/**, **/Application.yaml (Argo CRDs)
harness/**, .harness/**
```

Grep in CI configs for orchestrator handoff:
```
octo push, octopus-cli, OctopusDeploy/push-package-action
spin pipeline, hal deploy
argocd app sync
harness/connect, harness-cli
```

If the orchestrator is **Octopus Deploy**, treat it as a first-class discovery target and run the dedicated sub-playbook at `~/.claude/skills/cd-discovery/OCTOPUS-DISCOVERY.md`. The launcher (`SKILL.md`) decides which tier to run (API / CaC / Questionnaire) based on whether `--octopus-url` and `--octopus-api-key` (or their env vars) are set. The sub-playbook produces a **Deployment Orchestrator** section in the report and feeds revisions back into the main capability matrix — particularly Deployment Automation, Release Process, and Observability levels.

For other orchestrators, capture artifact handoff (which CI step publishes which package/manifest to which orchestrator), tag the gap as `[NEEDS CLARIFICATION: orchestrator outside repo]`, and surface it as a question in Phase 3.

### 1.12 GitHub Repository Posture

If the repository has a `github.com` git remote, treat GitHub as a first-class discovery target and run the dedicated sub-playbook at `~/.claude/skills/cd-discovery/GH-DISCOVERY.md`. The launcher (`SKILL.md`) decides whether to run based on `gh auth status` and the `--skip-github` flag.

The sub-playbook covers what is **not visible from the codebase scan alone**:
- Branch protection state (required status checks, required reviewers, code-owner enforcement, admin bypass)
- Repository security feature state (GitHub Advanced Security, secret scanning + push protection, CodeQL default setup, Dependabot updates toggle)
- Open security alert backlog by source and severity (Dependabot, code scanning, secret scanning) — counts only
- Workflow execution reality (success rates, dormant or stale workflows that exist but never run)
- PR cadence (lead time distribution + base-branch distribution — documentation drift detector)
- Default `GITHUB_TOKEN` workflow permissions
- CODEOWNERS presence

The sub-playbook produces a **GitHub Repository Posture** section in the report and feeds revisions back into the main capability matrix — particularly Build & CI, Testing, Security, and Release Process.

**Framing rule** (must propagate into both the report and the agent's reasoning): *missing branch protection on a default branch is only a finding when feedback loops are weak elsewhere.* Trunk-based development legitimately commits directly to main. Before downgrading Build & CI on branch-protection state, survey Observability, Testing, and Deployment Automation; severity emerges from the combination, not from the bare branch-protection state.

Quick git-remote detection:

```bash
git remote -v | grep -E 'github\.com[:/]'
```

If GitHub is in scope but `gh auth status` fails, fall back to Tier 2 of `GH-DISCOVERY.md` (questionnaire) or skip if the user opted out.

---

## Phase 2: Analysis & Gap Detection

Map all findings from Phase 1 to 7 dimensions. For each dimension, assess against the L0-L4 capability model.

### Dimension Assessment

For each of the 7 dimensions, determine:

1. **Level estimate** (L0-L4) based on artifacts found and their content
2. **Confidence** (HIGH = direct evidence from configs, MED = inferred from partial evidence, LOW = guessing from absence)
3. **Evidence** — specific files and line numbers
4. **Gaps** — what's missing or incomplete
5. **Questions** — what needs human clarification (can't be determined from code alone)

#### Capability Levels by Dimension

**1. Build & CI**
- L0: No CI. Manual builds.
- L1: CI runs on commit. Automated build.
- L2: CI gates merges. Build caching. Parallel jobs.
- L3: CI runs fast (<10 min). All checks enforcing. Flaky test management.
- L4: CI is optimized. Selective testing. Build times continuously monitored.

**2. Testing**
- L0: No automated tests or minimal coverage.
- L1: Unit tests exist. Run in CI.
- L2: Unit + integration tests. Coverage tracked.
- L3: Unit + integration + e2e/contract. Coverage enforced. Tests gate deploy.
- L4: Comprehensive pyramid. Contract testing between services. Test reliability monitored.

**3. Deployment Automation**
- L0: Manual deployment (SSH, console clicks, run scripts by hand).
- L1: Scripted deployment, but triggered manually.
- L2: CD pipeline deploys to staging automatically. Prod is push-button.
- L3: Every green commit deploys to prod via progressive rollout.
- L4: Deployment is a non-event. Multiple deploys per day. Automatic rollback.

**4. Infrastructure as Code**
- L0: Manual infrastructure provisioning.
- L1: Some IaC exists but not comprehensive.
- L2: IaC covers most infrastructure. Environments defined in code.
- L3: Full IaC. Environment parity. Infrastructure changes go through PR review.
- L4: Self-service infrastructure. Drift detection. Immutable infrastructure.

**5. Observability**
- L0: No monitoring. Find issues from user reports.
- L1: Basic health checks or uptime monitoring.
- L2: Application metrics + alerting. Structured logging.
- L3: Distributed tracing. SLOs defined. Alert on symptoms not causes.
- L4: Full observability stack. Anomaly detection. Deployment impact automatically correlated.

**6. Release Process**
- L0: No versioning strategy. Ad-hoc releases.
- L1: Version numbers exist. Manual changelog.
- L2: Semantic versioning. Automated changelog. Release branches.
- L3: Automated releases from CI. Feature flags for decoupling deploy from release.
- L4: Continuous release. Progressive delivery. Experimentation built in.

**7. Security**
- L0: No automated security checks.
- L1: Dependency scanning (Dependabot, Snyk, etc.).
- L2: SAST in CI. Secrets scanning. Branch protection.
- L3: Security checks gate deployment. Container scanning. Policy as code.
- L4: Security is shift-left. Threat modeling in design. Automated compliance checks.

### Anti-Pattern Detection

Flag these anti-patterns with file:line references:

| Anti-Pattern | What to Look For |
|-------------|-----------------|
| Advisory-only CI | `continue-on-error: true` on test/lint steps; `allow_failure: true` in GitLab |
| Ungated deploys | Deploy jobs that don't depend on (`needs:`) test jobs |
| Non-blocking security | Security scan steps with `continue-on-error` or not in required checks |
| Secrets in code | Hardcoded URLs with credentials, API keys in config files (flag the pattern, not the value) |
| Missing health checks | Services deployed without readiness/liveness probes |
| No rollback mechanism | Deploy scripts with no rollback logic or previous-version reference |
| Test-deploy gap | Tests run against different env/config than production deploy |

---

## Phase 3: Interactive Interview

**Skip this phase if instructed to skip the interview.** Tag all gap items with `[NEEDS CLARIFICATION]` in the output instead.

### 3.1 Present Summary

Display a dimension-by-dimension summary showing:
- Estimated level
- Key findings (1-2 bullet points per dimension)
- Number of gaps/questions per dimension

Example format:
```
## Discovery Summary

1. Build & CI — L2 (2 findings, 1 gap)
   Found: GitHub Actions CI on PR + push; lint + unit tests
   Gap: Can't determine if checks are required status checks

2. Testing — L1 (3 findings, 2 gaps)
   Found: Jest unit tests, 73% coverage
   Gaps: No integration tests detected; no e2e tests

...
```

Use `AskUserQuestion` to ask which dimensions the user wants to discuss. Offer options for each dimension plus "all" and "none (write report as-is)".

### 3.2 Deep-Dive Selected Dimensions

For each selected dimension, ask the targeted questions generated in Phase 2. Limit to 2-3 questions per dimension to avoid interview fatigue.

Questions must be specific to what was found, not generic.

Good:
- "Your CI runs lint + unit tests on PR. Are these configured as required status checks, or can PRs merge with failures?"
- "I found `scripts/deploy.sh` which pushes to ECS. Is this run manually or triggered from CI? How do you roll back a bad deploy?"
- "No monitoring configs found in the repo. Is observability managed externally (Datadog agent on infra, APM in a separate repo)?"

Bad:
- "How do you handle testing?"
- "Tell me about your deployment process"

Record all answers for inclusion in the output.

### 3.3 Revise Assessments

After the interview, revise level estimates and confidence scores based on user answers. Gaps may be filled (raising confidence), or user answers may reveal new concerns.

---

## Phase 4: Write Output

Read the template at `~/.claude/skills/cd-discovery/TEMPLATE.md` and generate `CD-DISCOVERY.md` in the project root.

### Output Rules

1. **Every claim must have evidence.** File paths with line numbers for `[FOUND]` items. Explicit `[MISSING]` tags for absent artifacts.
2. **Confidence reflects evidence quality.** HIGH = read the config and verified. MED = inferred from related artifacts. LOW = absence-based inference or unverified user claims.
3. **Anti-patterns get their own section.** Don't bury them in dimension details.
4. **Recommended next steps are concrete.** Not "improve testing" but "add integration tests for the API layer to close the unit-to-e2e gap."

---

## Quality Gate

Before considering discovery complete, verify:
- All 12 scan categories executed against the codebase (1.1–1.12)
- If an external deployment orchestrator was detected, the relevant sub-playbook ran (e.g. `OCTOPUS-DISCOVERY.md`) OR the gap is explicitly tagged
- If the repo has a GitHub remote, the GitHub sub-playbook ran (`GH-DISCOVERY.md`) OR was explicitly skipped via `--skip-github`
- Findings mapped to 7 dimensions with L0-L4 level estimates
- Anti-patterns detected and flagged with file:line references
- User interviewed about gaps (unless skip-interview mode)
- CD-DISCOVERY.md written to project root with populated capability matrix
- Deployment Orchestrator section populated when an orchestrator is in scope
- GitHub Repository Posture section populated when GitHub is in scope (or explicitly skipped)
- **Framing rule applied**: branch-protection findings are interpreted in the context of overall feedback-loop quality, not treated as findings in isolation
- Every finding backed by evidence (file paths) or tagged as [MISSING]
- No API keys, auth tokens, sensitive variable values, or full alert/PR payloads present in the report or agent memory

---

## Updating an existing report

When `CD-DISCOVERY.md` already exists and the user has additional context to fold in (corrections, clarifications, downgrades, new findings), do NOT re-run this playbook from scratch. Use the dedicated update path at `~/.claude/skills/cd-discovery/UPDATE-PLAYBOOK.md` — it ingests the existing report, decomposes user context into atomic claims, re-runs only the scan slices needed to verify those claims, and edits the report in place while preserving the audit trail.
