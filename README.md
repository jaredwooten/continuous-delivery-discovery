# continuous-delivery-discovery

A [Claude Code](https://claude.com/claude-code) skill + agent bundle that performs **automated CI/CD pipeline discovery** on any repository. Produces a structured `CD-DISCOVERY.md` capability assessment scored against the L0–L4 maturity model across seven dimensions (Build & CI, Testing, Deployment Automation, Release Process, Environments & Infra, Observability, Progressive Delivery).

The skill is a thin launcher; the heavy lifting is done by the bundled `continuous-delivery-strategist` agent, which reads playbooks for the main codebase scan plus optional sub-scans for **GitHub** (branch protection, security alerts, workflow execution reality, PR cadence) and **Octopus Deploy** (REST API → Config-as-Code → questionnaire fallback tiers).

## What you get

- `skills/cd-discovery/` — installs to `~/.claude/skills/cd-discovery/` and exposes `/cd-discovery` as a slash command
- `agents/continuous-delivery-strategist.md` — installs to `~/.claude/agents/` and is spawned by the skill
- An assessment-grade output report (not just a scan dump) — every finding is mapped to a capability level with confidence calls and named anti-patterns

## Prerequisites

- [Claude Code](https://claude.com/claude-code) installed and authenticated
- Optional but recommended: `gh` CLI authenticated (`gh auth login`) — enables the GitHub sub-playbook when the target repo has a `github.com` remote
- Optional: Octopus Deploy API key (`API-...`) — enables Tier 1 Octopus discovery against your Octopus server

## Install (agent-driven)

```bash
git clone https://github.com/jaredwooten/continuous-delivery-discovery.git
cd continuous-delivery-discovery
claude                            # open Claude Code in the cloned repo
```

Then in Claude Code, say:

> Read INSTALL.md and install this bundle.

The agent walks the steps, asks before overwriting anything, and verifies the install at the end. No shell script to debug — if anything goes sideways, you can ask the agent what it sees and it will adapt.

## Update

```bash
cd continuous-delivery-discovery
git pull
claude
```

Then:

> Read INSTALL.md and update my install.

The agent diffs the repo against your installed copy, backs up the existing files to `~/.claude/.backup-cd-discovery-<timestamp>/`, and copies the new versions into place. Your agent-memory at `~/.claude/agent-memory/continuous-delivery-strategist/` is preserved.

## Usage

Once installed, run from any project in Claude Code:

| Command | What it does |
|---|---|
| `/cd-discovery` | Scan codebase, interview about gaps, write `CD-DISCOVERY.md` |
| `/cd-discovery --skip-interview` | Same, but tag every gap `[NEEDS CLARIFICATION]` instead of asking |
| `/cd-discovery --assess` | Discovery + a phased improvement roadmap |
| `/cd-discovery --update` | Refresh an existing report with new context — verifies what's verifiable, preserves the audit trail |
| `/cd-discovery --skip-github` | Skip the GitHub sub-playbook even if the repo is on GitHub |
| `/cd-discovery --octopus-url <u> --octopus-api-key <k>` | Force Tier 1 Octopus discovery against a specific server |

The full flag set is in `skills/cd-discovery/SKILL.md` frontmatter.

## What gets scanned

**Codebase (12 categories):** CI workflow files, containers, IaC, build configs, environment configs, deploy scripts, observability config, feature flags, testing layout, release process artifacts, external orchestrator handoff, and GitHub repository posture.

**GitHub (when applicable):** branch protection state, required status checks, GitHub Advanced Security features (secret scanning + push protection, CodeQL default setup, Dependabot), open security alert counts, workflow execution success rates, dormant workflows, PR cadence + base-branch distribution, default `GITHUB_TOKEN` permissions, CODEOWNERS presence.

**Octopus Deploy (when applicable):** projects, lifecycles, channels, deployment process steps, runbooks, manual intervention gates, recent deployment outcomes — via REST API (Tier 1), Config-as-Code (Tier 2), or questionnaire (Tier 3).

## Output

Single file at the project root: `CD-DISCOVERY.md`. Sections include:

1. Executive Summary
2. Capability Matrix (seven dimensions × L0–L4 with confidence calls)
3. Detailed Findings per dimension
4. Deployment Orchestrator section (if Octopus is in scope)
5. GitHub Repository Posture section (if applicable)
6. Anti-Patterns observed
7. Recommended Next Steps

With `--assess`, the agent adds a phased improvement roadmap (2–6 week phases) with prerequisites, proof points, and audience-appropriate framing.

## Contributing

Issues and PRs welcome. If you change the skill or agent files, test them by running `/cd-discovery` against a sample repo before submitting — the only way to catch broken playbook references is to actually invoke the flow end-to-end.

When proposing playbook additions (new scan categories, new sub-orchestrators), please include:
- A concrete artifact pattern to grep / glob for
- How a finding maps into the L0–L4 capability matrix
- An example anti-pattern the new scan would surface

## License

MIT — see [LICENSE](LICENSE).
