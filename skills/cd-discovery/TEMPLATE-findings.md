# CD Discovery — Findings

> Generated: {date} | Repository: {repo_name}
>
> See also: [summary.md](./summary.md){if suggestions exist: " | [suggestions.md](./suggestions.md)"}

> Per-dimension deep dive. GitHub and Octopus evidence is woven into the relevant dimension sections — there are no dedicated "GitHub Repository Posture" or "Deployment Orchestrator" sections. Discovery source for sub-playbook items is noted inline with the evidence (e.g., `[evidence from gh CLI Tier 1, scanned 2026-05-26]`).

{repeat this block per dimension}

## {Dimension Name}

**Estimated Level:** L{n} — {level description}
**Confidence:** {HIGH/MED/LOW} — {why this confidence level}

**Artifacts Found:**
- `{path/to/file}` — {what it does} [{FOUND}]
- `{path/to/file:line}` — {specific finding} [{PARTIAL}]
- `{gh:repo-setting or octopus:project-step}` — {sub-playbook evidence woven in} [evidence from {source}, scanned {date}]

**Gaps Identified:**
- {gap description} [{MISSING}]

**User Context:**
- Q: {question asked}
- A: {user's answer}

{end repeat}

---

## Revision history

> Append-only audit trail for this file. Each entry: `### YYYY-MM-DD — <event>`.

{revision entries appended here on update}
