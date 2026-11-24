#!/usr/bin/env python3
"""Summarize private one-on-one records: who is due, and what asks are open. Standard library only."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

FOLDER = "one-on-ones"
CADENCE_DAYS = {"weekly": 7, "fortnightly": 14, "monthly": 30}
ORDER = {"overdue": 0, "due": 1, "never": 2, "unset": 3, "ok": 4}
LOG_HEADING = re.compile(r"^### (\d{4}-\d{2}-\d{2})\b", re.M)
OPEN_ASK = re.compile(r"^- \[ \] (\d{4}-\d{2}-\d{2})\b", re.M)
CADENCE = re.compile(r"^\*\*Cadence:\*\*\s*(.+?)\s*$", re.M)
EVERY_N = re.compile(r"^every (\d+) days?$", re.I)


def parse_day(text: str, path: Path) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{path.name}: invalid date '{text}'") from None


def cadence_days(text: str | None) -> int | None:
    if not text:
        return None
    text = text.strip().lower()
    if text in CADENCE_DAYS:
        return CADENCE_DAYS[text]
    match = EVERY_N.match(text)
    return int(match[1]) if match and int(match[1]) > 0 else None


def status_for(days_since: int | None, cadence: int | None) -> str:
    if days_since is None:
        return "never"
    if cadence is None:
        return "unset"
    if days_since >= cadence * 1.5:
        return "overdue"
    return "due" if days_since >= cadence else "ok"


def summarize(path: Path, today: date) -> dict:
    text = path.read_text(encoding="utf-8")
    title = re.search(r"^# (.+)$", text, re.M)
    cadence_text = CADENCE.search(text)
    cadence = cadence_days(cadence_text[1] if cadence_text else None)
    logged = [parse_day(d, path) for d in LOG_HEADING.findall(text)]
    asks = [parse_day(d, path) for d in OPEN_ASK.findall(text)]
    last = max(logged) if logged else None
    days_since = (today - last).days if last else None
    return {
        "name": title[1].strip() if title else path.stem,
        "file": f"{FOLDER}/{path.name}",
        "cadence": cadence_text[1] if cadence_text else None,
        "last": last.isoformat() if last else None,
        "days_since": days_since,
        "status": status_for(days_since, cadence),
        "open_asks": len(asks),
        "oldest_ask_days": (today - min(asks)).days if asks else None,
    }


def roster(root: Path, today: date) -> list[dict]:
    folder = Path(root) / FOLDER
    if not folder.is_dir():
        return []
    rows = [summarize(p, today) for p in sorted(folder.glob("*.md"))]
    return sorted(rows, key=lambda r: (ORDER[r["status"]], -(r["oldest_ask_days"] or 0), r["name"]))


def render(rows: list[dict], today: date) -> str:
    if not rows:
        return f"No one-on-one records under {FOLDER}/ as of {today}."
    lines = [f"One-on-ones as of {today}: {len(rows)} people", "",
             f"{'Name':<24}{'Status':<9}{'Last':<12}{'Days':>5}  {'Asks':>4}  Oldest ask"]
    for r in rows:
        days = "-" if r["days_since"] is None else r["days_since"]
        oldest = "-" if r["oldest_ask_days"] is None else f"{r['oldest_ask_days']}d"
        lines.append(f"{r['name'][:23]:<24}{r['status']:<9}{(r['last'] or '-'):<12}{days:>5}  {r['open_asks']:>4}  {oldest}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    cmd = commands.add_parser("roster", help="Who is due or overdue, and how many asks are open.")
    cmd.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    cmd.add_argument("--today", type=date.fromisoformat, default=None, help="YYYY-MM-DD; defaults to the host date.")
    cmd.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    today = args.today or date.today()
    try:
        rows = roster(args.root, today)
    except (ValueError, OSError) as error:
        print(f"One-on-one error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(rows, indent=2) if args.format == "json" else render(rows, today))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
