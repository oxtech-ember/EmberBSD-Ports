#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check parallel stage metadata collection before SDK stage locking."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'cross-bulk.sh'


class StageLockCollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cross-bulk-stage-lock-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.scripts = self.root / 'scripts'
        self.scripts.mkdir()
        shutil.copy2(SOURCE, self.scripts / 'cross-bulk.sh')
        (self.scripts / 'cross-bulk.sh').chmod(0o755)
        shutil.copy2(SOURCE.with_name('native-package-current.sh'),
                     self.scripts / 'native-package-current.sh')
        self.pkgsrc = self.root / 'pkgsrc'
        for path in ('pkgtools/pkg_install', 'tools/echo', 'text/alpha', 'text/beta', 'text/gamma'):
            directory = self.pkgsrc / path
            directory.mkdir(parents=True)
            (directory / 'Makefile').write_text('# stage metadata fixture\n')
        self.state = self.root / 'state'
        self.state.mkdir()
        self.nodes = ['tools/echo@native', 'text/alpha', 'text/beta', 'text/gamma']
        (self.state / 'order').write_text(''.join(node + '\n' for node in self.nodes))
        (self.state / 'edges').write_text(''.join(f'{node} {node}\n' for node in self.nodes) +
                                           'tools/echo@native text/beta\n')
        for name in ('done', 'failed', 'blocked', 'skipped'):
            (self.state / name).write_text('')
        self.host_python = Path(sys.executable).resolve()
        self.sdk = self.root / 'sdk'
        (self.sdk / 'scripts').mkdir(parents=True)
        (self.sdk / 'scripts/resolve-jobs.py').write_text(
            'import sys\nprint(2)\n')
        self.fake_bmake = self.root / 'bmake.py'
        self.fake_bmake.write_text(textwrap.dedent(r'''\
            #!/usr/bin/env python3
            import fcntl, json, os, pathlib, sys, time
            args = sys.argv[1:]
            def value(prefix):
                if prefix == '-C': return ''
                for item in args:
                    if item.startswith(prefix): return item.split('=', 1)[1]
                return ''
            directory = value('-C')
            # -C is normally a two-word option.
            if not directory and '-C' in args: directory = args[args.index('-C') + 1]
            path = os.path.relpath(directory, os.environ['PKGSRCDIR'])
            if path.startswith('..'): path = 'pkgtools/pkg_install'
            cross_native = 'USE_CROSS_COMPILE=no' in args
            native = path.endswith('/pkg_install') or path == 'pkgtools/pkg_install'
            varname = value('VARNAME=')
            varnames = value('VARNAMES=')
            if varname == 'EMBERBSD_NATIVE_TOOLSET_VERIFIED':
                print('fixture-native-toolset'); raise SystemExit(0)
            if varnames == 'EMBERBSD_HOST_PYTHON EMBERBSD_SDK_SOURCE':
                print(os.environ['TEST_HOST_PYTHON'])
                print(os.environ['TEST_SDK'])
                raise SystemExit(0)
            if native:
                values = {
                    'NATIVE_PKG_ADD_CMD': os.environ['TEST_PKG_ADD'],
                    'PKG_INFO': os.environ['TEST_PKG_INFO'],
                    'CROSSTARGETSETTINGS': 'CROSS_TEST_SETTING=yes',
                    '_PKG_DBDIR': os.environ['TEST_TARGET_DB'],
                    '_HOST_PKG_DBDIR': os.environ['TEST_NATIVE_DB'],
                    'PACKAGES': os.environ['TEST_PACKAGES'],
                    'WRKOBJDIR': os.environ['TEST_WORK'],
                    'EMBERBSD_HOST_PYTHON': os.environ['TEST_HOST_PYTHON'],
                    'EMBERBSD_SDK_SOURCE': os.environ['TEST_SDK'],
                }
                if varname:
                    print(values.get(varname, '')); raise SystemExit(0)
                if varnames:
                    for name in varnames.split(): print(values.get(name, ''))
                    raise SystemExit(0)
            if 'show-vars' not in args and 'show-var' not in args:
                raise SystemExit(0)
            if not varnames:
                print(''); raise SystemExit(0)
            query_started = time.monotonic()
            counter = pathlib.Path(os.environ['TEST_COUNTER'])
            lock_path = pathlib.Path(str(counter) + '.lock')
            with lock_path.open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                state = json.loads(counter.read_text() or '{"running":0,"maximum":0,"finished":[]}')
                state['running'] += 1
                state['maximum'] = max(state['maximum'], state['running'])
                state['started'] = state.get('started', []) + [path]
                state['timings'] = state.get('timings', []) + [{'path': path, 'start': query_started}]
                counter.write_text(json.dumps(state))
            delay = float(os.environ.get('TEST_QUERY_DELAY', '.02'))
            if path in os.environ.get('TEST_SLOW_PATHS', '').split():
                delay = float(os.environ.get('TEST_SLOW_QUERY_DELAY', '.40'))
            if path == os.environ.get('TEST_FAIL_PATH'):
                delay = float(os.environ.get('TEST_FAIL_QUERY_DELAY', '.02'))
            time.sleep(delay)
            names = varnames.split()
            base = path.rsplit('/', 1)[-1]
            role = 'native' if cross_native else 'target'
            wrkdir = os.path.join(os.environ['TEST_WORK'], path.replace('/', '_'), role)
            values = {
                'PKGNAME': base + '-1.0',
                'WRKDIR': wrkdir,
                'PKG_SKIP_REASON': '',
                'PKGBASE': base,
                'PKGVERSION_NOREV': '1.0',
                'PKGFILE': os.path.join(os.environ['TEST_PACKAGES'], 'All', base + '-1.0.tgz'),
                'WRKOBJDIR': os.environ['TEST_WORK'],
                '.MAKE.MAKEFILES': os.path.join(directory, 'Makefile'),
                '.CURDIR': directory,
                'EMBERBSD_HOST_PYTHON': os.environ['TEST_HOST_PYTHON'],
                'EMBERBSD_SDK_SOURCE': os.environ['TEST_SDK'],
            }
            output = [values.get(name, '') for name in names]
            with lock_path.open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                state = json.loads(counter.read_text())
                if path == os.environ.get('TEST_FAIL_PATH'):
                    state['running_when_failed'] = state['running']
                state['running'] -= 1
                state['finished'] = state.get('finished', []) + [path + ':' + role + ':' +
                    ('crossfed' if 'CROSS_TEST_SETTING=yes' in args else 'plain')]
                for timing in state['timings']:
                    if timing['path'] == path and 'end' not in timing:
                        timing['end'] = time.monotonic()
                        break
                counter.write_text(json.dumps(state))
            if path == os.environ.get('TEST_FAIL_PATH'):
                raise SystemExit(1)
            print('\n'.join(output))
        '''.replace('\\\n', '')))
        self.fake_bmake.chmod(0o755)
        self.pkg_info = self.root / 'pkg_info'
        self.pkg_info.write_text('#!/bin/sh\nexit 1\n')
        self.pkg_info.chmod(0o755)
        self.pkg_add = self.root / 'pkg_add'
        self.pkg_add.write_text('#!/bin/sh\nexit 0\n')
        self.pkg_add.chmod(0o755)
        self.packages = self.root / 'packages'
        self.packages.mkdir()
        self.work = self.root / 'work'
        self.native_db = self.root / 'native-db'
        self.target_db = self.root / 'target-db'
        self.native_db.mkdir(); self.target_db.mkdir()
        self.makeconf = self.root / 'mk.conf'
        self.makeconf.write_text('# fixture\n')
        self.counter = self.root / 'queries.json'
        self.counter.write_text('{"running":0,"maximum":0,"started":[],"finished":[]}')
        self.supervisor = self.scripts / 'stage-context-supervisor.py'
        self.supervisor.write_text(textwrap.dedent('''\
            import os, pathlib, sys
            args=sys.argv[1:]
            lock=pathlib.Path(args[args.index('--locks')+1])
            pathlib.Path(os.environ['TEST_LOCKS']).write_text(lock.read_text())
            raise SystemExit(97)
        '''))

    def run_build(self, fail_path=''):
        env = dict(os.environ)
        env.update({
            'BMAKE': str(self.fake_bmake), 'MAKECONF': str(self.makeconf),
            'PKGSRCDIR': str(self.pkgsrc), 'CROSS_BULK_CPUS': '2',
            'CROSS_BULK_JOBS': '2', 'CROSS_BULK_SHARED_BUILD': 'no',
            'CROSS_BULK_VARS_CACHE': 'no', 'CROSS_BULK_TRASH': 'no',
            'TEST_HOST_PYTHON': str(self.host_python), 'TEST_SDK': str(self.sdk),
            'TEST_PKG_ADD': str(self.pkg_add), 'TEST_PKG_INFO': str(self.pkg_info),
            'TEST_TARGET_DB': str(self.target_db), 'TEST_NATIVE_DB': str(self.native_db),
            'TEST_PACKAGES': str(self.packages), 'TEST_WORK': str(self.work),
            'TEST_COUNTER': str(self.counter), 'TEST_LOCKS': str(self.root / 'locks.json'),
            'TEST_FAIL_PATH': fail_path, 'TEST_FAIL_QUERY_DELAY': '.40',
            'TEST_SLOW_PATHS': 'text/beta text/gamma', 'TEST_SLOW_QUERY_DELAY': '.40',
        })
        return subprocess.run([str(self.scripts / 'cross-bulk.sh'), 'build',
                               str(self.state / 'order'), str(self.state)], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                              timeout=60)

    def test_collects_independent_roles_in_parallel_and_preserves_lock_order(self):
        result = self.run_build()
        self.assertEqual(result.returncode, 97, result.stdout)
        counters = json.loads(self.counter.read_text())
        self.assertEqual(counters['maximum'], 2, counters)
        self.assertEqual(len(counters['finished']), len(self.nodes), counters)
        locks = json.loads((self.root / 'locks.json').read_text())
        self.assertEqual([Path(row['work']).name for row in locks],
                         ['native', 'target', 'target', 'target'])
        self.assertEqual([row['work'] for row in locks], [
            str(self.work / 'tools_echo' / 'native'), str(self.work / 'text_alpha' / 'target'),
            str(self.work / 'text_beta' / 'target'), str(self.work / 'text_gamma' / 'target')])
        finished = counters['finished']
        self.assertIn('tools/echo:native:crossfed', finished)
        self.assertIn('text/beta:target:plain', finished)
        self.assertIn('text/alpha:target:plain', finished)

    def test_query_failure_drains_workers_and_never_supervises_partial_rows(self):
        result = self.run_build(fail_path='text/alpha')
        self.assertNotEqual(result.returncode, 97, result.stdout)
        counters = json.loads(self.counter.read_text())
        self.assertEqual(counters['running'], 0, counters)
        self.assertGreaterEqual(len(counters['started']), 2, counters)
        self.assertGreater(counters.get('running_when_failed', 0), 1, counters)
        self.assertEqual(len(counters['finished']), len(counters['started']), counters)
        self.assertFalse((self.root / 'locks.json').exists(), result.stdout)
        self.assertFalse((self.state / 'build.lock').exists(), result.stdout)

    def test_balances_expensive_tail_queries_and_preserves_lock_order(self):
        result = self.run_build()
        self.assertEqual(result.returncode, 97, result.stdout)
        counters = json.loads(self.counter.read_text())
        slow = [row for row in counters['timings'] if row['path'] in ('text/beta', 'text/gamma')]
        self.assertEqual(len(slow), 2, counters)
        self.assertLess(max(row['start'] for row in slow), min(row['end'] for row in slow), counters)
        locks = json.loads((self.root / 'locks.json').read_text())
        self.assertEqual([Path(row['work']).name for row in locks],
                         ['native', 'target', 'target', 'target'])


if __name__ == '__main__':
    unittest.main()
