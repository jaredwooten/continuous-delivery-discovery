# Octopus Deploy Discovery Sub-Playbook

Use when the repository deploys through Octopus Deploy and the orchestrator is not visible from the codebase alone. This is the collector's single Octopus protocol; write sanitized source observations to `evidence.md` under `EVIDENCE-LEDGER.md`.

The sub-playbook tries three sources in order. Stop at the first one that succeeds — do not double-collect.

Run each applicable API, CaC, or questionnaire collection once. Keep only sanitized evidence-minimum facts; never save raw responses or intermediate payloads. Specialists consume collected evidence without repeating queries; the strategist handles findings and synthesis.

```
Tier 1: REST API (highest fidelity)
   ↓ (if no URL/key, or auth fails)
Tier 2: Config-as-Code repo (medium fidelity)
   ↓ (if no CaC repo found)
Tier 3: Structured questionnaire (lowest fidelity, human memory)
```

## Inputs

Inputs follow flag → environment → omit, except the API key, which is supplied only through approved runtime secret/environment injection:

| Input | Flag | Env var | Required |
|-------|------|---------|----------|
| Octopus server URL | `--octopus-url` | `OCTOPUS_URL` | Tier 1 only |
| API key | **No command-line flag** | `OCTOPUS_API_KEY` | Tier 1 only |
| Space ID or name | `--octopus-space` | `OCTOPUS_SPACE` | Tier 1 only |
| Project name(s) | `--octopus-project` | `OCTOPUS_PROJECT` | optional filter |

Never accept, type, or persist the API key in flags, prompts, commands, history, files, or output. Supply it to curl only via stdin config (never argv, including `-H`); on failure record only the mode (4xx, 5xx, network).

---

## Tier 1: REST API Scan

Use this helper for every Tier 1 request. The key must already be in the environment via approved secret injection; do not export it in a command. Do not enable shell tracing or curl verbose/trace output. Endpoints use `${OCTOPUS_URL}/api`; replace `{space}` with the resolved space ID.

```bash
octopus_get() {
  local url=$1
  curl --silent --show-error --config - <<EOF
header = "X-Octopus-ApiKey: ${OCTOPUS_API_KEY}"
url = "${url}"
EOF
}
```

Pass the URL to `octopus_get`; do not add a key header to its invocation.

### 1.1 Resolve Space

```bash
octopus_get "$OCTOPUS_URL/api/spaces/all" | jq '.[] | {Id, Name, IsDefault}'
```

Use a matching `Id`/`Name`; otherwise use the default and record that assumption.

### 1.2 Locate the Project(s)

```bash
octopus_get "$OCTOPUS_URL/api/{space}/projects/all" | jq '.[] | {Id, Name, Slug, LifecycleId, IsDisabled, IsVersionControlled}'
```

Match `--octopus-project` exactly or by substring. Without it, repository-name matching only identifies candidates. If ambiguous, do not choose or interview: mark inventory `BLOCKED`, record an `UNVERIFIED` selection with exact candidates and a generated question ("Which project should I inspect: <candidate list>?") in the handoff, and stop project-specific collection. The strategist/launcher asks and starts a targeted continuation; record the selected project and basis afterward.

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

Record whether there is a manual intervention before production, explicit lifecycle rollback, or `Octopus.Script` action. For scripts, retain only a concise sanitized operation description, never contents with credentials, values, or unrelated details.

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

Preserve the selected lifecycle/phase scope for automatic deployment targets.

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

For each environment, record deployment count/frequency; calculate failure rate as `FailureEncountered: true / total deployments` and mean duration from task start/completion. State calendar window or latest-N sample, population/exclusions, numerator/denominator; never label a latest-N sample a 30/90-day rate. Label failure-to-next-success intervals as recovery proxies. Omit individual `DeployedBy` names. No DORA classification.

### 1.7 Runbooks (Operational Playbook Coverage)

```bash
octopus_get "$OCTOPUS_URL/api/{space}/projects/{id}/runbooks" | jq '.Items | map({
    Name, Description, EnvironmentScope,
    PublishedRunbookSnapshotId, RunRetentionPolicy
  })'
```

Record names and concise sanitized descriptions only as needed to identify rollback, restart, secret rotation, database maintenance, or disaster-recovery coverage. Absence in queried scope is a source fact, not a finding.

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

Collect only necessary variable names, sensitivity flags, and scope. Never read or persist `.Value`, even for non-sensitive variables; do not infer sensitivity or contents from names/schema. Any later suspected-unsafe-value check requires separate safe verification.

### 1.9 Targets / Deployment Surface

```bash
octopus_get "$OCTOPUS_URL/api/{space}/machines/all" \
  | jq 'map({Name, Status, HealthStatus, Roles, EnvironmentIds, IsDisabled, Endpoint: .Endpoint.CommunicationStyle})'
```

Capture sanitized surface type, status/health, and environment association; omit hostnames, account IDs, and machine details. Strategist analysis determines whether disabled/unhealthy targets are active, supported by scoped evidence.

### 1.10 Subscriptions / Notifications

```bash
octopus_get "$OCTOPUS_URL/api/{space}/subscriptions/all" | jq 'map({Name, Type, EventNotificationSubscription})'
```

Record subscription/event types and sanitized destination categories only (e.g. chat, email, incident management); omit addresses, webhooks, and payloads. Alert-coverage assessment belongs to strategist synthesis.

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

OCL is HCL-flavored. Read each applicable file once; record sanitized defined state for deployment process, channels, runbooks, and variable schema, with file/line locators. Never persist variable values.

If multiple CaC directories or sibling repos are plausible, do not infer which to inspect. Mark inventory `BLOCKED`, create an `UNVERIFIED` record, and hand off the exact question ("Which CaC project directory or sibling repository should I inspect: <candidate list>?"). The strategist/launcher asks and invokes a targeted continuation; headless/skip-interview stays blocked.

CaC gives defined, not observed, state. Record deployment frequency, failure rate, and current target health as unavailable in Tier 2; never infer them from configuration.

---

## Tier 3: Structured Questionnaire (Fallback)

When Tier 1 and 2 are unavailable, do not interview. Mark the questionnaire `BLOCKED` (or `SKIPPED` if opted out), add `UNVERIFIED` records, and return exact questions in the handoff. The strategist/launcher asks in batches of 3–4 and invokes targeted continuation. Record answers as concise `USER-REPORTED` observations sourced to the exact question. Headless/skip-interview stays unresolved; do not infer or mark complete.

For each clarification, return:

```yaml
clarification:
  source_family: octopus-project-selection | octopus-cac-selection | octopus-questionnaire
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

Write sanitized Octopus source observations and inventory to `evidence.md` under `EVIDENCE-LEDGER.md`. Cite precise resource/file/question and filters; include scope, access context, bounds, and limitations. Metrics state time/sample window, population, calculation, numerator/denominator, and sample limits. Do not infer metrics from CaC or unobserved data, or retain full API responses, task errors, alert bodies, or unnecessary identifiers.

### Interpretation boundary

Route only relevant collected evidence: deployment/lifecycle/runbook controls to release analysis, observed deployment/task metrics to flow analysis, and direct producer-side artifact handoff to CI analysis. Analysts consume evidence and IDs; they do not query sources. Build-once/promote unchanged is a strength; per-environment rebuilds, mutable production tags, or retagging are serious concerns. Identical artifact bytes with runtime config swapped at deploy are acceptable with that qualification. These are strategist interpretations, not collection labels.
