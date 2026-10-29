#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted controls for the canonical initial pkgtools.
"""Check source policy and fixed cases. Do not execute configure or native tools."""

import argparse
import copy
import json
from pathlib import Path
import re
import shlex
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT
MANIFEST = ROOT / 'profiles/common-build-tools/bootstrap/pkg-install.json'
POLICY = ROOT / 'profiles/development-toolchain/darwin-bootstrap.mk.conf'
PATCH_RELATIVE = 'profiles/common-build-tools/patches/pkgsrc-pkg-install-dyld-cache.patch'
PATCH = ROOT / PATCH_RELATIVE
NATIVE_STAGE_PATCH_RELATIVE = 'profiles/common-build-tools/patches/pkgsrc-pkg-install-native-stage.patch'


def original(relative):
    return (SOURCE / 'upstream/pkgsrc' / relative).read_text()


def canonical_libarchive_args(bootstrap):
    begin = bootstrap.index('copy_src $pkgsrcdir/archivers/libarchive/files libarchive\n')
    end = bootstrap.index('MAKE=$bmake &&', begin)
    text = bootstrap[begin:end].split('$shprog ./configure $configure_quiet_flags ', 1)[1]
    words = shlex.split(text.replace('\\\n', ' '))
    if not words or any(not word.startswith('--') for word in words):
        raise ValueError('Unexpected canonical libarchive options')
    return words


def check_manifest(value, bootstrap):
    if value['format'] != 'emberbsd-native-bootstrap-program' or value['version'] != 1 or \
            value['name'] != 'pkg-install' or value['initial_only'] is not True or \
            value['build_system'] != 'pkgsrc-bootstrap':
        raise ValueError('Not the initial pkg_install contract')
    if value['compiler'] != dict(family='gcc', major=16, abi='native'):
        raise ValueError('Initial compiler contract differs')
    expected = [('libarchive', 'archivers/libarchive', canonical_libarchive_args(bootstrap)),
                ('pkg_install', 'pkgtools/pkg_install', ['--enable-bootstrap'])]
    components = [dict(name=name, canonical_host_recipe=recipe + '/Makefile',
        source_directory=recipe + '/files', configure_args=args, make_targets=['all'])
        for name, recipe, args in expected]
    if value['components'] != components:
        raise ValueError('Supported canonical bootstrap components differ')
    if value['bootstrap_script'] != 'bootstrap/bootstrap' or \
            value['infrastructure_patches'] != [PATCH_RELATIVE, NATIVE_STAGE_PATCH_RELATIVE] or \
            value['compat'] != dict(recipe='pkgtools/libnbcompat', include_dir='include',
                                    static_library='lib/libnbcompat.a'):
        raise ValueError('Canonical source and library provenance differ')
    outputs = {'pkg_' + name: 'pkg_install/' + name + '/pkg_' + name
               for name in ('add', 'admin', 'create', 'info')}
    if value['output_programs'] != outputs or value['invocations'] != list(outputs):
        raise ValueError('Initial output roster differs')
    roles = value['required_tool_roles']
    if len(set(roles)) != len(roles) or any(role.startswith('pkg_') for role in roles) or \
            set(roles) & {'gzip', 'bzip2', 'xz', 'gmake'} or \
            not {'cc', 'cxx', 'cpp', 'sh', 'make', 'install', 'ar', 'ranlib', 'find'} <= set(roles):
        raise ValueError('Initial tools require selected BSD make and no old pkgtools or compressors')
    for case in value['runtime_cases']:
        if case['invocation'] == 'pkg_add' and \
                set(case['args']) & {'-f', '-D', '-m', '-n', '-I'}:
            raise ValueError('A package-add check bypass is not a semantic case')
        if case['invocation'] == 'pkg_create' and \
                case['args'][:2] != ['-F', 'none'] and case['args'] != ['-V']:
            raise ValueError('Package creation must select no compression explicitly')


def compression(profile, selected):
    """Check this one fixed source assignment's guards, not a general make parser."""
    stack, assignments = [], []
    for line in profile.splitlines():
        if re.match(r'^\.\s*if\b', line):
            stack.append(line)
        elif re.match(r'^\.\s*endif\b', line):
            stack.pop()
        elif re.match(r'^PKG_COMPRESSION\s*[?+:]?=', line):
            assignments.append((line, list(stack)))
    if assignments != [('PKG_COMPRESSION= none',
                         ['.if !defined(_EMBERBSD_DARWIN_BOOTSTRAP_POLICY)'])]:
        raise ValueError('Compression policy is absent or outside the one-time initial guard')
    refusal = '.if ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} != "yes"\n.error '
    if refusal not in profile or profile.index(refusal) > profile.index(assignments[0][0]):
        raise ValueError('The initial selector must be checked before compression policy')
    default = re.search(r'^PKG_COMPRESSION\?=\s*(\S+)', original('mk/defaults/mk.conf'), re.M)
    if default is None:
        raise ValueError('Canonical ordinary compression default is missing')
    return 'none' if selected else default[1]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.value = json.loads(MANIFEST.read_text())
        self.bootstrap = original('bootstrap/bootstrap')

    def test_manifest_matches_the_canonical_bootstrap_sequence(self):
        check_manifest(self.value, self.bootstrap)
        self.assertIn('--enable-bootstrap --prefix=$prefix', self.bootstrap)
        self.assertIn('STATIC_LIBARCHIVE=$wrkdir/libarchive/.libs/libarchive.a', self.bootstrap)
        self.assertIn("STATIC_LIBARCHIVE_LDADD='`extra_libarchive_depends`'", self.bootstrap)
        self.assertIn('PKG_COMPRESSION=none', self.bootstrap)

    def test_missing_minimal_mode_and_enabled_backend_refuse(self):
        for component, change in ((1, []), (0, ['--enable-static', '--disable-shared'])):
            value = copy.deepcopy(self.value)
            value['components'][component]['configure_args'] = change
            with self.assertRaisesRegex(ValueError, 'Supported canonical bootstrap components'):
                check_manifest(value, self.bootstrap)

    def test_bootstrap_excludes_delete_and_signature_objects_only(self):
        top = original('pkgtools/pkg_install/files/Makefile.in')
        self.assertIn('.if empty(BOOTSTRAP)\nSUBDIRS=\tlib add admin create delete info\n'
                      '.else\nSUBDIRS=\tlib add admin create info\n.endif', top)
        library = original('pkgtools/pkg_install/files/lib/Makefile.in')
        self.assertIn('.if !empty(BOOTSTRAP)\nCPPFLAGS+=\t-DBOOTSTRAP\n.else\n'
                      'OBJS+=\tgpgsig.o pkg_signature.o\n.endif', library)
        self.assertIn('#ifndef BOOTSTRAP\n#include <fetch.h>\n#endif',
                      original('pkgtools/pkg_install/files/lib/parse-config.c'))
        add = original('pkgtools/pkg_install/files/add/Makefile.in')
        self.assertIn('-linstall -lnetpgpverify -larchive -lbz2 -lz -lfetch', add)
        self.assertIn('-linstall ${STATIC_LIBARCHIVE} ${STATIC_LIBARCHIVE_LDADD} @LIBS@', add)

    def test_scoped_compression_and_ordinary_default(self):
        profile = POLICY.read_text()
        self.assertEqual(compression(profile, True), 'none')
        self.assertEqual(compression(profile, False), 'gzip')
        # Removing the owner assignment reproduces the old unsupported gzip path.
        with self.assertRaisesRegex(ValueError, 'Compression policy'):
            compression(profile.replace('PKG_COMPRESSION= none\n', ''), True)
        with self.assertRaisesRegex(ValueError, 'Compression policy'):
            compression(profile + '\nPKG_COMPRESSION= none\n', False)
        package = original('mk/pkgformat/pkg/package.mk')
        self.assertRegex(package, r'_PKG_ARGS_PACKAGE\+=\s*-F \$\{PKG_COMPRESSION\}')
        self.assertNotIn('PKG_SUFX=', profile)

    def test_create_selects_none_before_filename_heuristics(self):
        source = original('pkgtools/pkg_install/files/create/build.c')
        self.assertIn('if (CompressionType == NULL)', source)
        self.assertIn('else if (strcmp(CompressionType, "none") != 0)', source)
        creates = [row for row in self.value['runtime_cases'] if row['name'].startswith('create-')]
        self.assertEqual(len(creates), 3)
        self.assertTrue(all(row['args'][:2] == ['-F', 'none'] for row in creates))
        self.assertTrue(all(row['args'][-1].endswith('.tgz') for row in creates))
        value = copy.deepcopy(self.value)
        next(row for row in value['runtime_cases'] if row['name'] == 'create-cache')['args'][1] = 'gzip'
        with self.assertRaisesRegex(ValueError, 'no compression explicitly'):
            check_manifest(value, self.bootstrap)

    def test_semantic_errors_remain_real_and_have_no_bypass(self):
        cases = {row['name']: row for row in self.value['runtime_cases']}
        self.assertEqual(len(cases), 16)
        self.assertEqual(cases['registered-cache']['stdout'], 'initial-cache-1.0\n')
        self.assertEqual(cases['check-installed-payload']['args'][0], '-q')
        for name, library in (('missing-requires', '/usr/lib/__emberbsd_missing_required_library__.dylib'),
                              ('separate-root-refuses-host-cache', '/usr/lib/libSystem.B.dylib')):
            self.assertEqual(cases[name]['exit'], 1)
            self.assertTrue(cases[name]['stderr_nonempty'])
            self.assertEqual(cases[name]['stderr_contains'], 'missing required library: ' + library)
        for label in ('missing', 'target'):
            args = cases['create-' + label]['args']
            self.assertEqual(args[args.index('-I') + 1], '@WORK@/' + label + '-installed')
        for name in ('missing-not-registered', 'target-not-registered'):
            self.assertEqual(cases[name]['exit'], 1)
        for option in ('-f', '-D', '-m', '-n', '-I'):
            value = copy.deepcopy(self.value)
            next(row for row in value['runtime_cases'] if row['name'] == 'missing-requires')['args'].insert(0, option)
            with self.assertRaisesRegex(ValueError, 'check bypass'):
                check_manifest(value, self.bootstrap)
        self.assertIn('REQUIRES=/usr/lib/libSystem.B.dylib\n', self.value['files']['cache-build-info'])
        self.assertIn('REQUIRES=/usr/lib/__emberbsd_missing_required_library__.dylib\n',
                      self.value['files']['missing-build-info'])
        self.assertIn('OS_VERSION=@HOST_KERNEL_VERSION@\n', self.value['files']['cache-build-info'])

    def test_common_dyld_patch_keeps_missing_and_separate_root_refusals(self):
        patch = PATCH.read_text()
        self.assertIn('(Destdir != NULL && strcmp(Destdir, "/") != 0)', patch)
        self.assertIn('if (!found && required_library_in_shared_cache(libpath))', patch)
        self.assertIn('warnx("%s: missing required library: %s"', patch)
        # The additional cache query is not conditional on BOOTSTRAP mode.
        self.assertNotIn('#ifdef BOOTSTRAP', patch)
        source = original('pkgtools/pkg_install/files/add/perform.c')
        self.assertEqual(source.count('if (check_requires(pkg))'), 2)
        self.assertIn('if (ret == 1 && Force)', source)
        # Force still exists upstream, but this fixed producer never selects it.
        check_manifest(self.value, self.bootstrap)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ports-source', type=Path, default=ROOT)
    parser.add_argument('--dyld-patch', type=Path, default=PATCH)
    args, test_args = parser.parse_known_args()
    SOURCE = args.ports_source.resolve(strict=True)
    PATCH = args.dyld_patch.resolve(strict=True)
    unittest.main(argv=[sys.argv[0], *test_args])
