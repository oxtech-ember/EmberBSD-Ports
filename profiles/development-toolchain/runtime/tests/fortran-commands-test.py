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
import tempfile
import unittest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--gcc-source', type=Path, help='Audited unpacked GCC16 source for the real configure fragment')
parser.add_argument('--bmake', type=Path, help='BSD make for isolated target policy fragments')
parser.add_argument('--sdk-source', type=Path, help='Explicit SDK API1 source for owned make queries')
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

    def test_architecture_component_selection(self):
        self.assertEqual([x['component'] for x in self.plan('aarch64')],
                         ['libbacktrace'] * 2 + ['libgfortran'] * 3)
        self.assertEqual(len(self.plan('amd64')), 8)
        self.assertEqual(len(self.plan('aarch64')), 5)
        # No fake configure answer or feature-disable switch substitutes a library.
        for target in ('amd64', 'aarch64'):
            for row in self.plan(target):
                self.assertNotIn('--disable-libquadmath-support', row['argv'])

    @unittest.skipUnless(options.bmake and options.sdk_source, 'Set --bmake and --sdk-source for real make controls')
    def test_actual_make_sdk_alias_contract(self):
        sys.path.insert(0, str(options.sdk_source.resolve(strict=True) / 'src'))
        from emberbsd_sdk import API_VERSION
        from emberbsd_sdk.errors import CommandError
        from emberbsd_sdk.process import sanitized_environment
        from emberbsd_sdk.stream import capture_streamed
        self.assertEqual(type(API_VERSION), int)
        self.assertEqual(API_VERSION, 1)
        ports = Path(__file__).resolve().parents[4]
        contract = ports / 'pkgsrc/lang/gcc16-fortran-runtime/files/fortran_target.py'
        for values in ([], ['--target', 'riscv64'], ['--target', 'x86_64'],
                       ['--target', 'amd64', '--target', 'aarch64']):
            with self.subTest(contract_argv=values), self.assertRaises(CommandError) as error:
                capture_streamed([sys.executable, '-I', '-S', '-B', str(contract)] + values,
                    env=sanitized_environment(), timeout=10, stdout_limit=65536, stderr_limit=65536)
            self.assertEqual(error.exception.returncode, 2)
            self.assertEqual(error.exception.stdout, b'')
            self.assertFalse(error.exception.stdout_truncated or error.exception.stderr_truncated)
        text = (ports / 'profiles/common-build-tools/cross/fortran.mk').read_text()
        start = text.index('_EMBER_FORTRAN_ALIASES!=')
        query = text[start:text.index('_EMBER_FORTRAN_CHECK!=', start)]
        start = text.index('_EMBER_FORTRAN_SUPPORT=')
        fragment = text[start:text.index('CWRAPPERS_APPEND.f77+=', start)]
        with tempfile.TemporaryDirectory(prefix='.fortran-policy-', dir=ports) as directory:
            root = Path(directory)
            for target, triplet in (('amd64', 'x86_64--netbsd'), ('aarch64', 'aarch64--netbsd')):
                lib = root / target / 'usr/pkg/gcc16/lib'
                include = lib / 'gcc' / triplet / '16.2.0/include'
                include.mkdir(parents=True)
                for name in ('libgfortran.spec', 'libgfortran.so'):
                    (lib / name).write_text('fixture input')
                (include / 'ISO_Fortran_binding.h').write_text('fixture header')
                makefile = root / 'control.mk'
                makefile.write_text('EMBERBSD_FORTRAN_PYTHON=' + sys.executable + '\n'
                    + 'EMBERBSD_FORTRAN_PORTS_SOURCE=' + str(ports) + '\n'
                    + 'EMBERBSD_CROSS_TARGET=' + target + '\n_EMBER_CROSS_TRIPLET=' + triplet + '\n'
                    + 'CROSS_DESTDIR=' + str(root / target) + '\n' + query + '\n' + fragment)
                for present in (False, True):
                    quadmath = lib / 'libquadmath.so'
                    if present: quadmath.write_text('fixture input')
                    result = capture_streamed([str(options.bmake), '-r', '-f', str(makefile),
                        '-V', '${_EMBER_FORTRAN_ALIASES}', '-V', '${PKG_FAIL_REASON}'],
                        cwd=root, env=sanitized_environment(), timeout=10,
                        stdout_limit=65536, stderr_limit=65536)
                    self.assertFalse(result.stderr_truncated)
                    lines = result.value.decode().splitlines()
                    self.assertEqual(lines[0], 'libgfortran.so libquadmath.so' if target == 'amd64' else 'libgfortran.so')
                    self.assertEqual(bool(lines[1]), target == 'amd64' and not present)
                    self.assertEqual(result.stderr, b'')
                    print(json.dumps({'target':target, 'quadmath_alias_present':present,
                        'make_stdout':result.value.decode(), 'make_status':0}))
                # The core library remains mandatory on both targets.
                (lib / 'libgfortran.so').unlink()
                result = capture_streamed([str(options.bmake), '-r', '-f', str(makefile),
                    '-V', '${PKG_FAIL_REASON}'], cwd=root, env=sanitized_environment(),
                    timeout=10, stdout_limit=65536, stderr_limit=65536)
                self.assertIn(b'Install the verified', result.value)
                self.assertFalse(result.stderr_truncated)
            # Fault only the pure query transport. No compiler is substituted.
            fake_ports = root / 'query-fixture'
            helper = fake_ports / 'pkgsrc/lang/gcc16-fortran-runtime/files/fortran_target.py'
            helper.parent.mkdir(parents=True)
            for body in ("print('libgfortran.so', end=''); raise SystemExit(1)",
                         "raise SystemExit(0)"):
                helper.write_text(body + '\n')
                makefile.write_text('EMBERBSD_FORTRAN_PYTHON=' + sys.executable + '\n'
                    + 'EMBERBSD_FORTRAN_PORTS_SOURCE=' + str(fake_ports) + '\n'
                    + 'EMBERBSD_CROSS_TARGET=aarch64\n' + query)
                result = capture_streamed([str(options.bmake), '-r', '-f', str(makefile),
                    '-V', '${_EMBER_FORTRAN_ALIASES}', '-V', '${PKG_FAIL_REASON}'],
                    cwd=root, env=sanitized_environment(), timeout=10,
                    stdout_limit=65536, stderr_limit=65536)
                self.assertEqual(result.value.splitlines()[0], b'')
                self.assertIn(b'Cannot obtain the GCC16 Fortran target library contract', result.value)
                self.assertEqual(result.stderr, b'')
                self.assertFalse(result.stderr_truncated)
                print(json.dumps({'pure_query_fault':body, 'make_stdout':result.value.decode(), 'make_status':0}))

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
                    values = next(row for row in self.plan(target, compiler=compiler, sysroot=sysroot)
                                  if row['component'] == 'libgfortran')['env']
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
