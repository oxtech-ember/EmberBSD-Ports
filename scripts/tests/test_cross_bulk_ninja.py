#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the selected SDK/Ninja boundary, explicit limits and interrupted stages."""

import fcntl
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

RUNNER = Path(__file__).resolve().parents[1] / 'cross-bulk-ninja.py'
SDK = os.environ.get('EMBERBSD_SDK_SOURCE')
NINJA = shutil.which('ninja')


@unittest.skipUnless(SDK, 'select EMBERBSD_SDK_SOURCE')
class WorkerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ninja worker ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.budget = self.root / 'port.jobs'
        self.budget.write_text('2\n')
        self.log = self.root / 'call.json'
        self.fake = self.root / 'test-ninja'
        self.fake.write_text(f'#!{sys.executable}\nimport json, os, sys\n'
                             'if sys.argv[1:] == ["--version"]:\n'
                             '    print(os.environ["TEST_VERSION"])\n'
                             'else:\n'
                             '    with open(os.environ["TEST_CALL"], "w") as f:\n'
                             '        json.dump([sys.argv[1:], os.environ.get("MAKEFLAGS")], f)\n')
        self.fake.chmod(0o755)

    def argv(self, command, *, fixed=2, safe='yes', capped='no'):
        return [sys.executable, '-B', str(RUNNER), 'run', str(self.budget), str(fixed),
                safe, capped, SDK, *map(str, command)]

    def run_fake(self, *flags, version='1.13.2', inherited=None, **policy):
        env = dict(os.environ, TEST_VERSION=version, TEST_CALL=str(self.log))
        env.pop('MAKEFLAGS', None)
        if inherited is not None:
            env['MAKEFLAGS'] = inherited
        subprocess.run(self.argv([self.fake, *flags], **policy), env=env, check=True)
        return json.loads(self.log.read_text())

    def test_old_ninja_and_fixed_package_limits(self):
        self.assertEqual(self.run_fake(version='1.12.1'), [['-j', '2'], None])
        self.assertEqual(self.run_fake(safe='no'), [['-j', '1'], None])
        self.assertEqual(self.run_fake(fixed=1, capped='yes'), [['-j', '1'], None])
        self.assertEqual(self.run_fake(fixed=7, capped='yes'), [['-j', '2'], None])
        self.assertEqual(self.run_fake('-v', '-j1'), [['-v', '-j1'], None])
        self.assertEqual(self.run_fake('-j', '4', '-v'), [['-j', '2', '-v'], None])

    def test_grant_before_ninja_starts_does_not_add_slots_twice(self):
        for number in (6, 6, 3):
            subprocess.run([sys.executable, '-B', str(RUNNER), 'grant', str(self.budget), str(number)], check=True)
        self.assertEqual(self.budget.read_text(), '6\n')
        arguments, flags = self.run_fake('-v')
        self.assertEqual(arguments, ['-v'])
        self.assertIn('--jobserver-auth=fifo:', flags)
        self.assertFalse(self.budget.with_suffix('.ninja').is_symlink())

    def test_inherited_options_and_assignments_survive_the_new_budget(self):
        value = r'A=some\ -j99\ arg'
        original = f'-r -j 2 -J 15,16 {value} --jobserver-auth=fifo:stale -- B=-j6'
        args, flags = self.run_fake('-v', inherited=original, safe='')
        self.assertEqual(args, ['-v'])
        self.assertTrue(flags.startswith(f'-r {value} -j --jobserver-auth=fifo:'))
        self.assertTrue(flags.endswith(' -- B=-j6'))
        self.assertNotIn('stale', flags)
        self.assertEqual(self.run_fake('-j1', inherited=original), [['-j1'], original])

    def test_bmake_assignment_is_not_a_gnu_make_flag_word(self):
        assignment = 'DEPENDS_TARGET=emberbsd-refuse-unpreflighted-dependency'
        _, flags = self.run_fake(inherited=f'{assignment} -j2')
        self.assertTrue(flags.split()[0].startswith('-'))
        self.assertIn(assignment, flags.split())
        self.assertIn('--jobserver-auth=fifo:', flags)

        _, flags = self.run_fake(inherited=f'kn {assignment} -j2')
        self.assertEqual(flags.split()[0], 'kn')

    def test_nested_pkgsrc_invocation_runs_in_its_parent_slot(self):
        outer = self.root / 'outer'
        nested = self.argv([self.fake, '-j5'])
        outer.write_text(f'#!{sys.executable}\nimport subprocess, sys\n'
                         'if sys.argv[1:] == ["--version"]:\n    print("1.13.2")\n'
                         f'else:\n    sys.exit(subprocess.run({nested!r}, timeout=15).returncode)\n')
        outer.chmod(0o755)
        env = dict(os.environ, TEST_VERSION='1.13.2', TEST_CALL=str(self.log))
        subprocess.run(self.argv([outer]), env=env, check=True, timeout=30)
        self.assertEqual(json.loads(self.log.read_text())[0], ['-j1'])

    def test_fixed_and_adaptive_invocations_hold_the_same_slot_until_exit(self):
        self.fake.write_text(f'#!{sys.executable}\nimport pathlib, sys, time\n'
                             'if sys.argv[1:] == ["--version"]:\n    print("1.13.2")\n'
                             'else:\n    pathlib.Path("started").touch()\n'
                             '    while not pathlib.Path("release").exists(): time.sleep(0.025)\n'
                             '    sys.exit(17)\n')
        for arguments, policy in [([], {}), (['-j1'], {}), ([], {'safe': 'no'}), ([], {'capped': 'yes'})]:
            with self.subTest(arguments=arguments, policy=policy):
                with subprocess.Popen(self.argv([self.fake, *arguments], **policy), cwd=self.root) as proc:
                    try:
                        deadline = time.monotonic() + 30
                        while not (self.root / 'started').exists():
                            self.assertIsNone(proc.poll())
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(0.025)
                        with self.budget.with_suffix('.ninja-lock').open('a') as peer:
                            with self.assertRaises(BlockingIOError):
                                fcntl.flock(peer, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    finally:
                        (self.root / 'release').touch()
                    self.assertEqual(proc.wait(timeout=15), 17)
                (self.root / 'release').unlink()
                (self.root / 'started').unlink()

    @unittest.skipUnless(NINJA, 'select Ninja from the host prefix')
    def test_noop_and_interruption_release_the_fifo(self):
        script = self.root / 'command.py'
        script.write_text('import pathlib,time\np=pathlib.Path(".")\n'
                          'with open("calls", "a") as f: f.write("run\\n")\n'
                          'if (p/"hold").exists():\n'
                          '    (p/"started").touch()\n    time.sleep(60)\n(p/"result").touch()\n')
        cmd = shlex.join([sys.executable, '-B', str(script)]).replace('$', '$$')
        (self.root / 'build.ninja').write_text(f'rule run\n  command = {cmd}\nbuild result: run\n')
        for _ in range(2):
            subprocess.run(self.argv([NINJA]), cwd=self.root, check=True, capture_output=True)
        self.assertEqual((self.root / 'calls').read_text(), 'run\n')
        (self.root / 'result').unlink()
        (self.root / 'hold').touch()
        proc = subprocess.Popen(self.argv([NINJA]), cwd=self.root, start_new_session=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 30
            while not (self.root / 'started').exists():
                self.assertIsNone(proc.poll())
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.03)
            proc.send_signal(signal.SIGTERM)
            self.assertNotEqual(proc.wait(timeout=12), 0)
            self.assertFalse(self.budget.with_suffix('.ninja').is_symlink())
            (self.root / 'hold').unlink()
            subprocess.run(self.argv([NINJA]), cwd=self.root, check=True, capture_output=True)
            self.assertTrue((self.root / 'result').is_file())
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()


if __name__ == '__main__':
    unittest.main()
