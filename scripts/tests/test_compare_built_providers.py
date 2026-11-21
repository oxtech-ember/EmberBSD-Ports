# SPDX-License-Identifier: BSD-2-Clause
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'compare-built-providers.py'
spec = importlib.util.spec_from_file_location('compare_built_providers', SCRIPT)
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


class Archives(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.files = {'lib/libx.so.1': b'\x7fELFlibrary', 'lib/libx.a': b'static',
                      'include/x.h': b'header', 'bin/generator': b'tool'}

    def archive(self, revision, *, changed=None, architecture='aarch64', checksum=None, link=None):
        files = self.files.copy()
        files.update(changed or {})
        name = 'libx-1nb' + str(revision)
        info = ('PKGPATH=devel/libx\nMACHINE_ARCH=' + architecture +
                '\nOPSYS=NetBSD\nLOCALBASE=/usr/pkg\nPROVIDES=/usr/pkg/lib/libx.so.1\n')
        plist = ['@name ' + name, '@cwd /usr/pkg', '@pkgdep zlib>=1']
        for key, value in files.items():
            md5 = hashlib.md5(value, usedforsecurity=False).hexdigest()
            plist.extend([key, '@comment MD5:' + (checksum or {}).get(key, md5)])
        if link is not None:
            plist.extend(['lib/libx.so', '@comment Symlink:' + link])
        payload = {'+BUILD_INFO': info.encode(), '+CONTENTS': '\n'.join(plist).encode(), **files}
        result = self.directory / (name + '.tgz')
        with tarfile.open(result, 'w:gz') as archive:
            for key, value in payload.items():
                member = tarfile.TarInfo(key)
                member.size = len(value)
                archive.addfile(member, io.BytesIO(value))
            if link is not None:
                member = tarfile.TarInfo('lib/libx.so')
                member.type = tarfile.SYMTYPE
                member.linkname = 'libx.so.1'
                archive.addfile(member)
        return result

    def test_revision_only_and_consumer_inputs(self):
        baseline = self.archive(1)
        self.assertTrue(comparison.compare(baseline, self.archive(2))['same_provider_inputs'])
        for name in self.files:
            with self.subTest(name=name):
                changed = self.archive(2, changed={name: self.files[name] + b'different'})
                result = comparison.compare(baseline, changed)
                self.assertFalse(result['same_provider_inputs'])
                self.assertEqual(result['changed_files'], [name])

    def test_registered_links_match_archived_links(self):
        baseline = self.archive(1, link='libx.so.1')
        self.assertTrue(comparison.compare(baseline, self.archive(2, link='libx.so.1'))['same_provider_inputs'])
        with self.assertRaisesRegex(ValueError, 'link differs'):
            comparison.compare(baseline, self.archive(2, link='libx.so.2'))

    def test_architecture_and_register(self):
        baseline = self.archive(1)
        different = comparison.compare(baseline, self.archive(2, architecture='x86_64'))
        self.assertFalse(different['same_provider_inputs'])
        for path in self.files:
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'differs from registered'):
                comparison.compare(baseline, self.archive(2, checksum={path: '0' * 32}))


if __name__ == '__main__':
    unittest.main()
