---
name: research
description: Run a multi-agent research loop on a topic. Plans sub-questions, researches them in parallel, critiques the findings, then writes a sourced report. Use when the user asks to research a topic in depth or to verify claims; a single quick lookup does not need it.
---

# Research

The main session supervises. Workers, critic, and synthesizer are subagents. Subagents cannot ask the user questions or start other subagents, so every step below that needs either stays in the main session. Follow [AGENTS.md](../../../AGENTS.md). Paths resolve from the repository root.

Agents live in `.claude/agents/`: `researcher`, `research-critic`, `research-synthesizer`. Skip this loop for a single quick lookup; send it straight to `researcher`.

## Layout

Everything lands under `research-topics/<topic>/`, which is git-ignored. Create the folder if it is missing.

- `artifacts/plan.md`: question, assumptions, sub-questions
- `artifacts/findings/<sq-id>.md`: one file per sub-question, from workers
- `artifacts/sources.md`: all sources, shared
- `artifacts/review.md`: critic output
- `artifacts/report.md`: final synthesis
- `notes/`: the user's own thoughts. No agent writes here.

## Steps

1. **Clarify.** Read `research-topics/<topic>/README.md` if it exists. If the request is ambiguous on scope, audience, or decision it serves, ask the user up to three short questions. If they are unavailable, write explicit assumptions into the plan instead.
2. **Plan.** Write `artifacts/plan.md`: the question, the decision it informs, assumptions, and 3 to 6 sub-questions with ids `sq1`, `sq2`, and so on. Note any primary sources to verify. Show the plan to the user and wait for a yes unless they said to proceed.
3. **Research.** Launch one `researcher` per sub-question in a single parallel call. Give each: topic slug, its sub-question id and text, the output path `artifacts/findings/<sq-id>.md`, and any primary sources to check. Workers return about 100 words. Do not read raw pages in the main session.
4. **Critique.** Launch `research-critic` with the topic slug. It reads the plan and findings and writes `artifacts/review.md` with contradictions, stale data, uncited claims, missing perspectives, and a list of targeted follow-up queries.
5. **Second wave, once.** If the review lists gaps that matter to the question, launch targeted `researcher` runs for those only, then rerun the critic on the new findings. Do not loop a third time. List what remains open in the report.
6. **Synthesize.** Launch `research-synthesizer` with the topic slug. It reads only `plan.md`, `findings/`, and `review.md`, and writes `artifacts/report.md`.
7. **Report to the user.** Give the bottom line, how strong the evidence is, what stays unverified, and the path to the report. Offer to update `research-topics/<topic>/README.md`. Update it only after the user agrees, since it holds their current position.

## Rules

- The main session reads findings and the review, never raw web pages.
- Keep personal, employer, and project details out of every subagent prompt that could reach a search query.
- Publishing a page or sharing the report is a separate request from the user.
- Do not write to `notes/`.
