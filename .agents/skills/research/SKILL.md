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
- `artifacts/findings/<sq-id>.jsonl`: claim records, one per line, from workers
- `artifacts/findings/<sq-id>.state.json`: each worker's queries, URLs, and open questions
- `artifacts/state.json`: merged queries, visited URLs, and open questions
- `artifacts/stats.json`: source-quality counts from `scripts/research_state.py`
- `artifacts/review.md`: critic output
- `artifacts/report.md`: final synthesis
- `notes/`: the user's own thoughts. No agent writes here.

## Steps

1. **Clarify.** Read `research-topics/<topic>/README.md` if it exists. If the request is ambiguous on scope, audience, or decision it serves, ask the user up to three short questions. If they are unavailable, write explicit assumptions into the plan instead.
2. **Plan.** Write `artifacts/plan.md`: the question, the decision it informs, assumptions, and 3 to 6 sub-questions with ids `sq1`, `sq2`, and so on. Note any primary sources to verify. Show the plan to the user and wait for a yes unless they said to proceed.
3. **Research.** Launch one `researcher` per sub-question in a single parallel call. Give each: topic slug, its sub-question id and text, and any primary sources to check. Workers write `findings/<sq-id>.jsonl` and `findings/<sq-id>.state.json` and return about 100 words. Do not read raw pages in the main session. Give workers disjoint sub-questions; workers in one wave cannot see each other's queries.
   After the wave, run `python3 scripts/research_state.py validate research-topics/<topic>/artifacts`. If it reports problems, send those workers back to fix their files. Then run `python3 scripts/research_state.py merge research-topics/<topic>/artifacts` so the next wave can skip visited URLs and repeated queries.
4. **Critique.** Run `python3 scripts/research_state.py stats research-topics/<topic>/artifacts > research-topics/<topic>/artifacts/stats.json`. Then launch `research-critic` with the topic slug. It reads the plan, stats, state, and claim records and writes `artifacts/review.md` with contradictions, stale data, uncited claims, missing perspectives, and a list of targeted follow-up queries.
5. **Second wave, once.** If the review lists gaps that matter to the question, launch targeted `researcher` runs for those only, then validate, merge, recompute stats, and rerun the critic. Do not loop a third time. List what remains open in the report.
6. **Synthesize.** Launch `research-synthesizer` with the topic slug. It reads only `plan.md`, `findings/*.jsonl`, and `review.md`, and writes `artifacts/report.md`.
7. **Report to the user.** Give the bottom line, how strong the evidence is, what stays unverified, and the path to the report. Offer to update `research-topics/<topic>/README.md`. Update it only after the user agrees, since it holds their current position.

## Rules

- The main session reads findings and the review, never raw web pages.
- Keep personal, employer, and project details out of every subagent prompt that could reach a search query.
- Publishing a page or sharing the report is a separate request from the user.
- Do not write to `notes/`.
