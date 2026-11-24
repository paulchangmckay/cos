#!/usr/bin/env python3
"""Local, connector-independent bookkeeping for email-discovered meeting sources."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import tempfile
from datetime import datetime, timedelta, timezone
from uuid import uuid4

class IntakeError(ValueError):
    """An actionable source or ledger error."""

def timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise IntakeError("Use an ISO timestamp with an explicit timezone offset.") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise IntakeError("Timestamps require an explicit timezone offset.")
    try:
        return result.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise IntakeError("Timestamp cannot be represented in UTC.") from exc

def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")

def now() -> str:
    return iso(datetime.now(timezone.utc))

def identity(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512 or any(c.isspace() for c in value):
        raise IntakeError("Source IDs must be nonempty strings without whitespace (at most 512 characters).")
    return value

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

class Intake:
    """One short-lived ledger transaction; reload after a concurrent-write conflict."""
    def __init__(self, root: str | Path = "."):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise IntakeError("Workspace root must be a directory.")
        self.path = self.inside("transcripts/.ingestion-state.json")
        self.original = self.path.read_bytes() if self.path.exists() else None
        if self.original is None:
            self.state = {"schema_version": 1, "last_completed_scan_at": None,
                          "last_completed_scan_id": None, "active_scan": None,
                          "messages": {}, "documents": {}}
        else:
            try:
                self.state = json.loads(self.original)
            except (UnicodeDecodeError, ValueError, RecursionError) as exc:
                raise IntakeError(f"Invalid ingestion ledger: {self.path}. Preserve and repair it before retrying.") from exc
            self._validate_state()

    def inside(self, relative: str | Path) -> Path:
        relative = Path(relative)
        if relative.is_absolute() or ".." in relative.parts:
            raise IntakeError(f"Archive path must stay within the workspace: {relative}")
        result = self.root / relative
        current = self.root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise IntakeError(f"Symlinks are not permitted in ingestion paths: {current}")
        if not result.resolve().is_relative_to(self.root):
            raise IntakeError(f"Ingestion path escapes the workspace: {relative}")
        return result

    def _validate_state(self):
        try:
            self._validate_state_fields()
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            raise IntakeError("Invalid ingestion ledger; preserve and repair it before retrying: " + str(exc)) from exc

    def _validate_state_fields(self):
        state = self.state
        required = {"schema_version", "last_completed_scan_at", "last_completed_scan_id", "active_scan", "messages", "documents"}
        if not isinstance(state, dict) or not required <= state.keys() or type(state["schema_version"]) is not int or state["schema_version"] != 1:
            raise IntakeError("Missing fields or unsupported schema.")
        if not isinstance(state["messages"], dict) or not isinstance(state["documents"], dict):
            raise IntakeError("Messages and documents must be objects.")
        for field in ("last_completed_scan_at",):
            if state[field] is not None:
                timestamp(state[field])
        if state["last_completed_scan_id"] is not None:
            identity(state["last_completed_scan_id"])
        if not isinstance(state.get("abandoned_scans", []), list):
            raise IntakeError("Invalid abandoned scan history.")
        active = state["active_scan"]
        if active is not None:
            scan_keys = {"id", "started_at", "since", "until", "query", "next_page_token", "pages", "enumeration_complete"}
            if not isinstance(active, dict) or not scan_keys <= active.keys() or not isinstance(active["pages"], list) or type(active["enumeration_complete"]) is not bool:
                raise IntakeError("Invalid active scan.")
            identity(active["id"])
            if timestamp(active["since"]) > timestamp(active["until"]) or timestamp(active["started_at"]) != timestamp(active["until"]):
                raise IntakeError("Invalid scan window.")
            if not isinstance(active["query"], str) or not active["query"]:
                raise IntakeError("Missing scan query.")
            if active["next_page_token"] is not None:
                identity(active["next_page_token"])
            for page in active["pages"]:
                if not isinstance(page, dict) or set(page) != {"page_token", "message_ids", "next_page_token"}:
                    raise IntakeError("Invalid saved search page.")
                self._id_list(page["message_ids"])
                for token in (page["page_token"], page["next_page_token"]):
                    if token is not None:
                        identity(token)
        for message_id, message in state["messages"].items():
            identity(message_id)
            if not isinstance(message, dict) or message.get("status") not in {"pending", "complete", "failed"}:
                raise IntakeError("Invalid message entry.")
            self._id_list(message["document_ids"])
            if message.get("last_error") is not None and not isinstance(message["last_error"], str):
                raise IntakeError("Invalid message failure.")
            if any(doc not in state["documents"] for doc in message["document_ids"]):
                raise IntakeError("Message references a missing document.")
        for doc_id, source in state["documents"].items():
            identity(doc_id)
            if not isinstance(source, dict) or not isinstance(source.get("snapshots"), list) or type(source["needs_fetch"]) is not bool:
                raise IntakeError("Invalid document entry.")
            self._id_list(source["message_ids"])
            if any(message not in state["messages"] for message in source["message_ids"]):
                raise IntakeError("Document references a missing message.")
            if source["last_error"] is not None and not isinstance(source["last_error"], str):
                raise IntakeError("Invalid document failure.")
            current = source["current_by_kind"]
            if not isinstance(current, dict) or set(current) - {"notes", "transcript"}:
                raise IntakeError("Invalid current source versions.")
            seen = set()
            for snapshot in source["snapshots"]:
                if not isinstance(snapshot, dict) or snapshot.get("kind") not in {"notes", "transcript"} or snapshot.get("status") not in {"archived", "complete"}:
                    raise IntakeError("Invalid source snapshot.")
                if not isinstance(snapshot["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", snapshot["sha256"]) or snapshot["id"] != snapshot["kind"] + ":" + snapshot["sha256"] or snapshot["id"] in seen:
                    raise IntakeError("Invalid or duplicate source identity.")
                seen.add(snapshot["id"])
                for field in ("archive_path", "metadata_path"):
                    value = snapshot[field]
                    if not isinstance(value, str) or not value.startswith("transcripts/"):
                        raise IntakeError("Source paths must be under transcripts/.")
                    self.inside(value)
                if not isinstance(snapshot["observed_versions"], list) or any(not isinstance(v, str) for v in snapshot["observed_versions"]):
                    raise IntakeError("Invalid provider versions.")
                timestamp(snapshot["retrieved_at"])
                timestamp(snapshot["last_retrieved_at"])
                if snapshot["status"] == "complete":
                    timestamp(snapshot["completed_at"])
            for kind, snapshot_id in current.items():
                if not any(item["id"] == snapshot_id and item["kind"] == kind for item in source["snapshots"]):
                    raise IntakeError("Current source version has no preserved snapshot.")

    @staticmethod
    def _id_list(values):
        if not isinstance(values, list):
            raise IntakeError("Expected a list of source IDs.")
        for value in values:
            identity(value)

    def save(self):
        """Serialize writers and reject stale instances without replacing their changes."""
        self.inside("transcripts").mkdir(parents=True, exist_ok=True)
        lock = self.inside("transcripts/.ingestion-state.lock")
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise IntakeError(f"Another write holds {lock}. If its process exited, inspect and remove that stale lock before retrying.") from exc
        try:
            os.close(fd)
            self.path = self.inside("transcripts/.ingestion-state.json")
            current = self.path.read_bytes() if self.path.exists() else None
            if current != self.original:
                raise IntakeError("Ingestion ledger changed concurrently. Reload status and retry; no ledger changes were saved.")
            payload = (json.dumps(self.state, indent=2, sort_keys=True) + "\n").encode()
            with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix=".ingestion-state-", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.replace(temporary, self.path)
            finally:
                temporary.unlink(missing_ok=True)
            self.original = payload
        finally:
            lock.unlink(missing_ok=True)

    def window(self, at: str) -> dict:
        end = timestamp(at).replace(microsecond=0)
        checkpoint = self.state["last_completed_scan_at"]
        start = timestamp(checkpoint) if checkpoint else end
        if start > end:
            raise IntakeError("Scan time precedes the last completed checkpoint.")
        start -= timedelta(days=7)
        query = ('(from:gemini-notes@google.com OR '
                 '(from:drive-shares-dm-noreply@google.com subject:"Notes by Gemini")) '
                 f'-in:spam -in:trash after:{int(start.timestamp())} before:{int(end.timestamp())}')
        return {"since": iso(start), "until": iso(end), "query": query}

    def scan_start(self, at: str) -> dict:
        if self.state["active_scan"] is not None:
            return self.state["active_scan"]
        window = self.window(at)
        scan = {"id": uuid4().hex, "started_at": window["until"], **window,
                "next_page_token": None, "pages": [], "enumeration_complete": False}
        self.state["active_scan"] = scan
        self.save()
        return scan

    def _scan(self, scan_id: str) -> dict:
        scan = self.state["active_scan"]
        if scan is None or scan["id"] != scan_id:
            raise IntakeError("No matching active scan. Use scan-start or resume its returned ID.")
        return scan

    def scan_page(self, scan_id: str, message_ids: list[str], next_page_token: str | None, page_token: str | None = None) -> dict:
        scan = self._scan(scan_id)
        if not isinstance(message_ids, list):
            raise IntakeError("message_ids must be a list of Gmail message IDs.")
        ids = sorted({identity(item) for item in message_ids})
        for token in (page_token, next_page_token):
            if token is not None:
                identity(token)
        page = {"page_token": page_token, "message_ids": ids, "next_page_token": next_page_token}
        for previous in scan["pages"]:
            if previous["page_token"] == page_token:
                if previous == page:
                    return {"scan_id": scan_id, "duplicate_page": True, "next_page_token": scan["next_page_token"]}
                raise IntakeError("The same page token returned different results; checkpoint was not advanced.")
        if scan["enumeration_complete"] or page_token != scan["next_page_token"]:
            raise IntakeError("Page is out of order; use the active scan's next_page_token.")
        if next_page_token is not None and (next_page_token == page_token or any(p["page_token"] == next_page_token for p in scan["pages"])):
            raise IntakeError("Search returned a repeated continuation token; checkpoint was not advanced.")
        for message_id in ids:
            self.state["messages"].setdefault(message_id, {"status": "pending", "document_ids": []})
        scan["pages"].append(page)
        scan["next_page_token"] = next_page_token
        scan["enumeration_complete"] = next_page_token is None
        self.save()
        return {"scan_id": scan_id, "next_page_token": next_page_token, "enumeration_complete": scan["enumeration_complete"]}

    def scan_restart(self, scan_id: str) -> dict:
        scan = self._scan(scan_id)
        # Preserve the abandoned pagination record, discovered IDs, and checkpoint.
        self.state.setdefault("abandoned_scans", []).append(scan.copy())
        restarted = dict(scan, id=uuid4().hex, pages=[], next_page_token=None, enumeration_complete=False)
        self.state["active_scan"] = restarted
        self.save()
        return restarted

    def scan_finish(self, scan_id: str) -> dict:
        if self.state["active_scan"] is None and self.state["last_completed_scan_id"] == scan_id:
            return {"last_completed_scan_at": self.state["last_completed_scan_at"]}
        scan = self._scan(scan_id)
        if not scan["enumeration_complete"] or not scan["pages"]:
            raise IntakeError("Discovery is incomplete. Record every search page, including the terminal page, before finishing.")
        self.state["last_completed_scan_at"] = scan["started_at"]
        self.state["last_completed_scan_id"] = scan_id
        self.state["active_scan"] = None
        self.save()
        return {"last_completed_scan_at": self.state["last_completed_scan_at"]}

    def _document(self, document_id: str) -> dict:
        identity(document_id)
        return self.state["documents"].setdefault(document_id, {
            "message_ids": [], "needs_fetch": True, "last_error": None, "snapshots": [], "current_by_kind": {}})

    def register_message(self, message_id: str, document_ids: list[str], no_document_reason: str | None = None) -> dict:
        identity(message_id)
        self._id_list(document_ids)
        if no_document_reason is not None and not isinstance(no_document_reason, str):
            raise IntakeError("A no-document reason must be text.")
        if not document_ids and not (isinstance(no_document_reason, str) and no_document_reason.strip()):
            raise IntakeError("Supply discovered document IDs, or explain why this notification contains no usable document.")
        for document_id in document_ids:
            identity(document_id)
        message = self.state["messages"].setdefault(message_id, {"status": "pending", "document_ids": []})
        for document_id in sorted(set(document_ids)):
            source = self._document(document_id)
            if message_id not in source["message_ids"]:
                source["message_ids"].append(message_id)
                source["needs_fetch"] = True
            if document_id not in message["document_ids"]:
                message["document_ids"].append(document_id)
        message.update(status="complete", last_error=None)
        if no_document_reason:
            message["no_document_reason"] = no_document_reason.strip()
        self.save()
        return message

    def _matching_archive(self, content_hash: str) -> Path | None:
        directory = self.inside("transcripts")
        if not directory.exists():
            return None
        for parent, directories, files in os.walk(directory, followlinks=False):
            directories[:] = sorted(d for d in directories if not d.startswith(".") and not (Path(parent) / d).is_symlink())
            for name in sorted(files):
                candidate = Path(parent) / name
                if name.startswith(".") or candidate.suffix != ".txt" or candidate.is_symlink():
                    continue
                candidate = self.inside(candidate.relative_to(self.root))
                if digest(candidate.read_bytes()) == content_hash:
                    return candidate
        return None

    def _write_new(self, path: Path, content: bytes):
        self.inside(path.relative_to(self.root))
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=path.parent, prefix=".source-")
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                # A hard link installs the fully written bytes atomically and
                # refuses to replace an existing archive, unlike os.replace.
                os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() != content:
                    raise IntakeError(f"Preserving conflicting archive: {path}. Inspect it before retrying.")
        finally:
            temporary.unlink(missing_ok=True)

    def archive(self, document_id: str, kind: str, content: bytes, *, provider_version: str | None = None,
                tab_id: str | None = None, source_url: str | None = None, retrieved_at: str | None = None) -> dict:
        identity(document_id)
        if kind not in {"notes", "transcript"}:
            raise IntakeError("Source kind must be notes or transcript.")
        if not isinstance(content, bytes) or not content.strip():
            raise IntakeError("Retrieved source text is empty; preserve the pending source and report the retrieval gap.")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise IntakeError("Retrieved source must be UTF-8 text.") from exc
        for value in (provider_version, tab_id, source_url):
            if value is not None and not isinstance(value, str):
                raise IntakeError("Source provenance values must be strings when supplied.")
        retrieved_at = iso(timestamp(retrieved_at or now()))
        source = self._document(document_id)
        content_hash = digest(content)
        snapshot_id = kind + ":" + content_hash
        snapshot = next((s for s in source["snapshots"] if s["id"] == snapshot_id), None)
        if snapshot is not None:
            self._verify_snapshot(document_id, snapshot)
            if provider_version is not None and provider_version not in snapshot["observed_versions"]:
                snapshot["observed_versions"].append(provider_version)
            snapshot["last_retrieved_at"] = retrieved_at
        else:
            archive = self._matching_archive(content_hash)
            reused = archive is not None
            stem = f"{digest(document_id.encode())[:16]}-{kind}-{content_hash}"
            if archive is None:
                archive = self.inside(f"transcripts/gemini/{stem}.txt")
                self._write_new(archive, content)
            metadata_path = self.inside(f"transcripts/gemini/{stem}.source.json")
            metadata = {"document_id": document_id, "kind": kind, "sha256": content_hash,
                        "provider_version": provider_version, "tab_id": tab_id, "source_url": source_url,
                        "retrieved_at": retrieved_at, "archive_path": str(archive.relative_to(self.root)),
                        "reused_existing_archive": reused}
            # Interrupted archival is recoverable by matching the preserved bytes.
            if not metadata_path.exists():
                self._write_new(metadata_path, (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode())
            else:
                preserved = json.loads(metadata_path.read_text())
                if not isinstance(preserved, dict) or any(preserved.get(k) != metadata[k] for k in ("document_id", "kind", "sha256")):
                    raise IntakeError("Conflicting source metadata; preserve it and inspect before retrying.")
                archive = self.inside(preserved["archive_path"])
            snapshot = {"id": snapshot_id, "kind": kind, "sha256": content_hash,
                        "archive_path": str(archive.relative_to(self.root)),
                        "metadata_path": str(metadata_path.relative_to(self.root)),
                        "observed_versions": [] if provider_version is None else [provider_version],
                        "retrieved_at": retrieved_at, "last_retrieved_at": retrieved_at, "status": "archived"}
            source["snapshots"].append(snapshot)
        self._verify_snapshot(document_id, snapshot)
        if source["current_by_kind"].get(kind) != snapshot_id:
            snapshot["status"] = "archived"
        source["current_by_kind"][kind] = snapshot_id
        source.update(needs_fetch=False, last_error=None)
        self.save()
        return {**snapshot, "needs_reconciliation": snapshot["status"] != "complete"}

    def _verify_snapshot(self, document_id: str, snapshot: dict):
        path = self.inside(snapshot["archive_path"])
        if not path.is_file() or digest(path.read_bytes()) != snapshot["sha256"]:
            raise IntakeError(f"Archived source is missing or changed: {path}. Restore or inspect it before retrying.")
        metadata_path = self.inside(snapshot["metadata_path"])
        try:
            metadata = json.loads(metadata_path.read_text())
        except (OSError, ValueError) as exc:
            raise IntakeError("Source metadata is missing or invalid; restore or inspect it before retrying.") from exc
        expected = {"document_id": document_id, "kind": snapshot["kind"], "sha256": snapshot["sha256"], "archive_path": snapshot["archive_path"]}
        if not isinstance(metadata, dict) or any(metadata.get(key) != value for key, value in expected.items()):
            raise IntakeError("Source metadata conflicts with the preserved snapshot.")

    def complete(self, document_id: str, snapshot_id: str) -> dict:
        source = self.state["documents"].get(document_id)
        snapshot = next((s for s in source["snapshots"] if s["id"] == snapshot_id), None) if source else None
        if snapshot is None:
            raise IntakeError("Archive this document snapshot before marking reconciliation complete.")
        if source["current_by_kind"].get(snapshot["kind"]) != snapshot_id:
            raise IntakeError("This snapshot was superseded; reconcile the current source version.")
        self._verify_snapshot(document_id, snapshot)
        snapshot.update(status="complete", completed_at=snapshot.get("completed_at") or now(), last_completed_at=now())
        self.save()
        return snapshot

    def fail(self, error: str, *, document_id: str | None = None, message_id: str | None = None) -> dict:
        if not isinstance(error, str) or not error.strip() or bool(document_id) == bool(message_id):
            raise IntakeError("Supply one document/message ID and a concrete nonempty error.")
        if document_id:
            source = self._document(document_id)
            source.update(needs_fetch=True, last_error=error.strip())
        else:
            identity(message_id)
            source = self.state["messages"].setdefault(message_id, {"document_ids": []})
            source.update(status="failed", last_error=error.strip())
        self.save()
        return source

    def status(self) -> dict:
        pending = {}
        for doc_id, source in self.state["documents"].items():
            current = set(source["current_by_kind"].values())
            incomplete = [s for s in source["snapshots"] if s["id"] in current and s["status"] != "complete"]
            awaiting = not any(s["kind"] == "transcript" and s["status"] == "complete" for s in source["snapshots"])
            if source["needs_fetch"] or incomplete or awaiting:
                pending[doc_id] = {"fetch_required": source["needs_fetch"] or awaiting,
                                   "awaiting_transcript": awaiting, "last_error": source["last_error"],
                                   "pending_reconciliation": incomplete}
        return {"last_completed_scan_at": self.state["last_completed_scan_at"],
                "active_scan": self.state["active_scan"],
                "pending_messages": {key: value for key, value in self.state["messages"].items() if value["status"] != "complete"},
                "pending_documents": pending}

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Workspace root (default: current directory).")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    window = commands.add_parser("window")
    window.add_argument("--at", default=None)
    start = commands.add_parser("scan-start")
    start.add_argument("--at", default=None)
    page = commands.add_parser("scan-page")
    page.add_argument("--scan", required=True)
    page.add_argument("--input", type=Path, required=True, help='JSON: {"message_ids": [...], "next_page_token": null|string}')
    page.add_argument("--page-token")
    restart = commands.add_parser("scan-restart")
    restart.add_argument("--scan", required=True)
    finish = commands.add_parser("scan-finish")
    finish.add_argument("--scan", required=True)
    message = commands.add_parser("register-message")
    message.add_argument("--message-id", required=True)
    message.add_argument("--document-id", action="append", default=[])
    message.add_argument("--no-document-reason")
    archive = commands.add_parser("archive")
    archive.add_argument("--document-id", required=True)
    archive.add_argument("--kind", choices=("notes", "transcript"), required=True)
    archive.add_argument("--input", type=Path, required=True)
    archive.add_argument("--version")
    archive.add_argument("--tab-id")
    archive.add_argument("--source-url")
    complete = commands.add_parser("complete")
    complete.add_argument("--document-id", required=True)
    complete.add_argument("--snapshot", required=True)
    fail = commands.add_parser("fail")
    target = fail.add_mutually_exclusive_group(required=True)
    target.add_argument("--document-id")
    target.add_argument("--message-id")
    fail.add_argument("--error", required=True)
    args = parser.parse_args(argv)
    try:
        intake = Intake(args.root)
        if args.command == "status":
            result = intake.status()
        elif args.command == "window":
            result = intake.window(args.at or now())
        elif args.command == "scan-start":
            result = intake.scan_start(args.at or now())
        elif args.command == "scan-page":
            payload = json.loads(args.input.read_text())
            if not isinstance(payload, dict) or "next_page_token" not in payload:
                raise IntakeError("Page JSON must contain message_ids and next_page_token (null for the terminal page).")
            result = intake.scan_page(args.scan, payload.get("message_ids"), payload["next_page_token"], args.page_token)
        elif args.command == "scan-restart":
            result = intake.scan_restart(args.scan)
        elif args.command == "scan-finish":
            result = intake.scan_finish(args.scan)
        elif args.command == "register-message":
            result = intake.register_message(args.message_id, args.document_id, args.no_document_reason)
        elif args.command == "archive":
            result = intake.archive(args.document_id, args.kind, args.input.read_bytes(), provider_version=args.version,
                                    tab_id=args.tab_id, source_url=args.source_url)
        elif args.command == "complete":
            result = intake.complete(args.document_id, args.snapshot)
        else:
            result = intake.fail(args.error, document_id=args.document_id, message_id=args.message_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (IntakeError, OSError, UnicodeError, json.JSONDecodeError, OverflowError, RuntimeError) as exc:
        parser.exit(1, f"meeting intake: {exc}\n")

if __name__ == "__main__":
    raise SystemExit(main())
