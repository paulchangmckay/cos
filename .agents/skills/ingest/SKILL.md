---
name: ingest
description: Process requested meeting sources or notes into a strategic read and material local context. Ordinary thinking aloud stays conversational.
---

# Ingest context

Help the user understand what the material changes, why it matters, and what deserves further thought or action. The chief-of-staff read is the purpose of the workflow. Source preservation and warranted context updates support it. Follow [AGENTS.md](../../../AGENTS.md) and [writing style](../../../docs/writing-style.md); paths below resolve from the repository root.

Use the supplied input or a source discovered through an explicitly enabled workflow in `sources.local.md`. If neither is present, ask for input. Ordinary thinking aloud does not select ingest or authorize saving; a request to process or capture sources can select it in natural language. Read only supplied material and relevant configured sources.

## Ground the interpretation

For transcripts, preserve the original before interpreting it under [source preservation](references/source-preservation.md). That reference also routes configured Gemini intake, versioning, deduplication, and retry bookkeeping. Ordinary notes need no transcript archive. Keep source evidence distinct from generated notes and interpretation.

Use the [date and source rules](../../../docs/context-handling.md#dates-and-periods). Read relevant local role, stakeholder, priority, team, and project context, following canonical profiles. Before project-specific assessment, read the configured workspace's `STATUS.md` under [linked-workspace handling](../../../docs/context-handling.md#linked-project-workspaces). Missing context is a visibility gap. Verify unfamiliar or inconsistent names before adding them to records.

Read original passages when nuance could change the judgment. Cross-reference people and topics that matter to the material; avoid loading unrelated context merely because files exist.

## Develop and discuss the read

Form a considered interpretation and develop its strongest observations. Explain the detail that led to a read, the human or organizational significance, and the implication for the user's choices. Explore a credible alternative when it changes the assessment. Avoid retelling everything in the source or merely extracting commitments.

Consider power, incentives, information asymmetry, trust, autonomy, how the user showed up, and second-order consequences where the source supports them. Distinguish observed behavior from possible motives in ordinary language. Interesting possibilities and progress deserve attention as well as problems.

Help the user hold a strategic perspective: what does this change about direction, priorities, their role, or where their involvement matters? Make relevant cross-project connections. Use the applicable [advisory lens](../../../docs/advisory-lenses.md) for delivery risk, capacity, or coaching without turning the response into an audit or requiring named stages.

Lead the conversation with what is worth discussing. Give important reasoning room to develop, and leave space for the user to disagree or explore it further. Do not force a recommendation, question, or quota of insights. When the source changes little, say so briefly. This workflow produces a strategic read; a shareable meeting summary requires its own request. When called within morning intake, carry material findings into the briefing rather than issuing a receipt for each source.

## Update durable context

Apply the [writeback policy](../../../docs/context-handling.md#writeback-policy). Save only material changes to understanding or future action. A familiar pattern may deserve deeper conversation without another record. Keep exploratory interpretations appropriately qualified; do not save a possible motive as a fact.

Keep linked-project updates strategic. Reconcile indexed relationships alongside affected prose under the [structured-context rules](../../../docs/context-handling.md#structured-context-pilot). Coaching files hold lasting patterns, not isolated commitments. A no-change decision is valid. Keep any useful save receipt brief and after the substantive read; do not narrate routine mechanics.

External action items stay in their existing trackers. Ingest authorizes no messages, Jira changes, or calendar writes. Do not write to `daily/*.md`; eod owns daily synthesis. Reusable framework changes follow [CONTRIBUTING.md](../../../CONTRIBUTING.md); ignored context updates need no Git commit.
