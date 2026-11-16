# Octopus Deploy Discovery Sub-Playbook

Use this sub-playbook when the repository is deployed via **Octopus Deploy** and the orchestrator is not visible from the codebase alone. It is the single Octopus source-collection protocol, owned and executed by `cd-evidence-collector`. The collector writes sanitized, attributable raw source observations and a source inventory to the canonical `<target-repo>/cd-discovery/evidence.md`, following `EVIDENCE-LEDGER.md`.

The sub-playbook tries three sources in order. Stop at the first one that succeeds — do not double-collect.

The collector performs each applicable API, CaC, or questionnaire collection once. Do not write raw API responses, command output, or intermediate payloads to files or memory; sanitize at collection time and retain only the evidence minimum needed for attribution. Use stable `SRC-` IDs for source observations; do not use analyst finding IDs (`CI-`, `REL-`, `FLOW-`) for collected facts. Specialists consume the collected evidence and must not repeat queries or broaden collection. After specialist results return, the strategist appends the separate analyst findings section to the same `evidence.md` and performs assessment and report synthesis.

```
Tier 1: REST API (highest fidelity)
   ↓ (if no URL/key, or auth fails)
Tier 2: Config-as-Code repo (medium fidelity)
   ↓ (if no CaC repo found)
Tier 3: Structured questionnaire (lowest fidelity, human memory)
```

## Inputs

The skill launcher passes any of the following (in priority order: flag → env var → omit), except that the API key is supplied only through approved runtime secret injection or the process environment:

| Input | Flag | Env var | Required |
|-------|------|---------|----------|
| Octopus server URL | `--octopus-url` | `OCTOPUS_URL` | Tier 1 only |
| API key | **No command-line flag** | `OCTOPUS_API_KEY` | Tier 1 only |
| Space ID or name | `--octopus-space` | `OCTOPUS_SPACE` | Tier 1 only |
| Project name(s) | `--octopus-project` | `OCTOPUS_PROJECT` | optional filter |

**The API key must be provided only as an environment variable or approved runtime secret; never accept it as a flag or prompt value.** Do not type it into a command, shell history, prompt, file, or output. Never echo it to the terminal, report, or memory. Supply it to curl through standard input as curl configuration, never by expanding it into a command-line argument (including `-H`/`--header`). If a Tier 1 attempt fails, log the failure mode (4xx, 5xx, network) without the key value.

---

## Tier 1: REST API Scan

Use the following shell helper for every Tier 1 request. It streams curl configuration over stdin, so the key is not included in curl's process arguments and is not written to a file. The key must already be present in the environment via approved runtime secret injection; do not enter it into an `export` command or other shell-history entry. Do not enable shell tracing (`set -x`) or curl verbose/trace output while using the secret. All endpoints below are relative to `${OCTOPUS_URL}/api`. Replace `{space}` with the resolved space ID (e.g. `Spaces-1`).

```bash
octopus_get() {
  local url=$1
  curl --silent --show-error --config - <<EOF
header = "X-Octopus-ApiKey: ${OCTOPUS_API_KEY}"
url = "${url}"
EOF
}
```

Pass the URL to `octopus_get`; do not add an API-key header to the invocation or enable verbose/trace output.

### 1.1 Resolve Space

```bash
octopus_get "$OCTOPUS_URL/api/spaces/all" | jq '.[] | {Id, Name, IsDefault}'
```

If `--octopus-space` matches an `Id` or `Name`, use that. Otherwise pick the default space and record the selected default-space assumption in the source inventory.

### 1.2 Locate the Project(s)

```bash
octopus_get "$OCTOPUS_URL/api/{space}/projects/all" | jq '.[] | {Id, Name, Slug, LifecycleId, IsDisabled, IsVersionControlled}'
```

Match against `--octopus-project` (substring or exact). If not provided, use repository-name matching only to identify candidate projects (e.g., `mi-portal` → project slugs or names containing `mi-portal`, `mi-api`, or `mi-web`). If the result is ambiguous, do not choose a project or ask the user. Record the source inventory as `BLOCKED`, create an `UNVERIFIED` evidence record for the unresolved selection with the exact candidate set and structured question in the collector handoff, and return control to the strategist/launcher. The strategist/launcher asks the user, then invokes a targeted collector continuation with the sanitized answer. Until then, do not collect project-specific resources. Record the selected project and selection basis after continuation.

For each matched project, capture:
- `Id`, `Name`, `Slug`, `IsDisabled`, `IsVersionControlled` (CaC enabled?)
- `LifecycleId`, `ProjectGroupId`
- `DeploymentProcessId`, `VariableSetId`

### 1.3 Deployment Process

```bash
octopus_get "$OCTOPUS_URL/api/{space}/deploymentprocesses/{id}" | jq '{
    Steps: .Steps | map({
      Name, StartTrigger, Condition, PackageRequirement,
      ActionTypes: (.Actions | map(.ActionType)),
      Environments: (.Actions | map(.Environments) | flatten | unique),
      ExcludedEnvironments: (.Actions | map(.ExcludedEnvironments) | flatten | unique),
      RunOnServer: (.Actions[0].Properties["Octopus.Action.RunOnServer"]),
      ManualIntervention: (.Actions | any(.ActionType == "Octopus.Manual"))
    })
  }'
```

Extract per step:
- **Name** and **ActionType** (e.g. `aws.ecs.UpdateService`, `Octopus.AwsRunCloudFormation`, `Octopus.Script`, `Octopus.Manual`, `Octopus.Email`)
- **Environment scoping** — which envs run this step
- **Manual intervention gates** — any `Octopus.Manual` actions are deploy-pause points
- **Conditions** — `OnlyIfPriorStepFailed`, `OnlyIfPriorStepSucceeded`, etc. (rollback hints)
- **Health check or smoke test** steps after a deploy action

Record, without judging, whether the inspected process contains a manual
intervention before production, an explicit rollback step in the lifecycle,
and `Octopus.Script` actions. For script actions, record only a concise,
sanitized description of the relevant operation; never copy script contents
that include credentials, values, or unrelated implementation details.

### 1.4 Lifecycle & Promotion Rules

```bash
octopus_get "$OCTOPUS_URL/api/{space}/lifecycles/{id}" | jq '{
    Name, Description,
    Phases: .Phases | map({
      Name,
      MinimumEnvironmentsBeforePromotion,
      IsOptionalPhase,
      AutomaticDeploymentTargets,
      OptionalDeploymentTargets
    }),
    ReleaseRetentionPolicy,
    TentacleRetentionPolicy
  }'
```

Capture:
- **Phase order** (which envs gate which) — this is the promotion path
- `AutomaticDeploymentTargets` — environments that auto-deploy on a new release (no human gate)
- `OptionalDeploymentTargets` — environments that require a human "Deploy" click
- `MinimumEnvironmentsBeforePromotion` — ratchet preventing skipping envs
- **Retention policy** — how many releases / days are kept (matters for rollback window)

The `AutomaticDeploymentTargets` list is the observed configuration for
automatic deployment targets; preserve the selected lifecycle/phase scope.

### 1.5 Channels & Versioning Rules

```bash
octopus_get "$OCTOPUS_URL/api/{space}/projects/{id}/channels" | jq '.Items | map({
    Name, IsDefault, LifecycleId,
    Rules: .Rules | map({Tag, VersionRange, ActionPackages})
  })'
```

Note channels (e.g. `default`, `hotfix`, `release-candidate`) and their version-range gates. Channels often map to git branches.

### 1.6 Recent Deployments — Frequency & Failure Rate

```bash
# Last 50 deployments for the project
octopus_get "$OCTOPUS_URL/api/{space}/deployments?projects={projectId}&take=50" \
  | jq '.Items | map({
      Created, EnvironmentId, ReleaseId, TaskId,
      FailureEncountered: .FailureEncountered
    })'

# Resolve task state per deployment for State + Duration
octopus_get "$OCTOPUS_URL/api/{space}/tasks/{taskId}" \
  | jq '{State, FinishedSuccessfully, StartTime, CompletedTime}'
```

If computing metrics from collected records, record the exact time window or
returned-sample bounds, population and exclusions, and calculation method
(including numerator/denominator for rates). For a latest-N sample, do not
describe the result as a fixed 30/90-day rate unless the selected records
actually span that calendar interval. Record duration calculation and failed
deployment-to-next-success matching rules for any recovery proxy. Do not retain
individual `DeployedBy` names; at most record an aggregate count/distribution
when needed, with the population and window stated. Do not make DORA maturity or
health judgments.

### 1.7 Runbooks (Operational Playbook Coverage)

```bash
octopus_get "$OCTOPUS_URL/api/{space}/projects/{id}/runbooks" | jq '.Items | map({
    Name, Description, EnvironmentScope,
    PublishedRunbookSnapshotId, RunRetentionPolicy
  })'
```

Record runbook names and sanitized descriptions only as needed to identify
whether the queried project has runbooks for rollback, restart, secret
rotation, database maintenance, or disaster recovery. Absence within this
queried scope is a source fact, not a finding.

### 1.8 Variables (Schema Only — No Values)

```bash
octopus_get "$OCTOPUS_URL/api/{space}/variables/{variableSetId}" \
  | jq '{
      Variables: .Variables | map({
        Name,
        IsSensitive,
        Scope: (.Scope | keys)
      })
    }'
```

**Strict rule: collect only variable names when strictly necessary, sensitivity flag, and scope. Never collect or persist `.Value`, including values marked non-sensitive.** Do not infer sensitivity from a name, and do not infer value contents from schema. Record schema observations only; any later inspection of a suspected unsafe value requires separate safe verification.

### 1.9 Targets / Deployment Surface

```bash
octopus_get "$OCTOPUS_URL/api/{space}/machines/all" \
  | jq 'map({Name, Status, HealthStatus, Roles, EnvironmentIds, IsDisabled, Endpoint: .Endpoint.CommunicationStyle})'
```

Capture a sanitized deployment-surface type, status/health state, and
environment association. Do not retain sensitive hostnames, account identifiers,
or machine details. Whether disabled or unhealthy targets are in the active
path is strategist analysis and must be supported by scoped observations.

### 1.10 Subscriptions / Notifications

```bash
octopus_get "$OCTOPUS_URL/api/{space}/subscriptions/all" | jq 'map({Name, Type, EventNotificationSubscription})'
```

Record configured subscription/event types and sanitized destination categories
only (for example, chat, email, incident management); omit recipient addresses,
webhooks, and payloads. Whether alert coverage is sufficient is strategist
analysis.

---

## Tier 2: Config-as-Code Repo

Triggered when Tier 1 isn't available **and** any matched project has `IsVersionControlled: true`, OR the user points at a CaC repo path.

Look for these files in the target repo (or a sibling repo if the user provides one):

```
.octopus/<project-slug>/deployment_process.ocl
.octopus/<project-slug>/variables.ocl
.octopus/<project-slug>/deployment_settings.ocl
.octopus/<project-slug>/runbooks/*.ocl
.octopus/<project-slug>/channels/*.ocl
```

OCL is HCL-flavored. Read each applicable file once and record the defined
state using sanitized facts matching the relevant Tier 1 observation
boundaries (deployment process, channels, runbooks, and variable schema only).
Preserve file path and line/source locator in each record. Never persist
variable values.

If multiple candidate CaC project directories or sibling-repository paths are
plausible and the approved scope does not resolve them, do not choose or inspect
one by inference. Record the affected source inventory as `BLOCKED`, create an
`UNVERIFIED` record, and return the structured clarification handoff below to
the strategist/launcher. The strategist/launcher asks the user and invokes a
targeted collector continuation with the sanitized answer. In headless or
skip-interview mode, leave it blocked and needing clarification.

Note that CaC files give you the **defined** state but not the **observed** state — you won't see deploy frequency, failure rate, or current target health from CaC alone. Record these metric source families as unavailable in Tier 2 in the evidence inventory, with the bounded reason; do not infer them from configuration.

---

## Tier 3: Structured Questionnaire (Fallback)

Triggered when both Tier 1 and Tier 2 are unavailable. The collector does not ask the user. It records the questionnaire source inventory as `BLOCKED` (or `SKIPPED` when explicitly skipped), adds an `UNVERIFIED` evidence record for each unresolved question, and returns a structured question handoff to the strategist/launcher. The strategist/launcher asks the questions via `AskUserQuestion` in batches of 3–4, then invokes a targeted collector continuation with the sanitized answers. Record each supplied answer as a `USER-REPORTED` source observation in `evidence.md`, with the exact question as the source reference and a concise paraphrase of the answer. If the run is headless or interview is skipped, leave the blocker and mark it as needing clarification; do not infer an answer or mark the source complete.

For each pending clarification, the collector handoff must include:

```yaml
clarification:
  source_family: octopus-project-selection | octopus-questionnaire
  inventory_status: BLOCKED | SKIPPED
  evidence_status: UNVERIFIED
  exact_question: <one exact user-facing question>
  context: <sanitized candidates or bounded reason the fact is unavailable>
  continuation_scope: <specific source/question IDs to collect after answer>
  headless_or_skipped: <true|false>
```

### Batch A — Project & Lifecycle

1. **Project structure.** "Is this repo deployed as one Octopus project, or split (e.g., separate API and webapp projects)? What are their names?"
2. **Environments.** "What environments exist in the lifecycle, in order? (e.g., dev → stage → prod)"
3. **Auto-promotion.** "Which environments auto-deploy on a successful CI build, and which require a human to click 'Deploy'?" (multi-select per env)
4. **Channels.** "Do you use Octopus channels (e.g., default + hotfix), or one channel for everything?"

### Batch B — Deployment Process & Safety

5. **Deploy strategy.** "Per environment: rolling, blue-green, canary, or stop-and-replace?"
6. **Manual interventions.** "Are there any manual approval / sign-off steps in the deployment process? Where, and who approves?"
7. **Rollback.** "How do you roll back a bad deploy? Is it (a) re-deploy a previous Octopus release, (b) a runbook, (c) a manual scripted rollback, or (d) we haven't needed to and aren't sure?"
8. **Post-deploy verification.** "Does the deploy process include a smoke/health check step that fails the deploy if it fails? Or is verification done outside Octopus?"

### Batch C — Operational Posture

9. **Frequency.** "Roughly how often does code reach prod? (multiple per day / daily / weekly / less)"
10. **Recent failures.** "In the last 90 days, how many prod deploys failed or had to be rolled back? (rough count is fine)"
11. **MTTR.** "When a prod deploy fails, what's the typical time to recovery — minutes, hours, half a day?"
12. **Notifications.** "Where do deploy failures alert? (Slack channel, email list, PagerDuty, nowhere)"
13. **Runbooks.** "Do you use Octopus runbooks for ops tasks (rollback, restart, secret rotation, DB maintenance)? Which ones exist?"

### Batch D — Trust & Gaps

14. **Drift.** "Do you trust that the Octopus deployment process matches what's actually running, or has it drifted?"
15. **Bus factor.** "How many people on the team can confidently modify the Octopus deployment process?"
16. **Pain.** "What's the single most painful thing about the current Octopus setup?" (free text)

---

## Output: source evidence in `evidence.md`

Write all collected Octopus observations and source inventory rows to
`<target-repo>/cd-discovery/evidence.md`, following the canonical structure and
`SRC-` schema in `EVIDENCE-LEDGER.md`. Do not emit a weave map, dimension-tagged
findings, maturity levels, severity, or recommendations. Preserve only the raw
evidence minimum needed for attributable analysis: summarize configuration
states, bounded counts, and sanitized step/action facts instead of copying full
API responses, task error messages, alert bodies, or unnecessary identifiers.

For every source family attempted, record inventory status (`COMPLETE`,
`PARTIAL`, `BLOCKED`, `SKIPPED`, `NOT_APPLICABLE`, or `MISSING`), scope,
sanitized access context, and limitation/reason. User answers are `USER-REPORTED`
evidence records, not inventory statuses. Each observation cites
the precise resource/file/question and relevant filters, includes access
context, and states its scope. Metrics must explicitly state time window,
population, and calculation method, including numerator/denominator and
sampling limits. Do not infer metrics from CaC or unobserved data.

Example source observation (illustrative; use actual observed values and date):

```markdown
#### SRC-octopus-prod-deployment-outcomes — production deployment outcomes
- Status: VERIFIED
- Freshness: CURRENT
- Scope: sanitized project alias `project-a`; production; latest-50 deployment sample as of 2026-11-13 (not a fixed calendar window); 20 completed deployments; count `FailureEncountered: true`; fraction = 3 / 20 completed deployments.
- Source: api — deployment list filtered by the selected project, `take=50`; task state fetched for each returned deployment.
- Observed: 2026-11-13
- Access context: Octopus Tier 1 API, sanitized selected-space alias, read access.
- Supports: true
- Limitations: Limited to the returned latest-50 sample; only completed production deployments were included in the denominator.
- Related IDs: none
```

### Collection ownership and handoff

`cd-evidence-collector` performs each applicable API request, CaC inspection,
or questionnaire capture once. Specialists receive only relevant sanitized
observations and `SRC-` references from `evidence.md`; they do not call the
Octopus API, inspect already-collected CaC files again, or broaden collection.
If needed evidence is absent, return it to the strategist as a structured
clarification handoff. The strategist/launcher asks the user and may invoke a
targeted collector continuation with the sanitized answer; the collector does
not ask the user. A headless or skip-interview run leaves the source `BLOCKED`
or `SKIPPED` and the evidence `UNVERIFIED`, with the exact question marked as
needing clarification. Specialists do not query sources independently. After specialist results return,
the strategist validates and appends the separate `CI-`, `REL-`, and `FLOW-`
analyst findings under `## Analyst findings` in the same document, citing source
IDs and reconciling duplicate claims.

### Evidence routing boundaries

The collector records source facts once. When useful, the strategist may route
the already-collected observations to specialists within these boundaries:

| Collected Octopus evidence | Optional evidence-only agent | Routing boundary |
|---|---|---|
| Deployment process, lifecycle phases, approval/manual-intervention gates, channels that constrain release eligibility, post-deploy checks, runbooks, promotion and recovery controls | `release-safety-recovery` (`REL-` records) | Release/process/lifecycle/runbook/promotion/recovery evidence after artifact handoff. |
| Deployment and task history, actual outcomes, and measured frequency/duration/failure/recovery intervals | `delivery-metrics-flow` (`FLOW-` records) | Observed history and outcomes only; scope population, time bounds, calculation, and limitations. |
| CI/build/package/artifact details | `ci-artifact-integrity` (`CI-` records) | Only when collected Octopus evidence directly establishes the producer-side artifact handoff or its identity; do not duplicate CI repository scans. |

### Preserved synthesis nuance

The following are strategist interpretation rules, not collector output.
Build-once-promote-the-same-artifact is the load-bearing CD principle. When
evidence establishes a single build per commit, an immutable tag promoted
unchanged through environments, and a deploy step that reads the build tag,
the strategist may name it as a Strength to Protect. Rebuilding per
environment, allowing a mutable tag to reach production, or retagging at deploy
is a serious Deployment concern regardless of other strengths. Build-once with
config swapped at deploy (identical artifact bytes; runtime configuration
changed by deployment) is acceptable and must retain that nuance. The evidence
records only observed facts; it does not label severity or strength.

### Authentication and sensitive-data rules (preserved)

- Tier 1 API: supply `OCTOPUS_API_KEY` only via approved runtime secret or
  environment injection, and pass it to curl through stdin configuration, never
  process arguments. Never type it into shell history, prompts, files, terminal
  output, `evidence.md`, memory, or reports. If an attempt fails, record only
  the failure mode (4xx, 5xx, network), never the key.
- Variable collection is schema-only. Never collect or persist `.Value`, even
  transiently in output; record names only when necessary, sensitivity flag,
  and scope. Do not expose secret-like variable identifiers unnecessarily.
- Never store alert payloads, task error messages, sensitive identifiers, or
  unnecessary deployment/user data. Use aggregate counts and narrow sanitized
  references.

---

## Quality Gate

Before declaring Octopus source collection complete, verify:
- ✅ Every applicable source family recorded in `<target-repo>/cd-discovery/evidence.md` inventory with status, attempted scope, sanitized access context, and limitation/reason
- ✅ Source observations use stable `SRC-` IDs and the `EVIDENCE-LEDGER.md` source-record schema
- ✅ Selected space/project and selection basis recorded without exposing unnecessary identifiers
- ✅ Lifecycle phase order, promotion settings, and deployment-process actions recorded as scoped source facts when accessible
- ✅ Metrics record the time window, population, calculation method, numerator/denominator, and sample limits; CaC-only gaps are explicit
- ✅ Specialist handoff uses only existing sanitized observations and `SRC-` IDs; no source is queried or inspected twice
- ❌ No API key, secret/sensitive variable value, full task error, alert payload, or unnecessary sensitive identifier is present in `evidence.md` or agent memory
- ❌ No final maturity, severity, recommendation, or dimension-tagged weave map is emitted by the collector
