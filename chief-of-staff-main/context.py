#!/usr/bin/env python3
"""Read a small, optional relationship index from local Markdown. Standard library only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlsplit

MARKER = "<!-- context-record -->"
FENCE = chr(96) * 3
BLOCK = re.compile(re.escape(MARKER) + r"\s*" + FENCE + r"json\n(.*?)\n" + FENCE, re.S)
KINDS = {"person", "initiative", "system"}
RELATIONS = {"contributes_to", "depends_on", "part_of", "owns", "reports_to"}
STATUSES = {"observed", "proposed", "accepted", "unresolved", "ended"}
BASES = {"documented", "reported", "inferred"}
INDEX = Path("knowledge/context-index.md")
COVERAGE = ("Coverage is limited to explicitly indexed records and selected relationships. "
            "Missing records or edges are unknown. Read the linked prose and dated sources; "
            "this index does not establish current authority or deployment.")


def fail(message):
    raise ValueError(message)


def anchor(text):
    text = re.sub(r"[*_\x60]", "", text).strip().lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def sections(text):
    body = BLOCK.sub("", text)
    headings = list(re.finditer(r"^## (.+)$", body, re.M))
    return {anchor(h.group(1)): body[h.start():headings[i + 1].start() if i + 1 < len(headings) else len(body)].strip()
            for i, h in enumerate(headings)}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("Duplicate JSON key: " + key)
        result[key] = value
    return result


def local_source(root, reference):
    if not isinstance(reference, str) or not reference:
        fail("Sources must be nonempty strings")
    parsed = urlsplit(reference)
    if parsed.scheme in {"https", "http"}:
        if not parsed.netloc:
            fail("Invalid source URL: " + reference)
        return
    if parsed.scheme or parsed.netloc or Path(parsed.path).is_absolute():
        fail("Local sources must be relative to the repository: " + reference)
    path = (root / unquote(parsed.path)).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        fail("Source escapes repository: " + reference)
    if not path.is_file():
        fail("Missing source: " + reference)
    if parsed.fragment and path.suffix == ".md":
        headings = re.findall(r"^#{1,6} (.+)$", path.read_text(), re.M)
        if unquote(parsed.fragment) not in {anchor(h) for h in headings}:
            fail("Missing source heading: " + reference)


def contained_path(root, path, label):
    """Resolve parents before access so symlinks cannot escape the repository."""
    try:
        resolved = path.resolve()
    except RuntimeError:
        fail(label + " contains an unresolvable symlink: " + str(path))
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        fail(label + " escapes repository: " + str(path))
    return resolved


def load_records(root):
    root = root.resolve()
    records = {}
    for folder in ("projects", "people"):
        directory = contained_path(root, root / folder, "Record directory")
        for path in sorted(directory.glob("*.md")):
            if path.is_symlink():
                fail("Indexed records cannot be symlinks: " + str(path))
            contained_path(root, path, "Indexed record")
            text = path.read_text()
            if MARKER not in text:
                continue
            matches = list(BLOCK.finditer(text))
            if text.count(MARKER) != 1 or len(matches) != 1:
                fail("Expected one complete context block: " + str(path))
            data = json.loads(matches[0].group(1), object_pairs_hook=unique_object)
            if not isinstance(data, dict):
                fail("Context block must be an object: " + str(path))
            allowed = {"schema", "id", "type", "name", "aliases", "sections", "relations"}
            if set(data) - allowed:
                fail("Unknown record fields: " + str(set(data) - allowed))
            if type(data.get("schema")) is not int or data["schema"] != 1 or not isinstance(data.get("type"), str) or data["type"] not in KINDS:
                fail("Invalid schema or type: " + str(path))
            identity = data.get("id", "")
            if not isinstance(identity, str) or not re.fullmatch(re.escape(data["type"]) + r":[a-z0-9]+(?:-[a-z0-9]+)*", identity):
                fail("Invalid stable ID: " + str(path))
            if identity in records:
                fail("Duplicate ID: " + identity)
            if not isinstance(data.get("name"), str) or not data["name"].strip():
                fail("Missing name: " + identity)
            for field in ("aliases", "sections"):
                values = data.get(field, [])
                if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
                    fail("Invalid " + field + ": " + identity)
                if len({v.casefold() for v in values}) != len(values):
                    fail("Duplicate " + field + ": " + identity)
                data[field] = values
            for heading in data["sections"]:
                if heading not in sections(text):
                    fail("Missing section " + heading + ": " + identity)
            if not isinstance(data.get("relations", []), list):
                fail("Relations must be a list: " + identity)
            data["relations"] = data.get("relations", [])
            records[identity] = dict(data, path=path.relative_to(root).as_posix(), text=text)
    names = {}
    for identity, record in records.items():
        for name in [identity, record["name"]] + record["aliases"]:
            key = name.casefold()
            if key in names and names[key] != identity:
                fail("Ambiguous indexed name or alias: " + name)
            names[key] = identity
        seen = set()
        for rel in record["relations"]:
            required = {"type", "to", "status", "basis", "as_of", "sources", "note"}
            if not isinstance(rel, dict) or set(rel) != required:
                fail("Relationship needs type, target, status, basis, date, sources and note: " + identity)
            if not all(isinstance(rel[k], str) for k in required - {"sources"}):
                fail("Relationship fields must be strings: " + identity)
            if rel["type"] not in RELATIONS or rel["status"] not in STATUSES or rel["basis"] not in BASES:
                fail("Invalid relationship vocabulary: " + identity)
            if rel["to"] not in records:
                fail("Unknown relationship target: " + rel["to"])
            if (rel["type"], rel["to"]) in seen or rel["to"] == identity:
                fail("Repeated or self relationship: " + identity)
            seen.add((rel["type"], rel["to"]))
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", rel["as_of"]):
                fail("Invalid observation date: " + identity)
            date.fromisoformat(rel["as_of"])
            if not rel["note"].strip() or not isinstance(rel["sources"], list) or not rel["sources"]:
                fail("Relationship needs evidence and scope: " + identity)
            if rel["basis"] == "inferred" and rel["status"] in {"observed", "accepted"}:
                fail("Inference cannot establish observation or acceptance: " + identity)
            for source in rel["sources"]:
                local_source(root, source)
    return records


def resolve(records, query):
    matches = [r for r in records.values()
               if query.casefold() in {n.casefold() for n in [r["id"], r["name"]] + r["aliases"]}]
    if len(matches) != 1:
        fail("No unique exact indexed match for " + repr(query) +
             ". Use find, or search the remaining project files and stakeholders.md. " + COVERAGE)
    return matches[0]


def edges(records, identity=None):
    for record in sorted(records.values(), key=lambda r: r["id"]):
        for rel in record["relations"]:
            if identity is None or record["id"] == identity or rel["to"] == identity:
                yield record, rel


def reference_link(root, reference, from_dir=None):
    if urlsplit(reference).scheme:
        return reference
    path, sep, fragment = reference.partition("#")
    destination = os.path.relpath(root / path, from_dir) if from_dir else str(root / path)
    return destination + (sep + fragment if sep else "")


def edge_line(root, records, source, rel, from_dir=None):
    target = records[rel["to"]]
    left = "[" + source["name"] + "](" + reference_link(root, source["path"], from_dir) + ")"
    right = "[" + target["name"] + "](" + reference_link(root, target["path"], from_dir) + ")"
    evidence = ", ".join("[source " + str(i + 1) + "](" + reference_link(root, ref, from_dir) + ")"
                         for i, ref in enumerate(rel["sources"]))
    return (f"- {left} → {rel['type']} → {right}. "
            f"Status: {rel['status']}; basis: {rel['basis']}; observed: {rel['as_of']}. "
            f"{rel['note']} Evidence: {evidence}.")


def render_index(root, records):
    fingerprint = hashlib.sha256("".join(r["path"] + "\0" + r["text"] for r in sorted(records.values(), key=lambda r: r["id"])).encode()).hexdigest()
    lines = ["# Context index", "", COVERAGE, "",
             "Generated with python3 context.py index --write. Edit canonical Markdown; rebuild this view after changes.",
             "", "Input fingerprint: " + fingerprint + ".", "",
             "## Records", "", "| Record | Type | Stable ID |", "|---|---|---|"]
    for record in sorted(records.values(), key=lambda r: r["name"]):
        link = reference_link(root, record["path"], root / INDEX.parent)
        lines.append(f"| [{record['name']}]({link}) | {record['type']} | {record['id']} |")
    lines += ["", "## Relationships", ""]
    lines += [edge_line(root, records, src, rel, root / INDEX.parent) for src, rel in edges(records)]
    lines += ["", "## Other context", "",
              "Continue with [stakeholders](../stakeholders.md), [organization](../org/structure.md) and other project files when this view does not cover the question.",
              "Formal facts retain their original observation dates. Recheck consequential current facts against their authoritative sources.", ""]
    return "\n".join(lines)


def index_path(root):
    path = root / INDEX
    if path.is_symlink():
        fail("Context index cannot be a symlink: " + str(path))
    return contained_path(root, path, "Context index")


def validate_index(root, records):
    path = index_path(root)
    if not records and not path.exists():
        return
    if not path.exists() or path.read_text() != render_index(root, records):
        fail("Context index missing or stale. Run: python3 context.py index --write")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    index = commands.add_parser("index")
    index.add_argument("--write", action="store_true", help="Rebuild knowledge/context-index.md")
    find = commands.add_parser("find")
    find.add_argument("query")
    show = commands.add_parser("show")
    show.add_argument("query")
    section = commands.add_parser("section")
    section.add_argument("query")
    section.add_argument("heading", help="Markdown heading or its anchor")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        records = load_records(root)
        if args.command == "validate":
            validate_index(root, records)
            print(f"Valid: {len(records)} records, {sum(len(r['relations']) for r in records.values())} relationships; generated index current.")
        elif args.command == "index":
            output = render_index(root, records)
            if args.write:
                destination = index_path(root)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(output)
                print(destination)
            else:
                print(output, end="")
        elif args.command == "find":
            print(COVERAGE)
            matches = [r for r in records.values() if args.query.casefold() in " ".join([r["id"], r["name"]] + r["aliases"]).casefold()]
            for record in matches:
                print(f"{record['id']}: {record['name']} ({root / record['path']})")
            if not matches:
                fail("No indexed matches. Search remaining project files and stakeholders.md.")
        else:
            record = resolve(records, args.query)
            if args.command == "section":
                selected = sections(record["text"]).get(anchor(args.heading))
                if selected is None:
                    fail("Unknown section. Available: " + ", ".join(sections(record["text"])))
                print(f"Source: {root / record['path']}#{anchor(args.heading)}\n\n{selected}")
            else:
                print("# " + record["name"] + "\n\n" + COVERAGE)
                print("\nCanonical record: " + str(root / record["path"]))
                print("\n## Recorded relationships\n")
                found = list(edges(records, record["id"]))
                print("\n".join(edge_line(root, records, src, rel) for src, rel in found) if found else "No selected relationships recorded; coverage is incomplete.")
                print("\n## Read next\n")
                for heading in record["sections"]:
                    print(f"- {root / record['path']}#{heading}")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("Context error: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
