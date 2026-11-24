# Chief of staff for Codex and Claude Code

A local advisory workspace for strategic prioritization, coaching, meeting intake, and evidence-based OKR review. It is meant to feel like an intellectually engaged chief of staff who remembers the work, develops a view, and helps you keep immediate demands in perspective.

The repository contains the reusable framework. Your company context, personal notes, transcripts, and intake history stay in ignored local files. Each person uses their own clone and connected accounts.

## Start here

Clone the repository, then open the folder as a Codex project or in Claude Code:

```sh
git clone https://github.com/paulchangmckay/cos.git
cd cos
```

Codex reads AGENTS.md directly; Claude Code reads [CLAUDE.md](CLAUDE.md), which imports it. Claude Code also needs a one-time skill link: `mkdir -p .claude && ln -sfn ../.agents/skills .claude/skills`. In Claude Code, write `/morning` where this guide says `$morning`. [AGENTS.md](AGENTS.md) sets the relationship and advisory posture. Both tools discover onboarding plus the five everyday workflows in `.agents/skills/`. [writing style](docs/writing-style.md) defines the voice. Detailed [context handling](docs/context-handling.md) and [advisory lenses](docs/advisory-lenses.md) are references for relevant tasks, rather than a manual to load for every conversation. See the [official skill documentation](https://learn.chatgpt.com/docs/build-skills) for project skill discovery. If updated skills do not appear in an existing chat, start a fresh project chat or restart Codex.

You can get value without connectors or Python. Start a chat in this project:

> Help me get started.

This selects the [onboarding interview](.agents/skills/onboard/SKILL.md); you can also invoke `$onboard`. It asks one or two questions at a time about your remit, important relationships, priorities, and how you want the adviser to work with you. Useful context is saved progressively in ignored local files. Bring a real decision and the adviser will start helping as soon as there is enough to go on. The interview closes with a short tour of the five everyday workflows, how to work conversationally with the adviser, and one suggested next use tailored to your needs. You can skip topics or say "Continue setup" in a later chat.

Source setup is optional. You can start entirely from conversation and supplied notes, then configure calendar, Gmail/Docs, or other sources when useful. Opening the project alone does not start an interview or read connected accounts.

If you prefer to set up files yourself, [templates/self.md](templates/self.md) and [templates/priorities.md](templates/priorities.md) show the small amount of context that helps. Create only what you need. The [context guide](templates/context.md) explains the other local files; missing files are normal on a fresh clone.

For a first ingest, try a fictional example before using work material:

> Ingest this fictional note: I own a pilot due next Friday. The sponsor wants a recommendation on whether to expand it. We have usage figures but no agreed measure of business value. Help me decide what to do next. Do not save these fictional facts.

A useful response should form a view and explain the next decision. It should not invent an impact result or turn the note into a tracker. Once comfortable, supply a real note or transcript and ask to ingest it. Transcript ingest preserves the original locally and applies only material context updates.

## Repository layout

```text
AGENTS.md            Adviser posture and rules (Codex reads this)
CLAUDE.md            Imports AGENTS.md for Claude Code
README.md            This guide
CONTRIBUTING.md      Contribution and sharing checks
.agents/skills/      The seven workflows (onboard, morning, ingest, eod, okr-check, org-map, one-on-one)
.github/workflows/   CI: tests and repository checks
docs/                Reference guides (context handling, lenses, writing style, intake, structured context)
scripts/             Python tools (context, meeting_intake, synthesis, check_repo)
templates/           Starting files to copy into your local context
tests/               Synthetic tests for the scripts
daily/ okrs/ projects/ team/ one-on-ones/   Your private local context (git-ignored; only .gitkeep is tracked)
```

## Everyday workflows

| Request | Skill |
|---|---|
| Get started, resume setup, or refresh adviser context | `$onboard` |
| Start the day or talk through priorities | `$morning` |
| Close the day and save a daily synthesis | `$eod` |
| Process notes, a transcript, or a supplied file | `$ingest` followed by the input |
| Review OKRs for yourself, a person, or the team | `$okr-check self`, `$okr-check <person>`, `$okr-check team` |
| Map reporting lines, team remits, or decision ownership | `$org-map` |
| Prep or capture a one-on-one with the three standard questions, or see who is due | `$one-on-one <name>`, `$one-on-one team` |

Ordinary language can select these workflows too. Start conversationally. The adviser should develop a view from your context, disagree when useful, and leave a quiet day quiet. [Synthetic voice examples](docs/voice-examples.md) show the intended register. Adjust preferences in `self.md` as you learn what helps. Instructions can steer the voice; judge the result in your actual Codex setup.

Thinking aloud stays conversational unless you ask to capture or process it. The adviser should help you examine which problems deserve your involvement, connect decisions across projects, and develop important reasoning without rushing to a plan. Routine workflow steps stay out of chat; useful findings and a brief save receipt carry the result.

## Sources and meeting intake

Copy the structure in [templates/sources.local.md](templates/sources.local.md) into ignored `sources.local.md` to configure only the accounts and sources you want used. Connecting an account does not configure this workspace to read unrelated data. Credentials belong in the connector or supported credential store, never in a context file.

Jira supplies work status, Confluence supplies canonical documentation, and your configured calendar supplies scheduling context. These are optional. Missing access is a coverage gap; you can always supply context directly.

When hands-on work moves to a separate local folder, configure a linked workspace in `sources.local.md` using the [source template](templates/sources.local.md) and give it a [project status file](templates/project-status.md). CoS reads that delivery state while its project file keeps the strategic view; see [Linked project workspaces](AGENTS.md#linked-project-workspaces).

To use morning meeting intake, enable it for a specific Gmail account with read access to the linked Google Docs through your available connectors. `$morning` searches Gemini notification emails, inspects the linked documents for transcript tabs, and ingests new or changed sources before the briefing. It searches seven days on the first run, then catches up from the last completed search with a seven-day overlap. No meeting folder needs maintaining.

The agent uses [meeting_intake.py](scripts/meeting_intake.py) for local progress and archive bookkeeping. The helper requires Python 3.10+ and uses only the standard library; it does not call Gmail or Drive itself. See [docs/meeting-intake.md](docs/meeting-intake.md) for the procedure, retries, deduplication, and notes that later gain a transcript. Mailbox state and Drive files are unchanged. If intake is disabled or access is missing, paste a transcript or supply a file to `$ingest`.

Org mapping uses the configured employee directory for formal structure, Confluence for documented remits, and meetings for relationship evidence. Maps stay in ignored `org/`. Reporting lines, decision rights, and inferred influence remain distinct.

## What stays local

**Company and personal content never belongs in Git, even in this private repository.** Context, source snapshots, org maps, intake state, cached knowledge, and generated debriefs are ignored. A clone does not back them up, and this framework configures no cloud sync.

Ignore rules cannot protect an already tracked file or prevent force-adding content. Review the actual staged diff before contributing. [CONTRIBUTING.md](CONTRIBUTING.md) explains the sharing check and pull-request workflow. Use synthetic examples in reusable docs and tests.

## One-on-ones

Every one-on-one uses the same three questions: what's working, what's frustrating, and what do you need from me? Capture works three ways: from a Gemini transcript through meeting intake, from notes you paste, or from a two-minute interview where the adviser asks you the questions afterwards. Records, open asks and cadence live in ignored `one-on-ones/`. See [one-on-ones](docs/one-on-ones.md) and run `python3 scripts/one_on_one.py roster` to see who is due.

## Optional Python tools

All local tools require Python 3.10+ and only the standard library. The five advisory workflows also work from supplied context without a tracker or structured index.

### Structured context

Selected Markdown records can carry stable identities and qualified relationships. [structured-context.md](docs/structured-context.md) describes the format and lookup commands. Prose and source archives remain canonical; the generated index is partial. Canonical stakeholder profiles in `people/` and generated views in `knowledge/` remain ignored.

### Classified activity scanner

`synthesis.py` reads classified tracker JSONL records. It does not read raw assistant sessions or meeting transcripts. No collector or historical logs are included.

```sh
python3 scripts/synthesis.py --root /path/to/your/activity-logs --date YYYY-MM-DD
CHIEF_OF_STAFF_LOG_DIR=/path/to/your/activity-logs python3 scripts/synthesis.py --days 7
```

Replace `YYYY-MM-DD` with the day you want. `--date` selects one exact day. `--days N` covers today and the preceding N days using the execution host's local date. Daily workflows determine the date from client context, then the timezone configured in `sources.local.md`, and otherwise state the host-local fallback. They pass `--date` explicitly. Fiscal periods come from your supplied calendar or OKR context.

Supported records are classified legacy session objects and collector `daily_activity` objects. Timestamps must include a timezone offset. Daily records use `activity_date`, `transcript_path`, and a valid `collector_run_at` or `timestamp`. Provided counts must be nonnegative integers, and durations must be finite and nonnegative. Raw Codex session records, undated objects, malformed JSON, and unreadable files produce a diagnostic and nonzero exit, without a successful summary. Missing evidence never implies inactivity.

## Contribute

Framework improvements go through task branches and reviewed pull requests. Keep work context out of the diff and run the checks in [CONTRIBUTING.md](CONTRIBUTING.md). Your local context remains yours; this repository shares the starting system.
