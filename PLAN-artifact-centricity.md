# Plan: Encode artifact-centricity findings into `continuous-delivery-discovery`

## Context

A discovery run produced `mi-portal/CD-DISCOVERY.md`. The strategist agent reviewed it and surfaced one structural defect plus one omission:

1. **Structural defect — verification miss.** The report claimed at line 56 that `webapp-build.yaml` runs `npm install`. The file actually runs `npm ci` (verified at `webapp-build.yaml:37`). The skill has strong verification discipline in the UPDATE path but the *initial* scan didn't have an artifact-identity-flavored grep that would have caught this, so a stale anti-pattern row shipped at `CD-DISCOVERY.md:482`.
2. **Omission — artifact-centricity is invisible.** The mi-portal pipeline correctly implements *build-once-promote-the-same-artifact* (single ECR push in `api-build.yml:131-168`; `docker-tag.txt` packaged into the Octopus zip; `deploy_api.sh:69` reads that tag rather than rebuilding). This is the load-bearing CD principle, and neither the playbook nor the strategist names it, checks for it, or celebrates it when present. A reader of `CD-DISCOVERY.md` cannot tell that the pattern is in place or that small "improvements" (parameterizing tags per env, retagging at deploy, rebuilding per env) would silently regress it.

The mi-portal team's prior feedback also established a **context-aware severity rule** for branch protection. The same shape applies to artifact-centricity: severity depends on whether the foundation is in place. When it is, findings should be *descriptive* and framed as **Strengths to Protect**. When it isn't, they're HIGH-severity Deployment Automation gaps.

**Intended outcome.** Future `cd-discovery` runs:
- Detect artifact-centricity state explicitly (build-once vs. rebuild-per-env, immutable tags, tag handoff pattern, SBOM/signing, dependency caching).
- Name strengths that are working — not just gaps. Every dimension can carry a `Strengths to Protect:` field in the output template.
- Catch claim/code drift like the `npm install` vs `npm ci` issue via a small, targeted set of verification greps tied to the new scan category.
- Apply the same context-aware framing rule already used for branch protection, but for artifact-centricity.

The architecture supports this surgically. No restructuring needed.

---

## Files to modify

All paths are absolute under `/Users/jwooten/dev/continuous-delivery-discovery/`.

| File | Edit type | Approximate insertion point |
|---|---|---|
| `skills/cd-discovery/PLAYBOOK.md` | Add §1.13 (new scan category) + 4 new anti-pattern rows + Quality Gate update | After §1.12; anti-pattern table; Quality Gate |
| `agents/continuous-delivery-strategist.md` | Add Discovery Mode bullet 6 (artifact-centricity framing rule) + Quality Check 6 | Section §6 Discovery Mode; Quality Checks |
| `skills/cd-discovery/TEMPLATE.md` | Add `Strengths to Protect:` field to per-dimension Detailed Findings block; add Strengths-to-Protect roll-up section after Capability Matrix | Detailed Findings block; new section after Capability Matrix |
| `skills/cd-discovery/GH-DISCOVERY.md` | Add §1.13 (artifact provenance from the GH side) + extend Framing Rule with an artifact-centricity parallel + Quality Gate row | After §1.12; Framing Rule block; Quality Gate |
| `skills/cd-discovery/UPDATE-PLAYBOOK.md` | Add one decomposition example: an artifact-centricity claim with verifiability tags | Phase 3/4 examples |

---

## Detailed change set

### 1. `skills/cd-discovery/PLAYBOOK.md`

**Add §1.13 "Artifact Identity & Promotion"** after the §1.12 GitHub block. New scan category — keep the style of the existing 1.x sections.

Content sketch:

> ### 1.13 Artifact Identity & Promotion
>
> The single most load-bearing CD principle is **build the artifact once; promote the same bytes through environments**. Detect whether the pipeline implements it, partially implements it, or violates it.
>
> Look for the build step(s) that produce deployable artifacts (container images, language packages, deployment zips). For each:
>
> - **Build occurrence count.** Does CI build the artifact once per commit, or once per target environment? Grep for repeated `docker build`, `dotnet publish`, `npm run build` in the same workflow across multiple jobs.
> - **Tag/version identity.** What identifier travels with the artifact? Grep for `docker tag`, `docker push --all-tags`, `:latest`, `:${{ github.sha }}`, `:${{ github.run_number }}`, version files like `build_properties.json`, `package.json` version fields, `<Version>` in `.csproj`.
> - **Immutability.** Is the production-targeted tag immutable (versioned, SHA-pinned), or mutable (`:latest`, environment-named tags like `:prod`)? `docker push --all-tags` plus a `:latest` retag is a race risk worth flagging.
> - **Promotion mechanism.** Does the deploy step read the tag from the build (via a file packaged with the deploy script, an artifact upload, or an output) — or does it construct the tag itself per environment? Grep deploy scripts for `cat *tag*.txt`, environment-substituted tags, or per-env image references.
> - **Build-time vs. runtime configuration injection.** If the artifact is identical across environments but config is swapped at deploy time (e.g., Ansible replacing `environment.values.{env}.js` in an otherwise-identical webapp bundle), record this as a build-once-with-asterisk pattern — not a violation, but worth naming.
> - **Provenance & signing.** Grep workflows for `cosign`, `sigstore`, `anchore/sbom-action`, `actions/attest-build-provenance`, `slsa-framework`. Note absence; severity depends on §1.7 supply-chain risk.
> - **Dependency caching.** Grep for `actions/cache`, `setup-node` with `cache:`, `setup-dotnet` with cache hints, Docker layer caching (`cache-from`, `cache-to`, `gha`). Cache absence on the main build path inflates feedback time — name it.
> - **Install command hygiene.** Grep specifically for `npm install` vs `npm ci`, `yarn install` (no `--frozen-lockfile`) vs `yarn install --frozen-lockfile`, `pip install` (no `--require-hashes`). Non-deterministic installs corrupt artifact identity.
>
> **Framing rule** (must propagate into both the report and the agent's reasoning): *build-once-promote-the-same-artifact is the load-bearing pattern under L3+ Deployment Automation.* When it is in place, name it as a **Strength to Protect** with file:line evidence and call out what would break it. When it is absent or partially implemented (per-env rebuilds, mutable tags reaching prod, retag-at-deploy), surface it as a HIGH-severity Deployment Automation finding regardless of how green the rest of the pipeline looks. Build-once-with-config-swap-at-deploy is acceptable but must be framed as an asterisk.

**Add anti-pattern rows** to the Anti-Pattern Detection table:

| Anti-Pattern | What to Look For |
|---|---|
| Mutable image tag reaches prod | Production deploy references `:latest` or env-named tags; `docker push --all-tags` followed by no immutable tag enforcement in registry policy |
| Per-environment rebuild | Same artifact built more than once per commit (separate dev/stage/prod build jobs producing fresh tags) |
| Retag at deploy time | Deploy script constructs an env-specific tag and retags the CI-built image rather than promoting the original tag |
| Deploy-code coupled to runtime artifact | Deploy scripts/playbooks bundled inside the runtime artifact, forcing a full rebuild to fix deploy tooling |
| Non-deterministic install in CI | `npm install` instead of `npm ci`; `yarn install` without `--frozen-lockfile`; `pip install` without hash pinning |
| No artifact provenance | No SBOM emission, no image signing (cosign/Notation), no SLSA attestation in the build that ships to prod |
| No dependency caching on main build | `setup-node`/`setup-dotnet`/`setup-python` without `cache:`; no Docker layer cache on builds taking >2 min |

**Update Quality Gate** — change `All 12 scan categories executed (1.1–1.12)` → `All 13 scan categories executed (1.1–1.13)`. Add bullet: `Artifact-centricity findings interpreted with the framing rule — strengths named explicitly when build-once-promote is in place; HIGH-severity when violated`.

---

### 2. `agents/continuous-delivery-strategist.md`

**Add bullet 6 to Discovery Mode** between current bullets 5 and 6 — renumber subsequent bullets so the framing rules sit together.

> 6. **Framing rule for artifact-centricity.** Build-once-promote-the-same-artifact is the load-bearing CD principle. When `PLAYBOOK.md` §1.13 finds it in place (single build per commit, immutable tag promoted unchanged through environments, deploy step reads the tag from the build rather than constructing it), name it as a **Strength to Protect** in the report with file:line evidence — not just an absent gap. Tell the reader what would silently regress it (per-env tag parameterization, retag-at-deploy, separate per-env build jobs). When the codebase rebuilds per environment, lets a mutable tag reach prod, or retags at deploy, surface it as a HIGH-severity Deployment Automation finding regardless of how green the rest of the pipeline looks. Build-once-with-config-swap-at-deploy (identical bundle, runtime config swapped) is acceptable but must be framed as an asterisk so future readers don't think it's a full violation.

**Add a quality check** to the Quality Checks list:

> 6. Are positive findings — **Strengths to Protect** — named explicitly with file:line evidence, or does the report read as if everything were a gap? Pipelines that get artifact-centricity right need that strength visible so it isn't silently regressed.

---

### 3. `skills/cd-discovery/TEMPLATE.md`

**Add `Strengths to Protect:` to the per-dimension Detailed Findings block**. Insert between `Artifacts Found:` and `Gaps Identified:`:

```
**Strengths to Protect:**
- `{path/to/file:line}` — {what works, in one line} — {what would silently regress it}
```

**Add a roll-up section after the Capability Matrix**, before `## Detailed Findings`:

```markdown
## Strengths to Protect

> The load-bearing patterns the team is getting right. Naming these explicitly defends against well-intentioned "improvements" that silently regress them. If this section is empty, the report is incomplete — every pipeline has something working.

| Strength | Evidence | What would break it |
|---|---|---|
| {pattern name, e.g. "Build-once-promote via docker-tag.txt handoff"} | `{file:line}` | {specific change that regresses it} |
```

---

### 4. `skills/cd-discovery/GH-DISCOVERY.md`

**Add §1.13 "Artifact provenance from the GitHub side"** after §1.12 CODEOWNERS:

> ### 1.13 Artifact provenance and supply-chain posture
>
> Grep the workflows for the supply-chain signals that don't show up in `repos/{O}/{R}/security_and_analysis`:
>
> ```bash
> grep -rEn 'cosign|sigstore|actions/attest-build-provenance|anchore/sbom-action|slsa-framework|syft|grype' .github/workflows/
> ```
>
> Also check workflow caching coverage on the build path:
>
> ```bash
> grep -rEn 'actions/cache|cache:\s*(npm|yarn|pnpm|pip|maven|gradle)|cache-from|cache-to' .github/workflows/
> ```
>
> And install-command hygiene:
>
> ```bash
> grep -rEn '\bnpm install\b|\byarn install\b|\bpip install\b' .github/workflows/
> ```
> (Cross-check matches against the surrounding line; `npm ci` and `--frozen-lockfile` are not findings.)
>
> Capture: presence/absence of SBOM emission, image signing, build-provenance attestations, dependency cache coverage, and install-command determinism. Feed into the §1.13 PLAYBOOK output and into the Security + Deployment Automation dimensions.

**Extend the Framing Rule block** with a parallel artifact-centricity rule:

> **Framing rule — artifact-centricity findings.** Parallel to the branch-protection rule: build-once-promote-the-same-artifact is load-bearing. When it's in place (verified by §1.13 of the main playbook), name it as a **Strength to Protect** in the Cross-stitch section, with explicit warnings about what would regress it. When it's absent, treat it as a HIGH-severity Deployment Automation finding regardless of how strong the rest of the pipeline looks — re-testing per environment defeats the confidence model that CD depends on.

**Add to Quality Gate**:

> - ✅ Artifact provenance grep executed (cosign, SBOM, attestation, cache, install-command hygiene)
> - ✅ Artifact-centricity findings interpreted with the framing rule — strengths named explicitly when build-once-promote is in place

---

### 5. `skills/cd-discovery/UPDATE-PLAYBOOK.md`

**Add one decomposition example** alongside existing examples:

> **Example: artifact-centricity claim.**
> User context: "Our images are built once in CI and the same tag is promoted unchanged through dev → stage → prod."
> Decomposition:
> 1. *Single build per commit* — verifiability: CODEBASE. `grep -c 'docker build' .github/workflows/<workflow>.yml` in the relevant job; confirm one build step, not one per env.
> 2. *Tag immutability through promotion* — verifiability: CODEBASE. Grep deploy scripts for tag construction. Confirm the tag is **read from** a file/output produced by the build, not constructed in the deploy step. Look for `cat *tag*.txt`, `${{ needs.build.outputs.tag }}`, or equivalent.
> 3. *Tag never mutated post-push* — verifiability: PARTIAL. Grep workflows for `docker tag` calls after the production push; check registry retention policy (EXTERNAL, ask user).
> Implied action: raise confidence on Deployment Automation; **add a Strengths to Protect entry** naming the specific file:line that implements the handoff.

---

## Verification

After the edits:

1. **Dry-run consistency check.** `grep -rEn 'artifact-centricity|build-once|Strengths to Protect' /Users/jwooten/dev/continuous-delivery-discovery/` should return matches in all five edited files.
2. **Quality-Gate scan-count consistency.** Confirm PLAYBOOK.md Quality Gate now says "1.1–1.13" (not 1.1–1.12).
3. **Replay the mi-portal scenario.** Re-run `cd-discovery` against `/Users/jwooten/dev/mi-portal` (or use the UPDATE path against the existing `CD-DISCOVERY.md`). Expected new behavior:
   - §1.13 grep finds the `docker-tag.txt` handoff at `api-build.yml:131-134` and `deploy_api.sh:69`.
   - The npm-install-vs-npm-ci grep correctly identifies `webapp-build.yaml:37` as `npm ci` — the existing stale anti-pattern row at `CD-DISCOVERY.md:482` gets removed.
   - A `Strengths to Protect` section appears with at least two entries: the `docker-tag.txt` handoff and the immutable versioned tag on prod.
   - The dependency-caching grep flags missing `actions/cache`/`setup-node` cache on `webapp-build.yaml` and `api-build.yml` as a new finding.
   - Image signing / SBOM absence is named in Security or Deployment Automation gaps with explicit severity.
4. **Branch-protection rule still works.** The existing context-aware severity for branch protection must not regress.
5. **Manual eyeball of the strategist's response shape.** Quality Check #6 should now cause the agent to surface Strengths to Protect explicitly — not just gaps.
