# Thinking block

A fixed 15-minute exercise, run before the day starts. It uses four questions:

1. What's going well?
2. What's not?
3. What am I avoiding?
4. What needs to change?

A leader with no time to think is only going through the motions. The block protects that time. The value comes from answering without feedback, so the skill is deliberately quiet.

## How it runs

Run `/think`. The agent opens with the rules, asks one question at a time, and replies to each answer with only the next question. It reads none of your context until you finish, so priorities and past entries cannot steer what you write.

After question 4 it saves your words, then reflects once: it sets what you said you are avoiding against the evidence in your files, and ends with one decision for today. Then it offers `/morning`.

`/morning` offers the block once when no entry exists for today. Declining ends the offer for that day.

## Tips for a screen

- Close other apps and turn on Do Not Disturb before you start.
- Write unedited. Dictation works.
- The agent cannot keep time. Use a timer in a separate terminal, for example `sleep 900 && say "Time"`, or a calendar block.

## Where entries live

`thinking/YYYY-MM-DD.md`, one file per day, git-ignored. Entries are saved verbatim: no spelling fixes, no summaries. A second session on the same day goes under `## Session 2`.

The agent reads the last seven entries to spot repeats. When the same avoidance appears in three or more, it says so with the dates and offers to record it in `self.md`. It writes nothing there without your agreement.

## Boundaries

- Entries are private. They never enter `daily/`, a one-on-one record, a commit, or a message.
- The agent gives no feedback during the exercise and no diagnosis after it.
- A short entry is a complete entry. Missing evidence does not mean there is nothing to avoid.
