"""Synthetic release-boundary regressions; no actual credentials or company data."""
import importlib.util
from pathlib import Path
import unittest
import subprocess
import tempfile

spec = importlib.util.spec_from_file_location('check_repo', Path(__file__).resolve().parents[1] / 'scripts/check_repo.py')
check_repo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_repo)


class ReleaseChecks(unittest.TestCase):
    def test_private_files_cannot_be_released_despite_ignore_rules(self):
        for path in ('people/a.md', 'knowledge/source.txt', 'transcripts/.ingestion-state.json',
                     'sources.local.md', 'Self.md', 'People/a.md', '.codex/config.toml', 'projects/client.md', '.env.local', 'key.pem'):
            with self.subTest(path=path):
                self.assertTrue(check_repo.check_files({path: b'private'}))
        self.assertEqual(check_repo.check_files({'projects/.gitkeep': b'', 'templates/self.md': b'# Template\n'}), [])
        self.assertTrue(check_repo.check_files({'projects/.gitkeep': b'private context'}))

    def test_sensitive_matches_report_rule_and_path_without_value(self):
        token = 'ghp_' + 'A' * 36
        errors = check_repo.check_files({'README.md': token.encode()})
        self.assertTrue(any('GitHub token' in error for error in errors))
        self.assertNotIn(token, '\n'.join(errors))
        assignment = '{"api_key": "' + 'aB7z' * 8 + '"}'
        errors = check_repo.check_files({'config.json': assignment.encode()})
        self.assertTrue(any('credential assignment' in error for error in errors))

    def test_symlinks_are_rejected(self):
        errors = check_repo.check_files({'README.md': b'outside'}, {'README.md': '120000'})
        self.assertTrue(errors)

    def test_frontmatter_and_relative_navigation(self):
        files = {
            'README.md': b'# Start\n\n[Guide](docs/guide.md#first-step)\n',
            'docs/guide.md': b'# Guide\n\n## First step\n\n[Home](../README.md)\n',
            '.agents/skills/morning/SKILL.md': b'---\nname: morning\ndescription: Prepare a useful briefing.\n---\n# Morning\n',
        }
        self.assertEqual(check_repo.check_files(files), [])
        files['docs/guide.md'] = b'# Guide\n[Missing](../missing.md)\n'
        self.assertEqual(len(check_repo.check_files(files)), 2)
        files['.agents/skills/morning/SKILL.md'] = b'# No frontmatter\n'
        self.assertTrue(any('frontmatter' in item for item in check_repo.check_files(files)))

    def test_index_scan_catches_staged_secret_hidden_by_clean_working_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', directory], check=True)
            secret = 'ghp_' + 'Z' * 36
            (root / 'README.md').write_text(secret)
            subprocess.run(['git', '-C', directory, 'add', 'README.md'], check=True)
            (root / 'README.md').write_text('# Clean working copy\n')
            files, modes = check_repo.load_git(root)
            self.assertTrue(check_repo.check_files(files, modes))
            files, modes = check_repo.load_git(root, worktree=True)
            self.assertEqual(check_repo.check_files(files, modes), [])

    def test_malformed_yaml_cannot_pass_frontmatter_validation(self):
        for description in ('true', 'nested: value', 'nested:\tvalue', '# comment only', '- sequence', '? mapping', '"unterminated', '|', 'null'):
            content = f'---\nname: morning\ndescription: {description}\n---\n# Morning\n'
            with self.subTest(description=description):
                self.assertTrue(check_repo.check_files({'.agents/skills/morning/SKILL.md': content.encode()}))
        content = b'---\nname: wrong\nname: morning\ndescription: Brief the day.\n---\n'
        self.assertTrue(check_repo.check_files({'.agents/skills/morning/SKILL.md': content}))

    def test_examples_do_not_create_navigation_requirements(self):
        content = '# Example\n\n```markdown\n[Placeholder](missing.md)\n```\n'
        self.assertEqual(check_repo.check_files({'README.md': content.encode()}), [])


if __name__ == '__main__':
    unittest.main()
