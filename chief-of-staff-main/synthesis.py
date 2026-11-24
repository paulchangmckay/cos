#!/usr/bin/env python3
"""
Activity scanner for the chief-of-staff project.

Reads classified usage-tracker JSONL logs and outputs activity summaries
grouped by project. Raw assistant conversation transcripts are not input.
Supports legacy session rows and v2 collector-emitted daily_activity rows.

Usage:
  synthesis.py --days 7
  synthesis.py --days 0
  synthesis.py --days 1
  synthesis.py --date 2026-04-10
  synthesis.py --format json
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import re
import signal
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DEFAULT_LOG_DIR = Path(
    os.environ.get(
        "CHIEF_OF_STAFF_LOG_DIR",
        str(Path.home() / ".local/share/chief-of-staff/activity-logs"),
    )
).expanduser()
CLASSIFICATION_STATES = {
    "ok",
    "trivial",
    "no_transcript",
    "classify_timeout",
    "unclassified_other_error",
    "classify_error",
    "parse_error",
}
DAILY_ACTIVITY_RECORD = "daily_activity"


class _ReadTimeout(Exception):
    """Raised when reading a single log file exceeds the per-file timeout."""


_ACT_TS_RE = re.compile(r"-(\d{8})T\d{6}\.jsonl$")


def _file_in_window(
    path: Path, dt_from: _dt.date | None, dt_to: _dt.date | None
) -> bool:
    """Date-filter reliably-timestamped activities-* files; keep everything else.

    The per-session ``activities-<machine>-YYYYMMDDTHHMMSS.jsonl`` files carry a
    date in their name, so when a window is requested we skip files clearly
    outside it (one-day margin for timezone/boundary effects). Files without a
    parseable date (e.g. the rolling ``sessions-*.jsonl``) are always kept and
    filtered downstream by ``in_range``. This keeps recent queries from even
    opening the (often cloud-only / dehydrated) historical files.
    """
    if dt_from is None:
        return True
    m = _ACT_TS_RE.search(path.name)
    if not m:
        return True
    try:
        fdate = _dt.datetime.strptime(m.group(1), "%Y%m%d").date()
    except ValueError:
        return True
    margin = _dt.timedelta(days=1)
    if fdate < dt_from - margin:
        return False
    if dt_to and fdate > dt_to + margin:
        return False
    return True


class LogDirUnavailable(Exception):
    """Raised when the log root exists but its contents cannot be enumerated.

    A configured log root can live on a cloud-backed mount. When its sync
    client is unavailable, the directory entry can still exist while listing
    it raises ``Operation not permitted``. Globbing then silently yields
    zero files, which is indistinguishable from a genuinely empty window. We must
    surface this loudly rather than report "0 sessions" off blind data.
    """


class LogInputError(ValueError):
    """Configured logs are incomplete or not supported classified activity."""


def discover_log_files(root: Path) -> list[Path]:
    """List the root and its immediate subdirectories without hiding I/O errors."""
    files: list[Path] = []
    try:
        with os.scandir(root) as entries:
            children = list(entries)
        for entry in children:
            path = Path(entry.path)
            if path.suffix == ".jsonl":
                files.append(path)
            elif entry.is_dir():
                with os.scandir(path) as entries:
                    files.extend(Path(child.path) for child in entries
                                 if Path(child.path).suffix == ".jsonl")
    except OSError as exc:
        raise LogDirUnavailable(f"{root}: {exc}") from exc
    return sorted(files)


def parse_timestamp(ts: str | None) -> _dt.datetime | None:
    """Parse an explicitly timezone-aware timestamp, retaining its supplied offset."""
    if not isinstance(ts, str) or not ts:
        return None
    try:
        parsed = _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        parsed.astimezone(_dt.timezone.utc)
        return parsed
    except (ValueError, OverflowError):
        return None


def parse_date_value(value: str | None) -> _dt.date | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return _dt.date.fromisoformat(value)
    except ValueError:
        return None


def validate_row(row: Any) -> dict[str, Any]:
    """Require the minimal classified tracker schema, allowing producer extensions."""
    if not isinstance(row, dict):
        raise LogInputError("expected a classified activity object")
    string_fields = (
        "timestamp", "collector_run_at", "activity_date", "transcript_path",
        "category", "classification_state", "summary", "working_directory",
        "user", "record_type", "entrypoint", "session_id", "_folder_user",
        "suggested_new_category",
    )
    for field in string_fields:
        if field in row and not isinstance(row[field], str):
            raise LogInputError(f"{field} must be a string")
    state = row.get("classification_state", "").strip()
    category = row.get("category", "").strip()
    if state and state not in CLASSIFICATION_STATES:
        raise LogInputError(f"unsupported classification_state: {state!r}")
    if not category and not state:
        raise LogInputError("unsupported record: expected category or a known classification_state; raw transcripts are not activity logs")
    if state == "ok" and not category:
        raise LogInputError("classification_state ok requires a nonempty category")
    for field in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens"):
        if field in row and (type(row[field]) is not int or row[field] < 0):
            raise LogInputError(f"{field} must be a nonnegative integer")
    if "session_duration_minutes" in row:
        value = row["session_duration_minutes"]
        try:
            valid_duration = type(value) in (int, float) and math.isfinite(value) and value >= 0
        except OverflowError:
            valid_duration = False
        if not valid_duration:
            raise LogInputError("session_duration_minutes must be a finite nonnegative number")
    if row.get("record_type") == DAILY_ACTIVITY_RECORD:
        if parse_date_value(row.get("activity_date")) is None:
            raise LogInputError("daily_activity requires a valid activity_date (YYYY-MM-DD)")
        if not row.get("transcript_path", "").strip():
            raise LogInputError("daily_activity requires a nonempty transcript_path")
        if not (parse_timestamp(row.get("collector_run_at")) or parse_timestamp(row.get("timestamp"))):
            raise LogInputError("daily_activity requires a timezone-aware collector_run_at or timestamp")
    elif parse_timestamp(row.get("timestamp")) is None:
        raise LogInputError("legacy activity requires a timezone-aware timestamp")
    return row


def load_rows(
    root: Path,
    dt_from: _dt.date | None = None,
    dt_to: _dt.date | None = None,
    read_timeout: int = 6,
    files: list[Path] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def _on_alarm(signum: int, frame: Any) -> None:
        raise _ReadTimeout("read deadline exceeded")

    has_alarm = hasattr(signal, "SIGALRM")
    previous_handler = signal.signal(signal.SIGALRM, _on_alarm) if has_alarm else None
    try:
        if files is None:
            files = discover_log_files(root)
        for path in files:
            if not _file_in_window(path, dt_from, dt_to):
                continue
            folder_user = path.parent.name if path.parent != root else None
            line_number = 0
            try:
                if has_alarm:
                    signal.alarm(read_timeout)
                with path.open("r", encoding="utf-8") as handle:
                    for line_number, line in enumerate(handle, 1):
                        if not line.strip():
                            continue
                        try:
                            row = validate_row(json.loads(line))
                        except (ValueError, RecursionError) as exc:
                            raise LogInputError(f"{path}:{line_number}: {exc}") from exc
                        if row.get("record_type") == DAILY_ACTIVITY_RECORD and (
                            row.get("entrypoint") == "sdk-cli"
                            or "/subagents/" in row.get("transcript_path", "")
                        ):
                            continue
                        if folder_user:
                            row.setdefault("_folder_user", folder_user)
                        rows.append(row)
            except (OSError, UnicodeError, _ReadTimeout) as exc:
                raise LogInputError(f"{path}:{line_number or 1}: cannot read log ({exc})") from exc
            finally:
                if has_alarm:
                    signal.alarm(0)
    finally:
        if has_alarm:
            signal.signal(signal.SIGALRM, previous_handler)
    return rows


def activity_date_for_row(row: dict[str, Any]) -> _dt.date | None:
    if row.get("record_type") == DAILY_ACTIVITY_RECORD:
        dt = parse_date_value(str(row.get("activity_date") or ""))
        if dt:
            return dt
    ts = parse_timestamp(row.get("timestamp"))
    return ts.date() if ts else None


def in_range(row: dict[str, Any], dt_from: _dt.date | None, dt_to: _dt.date | None) -> bool:
    activity_date = activity_date_for_row(row)
    if activity_date is None:
        return False
    if dt_from and activity_date < dt_from:
        return False
    if dt_to and activity_date > dt_to:
        return False
    return True


def active_tokens(row: dict[str, Any]) -> int:
    return int(row.get("input_tokens", 0) or 0) + int(row.get("output_tokens", 0) or 0)


def total_tokens(row: dict[str, Any]) -> int:
    return (
        active_tokens(row)
        + int(row.get("cache_read_tokens", 0) or 0)
        + int(row.get("cache_creation_tokens", 0) or 0)
    )


def infer_classification_state(row: dict[str, Any]) -> str:
    state = str(row.get("classification_state") or "").strip()
    if state in CLASSIFICATION_STATES:
        return state
    category = row.get("category")
    summary = str(row.get("summary") or "")
    if category == "Trivial":
        return "trivial"
    if category == "Unclassified" and summary == "No transcript data":
        return "no_transcript"
    if category == "Unclassified" and "TimeoutExpired" in summary:
        return "classify_timeout"
    if category == "Unclassified" and "parse failed" in summary.lower():
        return "parse_error"
    if category == "Unclassified":
        return "unclassified_other_error"
    return "ok"


def attribute_user(row: dict[str, Any]) -> str:
    return row.get("_folder_user") or row.get("user") or "unknown"


def annotate_row(row: dict[str, Any], idx: int) -> dict[str, Any]:
    out = dict(row)
    out["_idx"] = idx
    out["_user"] = attribute_user(row)
    timestamp = parse_timestamp(row.get("timestamp"))
    collector = parse_timestamp(row.get("collector_run_at")) or timestamp
    out["_ts"] = timestamp.astimezone(_dt.timezone.utc) if timestamp else None
    out["_collector_run_ts"] = collector.astimezone(_dt.timezone.utc) if collector else None
    out["_activity_date"] = activity_date_for_row(row)
    out["_record_type"] = row.get("record_type") or "legacy_session_end"
    out["_state"] = infer_classification_state(row)
    out["_total_tokens"] = total_tokens(row)
    out.setdefault("snapshot_count", 1)
    out.setdefault("first_snapshot_at", row.get("timestamp", ""))
    out.setdefault("last_snapshot_at", row.get("timestamp", ""))
    out.setdefault("had_unclassified_snapshot", row.get("category") == "Unclassified")
    out.setdefault("had_no_transcript_snapshot", out["_state"] == "no_transcript")
    out.setdefault("had_classification_retry", False)
    out.setdefault("used_prior_classification", False)
    return out


def _ts_rank(row: dict[str, Any]) -> float:
    dt = row.get("_ts")
    return dt.timestamp() if isinstance(dt, _dt.datetime) else float("-inf")


def _collector_rank(row: dict[str, Any]) -> float:
    dt = row.get("_collector_run_ts")
    if isinstance(dt, _dt.datetime):
        return dt.timestamp()
    return _ts_rank(row)


def canonical_group(group: list[dict[str, Any]], *, rank_fn, snapshot_time_field: str) -> dict[str, Any]:
    canonical = max(
        group,
        key=lambda r: (rank_fn(r), r["_total_tokens"], 1 if r["_state"] == "ok" else 0, r["_idx"]),
    )
    out = dict(canonical)

    classified_group = [row for row in group if row["_state"] == "ok"]
    if out["_state"] != "ok" and classified_group:
        prior_classified = max(
            classified_group,
            key=lambda r: (rank_fn(r), r["_total_tokens"], r["_idx"]),
        )
        for field in (
            "category",
            "summary",
            "confidence",
            "suggested_new_category",
            "taxonomy_version",
        ):
            out[field] = prior_classified.get(field)
        out["_state"] = "ok"
        out["used_prior_classification"] = True
    else:
        out["used_prior_classification"] = False

    def snapshot_marker(row: dict[str, Any]) -> str:
        preferred = row.get(snapshot_time_field)
        return preferred if parse_timestamp(preferred) else str(row.get("timestamp") or "")

    parsed_times = sorted(
        (parsed.astimezone(_dt.timezone.utc), snapshot_marker(r))
        for r in group
        if (parsed := parse_timestamp(snapshot_marker(r))) is not None
    )
    if parsed_times:
        out["first_snapshot_at"] = parsed_times[0][1]
        out["last_snapshot_at"] = parsed_times[-1][1]
    else:
        stamps = [snapshot_marker(r) for r in group if snapshot_marker(r)]
        out["first_snapshot_at"] = stamps[0] if stamps else ""
        out["last_snapshot_at"] = stamps[-1] if stamps else ""

    out["snapshot_count"] = len(group)
    out["had_unclassified_snapshot"] = any(r.get("category") == "Unclassified" for r in group)
    out["had_no_transcript_snapshot"] = any(r["_state"] == "no_transcript" for r in group)
    out["had_classification_retry"] = any(r["_state"] != "ok" for r in group) and any(
        r["_state"] == "ok" for r in group
    )
    return out


def canonicalize_daily(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        transcript_path = str(row.get("transcript_path") or "").strip()
        if not transcript_path:
            transcript_path = f"__missing_path__:{row['_idx']}"
        activity_date = str(row.get("activity_date") or "").strip()
        if not activity_date:
            activity_date = f"__missing_date__:{row['_idx']}"
        grouped[(row["_user"], transcript_path, activity_date)].append(row)
    return sorted(
        (
            canonical_group(group, rank_fn=_collector_rank, snapshot_time_field="collector_run_at")
            for group in grouped.values()
        ),
        key=lambda r: (_ts_rank(r), _collector_rank(r), r["_total_tokens"], r["_idx"]),
    )


def canonicalize_legacy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        sid = str(row.get("session_id") or "").strip()
        if not sid:
            sid = f"__missing__:{row['_idx']}"
        grouped[(row["_user"], sid)].append(row)
    return sorted(
        (
            canonical_group(group, rank_fn=_ts_rank, snapshot_time_field="timestamp")
            for group in grouped.values()
        ),
        key=lambda r: (_ts_rank(r), r["_total_tokens"], r["_idx"]),
    )


def drop_legacy_rows_covered_by_daily(
    legacy_rows: list[dict[str, Any]],
    daily_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    covered = {
        (row["_user"], str(row.get("session_id") or ""), str(row.get("activity_date") or ""))
        for row in daily_rows
        if row.get("session_id") and row.get("activity_date")
    }
    if not covered:
        return legacy_rows

    kept: list[dict[str, Any]] = []
    for row in legacy_rows:
        activity_date = row.get("_activity_date")
        key = (
            row["_user"],
            str(row.get("session_id") or ""),
            activity_date.isoformat() if isinstance(activity_date, _dt.date) else "",
        )
        if key in covered:
            continue
        kept.append(row)
    return kept


def canonicalize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    daily_rows = [row for row in rows if row["_record_type"] == DAILY_ACTIVITY_RECORD]
    legacy_rows = [row for row in rows if row["_record_type"] != DAILY_ACTIVITY_RECORD]
    canonical_daily = canonicalize_daily(daily_rows)
    canonical_legacy = canonicalize_legacy(legacy_rows)
    canonical_legacy = drop_legacy_rows_covered_by_daily(canonical_legacy, canonical_daily)
    return sorted(
        canonical_legacy + canonical_daily,
        key=lambda r: (_ts_rank(r), _collector_rank(r), r["_total_tokens"], r["_idx"]),
    )


PROJECT_ALIASES: dict[str, str] = {}


def project_name(working_dir: str) -> str:
    if not working_dir:
        return "(unknown)"
    for pattern, alias in PROJECT_ALIASES.items():
        if pattern in working_dir:
            return alias
    p = Path(working_dir)
    name = p.name
    if name.startswith("_"):
        name = name[1:]
    return name or p.parent.name or "(unknown)"


def fmt_duration(minutes: float | None) -> str:
    if not minutes:
        return "?"
    if minutes < 60:
        return f"{int(minutes)}m"
    return f"{int(minutes // 60)}h{int(minutes % 60)}m"


def display_category(row: dict[str, Any]) -> str:
    state = row.get("_state")
    if state == "ok":
        return str(row.get("category") or "?")
    return f"Unclassified ({state})"


def state_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(str(row.get("_state") or "unknown") for row in rows)


def mixed_mode_note(rows: list[dict[str, Any]]) -> str | None:
    has_daily = any(row["_record_type"] == DAILY_ACTIVITY_RECORD for row in rows)
    has_legacy = any(row["_record_type"] != DAILY_ACTIVITY_RECORD for row in rows)
    if has_daily and has_legacy:
        return "Mixed mode: daily_activity rows are treated as canonical; overlapping legacy SessionEnd rows are excluded."
    return None


def row_revision_suffix(row: dict[str, Any]) -> str:
    count = int(row.get("snapshot_count", 1) or 1)
    if count <= 1:
        return ""
    noun = "revisions" if row.get("_record_type") == DAILY_ACTIVITY_RECORD else "snapshots"
    return f" [{count} {noun}]"


def fmt_text(rows: list[dict[str, Any]], dt_from: _dt.date, dt_to: _dt.date) -> str:
    lines: list[str] = []
    states = state_counts(rows)
    ok_count = states.get("ok", 0)
    unclassified_count = len(rows) - ok_count
    lines.append(
        f"Activity: {dt_from} to {dt_to} ({len(rows)} sessions; {ok_count} classified, {unclassified_count} unclassified)"
    )
    lines.append(
        "States: " + ", ".join(f"{state}={count}" for state, count in sorted(states.items()))
    )
    note = mixed_mode_note(rows)
    if note:
        lines.append(note)
    lines.append("")

    by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_project[project_name(row.get("working_directory", ""))].append(row)

    for proj, proj_rows in sorted(
        by_project.items(),
        key=lambda item: (-sum(r["_total_tokens"] for r in item[1]), -len(item[1]), item[0]),
    ):
        total_dur = sum(r.get("session_duration_minutes", 0) or 0 for r in proj_rows)
        categories = defaultdict(int)
        for row in proj_rows:
            categories[display_category(row)] += 1
        cat_str = ", ".join(
            f"{category}: {count}"
            for category, count in sorted(categories.items(), key=lambda item: (-item[1], item[0]))
        )
        lines.append(f"## {proj} ({len(proj_rows)} sessions, {fmt_duration(total_dur)})")
        lines.append(f"   Categories: {cat_str}")
        for row in sorted(proj_rows, key=lambda item: (_ts_rank(item), _collector_rank(item))):
            ts = str(row.get("activity_date") or str(row.get("timestamp") or "")[:16].replace("T", " "))
            dur = fmt_duration(row.get("session_duration_minutes"))
            label = display_category(row)
            notes: list[str] = []
            suffix = row_revision_suffix(row)
            if row.get("used_prior_classification"):
                notes.append("salvaged classification")
            if suffix:
                notes.append(suffix.strip(" []"))
            note_suffix = f" [{' ; '.join(notes)}]" if notes else ""
            lines.append(
                f"   {ts}  {dur:>6s}  {label:28s}  {row.get('summary', '')}{note_suffix}"
            )
        lines.append("")

    lines.append("---")
    lines.append(f"Unclassified sessions: {unclassified_count}")
    lines.append(f"No-transcript sessions: {states.get('no_transcript', 0)}")
    lines.append(f"Classification timeouts: {states.get('classify_timeout', 0)}")
    lines.append(f"Other classification errors: {states.get('unclassified_other_error', 0) + states.get('classify_error', 0) + states.get('parse_error', 0)}")
    lines.append(
        f"Recovered by canonical salvage: {sum(1 for row in rows if row.get('used_prior_classification'))}"
    )
    return "\n".join(lines)


def fmt_json(rows: list[dict[str, Any]], dt_from: _dt.date, dt_to: _dt.date) -> str:
    by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_project[project_name(row.get("working_directory", ""))].append(row)

    states = state_counts(rows)
    output = {
        "range": {"from": str(dt_from), "to": str(dt_to)},
        "total_sessions": len(rows),
        "classified_sessions": states.get("ok", 0),
        "unclassified_sessions": len(rows) - states.get("ok", 0),
        "state_counts": dict(sorted(states.items())),
        "mixed_mode": mixed_mode_note(rows) is not None,
        "projects": {},
    }
    for proj, proj_rows in by_project.items():
        output["projects"][proj] = {
            "sessions": len(proj_rows),
            "total_duration_minutes": round(
                sum(r.get("session_duration_minutes", 0) or 0 for r in proj_rows), 1
            ),
            "entries": [
                {
                    "timestamp": str(r.get("timestamp") or "")[:19],
                    "activity_date": str(r.get("activity_date") or ""),
                    "record_type": r.get("_record_type"),
                    "classification_state": r.get("_state"),
                    "category": display_category(r),
                    "summary": r.get("summary") or "",
                    "duration_minutes": r.get("session_duration_minutes") or 0,
                    "total_tokens": r.get("_total_tokens") or 0,
                    "snapshot_count": r.get("snapshot_count") or 1,
                    "used_prior_classification": bool(r.get("used_prior_classification")),
                }
                for r in sorted(proj_rows, key=lambda item: (_ts_rank(item), _collector_rank(item)))
            ],
        }
    return json.dumps(output, indent=2)


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=lambda value: Path(value).expanduser(), default=DEFAULT_LOG_DIR)
    ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--date", type=_dt.date.fromisoformat, default=None)
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument(
        "--allow-empty",
        action="store_true",
        help="Permit a reachable-but-empty log directory (zero .jsonl files) "
        "instead of treating it as a down/unsynced mount.",
    )
    return ap.parse_args(argv)


def resolve_range(args: argparse.Namespace) -> tuple[_dt.date, _dt.date]:
    today = _dt.datetime.now().date()
    if args.date:
        return args.date, args.date
    days = 0 if args.days is None else args.days
    dt_from = today - _dt.timedelta(days=days)
    return dt_from, today


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.root.exists():
        print(f"Log root not found: {args.root}", file=sys.stderr)
        return 1

    try:
        files = discover_log_files(args.root)
    except LogDirUnavailable as exc:
        print(
            f"synthesis: cannot read log directory ({exc}). "
            "Check --root or CHIEF_OF_STAFF_LOG_DIR and restore access to the "
            "configured log source. Refusing to report zero sessions from missing evidence.",
            file=sys.stderr,
        )
        return 2
    if not files and not args.allow_empty:
        print(
            f"synthesis: log directory {args.root} is reachable but contains no .jsonl "
            "session logs. Configure a usage tracker or restore the log source. Pass --allow-empty "
            "if you genuinely expect no logs.",
            file=sys.stderr,
        )
        return 2

    dt_from, dt_to = resolve_range(args)
    try:
        rows = [
            annotate_row(row, i)
            for i, row in enumerate(load_rows(args.root, dt_from, dt_to, files=files))
        ]
    except LogInputError as exc:
        print(f"synthesis: {exc}. Refusing to summarize incomplete evidence.", file=sys.stderr)
        return 2
    rows = [row for row in rows if in_range(row, dt_from, dt_to)]
    rows = [row for row in rows if row["_state"] != "trivial"]
    rows = canonicalize(rows)

    if args.format == "json":
        print(fmt_json(rows, dt_from, dt_to))
    else:
        print(fmt_text(rows, dt_from, dt_to))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
