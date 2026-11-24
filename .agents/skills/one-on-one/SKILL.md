---
name: one-on-one
description: Prepare for, capture, or review a one-on-one with a team member using the three standard questions, or show which one-on-ones are due. Use when the user asks to prep, debrief, or review one-on-ones.
---

# One-on-ones

Every one-on-one asks the same three questions in the same words. Follow [AGENTS.md](../../../AGENTS.md) and [writing style](../../../docs/writing-style.md). The format, file shape, statuses, and boundaries are in [one-on-ones](../../../docs/one-on-ones.md). Paths below resolve from the repository root.

1. What's working?
2. What's frustrating?
3. What do you need from me?

Pick the mode from the request. Say nothing about modes or file operations in chat.

## Identify the person

Match the name to an existing `one-on-ones/<name>.md`, then to `people/` and `team/`. If two people could match, or none does, ask once. Do not create a record for a person the user has not confirmed. A new record starts from [the template](../../../templates/one-on-one.md), saved under `one-on-ones/` with a lowercase hyphenated name.

## Prep

Use when the user is about to meet someone.

1. Read `one-on-ones/<name>.md`: open asks, the last log entry, the current picture. Read the person's `team/` and `people/` files and any project the user names.
2. Give a short prep. Lead with asks the user still owes, with their age. Add at most two specific follow-ups from the last entry or recent work. Say plainly when there is nothing to add.
3. Offer the three questions verbatim. Do not add more.

Prep saves nothing.

## Capture

Use after the meeting. The source decides how.

**`gemini`.** Intake or ingest has found a transcript. It is a one-on-one when it is a two-person meeting and the other person has a record in `one-on-ones/` or the user names them as a direct report. If unsure, ask once. Preserve the original transcript first under the [source preservation](../ingest/references/source-preservation.md) rules. Take answers only from what the person said.

**`notes`.** The user pastes notes. Map them to the three questions. Keep the person's words where the notes have them.

**`memory`.** The user has no notes. Ask the three questions one at a time, in the user's words, and wait for each answer. Then ask only: "Did you commit to anything?" Stop there. The interview should take about two minutes. Record the source as `memory` and state under the entry that it is the user's recollection of what the person said, not a quote.

In every mode:

- An unanswered question is written "Not discussed". Never infer an answer.
- Put interpretation on its own line starting "My read:". Do not record a possible motive as fact.
- Add a dated entry at the top of `## Log` with the source in the heading.
- Turn each concrete "need from me" into a line under `## Open asks`, dated today. Ask the user what they answered, and record it. Do not assume it was accepted.
- Close an ask the user says is finished: mark the box and add the date.
- Rewrite `## Current picture` only when the picture changed. Apply the [writeback policy](../../../docs/context-handling.md#writeback-policy). Promote a lasting pattern to `team/<name>.md` only if it passes the six-month test.
- Do not write to `daily/`. Eod owns it.

Give the user a short read first: what stood out, what they now owe, and whether anything changes their priorities. Add a one-line save receipt after.

## Team review

Use when the user asks who is due, how the team is doing, or what is coming up across their one-on-ones.

1. Run `python3 scripts/one_on_one.py roster` with `--today` set to the user's date.
2. Read the records flagged overdue, due, or holding old asks.
3. Report who needs a meeting, which asks are oldest, and which frustrations recur across people. State the count and the names, and qualify what the evidence cannot show.
4. Weigh the open asks against the user's capacity using the absorbability lens in [advisory lenses](../../../docs/advisory-lenses.md). Name asks that quietly change the user's role.

A quiet record is not a problem. Do not score or rank people.

## Boundaries

Records are private. Send no messages and change no calendars. A request for this workflow authorizes only the local record updates above.
