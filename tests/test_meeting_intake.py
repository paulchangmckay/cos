import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'scripts'))
"""Synthetic meeting-intake state and archive regressions."""
import json
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from meeting_intake import Intake, IntakeError, main


class MeetingIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.intake = Intake(self.root)

    def reload(self):
        self.intake = Intake(self.root)
        return self.intake

    def scan(self, at="2026-10-15T09:00:00-07:00", ids=None):
        scan = self.intake.scan_start(at)
        self.intake.scan_page(scan["id"], ids or [], None)
        self.intake.scan_finish(scan["id"])
        return scan

    def test_cli_full_intake_then_identical_retry_has_one_archive(self):
        def command(*args):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--root", str(self.root), *args]), 0)
            return json.loads(output.getvalue())
        scan = command("scan-start", "--at", "2026-10-15T16:00:00Z")
        incoming = self.root / "transcripts/.incoming"
        incoming.mkdir()
        page = incoming / "page.json"
        page.write_text(json.dumps({"message_ids": ["mail-cli"], "next_page_token": None}))
        command("scan-page", "--scan", scan["id"], "--input", str(page))
        command("scan-finish", "--scan", scan["id"])
        command("register-message", "--message-id", "mail-cli", "--document-id", "doc-cli")
        source = incoming / "retrieved.txt"
        source.write_text("A: The pilot remains a proposal.\n")
        args = ("archive", "--document-id", "doc-cli", "--kind", "transcript", "--input", str(source), "--version", "synthetic-revision")
        snapshot = command(*args)
        self.assertTrue(snapshot["needs_reconciliation"])
        pending = command("status")["pending_documents"]["doc-cli"]
        self.assertEqual(pending["pending_reconciliation"][0]["id"], snapshot["id"])
        command("complete", "--document-id", "doc-cli", "--snapshot", snapshot["id"])
        self.assertFalse(command(*args)["needs_reconciliation"])
        self.assertFalse(command("status")["pending_documents"])
        self.assertEqual(len(list((self.root / "transcripts/gemini").glob("*.txt"))), 1)

    def test_initial_window_is_seven_days_and_read_only(self):
        window = self.intake.window("2026-10-15T09:00:00-07:00")
        self.assertEqual(window["since"], "2026-10-08T16:00:00+00:00")
        self.assertEqual(window["until"], "2026-10-15T16:00:00+00:00")
        self.assertIn("from:gemini-notes@google.com", window["query"])
        self.assertNotIn("is:unread", window["query"])
        self.assertFalse((self.root / "transcripts").exists())
        with self.assertRaises(IntakeError):
            self.intake.window("2026-10-15T09:00:00")

    def test_pagination_checkpoint_resumes_and_preserves_pending_messages(self):
        scan = self.intake.scan_start("2026-10-15T16:00:00Z")
        with self.assertRaises(IntakeError):
            self.intake.scan_finish(scan["id"])
        self.intake.scan_page(scan["id"], ["mail1"], "page2")
        with self.assertRaises(IntakeError):
            self.intake.scan_finish(scan["id"])
        self.assertIsNone(self.reload().state["last_completed_scan_at"])
        self.assertEqual(self.intake.scan_start("2026-10-16T16:00:00Z")["id"], scan["id"])
        with self.assertRaises(IntakeError):
            self.intake.scan_page(scan["id"], ["mail2"], None, "wrong")
        self.intake.scan_page(scan["id"], ["mail2"], None, "page2")
        self.intake.scan_finish(scan["id"])
        self.assertEqual(self.reload().state["last_completed_scan_at"], "2026-10-15T16:00:00+00:00")
        self.assertEqual(set(self.intake.status()["pending_messages"]), {"mail1", "mail2"})

    def test_page_replay_is_idempotent_and_token_cycle_rejected(self):
        scan = self.intake.scan_start("2026-10-15T16:00:00Z")
        self.intake.scan_page(scan["id"], ["mail1"], "page2")
        result = self.intake.scan_page(scan["id"], ["mail1"], "page2")
        self.assertTrue(result["duplicate_page"])
        with self.assertRaises(IntakeError):
            self.intake.scan_page(scan["id"], ["different"], "page2")
        with self.assertRaises(IntakeError):
            self.intake.scan_page(scan["id"], [], "page2", "page2")

    def test_expired_pagination_can_restart_without_losing_discoveries(self):
        scan = self.intake.scan_start("2026-10-15T16:00:00Z")
        self.intake.scan_page(scan["id"], ["mail1"], "expired")
        restarted = self.intake.scan_restart(scan["id"])
        self.assertEqual(restarted["query"], scan["query"])
        self.assertIsNone(restarted["next_page_token"])
        self.assertIsNone(self.intake.state["last_completed_scan_at"])
        self.intake.scan_page(restarted["id"], ["mail2"], None)
        self.intake.scan_finish(restarted["id"])
        self.assertEqual(set(self.reload().status()["pending_messages"]), {"mail1", "mail2"})

    def test_missed_mornings_and_delayed_notifications_use_receipt_window(self):
        scan = self.scan()
        self.assertEqual(self.intake.scan_finish(scan["id"])["last_completed_scan_at"], scan["started_at"])
        window = self.reload().window("2026-10-30T16:00:00Z")
        self.assertEqual(window["since"], "2026-10-08T16:00:00+00:00")
        self.assertEqual(window["until"], "2026-10-30T16:00:00+00:00")
        self.assertIn("after:1791475200", window["query"])

    def test_repeated_notifications_resolve_to_one_document(self):
        self.scan(ids=["mail1", "mail2"])
        self.intake.register_message("mail1", ["doc1"])
        self.intake.register_message("mail2", ["doc1", "doc1"])
        snapshot = self.intake.archive("doc1", "transcript", b"A: Decision is to proceed.\n")
        self.intake.complete("doc1", snapshot["id"])
        self.intake.register_message("mail2", ["doc1"])
        self.assertFalse(self.intake.status()["pending_messages"])
        self.assertFalse(self.intake.status()["pending_documents"])
        self.assertEqual(self.intake.state["documents"]["doc1"]["message_ids"], ["mail1", "mail2"])

    def test_reverted_content_requires_reconciliation_again(self):
        first = self.intake.archive("doc1", "transcript", b"Decision A\n")
        self.intake.complete("doc1", first["id"])
        second = self.intake.archive("doc1", "transcript", b"Decision B\n")
        self.intake.complete("doc1", second["id"])
        reverted = self.intake.archive("doc1", "transcript", b"Decision A\n")
        self.assertTrue(reverted["needs_reconciliation"])
        self.assertEqual(len(self.reload().status()["pending_documents"]["doc1"]["pending_reconciliation"]), 1)
        self.intake.complete("doc1", reverted["id"])
        self.assertFalse(self.intake.archive("doc1", "transcript", b"Decision A\n")["needs_reconciliation"])

    def test_superseded_pending_source_cannot_reconcile_after_current_source(self):
        old = self.intake.archive("doc1", "transcript", b"Old source\n")
        current = self.intake.archive("doc1", "transcript", b"Current source\n")
        pending = self.reload().status()["pending_documents"]["doc1"]["pending_reconciliation"]
        self.assertEqual([s["id"] for s in pending], [current["id"]])
        with self.assertRaisesRegex(IntakeError, "superseded"):
            self.intake.complete("doc1", old["id"])
        self.intake.complete("doc1", current["id"])
        self.assertFalse(self.reload().status()["pending_documents"])
        self.assertEqual((self.root / old["archive_path"]).read_bytes(), b"Old source\n")

    def test_same_content_new_provider_revision_needs_no_reconciliation(self):
        content = b"A: Proceed after approval.\n"
        snapshot = self.intake.archive("doc1", "transcript", content, provider_version="rev1")
        self.intake.complete("doc1", snapshot["id"])
        files = set((self.root / "transcripts").rglob("*.txt"))
        repeated = self.intake.archive("doc1", "transcript", content, provider_version="rev2")
        self.assertFalse(repeated["needs_reconciliation"])
        self.assertEqual(repeated["observed_versions"], ["rev1", "rev2"])
        self.assertEqual(files, set((self.root / "transcripts").rglob("*.txt")))
        self.assertEqual(len(self.reload().state["documents"]["doc1"]["snapshots"]), 1)

    def test_changed_source_preserves_previous_snapshot(self):
        old = self.intake.archive("doc1", "transcript", b"A: Old decision.\n", provider_version="rev1")
        self.intake.complete("doc1", old["id"])
        new = self.intake.archive("doc1", "transcript", b"A: Revised decision.\n", provider_version="rev2")
        self.assertTrue(new["needs_reconciliation"])
        self.assertNotEqual(old["archive_path"], new["archive_path"])
        self.assertEqual((self.root / old["archive_path"]).read_bytes(), b"A: Old decision.\n")
        self.assertEqual(len(self.reload().status()["pending_documents"]["doc1"]["pending_reconciliation"]), 1)

    def test_notes_remain_eligible_without_new_email_and_upgrade_kind(self):
        content = b"Decision text.\n"
        notes = self.intake.archive("doc1", "notes", content)
        self.intake.complete("doc1", notes["id"])
        pending = self.reload().status()["pending_documents"]["doc1"]
        self.assertTrue(pending["fetch_required"])
        self.assertTrue(pending["awaiting_transcript"])
        transcript = self.intake.archive("doc1", "transcript", content)
        self.assertTrue(transcript["needs_reconciliation"])
        self.assertEqual(transcript["archive_path"], notes["archive_path"])
        self.assertNotEqual(transcript["id"], notes["id"])
        self.intake.complete("doc1", transcript["id"])
        self.assertFalse(self.reload().status()["pending_documents"])

    def test_later_notes_do_not_downgrade_completed_transcript(self):
        transcript = self.intake.archive("doc1", "transcript", b"Full source\n")
        self.intake.complete("doc1", transcript["id"])
        notes = self.intake.archive("doc1", "notes", b"Summary\n")
        self.intake.complete("doc1", notes["id"])
        self.assertFalse(self.reload().status()["pending_documents"])

    def test_access_failure_and_interruption_remain_retryable_without_mail(self):
        self.intake.fail("Permission denied", document_id="doc1")
        self.intake.fail("Mailbox temporarily unavailable", message_id="mail1")
        self.assertEqual(self.reload().status()["pending_documents"]["doc1"]["last_error"], "Permission denied")
        self.assertIn("mail1", self.intake.status()["pending_messages"])
        snapshot = self.intake.archive("doc1", "transcript", b"A: Context.\n")
        pending = self.reload().status()["pending_documents"]["doc1"]
        self.assertEqual(pending["pending_reconciliation"][0]["id"], snapshot["id"])
        self.assertTrue(self.intake.archive("doc1", "transcript", b"A: Context.\n")["needs_reconciliation"])
        self.intake.complete("doc1", snapshot["id"])
        self.assertNotIn("doc1", self.reload().status()["pending_documents"])

    def test_exact_manual_archive_reused_but_title_match_is_not_enough(self):
        directory = self.root / "transcripts"
        directory.mkdir()
        manual = directory / "manual.txt"
        manual.write_bytes(b"A: Same source.\n")
        snapshot = self.intake.archive("doc1", "transcript", manual.read_bytes())
        self.assertEqual(snapshot["archive_path"], "transcripts/manual.txt")
        self.assertEqual(len(list(directory.rglob("*.txt"))), 1)
        self.assertTrue(snapshot["needs_reconciliation"])
        changed = self.intake.archive("doc2", "transcript", b"A: Different source.\n")
        self.assertNotEqual(changed["archive_path"], snapshot["archive_path"])

    def test_staging_text_is_never_adopted_as_immutable_archive(self):
        incoming = self.root / "transcripts/.incoming"
        incoming.mkdir(parents=True)
        scratch = incoming / "retrieved.txt"
        scratch.write_bytes(b"Original source\n")
        snapshot = self.intake.archive("doc1", "transcript", scratch.read_bytes())
        scratch.write_bytes(b"Next source\n")
        self.assertNotEqual(snapshot["archive_path"], "transcripts/.incoming/retrieved.txt")
        self.assertEqual((self.root / snapshot["archive_path"]).read_bytes(), b"Original source\n")

    def test_cannot_complete_missing_or_changed_archive(self):
        with self.assertRaises(IntakeError):
            self.intake.complete("doc1", "transcript:unknown")
        snapshot = self.intake.archive("doc1", "transcript", b"Verbatim\n")
        (self.root / snapshot["archive_path"]).write_bytes(b"Changed\n")
        with self.assertRaises(IntakeError):
            self.intake.complete("doc1", snapshot["id"])
        with self.assertRaises(IntakeError):
            self.intake.archive("doc1", "transcript", b"Verbatim\n")

    def test_empty_or_binary_source_does_not_create_state(self):
        for content in (b"", b" \n", b"\xff"):
            with self.assertRaises(IntakeError):
                self.intake.archive("doc1", "transcript", content)
        self.assertFalse((self.root / "transcripts").exists())

    def test_parent_and_file_symlinks_cannot_escape(self):
        with tempfile.TemporaryDirectory() as other:
            (self.root / "transcripts").symlink_to(other, target_is_directory=True)
            with self.assertRaises(IntakeError):
                Intake(self.root)
            (self.root / "transcripts").unlink()
            (self.root / "transcripts").mkdir()
            (self.root / "transcripts/gemini").symlink_to(other, target_is_directory=True)
            with self.assertRaises(IntakeError):
                self.intake.archive("doc1", "transcript", b"Source\n")
            self.assertEqual(list(Path(other).iterdir()), [])
        with self.assertRaises(IntakeError):
            self.intake.inside("../outside.txt")

    def test_stale_writer_does_not_overwrite_other_transaction(self):
        stale = Intake(self.root)
        self.intake.register_message("mail1", ["doc1"])
        with self.assertRaisesRegex(IntakeError, "concurrently"):
            stale.register_message("mail2", ["doc2"])
        self.assertEqual(set(self.reload().state["messages"]), {"mail1"})
        self.assertFalse((self.root / "transcripts/.ingestion-state.lock").exists())

    def test_failed_ledger_save_after_archive_can_retry_preserved_source(self):
        with patch.object(self.intake, "save", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                self.intake.archive("doc1", "transcript", b"Original\n")
        existing = list((self.root / "transcripts").rglob("*.txt"))
        self.assertEqual(len(existing), 1)
        snapshot = self.reload().archive("doc1", "transcript", b"Original\n")
        self.assertEqual(self.root / snapshot["archive_path"], existing[0])
        self.assertTrue(snapshot["needs_reconciliation"])

    def test_interrupted_source_write_never_leaves_a_partial_final_archive(self):
        with patch("meeting_intake.os.fsync", side_effect=OSError("write interrupted")):
            with self.assertRaises(OSError):
                self.intake.archive("doc1", "transcript", b"Complete source\n")
        self.assertEqual(list((self.root / "transcripts").rglob("*.txt")), [])
        self.assertEqual(list((self.root / "transcripts").rglob(".source-*")), [])
        result = self.reload().archive("doc1", "transcript", b"Complete source\n")
        self.assertEqual((self.root / result["archive_path"]).read_bytes(), b"Complete source\n")

    def test_corrupt_ledger_is_not_reset(self):
        directory = self.root / "transcripts"
        directory.mkdir()
        ledger = directory / ".ingestion-state.json"
        for payload in ("{broken", '{}', '{"schema_version":1,"messages":{},"documents":{}}'):
            ledger.write_text(payload)
            with self.assertRaisesRegex(IntakeError, "ledger"):
                Intake(self.root)
            self.assertEqual(ledger.read_text(), payload)

    def test_no_document_message_requires_reason(self):
        with self.assertRaises(IntakeError):
            self.intake.register_message("mail1", [])
        self.intake.register_message("mail1", [], "Notification has summary text only; no document link.")
        self.assertFalse(self.reload().status()["pending_messages"])


if __name__ == "__main__":
    unittest.main()
