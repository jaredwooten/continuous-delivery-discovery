# INSTALL.md — Agent-followable install playbook

**Audience:** an agent running inside Claude Code (you). The user has asked you to install or update this bundle. Follow these steps in order. If anything is ambiguous, stop and ask the user via `AskUserQuestion` — do not improvise.

**What gets installed:**
- The `cd-discovery` skill → `~/.claude/skills/cd-discovery/` (6 files)
- The `continuous-delivery-strategist` agent → `~/.claude/agents/continuous-delivery-strategist.md`
- An agent-memory directory → `~/.claude/agent-memory/continuous-delivery-strategist/` (created empty on fresh install; preserved as-is on update)

**Install methods (two options):**
- **Copy** (recommended for most users) — files are copied into `~/.claude/`. The cloned repo can move or be deleted afterward. Updates require re-running this playbook against a fresh `git pull`.
- **Symlink** (for contributors / dogfooders) — `~/.claude/skills/cd-discovery` and `~/.claude/agents/continuous-delivery-strategist.md` become symlinks to the cloned repo. Edits in the repo apply live to your Claude Code sessions. Updates are just `git pull` inside the cloned repo — no copying or backup needed. **Caveat:** if you delete or move the cloned repo, the symlinks dangle and the skill silently fails to load.

## Step 1 — Detect mode (fresh vs update) and installed method

Check whether both install targets already exist:

- Does `~/.claude/skills/cd-discovery` exist (as a directory **or** as a symlink)?
- Does `~/.claude/agents/continuous-delivery-strategist.md` exist (as a file **or** as a symlink)?

Use `test -e` (not `test -d` / `test -f`) so symlinks count as present.

Mode resolution:

| Skill | Agent | Mode |
|---|---|---|
| Missing | Missing | **Fresh install** — go to Step 3a |
| Present | Present | **Update** — go to Step 3b |
| One present, one missing | | **Partial install detected.** Ask the user via `AskUserQuestion` whether to (a) treat it as a fresh install and replace whatever is there, or (b) abort so they can investigate manually. Do not guess. |

**If mode is Update**, also detect the installed method by checking whether the targets are symlinks (`test -L`):

- Both are symlinks pointing into a cloned copy of this repo → **symlinked install** (use Step 3b-link)
- Neither is a symlink → **copied install** (use Step 3b-copy)
- Mixed (one symlink, one regular) → ask the user how to proceed; don't guess

**If mode is Fresh install**, ask the user via `AskUserQuestion` which method to use:

- "Copy (recommended) — files copied into `~/.claude/`; cloned repo is no longer needed afterward."
- "Symlink (for contributors) — `~/.claude/` entries link to the cloned repo; edits + `git pull` flow directly."

Record the chosen method and proceed to Step 3a-copy or Step 3a-link.

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

## Step 3a-copy — Fresh install (copy method)

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

## Step 3a-link — Fresh install (symlink method)

The user is running this from inside the cloned repo. Capture its absolute path first; symlinks must be absolute, not relative.

1. Resolve the absolute repo path:
   ```bash
   REPO_DIR="$(cd "$(pwd)" && pwd)"   # absolute path of cwd
   ```
   Sanity-check `$REPO_DIR/skills/cd-discovery/SKILL.md` exists. If not, abort — they're in the wrong dir.

2. `mkdir -p ~/.claude/agent-memory/continuous-delivery-strategist`

3. Create the skill symlink:
   ```bash
   ln -s "$REPO_DIR/skills/cd-discovery" ~/.claude/skills/cd-discovery
   ```

4. Create the agent symlink:
   ```bash
   ln -s "$REPO_DIR/agents/continuous-delivery-strategist.md" ~/.claude/agents/continuous-delivery-strategist.md
   ```

5. Verify with `ls -la` — both targets should show as symlinks (`l...`) pointing into `$REPO_DIR`. Then `ls ~/.claude/skills/cd-discovery/` should list all 6 skill files (visible through the symlink).

Proceed to **Step 4**. Mention to the user that future updates are just `git pull` from inside the cloned repo — no need to re-run this playbook.

## Step 3b-copy — Update (copy method)

1. **Diff each repo file against its installed counterpart.** For each of the 7 files:
   - Repo: `skills/cd-discovery/<file>.md` or `agents/continuous-delivery-strategist.md`
   - Installed: `~/.claude/skills/cd-discovery/<file>.md` or `~/.claude/agents/continuous-delivery-strategist.md`

   Use `diff` (or compare hashes). Track which files differ.

2. **If no files differ** — tell the user "Already up to date." and exit. Do not write anything.

3. **If any files differ** — summarize the changes to the user (filename + line-count delta is enough) and confirm via `AskUserQuestion` before overwriting. Provide two options: "Proceed (back up and replace)" and "Cancel".

4. **On confirm:**
   - Create a timestamped backup dir: `~/.claude/.backup-cd-discovery-$(date +%Y%m%d-%H%M%S)/`
   - Copy the *currently installed* `cd-discovery` skill dir and agent file into the backup dir, preserving structure.
   - Copy the repo versions over the installed paths (same `cp` commands as Step 3a-copy steps 2 & 3).
   - **Do not touch `~/.claude/agent-memory/continuous-delivery-strategist/`.** That's the agent's accumulated learnings across sessions. Preserve it.

5. Verify the post-update file list matches the repo.

Proceed to **Step 4**.

## Step 3b-link — Update (symlink method)

For symlinked installs, "update" is just pulling the cloned repo. There's nothing to copy and no backup is needed — the symlinks already point at the files `git pull` is about to change.

1. Resolve the cloned repo path from the existing symlink:
   ```bash
   SKILL_LINK_TARGET="$(readlink ~/.claude/skills/cd-discovery)"
   REPO_DIR="$(cd "$(dirname "$(dirname "$SKILL_LINK_TARGET")")" && pwd)"
   ```
   `$REPO_DIR` should now be the repo root. Confirm `$REPO_DIR/.git/` exists; if not, abort — the symlink target isn't a git checkout and you can't safely update.

2. Check working-tree state in the repo:
   ```bash
   git -C "$REPO_DIR" status --porcelain
   ```
   - If the output is empty (clean tree) → proceed to step 3.
   - If there are uncommitted changes → surface them to the user via `AskUserQuestion` with options: "Stash and pull", "Pull anyway (may conflict)", "Cancel". Do not silently overwrite local changes.

3. Pull:
   ```bash
   git -C "$REPO_DIR" pull --ff-only
   ```
   If the pull fails (non-fast-forward, network error, conflict), surface the exact error and stop — do not retry with `--rebase` or `--force` unless the user asks for it.

4. Report what changed since the last pull (one-line summary of the diff range is enough). The symlinks haven't changed; the underlying files have.

5. **Do not touch `~/.claude/agent-memory/continuous-delivery-strategist/`.** Preserved as-is.

Proceed to **Step 4**.

## Step 4 — Post-install verification

Report back to the user:

- The installed paths:
  - `~/.claude/skills/cd-discovery/` (list the 6 files; for symlinked installs, note the symlink target)
  - `~/.claude/agents/continuous-delivery-strategist.md` (for symlinked installs, note the symlink target)
  - `~/.claude/agent-memory/continuous-delivery-strategist/` (preserved on update; empty on fresh install)
- Install method used: **copy** or **symlink** — say so explicitly, since the update flow differs.
- For copy-method updates: the backup directory path so they can roll back if needed.
- For symlinked installs: remind them that future updates are just `git pull` inside the cloned repo (no need to re-invoke this playbook), and warn that deleting/moving the cloned repo will break the install silently.
- How to invoke:
  - `/cd-discovery` — fresh discovery
  - `/cd-discovery --suggest` — discovery + suggestions.md (gaps, tradeoffs, dependency map)
  - `/cd-discovery --update` — refresh an existing report
  - Full flag reference in `~/.claude/skills/cd-discovery/SKILL.md`

If `gh` CLI auth is set up (`gh auth status`), mention that the GitHub sub-playbook will run automatically on GitHub-hosted repos. If not, note that they can run `gh auth login` to enable it.

## Step 5 — Failure mode

If any step fails (permission denied, missing source file, copy error, broken symlink, `git pull` conflict, disk full, etc.):

1. Surface the exact error to the user — full command, full error message.
2. **Stop.** Do not attempt to "fix" by retrying with different paths, reordering steps, or leaving the install partially complete.
3. **Copy-method updates:** if a backup was created and the new copy failed midway, tell the user the backup is intact at the timestamped path and they can manually restore by `cp -R` from the backup. Do not delete the backup directory regardless of outcome — let the user clean it up after verifying things work.
4. **Symlink-method updates:** if `git pull` fails (conflict, non-fast-forward, network error), the existing symlinks still point at the pre-pull state of the working tree, so the install is in a consistent state — surface the git error and let the user resolve it manually.
5. **Symlink-method fresh installs:** if symlink creation fails after the backup move (in a partial-install repair scenario), tell the user where the backup lives and stop — do not try to fall back to copy mode without asking.
