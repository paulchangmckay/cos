---
name: think
description: Run a quiet 15-minute thinking block with four fixed questions, save the answers verbatim, then reflect them against the user's context. Use when the user asks to think, reflect, or start the thinking block.
---

# Thinking block

Four fixed questions, asked one at a time, answered without feedback. Follow [AGENTS.md](../../../AGENTS.md) and [writing style](../../../docs/writing-style.md). Background and boundaries are in [thinking block](../../../docs/thinking-block.md). Paths below resolve from the repository root.

1. What's going well?
2. What's not?
3. What am I avoiding?
4. What needs to change?

## Before the questions

Check `thinking/` for a file named for today's date, using the [date rules](../../../docs/context-handling.md#dates-and-periods). If one exists, say so in one sentence and ask whether to add a second session or review that entry. Otherwise start.

Read no other context yet. Priorities, projects, and past entries would shape the user's answers. Reading comes after the answers.

Open with exactly this, then question 1:

> Fifteen minutes. Close other apps and turn on Do Not Disturb. Write unedited. I will only ask the questions and will not respond until the end.

## During

After each answer, reply with the next question and nothing else. No acknowledgement, praise, advice, reassurance, or follow-up. Short answers are complete answers.

- If the user writes "pass", record "Skipped" and move on.
- If the user asks something unrelated, reply "Parked until the end." and keep a note of it.
- If the user says time is up, go to the close with the answers so far.
- The agent cannot measure time. Never claim to.

## Save, then reflect

After question 4, save before saying anything else. Write to `thinking/YYYY-MM-DD.md`, using this shape:

```markdown
# YYYY-MM-DD

**What's going well?**
The user's words, exactly as typed.

**What's not?**
...

**What am I avoiding?**
...

**What needs to change?**
...

**Parked:** only if something was parked.
```

Save verbatim. Do not correct spelling, tidy sentences, or summarize. A second session on the same day goes under `## Session 2` in the same file. Create the file only after the answers exist.

Then give one short reflection in prose. Now read `priorities.md`, the last seven files in `thinking/`, relevant `projects/` files, and, when `one-on-ones/` exists, run `python3 scripts/one_on_one.py roster --today YYYY-MM-DD`.

- Set what the user said they are avoiding beside what the files show. Name an overdue one-on-one, an old open ask, or a stalled priority when one fits. Keep observation apart from interpretation.
- If the same avoidance appears in three or more of the last seven entries, say so with the dates. Offer to record the pattern under development context in `self.md`. Write it only if the user agrees.
- End with one decision the user could make today. Then offer `/morning`.

Missing evidence does not mean there is nothing to avoid. Do not diagnose or use clinical labels. Say less when the entry says little.

## Boundaries

Entries are private. Never copy them into `daily/` (eod owns that), a one-on-one record, a commit, or a message. Do not quote them to anyone else. Send no messages and change no calendars. This workflow authorizes only the entry file and, with agreement, one `self.md` line.
