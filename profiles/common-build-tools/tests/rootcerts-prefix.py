#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check CA source and finite make metadata. Do not build or install packages.

The fixture evaluates the real recipe with synthetic OpenSSL selection and
configuration data. It does not qualify the complete dependency graph.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import types
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / 'profiles/common-build-tools/patches/mozilla-rootcerts-prefix.patch'
RECIPE = 'security/mozilla-rootcerts-openssl/Makefile'
PLIST = 'security/mozilla-rootcerts-openssl/PLIST'
HELPER = ROOT / 'profiles/common-build-tools/tests/bsdinstall-source.py'
model = types.ModuleType('source_patch_model')
model.__file__ = str(HELPER)
exec(compile(HELPER.read_bytes(), str(HELPER), 'exec'), model.__dict__)
ARGS = None


def sources():
    originals = {name: (ROOT / 'pkgsrc' / name).read_text()
                 for name in (RECIPE,)}
    return originals, model.replay(originals, PATCH.read_text())


class PrefixTests(unittest.TestCase):
    def test_existing_install_and_owned_files_are_unchanged(self):
        originals, result = sources()
        def install(text):
            return text.split('do-install:\n')[1].split('.include ')[0]
        self.assertEqual(install(result[RECIPE]), install(originals[RECIPE]))
        self.assertNotIn('cert.pem', result[RECIPE])
        self.assertIn('${DESTDIR}${OPENSSLDIR}', install(result[RECIPE]))
        self.assertIn('${SCRIPT} -d ${DESTDIR} install', install(result[RECIPE]))
        # Existing CA payloads remain under the ordinary package packing list.
        plist = (ROOT / 'pkgsrc' / PLIST).read_text().splitlines()
        self.assertIn('${MYETCDIR}/openssl/certs/ca-certificates.crt', plist)
        self.assertGreater(len([line for line in plist if line.endswith('.pem')]), 100)
        self.assertFalse(any(line.endswith('/cert.pem') for line in plist))

    def test_one_owner_preserves_certificate_data(self):
        originals, result = sources()
        self.assertEqual(set(result), {RECIPE})
        record = 'patch\t' + PATCH.relative_to(ROOT).as_posix() + '\n'
        self.assertEqual((ROOT / 'pkgsrc/export.conf').read_text().count(record), 1)
        for name in ('mozilla-rootcerts', 'mozilla-rootcerts-openssl'):
            self.assertTrue((ROOT / 'pkgsrc/security' / name).is_dir())
            self.assertIn('security/' + name, (ROOT / 'pkgsrc/replaces').read_text().splitlines())
        self.assertIn('mozilla-rootcerts>=1.1.20261020:', result[RECIPE])

    def test_foundation_selects_trust_in_final_prefix(self):
        policy = (ROOT / 'profiles/development-toolchain/darwin-bootstrap.mk.conf').read_text()
        self.assertIn('BOOTSTRAP_DEPENDS+= mozilla-rootcerts-openssl>=2.24nb1:../../security/mozilla-rootcerts-openssl', policy)
        self.assertRegex(policy, r'(?m)^PREFER.openssl= pkgsrc$')
        self.assertRegex(policy, r'(?m)^PKG_SYSCONFBASEDIR= \$\{LOCALBASE\}/etc$')

    def test_real_metadata_and_former_failure(self):
        if not ARGS.make_arg:
            self.skipTest("Supply an explicit SDK make tuple for finite metadata")
        originals, result = sources()
        work = ARGS.work.resolve()
        work.mkdir(parents=True, exist_ok=False)
        for directory in ('security/mozilla-rootcerts-openssl', 'security/openssl', 'mk'):
            (work / directory).mkdir(parents=True, exist_ok=True)
        (work / 'security/openssl/builtin.mk').write_text('# Explicit fixture selection; no discovery.\n')
        (work / 'mk/bsd.pkg.mk').write_text('PKG_SYSCONFDIR= ${PKG_SYSCONFBASEDIR}\n')
        variables = ['PREFIX', 'OPENSSLDIR', 'PLIST_SUBST', 'NOT_FOR_UNPRIVILEGED', 'SCRIPT']
        receipts = {}

        def query(text, builtin, config):
            path = work / RECIPE
            path.write_text('PREFIX= /sdk/final\n' + text)
            command = [*ARGS.make_arg, '-r', '-C', str(path.parent),
                'LOCALBASE=/sdk/final', 'PKG_SYSCONFBASEDIR=' + config,
                'USE_BUILTIN.openssl=' + builtin]
            for variable in variables:
                command += ['-v', variable]
            run = subprocess.run(command, check=True, capture_output=True, text=True)
            lines = run.stdout.splitlines()
            self.assertEqual(len(lines), len(variables), run.stdout)
            return dict(zip(variables, lines))

        old = query(originals[RECIPE], 'no', '/sdk/final/etc')
        self.assertEqual(old['PREFIX'], '/')
        for name, builtin, config, prefix, certdir, relative in (
            ('contained', 'no', '/sdk/final/etc', '/sdk/final', '/sdk/final/etc/openssl/certs', 'etc'),
            ('external', 'no', '/separate/config', '/', '/separate/config/openssl/certs', 'separate/config'),
            ('neighbor', 'no', '/sdk/final-other/etc', '/', '/sdk/final-other/etc/openssl/certs', 'sdk/final-other/etc'),
            ('builtin', 'yes', '/sdk/final/etc', '/', '/etc/openssl/certs', 'etc'),
        ):
            data = query(result[RECIPE], builtin, config)
            self.assertEqual(data['PREFIX'], prefix, name)
            self.assertEqual(data['OPENSSLDIR'], certdir, name)
            self.assertIn('MYETCDIR=' + relative, data['PLIST_SUBST'].split(), name)
            self.assertEqual(data['NOT_FOR_UNPRIVILEGED'], 'yes' if builtin == 'yes' else '', name)
            self.assertEqual(data['SCRIPT'], '/sdk/final/sbin/mozilla-rootcerts', name)
            receipts[name] = data
        for name, mutant in (
            ('lost-containment', result[RECIPE].replace('SET_PREFIX=\t\tno', 'SET_PREFIX=\t\tyes')),
            ('absolute-plist', result[RECIPE].replace(':S/^\\///', '')),
        ):
            data = query(mutant, 'no', '/sdk/final/etc')
            self.assertFalse(data['PREFIX'] == '/sdk/final' and
                             'MYETCDIR=etc' in data['PLIST_SUBST'].split(), name)
            receipts[name] = data
        receipts['before'] = old
        (work / 'metadata.json').write_text(json.dumps(receipts, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make-arg', action='append', default=[])
    parser.add_argument('--work', type=Path)
    ARGS, remaining = parser.parse_known_args()
    if ARGS.make_arg and (ARGS.work is None or not ARGS.work.is_absolute()):
        parser.error('--make-arg requires a new absolute --work directory')
    unittest.main(argv=[__file__, *remaining])
