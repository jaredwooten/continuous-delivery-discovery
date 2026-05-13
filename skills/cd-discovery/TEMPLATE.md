# CD Discovery Report

> Generated: {date} | Repository: {repo_name}

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

## Detailed Findings

{repeat this block per dimension}

### {Dimension Name}

**Estimated Level:** L{n} — {level description}
**Confidence:** {HIGH/MED/LOW} — {why this confidence level}

**Artifacts Found:**
- `{path/to/file}` — {what it does} [{FOUND}]
- `{path/to/file:line}` — {specific finding} [{PARTIAL}]

**Gaps Identified:**
- {gap description} [{MISSING}]

**User Context:**
- Q: {question asked}
- A: {user's answer}

{end repeat}

## Deployment Orchestrator

> Omit this section entirely if no external orchestrator is in use. Otherwise populate using the relevant sub-playbook (e.g. `OCTOPUS-DISCOVERY.md`).

**Orchestrator:** {Octopus Deploy | Spinnaker | Argo CD | Harness | other}
**Discovery tier:** {API | CaC | Questionnaire | N/A}
**Confidence:** {HIGH | MED | LOW}

**Project(s) discovered:**
- {project name + slug}

**Lifecycle / Promotion**
- Phase order: {dev → stage → prod}
- Auto-promote map: {env: yes/no per env}
- Retention: {N releases / N days}

**Deployment Process Summary**
| Step | Action Type | Env Scope | Notes |
|------|-------------|-----------|-------|
| {n. name} | {action type} | {envs} | {manual gate? rollback? smoke?} |

**Operational Metrics** *(API tier only — otherwise mark as `[USER-REPORTED]` or `[UNAVAILABLE]`)*
- Deploy frequency per env: {…}
- Change failure rate: {…}
- Mean deploy duration: {…}
- MTTR proxy: {…}

**Runbooks**
- {present runbooks}
- {notable absences}

**Variables (schema only — no values)**
- {count, sensitive count, mismatches}

**Notifications**
- {channels and gaps}

**Findings**
- [{HIGH/MED/LOW}] {finding with file/step reference}

**Cross-stitch into capability matrix**
- Deployment Automation: {old level} → {new level} because {reason}
- Release Process: {old level} → {new level} because {reason}
- Observability: {old level} → {new level} because {reason}

## GitHub Repository Posture

> Omit this section entirely if the repo is not on GitHub or if `--skip-github` was set.
> Populate using `GH-DISCOVERY.md`.

**Discovery source:** {gh CLI REST API (Tier 1) | Questionnaire (Tier 2) | N/A}
**Confidence:** {HIGH | MED | LOW}
**Scanned:** {YYYY-MM-DD}
**Authenticated as:** {gh user} ({viewerPermission})

### Branch protection and merge gating

| Branch | Protected | Required reviews | Required status checks | Stale dismissal | Code owners | Admin enforced |
|--------|-----------|------------------|------------------------|-----------------|-------------|----------------|
| {default} | … | … | … | … | … | … |
| {secondary} | … | … | … | … | … | … |

### Repository-level security feature state

| Feature | State |
|---------|-------|
| GitHub Advanced Security | … |
| Secret scanning (+push protection, AI detection, validity, non-provider) | … |
| Code scanning default setup (CodeQL) | … (languages: …) |
| Dependabot vulnerability alerts | … |
| Dependabot security updates (auto-PR lane) | … |
| Default `GITHUB_TOKEN` permissions | … |

### Open security alert backlog

| Source | Critical | High | Medium | Low | Total |
|--------|---------:|-----:|-------:|----:|------:|
| Dependabot | … | … | … | … | … |
| Code scanning | … | … | … | … | … |
| Secret scanning | — | — | — | — | … |
| **Combined** | | | | | … |

> Counts only. Alert bodies are never copied into this report.

### Workflow execution reality (last {N} runs)

| Workflow | Total | Success | Failure | Failure rate |
|----------|------:|--------:|--------:|-------------:|
| … | … | … | … | … |

**Workflows defined but not running:** {list, with last-success date when known}

### PR cadence (last 100 merged PRs)

- Base-branch distribution: …
- Lead time (open → merged): p50 = …, p90 = …, p99 = …, mean = …
- Documentation drift: {none | CLAUDE.md says PRs target X but reality is Y}

### Dependabot PR queue

- {N} open Dependabot PRs

### CODEOWNERS

- {present at path | missing}

### Cross-stitch into capability matrix

> **Framing rule:** missing branch protection on a default branch is only a finding when feedback loops are weak elsewhere. When downgrading Build & CI on branch-protection state, explicitly cite the observed Observability/Testing/Deployment state in the reason column.

- Build & CI: {old level} → {new level} because {reason — cite feedback-loop context}
- Testing: {old level} → {new level} because {reason}
- Security: {old level} → {new level} because {reason}
- Release Process: {old level} → {new level} because {reason — note documentation drift if any}

## Anti-Patterns Detected

| Anti-Pattern | Location | Impact |
|-------------|----------|--------|
| {pattern name} | `{file:line}` | {why this matters} |

## Recommended Next Steps

1. {highest-leverage quick win}
2. {second priority item}
3. {third priority item}

---

*For a full assessment with phased roadmap, run `/cd-discovery --assess`.*
