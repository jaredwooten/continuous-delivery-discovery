# Plan: Fix `cd-discovery` subagent blocking on user interview

## Context

`skills/cd-discovery/SKILL.md` spawns the `continuous-delivery-strategist` agent as a headless subagent (via the `Agent` tool) to run automated discovery. The spawn prompt instructs the subagent to, after scanning, "present a summary and interview the user about gaps using `AskUserQuestion`" (unless `--skip-interview` is set).

This doesn't work. A subagent dispatched via the `Agent` tool has no live channel back to the actual human — it runs to completion and returns a single result. `AskUserQuestion` only functions in the top-level loop that is actually talking to the user. In practice this has manifested as the subagent recognizing it wants to ask a clarifying question but having no way to do so, and silently skipping the interview rather than hanging or erroring.

The `continuous-delivery-strategist` agent is also used **standalone** — invoked directly as the main agent in a conversation (e.g. "Our deployments take 3 hours and we only deploy once a week..."). In that mode it correctly interviews the user per Core Operating Principle #1, because it *is* the thing talking to the user. The fix must not touch that path — only the headless-subagent path spawned by the skill.

**Fix.** Never instruct the subagent to call `AskUserQuestion`. It always tags gaps with `[NEEDS CLARIFICATION: <specific question>]` (today's `--skip-interview` behavior becomes unconditional for the subagent). The skill's top-level orchestrator — which already runs `AskUserQuestion` successfully for the W1–W5 prompts — reads the returned `findings.md` after the scan, interviews the user about any tagged gaps itself, and folds the answers back in by auto-invoking the **existing** "Spawn the Update Agent" path (no new fold-in mechanism; reuse `UPDATE-PLAYBOOK.md`'s verify/edit/revision-log phases).

`--skip-interview` changes meaning slightly: it no longer changes subagent behavior (tagging is now unconditional) — it now controls whether the top-level orchestrator runs the post-scan interview step at all.

---

## Files to modify

All paths are absolute under `/Users/jwooten/dev/continuous-delivery-discovery/`.

| File | Edit type | Approximate insertion point |
|---|---|---|
| `skills/cd-discovery/PLAYBOOK.md` | Rewrite Phase 3 (drop interactivity, always tag with embedded question, delete 3.3); update Quality Gate line | Phase 3 (~lines 329-377); Quality Gate (~line 428) |
| `agents/continuous-delivery-strategist.md` | Add headless-mode line to §6 Discovery Mode, scoped to Discovery Mode only | §6 Discovery Mode, new step 1a |
| `skills/cd-discovery/SKILL.md` | Update `--skip-interview` doc line; simplify spawn-prompt interview conditional; add new "Interview Gaps" orchestration step; add fold-in framing note to Update Agent prompt; update Report Completion | Line 18; lines 111-112; new section after "Spawn the Agent"; "Spawn the Update Agent" `<objective>`; "Report Completion → Fresh-discovery path" |

---

## Detailed change set

### 1. `skills/cd-discovery/PLAYBOOK.md`

**Rename and rewrite Phase 3 header/intro** (currently line 329-331):

```
## Phase 3: Tag Gaps for Interview
```

Replace:
> **Skip this phase if instructed to skip the interview.** Tag all gap items with `[NEEDS CLARIFICATION]` in the output instead.

With:
> **You are a headless subagent.** You have no channel to interview the user directly — this is true regardless of `--skip-interview` or any other flag. Tag every gap item with `[NEEDS CLARIFICATION: <specific question>]`, embedding a concrete, evidence-grounded question directly in the tag (see 3.2's good/bad examples for the bar), so a human reader — or the top-level orchestrator that spawned you — can ask it verbatim later. Do not attempt to use `AskUserQuestion`.

**3.1 Present Summary** — keep the dimension-by-dimension summary format (still written into `summary.md`/`findings.md` as-is). Remove the line "Use `AskUserQuestion` to ask which dimensions the user wants to discuss. Offer options for each dimension plus 'all' and 'none (write report as-is)'." — that decision now belongs to the top-level orchestrator, not the subagent.

**3.2 Deep-Dive Selected Dimensions** → repurpose as tag-writing guidance: for each gap, write one specific, targeted question (2-3 per dimension max) directly into its `[NEEDS CLARIFICATION: ...]` tag. Keep the existing good/bad examples (they're specificity guidance, still correct) but drop "Record all answers for inclusion in the output" (line 372) since there's no interview happening in this pass to record answers from.

**Delete 3.3 "Revise Assessments"** entirely from the subagent's job. Add a one-line note in its place: *Revision after answers happens later, in the top-level orchestrator's fold-in step (the Update Agent path) — not in this subagent invocation.*

**Quality Gate** (line 428): change
> User interviewed about gaps (unless skip-interview mode)

to:
> Every gap tagged `[NEEDS CLARIFICATION: <specific question>]` — the interview itself happens later, at the top-level orchestrator, never inside this subagent invocation.

---

### 2. `agents/continuous-delivery-strategist.md`

**Insert new step 1a into §6 Discovery Mode**, immediately after step 1 ("Read the playbook file first..."), and renumber steps 2-10 accordingly:

> 1a. **You are headless in Discovery Mode.** When spawned via the `cd-discovery` skill for automated discovery, you have no interactive channel to the user — never call `AskUserQuestion` in this mode, even where Phase 3 of the playbook or Core Operating Principle #1 would otherwise have you prompt the user. Tag every gap per Phase 3 instead. This restriction is scoped to Discovery Mode only: when you are invoked directly as the main agent in a conversation (not spawned by the skill), continue interviewing the user per Core Operating Principle #1 as usual — you have a real channel to them in that case.

No other changes to this file — Core Operating Principle #1 (general standalone-use interview behavior) is untouched.

---

### 3. `skills/cd-discovery/SKILL.md`

**Line 18** — argument doc, change:
> `--skip-interview` — skip the interactive gap interview; tag gaps with `[NEEDS CLARIFICATION]`

to:
> `--skip-interview` — skip the post-scan interview step; leave gaps tagged `[NEEDS CLARIFICATION]` in `findings.md`

**Lines 111-112** (inside the "Spawn the Agent" prompt template) — delete both conditional lines:
```
{If --skip-interview: "Skip the interactive interview. Tag all gaps with [NEEDS CLARIFICATION] instead."}
{If NOT --skip-interview: "After scanning, present a summary and interview the user about gaps using AskUserQuestion."}
```
Replace with one unconditional line (applies regardless of `--skip-interview`):
```
You are being spawned as a headless subagent for automated discovery — you have no channel back to the user. Do not call AskUserQuestion. Tag every gap per Phase 3 of the playbook, with a specific, targeted question embedded directly in each [NEEDS CLARIFICATION: ...] tag.
```

**New section — "## Interview Gaps"** — insert after "## Spawn the Agent" and before "## Spawn the Update Agent". Applies only to the fresh-discovery paths (W1/W2); W3/W4/W4-scoped/W5 don't scan for new gaps and are unaffected.

```markdown
## Interview Gaps

Runs after the fresh-discovery agent (W1/W2) returns and `cd-discovery/findings.md` has been written, before Report Completion.

1. If `--skip-interview` was passed: skip this section entirely. Report completion with gap count only (tags remain in place).
2. Read `cd-discovery/findings.md` and locate every `[NEEDS CLARIFICATION: <question>]` tag, grouped by the dimension section it appears under.
3. If none found: skip to Report Completion.
4. Otherwise, present the dimension-by-dimension summary (level, key findings, gap count per dimension — same format as the removed Phase 3.1) and use `AskUserQuestion` to ask which dimensions the user wants to discuss: options are each dimension with gaps, plus "all" and "none (leave tagged)".
5. If the user picks "none": skip to Report Completion with tags left in place.
6. For each selected dimension, ask its extracted targeted question(s) via `AskUserQuestion` (2-3 per dimension, batched into as few calls as the tool allows).
7. Assemble every question+answer pair into a single context string, one entry per resolved gap:
   ```
   Dimension: <name>
   Q: <the [NEEDS CLARIFICATION] question text>
   A: <user's answer>
   ```
8. Automatically invoke "Spawn the Update Agent" (below) using this assembled string as the `INLINE` context — do not prompt the user again for `--update`-style context; this *is* that context.
```

**"Spawn the Update Agent" `<objective>` block** — add one conditional sentence for this auto-invoked case:
```
{If auto-invoked from the post-scan Interview Gaps step:} This context is answers from the interview immediately following a fresh discovery. Resolve each matching [NEEDS CLARIFICATION] tag directly — replace it with the resolved finding and revised level/confidence. Tags with no matching answer stay as [NEEDS CLARIFICATION].
```

**"Report Completion → Fresh-discovery path"** — add a line covering the interview outcome:
> If the Interview Gaps step ran: report how many gaps were found, how many were resolved via interview, and how many remain `[NEEDS CLARIFICATION]`. Remind the user to `git diff cd-discovery/` before committing, same as the Update path.

---

## Verification

1. Run `/cd-discovery` (no flags) against a repo with real gaps. Confirm the subagent returns promptly — no hang, no attempted `AskUserQuestion` call — and `findings.md` contains `[NEEDS CLARIFICATION: <specific question>]` tags.
2. Confirm the Interview Gaps step fires: dimension summary is displayed, `AskUserQuestion` is actually invoked at the top level, answers are collected.
3. Confirm the auto-invoked Update Agent resolves the tags — `git diff cd-discovery/` shows the tags replaced with resolved findings and a new revision-log entry appended.
4. Run `/cd-discovery --skip-interview`. Confirm tags are left in place, no interview is attempted, and the completion report shows gap count only.
5. Invoke the `continuous-delivery-strategist` agent directly in a plain conversation (not via the skill). Confirm it still asks discovery questions normally — regression check that standalone Core Operating Principle #1 behavior wasn't silenced by the Discovery Mode change.
6. `grep -n "AskUserQuestion" skills/cd-discovery/PLAYBOOK.md` — should return zero matches (the subagent playbook never references the tool after this change).
