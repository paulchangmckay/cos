# Structured context

Markdown remains the local record. Selected files have stable identities and a small set of qualified relationships. The prose holds interpretation and detail. Original evidence stays in its source archive.

This is an optional, partial index. Unindexed people and projects remain usable. Missing edges mean unknown coverage. A link, a mention, and a formal assignment have different meanings.

## Read

Use `python3 scripts/context.py find "name"` to locate indexed names. Use `python3 scripts/context.py show "exact name or id"` for incoming and outgoing relationships, their evidence, and relevant sections. Resolution requires an exact ID, name, or explicit alias. A partial name never selects a person automatically.

Use `python3 scripts/context.py section "exact name or id" "heading"` to read a relevant prose section. For unindexed context, search the existing project files and stakeholder overview. Follow profile links in `stakeholders.md` before reading or updating a migrated person.

Relationship views are discovery aids. Read relevant prose and cited evidence before making a consequential assessment. Formal reporting stays in the sourced org map. A dated graph edge does not refresh a directory observation.

## Record format

Place one JSON block after the prose, immediately following the comment `<!-- context-record -->`, inside a normal fenced JSON code block. JSON keeps the reader in Python's standard library. No database or package installation is required.

Record fields:

| Field | Meaning |
|---|---|
| schema | Integer 1 |
| id | Stable type-prefixed slug, such as person:alex-rivera |
| type | person, initiative, or system |
| name | Canonical display name |
| aliases | Explicit alternate names; ambiguous first names stay absent |
| sections | Existing level-two heading anchors worth reading next |
| relations | Selected outgoing relationships |

Use the smallest vocabulary that answers a recurring question. Add further types only when a real use case requires them.

Each relationship has `type`, `to`, `status`, `basis`, `as_of`, `sources`, and `note`. The target is an existing stable ID. Sources are repository-relative paths, optionally with a Markdown heading, or explicit HTTP(S) links. Local snapshots are preferable when available.

Relationship meanings:

| Type | Direction and scope |
|---|---|
| contributes_to | Person supplies work, expertise, or direction to the target; the note specifies the role |
| depends_on | Consumer requires the provider in the stated scope |
| part_of | Component or initiative sits within the stated broader scope |
| owns | Person has the specific accountability described in the note |
| reports_to | Person formally reports to the target person, supported by directory evidence |

Status and evidence are independent:

- `observed`: the stated relationship was observed as of the evidence date; acceptance of additional obligations is not implied.
- `proposed`: an intended arrangement awaiting acceptance.
- `accepted`: evidence explicitly establishes acceptance of the stated obligation.
- `unresolved`: the relationship is disputed or unsettled.
- `ended`: evidence establishes that the stated relationship ended.

Basis is `documented`, `reported`, or `inferred`. An inference cannot establish observed or accepted status. The note states scope and material limits. Do not infer programme ownership from document authorship or deployment from an architecture proposal.

`as_of` is the date of the retained evidence observation, not the date the metadata was edited. Leave old observations dated honestly. A later contradictory source requires reconciling the claim; retain the earlier evidence and its limits in prose or its source archive.

## Update

Keep the relationship once, on the source entity's canonical record. Incoming relationships and overview links are generated. Update relevant prose and structured relationships together when evidence materially changes them. Do not duplicate a moved profile in the stakeholder overview or convert coaching impressions into formal ownership.

After changing an indexed record:

    python3 scripts/context.py index --write
    python3 scripts/context.py validate

The generated view lives at `knowledge/context-index.md`. Validation checks identities, aliases, relationship vocabulary, evidence paths, dates, and relevant headings. It rejects stale generated output using a fingerprint of the canonical records. Query commands read current canonical records directly.

Validation checks structure and local links; it does not establish that a source supports a claim or that a dated claim remains current. That assessment belongs to the ingest or review.

The index may be rebuilt at any time. It contains private company context and stays ignored, alongside `people/` and the existing context paths. Reusable code and these instructions contain no company records.

## Scope changes and evaluation

Extend the pilot only after checking answer quality, retrieval effort, and maintenance cost against the same questions and source material. Compare against heading-aware search and targeted reads. A reduction measured against full-document reading alone is insufficient evidence.

Before moving content, preserve a private baseline and maintain the old links. Verify moved prose and source references. Keep pilot-specific questions, baseline snapshots and results under ignored `knowledge/`. Use synthetic records for code tests:

    python3 -B -m unittest discover -s tests -p 'test_context.py'
