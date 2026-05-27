# Octopus Deploy Discovery Sub-Playbook

Use this sub-playbook when the repository is deployed via **Octopus Deploy** and the orchestrator is not visible from the codebase alone. It produces a **weave map** — a structured list of evidence items tagged with discovery tier and target dimension(s) — that gets folded into the `findings.md` file for the strategist to integrate into the capability matrix.

The sub-playbook tries three sources in order. Stop at the first one that succeeds — do not double-collect.

```
Tier 1: REST API (highest fidelity)
   ↓ (if no URL/key, or auth fails)
Tier 2: Config-as-Code repo (medium fidelity)
   ↓ (if no CaC repo found)
Tier 3: Structured questionnaire (lowest fidelity, human memory)
```

## Inputs

The skill launcher passes any of the following (in priority order: flag → env var → omit):

| Input | Flag | Env var | Required |
|-------|------|---------|----------|
| Octopus server URL | `--octopus-url` | `OCTOPUS_URL` | Tier 1 only |
| API key | `--octopus-api-key` | `OCTOPUS_API_KEY` | Tier 1 only |
| Space ID or name | `--octopus-space` | `OCTOPUS_SPACE` | Tier 1 only |
| Project name(s) | `--octopus-project` | `OCTOPUS_PROJECT` | optional filter |

**Never echo the API key to the terminal, the report, or memory.** Pass it via the `X-Octopus-ApiKey` header only. If a Tier 1 attempt fails, log the failure mode (4xx, 5xx, network) without the key value.

---

## Tier 1: REST API Scan

Use `curl` (already available) with the API key in the `X-Octopus-ApiKey` header. All endpoints below are relative to `${OCTOPUS_URL}/api`. Replace `{space}` with the resolved space ID (e.g. `Spaces-1`).

### 1.1 Resolve Space

```bash
curl -sS -H "X-Octopus-ApiKey: $OCTOPUS_API_KEY" \
  "$OCTOPUS_URL/api/spaces/all" | jq '.[] | {Id, Name, IsDefault}'
```

If `--octopus-space` matches an `Id` or `Name`, use that. Otherwise pick the default space and note the assumption in the report.

### 1.2 Locate the Project(s)

```bash
curl -sS -H "X-Octopus-ApiKey: $OCTOPUS_API_KEY" \
  "$OCTOPUS_URL/api/{space}/projects/all" | jq '.[] | {Id, Name, Slug, LifecycleId, IsDisabled, IsVersionControlled}'
```

Match against `--octopus-project` (substring or exact). If not provided, infer the project(s) by repository name match (e.g., `mi-portal` → projects whose slug or name contains `market-insights`, `mi-portal`, `mi-api`, `mi-web`). List candidates and confirm with the user via `AskUserQuestion` if ambiguous.

For each matched project, capture:
- `Id`, `Name`, `Slug`, `IsDisabled`, `IsVersionControlled` (CaC enabled?)
- `LifecycleId`, `ProjectGroupId`
- `DeploymentProcessId`, `VariableSetId`

### 1.3 Deployment Process

```bash
curl -sS -H "X-Octopus-ApiKey: $OCTOPUS_API_KEY" \
  "$OCTOPUS_URL/api/{space}/deploymentprocesses/{id}" | jq '{
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

Flag if found:
- No manual-intervention before prod (good or bad depending on team's intent — surface for discussion)
- Deploy step with no rollback step in the same lifecycle
- `Octopus.Script` steps doing custom work (write down what they do — these are where logic hides)

### 1.4 Lifecycle & Promotion Rules

```bash
curl -sS -H "X-Octopus-ApiKey: $OCTOPUS_API_KEY" \
  "$OCTOPUS_URL/api/{space}/lifecycles/{id}" | jq '{
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

This answers the big question from the assessment: "is dev → stage → prod automated or manual?" The `AutomaticDeploymentTargets` list is the authoritative answer.

### 1.5 Channels & Versioning Rules

```bash
curl -sS -H "X-Octopus-ApiKey: $OCTOPUS_API_KEY" \
  "$OCTOPUS_URL/api/{space}/projects/{id}/channels" | jq '.Items | map({
    Name, IsDefault, LifecycleId,
    Rules: .Rules | map({Tag, VersionRange, ActionPackages})
  })'
```

Note channels (e.g. `default`, `hotfix`, `release-candidate`) and their version-range gates. Channels often map to git branches.

### 1.6 Recent Deployments — Frequency & Failure Rate

```bash
# Last 50 deployments for the project
curl -sS -H "X-Octopus-ApiKey: $OCTOPUS_API_KEY" \
  "$OCTOPUS_URL/api/{space}/deployments?projects={projectId}&take=50" \
  | jq '.Items | map({
      Created, EnvironmentId, ReleaseId, TaskId,
      DeployedBy, FailureEncountered: .FailureEncountered
    })'

# Resolve task state per deployment for State + Duration
curl -sS -H "X-Octopus-ApiKey: $OCTOPUS_API_KEY" \
  "$OCTOPUS_URL/api/{space}/tasks/{taskId}" \
  | jq '{State, FinishedSuccessfully, StartTime, CompletedTime, ErrorMessage}'
```

Compute:
- **Deploy frequency per environment** (count by env over the last 30/90 days) — DORA metric #1
- **Change failure rate** — `FailureEncountered: true` count / total — DORA metric #3
- **Mean deploy duration** per env — pipeline efficiency
- **MTTR proxy** — for failed deployments, time until the next successful deployment to the same env — DORA metric #4
- **Who deploys** — distribution of `DeployedBy` (a single name = bus factor risk; many names = healthy)

### 1.7 Runbooks (Operational Playbook Coverage)

```bash
curl -sS -H "X-Octopus-ApiKey: $OCTOPUS_API_KEY" \
  "$OCTOPUS_URL/api/{space}/projects/{id}/runbooks" | jq '.Items | map({
    Name, Description, EnvironmentScope,
    PublishedRunbookSnapshotId, RunRetentionPolicy
  })'
```

Note runbooks for: rollback, restart, secret rotation, DB maintenance, disaster recovery. **Absence of a rollback runbook is a finding.**

### 1.8 Variables (Schema Only — No Values)

```bash
curl -sS -H "X-Octopus-ApiKey: $OCTOPUS_API_KEY" \
  "$OCTOPUS_URL/api/{space}/variables/{variableSetId}" \
  | jq '{
      Variables: .Variables | map({
        Name,
        IsSensitive,
        Scope: (.Scope | keys),
        Source: (if .Value == null and .IsSensitive then "secret" else "config" end)
      })
    }'
```

**Strict rule: only collect variable names, sensitivity flag, and scope. Never collect `.Value` for sensitive variables, and avoid copying any value into the report.** Look for:
- Sensitive variables that aren't flagged sensitive (Name suggests secret, `IsSensitive: false`)
- Per-environment overrides for the same variable (signals env divergence)
- Connection strings hardcoded in non-sensitive variables

### 1.9 Targets / Deployment Surface

```bash
curl -sS -H "X-Octopus-ApiKey: $OCTOPUS_API_KEY" \
  "$OCTOPUS_URL/api/{space}/machines/all" \
  | jq 'map({Name, Status, HealthStatus, Roles, EnvironmentIds, IsDisabled, Endpoint: .Endpoint.CommunicationStyle})'
```

Capture deployment surface (ECS clusters, Tentacles, SSH targets, k8s clusters, AWS accounts), their health, and which environments they belong to. Disabled or unhealthy targets in the active path are findings.

### 1.10 Subscriptions / Notifications

```bash
curl -sS -H "X-Octopus-ApiKey: $OCTOPUS_API_KEY" \
  "$OCTOPUS_URL/api/{space}/subscriptions/all" | jq 'map({Name, Type, EventNotificationSubscription})'
```

Note: are deploy failures alerted to Slack/email/PagerDuty? Silent failures are a maturity gap.

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

OCL is HCL-flavored. Read each file and extract the same structured data as Tier 1.6 (deployment process), 1.5 (channels), 1.7 (runbooks), 1.8 (variable schema only).

Note that CaC files give you the **defined** state but not the **observed** state — you won't see deploy frequency, failure rate, or current target health from CaC alone. Flag in the report that those metrics are unavailable in Tier 2.

---

## Tier 3: Structured Questionnaire (Fallback)

Triggered when both Tier 1 and Tier 2 are unavailable. Ask via `AskUserQuestion`. Group into batches of 3-4 to avoid fatigue. Tag every answer with `[USER-REPORTED]` in the report so confidence is visible.

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

---

## Quality Gate

Before declaring the Octopus discovery complete, verify:
- ✅ Discovery tier recorded in the output (API / CaC / Questionnaire)
- ✅ At least one project located and named
- ✅ Lifecycle phase order + auto-promote map captured
- ✅ Deployment process steps enumerated with action types
- ✅ Manual intervention steps surfaced
- ✅ Rollback story captured (runbook, redeploy, or "none")
- ✅ Findings cross-referenced into the main capability matrix
- ❌ No API key, secret value, or sensitive variable value present anywhere in `CD-DISCOVERY.md` or agent memory
