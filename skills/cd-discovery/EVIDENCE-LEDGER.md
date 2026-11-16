# Discovery Evidence Contract

The canonical collection artifact is `<target-repo>/cd-discovery/evidence.md`.
It holds source observations gathered by `cd-evidence-collector` and, in a
separate section appended after specialist results, analyst findings maintained
by the `continuous-delivery-strategist`. The collector owns source collection
and records sanitized, attributable evidence only. Analysts own their findings
and may cite source-observation IDs; they must not repeat queries already
covered by the collection protocols. `evidence.md` is an evidence handoff, not
an assessment or report.

## Canonical `evidence.md` structure

Use this canonical structure in `<target-repo>/cd-discovery/evidence.md`. Keep
dated collection runs and source observations under the collection sections;
the strategist appends `## Analyst findings` after specialist results:

```markdown
# CI/CD Evidence

## Current collection state
- State: IN_PROGRESS | COMPLETE | PARTIAL
- Ready for strategist/analyst use: no | yes
- Latest run: <run ID and date>

## Run <YYYY-MM-DD>-<short-run-key>
- Started/observed date: YYYY-MM-DD
- Target: <sanitized repository alias and ref>
- Requested scope: <bounded categories, paths, systems, filters>
- Access context: <read-only local ref; authenticated tool/tier/role, sanitized>
- Collection state: IN_PROGRESS | COMPLETE | PARTIAL

### Source inventory
One row per requested source/slice, including status, attempted scope,
sanitized access context, and limitation/reason.

### Evidence records
Sanitized, attributable source records using the schema below. Assign stable
`SRC-` IDs.

## Analyst findings
The strategist appends validated `CI-`, `REL-`, and `FLOW-` specialist/analyst
finding records here after specialist results are returned and reconciled.
```

### Run statuses and source inventory

Use `IN_PROGRESS`, `COMPLETE`, or `PARTIAL` for the current collection and each
run. Keep `Ready: no` while collecting or if any requested source is not
attempted or dispositioned. Set `COMPLETE` / `Ready: yes` only when requested
slices have completed or justified dispositions, records have locators and
limitations, and safety checks pass. Use `PARTIAL` / `Ready: no` if a requested
slice remains blocked, skipped without disposition, or materially incomplete.

Every requested source/slice appears in the source inventory, including
inaccessible, skipped, empty, and user-reported sources. Inventory status must
be exactly one of:

- `COMPLETE` — the planned bounded collection completed.
- `PARTIAL` — some, but not all, planned evidence was collected.
- `BLOCKED` — access, permissions, network, or another explicit blocker
  prevented collection.
- `SKIPPED` — collection was intentionally not attempted (state why).
- `NOT_APPLICABLE` — the source family does not apply; record the evidenced
  basis.
- `MISSING` — an expected source/artifact was not found after searching an
  explicitly bounded and accessible scope.

Use these inventory columns: `Source/slice`, `Status`, `Scope attempted`,
`Access context`, and `Limitation / reason`. An empty search result is
`COMPLETE` with its bounded search recorded; it is not `BLOCKED`. Use `MISSING`
for the bounded negative result, not for unsearched or inaccessible scope.
Explain every partial, blocked, skipped, not-applicable, or missing source.

### Source-observation record schema

Each source observation is a minimal, neutral statement directly supported by
the cited source. Use the record format below; the analyst finding contract
later in this document is separate and must not replace `SRC-` records:

| Field | Requirement |
|---|---|
| Record heading | `SRC-<concise-lowercase-hyphenated-claim-key> — <neutral claim>`. Reuse an ID for the same enduring claim and scope; do not encode dates, severity, or transient status. |
| `Status` | One evidence-record status from the list below. A user answer not independently verified uses `USER-REPORTED`; a bounded negative search uses `MISSING`. |
| `Scope` | Repository/system, ref/environment/component, filters, and bounds. Metrics also state time window, population, and calculation method (including numerator/denominator or equivalent). |
| `Source` | Source kind plus the narrow locator/resource/query/question. Never paste full responses. |
| `Observed` | Date inspected or received (`YYYY-MM-DD`), not an inferred creation date. |
| `Access context` | Sanitized tool/tier/role and applicable repository ref/system. Never record credentials or sensitive identities. |
| `Supports` | `true` or `false`, indicating whether the source supports or contradicts this observation/claim. |
| `Limitations` | Search bounds, sampling, unavailable coverage, ambiguity, freshness, inference, or redaction caveats. Use `None known` only after checking. |
| `Related IDs` | Related `SRC-` identifiers or `none`. Do not mint a second record for a duplicate claim. |

Evidence-record status must be exactly one of `VERIFIED`, `PARTIAL`, `MISSING`,
`BLOCKED`, `SKIPPED`, `NOT-APPLICABLE`, `USER-REPORTED`, `UNVERIFIED`, or
`CONFLICTED`. `MISSING` requires an explicitly bounded accessible search;
inaccessible or unsearched scope is not missing. Preserve conflicting sources
and mark the affected claim `CONFLICTED`. Across collection runs, preserve old
records; mark replaced historical records `STALE` or `SUPERSEDED` with the
replacing `SRC-` reference while retaining the applicable evidence status.

Example canonical run, source inventory, and source record:

```markdown
## Current collection state
- State: COMPLETE
- Ready for strategist/analyst use: yes
- Latest run: 2026-11-13-github-read

## Run 2026-11-13-github-read
- Started/observed date: 2026-11-13
- Target: `acme/payments` at default branch `main`
- Requested scope: GitHub workflow run outcomes, latest 200 returned runs
- Access context: read-only GitHub CLI Tier 1; authenticated repository access
- Collection state: COMPLETE

### Source inventory

| Source/slice | Status | Scope attempted | Access context | Limitation / reason |
|---|---|---|---|---|
| GitHub workflow runs | COMPLETE | `acme/payments`; latest 200 returned runs | GitHub CLI Tier 1, read-only repository access | Not a fixed calendar window; incomplete runs excluded from failure fraction. |

### Evidence records

#### SRC-gh-build-run-outcomes — build workflow run outcomes
- Status: VERIFIED
- Scope: `acme/payments`, workflow `build`; latest 200 returned runs as of 2026-11-13 (not a fixed calendar interval); 20 completed runs (18 success, 2 failure); failure fraction = 2 / 20 completed runs.
- Source: api — `gh run list`; limit 200; fields `status`, `conclusion`, `workflowName`, `createdAt`.
- Observed: 2026-11-13
- Access context: GitHub CLI Tier 1, authenticated read-only repository access.
- Supports: true
- Limitations: Run query capped at 200; not a calendar-period rate; runs without a completed conclusion are excluded from the denominator.
- Related IDs: none
```

### Shared source attribution

Use the fields in the respective source-record or analyst finding schema. Cite
the narrowest useful locator: API resource plus query/filter, file path/line,
repository and ref, or interview question and concise paraphrase. Never record
credentials or paste full responses.

### Data minimization and analyst boundary

Preserve only the raw evidence minimum necessary to support later analysis.
Never write credentials/tokens, secret or sensitive variable values, full alert
bodies, full PR bodies, or unnecessary personal/customer data. For sensitive
sources, retain a sanitized fact, a narrow locator, and the access/redaction
limitation. Do not turn source observations into findings, score maturity,
assign final severity, recommend actions, or write summary/findings/suggestions
reports. `cd-evidence-collector` performs each applicable source query once and
writes the observations and inventory; specialists consume that evidence and
return analyst records only. The strategist appends the separate analyst
findings section after validating, deduplicating, and reconciling specialist
results.

## Analyst finding record contract

This section defines `CI-`, `REL-`, and `FLOW-` records appended by the
strategist under `## Analyst findings` in the same `evidence.md`. These records
are analyst interpretations of source observations, not replacements for the
collector's `SRC-` records. Analysts should cite relevant `SRC-` IDs in their
source references and must not repeat source queries.

## Record requirements

Each finding has exactly one owner: the worker responsible for maintaining the
complete finding record. Other workers may cite or return a reference to its
stable ID; they must not create a second finding for the same claim. Include
every field below, using an explicit empty list only where no related IDs or
sources apply. `limitations` is always required and must state why evidence may
be incomplete, stale, indirect, or otherwise constrained; use `None known` only
when the worker has checked and found no material limitation.

| Field | Requirement |
|---|---|
| `id` | Stable ID in the form `<PREFIX>-<normalized-claim-key>`. Use `CI-` for CI/build/test pipeline claims, `REL-` for release/deployment claims, and `FLOW-` for delivery-flow, operational feedback, or metric claims. Normalize a concise, unique claim key using lowercase words separated by hyphens. Base it on the enduring subject and claim, not line numbers, dates, status, confidence, or severity. Once assigned, reuse the same ID when the claim is revisited. |
| `claim` | One concise, atomic, neutral, testable statement of what the evidence establishes or fails to establish. State the relevant subject and boundary; do not make a recommendation or maturity judgment. |
| `owner` | One worker identifier/name. References from other workers reuse the ID and do not create another owner or competing record. |
| `status` | Exactly one value from the status definitions below. |
| `confidence` | `HIGH`, `MED`, or `LOW`, with a required `confidence_reason`. This describes evidence quality and directness, not impact, severity, or priority. |
| `scope` | Required boundaries that make the claim interpretable and reproducible: repository/system or service, relevant branch/environment/component, and any inclusion/exclusion filters. For a metric, scope must additionally state its **time window**, **population**, and **calculation method** (including numerator/denominator or equivalent where applicable). Do not imply broader coverage than was examined. |
| `sources` | Attributable citations for supporting and contradicting evidence. Each source records a locator/reference, observed date (`YYYY-MM-DD`), and access context. Source-specific minimums are below. Do not copy sensitive or unnecessarily large source content into the ledger. |
| `limitations` | Required account of search bounds, unavailable coverage, sampling, ambiguity, freshness, inference, or other caveats. Explain when no material limitation is known. |
| `related_ids` | IDs of claims that provide context, overlap, or conflict; use `[]` if none. Never mint a new ID merely to repeat a claim owned elsewhere. |

### Status values

- `VERIFIED` — directly supported by sufficient, attributable evidence within
  the stated scope.
- `PARTIAL` — evidence supports only part of the claim or only part of the
  stated scope.
- `MISSING` — the expected evidence/artifact was not found **after a search of
  an explicitly bounded and accessible scope**. Record what was searched and
  the bounds in `scope`, `sources`, and/or `limitations`. An unsearched or
  inaccessible area is not `MISSING`.
- `USER-REPORTED` — the claim is based on a user's statement and has not been
  independently verified. Cite the response as a source.
- `UNVERIFIED` — a claim or lead exists, but available evidence does not
  establish it and the reason is not simply inaccessible access; state what
  remains unverified.
- `NOT-APPLICABLE` — the capability or question does not apply to the stated
  system/scope. Cite the basis for determining this.
- `BLOCKED` — verification is prevented by inaccessible systems, permissions,
  missing access, or another explicit blocker. State the attempted access and
  blocker; do not describe the inaccessible evidence as absent.
- `CONFLICTED` — attributable evidence sources materially disagree. Preserve
  both sides and their scopes; do not silently choose one.

### Source attribution

For each analyst finding source, record:

- `kind`: `file`, `api`, `user-response`, or another explicit source type.
- `reference`: a precise locator, such as `path/to/file.yml:12-19`, API
  resource/endpoint plus relevant query or filters, or the interview question
  and a concise paraphrase of the user's answer.
- `observed_date`: the date the worker inspected or received the evidence, not
  an inferred creation date.
- `access_context`: enough context to identify how and where it was observed,
  such as repository and commit/ref, API/system and accessible account/role,
  environment, tool/tier, or interview channel. Record that access was
  unavailable when relevant. Never record credentials or tokens.
- `supports`: `true` or `false`, indicating whether the source supports or
  contradicts the claim. (Source observations omit this field because their
  source directly attributes the observation.)

Use the narrowest useful citation. For API evidence, identify the resource,
query/filter, and relevant returned fact without pasting full responses. For
user responses, identify the question and paraphrase only the relevant answer.

## Evidence-worker boundaries and safe handling

Workers return ledger records, evidence references, and explicit limitations
only. They do not assign final delivery maturity, severity, or priority; rank
findings; propose prioritized recommendations; or write `summary.md`,
`findings.md`, `suggestions.md`, or another discovery report. Leave synthesis
and any assessment to the strategist.

Keep the ledger secret-safe and data-minimal. Never include credentials,
tokens, secret values, raw alert bodies, or full pull-request content. Cite a
redacted/narrow source reference and state the redaction or access limitation
when needed. Do not include personal or customer data unless strictly needed
to establish the claim; prefer an aggregate or sanitized reference.

## Compact YAML example

```yaml
- id: CI-required-checks-default-branch
  claim: The default branch requires the CI test workflow before merge.
  owner: github-worker
  status: VERIFIED
  confidence: HIGH
  confidence_reason: Branch protection settings and the named required check were directly inspected.
  scope:
    repository: acme/payments
    branch: main
    settings_examined: required status checks
  sources:
    - kind: api
      reference: "GitHub branch protection for main; required check: CI / test"
      observed_date: "2026-11-13"
      access_context: "GitHub API, acme/payments, read-only repository settings access"
      supports: true
  limitations: "Settings were inspected for main only; other branches are outside scope."
  related_ids: []
```

## Strategist validation: conflicts and deduplication

1. Validate required fields, status spelling, confidence reason, bounded scope,
   source attribution, and explicit limitations before using a record. Reject
   or return incomplete records for correction; do not fill evidence gaps by
   inference.
2. Resolve IDs against the ledger by normalized claim key and scope. If workers
   report the same underlying claim, retain one canonical ID and owner, attach
   additional attributable sources to that record, and have other records
   reference the canonical ID. Do not deduplicate claims whose branch,
   environment, population, or time window differs materially.
3. For disagreement, compare source dates, access context, exact scope, and
   directness. Keep both supporting and contradicting sources, link relevant
   IDs in `related_ids`, and mark the affected claim `CONFLICTED` until the
   evidence resolves the disagreement. Do not settle a conflict by choosing
   the higher confidence label alone or by dropping the contrary source.
4. Preserve unresolved boundaries and limitations in the ledger. Any maturity,
   severity, prioritization, recommendations, and report framing happen only in
   the strategist's later synthesis.
