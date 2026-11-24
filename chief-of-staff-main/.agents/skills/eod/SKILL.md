---
name: eod
description: Write a chief-of-staff end-of-day synthesis when the user asks to close the day or save today's strategic account for tomorrow's briefing.
---

# End-of-day synthesis

Make sense of the day with the user and save the account worth carrying into tomorrow. Develop a view of what changed, what it means, and which choices deserve attention. Follow [AGENTS.md](../../../AGENTS.md) and [WRITING.md](../../../WRITING.md), using the [date and source rules](../../../docs/context-handling.md#dates-and-periods). Paths below resolve from the repository root.

Save a prose account to `daily/YYYY-MM-DD.md` using today's date in the user's timezone. A request for this workflow authorizes the daily file and material local writebacks under the [writeback policy](../../../docs/context-handling.md#writeback-policy). Missing local files are normal.

## Gather evidence

If classified activity logs are configured, run `python3 synthesis.py --date YYYY-MM-DD` for today with the configured source. A nonzero exit means the scanner supplied no valid summary. Report the gap; proceed only from other adequate supplied or authorized local evidence, or ask for context. With no tracker, work from supplied context and local sources; ask only if there is too little evidence to write a truthful account. State the account's evidence coverage. Missing logs never mean a quiet day.

Read `sources.local.md`, today's existing daily file, relevant preserved meeting sources, `priorities.md`, and relevant stakeholder and project context. Before project-specific assessment, read configured status under [linked-workspace handling](../../../docs/context-handling.md#linked-project-workspaces). Use the last three to five daily files for trajectory and revisit prior calls when relevant. Read authorized original session transcripts when a thin summary could change the judgment. Do not run a second mailbox discovery merely to close the day. Read tomorrow's calendar through an available connector for the configured account; explain material schedule gaps.

Preserve existing daily content and real calls. Reconcile new evidence rather than overwriting or duplicating the day's account.

## Develop the read

Explain what the day changes about the user's priorities, relationships, or larger direction. Notice a promising opening or an important decision as readily as an unresolved problem. Consider whether their attention went where their judgment mattered, and whether repeated tactical involvement reveals an ownership or capability question. Hands-on progress may have been the right investment; assess its purpose and consequence.

Use relevant [advisory lenses](../../../docs/advisory-lenses.md) for risk, delivery, capacity, and coaching. Develop meaningful connections across the evidence without forcing a verdict or lesson. The conversation should carry this interpretation, with a brief save receipt afterward. Do not recite the workflow or reproduce the daily file's headings in chat by default. If the user only asks to save a settled account, a concise confirmation is enough.

## Write the daily file

This is a saved-record shape, not a conversational template. Include sections only where the evidence warrants them:

```markdown
# YYYY-MM-DD

## What happened
Prose on what shifted strategically, with people, tensions, and consequences.

## What I'm watching
Only matters that clear the risk gate in the advisory lenses. Omit when empty.

## Tomorrow
The shape of the next day and specific preparation, when known.
```

Use a calendar table only if more than three meetings need preparation. A quiet day can be one paragraph when supported by evidence. Record meaningful calls with position, confidence, and what would falsify them. Flag shipped work lacking an adoption check, impact measurement, or communication date.

## Durable writebacks

Apply scoped local updates only when an observation materially transforms understanding under the writeback policy. A useful discussion can produce no durable update. Keep any receipt brief; the file operations are supporting work.

Follow [project ownership and writeback limits](../../../docs/context-handling.md#writeback-policy). For linked projects, keep CoS updates strategic and honor workspace write permissions. Reconcile changed indexed records under the [structured-context rules](../../../docs/context-handling.md#structured-context-pilot).

Keep coaching files focused on lasting patterns, not isolated commitments. Daily files remain a journal, not canonical stakeholder or project state. No external writes are included.
