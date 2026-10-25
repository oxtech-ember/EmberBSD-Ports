#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted finite source-policy controls.
"""Check foundation edges and canonical shell routes. Execute no native tool."""
import argparse
import fnmatch
from pathlib import Path
import re
import sys
import types
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT
POLICY = ROOT / 'profiles/development-toolchain/darwin-bootstrap.mk.conf'
HELPER = ROOT / 'profiles/development-toolchain/tests/darwin-bootstrap-bsdinstall.py'
model = types.ModuleType('installer_source_model')
model.__file__ = str(HELPER)
exec(compile(HELPER.read_bytes(), str(HELPER), 'exec'), model.__dict__)

# These are provider requirements, not a claim about the complete build graph.
PROVIDERS = {
    'sysutils/bsdinstall': ('bsdinstall', ('bin/bsdinstall',)),
    'devel/bmake': ('bmake', ('bin/bmake',)),
    'devel/gmake': ('gmake', ('bin/gmake',)),
    'sysutils/coreutils': ('coreutils', tuple('bin/g' + name for name in
        'basename cat cut date dirname env expr head id pwd sort tail tr uname uniq wc '
        'chgrp chmod chown cp ln ls mkdir mv rm rmdir sleep touch printf'.split())),
    'sysutils/findutils': ('findutils', ('bin/gfind', 'bin/gxargs')),
    'textproc/grep': ('grep', ('bin/ggrep', 'bin/gegrep', 'bin/gfgrep')),
    'textproc/gsed': ('gsed', ('bin/gsed',)),
    'lang/nawk': ('nawk', ('bin/nawk',)),
    'pkgtools/pkg_install': ('pkg_install', tuple('sbin/pkg_' + name for name in
                                              ('add', 'create', 'admin', 'info'))),
    'pkgtools/pkg_install-info': ('pkg_install-info', ('bin/pkg_install-info',)),
    'devel/diffutils': ('diffutils', ('bin/gcmp', 'bin/gdiff')),
    'devel/meson': ('meson', ('bin/meson',)),
    'security/mozilla-rootcerts-openssl': ('mozilla-rootcerts-openssl',
        ('${MYETCDIR}/openssl/certs/ca-certificates.crt',)),
}


def source(relative):
    overlay = SOURCE / 'pkgsrc' / relative
    return (overlay if overlay.is_file() else SOURCE / 'upstream/pkgsrc' / relative).read_text()


def match(text, expression):
    found = re.search(expression, text, re.M)
    if found is None:
        raise AssertionError('Missing canonical source expression: ' + expression)
    return found[1]


def bmake_version():
    # This exact recipe hunk precedes the release source import.
    patch = (SOURCE / 'profiles/common-build-tools/patches/pkgsrc-bmake-20260912.patch').read_text()
    section = patch[:patch.index('diff --git a/devel/bmake/files/')]
    recipe = source('devel/bmake/Makefile')
    before = match(section, r'^-PKGNAME=\s*(bmake-\S+)')
    after = match(section, r'^\+PKGNAME=\s*(bmake-\S+)')
    assert match(recipe, r'^PKGNAME=\s*(\S+)') == before
    return after.removeprefix('bmake-')


def versions():
    values = {'devel/bmake': bmake_version(),
        'pkgtools/pkg_install': match(source('pkgtools/pkg_install/files/lib/version.h'),
                                     r'^#define PKGTOOLS_VERSION (\d+)'),
        'pkgtools/pkg_install-info': match(source('devel/gtexinfo/Makefile.common'),
                                          r'^TEXINFO_VERSION=\s*(\S+)')}
    for recipe, name in (('sysutils/bsdinstall', 'bsdinstall'), ('devel/gmake', 'make'),
                         ('sysutils/coreutils', 'coreutils'), ('sysutils/findutils', 'findutils'),
                         ('textproc/grep', 'grep'), ('textproc/gsed', 'sed'),
                         ('lang/nawk', 'nawk'), ('devel/diffutils', 'diffutils'), ('devel/meson', 'meson')):
        file = recipe + ('/Makefile.common' if recipe == 'sysutils/coreutils' else '/Makefile')
        values[recipe] = match(source(file), r'^DISTNAME=\s*' + name + r'-(\S+)')
    values['sysutils/bsdinstall'] += 'nb' + match(source('sysutils/bsdinstall/Makefile'),
                                                r'^PKGREVISION=\s*(\S+)')
    ca = 'security/mozilla-rootcerts-openssl'
    revision_patch = (SOURCE / 'profiles/common-build-tools/patches/mozilla-rootcerts-prefix.patch').read_text()
    values[ca] = match(source(ca + '/Makefile'), r'^PKGNAME=\s*mozilla-rootcerts-openssl-(\S+)')
    values[ca] += 'nb' + match(revision_patch, r'^\+PKGREVISION=\s*(\S+)')
    return values


def shell_body(text):
    start = re.search(r'^\.\s*if \$\{TOOLS_PLATFORM.sh:M\?\*/bin/mksh\}\s*$', text, re.M)
    if start is None:
        raise AssertionError('Missing canonical mksh decision')
    return re.split(r'^\.\s*(?:elif|else|endif)\b', text[start.end():], maxsplit=1, flags=re.M)[0]


def shell_routes(texts, prefix, selected):
    if not fnmatch.fnmatchcase(selected, '?*/bin/mksh'):
        raise AssertionError('The selected input does not activate the mksh branch')
    result = {}
    for name, variable, marker in (
            ('devel/bmake', 'CONFIGURE_ARGS', '--with-defshell='),
            ('devel/gmake', 'CPPFLAGS', '-DPKGSRC_DEFAULT_SHELL='),
            ('devel/ninja-build', 'CFLAGS', '-DNINJA_SHELL=')):
        body = shell_body(texts[name])
        assert '../../shells/mksh' in body, 'The final shell lacks its normal dependency'
        value = match(body, r'^' + variable + r'\+=\s*(' + re.escape(marker) + r'.*)')
        assert '${PREFIX}/bin/mksh' in value, 'The installed shell is not in the final prefix'
        result[name] = value.replace('${PREFIX}', prefix)
    assert '--with-default-sys-path=${PREFIX}/share/mk' in texts['devel/bmake']
    return result


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.policy = POLICY.read_text()
        self.state = dict(EMBERBSD_DARWIN_BOOTSTRAP='yes', BSD_PKG_MK='1',
                          LOCALBASE='/final/prefix')

    def test_root_edges_wait_for_pkgpath_and_apply_once(self):
        state = model.apply_policy(self.policy, dict(self.state))
        self.assertEqual(state, self.state)
        state['PKGPATH'] = 'lang/gcc16'
        model.apply_policy(self.policy, state)
        self.assertEqual(set(model.dependencies(state)), set(PROVIDERS))
        self.assertEqual(len(model.dependencies(state)), len(PROVIDERS))
        self.assertEqual(model.apply_policy(self.policy, dict(state)), state)

    def test_dependency_versions_and_payloads_come_from_common_owners(self):
        state = model.apply_policy(self.policy, dict(self.state, PKGPATH='lang/gcc16'))
        expected = versions()
        for word in state['BOOTSTRAP_DEPENDS'].split():
            package, recipe = word.split(':../../')
            name, floor = package.split('>=')
            self.assertEqual((name, floor), (PROVIDERS[recipe][0], expected[recipe]))
            plist = source(recipe + '/PLIST').splitlines()
            for member in PROVIDERS[recipe][1]:
                self.assertIn(member, plist, (recipe, member))
        self.assertNotIn('bin/ginstall', PROVIDERS['sysutils/coreutils'][1])

    def test_native_and_nonroot_policy_stays_unchanged(self):
        seeds = model.seed_make_recipes(self.policy)
        for name in ('pkgtools/libnbcompat', 'devel/bmake', 'pkgtools/bootstrap-mk-files',
                     'devel/meson', 'devel/ninja-build', 'lang/llvm'):
            state = model.apply_policy(self.policy, dict(self.state, PKGPATH=name))
            roots = [] if name in seeds else ['devel/bmake']
            self.assertEqual(model.dependencies(state), roots, name)
        for changes in (dict(EMBERBSD_DARWIN_BOOTSTRAP='no', PKGPATH='lang/gcc16'),
                        dict(PKGPATH='lang/gcc16')):
            state = dict(self.state, **changes)
            if changes.get('EMBERBSD_DARWIN_BOOTSTRAP') != 'no':
                del state['BSD_PKG_MK']
            self.assertEqual(model.apply_policy(self.policy, dict(state)), state)

    def test_standard_data_and_ninja_dependencies_are_not_artificial_roots(self):
        self.assertIn('bootstrap-mk-files-[0-9]*:../../pkgtools/bootstrap-mk-files',
                      source('devel/bmake/Makefile'))
        self.assertIn('ninja-build>=1.7:../../devel/ninja-build', source('devel/meson/Makefile'))
        self.assertNotIn('pkgtools/bootstrap-mk-files', PROVIDERS)
        self.assertNotIn('devel/ninja-build', PROVIDERS)
        self.assertIn('share/mk/sys.mk', source('pkgtools/bootstrap-mk-files/PLIST').splitlines())
        self.assertIn('bin/ninja', source('devel/ninja-build/PLIST').splitlines())

    def test_policy_edges_cannot_form_self_or_global_cycles(self):
        graph = model.graph(self.policy)
        self.assertEqual(model.reachable(graph), set(graph))
        mutant = self.policy.replace('.    if ${PKGPATH} == "lang/gcc16"',
                                     '.    if ${PKGPATH} != ""')
        with self.assertRaisesRegex(ValueError, 'dependency cycle'):
            model.reachable(model.graph(mutant))

    def test_canonical_make_and_ninja_shells_use_the_final_mksh(self):
        texts = {name: source(name + '/Makefile') for name in
                 ('devel/bmake', 'devel/gmake', 'devel/ninja-build')}
        routes = shell_routes(texts, '/final/prefix', '/accepted/initial/bin/mksh')
        self.assertEqual(routes['devel/bmake'], '--with-defshell=/final/prefix/bin/mksh')
        for value in routes.values():
            self.assertIn('/final/prefix/bin/mksh', value)
            self.assertNotIn('/accepted/initial', value)
        configure = source('devel/bmake/files/configure.in')
        self.assertIn('AC_DEFINE_UNQUOTED(DEFSHELL_PATH, "$defshell_path"', configure)
        self.assertIn('shellPath = bmake_strdup(DEFSHELL_PATH);', source('devel/bmake/files/job.c'))

    def test_lost_or_initial_shell_configuration_is_causally_rejected(self):
        texts = {name: source(name + '/Makefile') for name in
                 ('devel/bmake', 'devel/gmake', 'devel/ninja-build')}
        for name in texts:
            for replacement in ('/bin/sh', '${EMBERBSD_DARWIN_SH}'):
                mutant = dict(texts)
                mutant[name] = texts[name].replace('${PREFIX}/bin/mksh', replacement)
                with self.subTest(recipe=name, replacement=replacement):
                    with self.assertRaisesRegex(AssertionError, 'final prefix'):
                        shell_routes(mutant, '/final/prefix', '/accepted/initial/bin/mksh')
        with self.assertRaisesRegex(AssertionError, 'does not activate'):
            shell_routes(texts, '/final/prefix', '/accepted/other-shell')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ports-source', type=Path, default=ROOT)
    args, remaining = parser.parse_known_args()
    SOURCE = args.ports_source
    unittest.main(argv=[__file__, *remaining])
