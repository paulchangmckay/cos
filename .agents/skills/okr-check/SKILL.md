---
name: okr-check
description: Review evidence-based OKR progress for the user, a named team member, or the team using linked Jira issues and relevant Confluence documentation.
---

# Check OKRs

Help the user judge progress toward intended outcomes and choose where their leadership matters next. Follow [AGENTS.md](../../../AGENTS.md) and [writing style](../../../docs/writing-style.md), using the [date and source rules](../../../docs/context-handling.md#dates-and-periods). Paths below resolve from the repository root. Missing context files are normal; work from supplied evidence and identify material gaps.

Use the scope in the user's request: `self`, a team member's name, or `team`. Clarify when scope is unclear. Read the OKR file for the current quarter, or the quarter explicitly requested. Do not substitute the newest filename for the requested period.

## Verify source evidence

Jira is the work-tracking source; Confluence is the documentation and knowledge source. Use the account and site configured in `sources.local.md`.

For every linked Jira issue, read the current issue and relevant comments or activity through available connected tools. Resolve the issue key from its `/browse/KEY-123` URL or use a supplied key. Discover comment and history read capabilities as needed; a comment count is not the comments themselves.

Check status, assignee, due date, acceptance criteria, blockers, and issue links. For an epic or parent, inspect relevant child issues and coverage before claiming completion. Paginate comments, changelogs, or child searches when needed for the assessment; avoid treating a partial page as the complete record.

Read linked or directly relevant Confluence pages for commitments, definitions of success, decisions, and evidence of impact. Cite the source page and its date or version where relevant. Issue closure establishes workflow completion; it does not establish a measured business outcome.

If Jira is unavailable or an issue is inaccessible, identify the gap, use supplied evidence where possible, and label that KR unverified. Do not call an unverified KR on track by default. An old update is an evidence gap; apply the [risk gate](../../../docs/advisory-lenses.md#reassessing-risk) before treating it as delivery risk.

Chase open threads in local source archives or configured meeting sources before asking whether a conversation happened. Find meetings by person, topic, and date. Read the original for decisions and commitments. State when meeting evidence is unavailable.

Cross-reference `priorities.md`, relevant `projects/*.md`, and the [operating loop](../../../docs/advisory-lenses.md#delivery-and-the-operating-loop). Read relevant configured project status under [linked-workspace handling](../../../docs/context-handling.md#linked-project-workspaces). Watch for unvalidated work, substantial effort absent from the OKR ledger, and shipped work awaiting measured impact or a recorded outcome.

## Assess and advise

For verified KRs, assess on track, at risk, behind, or blocked from the evidence. Cite specific issues, Confluence passages, or transcript details with source links and dates. Explain what moved, what matters next, and any actual blocker. Apply the risk gate before assigning at risk or behind.

For team members, prepare specific 1-1 questions, earned praise, and matters worth probing. Group them by person. For a broader review, surface systemic blockers, common dependencies, and capacity or attention patterns when warranted.

Lead with the main judgment and develop the reasoning that matters. Explain strategic tradeoffs, capacity questions, and what needs the user's influence versus an owner's execution. An OKR grid is appropriate for comparisons; it supports the conversation. Do not make an advisor read an optional closing addendum or force named stages into every assessment. Avoid manufacturing concern or praise, and keep routine verification mechanics out of chat.

This is a read-only review. Changes to OKR files, durable context, Jira, Confluence, or calendar items require a request or existing authorization for the specific change.
