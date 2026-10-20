#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Synthetic ELF, native package and bundle regressions.
"""Exercise GCC16 installer packaging and the bootstrap runtime audit."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOTS = ['/bin/sh', '/bin/tar', '/usr/bin/tar', '/usr/bin/sha512',
         '/usr/bin/cmp', '/usr/bin/id', '/usr/sbin/pkg_add', '/usr/sbin/pkg_info']
INSTALLER = Path(__file__).resolve().parents[1]
RUNTIME_FILES = INSTALLER.parent / 'development-toolchain/runtime/recipe/files'
sys.path.insert(0, str(RUNTIME_FILES))
import sdk_source
_test_arguments = sdk_source.arguments(sys.argv[1:])
SDK_SOURCE = sdk_source.load()
import runtime as rt


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(*args, env=None):
    process_env = os.environ.copy()
    process_env.update({'COPYFILE_DISABLE': '1', 'XZ_OPT': '-0'})
    if env:
        process_env.update(env)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=process_env, check=False)
    if result.returncode:
        raise AssertionError(f'{args!r}\n{result.stdout}{result.stderr}')
    return result.stdout


def elf_bytes(*, soname=None, needed=(), rpath=None, executable=False,
              machine=62, static=False):
    """Create a minimal, non-executed ELF fixture for the production parsers."""
    strings = bytearray(b'\0')
    indexes = {}
    for name in ([soname] if soname else []) + list(needed) + ([rpath] if rpath else []):
        indexes[name] = len(strings)
        strings.extend(name.encode() + b'\0')
    dynamic = []
    if not static:
        dynamic = [(5, 0x400280), (10, len(strings))]
        if soname:
            dynamic.append((14, indexes[soname]))
        if rpath:
            dynamic.append((29, indexes[rpath]))
        dynamic.extend((1, indexes[name]) for name in needed)
        dynamic.append((0, 0))
    dynamic_data = b''.join(struct.pack('<QQ', *entry) for entry in dynamic)
    interpreter = b'/libexec/ld.elf_so\0' if executable and not static else b''
    dynamic_offset = 320
    string_offset = 640
    interpreter_offset = string_offset + len(strings)
    total = interpreter_offset + len(interpreter)
    phdrs = [(1, 5, 0, 0x400000, 0x400000, total, total, 4096)]
    if not static:
        phdrs.extend([
            (2, 6, dynamic_offset, 0x400140, 0x400140,
             len(dynamic_data), len(dynamic_data), 8),
            (0x6474E552, 4, dynamic_offset, 0x400140, 0x400140,
             len(dynamic_data), len(dynamic_data), 1),
        ])
    if interpreter:
        phdrs.append((3, 4, interpreter_offset, 0x400000 + interpreter_offset,
                      0x400000 + interpreter_offset, len(interpreter), len(interpreter), 1))

    data = bytearray(total)
    data[:16] = b'\x7fELF\x02\x01\x01'.ljust(16, b'\0')
    data[16:64] = struct.pack('<HHIQQQIHHHHHH', 2 if executable else 3, machine,
                              1, 0x400100 if executable else 0, 64, 0, 0,
                              64, 56, len(phdrs), 0, 0, 0)
    for index, phdr in enumerate(phdrs):
        struct.pack_into('<IIQQQQQQ', data, 64 + 56 * index, *phdr)
    if dynamic_data:
        data[dynamic_offset:dynamic_offset + len(dynamic_data)] = dynamic_data
    data[string_offset:string_offset + len(strings)] = strings
    if interpreter:
        data[interpreter_offset:] = interpreter
    return bytes(data)


class FixtureStage:
    def __init__(self, payload, result):
        self.payload = Path(payload)
        self.result = result

    def verify(self):
        return self.result

    def install(self, destination):
        prefix = Path(destination) / 'usr/pkg'
        prefix.mkdir(parents=True)
        files = self.result['files'] + [
            'share/licenses/gcc16-runtime/' + name for name in rt.LICENSES
        ]
        for name in files:
            source, target = self.payload / name, prefix / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_symlink():
                target.symlink_to(os.readlink(source))
            else:
                shutil.copyfile(source, target)
                target.chmod(source.stat().st_mode & 0o777)
        return self.result


class RuntimeInstallerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg_create = os.environ['PKG_CREATE']
        cls.bsdtar = os.environ.get('BSDTAR', 'bsdtar')
        cls.readelf = os.environ.get('READ_ELF')
        cls.builder = INSTALLER / 'bundle-gcc16.py'
        cls.auditor = INSTALLER / 'audit-bootstrap.rb'

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='ember-runtime-installer-')).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def make_package(self):
        for root in (self.tmp / 'payload', self.tmp / 'created', self.tmp / 'bundle'):
            if root.is_symlink() or root.is_file():
                root.unlink()
            elif root.exists():
                shutil.rmtree(root)
        self.payload = self.tmp / 'payload'
        lib = self.payload / 'gcc16/lib'
        lib.mkdir(parents=True)
        (lib / 'libgcc_s.so.1').write_bytes(elf_bytes(
            soname='libgcc_s.so.1', needed=['libc.so.12'], rpath='/usr/pkg/gcc16/lib'))
        (lib / 'libstdc++.so.7.36').write_bytes(elf_bytes(
            soname='libstdc++.so.7', needed=['libc.so.12', 'libgcc_s.so.1'],
            rpath='/usr/pkg/gcc16/lib'))
        for path in lib.iterdir():
            path.chmod(0o755)
        (lib / 'libstdc++.so.7').symlink_to('libstdc++.so.7.36')
        license_dir = self.payload / 'share/licenses/gcc16-runtime'
        license_dir.mkdir(parents=True)
        for name in rt.LICENSES:
            (license_dir / name).write_text('License fixture: ' + name)

        files = ['gcc16/lib/libgcc_s.so.1', 'gcc16/lib/libstdc++.so.7',
                 'gcc16/lib/libstdc++.so.7.36']
        metadata = {
            'OPSYS': 'NetBSD', 'OS_VERSION': '11.0', 'MACHINE_ARCH': 'x86_64',
            'PKGPATH': 'lang/gcc16-runtime', 'PKGNAME': rt.NAME,
            'LICENSE': 'gnu-gpl-v3', 'GCC_VERSION': rt.VERSION,
            'GCC_RUNTIME_SONAME': 'libstdc++.so.7',
            'GCC_RUNTIME_LIBRARIES': 'libgcc,libstdc++',
            'GCC_RUNTIME_SONAMES': 'libgcc_s.so.1,libstdc++.so.7',
            'GCC_RUNTIME_TARGET': 'amd64', 'GCC_RUNTIME_TRIPLET': 'x86_64--netbsd',
            'GCC_RUNTIME_MACHINE_ARCH': 'x86_64',
            'GCC_SOURCE_SHA256': rt.SOURCE_SHA256,
            'GCC_RECIPE_SHA256': 'a' * 64, 'GCC_RECIPE_DISTINFO_SHA256': 'a' * 64,
            'GCC_RUNTIME_INPUTS_SHA256': 'a' * 64, 'GCC_RUNTIME_STAGE_SHA256': 'a' * 64,
            'GCC_RUNTIME_LINKS_SHA256': 'a' * 64,
            'GCC_RUNTIME_CXX_MATH_INPUTS_SHA256': 'a' * 64,
            'GCC_RUNTIME_CXX_TLS_INPUTS_SHA256': 'a' * 64,
            'EMBERBSD_SEED_SOURCE': 'b' * 40,
        }
        result = {
            'files': files,
            'metadata': metadata,
            'elf': {
                name: rt.ELF((self.payload / name).resolve()).verify(
                    'libstdc++.so.7' if 'libstdc++' in name else 'libgcc_s.so.1',
                    rt.TARGETS['amd64'], ['libgcc_s.so.1', 'libstdc++.so.7'])
                for name in files
            },
            'tls_abi': {'fixture': 'synthetic non-executed ELF'},
        }
        self.source = self.tmp / 'created'
        rt.create(FixtureStage(self.payload, result), self.pkg_create, self.source)
        self.package = self.source / (rt.NAME + '.tgz')
        self.output = self.tmp / 'bundle'

    def bundle(self):
        return subprocess.run(
            [sys.executable, '-B', str(self.builder), str(self.source), str(self.output),
             '--sdk-source', SDK_SOURCE],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={**os.environ, 'BSDTAR': self.bsdtar}, check=False)

    def test_cli_loads_python_runtime_before_argument_validation(self):
        result = subprocess.run(
            [sys.executable, '-B', str(self.builder), '--sdk-source', SDK_SOURCE],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        self.assertEqual(1, result.returncode)
        self.assertIn('Usage: bundle-gcc16.py', result.stderr)
        self.assertNotIn('LoadError', result.stderr)

    def rewrite_package(self, mutate):
        extracted = self.tmp / 'package-edit'
        if extracted.exists():
            shutil.rmtree(extracted)
        extracted.mkdir()
        with tarfile.open(self.package, 'r:*') as archive:
            archive.extractall(extracted, filter='data')
        mutate(extracted)
        members = [path for path in extracted.rglob('*') if path.is_file() or path.is_symlink()]
        with tarfile.open(self.package, 'w:gz') as archive:
            for path in members:
                name = path.relative_to(extracted).as_posix()
                info = archive.gettarinfo(str(path), arcname=name)
                if info.isfile():
                    with path.open('rb') as stream:
                        archive.addfile(info, stream)
                else:
                    archive.addfile(info)
        (self.source / 'package.sha256').write_text(
            f'{sha256(self.package)}  {rt.NAME}.tgz\n')

    @staticmethod
    def refresh_md5(directory, name, old_bytes):
        plist = directory / '+CONTENTS'
        old_digest = hashlib.md5(old_bytes).hexdigest()
        new_digest = hashlib.md5((directory / name).read_bytes()).hexdigest()
        plist.write_text('\n'.join(line.replace(old_digest, new_digest)
                                   for line in plist.read_text().splitlines()) + '\n')

    def test_bundle_builds_real_native_package_output_and_preserves_contract(self):
        self.make_package()
        before = {name: sha256(self.source / name) for name in sorted(p.name for p in self.source.iterdir())}
        result = self.bundle()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        archive = self.output / 'runtime-gcc16.tar.xz'
        inner = self.tmp / 'bundle-inner'
        inner.mkdir()
        run(self.bsdtar, '-xf', str(archive), '-C', str(inner))
        self.assertEqual('gcc16\n', (inner / 'PROFILE').read_text())
        self.assertEqual(rt.NAME + '\n', (inner / 'ROOTS').read_text())
        self.assertEqual(self.package.read_bytes(),
                         (inner / 'All' / (rt.NAME + '.tgz')).read_bytes())
        package_sha = hashlib.sha512(self.package.read_bytes()).hexdigest()
        self.assertEqual(f'SHA512 ({rt.NAME}.tgz) = {package_sha}\n',
                         (inner / 'SHA512').read_text())
        archive_sha = hashlib.sha512(archive.read_bytes()).hexdigest()
        self.assertEqual(f'SHA512 (runtime-gcc16.tar.xz) = {archive_sha}\n',
                         (self.output / 'SHA512').read_text())
        self.assertLessEqual(archive.stat().st_size, 64 * 1024 * 1024)
        listing = run(self.bsdtar, '-tvf', str(archive))
        self.assertIn('root', listing)
        self.assertIn('wheel', listing)
        self.assertNotRegex(listing, r'AppleDouble|SCHILY\.xattr|\.DS_Store')
        self.assertEqual(before, {name: sha256(self.source / name)
                                  for name in sorted(p.name for p in self.source.iterdir())})
        provenance = json.loads((self.output / 'PROVENANCE.json').read_text())
        self.assertEqual(sha256(self.package), provenance['package']['sha256'])

    def test_bundle_rejects_changed_package_digest_and_bad_receipts(self):
        self.make_package()
        original = json.loads((self.source / 'provenance.json').read_text())
        for key, value in [('PKGTOOLS_VERSION', None), ('PKGTOOLS_VERSION', '20260230'),
                           ('PKGTOOLS_VERSION', '20260227nb1'),
                           ('EMBERBSD_PKG_CREATE_SHA256', 'invalid'),
                           ('UNREVIEWED_METADATA', 'extra')]:
            receipt = json.loads(json.dumps(original))
            if value is None:
                del receipt['metadata'][key]
            else:
                receipt['metadata'][key] = value
            (self.source / 'provenance.json').write_text(json.dumps(receipt))
            result = self.bundle()
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(self.output.exists())
        (self.source / 'provenance.json').write_text(json.dumps(original))
        with self.package.open('ab') as stream:
            stream.write(b'changed')
        self.assertNotEqual(0, self.bundle().returncode)

    def test_bundle_reaudits_elf_and_rejects_unapproved_package_contents(self):
        mutations = []
        def wrong_arch(directory):
            name = 'gcc16/lib/libgcc_s.so.1'
            path = directory / name
            original = path.read_bytes()
            data = bytearray(original)
            data[18:20] = struct.pack('<H', 183)
            path.write_bytes(data)
            self.refresh_md5(directory, name, original)
        mutations.append(wrong_arch)
        mutations.append(lambda d: (d / 'gcc16/lib/crtbegin.o').write_text('unshipped object'))
        mutations.append(lambda d: (d / '+CONTENTS').write_text(
            (d / '+CONTENTS').read_text() + '@exec touch /tmp/unsafe\n'))
        mutations.append(lambda d: (d / 'share/licenses/gcc16-runtime/COPYING.RUNTIME').unlink())
        for mutate in mutations:
            self.make_package()
            self.rewrite_package(mutate)
            result = self.bundle()
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(self.output.exists())

    def test_bundle_rejects_changed_pkgtools_metadata_and_symlink_escape(self):
        self.make_package()
        def mutate_info(directory):
            path = directory / '+BUILD_INFO'
            path.write_text('\n'.join(
                line.split('=', 1)[0] + '=' + 'a' * 64
                if line.startswith('EMBERBSD_PKG_CREATE_SHA256=') else line
                for line in path.read_text().splitlines()) + '\n')
        self.rewrite_package(mutate_info)
        self.assertNotEqual(0, self.bundle().returncode)

        self.make_package()
        def duplicate_pkgtools(directory):
            path = directory / '+BUILD_INFO'
            path.write_text(path.read_text() + 'PKGTOOLS_VERSION=20260227\n')
        self.rewrite_package(duplicate_pkgtools)
        self.assertNotEqual(0, self.bundle().returncode)

        self.make_package()
        def wrong_target(directory):
            path = directory / '+BUILD_INFO'
            path.write_text(path.read_text().replace('MACHINE_ARCH=x86_64',
                                                     'MACHINE_ARCH=aarch64'))
        self.rewrite_package(wrong_target)
        self.assertNotEqual(0, self.bundle().returncode)

        self.make_package()
        def mutate_link(directory):
            path = directory / 'gcc16/lib/libstdc++.so.7'
            path.unlink()
            path.symlink_to('/usr/pkg/gcc16/lib/libstdc++.so.7.36')
        self.rewrite_package(mutate_link)
        self.assertNotEqual(0, self.bundle().returncode)

    def test_bundle_rejects_missing_conflicts_and_nested_output(self):
        self.make_package()
        def remove_conflicts(directory):
            path = directory / '+CONTENTS'
            path.write_text('\n'.join(line for line in path.read_text().splitlines()
                                      if not line.startswith('@pkgcfl ')) + '\n')
        self.rewrite_package(remove_conflicts)
        self.assertNotEqual(0, self.bundle().returncode)

        self.make_package()
        self.output = self.source / 'nested'
        result = self.bundle()
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.output.exists())

    def test_bundle_enforces_capacity_and_preserves_existing_outputs(self):
        self.make_package()
        def enlarge(directory):
            name = 'gcc16/lib/libgcc_s.so.1'
            path = directory / name
            original = path.read_bytes()
            path.write_bytes(original + os.urandom(65 * 1024 * 1024))
            self.refresh_md5(directory, name, original)
        self.rewrite_package(enlarge)
        result = self.bundle()
        self.assertNotEqual(0, result.returncode)
        self.assertIn('64 MiB', result.stderr)
        self.assertFalse(self.output.exists())

        self.make_package()
        self.output.symlink_to('missing')
        result = self.bundle()
        self.assertNotEqual(0, result.returncode)
        self.assertEqual('missing', os.readlink(self.output))

    def test_bundle_publishes_only_one_competing_output(self):
        self.make_package()
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _index: self.bundle(), range(2)))
        self.assertEqual(1, sum(result.returncode == 0 for result in results),
                         ''.join(result.stderr for result in results))
        archive = self.output / 'runtime-gcc16.tar.xz'
        digest = hashlib.sha512(archive.read_bytes()).hexdigest()
        self.assertEqual(f'SHA512 (runtime-gcc16.tar.xz) = {digest}\n',
                         (self.output / 'SHA512').read_text())

    @unittest.skipUnless(os.environ.get('READ_ELF'), 'Set READ_ELF to host binutils readelf')
    def test_bootstrap_audit_follows_loader_and_recursive_dependencies(self):
        dest = self.make_bootstrap()
        result = self.audit_bootstrap(dest)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(ROOTS, report['roots'])
        self.assertIn('/usr/lib/libc.so.12', report['files'])
        self.assertIn('/libexec/ld.elf_so', report['files'])

    @unittest.skipUnless(os.environ.get('READ_ELF'), 'Set READ_ELF to host binutils readelf')
    def test_bootstrap_audit_rejects_foreign_dependencies_and_runtime_paths(self):
        cases = (
            lambda d: (d / 'usr/lib/libc.so.12').unlink(),
            lambda d: self.replace_machine(d / 'usr/lib/libc.so.12'),
            lambda d: self.replace_link(d / 'usr/lib/libc.so.12', '../../../../outside'),
            lambda d: self.set_rpath(d / 'usr/sbin/pkg_add', '/usr/pkg/gcc16/lib'),
            lambda d: (d / 'usr/sbin/pkg_info').write_text('not ELF source'),
        )
        for mutate in cases:
            dest = self.make_bootstrap()
            mutate(dest)
            result = self.audit_bootstrap(dest)
            self.assertNotEqual(0, result.returncode, result.stdout)

    def make_bootstrap(self):
        dest = self.tmp / 'dest'
        if dest.exists():
            shutil.rmtree(dest)
        (dest / 'usr/lib').mkdir(parents=True)
        (dest / 'libexec').mkdir(parents=True)
        (dest / 'usr/lib/libc.so.12').write_bytes(elf_bytes(soname='libc.so.12'))
        (dest / 'usr/lib/libutil.so.7').write_bytes(
            elf_bytes(soname='libutil.so.7', needed=['libc.so.12']))
        (dest / 'libexec/ld.elf_so').write_bytes(elf_bytes())
        for root in ROOTS:
            path = dest / root.lstrip('/')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(elf_bytes(needed=['libutil.so.7'], executable=True))
            path.chmod(0o755)
        (dest / 'usr/bin/sha512').rename(dest / 'usr/bin/cksum')
        (dest / 'usr/bin/sha512').symlink_to('/usr/bin/cksum')
        (dest / 'bin/tar').unlink()
        (dest / 'bin/tar').symlink_to('../usr/bin/tar')
        return dest

    def audit_bootstrap(self, dest):
        return subprocess.run(['/usr/bin/ruby', str(self.auditor), str(dest), self.readelf],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, check=False)

    @staticmethod
    def replace_machine(path):
        data = bytearray(path.read_bytes())
        data[18:20] = struct.pack('<H', 183)
        path.write_bytes(data)

    @staticmethod
    def replace_link(path, target):
        path.unlink()
        path.symlink_to(target)

    @staticmethod
    def set_rpath(path, value):
        path.write_bytes(elf_bytes(needed=['libutil.so.7'], rpath=value, executable=True))
        path.chmod(0o755)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *_test_arguments])
