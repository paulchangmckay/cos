# Contributing

Contribute the reusable framework: instructions, workflows, templates, and code. Keep personal and company context in each user's ignored local files. A private repository still needs this boundary.

Create a task branch from current `main`, make a focused change, and open a pull request for review. Use `codex/` for agent-created branches. Commit or merge only with the current user's authorization; this baseline grants no standing consent. Do not publish a user's local context, archive branches, or personal history.

Before staging, read the complete diff for names, confidential examples, account identifiers, private URLs, credentials, and claims that assume one user's consent. Use synthetic fixtures. Ignore rules do not remove already tracked files and can be bypassed, so stage explicit paths and inspect the index:

```sh
git diff
git add path/to/reusable-file
git diff --cached
python3 -B -m unittest discover -s tests
python3 scripts/check_repo.py
git diff --cached --check
```

Python 3.10 or later is required for the optional utilities and checks. There are no third-party Python dependencies. The release checker examines the whole staged tree, including credential signatures, private paths, skill frontmatter, and local Markdown navigation. `--worktree` checks working content for paths already in the index; `--ref HEAD` checks a committed tree. New files need explicit staging before the checker includes them. Skill frontmatter uses one-line `name` and `description` strings; the checker rejects other YAML forms. Matching content is never printed. These checks catch common mistakes; reviewers still assess what is suitable for sharing.

Run scanner tests with synthetic classified activity records, never private assistant histories. For meeting intake, exercise retries, unchanged repeats, notes becoming transcripts, and interrupted reconciliation. Validate changed skills with the Skill Creator validator when available, and walk through their instructions with realistic synthetic input. Examples of the intended advisory voice live in [voice examples](docs/voice-examples.md). Tone still needs evaluation in the actual model and client.

CI checks the standard-library suite, the release boundary, frontmatter, local documentation links, and whitespace on Python 3.10 and 3.13. Passing CI establishes the tested behavior and file boundary; it does not verify connector permissions, organizational approval, or the accuracy of private context.
