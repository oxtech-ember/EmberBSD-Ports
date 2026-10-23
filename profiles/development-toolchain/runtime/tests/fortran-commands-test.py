# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; source-only command-contract controls, no compiler execution.
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shlex
import subprocess
import sys
import unittest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--gcc-source', type=Path, help='Audited unpacked GCC16 source for the real configure fragment')
options, remaining = parser.parse_known_args()

path = Path(__file__).resolve().parents[4] / 'profiles/development-toolchain/bootstrap/fortran_commands.py'
spec = importlib.util.spec_from_file_location('fortran_commands', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Commands(unittest.TestCase):
    def plan(self, target='amd64', **changes):
        values = dict(target=target, build_triplet='aarch64-apple-darwin27.0.0',
                      source='/new/source', work='/new/runtime', compiler='/new/compiler',
                      sysroot='/accepted/sysroot', make='/native/gmake', jobs=12,
                      native_cc='/native/gcc-16')
        values.update(changes)
        return module.component_plan(**values)

    def test_real_components_and_order(self):
        p = self.plan()
        self.assertEqual([(x['component'], x['phase']) for x in p],
                         [('libbacktrace', 'configure'), ('libbacktrace', 'build'),
                          ('libquadmath', 'configure'), ('libquadmath', 'build'), ('libquadmath', 'install'),
                          ('libgfortran', 'configure'), ('libgfortran', 'build'), ('libgfortran', 'install')])
        self.assertIn('--enable-host-shared', p[0]['argv'])
        self.assertNotIn('--with-toolexeclibdir=/usr/pkg/gcc16/lib', p[0]['argv'])

    def test_target_and_provider_transport(self):
        for target, (triplet, flags) in module.TARGETS.items():
            with self.subTest(target=target):
                for row in self.plan(target):
                    self.assertEqual(row['env']['FC'], row['env']['F77'])
                    self.assertEqual(row['env']['GFORTRAN'], row['env']['FC'])
                    self.assertEqual(shlex.split(row['env']['CC'])[0], '/new/compiler/bin/' + triplet + '-gcc')
                    self.assertEqual(shlex.split(row['env']['FC'])[0], '/new/compiler/bin/' + triplet + '-gfortran')
                    self.assertIn('--sysroot=/accepted/sysroot', shlex.split(row['env']['FC']))
                    self.assertIn('-B/accepted/sysroot/usr/pkg/gcc16/lib/gcc/' + triplet + '/16.2.0/', shlex.split(row['env']['FC']))
                    self.assertEqual(row['env']['FCFLAGS'], flags + ' -fPIC')
                    if row['phase'] == 'configure':
                        self.assertIn('--host=' + triplet, row['argv'])
                        self.assertIn('--target=' + triplet, row['argv'])
                        self.assertIn('--build=aarch64-apple-darwin27.0.0', row['argv'])
                    if row['phase'] == 'build':
                        self.assertEqual(row['argv'], ['/native/gmake', '-j12', 'V=1', 'all'])
                    if row['phase'] == 'install':
                        self.assertEqual(row['argv'], ['/native/gmake', 'DESTDIR=/new/runtime/stage', 'V=1', 'install'])

    def test_no_fake_answers_or_compiler_runtime_recursion(self):
        for row in self.plan():
            self.assertFalse(any('_cv_' in k or k.startswith('ac_cv') for k in row['env']))
            self.assertFalse(set(row['argv']) & {'all-gcc', 'install-gcc', 'all-target-libgcc', 'all-target-libstdc++-v3'})
            self.assertNotIn('--disable-libquadmath-support', row['argv'])
            self.assertEqual(row['env']['CONFIG_SITE'], '/dev/null')

    def test_quoting_and_target_native_separation(self):
        row = self.plan(compiler='/new compiler', sysroot='/accepted sysroot', native_cc='/native compiler/gcc-16')[0]
        self.assertEqual(shlex.split(row['env']['FC'])[0], '/new compiler/bin/x86_64--netbsd-gfortran')
        self.assertIn('--sysroot=/accepted sysroot', shlex.split(row['env']['FC']))
        self.assertEqual(shlex.split(row['env']['CC_FOR_BUILD']), ['/native compiler/gcc-16'])

    @unittest.skipUnless(options.gcc_source, 'Set --gcc-source for the real upstream fragment')
    def test_actual_upstream_fc_assignment(self):
        # Run only the exact upstream assignment. No compiler or configure runs.
        root = options.gcc_source.resolve(strict=True)
        for name in ('configure.ac', 'configure'):
            source = root / 'libgfortran' / name
            content = source.read_bytes()
            matches = [line for line in content.splitlines() if line == b'FC="$GFORTRAN"']
            self.assertEqual(len(matches), 1)
            fragment = matches[0]
            print('upstream-fragment ' + str(source) + ' sha256=' + hashlib.sha256(content).hexdigest())
            for target in module.TARGETS:
                for compiler, sysroot in (('/new/compiler', '/accepted/sysroot'),
                                          ('/new compiler', '/accepted sysroot')):
                    values = self.plan(target, compiler=compiler, sysroot=sysroot)[5]['env']
                    script = fragment.decode() + '\nprintf "%s\n" "$FC"\n'
                    base = {'PATH': '/usr/bin:/bin', 'FC': values['FC'], 'F77': values['F77']}
                    before = subprocess.run(['/bin/sh', '-c', script], env=base,
                                            capture_output=True, check=True, timeout=5)
                    after = subprocess.run(['/bin/sh', '-c', script],
                                           env=dict(base, GFORTRAN=values['GFORTRAN']),
                                           capture_output=True, check=True, timeout=5)
                    self.assertEqual((before.stdout, before.stderr), (b'\n', b''))
                    self.assertEqual((after.stdout, after.stderr), (values['FC'].encode() + b'\n', b''))
                    triplet = module.TARGETS[target][0]
                    expected = [compiler + '/bin/' + triplet + '-gfortran', '--sysroot=' + sysroot,
                                '-B' + sysroot + '/usr/pkg/gcc16/lib/gcc/' + triplet + '/16.2.0/',
                                '-B' + sysroot + '/usr/pkg/gcc16/lib/']
                    self.assertEqual(shlex.split(after.stdout.decode()), expected)
                    print(json.dumps({"source": str(source), "target": target,
                        "before_status": before.returncode, "before_stdout": before.stdout.decode(),
                        "after_status": after.returncode, "after_stdout": after.stdout.decode(),
                        "expected_argv": expected, "stderr_empty": not (before.stderr or after.stderr)}))

    def test_invalid_plan_refuses(self):
        for changes in ({'target': 'riscv64'}, {'jobs': 0}, {'jobs': -1}, {'jobs': '12'}, {'jobs': True},
                        {'source': 'relative'}, {'work': '/new/../old'},
                        {'build_triplet': 'x86_64--netbsd'}, {'build_triplet': 'bad;execute'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.plan(**changes)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + remaining, verbosity=2)
