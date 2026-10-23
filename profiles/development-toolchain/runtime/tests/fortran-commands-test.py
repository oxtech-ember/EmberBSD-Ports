# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; source-only command-contract controls, no compiler execution.
from pathlib import Path
import importlib.util
import shlex
import unittest

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

    def test_invalid_plan_refuses(self):
        for changes in ({'target': 'riscv64'}, {'jobs': 0}, {'jobs': -1}, {'jobs': '12'}, {'jobs': True},
                        {'source': 'relative'}, {'work': '/new/../old'},
                        {'build_triplet': 'x86_64--netbsd'}, {'build_triplet': 'bad;execute'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.plan(**changes)


if __name__ == '__main__':
    unittest.main(verbosity=2)
