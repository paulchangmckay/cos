"""Synthetic scanner regressions; no assistant session history is used."""
import contextlib
import datetime as dt
import io
import json
import signal
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import synthesis


class SynthesisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthesis-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "sessions.jsonl"
        self.legacy = {
            "timestamp": "2026-01-10T10:00:00-05:00", "session_id": "sample-session",
            "category": "Planning", "summary": "A synthetic planning session.",
            "working_directory": "/example/workspace",
        }
        self.daily = dict(self.legacy, record_type="daily_activity", activity_date="2026-01-10",
                          transcript_path="/example/session.jsonl",
                          collector_run_at="2026-01-11T04:00:00Z")

    def write(self, *rows, path=None):
        (path or self.path).write_text("".join(json.dumps(row) + "\n" for row in rows))

    def invoke(self, *extra):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = synthesis.main(["--root", str(self.root), "--date", "2026-01-10", *extra])
        return result, stdout.getvalue(), stderr.getvalue()

    def canonical(self, *rows):
        return synthesis.canonicalize([synthesis.annotate_row(synthesis.validate_row(row), i)
                                       for i, row in enumerate(rows)])

    def test_minimal_legacy_defaults_and_text_and_json_interfaces(self):
        self.write(dict(self.legacy, record_type="producer-extension"))
        result, output, error = self.invoke("--format", "json")
        self.assertEqual((result, error), (0, ""))
        data = json.loads(output)
        self.assertEqual(data["total_sessions"], 1)
        entry = data["projects"]["workspace"]["entries"][0]
        self.assertEqual(entry["total_tokens"], 0)
        self.assertEqual(entry["duration_minutes"], 0)
        self.assertEqual(entry["record_type"], "producer-extension")
        result, output, error = self.invoke()
        self.assertEqual((result, error), (0, ""))
        self.assertIn("1 sessions; 1 classified", output)
        self.assertIn(self.legacy["summary"], output)

    def test_legacy_dedup_preserves_latest_metrics_and_salvages_classification(self):
        latest = dict(self.legacy, timestamp="2026-01-10T18:00:00Z", category="Unclassified",
                      summary="No transcript data", input_tokens=30, output_tokens=10)
        rows = self.canonical(self.legacy, latest)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["_total_tokens"], 40)
        self.assertEqual(row["summary"], self.legacy["summary"])
        self.assertEqual(row["snapshot_count"], 2)
        self.assertTrue(row["used_prior_classification"])
        self.assertTrue(row["had_no_transcript_snapshot"])
        self.assertTrue(row["had_classification_retry"])

    def test_daily_revisions_and_mixed_format_overlap(self):
        revised = dict(self.daily, collector_run_at="2026-01-12T01:00:00Z",
                       category="Delivery", input_tokens=50)
        other = dict(self.legacy, session_id="another-session")
        self.write(self.legacy, self.daily, revised, other)
        result, output, error = self.invoke("--format", "json")
        self.assertEqual((result, error), (0, ""))
        data = json.loads(output)
        self.assertEqual(data["total_sessions"], 2)
        self.assertTrue(data["mixed_mode"])
        entries = data["projects"]["workspace"]["entries"]
        daily = next(row for row in entries if row["record_type"] == "daily_activity")
        self.assertEqual(daily["snapshot_count"], 2)
        self.assertEqual(daily["total_tokens"], 50)
        self.assertEqual(daily["category"], "Delivery")

    def test_identical_session_ids_from_different_users_are_not_deduplicated(self):
        for user in ("sample-one", "sample-two"):
            folder = self.root / user
            folder.mkdir()
            self.write(self.legacy, path=folder / "sessions.jsonl")
        rows = synthesis.load_rows(self.root)
        self.assertEqual(len(self.canonical(*rows)), 2)

    def test_dates_use_daily_activity_and_legacy_supplied_offset(self):
        legacy = dict(self.legacy, timestamp="2026-01-10T23:30:00-08:00")
        daily = dict(self.daily, timestamp="2026-01-11T04:00:00Z")
        self.write(legacy, daily)
        result, output, error = self.invoke("--format", "json")
        self.assertEqual((result, error), (0, ""))
        self.assertEqual(json.loads(output)["total_sessions"], 1)
        day = dt.date(2026, 1, 10)
        self.assertTrue(synthesis.in_range(legacy, day, day))
        self.assertTrue(synthesis.in_range(daily, day, day))
        self.assertFalse(synthesis.in_range({}, day, day))
        args = synthesis.parse_args(["--days", "2"])
        start, end = synthesis.resolve_range(args)
        self.assertEqual((end - start).days, 2)
        args = synthesis.parse_args(["--days", "20", "--date", "2026-01-10"])
        self.assertEqual(synthesis.resolve_range(args), (day, day))

    def test_aware_time_sorting_and_daily_timestamp_fallback(self):
        earlier = dict(self.legacy, timestamp="2026-01-10T10:00:00+02:00")
        later = dict(self.legacy, timestamp="2026-01-10T09:30:00Z")
        row = self.canonical(later, earlier)[0]
        self.assertEqual(row["timestamp"], later["timestamp"])
        self.assertEqual(row["first_snapshot_at"], earlier["timestamp"])
        self.assertEqual(row["_ts"].tzinfo, dt.timezone.utc)
        for fallback in ("invalid", "2026-01-11T01:00:00"):
            daily = dict(self.daily, collector_run_at=fallback)
            row = self.canonical(daily)[0]
            self.assertEqual(row["first_snapshot_at"], self.daily["timestamp"])
        daily = dict(self.daily, timestamp="invalid")
        self.assertEqual(self.canonical(daily)[0]["first_snapshot_at"], self.daily["collector_run_at"])
        self.assertIsNone(synthesis.parse_timestamp("2026-01-10T10:00:00"))

    def test_valid_sdk_subagent_and_trivial_exclusions(self):
        self.write(dict(self.daily, entrypoint="sdk-cli"),
                   dict(self.daily, transcript_path="/example/subagents/child.jsonl"),
                   dict(self.legacy, category="Trivial"))
        result, output, error = self.invoke("--format", "json")
        self.assertEqual((result, error), (0, ""))
        self.assertEqual(json.loads(output)["total_sessions"], 0)
        self.write(dict(self.daily, entrypoint="sdk-cli", input_tokens=-1))
        result, output, error = self.invoke()
        self.assertNotEqual(result, 0)
        self.assertEqual(output, "")
        self.assertIn("input_tokens", error)

    def test_invalid_rows_fail_with_file_line_and_no_partial_summary(self):
        invalid = [
            [], 2, None, {},
            {"type": "session_meta", "timestamp": "2026-01-10T10:00:00Z", "payload": {}},
            dict(self.legacy, timestamp="2026-01-10T10:00:00"),
            dict(self.legacy, timestamp="2026-01-10"),
            dict(self.legacy, timestamp=123),
            dict(self.legacy, summary=[]),
            dict(self.legacy, working_directory={}),
            dict(self.legacy, classification_state="unknown"),
            dict(self.legacy, classification_state="ok", category=""),
            dict(self.daily, activity_date="2026-02-30"),
            dict(self.daily, activity_date="20260110"),
            dict(self.daily, transcript_path=" "),
            dict(self.daily, timestamp="invalid", collector_run_at="2026-01-10T10:00:00"),
        ]
        for field in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens"):
            invalid.extend(dict(self.legacy, **{field: value}) for value in (-1, True, "2", None, 1.5))
        invalid.extend(dict(self.legacy, session_duration_minutes=value)
                       for value in (-1, True, "2", None, float("nan"), float("inf"), 10**1000))
        for row in invalid:
            with self.subTest(row=row):
                self.write(self.legacy, row)
                result, output, error = self.invoke("--allow-empty")
                self.assertNotEqual(result, 0)
                self.assertEqual(output, "")
                self.assertIn("sessions.jsonl:2:", error)
                self.assertNotIn("Traceback", error)

    def test_malformed_json_and_invalid_utf8_are_evidence_failures(self):
        for content in (b'{"category":', b'\xff\n'):
            with self.subTest(content=content):
                self.path.write_bytes(content)
                result, output, error = self.invoke()
                self.assertNotEqual(result, 0)
                self.assertEqual(output, "")
                self.assertIn("sessions.jsonl:1:", error)

    def test_unreadable_and_timed_out_files_fail_without_summary(self):
        self.write(self.legacy)
        for exception in (PermissionError("sample denied"), synthesis._ReadTimeout("sample deadline")):
            with self.subTest(exception=exception):
                with mock.patch.object(Path, "open", side_effect=exception):
                    result, output, error = self.invoke()
                self.assertNotEqual(result, 0)
                self.assertEqual(output, "")
                self.assertIn("sessions.jsonl:1:", error)
                self.assertIn("cannot read log", error)

    def test_nested_directory_enumeration_errors_are_not_hidden(self):
        folder = self.root / "sample-user"
        folder.mkdir()
        original = synthesis.os.scandir
        def scandir(path):
            if Path(path) == folder:
                raise PermissionError("sample child denied")
            return original(path)
        with mock.patch.object(synthesis.os, "scandir", side_effect=scandir):
            result, output, error = self.invoke()
        self.assertNotEqual(result, 0)
        self.assertEqual(output, "")
        self.assertIn("sample child denied", error)
        self.assertIn("cannot read log directory", error)

    def test_missing_empty_and_outside_window_sources(self):
        result, output, error = self.invoke()
        self.assertNotEqual(result, 0)
        self.assertEqual(output, "")
        result, output, error = self.invoke("--allow-empty", "--format", "json")
        self.assertEqual((result, error), (0, ""))
        self.assertEqual(json.loads(output)["total_sessions"], 0)
        old = self.root / "activities-sample-20200101T120000.jsonl"
        old.write_text("malformed historical data\n")
        result, output, error = self.invoke("--format", "json")
        self.assertEqual((result, error), (0, ""))
        self.assertEqual(json.loads(output)["total_sessions"], 0)
        with contextlib.redirect_stderr(io.StringIO()):
            result = synthesis.main(["--root", str(self.root / "missing")])
        self.assertNotEqual(result, 0)

    def test_non_ok_classification_states_need_no_category(self):
        for state in synthesis.CLASSIFICATION_STATES - {"ok"}:
            row = dict(self.legacy, classification_state=state)
            del row["category"]
            self.assertEqual(synthesis.validate_row(row), row)

    @unittest.skipUnless(hasattr(signal, "SIGALRM"), "SIGALRM not available")
    def test_reader_restores_existing_alarm_handler(self):
        self.write(self.legacy)
        previous = signal.getsignal(signal.SIGALRM)
        synthesis.load_rows(self.root)
        self.assertEqual(signal.getsignal(signal.SIGALRM), previous)


if __name__ == "__main__":
    unittest.main()
