#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Canonical source checks and optional native bootstrap printf probes."""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
OPTIONS = argparse.Namespace(cc=None, cflag=[], work_root=None, analyze=False, cppcheck=None)


class InitialLibraryTests(unittest.TestCase):
    def test_common_manifest_exists(self):
        self.assertTrue((ROOT/'profiles/common-build-tools/bootstrap/libnbcompat.json').is_file())

    def test_single_diagnostic_implementation_exists(self):
        self.assertTrue((ROOT/'profiles/common-build-tools/files/emberbsd-configure-diagnostics.sh').is_file())

    def test_configure_printf_has_an_explicit_native_role(self):
        manifest=json.loads((ROOT/'profiles/common-build-tools/bootstrap/libnbcompat.json').read_text())
        configure=(ROOT/'upstream/pkgsrc/pkgtools/libnbcompat/files/configure').read_text()
        shell_recipe=(ROOT/'pkgsrc/shells/mksh/Makefile').read_text()
        self.assertIn('printf "%s\\n"',configure)
        self.assertIn('printf comes from the base utilities',shell_recipe)
        self.assertIn('printf',manifest['required_tool_roles'])

    def test_complete_common_options_and_exports(self):
        manifest=json.loads((ROOT/'profiles/common-build-tools/bootstrap/libnbcompat.json').read_text())
        recipe=(ROOT/'upstream/pkgsrc/pkgtools/libnbcompat/Makefile').read_text()
        bootstrap=' '.join((ROOT/'upstream/pkgsrc/bootstrap/bootstrap').read_text().replace('\\\n','').split())
        self.assertIn(' '.join(manifest['configure_args']),recipe)
        for option in manifest['configure_args']:
            self.assertIn(option,bootstrap)
        plist=(ROOT/'upstream/pkgsrc/pkgtools/libnbcompat/PLIST').read_text().splitlines()
        self.assertEqual(manifest['exports'],[line for line in plist if not line.startswith('@')])
        self.assertEqual(len(manifest['exports']),41)
        self.assertTrue({'cp','mv','ls','diff'} <= set(manifest['required_tool_roles']))
        self.assertEqual(manifest['make_targets'],['all'])
        self.assertEqual(manifest['stage_target'],'install')

    def test_generated_gcc_helper_has_exact_common_bytes(self):
        path=ROOT/'profiles/common-build-tools/generate-configure-diagnostics.py'
        spec=importlib.util.spec_from_file_location('diagnostic_generator',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        text=module.PATCH.read_text(); source=module.SOURCE.read_text()
        self.assertEqual(module.generated(text,source),text)
        self.assertNotEqual(module.generated(text,source+'# changed\n'),text)
        self.assertIn('SPDX-License-Identifier: GPL-3.0-or-later',source)
        self.assertIn('conflicting SDK mode selectors',source)
        self.assertIn('conflicting SDK uname selectors',source)
        self.assertIn('system uname is not a selected SDK input',source)
        self.assertIn("echo 'unavailable (selected SDK profile)'\n  return 1",source)
        recipe=(ROOT/'profiles/development-toolchain/patches/gcc-darwin-host.patch').read_text()
        for revision in (13,14,4):self.assertIn('+PKGREVISION=\t'+str(revision)+'\n',recipe)

    def test_export_binds_one_common_helper_and_infrastructure_patch(self):
        text=(ROOT/'pkgsrc/export.conf').read_text()
        self.assertEqual(text.count('file\tprofiles/common-build-tools/files/emberbsd-configure-diagnostics.sh\tpkgtools/libnbcompat/files/emberbsd-configure-diagnostics.sh\n'),1)
        self.assertEqual(text.count('patch\tprofiles/common-build-tools/patches/pkgsrc-libnbcompat-sdk-diagnostics.patch\n'),1)

    def test_exact_source_patch_keeps_recipe_and_configure_feature_tests(self):
        spec=importlib.util.spec_from_file_location('source_replay',Path(__file__).with_name('bsdinstall-source.py'))
        replay=importlib.util.module_from_spec(spec);spec.loader.exec_module(replay)
        names=['pkgtools/libnbcompat/Makefile','pkgtools/libnbcompat/files/configure',
               'pkgtools/libnbcompat/files/configure.ac']
        original={name:(ROOT/'upstream/pkgsrc'/name).read_text() for name in names}
        patch=(ROOT/'profiles/common-build-tools/patches/pkgsrc-libnbcompat-sdk-diagnostics.patch').read_text()
        changed=replay.replay(original,patch)
        self.assertEqual(changed[names[0]].replace('PKGREVISION=\t\t2\n',''),original[names[0]])
        hook=('# EmberBSD: use the common selected diagnostic helper in explicit SDK mode.\n'
              'if test "${EMBERBSD_CONFIGURE_SDK+set}" = set; then\n'
              '  . "${srcdir}/emberbsd-configure-diagnostics.sh" || exit 1\n'
              'else\n  emberbsd_host_diagnostic () { "$@"; }\nfi\n')
        before=original[names[1]]
        start=before.index('cat <<_ASUNAME\n');end=before.index('\n_ASUNAME\n',start)
        block=before[start:end]
        self.assertEqual(block.count('`(/'),9)
        expected=before[:start]+block.replace('`(/','`(emberbsd_host_diagnostic /')+before[end:]
        expected=expected.replace('exec 5>>config.log\n','exec 5>>config.log\n'+hook,1)
        for program in printf_programs(expected).values():
            indent = re.search(r'\n([ \t]*)int main', program)[1]
            fixed = program.replace('#include <stdio.h>\n', '#include <stdio.h>\n' + indent + '#include <string.h>\n', 1)
            expected = expected.replace(program, fixed)
        self.assertEqual(changed[names[1]], expected)
        addition=('dnl EmberBSD: preserve the canonical AS_UNAME body and route only its diagnostics.\n'
          'm4_define([AS_UNAME], m4_bpatsubst(m4_defn([AS_UNAME]),\n'
          '  [(/], [(emberbsd_host_diagnostic /]))\n'
          'm4_prepend([AS_UNAME], [\n'+hook.replace('"$@"','"$[]@"')+'])\n')
        expected_ac = original[names[2]].replace('AC_PREREQ(2.52)\n', 'AC_PREREQ(2.52)\n' + addition, 1)
        for program in printf_programs(expected_ac).values():
            indent = re.search(r'\n([ \t]*)int main', program)[1]
            fixed = program.replace('#include <stdio.h>\n', '#include <stdio.h>\n' + indent + '#include <string.h>\n', 1)
            expected_ac = expected_ac.replace(program, fixed)
        self.assertEqual(changed[names[2]], expected_ac)
        bad=dict(original);bad[names[1]]=bad[names[1]].replace('exec 5>>config.log','exec 5>>different.log',1)
        with self.assertRaisesRegex(ValueError,'Exact source context differs'):replay.replay(bad,patch)


def printf_programs(text):
    """Extract the actual two feature probes, not separately maintained examples."""
    result = {}
    for match in re.finditer(r'sprintf\(buf, "(%(?:lld|qd))", 4294967300LL\);', text):
        start = text.rfind('#include <stdio.h>', 0, match.start())
        end = text.index('}', match.end()) + 1
        if start == -1 or match[1] in result:
            raise ValueError('missing or duplicate printf feature probe')
        result[match[1]] = text[start:end] + '\n'
    if set(result) != {'%lld', '%qd'}:
        raise ValueError('both long-long printf probes are required')
    return result


def patched_sources():
    path = Path(__file__).with_name('bsdinstall-source.py')
    spec = importlib.util.spec_from_file_location('source_replay', path)
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    names = ['pkgtools/libnbcompat/Makefile', 'pkgtools/libnbcompat/files/configure',
             'pkgtools/libnbcompat/files/configure.ac']
    original = {name: (ROOT / 'upstream/pkgsrc' / name).read_text() for name in names}
    patch = (ROOT / 'profiles/common-build-tools/patches/pkgsrc-libnbcompat-sdk-diagnostics.patch').read_text()
    return original, replay.replay(original, patch)


class PrintfProbeTests(unittest.TestCase):
    def test_autoconf_and_generated_programs_match(self):
        original, changed = patched_sources()
        generated = printf_programs(changed['pkgtools/libnbcompat/files/configure'])
        canonical = printf_programs(changed['pkgtools/libnbcompat/files/configure.ac'])
        baseline = printf_programs(original['pkgtools/libnbcompat/files/configure'])
        for format in generated:
            self.assertEqual(' '.join(generated[format].split()), ' '.join(canonical[format].split()))
            self.assertIn('#include <string.h>', generated[format])
            self.assertNotIn('#include <string.h>', baseline[format])
            # Declaring strcmp is the only feature-test change: preserve the
            # buffer, tested value, formatting function and comparison result.
            self.assertEqual(' '.join(generated[format].replace('#include <string.h>\n', '').split()),
                             ' '.join(baseline[format].split()))

    def test_actual_native_printf_probes(self):
        if OPTIONS.cc is None:
            self.skipTest('select the native bootstrap compiler with --cc to compile and run the actual probes')
        compiler = Path(OPTIONS.cc)
        self.assertTrue(compiler.is_absolute() and compiler.is_file())
        original, changed = patched_sources()
        before = printf_programs(original['pkgtools/libnbcompat/files/configure'])
        after = printf_programs(changed['pkgtools/libnbcompat/files/configure'])
        with tempfile.TemporaryDirectory(prefix='libnbcompat-probes-', dir=OPTIONS.work_root) as directory:
            work = Path(directory)
            for format in after:
                with self.subTest(format=format):
                    name = format[1:]
                    bad = work / (name + '-before.c')
                    good = work / (name + '-after.c')
                    bad.write_text(before[format]); good.write_text(after[format])
                    flags = [str(compiler), *OPTIONS.cflag, '-std=c11', '-Werror=implicit-function-declaration']
                    failed = subprocess.run([*flags, str(bad), '-o', str(work / (name + '-bad'))],
                                            text=True, capture_output=True)
                    self.assertNotEqual(failed.returncode, 0, 'unfixed probe must expose the original declaration failure')
                    self.assertRegex(failed.stderr, r'(undeclared|implicit).*strcmp|strcmp.*(undeclared|implicit)')
                    built = subprocess.run([*flags, str(good), '-o', str(work / name)], text=True, capture_output=True)
                    self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                    ran = subprocess.run([str(work / name)], text=True, capture_output=True)
                    self.assertEqual(ran.returncode, 0, 'native libc does not support ' + format)
                    if OPTIONS.analyze:
                        analysis_flags = [flag for flag in flags if not flag.startswith('--ld-path=')]
                        analyzed = subprocess.run([*analysis_flags, '--analyze', '-Xanalyzer', '-analyzer-output=text',
                            str(good), '-o', str(work / (name + '.plist'))], text=True, capture_output=True)
                        self.assertEqual(analyzed.returncode, 0, analyzed.stdout + analyzed.stderr)
                        self.assertNotIn('warning:', analyzed.stderr)
                    if OPTIONS.cppcheck:
                        self.assertTrue(Path(OPTIONS.cppcheck).is_absolute() and Path(OPTIONS.cppcheck).is_file())
                        checked = subprocess.run([OPTIONS.cppcheck, '--std=c11', '--platform=unix64',
                            '--enable=warning,style,performance,portability', '--error-exitcode=1', '--library=std',
                            str(good)], text=True, capture_output=True)
                        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', help='absolute native compiler selected as an initial bootstrap input')
    parser.add_argument('--cflag', action='append', default=[], help='explicit bootstrap compiler or ABI flag')
    parser.add_argument('--work-root', help='existing local directory for temporary native probes')
    parser.add_argument('--analyze', action='store_true', help='also run the selected Clang static analyzer')
    parser.add_argument('--cppcheck', help='explicit diagnostic Cppcheck executable')
    OPTIONS, remaining = parser.parse_known_args()
    if (OPTIONS.analyze or OPTIONS.cppcheck) and not OPTIONS.cc:
        parser.error('--analyze/--cppcheck require --cc')
    unittest.main(argv=[sys.argv[0], *remaining])
