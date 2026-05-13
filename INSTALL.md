# INSTALL.md — Agent-followable install playbook

**Audience:** an agent running inside Claude Code (you). The user has asked you to install or update this bundle. Follow these steps in order. If anything is ambiguous, stop and ask the user via `AskUserQuestion` — do not improvise.

**What gets installed:**
- The `cd-discovery` skill → `~/.claude/skills/cd-discovery/` (6 files)
- The `continuous-delivery-strategist` agent → `~/.claude/agents/continuous-delivery-strategist.md`
- An agent-memory directory → `~/.claude/agent-memory/continuous-delivery-strategist/` (created empty on fresh install; preserved as-is on update)

## Step 1 — Detect mode (fresh vs update)

Check whether both install targets already exist:

- Does `~/.claude/skills/cd-discovery/` exist as a directory?
- Does `~/.claude/agents/continuous-delivery-strategist.md` exist as a file?

Mode resolution:

| Skill dir | Agent file | Mode |
|---|---|---|
| Missing | Missing | **Fresh install** — go to Step 3a |
| Present | Present | **Update** — go to Step 3b |
| One present, one missing | | **Partial install detected.** Ask the user via `AskUserQuestion` whether to (a) treat it as a fresh install and replace whatever is there, or (b) abort so they can investigate manually. Do not guess. |

## Step 2 — Prerequisites check

Run these checks before doing any file operations:

1. **You are in the cloned repo.** Confirm these files exist relative to the current working directory:
   - `skills/cd-discovery/SKILL.md`
   - `skills/cd-discovery/PLAYBOOK.md`
   - `skills/cd-discovery/TEMPLATE.md`
   - `skills/cd-discovery/UPDATE-PLAYBOOK.md`
   - `skills/cd-discovery/OCTOPUS-DISCOVERY.md`
   - `skills/cd-discovery/GH-DISCOVERY.md`
   - `agents/continuous-delivery-strategist.md`

   If any are missing, abort and tell the user they appear to be in the wrong directory or have a corrupted clone.

2. **Parent dirs exist.** Ensure these exist (create if not):
   - `~/.claude/skills/`
   - `~/.claude/agents/`
   - `~/.claude/agent-memory/`

## Step 3a — Fresh install

Execute in order:

1. `mkdir -p ~/.claude/agent-memory/continuous-delivery-strategist`
2. Copy the whole skill dir:
   ```bash
   cp -R skills/cd-discovery ~/.claude/skills/cd-discovery
   ```
3. Copy the agent file:
   ```bash
   cp agents/continuous-delivery-strategist.md ~/.claude/agents/continuous-delivery-strategist.md
   ```
4. Verify the install — list both destinations and confirm all 6 skill files and the agent file are present.

Proceed to **Step 4**.

## Step 3b — Update

1. **Diff each repo file against its installed counterpart.** For each of the 7 files:
   - Repo: `skills/cd-discovery/<file>.md` or `agents/continuous-delivery-strategist.md`
   - Installed: `~/.claude/skills/cd-discovery/<file>.md` or `~/.claude/agents/continuous-delivery-strategist.md`

   Use `diff` (or compare hashes). Track which files differ.

2. **If no files differ** — tell the user "Already up to date." and exit. Do not write anything.

3. **If any files differ** — summarize the changes to the user (filename + line-count delta is enough) and confirm via `AskUserQuestion` before overwriting. Provide two options: "Proceed (back up and replace)" and "Cancel".

4. **On confirm:**
   - Create a timestamped backup dir: `~/.claude/.backup-cd-discovery-$(date +%Y%m%d-%H%M%S)/`
   - Copy the *currently installed* `cd-discovery` skill dir and agent file into the backup dir, preserving structure.
   - Copy the repo versions over the installed paths (same `cp` commands as Step 3a steps 2 & 3).
   - **Do not touch `~/.claude/agent-memory/continuous-delivery-strategist/`.** That's the agent's accumulated learnings across sessions. Preserve it.

5. Verify the post-update file list matches the repo.

Proceed to **Step 4**.

## Step 4 — Post-install verification

Report back to the user:

- The installed paths:
  - `~/.claude/skills/cd-discovery/` (list the 6 files)
  - `~/.claude/agents/continuous-delivery-strategist.md`
  - `~/.claude/agent-memory/continuous-delivery-strategist/` (preserved on update; empty on fresh install)
- For updates: the backup directory path so they can roll back if needed.
- How to invoke:
  - `/cd-discovery` — fresh discovery
  - `/cd-discovery --assess` — discovery + improvement roadmap
  - `/cd-discovery --update` — refresh an existing report
  - Full flag reference in `~/.claude/skills/cd-discovery/SKILL.md`

If `gh` CLI auth is set up (`gh auth status`), mention that the GitHub sub-playbook will run automatically on GitHub-hosted repos. If not, note that they can run `gh auth login` to enable it.

## Step 5 — Failure mode

If any step fails (permission denied, missing source file, copy error, disk full, etc.):

1. Surface the exact error to the user — full command, full error message.
2. **Stop.** Do not attempt to "fix" by retrying with different paths, reordering steps, or leaving the install partially complete.
3. If a backup was created (update path) and the new copy failed midway, tell the user the backup is intact at the timestamped path and they can manually restore by `cp -R` from the backup.
4. Do not delete the backup directory regardless of outcome — let the user clean it up after verifying things work.
