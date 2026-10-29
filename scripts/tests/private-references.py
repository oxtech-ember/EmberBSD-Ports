#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Published recipes, profiles and scripts name no build host or board.

Concrete checkout paths, user home directories, development host names,
board/VM host names and per-run probe directories belong in private MAKECONF
or notes, never in Git. Generic placeholders (/absolute/..., target.example)
are fine. probes/ is not covered yet.
Usage: PY scripts/tests/private-references.py [-v]
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ('README.md', 'docs', 'licenses', 'pkgsrc', 'profiles', 'scripts')
PATTERNS = {
    'macOS volume checkout path': r'(?<![\w/])/Volumes/[A-Z][A-Za-z0-9]+/',
    'user home directory': r'(?<![\w/.~-])/Users/[a-z][a-z0-9._-]*/',
    'board or VM host name': r'\bember-[a-z0-9]+-[0-9]{2}\b',
    'development host name': r'\bneonix',
    'per-run Perl probe directory': r'/tmp/ember-perl\.[A-Za-z0-9]{8}\b',
}
COMPILED = [(name, re.compile(rx)) for name, rx in PATTERNS.items()]


def scan(root, paths):
    found = []
    for relative in paths:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        if b'\0' in data[:8192]:
            continue
        for number, line in enumerate(data.decode('utf-8', 'replace').splitlines(), 1):
            for name, rx in COMPILED:
                if rx.search(line):
                    found.append(f'{relative}:{number}: {name}: {line.strip()[:160]}')
    return found


def tracked(root):
    out = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--', *SCOPE],
                         capture_output=True, check=True).stdout
    return [p for p in out.decode().split('\0') if p]


class PrivateReferences(unittest.TestCase):
    def test_tracked_files_are_clean(self):
        found = scan(ROOT, tracked(ROOT))
        self.assertEqual(found, [], '\n' + '\n'.join(found))

    def test_planted_references_are_found(self):
        planted = {
            'a.mk': 'X=/Vol' 'umes/BigData/EmberBSD/build\n',
            'b.md': 'see /Us' 'ers/alice/src\n',
            'c.sh': 'ssh root@ember-' 'zero3w-01.local\n',
            'd.txt': 'built on neo' 'nix2024\n',
            'e.conf': 'DIR=/tmp/ember-' 'perl.AbCd1234\n',
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in planted.items():
                (root / name).write_text(text)
            found = scan(root, list(planted))
        self.assertEqual(sorted(line.split(':')[0] for line in found), sorted(planted))

    def test_generic_placeholders_are_accepted(self):
        text = ('/absolute/host/bin/perl\n/System/Volumes/Preboot/x\nView/Users/json/add.ctp\n'
                's|/Volumes/[^ ]*|BUILDDIR|\nbuilder@ember-target.local\n/usr/local/lib\n')
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'ok').write_text(text)
            self.assertEqual(scan(Path(directory), ['ok']), [])


if __name__ == '__main__':
    unittest.main()
