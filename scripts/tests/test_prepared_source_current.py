# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""A prepared source is refused when its receipt names another Ports recipe.

The check runs against this checkout's own recipes and Git objects."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/prepared-source-current.py'
GIT = '/usr/bin/git'
spec = importlib.util.spec_from_file_location('prepared_source_current', SCRIPT)
current = importlib.util.module_from_spec(spec)
spec.loader.exec_module(current)


class PreparedSourceCurrentTest(unittest.TestCase):
    def setUp(self):
        self.sdk = os.environ['EMBERBSD_SDK_SOURCE']
        self.work = tempfile.TemporaryDirectory(dir=os.environ['EMBERBSD_TEST_WORK'])
        self.addCleanup(self.work.cleanup)

    def receipt(self, name, package, identity):
        source = Path(self.work.name, name)
        source.mkdir()
        (source / current.RECEIPT).write_text(json.dumps({
            'format': 'emberbsd-prepared-source', 'version': 1, 'package': package,
            'identity': identity, 'tree_sha256': '0' * 64}))
        return source

    def check(self, *sources, patch=None):
        command = [sys.executable, '-B', str(SCRIPT), '--sdk-source', self.sdk, '--git', GIT]
        if patch:
            command += ['--patch', patch]
        for name, path in sources:
            command += ['--source', f'{name}={path}']
        return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def libevent_identity(self):
        script, package = current.OWNERS['libevent']
        owner = current.owner_module('libevent', ROOT / script)
        return {'effective': owner.git_effective_identity(GIT),
                'owner_sha256': hashlib.sha256((ROOT / script).read_bytes()).hexdigest()}

    def test_receipt_of_the_current_recipe_passes(self):
        source = self.receipt('libevent', 'devel/libevent', self.libevent_identity())
        result = self.check(('libevent', source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'current': ['libevent']})
        self.assertEqual(result.stderr, '')

    def test_receipt_of_another_recipe_is_stale(self):
        # A tree prepared before a recipe change (a stale Ports pin) names
        # other effective recipe objects.
        identity = self.libevent_identity()
        identity['effective']['effective_package_sha256'] = '1' * 64
        source = self.receipt('libevent', 'devel/libevent', identity)
        result = self.check(('libevent', source))
        self.assertEqual(result.returncode, 1)
        self.assertIn('libevent: ' + str(source) + ' is stale: it was prepared from another devel/libevent recipe',
                      result.stderr)

    def test_pkgsrc_pin_alone_does_not_make_a_receipt_stale(self):
        # The upstream revision is provenance: the effective recipe decides.
        identity = self.libevent_identity()
        identity['effective']['upstream'] = '2' * 40
        result = self.check(('libevent', self.receipt('libevent', 'devel/libevent', identity)))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_other_owner_script_is_reported_not_refused(self):
        identity = self.libevent_identity()
        identity['owner_sha256'] = '3' * 64
        result = self.check(('libevent', self.receipt('libevent', 'devel/libevent', identity)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('prepared by another scripts/source-inputs/libevent/source.py', result.stderr)

    def test_foreign_or_unidentified_receipt_is_stale(self):
        foreign = self.receipt('foreign', 'devel/other', self.libevent_identity())
        unnamed = self.receipt('unnamed', 'devel/byacc', {'fixture': True})
        result = self.check(('libevent', foreign), ('byacc', unnamed))
        self.assertEqual(result.returncode, 1)
        self.assertIn('libevent: ' + str(foreign) + ' is not a prepared devel/libevent source', result.stderr)
        self.assertIn('byacc: ' + str(unnamed) + ' is stale: its receipt does not name its recipe', result.stderr)

    def test_libopts_recipe_with_infrastructure_patch(self):
        # The AutoGen recipe is changed by an infrastructure patch; its
        # receipt records recipe file digests, rebuilt here from Git objects
        # and the patch, as the export makes them.
        patch = os.environ.get('EMBERBSD_TEST_GPATCH') or shutil.which('gpatch')
        if not patch:
            self.skipTest('GNU patch is not available')
        selector = current.selector()
        contents = current.recipe_files(selector, 'devel/autogen', GIT, patch)
        recipe = {'devel/autogen/distinfo': hashlib.sha256(contents['distinfo']).hexdigest()}
        recipe.update({'devel/autogen/' + name: hashlib.sha256(data).hexdigest()
                       for name, data in sorted(contents.items()) if name.startswith('patches/patch-')})
        generation = current.load(ROOT / 'scripts/source-inputs/autogen/recipe.py', 'autogen_recipe_test')
        with tempfile.TemporaryDirectory(dir=self.work.name) as temporary:
            for name in ('Makefile', 'Makefile.common', 'options.mk'):
                if name in contents:
                    Path(temporary, name).write_bytes(contents[name])
            generated = generation.generation_recipe(temporary)
        identity = {'package': 'autogen', 'recipe': recipe, 'generation_recipe': generated}
        source = self.receipt('libopts', 'devel/autogen', identity)
        result = self.check(('libopts', source), patch=patch)
        self.assertEqual(result.returncode, 0, result.stderr)
        # Without the infrastructure patch the Makefile differs.
        unpatched = self.receipt('unpatched', 'devel/autogen', dict(identity, generation_recipe={
            'Makefile': current.sha256(b'unpatched\n')}))
        result = self.check(('libopts', unpatched), patch=patch)
        self.assertEqual(result.returncode, 1)
        self.assertIn('it was prepared from another devel/autogen recipe', result.stderr)
        result = self.check(('libopts', source))
        self.assertEqual(result.returncode, 1)
        self.assertIn('select --patch', result.stderr)

    def test_configuration_is_read_once_for_every_source(self):
        selector = current.selector()
        exporter = selector._exporter(ROOT)
        self.assertIs(exporter, selector._exporter(ROOT))
        self.assertIs(exporter.configuration(ROOT), exporter.configuration(ROOT))


if __name__ == '__main__':
    unittest.main()
