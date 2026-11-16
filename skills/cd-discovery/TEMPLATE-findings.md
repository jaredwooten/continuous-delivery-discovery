# CD Discovery — Findings

> Generated: {date} | Repository: {repo_name}
>
> See also: [summary.md](./summary.md) | [evidence.md](./evidence.md){if suggestions exist: " | [suggestions.md](./suggestions.md)"}

> Per-dimension deep dive. GitHub and Octopus evidence is woven into the relevant dimension sections — there are no dedicated "GitHub Repository Posture" or "Deployment Orchestrator" sections. Discovery source for sub-playbook items is noted inline with the evidence (e.g., `[evidence from gh CLI Tier 1, scanned 2026-05-26]`).
>
> Stable finding IDs can be cited across dimensions. Use this file for report presentation and `evidence.md` as the canonical source and analyst ledger. Cite relevant `SRC-` source-observation IDs alongside analyst finding IDs; retain stable IDs when revisiting the same claim. Record status, confidence and its reason, scope, source attribution, and limitations so evidence provenance and boundaries remain auditable.

{repeat this block per dimension}

## {Dimension Name}

**Estimated Level:** L{n} — {level description}
**Confidence:** {HIGH/MED/LOW} — {why this confidence level}

**Findings:**
- **ID:** `{stable-id}` (for example, `CI-required-checks-default-branch`, `REL-production-approval-gate`, or `FLOW-deploy-frequency-production`)
  - **Claim:** {one concise, atomic statement of what evidence establishes or fails to establish}
  - **Owner:** {one worker or strategist identifier responsible for this complete finding record}
  - **Status:** {VERIFIED | PARTIAL | MISSING | USER-REPORTED | UNVERIFIED | NOT-APPLICABLE | BLOCKED | CONFLICTED}
  - **Confidence:** {HIGH | MED | LOW} — {confidence reason; evidence quality/directness, not impact}
  - **Scope:** {repository/system, branch/environment/component, filters; for metrics include time window, population, and calculation}
  - **Sources:**
    - `{SRC-claim-key}` — {kind}: `{precise locator or resource/query}` — observed {YYYY-MM-DD}; {access context}; supports: {true/false}
  - **Limitations:** {search bounds, unavailable coverage, sampling, ambiguity, freshness, inference, or `None known` after checking}
  - **Related IDs:** {stable IDs, or `[]`}

**Artifacts Found:**
- `{path/to/file}` — {what it does} [{FOUND}]
- `{path/to/file:line}` — {specific finding} [{PARTIAL}]
- `{gh:repo-setting or octopus:project-step}` — {sub-playbook evidence woven in} [evidence from {source}, scanned {date}] [finding: `{stable-id}`]

**Gaps Identified:**
- {gap description} [{MISSING}] [finding: `{stable-id}`]

**User Context:**
- Q: {question asked}
- A: {user's answer}

**Evidence ledger references:**
- Source evidence: `{SRC-claim-key}` — {brief source observation; see [evidence.md](./evidence.md)}
- Analyst finding: `{CI-/REL-/FLOW-claim-key}` — {brief claim or cross-dimension reference; retain the ID when citing this finding elsewhere}

{end repeat}

---

## Revision history

> Append-only audit trail for this file. Each entry: `### YYYY-MM-DD — <event>`.

{revision entries appended here on update}
