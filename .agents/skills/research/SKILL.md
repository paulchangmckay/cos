---
name: research
description: Run a multi-agent research loop on a topic. Plans sub-questions, researches them in parallel, critiques the findings, then writes a sourced report. Use when the user asks to research a topic in depth or to verify claims; a single quick lookup does not need it.
---

# Research

The main session supervises. Workers, critic, and synthesizer are subagents. Subagents cannot ask the user questions or start other subagents, so every step below that needs either stays in the main session. Follow [AGENTS.md](../../../AGENTS.md). Paths resolve from the repository root.

Agents live in `.claude/agents/`: `researcher`, `research-critic`, `research-synthesizer`, `research-briefer`. Skip this loop for a single quick lookup; send it straight to `researcher`.

## Layout

Everything lands under `research-topics/<topic>/`, which is git-ignored. Create the folder if it is missing.

- `artifacts/plan.md`: question, assumptions, sub-questions
- `artifacts/findings/<sq-id>.jsonl`: claim records, one per line, from workers. Ids are `sq1`, `sq2`, and so on; second-wave follow-ups add a letter (`sq2b`)
- `artifacts/findings/<sq-id>.state.json`: each worker's queries, URLs, and open questions
- `artifacts/state.json`: merged queries, visited URLs, and open questions
- `artifacts/stats.json`: source-quality counts from `scripts/research_state.py`
- `artifacts/review.md`: critic output
- `artifacts/audit.md`: statements the critic removed or changed in the final audit
- `artifacts/report.md`: final synthesis, the evidence ledger
- `artifacts/brief.md`: one-page decision brief that sits beside the report
- `notes/`: the user's own thoughts. No agent writes here.

## Steps

1. **Clarify.** Read `research-topics/<topic>/README.md` if it exists. If the request is ambiguous on scope, audience, or decision it serves, ask the user up to three short questions. If they are unavailable, write explicit assumptions into the plan instead.
2. **Plan.** Write `artifacts/plan.md`: the question, the decision it informs, assumptions, and 3 to 6 sub-questions with ids `sq1`, `sq2`, and so on. Note any primary sources to verify. Record today's date and a freshness threshold in days (default 365; use a shorter one for fast-moving topics). Set budgets: at most 6 sub-questions and 2 waves in total. Show the plan to the user and wait for a yes unless they said to proceed.
3. **Research.** Launch one `researcher` per sub-question in a single parallel call. Give each: topic slug, its sub-question id and text, today's date, the freshness threshold, and any primary sources to check. Workers follow the budgets and tool mix in `docs/research-tools.md`; do not tell them to prefer built-in tools. Workers write `findings/<sq-id>.jsonl` and `findings/<sq-id>.state.json` and return about 100 words. Do not read raw pages in the main session. Give workers disjoint sub-questions; workers in one wave cannot see each other's queries.
   After the wave, run `python3 scripts/research_state.py validate research-topics/<topic>/artifacts`. If it reports problems, send those workers back to fix their files. Then run `python3 scripts/research_state.py merge research-topics/<topic>/artifacts` so the next wave can skip visited URLs and repeated queries.
4. **Critique.** Run `python3 scripts/research_state.py stats research-topics/<topic>/artifacts --as-of <today> --stale-days <threshold> > research-topics/<topic>/artifacts/stats.json`. Then launch `research-critic` with the topic slug and today's date, in review mode. It reads the plan, stats, state, and claim records and writes `artifacts/review.md` with contradictions, stale data, uncited claims, missing perspectives, and a list of targeted follow-up queries.
5. **Second wave, once.** If the review lists gaps that matter to the question, launch targeted `researcher` runs for those only. Give each follow-up the id of the sub-question it extends plus a letter: `sq2b`, `sq3b`, `sq3c`. Each id gets its own `findings/<id>.jsonl` and `.state.json`, so wave 1 files stay untouched. If a follow-up spans two sub-questions, use the lower id. Then validate, merge, recompute stats, and rerun the critic. Do not loop a third time. List what remains open in the report.
6. **Synthesize.** Launch `research-synthesizer` with the topic slug. It reads only `plan.md`, `findings/*.jsonl`, and `review.md`, and writes `artifacts/report.md` with numbered `[n]` citations.
   If the synthesizer's write to `report.md` is rejected, it returns the full report text instead. Save that text verbatim to `artifacts/report.md` yourself. Do not ask it to try another path.
   Then run `python3 scripts/research_state.py check-report research-topics/<topic>/artifacts`. Launch `research-critic` once in audit mode with that output. It strips statements that no claim record supports and writes `audit.md`. If its rewrite of `report.md` is rejected, it returns exact old and new text for each edit. Apply those edits yourself, then mark them applied in `audit.md`. Run `check-report` again. Do not audit more than once; report any remaining errors to the user.
7. **Brief.** After the audit, launch `research-briefer` with the topic slug. It reads the README, plan, audited report, review, audit, and findings, and writes `artifacts/brief.md`: a decision brief that sits beside the report and does not replace it. If its write is rejected, save the returned text verbatim yourself. Run `python3 scripts/research_state.py check-brief research-topics/<topic>/artifacts`. Errors mean a missing section, a bad citation, a pillar count outside 2 to 4, or a number in a title that no claim record contains. Send the briefer back once to fix them; if errors remain, report them to the user. Skip this step when the user wants only the report.
8. **Report to the user.** Give the bottom line, how strong the evidence is, what stays unverified, and the paths to the report and the brief. Offer to update `research-topics/<topic>/README.md`. Update it only after the user agrees, since it holds their current position.

## Rules

- The main session reads findings and the review, never raw web pages.
- Keep personal, employer, and project details out of every subagent prompt that could reach a search query.
- Publishing a page or sharing the report is a separate request from the user.
- Do not write to `notes/`.
- Stop at the budgets in the plan. Do not start a third wave or add sub-questions mid-run; list what remains open.
