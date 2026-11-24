# Context handling

Use the relevant sections when sourcing an assessment, saving authorized context, or configuring a workflow. These are recordkeeping rules. They do not prescribe the shape or depth of the conversation. The advisory posture lives in [AGENTS.md](../AGENTS.md).

## Dates and periods

Use the client's current date and timezone for briefing dates, daily filenames, and calendar windows. If unavailable, use the timezone explicitly configured in `sources.local.md`; if neither is available, state the host-local fallback. Determine the current quarter from the user's configured fiscal calendar or supplied OKR period, rather than assuming a fiscal year.

Pass `--date YYYY-MM-DD` to `synthesis.py` for a specific day. Its relative `--days` option uses the execution host's local date.

## Sources and evidence

Configure accounts and authorized source locations in ignored `sources.local.md`. No employer account or source is configured by default. Use available tools and discover supported connector capabilities; do not assume fixed tool names. A connected account alone does not establish source scope. Missing connectors and missing records are visibility gaps.

### Activity logs

`synthesis.py` reads classified usage-tracker JSONL files, not raw assistant conversation transcripts. Supply `--root /path/to/logs` or set `CHIEF_OF_STAFF_LOG_DIR`. The default is `~/.local/share/chief-of-staff/activity-logs`. This repository includes no collector or historical logs.

Use `python3 scripts/synthesis.py --days N` for activity grouped by project. If the log root is missing or unreadable, report the material evidence gap. Never interpret missing logs as a quiet day. With no tracker, work from supplied context and other authorized evidence. Session logs capture only assisted work; missing Slack, meetings, or offline activity does not establish a stall.

### Meetings and sessions

Read only sources supplied by the user or configured in `sources.local.md`. Requested transcript ingest preserves the original under ignored `transcripts/`, keeping source metadata and interpretation separate. Follow the ingest skill's [source-preservation reference](../.agents/skills/ingest/references/source-preservation.md). Ordinary notes and thinking aloud do not automatically become transcript archives.

When email meeting intake is enabled for a configured mailbox, morning discovers Gemini notifications, retrieves linked documents and transcript tabs, and applies ingest to material changes. Follow [meeting intake](meeting-intake.md) for complete pagination, overlap windows, provenance, retries, and deduplication. Generated notes remain labeled as notes and eligible for a later transcript. A completed search checkpoint does not mean every source was successfully ingested.

Source archives and ingestion state stay under ignored `transcripts/`. Local preservation does not authorize upload, sync, or publication. Summaries are lossy; read the original when nuance affects the judgment. Verify unfamiliar or inconsistently transcribed names before adding them to context.

Local Codex sessions may live under `~/.codex/sessions/`. Their format differs from the scanner's classified records. Read only relevant sessions the user supplies or explicitly configures; do not scan account history by default.

### Jira, Confluence, and calendar

Jira is the work-tracking source. Confluence is the canonical source of documentation and company knowledge. Read linked issues and relevant documentation before a source-backed assessment. Status, acceptance criteria, and measured business impact are distinct. Connector writes require a request or existing authorization for the specific change.

The active-project list lives in local `projects/*.md`. Consult relevant canonical Confluence documentation and the configured current-role calendar when scheduling affects the advice. Account and site identifiers belong only in ignored `sources.local.md`.

### Org structure

Use the configured employee directory for formal reporting lines, roles, and departments; Confluence for documented remits and decision rights; supplied meetings for working-relationship evidence.

For orientation, read existing `org/structure.md` before walking the directory. Use its coverage boundary and source links to locate relevant branches. Leadership and reporting observations are dated. Check the live directory for individual lookups and consequential reporting facts, and canonical documentation for remit or authority. A title alone does not establish decision rights.

Build or refresh a map only within the requested scope using the [org-map skill](../.agents/skills/org-map/SKILL.md). Keep formal facts separate from inferred influence, preserve contradictions and unknowns, and avoid an indiscriminate roster.

## Context files

Create only useful files. Missing context is normal on a fresh clone. Templates in [templates/context.md](../templates/context.md) are guidance, not forms to fill.

| File | Purpose | Maintained by |
|---|---|---|
| `self.md` | Role, preferences, ambitions, performance narrative, and review context | user and chief of staff |
| `operating-model.md` | Mandate, decision rights, boundaries, and operating model | user and chief of staff |
| `priorities.md` | Current weekly focus and deliberate exclusions | user and chief of staff; morning refreshes through conversation |
| `stakeholders.md` | Navigation and profiles that have not moved | chief of staff through authorized context workflows |
| `people/*.md` | Canonical profiles for selected stakeholders | chief of staff through authorized context workflows |
| `projects/*.md` | Project context; strategic view and workspace pointer when linked | chief of staff through ingest and eod |
| `okrs/<quarter>.md` | OKRs with Jira and Confluence links | user, from supplied context or CSV |
| `team/*.md` | Durable coaching themes and development patterns | chief of staff through authorized context workflows |
| `daily/*.md` | Daily prose synthesis and real calls | eod writes; morning and eod revisit |
| `org/*.md` | Sourced formal structure and documented remits | org-map |
| `transcripts/` | Original sources, provenance, and local intake state | ingest, including configured morning intake |
| `sources.local.md` | Accounts and authorized source locations | user and chief of staff |
| `knowledge/context-index.md` | Generated view of selected relationships | `context.py` |
| `drafts/` | Ephemeral working drafts, not a memory layer | user and chief of staff |

## Writeback policy

Writebacks transform, not append. Before updating durable context, ask whether the observation changes existing understanding, adds a new angle, or would change what a future reader does. If none apply, make no durable edit. Another instance of a documented pattern does not need another entry. That pattern may still deserve a substantial conversation.

Within a requested workflow, save scoped reversible writebacks that clear this test. Follow the user's global confirmation policy; this project imposes no separate approval step for routine authorized local updates. Read before editing, preserve existing evidence and unrelated content, and date material claims. Distinguish observations, tentative interpretations, proposals, commitments, implemented behavior, adoption, and measured outcomes. Exploratory interpretations in conversation need not become durable claims.

Lead the response with what matters to the user's purpose. Briefly identify useful saved changes afterward, without listing every file operation. A purely administrative request can receive an operational confirmation. Completing a workflow can legitimately require no durable edit.

Coaching files hold lasting strengths, development areas, and themes spanning interactions. Apply the six-month test: would the line still tell a future reader something true about working with this person? Isolated meetings and commitments do not belong there. When in doubt, save fewer entries.

Daily files are a journal, not canonical stakeholder or project state. Only eod writes them; other skills do not add daily writebacks. Eod records meaningful calls with position, confidence, and what would change the judgment, and captures coaching evidence in normal prose. Revisit earlier calls when relevant, including those that proved wrong.

For unlinked projects, eod may reconcile substantive changes to Current State, Critical Blocker, or Open Risks. Key Stakeholders, What Done Looks Like, Cross-Project Dependencies, and the Status line change only by deliberate agreement. Linked-project context follows the ownership rules below.

## Linked project workspaces

The project workspace owns design, build state, decisions, and commitments with owners and dates, including adoption checks, impact measurement, and communication. Its `STATUS.md` summarizes state and links evidence. Jira and Confluence remain canonical for shared work and documentation. The CoS project file keeps purpose, strategic implications, stakeholder reads, cross-project links, and dated judgments with falsifiers. When assessing delivery it may record the operating-loop stage and unresolved decision. Unlinked projects retain delivery context in CoS.

Configure each CoS project file, absolute workspace path, and status file in `sources.local.md`. Before any relevant assessment, including ordinary advice and OKR reviews, read the configured `STATUS.md` alongside relevant sources. A missing workspace or status is a visibility gap, never evidence of inactivity.

A recent edit or file mtime does not establish freshness. Unrelated newer evidence does not invalidate status. If newer applicable evidence materially changes or contradicts it, use that evidence for the current assessment and flag that the workspace needs updating. Preserve the source through ingest; do not maintain a separate discrepancy record.

When linking an existing project, get the user's approval for the proposed content moves and relationship changes. Move delivery detail into the workspace and verify it before reducing the CoS record. Reconcile affected `owns` and `contributes_to` relations on canonical source records under the structured-context rules below. Preserve the project ID and supported strategic relationships; remove duplicated delivery claims.

CoS writebacks stay strategic and follow the materiality test. Propose a dated workspace decision entry when direction changes; write it only when requested or approved. Keep private stakeholder assessments and coaching in CoS. Keep transcripts in CoS `transcripts/`; use original-source URLs or safe references in potentially shared project files, without private CoS paths or a second source archive.

Use the [project status template](../templates/project-status.md). Project agents update `STATUS.md` before completing or handing off work that changes state, decisions, or commitments. This convention configures no automatic synchronization.

## Structured context pilot

Selected project records and `people/*.md` contain relationships described in [structured context](structured-context.md). Other context remains valid without them. `stakeholders.md` retains navigation and unmoved profiles. Follow a moved person's canonical overview link; do not recreate their profile in the overview. Formal reporting belongs in the sourced org map and coaching patterns in `team/`.

Use `knowledge/context-index.md` or `python3 scripts/context.py show "exact name or id"` to locate selected relationships and supporting sections. Read relevant prose before drawing an advisory conclusion. The index is partial; a missing entry does not establish absence. Source dates remain meaningful, and proposed relations do not establish accepted ownership or deployed behavior.

When a material writeback changes an indexed record, reconcile prose and affected relationships in the same edit. Store each relationship once on its source record. Rebuild with `python3 scripts/context.py index --write`, then run `python3 scripts/context.py validate`. Do not expand the vocabulary or convert records merely to fill the index.
