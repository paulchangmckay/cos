# Preserve an ingest source

Use this reference when a requested ingest includes a meeting transcript or a source discovered by configured meeting intake. Paths below resolve from the repository root. Ordinary thoughts and notes do not automatically become transcript archives.

## Supplied transcript

Save the original verbatim under ignored `transcripts/` before interpreting it. Use the stated meeting date in `YYYY-MM-DD-meeting-slug.txt`. If the date is unknown, use the receipt date and identify it as such in a companion `.source.md` file. Record the supplied title, meeting date when known, receipt date, source type, and original link or supplied path when available. Do not infer participants from ambiguous speaker labels.

Reuse an identical archived copy or choose a distinct filename when content differs. Never overwrite an earlier source. Preserve supplied names and wording in the original; explain corrections separately and verify unfamiliar or inconsistent names before adding them to context.

## Configured document intake

For sources discovered through Gemini emails, follow [meeting intake](../../../../docs/meeting-intake.md). Inspect document tabs and retrieve the actual transcript. Label generated notes as notes when no transcript is available. Use the helper to preserve source identity, provenance, content hash, and retry state.

Reconcile known source IDs and exact archived text with earlier manual ingest. Title and date alone do not prove duplication. Repeated notifications and unchanged completed source versions need no duplicate archive or context update. Mark a source complete only after preservation and context reconciliation succeed, including a deliberate no-change decision. A failure between these steps stays retryable.

Manual ingest updates the same bookkeeping when document identity is known. A notes-only source remains eligible for a later transcript. Preserve earlier versions when documents change. All source copies and intake state stay under ignored `transcripts/`; ingest does not upload them or modify Gmail or Drive.
