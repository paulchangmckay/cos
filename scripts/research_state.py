#!/usr/bin/env python3
"""Validate, merge, and summarize research findings for a topic. Standard library only.

Operates on a topic's artifacts directory (research-topics/<topic>/artifacts):
  findings/<sq-id>.jsonl        claim records, one JSON object per line
  findings/<sq-id>.state.json   a worker's queries, urls, and open questions
  state.json                    merged queries, visited urls, and open questions
  report.md                     final report with [n] citations checked against claims
  brief.md                      decision brief beside the report, checked by check-brief
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

FINDINGS = "findings"
STATE = "state.json"
REQUIRED = ("claim", "evidence", "source_url", "publish_date", "source_type", "read", "confidence")
SOURCE_TYPES = {"primary", "secondary", "vendor"}
READ_STATES = {"opened", "search-only"}
CONFIDENCE = {"high", "medium", "low"}
STALE_DAYS = 365
TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|mc_|ref$)", re.I)


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not TRACKING.match(k)])
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), host, path, query, ""))


def normalize_query(query: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", query.casefold()).split())


def claim_files(root: Path) -> list[Path]:
    return sorted((root / FINDINGS).glob("*.jsonl"))


def read_claims(path: Path):
    """Yield (line number, record or None, error or None) for each non-blank line."""
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            yield number, None, f"invalid JSON ({exc.msg})"
            continue
        if not isinstance(record, dict):
            yield number, None, "record is not a JSON object"
            continue
        yield number, record, None


def check_record(record: dict) -> list[str]:
    problems = []
    for key in REQUIRED:
        if key not in record:
            problems.append(f"missing field '{key}'")
    if "source_url" in record:
        parts = urlsplit(str(record["source_url"]))
        if parts.scheme not in ("http", "https") or not parts.netloc:
            problems.append("source_url must be an http(s) URL")
    if "publish_date" in record and record["publish_date"] is not None:
        try:
            date.fromisoformat(str(record["publish_date"]))
        except ValueError:
            problems.append("publish_date must be YYYY-MM-DD or null")
    for key, allowed in (("source_type", SOURCE_TYPES), ("read", READ_STATES), ("confidence", CONFIDENCE)):
        if key in record and record[key] not in allowed:
            problems.append(f"{key} must be one of {sorted(allowed)}")
    for key in ("claim", "evidence"):
        if key in record and not str(record[key]).strip():
            problems.append(f"{key} is empty")
    return problems


def validate(root: Path) -> list[str]:
    root = Path(root)
    if not (root / FINDINGS).is_dir():
        return [f"{root / FINDINGS}: findings directory not found"]
    errors = []
    for path in claim_files(root):
        for number, record, error in read_claims(path):
            if error:
                errors.append(f"{path.name}:{number}: {error}")
                continue
            for problem in check_record(record):
                errors.append(f"{path.name}:{number}: {problem}")
    return errors


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name}: invalid JSON ({exc.msg})") from None


def dedupe(values, normalize):
    seen, out = set(), []
    for value in values:
        key = normalize(value)
        if key and key not in seen:
            seen.add(key)
            out.append(value if normalize is normalize_query else key)
    return out


def merge(root: Path) -> dict:
    root = Path(root)
    queries, urls, questions, exhausted = [], [], [], []
    existing = root / STATE
    if existing.exists():
        saved = load_json(existing)
        queries += saved.get("executed_queries", [])
        urls += saved.get("visited_urls", [])
        questions += saved.get("open_questions", [])
        exhausted += saved.get("exhausted_tools", [])
    for path in sorted((root / FINDINGS).glob("*.state.json")):
        data = load_json(path)
        queries += data.get("queries", [])
        urls += data.get("urls", [])
        questions += data.get("open_questions", [])
        exhausted += data.get("exhausted_tools", [])
    for path in claim_files(root):
        for _, record, error in read_claims(path):
            if record and not error and record.get("read") == "opened" and record.get("source_url"):
                urls.append(record["source_url"])
    state = {
        "executed_queries": dedupe(queries, normalize_query),
        "visited_urls": sorted(dedupe(urls, normalize_url)),
        "open_questions": dedupe(questions, normalize_query),
        "exhausted_tools": sorted(set(exhausted)),
    }
    existing.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def stats(root: Path, today: date | None = None, stale_days: int = STALE_DAYS) -> dict:
    today = today or date.today()
    out = {"total_claims": 0, "search_only": 0, "undated": 0, "stale": 0, "stale_days": stale_days,
           "by_source_type": {}, "files": {}}
    for path in claim_files(Path(root)):
        types = set()
        count = 0
        for _, record, error in read_claims(path):
            if error or record is None:
                continue
            count += 1
            out["total_claims"] += 1
            kind = record.get("source_type")
            types.add(kind)
            out["by_source_type"][kind] = out["by_source_type"].get(kind, 0) + 1
            if record.get("read") == "search-only":
                out["search_only"] += 1
            published = record.get("publish_date")
            if published is None:
                out["undated"] += 1
                continue
            try:
                age = (today - date.fromisoformat(str(published))).days
            except ValueError:
                continue
            if age > stale_days:
                out["stale"] += 1
        out["files"][path.name] = {"claims": count, "vendor_only": bool(count) and types == {"vendor"}}
    return out


CITATION = re.compile(r"\[(\d+)\]")
SOURCE_LINE = re.compile(r"^\[(\d+)\]\s+(https?://\S+)")
FIGURE = re.compile(r"\d+(?:\.\d+)?\s?%|\b\d{2,}\b")


def check_report(root: Path, report: str = "report.md") -> dict:
    """Check numbered citations in a report against the claim records."""
    path = Path(root) / report
    if not path.exists():
        return {"errors": [f"{report}: not found"], "warnings": []}
    errors, warnings = [], []
    known = set()
    for claim_path in claim_files(Path(root)):
        for _, record, error in read_claims(claim_path):
            if record and not error and record.get("source_url"):
                known.add(normalize_url(str(record["source_url"])))
    body, sources, in_sources = [], {}, False
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^#{1,6}\s+Sources\b", line):
            in_sources = True
            continue
        if in_sources and line.startswith("#"):
            in_sources = False
        match = SOURCE_LINE.match(line) if in_sources else None
        if match:
            sources[match.group(1)] = match.group(2)
        elif not in_sources:
            body.append(line)
    for number, url in sorted(sources.items(), key=lambda item: int(item[0])):
        if normalize_url(url) not in known:
            errors.append(f"[{number}] {url}: not found in any claim record")
    text = "\n".join(body)
    cited = set(CITATION.findall(text))
    for number in sorted(cited - set(sources), key=int):
        errors.append(f"[{number}]: cited but has no entry in Sources")
    for number in sorted(set(sources) - cited, key=int):
        warnings.append(f"[{number}]: listed in Sources but never cited")
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block or block.startswith("#") or CITATION.search(block):
            continue
        figure = FIGURE.search(block)
        if figure:
            warnings.append(f"uncited figure '{figure.group(0)}': {block[:60]}")
    return {"errors": errors, "warnings": warnings}


BRIEF_SECTIONS = ("Recommendation", "What we found", "What we don't know", "What would change this",
                  "Next steps", "Sources")
BRIEF_WORD_LIMIT = 500
PILLARS = (2, 4)
YEAR = re.compile(r"^(19|20)\d\d$")


def check_brief(root: Path, brief: str = "brief.md") -> dict:
    """Check a decision brief: citations, required sections, pillar count, length, and title figures."""
    path = Path(root) / brief
    if not path.exists():
        return {"errors": [f"{brief}: not found"], "warnings": []}
    result = check_report(root, brief)
    errors, warnings = list(result["errors"]), list(result["warnings"])
    text = path.read_text(encoding="utf-8")
    headings = [line.lstrip("#").strip() for line in text.splitlines() if re.match(r"^##\s", line)]
    for section in BRIEF_SECTIONS:
        if section not in headings:
            errors.append(f"missing section '## {section}'")
    body = re.split(r"^##\s+Sources\b", text, maxsplit=1, flags=re.M)[0]
    titles = [line.lstrip("#").strip() for line in body.splitlines() if re.match(r"^###\s", line)]
    low, high = PILLARS
    if not low <= len(titles) <= high:
        errors.append(f"{len(titles)} pillar title(s); expected {low} to {high}")
    words = len(body.split())
    if words > BRIEF_WORD_LIMIT:
        warnings.append(f"{words} words before Sources; aim for {BRIEF_WORD_LIMIT} or fewer")
    evidence = " ".join(
        f"{record.get('claim', '')} {record.get('evidence', '')}"
        for claim_path in claim_files(Path(root))
        for _, record, error in read_claims(claim_path) if record and not error
    ).replace(" %", "%")
    for title in titles:
        for figure in FIGURE.findall(title):
            figure = figure.replace(" ", "")
            if YEAR.match(figure.rstrip("%")) or figure in evidence:
                continue
            errors.append(f"figure '{figure}' in title appears in no claim record: {title[:60]}")
    return {"errors": errors, "warnings": warnings}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, text in (("validate", "check claim records"), ("merge", "merge worker state into state.json"),
                       ("stats", "summarize source quality"), ("check-report", "check report citations"),
                       ("check-brief", "check the decision brief")):
        p = sub.add_parser(name, help=text)
        p.add_argument("artifacts", type=Path, help="research-topics/<topic>/artifacts")
        if name == "stats":
            p.add_argument("--as-of", type=date.fromisoformat, default=None, help="today's date, YYYY-MM-DD")
            p.add_argument("--stale-days", type=int, default=STALE_DAYS, help="claims older than this are stale")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            errors = validate(args.artifacts)
            for line in errors:
                print(line)
            print("ok" if not errors else f"{len(errors)} problem(s)")
            return 1 if errors else 0
        if args.command == "merge":
            state = merge(args.artifacts)
            print(json.dumps({k: len(v) for k, v in state.items()}))
            return 0
        if args.command in ("check-report", "check-brief"):
            result = (check_brief if args.command == "check-brief" else check_report)(args.artifacts)
            for line in result["errors"]:
                print(f"error: {line}")
            for line in result["warnings"]:
                print(f"warning: {line}")
            print("ok" if not result["errors"] else f"{len(result['errors'])} error(s)")
            return 1 if result["errors"] else 0
        print(json.dumps(stats(args.artifacts, args.as_of, args.stale_days), indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
