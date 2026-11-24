import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'scripts'))
"""Synthetic tests for the one-on-one roster; no real people or notes are used."""
import contextlib
import datetime as dt
import io
import json
import tempfile
import unittest
from pathlib import Path

import one_on_one

TODAY = dt.date(2026, 1, 31)


def record(name, cadence=None, asks=(), log=()):
    lines = [f"# {name}", ""]
    if cadence:
        lines += [f"**Cadence:** {cadence}", ""]
    lines += ["## Open asks", *asks, "", "## Log"]
    for day in log:
        lines += [f"### {day} · notes", "**What's working:** x", ""]
    return "\n".join(lines) + "\n"


class RosterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="one-on-one-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "one-on-ones").mkdir()

    def put(self, name, text):
        (self.root / "one-on-ones" / name).write_text(text)

    def rows(self):
        return {row["name"]: row for row in one_on_one.roster(self.root, TODAY)}

    def test_status_thresholds_follow_cadence(self):
        self.put("a.md", record("Ana", "weekly", log=["2026-01-28"]))      # 3 days: ok
        self.put("b.md", record("Ben", "weekly", log=["2026-01-24"]))      # 7 days: due
        self.put("c.md", record("Cy", "weekly", log=["2026-01-15"]))       # 16 days: overdue
        rows = self.rows()
        self.assertEqual([rows[n]["status"] for n in ("Ana", "Ben", "Cy")], ["ok", "due", "overdue"])
        self.assertEqual(rows["Cy"]["days_since"], 16)

    def test_never_and_unset_are_distinct_from_ok(self):
        self.put("d.md", record("Dee", "monthly"))
        self.put("e.md", record("Eli", None, log=["2026-01-30"]))
        rows = self.rows()
        self.assertEqual(rows["Dee"]["status"], "never")
        self.assertEqual(rows["Eli"]["status"], "unset")
        self.assertIsNone(rows["Dee"]["last"])

    def test_latest_log_date_wins_regardless_of_order(self):
        self.put("f.md", record("Fay", "fortnightly", log=["2026-01-02", "2026-01-29", "2026-01-10"]))
        self.assertEqual(self.rows()["Fay"]["last"], "2026-01-29")

    def test_open_asks_count_and_age_ignore_done_items(self):
        asks = ["- [ ] 2026-01-10 Decide pilot scope", "- [x] 2026-01-02 Intro to Sam", "- [ ] 2026-01-25 Review plan"]
        self.put("g.md", record("Gus", "weekly", asks=asks, log=["2026-01-30"]))
        row = self.rows()["Gus"]
        self.assertEqual((row["open_asks"], row["oldest_ask_days"]), (2, 21))

    def test_custom_day_cadence_and_unknown_cadence(self):
        self.put("h.md", record("Hal", "every 10 days", log=["2026-01-20"]))
        self.put("i.md", record("Ivy", "whenever", log=["2026-01-20"]))
        rows = self.rows()
        self.assertEqual(rows["Hal"]["status"], "due")
        self.assertEqual(rows["Ivy"]["status"], "unset")

    def test_invalid_date_fails_loudly_and_names_the_file(self):
        self.put("bad.md", record("Bo", "weekly", log=["2026-13-40"]))
        with self.assertRaisesRegex(ValueError, "bad.md"):
            one_on_one.roster(self.root, TODAY)

    def test_missing_folder_is_empty_not_an_error(self):
        empty = Path(tempfile.mkdtemp(prefix="one-on-one-empty-"))
        self.addCleanup(lambda: empty.rmdir())
        self.assertEqual(one_on_one.roster(empty, TODAY), [])

    def test_sort_puts_overdue_first_then_oldest_ask(self):
        self.put("j.md", record("Jo", "weekly", log=["2026-01-30"]))
        self.put("k.md", record("Kit", "weekly", log=["2026-01-10"]))
        self.assertEqual([r["name"] for r in one_on_one.roster(self.root, TODAY)], ["Kit", "Jo"])

    def test_cli_json_and_text(self):
        self.put("l.md", record("Lou", "weekly", log=["2026-01-10"]))
        for fmt, needle in (("json", '"overdue"'), ("text", "Lou")):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = one_on_one.main(["roster", "--root", str(self.root), "--today", "2026-01-31", "--format", fmt])
            self.assertEqual(code, 0)
            self.assertIn(needle, out.getvalue())
        data = json.loads(self._json())
        self.assertEqual(data[0]["name"], "Lou")

    def _json(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            one_on_one.main(["roster", "--root", str(self.root), "--today", "2026-01-31", "--format", "json"])
        return out.getvalue()


if __name__ == "__main__":
    unittest.main()
