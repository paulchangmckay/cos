---
name: morning
description: Prepare a conversational chief-of-staff morning briefing when the user asks to start the day, orient priorities, or review what matters today.
---

# Morning briefing

Help the user see where their attention matters today and why. Bring a chief-of-staff perspective on the decisions, relationships, and outcomes in play. Follow [AGENTS.md](../../../AGENTS.md) and [writing style](../../../docs/writing-style.md), using the [date and source rules](../../../docs/context-handling.md#dates-and-periods). Paths below resolve from the repository root.

The user may open with loosely formed thoughts. Gather enough context to engage, then follow their thread. Do not deliver a static report merely because this workflow is called a briefing. Routine intake happens in the background; the conversation does not need a workflow announcement or a list of completed steps.

## Gather and refresh context

Read `sources.local.md`, the most recent daily synthesis, `priorities.md`, and relevant stakeholder or project context when present. Daily files show past calls and trajectory; durable files establish current state. Before project-specific assessment, read configured workspace status under [linked-workspace handling](../../../docs/context-handling.md#linked-project-workspaces). Missing local files are normal.

When Gemini email intake is enabled for a configured mailbox, follow [meeting intake](../../../docs/meeting-intake.md) before forming the briefing. Retry pending sources, complete discovery pagination, and apply [ingest](../ingest/SKILL.md) to material changes. Preserve actual transcripts and their source status; complete ingestion only after archival and context reconciliation. Unchanged completed sources need no duplicate processing, and notes-only sources remain eligible for transcripts.

A failed document does not block the rest of the briefing. Explain coverage gaps that affect the read and keep failed intake retryable. No configured mailbox means no automatic mailbox search; manual ingest remains available. Leave email read state, labels, and Drive content unchanged.

If classified activity logs are configured, run `python3 scripts/synthesis.py --date YYYY-MM-DD` for yesterday in the user's timezone, using the configured `--root` or `CHIEF_OF_STAFF_LOG_DIR`. A nonzero exit means missing evidence; report the gap and check the configured source. With no tracker, use supplied context and state material visibility limits. Never infer inactivity from missing logs.

Read today's calendar through an available connector for the configured account. Reuse relevant local source archives; there is no last-24-hours meeting-folder scan. If priorities are over ten days old, treat them as potentially stale and invite a refresh when it matters. On Monday, also read the last three to five daily files and the week's calendar when available.

## Engage

Respond to the user's opening with a considered view of what deserves attention. Explain why a decision, relationship, opening, or consequence window matters. Connect the day to the user's larger priorities. Distinguish work needing their judgment or influence from work another owner can carry; help them choose where hands-on involvement is worthwhile. A calendar full of tasks is not itself a strategic agenda.

Use relevant [advisory lenses](../../../docs/advisory-lenses.md), including the risk gate before elevating concerns. Surface adoption, impact, or communication checks coming due when material. Coaching has no quota and should not repeat a recent nudge without new evidence. Develop a worthwhile observation rather than listing everything gathered. Ask when an answer changes the read, and let a clear day leave room to focus.

## One-on-ones today

When the calendar shows a one-on-one with someone who has a record in `one-on-ones/`, offer the [one-on-one](../one-on-one/SKILL.md) prep for that person. Run `python3 scripts/one_on_one.py roster --today YYYY-MM-DD` and mention overdue people only when it changes the day's choices.

## Priorities refresh and local outputs

On Monday, refresh priorities from what the user says is moving this week, and ask only when that is unclear. Refresh on other days when the user asks or supplies a material priority change. Update `priorities.md` from that conversation, including today's `**Last refreshed:**` date.

Local outputs include the pre-briefing source archive and intake record, material writebacks through ingest, and priorities refresh. Follow the [writeback policy](../../../docs/context-handling.md#writeback-policy). Give a short save receipt only when useful, after the substantive discussion. Leave `daily/*.md` to eod. No external writes are included.
