# Evidence Ledger Contract

This contract defines the evidence-only handoff from discovery workers to the
`continuous-delivery-strategist`. A ledger records attributable observations and
their limits; it is not an assessment or a report.

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

For every source, record:

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
  contradicts the claim.

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
