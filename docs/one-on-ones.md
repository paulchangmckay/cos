# One-on-ones

Every one-on-one uses the same three questions, in the same words:

1. What's working?
2. What's frustrating?
3. What do you need from me?

A fixed set makes answers comparable across people and across time. Extra questions are allowed, but prep offers at most two specific follow-ups.

## Where records live

`one-on-ones/<name>.md`, one file per person, git-ignored. The [template](../templates/one-on-one.md) shows the shape. The file holds a current picture, the asks you have not closed, and a dated log.

This is separate from `team/*.md`. Team files keep durable coaching patterns and pass the six-month test in the [writeback policy](context-handling.md#writeback-policy). A dated meeting log fails that test, so it lives here. A pattern that holds up over months can be promoted to the person's team file.

## Three ways to capture

| Source | How it arrives | What the record says |
|---|---|---|
| `gemini` | Meeting intake finds a Gemini transcript of a two-person meeting with someone who has a one-on-one record | Answers taken from what the person said. The original transcript is preserved first. |
| `notes` | You paste notes after the meeting | Answers mapped from your notes. Gaps stay as "Not discussed". |
| `memory` | The agent asks you the three questions, one at a time, in about two minutes | Your recollection of what they said. It is not a quote and the record says so. |

In every mode, an unanswered question is recorded as "Not discussed". The agent never fills it from inference.

## Open asks

A "need from me" that names something concrete becomes a line under Open asks, dated the day it was raised. Record what you answered, and never assume you accepted. Open asks use your capacity, so the adviser weighs them with the absorbability lens in [advisory lenses](advisory-lenses.md#coaching-when-the-moment-warrants-it).

## Roster

```sh
python3 scripts/one_on_one.py roster
python3 scripts/one_on_one.py roster --format json --today YYYY-MM-DD
```

The roster reads each record and reports the last meeting, the days since, open asks, and the age of the oldest ask. Status follows the person's cadence:

| Status | Meaning |
|---|---|
| ok | Fewer days than the cadence since the last meeting |
| due | At or past the cadence |
| overdue | At or past 1.5 times the cadence |
| never | A record exists but the log is empty |
| unset | No recognised cadence, so no judgement is made |

The roster counts and dates. It does not read meaning. Patterns, such as one frustration appearing in several records, come from the adviser reading the files.

## Boundaries

- Records are private context. They never enter `daily/` (eod owns that), a commit, or a message.
- Record what was said. Keep interpretation on its own line, labelled "My read:".
- Never score or rank people from these records.
- A quiet record is not a problem. Missing evidence is a visibility gap.
