# Local source configuration

Copy this to ignored `sources.local.md` at the repository root. This is plain guidance for the agent, not a machine-parsed configuration schema. Fill in only sources you want used, in your own words. Leave everything else unconfigured. Do not put passwords, tokens, cookies, or client secrets here.

## Date and scope

- Timezone fallback: Not configured. Use the client's date and timezone first; if neither is available, state the host-local fallback.
- Fiscal calendar / current OKR period: Not configured. Do not infer a fiscal quarter from the calendar quarter.
- Current role and employer scope: Not configured. A connected account alone does not authorize unrelated data access.

## Gemini meeting intake

- Enabled: No. Set to Yes only for the mailbox you want checked during morning briefing.
- Gmail account / connector identity: Not configured.
- Google Drive / Docs account that can read linked documents: Not configured.
- Additional source scope or exclusions: Not configured.

When enabled, morning intake reads Gemini notes notifications and Google Docs sharing notifications identifying Notes by Gemini. It follows actual document links, discovers transcript tabs, and uses the local helper described in `docs/meeting-intake.md` (path from the repository root). The first search covers seven days; later searches catch up from the last complete search with a seven-day overlap. It leaves Gmail and Drive unchanged. Sources and retry state remain under ignored `transcripts/`. No meeting folder is required.

## Linked project workspaces

- Linked projects: Not configured.

For each project you choose to link, record its name, CoS project file (relative to this repository), absolute local workspace path, and status file path (relative to that workspace, or absolute). These are readable local folders; a separate chat or app project alone supplies no status file.

Follow the [Linked project workspaces rules](../AGENTS.md#linked-project-workspaces). Start the workspace's status file from [project-status.md](project-status.md). This configuration does not authorize workspace writes.

## Other optional sources

- Calendar account: Not configured.
- Jira account and site: Not configured.
- Confluence account, site, and canonical spaces: Not configured.
- Employee directory and supported read method: Not configured.
- Classified activity-log root: Not configured. These must be classified tracker JSONL records, not raw assistant sessions.
- Other authorized local transcripts or specific session paths: Not configured. Do not scan assistant account history by default.

Manual notes and transcript ingest work without these connectors. Source copies are local; this file does not configure backup, cloud sync, external writes, or publication.
