---
name: onboard
description: Set up, resume, or refresh personal chief-of-staff context through a short interview when the user asks to get started or onboard. Applies to adviser context, not repository maintenance or model configuration.
---

# Get started

Follow [AGENTS.md](../../../AGENTS.md) and [WRITING.md](../../../WRITING.md), using the [date and context rules](../../../docs/context-handling.md#dates-and-periods). Paths below resolve from the repository root. Help the user establish enough local context for useful advice, then work on a real decision together. No connectors or Python are required. Keep routine mechanics out of chat.

## Start where the user is

Read existing `self.md`, `priorities.md`, and `sources.local.md` when present. Follow relevant links to existing project or stakeholder context only as needed. Missing files alone do not trigger this interview or block another requested workflow.

For a fresh start, briefly explain that you will ask a few questions and save useful context in private local files. The user can skip any topic or return later. Ask one or two focused questions per turn, then wait for their answer. Do not deliver the whole questionnaire at once or hide several questions inside each question.

A useful opening is: "What are you accountable for in your role, and what's one decision you'd like help with right now?" Adapt it to what the user has already supplied. Do not ask for their name, employer, or title again when those facts are known.

For a resumed interview, use the saved context to pick the next useful question. Briefly say what you already understand; do not restart. If the user wants to refresh an established setup, ask what has changed and preserve unrelated history and preferences.

## Develop the context through conversation

Cover what helps, in the order the conversation needs:

- **Remit:** responsibilities, ambitions, what success would change, and relevant decision boundaries. Understand which decisions need the user's judgment and where they want to build capability through others. Treat self-reported reporting lines and authority as self-reports, not verified directory facts.
- **Relationships and work:** the manager, peers, partners, and active projects that matter to the user's immediate problem. Ask about dynamics only when they affect the advice; a full org map is unnecessary.
- **Priorities:** the outcomes competing for attention, actual commitments or consequence windows, and any deliberate tradeoffs. Do not turn aspirations into commitments.
- **Adviser preferences:** how direct a challenge is useful, preferred response length, and anything that makes advice feel helpful or irritating. A concrete example can be more useful than an abstract tone label.
- **Sources:** offer optional source setup once you understand what would help. Accept supplied notes only as a complete, useful choice.

When a real problem arrives early, engage with it immediately. Ask the question that changes the decision, offer a grounded view when possible, and weave in the remaining setup naturally. Do not withhold useful advice until every topic is covered.

## Save as understanding develops

After a substantive answer, save the material supplied context before moving on. Use [templates/context.md](../../../templates/context.md) and its linked templates as guidance, not forms to fill. Create only files with useful content:

- `self.md` for role, mandate, and enduring adviser preferences.
- `priorities.md` for current agreed priorities and explicit tradeoffs, with the refresh date.
- Relevant stakeholder or project context only when supplied detail warrants a separate record. Follow existing canonical profiles rather than duplicating them.
- `sources.local.md` only for source choices the user actually makes.

Record that new facts are user-supplied and give their observation date using the context-handling date rules. Keep tentative interpretations distinct from facts. Read before editing, merge scoped additions, and preserve existing evidence and unrelated sections. Do not copy template prompts into live context or invent missing facts. All personal outputs remain ignored and follow the [writeback policy](../../../docs/context-handling.md#writeback-policy).

Briefly name what you saved. If writes are unavailable, say what remains unsaved and continue the conversation without claiming persistence. Do not create a separate questionnaire, completion flag, or setup tracker. Existing context is enough to resume.

## Configure sources only when chosen

Start from [templates/sources.local.md](../../../templates/sources.local.md). Ask which account and scope the user wants used for each chosen source; connected accounts alone do not establish that choice. Do not search email, calendars, directories, or assistant history to populate an interview without the relevant source authorization.

For morning Gemini intake, establish the mailbox, Docs identity that can read linked documents, and the user's choice to enable intake. Preserve existing source settings. Explain that morning briefing discovers notification emails and retrieves actual transcript tabs; no meeting folder needs maintaining. Follow [docs/meeting-intake.md](../../../docs/meeting-intake.md) when intake runs.

Distinguish a saved source configuration from working access. If the user requests an access check, use a bounded relevant read through an available connector and report what it establishes. Missing access can be handled later. Never request credentials in chat or claim that onboarding provisioned a connector, installed Python, or scheduled a background process.

## Finish with advice and orientation

Once there is enough context to help, give a first read on the user's real decision: what you would do, why, and the material uncertainty or next action. Do not invent a problem if they have none; explain that they can bring one later.

At the natural close of a first onboarding, give a compact, personalized introduction to working together. Briefly introduce all five everyday workflows, leading with those most relevant to the user's remit:

- [`$morning`](../morning/SKILL.md): orient priorities, prepare for the day, and discuss what deserves attention.
- [`$ingest`](../ingest/SKILL.md): develop a strategic read from sources the user asks to process; preserve supplied transcripts and save material changes to local context.
- [`$eod`](../eod/SKILL.md): capture the day's decisions and implications in a local daily synthesis.
- [`$okr-check`](../okr-check/SKILL.md): assess progress against available evidence and linked issues without changing the work tracker.
- [`$org-map`](../org-map/SKILL.md): map relevant reporting lines, remits, and decision ownership, keeping sourced facts separate from inferred influence.

Explain that ordinary language works: they can think aloud, bring an unfinished thought, correct facts, disagree with advice, or ask for a different tone. They do not need to memorize commands or turn every conversation into a named workflow. Thinking aloud alone does not start ingest or record maintenance.

Explain that useful context is saved selectively in ignored local files. A shared repository or separate clone does not carry those personal files. Connected sources are optional; describe only the sources actually configured and distinguish missing evidence from a confident assessment. These workflows run when requested; onboarding does not schedule them.

Suggest one practical next use based on what the user supplied, with a plain-language example they could use. Keep the tour brief and conversational, without another questionnaire or a requirement to try every skill. If the user asks to stop early, defer the tour. Do not repeat an orientation already given in the conversation or make an ordinary setup refresh repeat it unless requested.

Close with a brief account of the files actually saved and any source setup they chose to defer. Skipped optional topics do not make setup incomplete. If the user stops early, preserve what was learned and let them resume with "Continue setup" or `$onboard`. Do not turn the close into a briefing, readiness score, or checklist of empty files.
