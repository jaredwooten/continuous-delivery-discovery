# continuous-delivery-discovery

A [Claude Code](https://claude.com/claude-code) skill + agent bundle that performs **automated CI/CD pipeline discovery** on any repository. Produces structured capability assessments scored against the L0–L4 maturity model across seven dimensions (Build & CI, Testing, Deployment Automation, Release Process, Environments & Infra, Observability, Progressive Delivery).

The skill is a thin launcher for a five-agent workflow. The `continuous-delivery-strategist` owns scope, consent, the user interview, assessment, and report synthesis. It delegates bounded, read-only source collection to `cd-evidence-collector`, which maintains the canonical `<target-repo>/cd-discovery/evidence.md`. The strategist then routes relevant, sanitized evidence to three specialists: `ci-artifact-integrity` (CI gates and artifact handoff), `release-safety-recovery` (release controls and recovery), and `delivery-metrics-flow` (observed delivery outcomes). Specialists analyze only their assigned evidence and return finding records; they do not collect sources, repeat queries, assign final maturity or severity, or write reports. The strategist validates and reconciles their findings.

## What you get

- `skills/cd-discovery/` — installs to `~/.claude/skills/cd-discovery/` and exposes `/cd-discovery` as a slash command
- `agents/continuous-delivery-strategist.md` — installs to `~/.claude/agents/` and remains the primary agent spawned by the skill
- `agents/cd-evidence-collector.md` — installs alongside the strategist and owns the canonical source evidence document
- `agents/ci-artifact-integrity.md`, `agents/release-safety-recovery.md`, and `agents/delivery-metrics-flow.md` — evidence-only analysis agents installed alongside the strategist
- An assessment-grade output report (not just a scan dump) — every finding is mapped to a capability level with confidence calls and named anti-patterns

## Prerequisites

- [Claude Code](https://claude.com/claude-code) installed and authenticated
- Optional but recommended: `gh` CLI authenticated (`gh auth login`) — enables the GitHub sub-playbook when the target repo has a `github.com` remote
- Optional: Octopus URL and API key through approved runtime secret injection — enables Tier 1; never pass the key as a CLI argument

## Install (agent-driven)

```bash
git clone https://github.com/jaredwooten/continuous-delivery-discovery.git
cd continuous-delivery-discovery
claude                            # open Claude Code in the cloned repo
```

Then in Claude Code, say:

> Read INSTALL.md and install this bundle.

The agent walks the steps, asks before overwriting anything, and verifies the install at the end. No shell script to debug — if anything goes sideways, you can ask the agent what it sees and it will adapt.

**Two install methods.** The agent will ask which you want:
- **Copy** (recommended for most) — files copied into `~/.claude/`; the cloned repo can be deleted afterward. Future updates require re-running the install playbook.
- **Symlink** (for contributors / dogfooders) — `~/.claude/` entries link directly to the cloned repo. Edits + `git pull` flow live into your Claude Code sessions without re-installing. Don't pick this if you might delete or move the cloned repo — broken symlinks fail silently.

## Update

**Copy-method installs:**

```bash
cd continuous-delivery-discovery
git pull
claude
```

Then:

> Read INSTALL.md and update my install.

The agent diffs the repo against your installed copy, backs up the existing files to `~/.claude/.backup-cd-discovery-<timestamp>/`, and copies the new versions into place. Your agent-memory at `~/.claude/agent-memory/continuous-delivery-strategist/` is preserved.

**Symlink-method installs:**

```bash
cd continuous-delivery-discovery
git pull
```

That's it — the symlinks already point at the files `git pull` just updated. New Claude Code sessions pick up the changes on next skill/agent load.

## Usage

Once installed, run from any project in Claude Code:

| Command | What it does |
|---|---|
| `/cd-discovery` | Scan codebase, interview about gaps, write discovery output to `cd-discovery/` |
| `/cd-discovery --skip-interview` | Same, but tag every gap `[NEEDS CLARIFICATION]` instead of asking |
| `/cd-discovery --suggest` | Discovery + suggestions.md (gaps + tradeoffs + dependency map; a resource, not a plan) |
| `/cd-discovery --update` | Refresh an existing report with new context — verifies what's verifiable, preserves the audit trail |
| `/cd-discovery --skip-github` | Skip the GitHub sub-playbook even if the repo is on GitHub |
| `/cd-discovery --octopus-url <u>` | Scope Octopus Tier 1 discovery; provide `OCTOPUS_API_KEY` through approved environment/runtime secret injection, never as a flag |

The full flag set is in `skills/cd-discovery/SKILL.md` frontmatter.

With `--suggest`, the agent writes a third file (`cd-discovery/suggestions.md`) alongside `summary.md` and `findings.md`. Each suggestion identifies a gap from the findings, names what improving it would unlock, and states the cost. Sequence guidance is expressed as a dependency map — the team owns sequencing. No time-duration estimates. The file is a resource, not a plan: engineers form their own opinion and decide.

If you run `/cd-discovery` first and decide later that you want suggestions, run `/cd-discovery --suggest` against the existing directory — the agent reads your existing findings and writes only `suggestions.md` (no re-scan).

## What gets scanned

**Codebase:** CI workflow files, containers, IaC, build configs, environment configs, deploy scripts, observability config, feature flags, testing layout, release process artifacts, external orchestrator handoff, and GitHub repository posture.

**GitHub (when applicable):** branch protection state, required status checks, GitHub Advanced Security features (secret scanning + push protection, CodeQL default setup, Dependabot), open security alert counts, workflow execution outcomes, dormant workflows, PR cadence + base-branch distribution, default `GITHUB_TOKEN` permissions, CODEOWNERS presence, and workflow artifact supply-chain signals. The collector gathers each authorized source once; eligible sanitized evidence may be routed to a specialist without duplicating queries. Security alert findings may be synthesized directly by the strategist from the evidence.

**Octopus Deploy (when applicable):** projects, lifecycles, channels, deployment process steps, runbooks, manual intervention gates, and deployment/task history — via REST API (Tier 1), Config-as-Code (Tier 2), or user-reported evidence (Tier 3). The collector gathers authorized sources once and may route sanitized release-path or actual-outcome evidence to the corresponding specialist.

## Output

The skill produces a `cd-discovery/` directory at the project root:

- `cd-discovery/summary.md` — executive summary, capability matrix (L0–L4 across seven dimensions), Strengths to Protect, anti-patterns, top three quick wins.
- `cd-discovery/findings.md` — per-dimension deep dive. GitHub and Octopus evidence (when those sub-playbooks run) weaves into the relevant dimensions inline — there are no dedicated GitHub or Octopus sections.
- `cd-discovery/evidence.md` — canonical source inventory and dated, provenance-bearing `SRC-` observations; the strategist appends validated specialist finding records here under `Analyst findings`.
- `cd-discovery/suggestions.md` — only when `--suggest` has run. See description above.

Each report file is standalone-readable and maintains its own append-only revision log. `evidence.md` retains dated collection runs; replaced records get `Freshness: STALE` or `SUPERSEDED` and a replacement `SRC-` ID, never deletion.

### Migrating from the previous single-file output

If you ran an earlier version of this skill that wrote `CD-DISCOVERY.md` at the project root, the next `/cd-discovery` run will detect the legacy file and offer three options: **Migrate** (split it into the new layout, preserving content and revision history; removes the legacy file as part of the commit), **Fresh** (discard and run a new discovery), or **Cancel**. Choose Migrate to keep your audit trail intact.

## Contributing

Issues and PRs welcome. If you change the skill or agent files, test them by running `/cd-discovery` against a sample repo before submitting — the only way to catch broken playbook references is to actually invoke the flow end-to-end.

When proposing playbook additions (new scan categories, new sub-orchestrators), please include:
- A concrete artifact pattern to grep / glob for
- How a finding maps into the L0–L4 capability matrix
- An example anti-pattern the new scan would surface

## License

MIT — see [LICENSE](LICENSE).
