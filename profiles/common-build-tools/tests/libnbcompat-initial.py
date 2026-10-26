#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Source-only checks for the canonical initial Ports library."""
from pathlib import Path
import importlib.util
import json
import unittest

ROOT = Path(__file__).resolve().parents[3]


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
        self.assertEqual(changed[names[0]].replace('PKGREVISION=\t\t1\n',''),original[names[0]])
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
        self.assertEqual(changed[names[1]],expected)
        addition=('dnl EmberBSD: preserve the canonical AS_UNAME body and route only its diagnostics.\n'
          'm4_define([AS_UNAME], m4_bpatsubst(m4_defn([AS_UNAME]),\n'
          '  [(/], [(emberbsd_host_diagnostic /]))\n'
          'm4_prepend([AS_UNAME], [\n'+hook.replace('"$@"','"$[]@"')+'])\n')
        self.assertEqual(changed[names[2]],original[names[2]].replace('AC_PREREQ(2.52)\n',
                         'AC_PREREQ(2.52)\n'+addition,1))
        bad=dict(original);bad[names[1]]=bad[names[1]].replace('exec 5>>config.log','exec 5>>different.log',1)
        with self.assertRaisesRegex(ValueError,'Exact source context differs'):replay.replay(bad,patch)


if __name__ == '__main__':
    unittest.main()
