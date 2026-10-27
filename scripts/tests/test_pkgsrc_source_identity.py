# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise canonical-export identity with a small synthetic overlay."""

import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('identity', ROOT / 'scripts/pkgsrc-source-identity.py')
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)


class IdentityTest(unittest.TestCase):
    def test_overlay_change_and_gitlink(self):
        sdk = Path(__import__('os').environ['EMBERBSD_SDK_SOURCE'])
        work = Path(__import__('os').environ['EMBERBSD_TEST_WORK'])
        with tempfile.TemporaryDirectory(dir=work) as temp:
            root = Path(temp)
            for name in ('scripts', 'pkgsrc/cat/pkg', 'pkgsrc/lang/llvm/files', 'upstream/pkgsrc'):
                (root / name).mkdir(parents=True)
            shutil.copy(ROOT / 'scripts/prepare-pkgsrc.py', root / 'scripts')
            shutil.copy(ROOT / 'pkgsrc/lang/llvm/files/sdk_source.py', root / 'pkgsrc/lang/llvm/files')
            (root / 'pkgsrc/lang/llvm/Makefile').write_text('DISTNAME=llvm\n')
            (root / 'pkgsrc/export.conf').write_text('')
            (root / 'pkgsrc/cat/pkg/Makefile').write_text('DISTNAME=example\n')
            sha = b'1' * 40
            def git(argv, *, env):
                self.assertNotIn('GIT_INDEX_FILE', env)
                self.assertEqual(env['GIT_NO_LAZY_FETCH'], '1')
                if 'ls-files' in argv:
                    return b'160000 ' + sha + b' 0\tupstream/pkgsrc\n'
                return sha + b'\n'
            with patch.dict('os.environ', {'GIT_INDEX_FILE': '/untrusted'}), \
                    patch.object(identity.subprocess, 'check_output', side_effect=git):
                before = identity.identity(root, 'cat/pkg', sys.executable, sdk)
                self.assertEqual(before, identity.identity(root, 'cat/pkg', sys.executable, sdk))
                (root / 'pkgsrc/cat/pkg/Makefile').write_text('DISTNAME=changed\n')
                self.assertNotEqual(before, identity.identity(root, 'cat/pkg', sys.executable, sdk))
                overlay = root / 'overlay.patch'
                overlay.write_text('first patch\n')
                (root / 'pkgsrc/export.conf').write_text('patch\toverlay.patch\n')
                with_patch = identity.identity(root, 'cat/pkg', sys.executable, sdk)
                overlay.write_text('changed patch\n')
                self.assertNotEqual(with_patch, identity.identity(root, 'cat/pkg', sys.executable, sdk))
                sha = b'2' * 40
                self.assertNotEqual(before['upstream'], identity.identity(root, 'cat/pkg', sys.executable, sdk)['upstream'])
                other = root / 'other-sdk/src/emberbsd_sdk'
                other.mkdir(parents=True)
                (other / '__init__.py').write_text('API_VERSION = 1\n')
                with self.assertRaisesRegex(ValueError, 'different SDK'):
                    identity.identity(root, 'cat/pkg', sys.executable, root / 'other-sdk')
                with self.assertRaisesRegex(ValueError, 'absolute executable'):
                    identity.identity(root, 'cat/pkg', 'git', sdk)


if __name__ == '__main__':
    unittest.main()
