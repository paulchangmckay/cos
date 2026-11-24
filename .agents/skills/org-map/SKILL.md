---
name: org-map
description: Build or update a sourced local map of reporting lines, team remits, and decision ownership when the user asks to map an org, understand a reporting chain, or identify relevant stakeholders.
---

# Map org structure

Follow [AGENTS.md](../../../AGENTS.md) and [writing style](../../../docs/writing-style.md), using relevant [date, source, and context rules](../../../docs/context-handling.md). Resolve project paths from the repository root. Company data stays in ignored `org/`; reusable instructions never contain employee records. Keep routine mapping mechanics out of chat.

Use the scope in the user's request. For onboarding, a useful starting point is their manager chain, immediate peer group, and the adjacent functions they need to work with. A request merely to test directory access does not authorize creating a full employee roster.

## Establish formal facts

Read `sources.local.md` for the current employee directory, Confluence site, and authorized access method. Prefer a documented supported API or export when available. Otherwise, use the signed-in browser through the available browser tools. Verify search results and reporting links on the visible page. Do not infer a reporting line from shared attendance, department names, or titles alone.

Capture names, work roles, departments, manager relationships, relevant remit, profile/source links, and observation dates for the requested scope. Avoid collecting personal contact details or unrelated profile information. Directory data supports navigation and relationship mapping; it is not a headcount audit.

Use Confluence for documented team ownership and decision rights. Read the relevant source, not just a search title. Note its version or date. Check names against profiles when transcript spelling is uncertain.

## Distinguish structure from influence

Formal reporting, documented decision authority, and inferred influence are different claims. Record each with its source and confidence. A senior title does not prove that someone owns a particular decision. Treat impressions from meetings as interpretation, and surface gaps or conflicting evidence plainly.

Keep formal structure in `org/structure.md` or a focused file in `org/`. A compact relationship table or reporting tree is appropriate. Strategic relationship reads belong in the canonical stakeholder profile under the [writeback policy](../../../docs/context-handling.md#writeback-policy); follow moved profiles from `stakeholders.md` rather than recreating them there.

## Save within the requested scope

A request to build, save, or update the local map authorizes those scoped org files. Present meaningful changes when appropriate and follow the current user's permissions. Do not create unrelated stakeholder profiles or silently replace earlier evidence.

Keep source links and observation dates beside the facts. Update what changed; avoid accumulating duplicate snapshots. Write no company content into tracked framework files. Do not upload or sync the map to personal Drive or publish it to Confluence unless explicitly requested.

State which branches were covered and what remains unknown. Develop the practical implication when it matters to the user's decision: where influence may be needed, whose remit requires verification, or how to sequence a conversation. Distinguish that interpretation from directory facts and avoid manufacturing political dynamics. Keep any save receipt brief.
