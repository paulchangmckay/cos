import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'scripts'))
"""Synthetic tests for identity, evidence boundaries, and derived views."""
import copy
import contextlib
import io
from unittest import mock
import tempfile
import unittest
from pathlib import Path

import context


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="context-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for name in ("projects", "people", "knowledge"):
            (self.root / name).mkdir()
        (self.root / "knowledge/evidence.md").write_text("# Evidence\n\nA proposal, not an accepted assignment.\n")
        self.person = {
            "schema": 1, "id": "person:alex-rivera", "type": "person",
            "name": "Alex Rivera", "aliases": ["Rivera"], "sections": ["working-context"],
            "relations": [{
                "type": "contributes_to", "to": "system:signal-hub",
                "status": "proposed", "basis": "documented", "as_of": "2026-01-10",
                "sources": ["knowledge/evidence.md#evidence"],
                "note": "The draft names Alex; assignment acceptance is unknown."
            }]
        }
        self.system = {
            "schema": 1, "id": "system:signal-hub", "type": "system",
            "name": "Signal Hub", "aliases": ["Hub"], "sections": ["scope"], "relations": []
        }
        self.write("people/alex.md", self.person, "# Alex Rivera\n\n## Working context\n\nPreserve nuance.\n")
        self.write("projects/hub.md", self.system, "# Signal Hub\n\n## Scope\n\nA proposed capability.\n")

    def write(self, path, data, body=None):
        target = self.root / path
        if body is None:
            body = context.BLOCK.sub("", target.read_text()).rstrip() + "\n"
        target.write_text(body + "\n" + context.MARKER + "\n" + context.FENCE + "json\n"
                          + context.json.dumps(data, indent=2) + "\n" + context.FENCE + "\n")

    def test_incoming_view_preserves_proposal_scope_and_evidence(self):
        records = context.load_records(self.root)
        found = list(context.edges(records, "system:signal-hub"))
        self.assertEqual(len(found), 1)
        rendered = context.edge_line(self.root, records, *found[0])
        self.assertIn("Status: proposed; basis: documented; observed: 2026-01-10", rendered)
        self.assertIn("assignment acceptance is unknown", rendered)
        self.assertIn("knowledge/evidence.md#evidence", rendered)
        self.assertNotIn("owns", rendered)

    def test_exact_alias_resolution_does_not_guess_partial_names(self):
        records = context.load_records(self.root)
        self.assertEqual(context.resolve(records, "Rivera")["id"], self.person["id"])
        with self.assertRaisesRegex(ValueError, "No unique exact"):
            context.resolve(records, "Alex")
        with self.assertRaisesRegex(ValueError, "unknown"):
            context.resolve(records, "Unindexed project")

    def test_duplicate_identity_and_alias_fail(self):
        duplicate = copy.deepcopy(self.person)
        self.write("people/duplicate.md", duplicate, "# Copy\n\n## Working context\n\nTest.\n")
        with self.assertRaisesRegex(ValueError, "Duplicate ID"):
            context.load_records(self.root)
        duplicate["id"] = "person:another-person"
        duplicate["name"] = "Another Person"
        duplicate["aliases"] = ["Rivera"]
        self.write("people/duplicate.md", duplicate)
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            context.load_records(self.root)

    def test_incomplete_or_overstated_edges_fail(self):
        mutations = [
            ("missing source", lambda r: r.update(sources=[])),
            ("missing target", lambda r: r.update(to="system:missing")),
            ("bad date", lambda r: r.update(as_of="2026-02-30")),
            ("inferred acceptance", lambda r: r.update(basis="inferred", status="accepted")),
            ("inferred observation", lambda r: r.update(basis="inferred", status="observed")),
            ("missing status", lambda r: r.pop("status")),
        ]
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = copy.deepcopy(self.person)
                mutate(changed["relations"][0])
                self.write("people/alex.md", changed)
                with self.assertRaises(ValueError):
                    context.load_records(self.root)

    def test_source_paths_and_headings_must_resolve_inside_repository(self):
        for bad in ("../outside.md", "/tmp/outside.md", "knowledge/missing.md", "knowledge/evidence.md#missing"):
            with self.subTest(source=bad):
                changed = copy.deepcopy(self.person)
                changed["relations"][0]["sources"] = [bad]
                self.write("people/alex.md", changed)
                with self.assertRaises(ValueError):
                    context.load_records(self.root)

    def test_changed_prose_invalidates_saved_index_and_live_query_reads_new_data(self):
        records = context.load_records(self.root)
        index_path = self.root / context.INDEX
        index_path.write_text(context.render_index(self.root, records))
        context.validate_index(self.root, records)
        person_path = self.root / 'people/alex.md'
        person_path.write_text(person_path.read_text().replace('Preserve nuance.', 'Preserve updated nuance.'))
        with self.assertRaisesRegex(ValueError, 'stale'):
            context.validate_index(self.root, context.load_records(self.root))
        changed = copy.deepcopy(self.person)
        (self.root / "knowledge/acceptance.md").write_text("# Acceptance\n\nAlex accepted the scoped responsibility on January 12.\n")
        changed["relations"][0]["sources"] = ["knowledge/acceptance.md"]
        changed["relations"][0]["status"] = "accepted"
        changed["relations"][0]["as_of"] = "2026-01-12"
        changed["relations"][0]["note"] = "The new source explicitly records acceptance."
        self.write("people/alex.md", changed)
        updated = context.load_records(self.root)
        with self.assertRaisesRegex(ValueError, "stale"):
            context.validate_index(self.root, updated)
        found = list(context.edges(updated, "system:signal-hub"))
        self.assertEqual(found[0][1]["status"], "accepted")
        index_path.write_text(context.render_index(self.root, updated))
        context.validate_index(self.root, updated)

    def test_section_reads_do_not_include_metadata_or_neighbor_sections(self):
        text = "# Record\n\n## Scope\n\nUseful prose.\n\n## Other\n\nUnrelated.\n\n"
        text += context.MARKER + "\n" + context.FENCE + 'json\n{"schema": 1}\n' + context.FENCE + "\n"
        scoped = context.sections(text)["scope"]
        self.assertIn("Useful prose.", scoped)
        self.assertNotIn("Unrelated", scoped)
        self.assertNotIn("schema", scoped)

    def test_duplicate_json_fields_fail(self):
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            context.json.loads('{"id":"one","id":"two"}', object_pairs_hook=context.unique_object)


    def test_parent_record_directories_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory(prefix="context-outside-") as outside:
            outside_path = Path(outside)
            (outside_path / "sample.md").write_text("This outside file must not be read.\n")
            for name in ("projects", "people"):
                with self.subTest(directory=name):
                    original = self.root / name
                    saved = self.root / (name + "-saved")
                    original.rename(saved)
                    original.symlink_to(outside_path, target_is_directory=True)
                    try:
                        with self.assertRaisesRegex(ValueError, "escapes repository"):
                            context.load_records(self.root)
                    finally:
                        original.unlink()
                        saved.rename(original)

    def test_direct_record_symlink_is_rejected(self):
        link = self.root / "projects/symlink.md"
        link.symlink_to(self.root / "projects/hub.md")
        with self.assertRaisesRegex(ValueError, "cannot be symlinks"):
            context.load_records(self.root)

    def test_index_parent_symlink_cannot_read_or_write_outside_repository(self):
        with tempfile.TemporaryDirectory(prefix="context-index-outside-") as outside:
            outside_path = Path(outside)
            target = outside_path / "context-index.md"
            target.write_text("Keep the external index unchanged.\n")
            original = self.root / "knowledge"
            original.rename(self.root / "knowledge-saved")
            original.symlink_to(outside_path, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "escapes repository"):
                context.validate_index(self.root, {})
            with mock.patch("sys.argv", ["context.py", "--root", str(self.root), "index", "--write"]):
                with mock.patch.object(context, "load_records", return_value={}):
                    with contextlib.redirect_stderr(io.StringIO()):
                        result = context.main()
            self.assertNotEqual(result, 0)
            self.assertEqual(target.read_text(), "Keep the external index unchanged.\n")

    def test_last_record_removal_requires_index_rebuild(self):
        records = context.load_records(self.root)
        path = self.root / context.INDEX
        path.write_text(context.render_index(self.root, records))
        for record in records.values():
            (self.root / record["path"]).unlink()
        self.assertEqual(context.load_records(self.root), {})
        with self.assertRaisesRegex(ValueError, "stale"):
            context.validate_index(self.root, {})
        path.write_text(context.render_index(self.root, {}))
        context.validate_index(self.root, {})
        path.unlink()
        context.validate_index(self.root, {})

    def test_index_file_symlink_is_rejected_even_for_empty_workspace(self):
        path = self.root / context.INDEX
        path.symlink_to(self.root / "knowledge/evidence.md")
        with self.assertRaisesRegex(ValueError, "cannot be a symlink"):
            context.validate_index(self.root, {})


if __name__ == "__main__":
    unittest.main()
