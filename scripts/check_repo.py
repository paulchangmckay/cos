#!/usr/bin/env python3
"""Check the release boundary and reusable Markdown in the index or a Git tree.

Only paths and rule names are reported for sensitive matches; source values are
never printed. This is a guardrail, not a substitute for reviewing the diff.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

PRIVATE_DIRS = {
    'people', 'projects', 'team', 'one-on-ones', 'okrs', 'daily', 'org', 'knowledge',
    'transcripts', 'drafts', 'debriefs', 'activity-logs', '.codex', '.claude',
}
PLACEHOLDERS = {'projects/.gitkeep', 'team/.gitkeep', 'one-on-ones/.gitkeep', 'okrs/.gitkeep', 'daily/.gitkeep'}
PRIVATE_FILES = {
    'self.md', 'stakeholders.md', 'priorities.md', 'operating-model.md',
    'sources.local.md', 'performance-ratings-guide.md',
}
CREDENTIAL_NAMES = {
    'auth.json', 'credentials.json', 'credentials.yaml', 'credentials.yml',
    '.mcp.json', '.netrc', '.npmrc', 'id_rsa', 'id_ed25519', 'id_ecdsa',
}
SECRET_RULES = {
    'GitHub token': re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b'),
    'OpenAI-style key': re.compile(r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b'),
    'AWS access key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'Google API key': re.compile(r'\bAIza[A-Za-z0-9_-]{30,}\b'),
    'Slack token': re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
    'private key': re.compile(r'-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----'),
    'credential assignment': re.compile(
        r'''(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|authorization)["']?\s*[:=]\s*["']?[A-Za-z0-9_+/=.-]{20,}'''),
    'URL credentials': re.compile(r'https?://[^\s/:@]+:[^\s/@]+@'),
}


def path_error(name: str) -> str | None:
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts:
        return 'unsafe path'
    if name in PLACEHOLDERS:
        return None
    if path.parts[0].casefold() in PRIVATE_DIRS or name.casefold() in PRIVATE_FILES:
        return 'private context path'
    lowered = path.name.lower()
    if (lowered in CREDENTIAL_NAMES or lowered == '.env' or lowered.startswith('.env.')
            or path.suffix.lower() in {'.pem', '.key', '.p12', '.pfx', '.kdbx', '.csv'}):
        return 'credential or local data file'
    return None


def unfenced(text: str) -> str:
    """Ignore examples when checking navigation links."""
    return re.sub(r'(?ms)^\s*(`{3,}|~{3,}).*?^\s*\1\s*$', '', text)


def anchors(text: str) -> set[str]:
    result: set[str] = set()
    counts: dict[str, int] = {}
    for heading in re.findall(r'(?m)^#{1,6}\s+(.+?)\s*#*$', unfenced(text)):
        slug = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(slug if count == 0 else f'{slug}-{count}')
    return result


def parse_frontmatter(front: str) -> dict[str, str]:
    """Validate the two-scalar YAML subset used by this repository's skills.

    Supporting a deliberately small syntax keeps CI dependency-free and rejects
    ambiguous YAML rather than treating a regex match as a successful parse.
    """
    fields: dict[str, str] = {}
    for line in front.splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        match = re.fullmatch(r'(name|description):[ \t]+(.+)', line)
        if not match or match[1] in fields:
            raise ValueError('Unexpected or duplicate frontmatter field')
        value = match[2].strip()
        if value.startswith('"'):
            value = json.loads(value)
        elif value.startswith("'"):
            if not re.fullmatch(r"'(?:[^']|'')*'", value):
                raise ValueError('Invalid YAML string')
            value = value[1:-1].replace("''", "'")
        elif (not value or value[0] in '|>!&*[{`@#' or re.match(r'[-?:](?:\s|$)', value) or re.search(r':(?:\s|$)', value)
              or re.search(r'\s#', value) or value.lower() in {'true', 'false', 'null', '~'}
              or re.fullmatch(r'[+-]?[0-9.]+', value)):
            raise ValueError('Use an unambiguous string')
        if not isinstance(value, str):
            raise ValueError('Frontmatter values must be strings')
        fields[match[1]] = value
    if set(fields) != {'name', 'description'}:
        raise ValueError('Missing frontmatter field')
    return fields


def check_files(files: dict[str, bytes], modes: dict[str, str] | None = None) -> list[str]:
    errors: list[str] = []
    decoded: dict[str, str] = {}
    for name, data in sorted(files.items()):
        issue = path_error(name)
        if issue:
            errors.append(f'{name}: {issue}')
            continue
        if modes and modes.get(name) not in {'100644', '100755'}:
            errors.append(f'{name}: release files must be regular files')
            continue
        if name in PLACEHOLDERS and data:
            errors.append(f'{name}: placeholder must be empty')
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            errors.append(f'{name}: binary or non-UTF-8 file requires explicit review')
            continue
        decoded[name] = text
        for rule, pattern in SECRET_RULES.items():
            if pattern.search(text):
                errors.append(f'{name}: possible {rule}')
        if name.startswith('.agents/skills/') and name.endswith('/SKILL.md'):
            front = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
            if not front:
                errors.append(f'{name}: missing skill frontmatter')
                continue
            try:
                fields = parse_frontmatter(front[1])
            except ValueError:
                errors.append(f'{name}: invalid skill frontmatter; use one-line name and description strings')
                continue
            skill_name = fields['name']
            if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', skill_name) or skill_name != PurePosixPath(name).parent.name:
                errors.append(f'{name}: invalid or mismatched skill name')
            description = fields['description']
            if not description.strip() or len(description) > 1024 or '<' in description or '>' in description:
                errors.append(f'{name}: invalid skill description')
    for name, text in decoded.items():
        if not name.endswith('.md'):
            continue
        # Inline links and images; reference definitions are checked separately.
        source = unfenced(text)
        targets = re.findall(r'!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+["\'][^\n]*?["\'])?\)', source)
        targets += re.findall(r'(?m)^\s*\[[^\]\n]+\]:\s*(<[^>]+>|\S+)', source)
        for target in targets:
            target = target.strip('<>')
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            raw_path = unquote(parsed.path)
            if raw_path.startswith('/'):
                errors.append(f'{name}: absolute local documentation link')
                continue
            parts = list(PurePosixPath(name).parent.parts)
            invalid = False
            for part in PurePosixPath(raw_path).parts:
                if part == '..':
                    if not parts:
                        invalid = True
                        break
                    parts.pop()
                elif part != '.':
                    parts.append(part)
            dest = '/'.join(parts) if raw_path else name
            exists = dest in files or any(p.startswith(dest.rstrip('/') + '/') for p in files)
            if invalid or not exists:
                errors.append(f'{name}: missing local link {target}')
            elif parsed.fragment and dest.endswith('.md') and unquote(parsed.fragment) not in anchors(decoded.get(dest, '')):
                errors.append(f'{name}: missing heading in {target}')
    return errors


def git(*args: str, root: Path) -> bytes:
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def load_git(root: Path, ref: str | None = None, worktree: bool = False) -> tuple[dict[str, bytes], dict[str, str]]:
    files: dict[str, bytes] = {}
    modes: dict[str, str] = {}
    if ref:
        entries = git('ls-tree', '-rz', '--full-tree', ref, root=root).split(b'\0')
    else:
        entries = git('ls-files', '--stage', '-z', root=root).split(b'\0')
    for entry in entries:
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        mode, middle, last = metadata.decode().split()
        name = raw_name.decode('utf-8')
        if ref:
            blob_id = last
        else:
            blob_id = middle
            if last != '0':
                raise ValueError(f'{name}: unresolved index conflict')
        modes[name] = mode
        if worktree:
            path = root / name
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f'{name}: unsafe working-tree path')
            files[name] = path.read_bytes()
        elif mode in {'100644', '100755', '120000'}:
            files[name] = git('cat-file', 'blob', blob_id, root=root)
        else:
            files[name] = b''
    return files, modes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--ref', help='inspect a committed Git tree rather than the index')
    group.add_argument('--worktree', action='store_true', help='inspect working content for index-tracked paths')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        files, modes = load_git(args.root, args.ref, args.worktree)
        errors = check_files(files, modes)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'Release check failed: {exc}', file=sys.stderr)
        return 1
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Release checks passed for {len(files)} files ({args.ref or ("working tree" if args.worktree else "index")}).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
