# CD Discovery — Suggestions

> Generated: {date} | Repository: {repo_name}
>
> See also: [summary.md](./summary.md) | [findings.md](./findings.md)

## How to read this file

This is a resource, not a plan. The suggestions below identify gaps surfaced in `findings.md` and describe what improving each would unlock alongside the cost. Engineers own sequencing decisions — team capacity, parallel work, risk appetite, and stakeholder priorities are not visible to the agent that wrote this file.

Each suggestion uses the same structure:

- **Gap** — what was found
- **What improving unlocks** — the concrete capability or risk reduction
- **Cost / disruption** — what the work requires and what it makes harder

Sequence guidance is expressed as a dependency map ("X unlocks Y"). A dependency edge is a constraint on order, not a schedule. Engineers may legitimately sequence differently based on context.

No time-duration estimates are included. The team owns sizing and scheduling.

## Suggestions

{repeat per suggestion}

### {n}. {Short title — the action, framed as a consideration}

- **Gap:** {what was observed in findings.md, with file:line reference where applicable}
- **What improving unlocks:** {concrete capability — e.g., "rollback in under 5 minutes instead of the current ~45", "blocks the 'works on my machine' class of incident", etc.}
- **Cost / disruption:** {specific cost — e.g., "introduces a new tool the team must learn", "requires changes to N existing pipelines", "adds 2-3 minutes to every CI run"}
- **Depends on:** {list of suggestion numbers this depends on, or "none"}
- **Unlocks:** {list of suggestion numbers this enables, or "none"}

{end repeat}

## Dependency map

```
{suggestion 1} → {suggestion 3} → {suggestion 5}
              ↘
{suggestion 2} → {suggestion 4}
```

> Edges indicate "X unlocks Y" — Y can be done without X, but with reduced effect or higher risk. The team owns final sequencing.

---

## Revision history

> Append-only audit trail for this file. Each entry: `### YYYY-MM-DD — <event>`.

{revision entries appended here on update}
