#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that the documented pkgsrc checkout skips the pkgsrc history.

Ports reads only the pinned pkgsrc commit. The pin is normally not the tip of
the upstream default branch, so Git fetches it by name after the submodule
clone. Only an explicit --depth 1 limits that second fetch: the shallow
setting in .gitmodules and clone --shallow-submodules still download the
history below the pin. Every documented command therefore passes --depth 1.
"""
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SUBMODULE = 'upstream/pkgsrc'
COMMAND = re.compile(r'git submodule update\b[^\n`]*' + re.escape(SUBMODULE))


def git(*args, cwd=None):
    environment = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                       GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
    return subprocess.run(('git', '-c', 'protocol.file.allow=always', *args), cwd=cwd,
                          env=environment, check=True, capture_output=True, text=True).stdout.strip()


def documented_commands():
    commands = []
    for name in filter(None, git('ls-files', '-z', '--', '*.md', '*.py', cwd=ROOT).split('\0')):
        text = (ROOT / name).read_text(encoding='utf-8', errors='replace')
        commands.extend((name, command) for command in COMMAND.findall(text))
    return commands


class PkgsrcSubmoduleDepthTests(unittest.TestCase):
    def test_root_readme_command_fetches_the_pin_without_parents(self):
        if shutil.which('git') is None:
            self.skipTest('git is required')
        command = [row[1] for row in documented_commands() if row[0] == 'README.md']
        self.assertEqual(len(command), 1)
        work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, work)
        upstream = work / 'pkgsrc'
        git('init', '-q', str(upstream))
        for number in range(4):
            (upstream / 'file').write_text(str(number))
            git('add', 'file', cwd=upstream)
            git('commit', '-q', '-m', 'pkgsrc %d' % number, cwd=upstream)
        pin = git('rev-parse', 'HEAD~1', cwd=upstream)
        ports = work / 'ports'
        git('init', '-q', str(ports))
        git('update-index', '--add', '--cacheinfo', '160000,%s,%s' % (pin, SUBMODULE), cwd=ports)
        git('config', '-f', '.gitmodules', 'submodule.%s.path' % SUBMODULE, SUBMODULE, cwd=ports)
        git('config', '-f', '.gitmodules', 'submodule.%s.url' % SUBMODULE, upstream.as_uri(), cwd=ports)
        git('add', '.gitmodules', cwd=ports)
        git('commit', '-q', '-m', 'ports', cwd=ports)
        clone = work / 'clone'
        git('clone', '-q', ports.as_uri(), str(clone))
        arguments = shlex.split(command[0])
        self.assertEqual(arguments[0], 'git')
        git(*arguments[1:], cwd=clone)
        checkout = clone / SUBMODULE
        self.assertEqual(git('rev-parse', 'HEAD', cwd=checkout), pin)
        self.assertEqual(git('rev-list', '--count', pin, cwd=checkout), '1')

    def test_every_documented_submodule_command_fetches_one_commit(self):
        commands = documented_commands()
        self.assertTrue(commands)
        self.assertEqual([row for row in commands if '--depth 1' not in row[1]], [])


if __name__ == '__main__':
    unittest.main()
