import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'scripts'))
"""Synthetic tests for research state validation and merging; no real research is used."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

import research_state

TODAY = dt.date(2026, 6, 1)


def claim(**over):
    base = {
        "claim": "Example finding",
        "evidence": "short quote",
        "source_url": "https://example.com/a",
        "publish_date": "2026-05-12",
        "source_type": "primary",
        "read": "opened",
        "confidence": "high",
    }
    base.update(over)
    return base


class ArtifactsCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="research-state-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "findings").mkdir()

    def write_claims(self, name, records, raw_lines=()):
        lines = [json.dumps(r) for r in records] + list(raw_lines)
        (self.root / "findings" / name).write_text("\n".join(lines) + "\n")

    def write_state(self, name, data):
        (self.root / "findings" / name).write_text(json.dumps(data))


class NormalizeTests(unittest.TestCase):
    def test_url_drops_fragment_tracking_www_and_trailing_slash(self):
        a = research_state.normalize_url("HTTPS://www.Example.com/a/?utm_source=x&id=1#top")
        self.assertEqual(a, "https://example.com/a?id=1")

    def test_equivalent_urls_match(self):
        one = research_state.normalize_url("https://example.com/a/")
        two = research_state.normalize_url("https://www.example.com/a#x")
        self.assertEqual(one, two)

    def test_query_normalization_ignores_case_space_and_punctuation(self):
        one = research_state.normalize_query("  AEO vs. SEO?? ")
        two = research_state.normalize_query("aeo vs seo")
        self.assertEqual(one, two)


class ValidateTests(ArtifactsCase):
    def test_valid_records_pass(self):
        self.write_claims("sq1.jsonl", [claim(), claim(publish_date=None, read="search-only")])
        self.assertEqual(research_state.validate(self.root), [])

    def test_second_wave_ids_with_letter_suffix_validate_beside_wave_one(self):
        self.write_claims("sq2.jsonl", [claim()])
        self.write_claims("sq2b.jsonl", [claim(source_url="https://example.com/follow-up")])
        self.write_state("sq2b.state.json", {"queries": ["follow up"], "urls": [], "open_questions": []})
        self.assertEqual(research_state.validate(self.root), [])

    def test_bad_json_reports_file_and_line(self):
        self.write_claims("sq1.jsonl", [claim()], raw_lines=["{not json"])
        errors = research_state.validate(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("sq1.jsonl:2", errors[0])

    def test_missing_field_and_bad_enum_reported(self):
        bad = claim(source_type="blog")
        del bad["evidence"]
        self.write_claims("sq1.jsonl", [bad])
        text = " ".join(research_state.validate(self.root))
        self.assertIn("evidence", text)
        self.assertIn("source_type", text)

    def test_bad_date_and_url_reported(self):
        self.write_claims("sq1.jsonl", [claim(publish_date="May 2026", source_url="not a url")])
        text = " ".join(research_state.validate(self.root))
        self.assertIn("publish_date", text)
        self.assertIn("source_url", text)

    def test_blank_lines_are_skipped(self):
        self.write_claims("sq1.jsonl", [claim()], raw_lines=["", "   "])
        self.assertEqual(research_state.validate(self.root), [])

    def test_missing_findings_dir_is_an_error(self):
        empty = Path(self.temp.name) / "none"
        empty.mkdir()
        self.assertTrue(research_state.validate(empty))


class MergeTests(ArtifactsCase):
    def test_merge_dedupes_across_workers_and_adds_opened_claim_urls(self):
        self.write_state("sq1.state.json", {
            "queries": ["AEO vs SEO", "aeo statistics"],
            "urls": ["https://example.com/a/", "https://example.com/b"],
            "open_questions": ["Who owns this?"],
        })
        self.write_state("sq2.state.json", {
            "queries": ["aeo vs seo?"],
            "urls": ["https://www.example.com/a#x"],
            "open_questions": ["Who owns this?", "Is there a primary study?"],
        })
        self.write_claims("sq1.jsonl", [
            claim(source_url="https://example.com/c"),
            claim(source_url="https://example.com/d", read="search-only"),
        ])
        state = research_state.merge(self.root)
        self.assertEqual(len(state["executed_queries"]), 2)
        self.assertEqual(
            state["visited_urls"],
            ["https://example.com/a", "https://example.com/b", "https://example.com/c"],
        )
        self.assertEqual(len(state["open_questions"]), 2)

    def test_merge_keeps_existing_state_and_writes_file(self):
        (self.root / "state.json").write_text(json.dumps({
            "executed_queries": ["old query"],
            "visited_urls": ["https://example.com/old"],
            "open_questions": [],
        }))
        self.write_state("sq1.state.json", {"queries": ["new query"], "urls": [], "open_questions": []})
        research_state.merge(self.root)
        saved = json.loads((self.root / "state.json").read_text())
        self.assertIn("old query", saved["executed_queries"])
        self.assertIn("new query", saved["executed_queries"])
        self.assertIn("https://example.com/old", saved["visited_urls"])

    def test_merge_rejects_malformed_state_file(self):
        (self.root / "findings" / "sq1.state.json").write_text("{oops")
        with self.assertRaises(ValueError):
            research_state.merge(self.root)


class StatsTests(ArtifactsCase):
    def test_stats_flag_vendor_only_search_only_undated_and_stale(self):
        self.write_claims("sq1.jsonl", [
            claim(source_type="vendor"),
            claim(source_type="vendor", read="search-only"),
            claim(publish_date=None),
            claim(publish_date="2024-01-01"),
            claim(source_type="primary", read="opened"),
        ])
        self.write_claims("sq2.jsonl", [claim(source_type="vendor"), claim(source_type="secondary")])
        stats = research_state.stats(self.root, TODAY)
        self.assertEqual(stats["total_claims"], 7)
        self.assertEqual(stats["search_only"], 1)
        self.assertEqual(stats["undated"], 1)
        self.assertEqual(stats["stale"], 1)
        self.assertEqual(stats["stale_days"], 365)
        self.assertEqual(stats["by_source_type"]["vendor"], 3)
        by_file = stats["files"]
        self.assertEqual(by_file["sq1.jsonl"]["vendor_only"], False)
        self.assertEqual(by_file["sq2.jsonl"]["vendor_only"], False)

    def test_vendor_only_file_is_flagged(self):
        self.write_claims("sq1.jsonl", [claim(source_type="vendor"), claim(source_type="vendor")])
        stats = research_state.stats(self.root, TODAY)
        self.assertTrue(stats["files"]["sq1.jsonl"]["vendor_only"])


class FreshnessThresholdTests(ArtifactsCase):
    def test_stale_days_threshold_is_configurable(self):
        self.write_claims("sq1.jsonl", [claim(publish_date="2026-02-01"), claim(publish_date="2026-05-01")])
        strict = research_state.stats(self.root, TODAY, stale_days=60)
        loose = research_state.stats(self.root, TODAY, stale_days=365)
        self.assertEqual(strict["stale"], 1)
        self.assertEqual(strict["stale_days"], 60)
        self.assertEqual(loose["stale"], 0)


REPORT_OK = """# Topic: research report

## Bottom line
Clicks fell 38% on triggered queries [1]. Source overlap is low [2].

## Sources
[1] https://example.com/a (primary)
[2] https://example.com/b (secondary)
"""


class CheckReportTests(ArtifactsCase):
    def setUp(self):
        super().setUp()
        self.write_claims("sq1.jsonl", [
            claim(source_url="https://example.com/a"),
            claim(source_url="https://www.example.com/b/"),
        ])

    def report(self, text):
        (self.root / "report.md").write_text(text)
        return research_state.check_report(self.root)

    def test_clean_report_has_no_errors_or_warnings(self):
        result = self.report(REPORT_OK)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])

    def test_citation_without_source_entry_is_error(self):
        result = self.report(REPORT_OK.replace("[2] https://example.com/b (secondary)\n", "").replace("[2]", "[3]"))
        self.assertTrue(any("[3]" in e for e in result["errors"]))

    def test_source_url_not_in_claims_is_error(self):
        result = self.report(REPORT_OK.replace("https://example.com/b", "https://other.example.org/z"))
        self.assertTrue(any("other.example.org" in e for e in result["errors"]))

    def test_uncited_source_is_warning(self):
        result = self.report(REPORT_OK.replace(" Source overlap is low [2].", " Source overlap is low."))
        self.assertEqual(result["errors"], [])
        self.assertTrue(any("[2]" in w for w in result["warnings"]))

    def test_paragraph_with_figure_and_no_citation_is_warning(self):
        text = REPORT_OK.replace("## Sources", "Zero-click rose to 83% last year.\n\n## Sources")
        result = self.report(text)
        self.assertTrue(any("83%" in w for w in result["warnings"]))

    def test_missing_report_is_error(self):
        result = research_state.check_report(self.root)
        self.assertTrue(result["errors"])


BRIEF_OK = """# Topic: decision brief
Date: 2026-06-01

## Recommendation
Do the small thing first [1]. Skip the large one [2].

## What we found
### Clicks fell 40% when an overview appeared (confidence: medium)
- Overviews cut outbound clicks [1].
So what: protect organic reach first.

### Referrals stay small next to search (confidence: low)
- Few visits come from assistants [2].
So what: size any budget from your own logs.

## What we don't know
- No independent pricing data.

## What would change this
- A live replication of the study.

## Next steps
- Check analytics for assistant referrals. Owner to assign. Date to set.

## Sources
[1] https://example.com/a (primary)
[2] https://example.com/b (secondary)
"""


class CheckBriefTests(ArtifactsCase):
    def setUp(self):
        super().setUp()
        self.write_claims("sq1.jsonl", [
            claim(source_url="https://example.com/a", claim="Clicks fell 40% with an overview"),
            claim(source_url="https://www.example.com/b/", evidence="about 1% of visits"),
        ])

    def brief(self, text):
        (self.root / "brief.md").write_text(text)
        return research_state.check_brief(self.root)

    def test_clean_brief_has_no_errors(self):
        result = self.brief(BRIEF_OK)
        self.assertEqual(result["errors"], [])

    def test_missing_section_is_error(self):
        result = self.brief(BRIEF_OK.replace("## Next steps\n- Check analytics for assistant referrals. Owner to assign. Date to set.\n\n", ""))
        self.assertTrue(any("Next steps" in e for e in result["errors"]))

    def test_one_pillar_is_error(self):
        text = BRIEF_OK.replace("### Referrals stay small next to search (confidence: low)\n- Few visits come from assistants [2].\nSo what: size any budget from your own logs.\n\n", "")
        result = self.brief(text)
        self.assertTrue(any("pillar" in e for e in result["errors"]))

    def test_title_figure_missing_from_claims_is_error(self):
        result = self.brief(BRIEF_OK.replace("fell 40%", "fell 55%"))
        self.assertTrue(any("55%" in e for e in result["errors"]))

    def test_year_in_title_is_not_a_figure(self):
        result = self.brief(BRIEF_OK.replace("Clicks fell 40%", "Clicks fell 40% by 2026"))
        self.assertEqual(result["errors"], [])

    def test_bad_citation_is_error(self):
        result = self.brief(BRIEF_OK.replace("https://example.com/b", "https://other.example.org/z"))
        self.assertTrue(any("other.example.org" in e for e in result["errors"]))

    def test_long_brief_is_warning(self):
        padding = " ".join(["word"] * 520)
        result = self.brief(BRIEF_OK.replace("## What we don't know", f"{padding}\n\n## What we don't know"))
        self.assertTrue(any("words" in w for w in result["warnings"]))

    def test_missing_brief_is_error(self):
        self.assertTrue(research_state.check_brief(self.root)["errors"])


if __name__ == "__main__":
    unittest.main()
