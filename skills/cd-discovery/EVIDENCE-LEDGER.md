# Discovery Evidence Contract

Canonical handoff: `<target-repo>/cd-discovery/evidence.md`. The collector owns source inventory and `SRC-` observations; analysts return owned `CI-`, `REL-`, or `FLOW-` records; the strategist validates, reconciles, and appends analyst findings. This is evidence, not an assessment or report.

## Canonical document

```markdown
# CI/CD Evidence
## Current collection state
- State: IN_PROGRESS | COMPLETE | PARTIAL
- Ready for strategist/analyst use: no | yes
- Latest run: <run ID and date>
## Run <YYYY-MM-DD>-<short-key>
- Started/observed date: YYYY-MM-DD
- Target: <sanitized repository alias and ref>
- Requested scope: <bounded categories, paths, systems, filters>
- Access context: <sanitized read-only tool/tier/role and ref/system>
- Collection state: IN_PROGRESS | COMPLETE | PARTIAL
### Source inventory
| Source/slice | Status | Scope attempted | Access context | Limitation / reason |
### Evidence records
#### SRC-<stable-claim-key> — <neutral claim>
- Status: ...
- Freshness: CURRENT | STALE | SUPERSEDED
- Scope: ...
- Source: ...
- Observed: YYYY-MM-DD
- Access context: ...
- Supports: true | false
- Limitations: ...
- Related IDs: <SRC IDs or none>
## Analyst findings
<validated analyst records; strategist-owned>
```

Include one run per collection and one inventory row for every requested slice, including inaccessible, empty, skipped, user-reported, or inapplicable sources. Inventory status: `COMPLETE` (bounded work completed, including empty search), `PARTIAL`, `BLOCKED` (access/other blocker), `SKIPPED` (intentionally not attempted), `NOT_APPLICABLE` (evidenced basis), `MISSING` (not found in bounded accessible search). Record attempted bounds, sanitized access, and reason. Missing never means unsearched or inaccessible.

Run state is `IN_PROGRESS`, `COMPLETE`, or `PARTIAL`. Ready is `no` during collection or with undispositioned/incomplete requested slices; `yes` only when all slices are completed or justified, observations have locators and limitations, and safety checks pass. A blocked requested slice can be dispositioned but may leave the run partial.

## Source observations (`SRC-`)

One minimal, neutral, attributable observation per enduring claim/scope. Stable ID: `SRC-<lowercase-hyphenated-claim-key>`; no dates, severity, or transient status. Reuse IDs for the same claim/scope; retain old evidence across runs.

Required fields: `Status` (enum below); `Scope` (repository/system, ref/environment/component, filters/bounds; for metrics also time window, population, method and numerator/denominator); `Source` (kind plus narrow locator/resource/query/question); `Observed` (inspection/receipt date); `Access context` (sanitized); `Supports` (`true`/`false`); `Limitations` (bounds, gaps, ambiguity, freshness, inference, redaction; `None known` only after checking); `Related IDs` (IDs or `none`).

Evidence status: `VERIFIED`, `PARTIAL`, `MISSING`, `BLOCKED`, `SKIPPED`, `NOT-APPLICABLE`, `USER-REPORTED`, `UNVERIFIED`, `CONFLICTED`. `USER-REPORTED` cites the supplied answer. `MISSING` requires bounded accessible search. Preserve conflicting sources and mark claim `CONFLICTED`. Freshness is separate metadata: `CURRENT`, `STALE`, `SUPERSEDED`; historical records remain, and stale/superseded records cite the replacing SRC ID.

## Analyst records (`CI-`, `REL-`, `FLOW-`)

Analysts consume only the supplied evidence and explicitly scoped SRC IDs/sections; they do not collect or query sources. Return one atomic record per owned claim, stable ID `<CI|REL|FLOW>-<normalized-lowercase-hyphenated-claim-key>`, and cite exact SRC IDs. Required record fields:

```yaml
- id: CI|REL|FLOW-<claim-key>
  claim: <concise, neutral, bounded and testable>
  owner: <one worker>
  status: VERIFIED | PARTIAL | MISSING | BLOCKED | SKIPPED | NOT-APPLICABLE | USER-REPORTED | UNVERIFIED | CONFLICTED
  confidence: HIGH | MED | LOW
  confidence_reason: <evidence quality/directness, not impact>
  scope: <repository/system, ref/environment/component and filters>
  sources:
    - kind: file | api | user-response | <explicit type>
      reference: <narrow locator; cite SRC IDs>
      observed_date: YYYY-MM-DD
      access_context: <sanitized>
      supports: true | false
  limitations: <explicit bounds/gaps; None known only after checking>
  related_ids: [<IDs>] # [] if none
```

`MISSING` requires a bounded accessible search; `BLOCKED` means prevented access; `USER-REPORTED` is unverified user input; `NOT-APPLICABLE` needs a cited basis. Preserve contradictory sources and use `CONFLICTED` when they materially disagree. Never duplicate another owner's claim: cite its ID and let the strategist reconcile overlapping records without merging materially different scopes, environments, populations, or time windows.

## Ownership and safe handling

The collector alone performs each applicable bounded collection and maintains runs, inventory, and SRC records. Analysts return records only; they do not edit the evidence document. The strategist owns clarification, validation, deduplication, conflict resolution, synthesis, maturity/severity/priority judgments, recommendations, and reports. Workers state limitations and do not fill evidence gaps by inference.

Keep evidence minimal and secret-safe: never record credentials/tokens, secret or variable values, raw/full alert or PR content, large payloads, or unnecessary personal/customer data or sensitive identifiers. Use aggregate facts, safe aliases, narrow locators, and redaction/access limitations. Do not write reports, assessments, maturity ratings, severity, priority, or recommendations in this evidence handoff.
