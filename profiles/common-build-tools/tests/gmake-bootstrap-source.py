#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check the initial GNU make owner contract without running source scripts."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / 'profiles/common-build-tools/bootstrap/gnu-gmake.json'
ARCHIVE = None
KEYS = {'format', 'version', 'origin', 'compiler', 'build_system', 'configure_args',
    'initial_only', 'name', 'canonical_host_recipe', 'source_makefile', 'required_tool_roles',
    'make_targets', 'output_programs', 'invocations', 'files', 'runtime_cases'}


def validate(value):
    if not (set(value) == KEYS and value['format'] == 'emberbsd-native-bootstrap-program'
        and type(value['version']) is int and value['version'] == 1
        and value['compiler'] == dict(family='gcc', major=16, abi='native')
        and value['initial_only'] is True and value['name'] == 'gmake'
        and value['build_system'] == 'gnu-configure-bootstrap'
        and value['configure_args'] == ['--disable-nls', '--without-guile']
        and value['canonical_host_recipe'] == 'upstream/pkgsrc/devel/gmake/Makefile'
        and value['source_makefile'] == 'Makefile.in' and value['make_targets'] == []
        and value['output_programs'] == {'gmake': 'make'} and value['invocations'] == ['gmake']
        and not {'make', 'gmake'} & set(value['required_tool_roles'])
        and len(value['required_tool_roles']) == len(set(value['required_tool_roles']))):
        raise ValueError('The fixed initial source contract changed.')


def verify_archive(data, info):
    name = 'make-4.4.1.tar.gz'
    for label, constructor in (('BLAKE2s', hashlib.blake2s), ('SHA512', hashlib.sha512)):
        wanted = re.findall(r'^' + label + r' \(' + re.escape(name) + r'\) = ([0-9a-f]+)$', info, re.M)
        if len(wanted) != 1 or constructor(data).hexdigest() != wanted[0]:
            raise ValueError('Canonical archive checksum differs: ' + label)
    size = re.findall(r'^Size \(' + re.escape(name) + r'\) = ([0-9]+) bytes$', info, re.M)
    if size != [str(len(data))]:
        raise ValueError('Canonical archive size differs.')


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.value = json.loads(MANIFEST.read_bytes())
        self.recipe = ROOT / 'upstream/pkgsrc/devel/gmake'

    def test_existing_envelope_and_no_installed_make(self):
        validate(self.value)
        self.assertTrue({'cc', 'sh', 'ar', 'sed', 'grep', 'tr', 'mkdir', 'mv'} <= set(self.value['required_tool_roles']))
        for role in ('make', 'gmake'):
            bad = copy.deepcopy(self.value)
            bad['required_tool_roles'].append(role)
            with self.assertRaises(ValueError):
                validate(bad)
        for change in ({'command': ['/unbound/program']}, {'make_targets': [{'directory': '.', 'targets': ['all']}]},
                       {'compiler': dict(family='clang', major=21, abi='native')}):
            bad = dict(self.value, **change)
            with self.assertRaises(ValueError):
                validate(bad)

    def test_canonical_recipe_and_nls_policy(self):
        recipe = (self.recipe / 'Makefile').read_text()
        options = (self.recipe / 'options.mk').read_text()
        self.assertRegex(recipe, r'(?m)^DISTNAME=\s*make-4\.4\.1$')
        self.assertIn('PKG_SUGGESTED_OPTIONS=\tnls', options)
        self.assertIn('USE_BUILTIN.gettext', options)
        self.assertIn('PKGSRC_DEFAULT_SHELL', recipe)
        self.assertEqual(len(list((self.recipe / 'patches').glob('patch-*'))), 6)

    def test_release_bootstrap_and_checksum_mutants(self):
        data = ARCHIVE.read_bytes()
        info = (self.recipe / 'distinfo').read_text()
        verify_archive(data, info)
        with self.assertRaises(ValueError):
            verify_archive(bytes([data[0] ^ 1]) + data[1:], info)
        with self.assertRaises(ValueError):
            verify_archive(data[:-1], info)
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as source:
            expected = {'build.sh': '21f5b940e68da33ce933cfe11a7778ef40c42a23b331a855931e9495aecee618',
                        'build.cfg.in': '6cc60744c060d88591b6b4442043c3ef9a8e87d85272ee1ab2b746961c47b235',
                        'README': '21e8a99fb97a6f175d25eafe67d6b8645c11077ba9a7c54d8e37ecea00045004'}
            for name, digest in expected.items():
                member = source.getmember('make-4.4.1/' + name)
                self.assertTrue(member.isfile() and member.size < 32768)
                self.assertEqual(hashlib.sha256(source.extractfile(member).read()).hexdigest(), digest)

    def test_fixed_semantics_and_failures(self):
        cases = self.value['runtime_cases']
        self.assertEqual(len(cases), 8)
        self.assertEqual([c['exit'] for c in cases], [0, 0, 0, 0, 0, 1, 2, 2])
        self.assertTrue(all(c['invocation'] == 'gmake' for c in cases))
        source = self.value['files']['probe.mk']
        self.assertIn('test \'$(SHELL)\' = "$$EMBERBSD_BOOTSTRAP_EXPECTED_SHELL"', source)
        self.assertNotRegex(source, r'(?m)^SHELL\s*[:?+]?=')
        self.assertIn('$(MAKE) --no-print-directory', source)
        self.assertIn('-j2', cases[4]['args'])
        self.assertTrue(cases[-2]['stderr_nonempty'] and cases[-1]['stderr_nonempty'])


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--ports', type=Path, default=ROOT)
    cli.add_argument('--manifest', type=Path, default=MANIFEST)
    cli.add_argument('--archive', type=Path, required=True)
    args, rest = cli.parse_known_args()
    ROOT, MANIFEST, ARCHIVE = args.ports, args.manifest, args.archive
    unittest.main(argv=['gmake-bootstrap-source.py', *rest])
