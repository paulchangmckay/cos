@AGENTS.md

## Claude Code notes

- Skills live in `.agents/skills/` and subagents in `.agents/agents/` (shared with Codex). Claude Code reads `.claude/skills/` and `.claude/agents/`, so run once per clone: `mkdir -p .claude && ln -sfn ../.agents/skills .claude/skills && ln -sfn ../.agents/agents .claude/agents`. `.claude/` stays git-ignored.
- Invoke workflows as `/onboard`, `/morning`, `/ingest`, `/eod`, `/okr-check`, `/org-map`. Docs that say `$name` mean the same skill.
- Use `claude/` as the prefix for agent-created branches (CONTRIBUTING says `codex/` for Codex).
