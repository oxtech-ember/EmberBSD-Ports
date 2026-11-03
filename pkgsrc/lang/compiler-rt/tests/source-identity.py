#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check that prepared-source identity follows the producer's actual inputs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile


def sha1_patch(data):
    filtered = b''.join(line for line in data.splitlines(True) if b'$NetBSD' not in line)
    return hashlib.sha1(filtered).hexdigest()


def main():
    with tempfile.TemporaryDirectory(prefix='llvm-source-identity-') as tmp:
        root = Path(tmp) / 'ports'
        owner = root / 'pkgsrc/lang/compiler-rt'
        pkgsrc = root / 'pkgsrc'
        llvm = pkgsrc / 'lang/llvm'
        (owner / 'files').mkdir(parents=True)
        (owner / 'patches').mkdir()
        (llvm / 'patches').mkdir(parents=True)
        source_code = Path(__file__).resolve().parents[1] / 'files/source.py'
        local_source = owner / 'files/source.py'
        local_source.write_bytes(source_code.read_bytes())
        (owner / 'files/profile_patch.py').write_bytes(
            (source_code.parent / 'profile_patch.py').read_bytes())
        (llvm / 'version.mk').write_text('LLVM_VERSION=23.0.0\n')
        (owner / 'files/source-components.json').write_text(
            '["compiler-rt/lib/builtins"]\n')

        archive = 'llvm-project-23.0.0.src.tar.xz'
        archive_sha512 = 'a' * 128
        archive_blake2s = 'b' * 64
        archive_size = 123
        cmake = b'--- cmake/module.cmake.orig\n+++ cmake/module.cmake\n@@ -1 +1 @@\n-old\n+new\n'
        unrelated = b'--- llvm/lib/ObjCopy/file.cpp.orig\n+++ llvm/lib/ObjCopy/file.cpp\n@@ -1 +1 @@\n-old\n+new\n'
        cmake_path = llvm / 'patches/patch-cmake-runtime'
        cmake_path.write_bytes(cmake)
        cmake_extra = b'--- cmake/extra.cmake.orig\n+++ cmake/extra.cmake\n@@ -1 +1 @@\n-old\n+new\n'
        cmake_extra_path = llvm / 'patches/patch-cmake-extra'
        cmake_extra_path.write_bytes(cmake_extra)
        llvm_distinfo = llvm / 'distinfo'
        package_distinfo = owner / 'distinfo'

        def write_distinfo(patches=(), sha512=archive_sha512):
            lines = [f'SHA512 ({archive}) = {sha512}',
                     f'BLAKE2s ({archive}) = {archive_blake2s}',
                     f'Size ({archive}) = {archive_size}']
            lines.extend(f'SHA1 ({name}) = {sha1_patch(data)}'
                         for name, data in patches)
            contents = '\n'.join(lines) + '\n'
            llvm_distinfo.write_text(contents)
            package_distinfo.write_text('\n'.join((
                f'SHA512 ({archive}) = {archive_sha512}',
                f'BLAKE2s ({archive}) = {archive_blake2s}',
                f'Size ({archive}) = {archive_size}')) + '\n')

        write_distinfo([('patch-cmake-runtime', cmake), ('patch-cmake-extra', cmake_extra)])

        spec = importlib.util.spec_from_file_location('source_identity_producer', local_source)
        producer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(producer)

        class SDKError(Exception):
            pass

        class Paths:
            @staticmethod
            def open_regular(path):
                return Path(path).open('rb'), None

            @staticmethod
            def verify_stable(path, before):
                return None

            @staticmethod
            def canonical_existing(path):
                return str(Path(path).resolve(strict=True))

        class JSONIO:
            @staticmethod
            def read_json(path):
                return json.loads(Path(path).read_text())

        producer.SDKError = SDKError
        producer.paths = Paths
        producer.jsonio = JSONIO
        producer.OWNER = owner.resolve()
        producer.PORTS = root.resolve()
        producer.DEFAULT_PKGSRC = pkgsrc.resolve()
        producer.PKGSRC = pkgsrc.resolve()
        producer.EXPORTED = True
        git = '/selected/git'
        initial, _ = producer.recipe(git)

        def verify(metadata, files=None):
            source = Path(tmp) / 'prepared'
            source.mkdir(exist_ok=True)
            recipe = dict(metadata['recipe'])
            if files is not None:
                recipe['files'] = files
            manifest = dict(format='emberbsd-llvm-source', version=2, **metadata,
                            tree_sha256='c' * 64)
            manifest['recipe'] = recipe
            (source / producer.SOURCE_MANIFEST).write_text(json.dumps(manifest))
            return producer.verify_source(source, git)

        baseline = verify(initial)
        legacy_files = dict(initial['recipe']['files'], **{
            'pkgsrc/lang/compiler-rt/files/source.py': 'old producer implementation',
            'pkgsrc/lang/llvm/distinfo': 'old broad patch inventory'})
        verify(initial, legacy_files)
        incompatible_legacy = dict(legacy_files)
        incompatible_legacy['pkgsrc/lang/llvm/patches/patch-cmake-runtime'] = '0' * 64
        try:
            verify(initial, incompatible_legacy)
        except SDKError as error:
            assert 'recipe inputs changed' in str(error)
        else:
            raise AssertionError('legacy compatibility accepted changed selected patch')
        incompatible_api = dict(initial)
        incompatible_api['recipe'] = dict(initial['recipe'], preparation_api=2)
        try:
            verify(incompatible_api)
        except SDKError as error:
            assert 'preparation API changed' in str(error)
        else:
            raise AssertionError('accepted a different preparation API')
        unrelated_path = llvm / 'patches/patch-objcopy-macho'
        unrelated_path.write_bytes(unrelated)
        write_distinfo([('patch-cmake-runtime', cmake), ('patch-cmake-extra', cmake_extra),
                        ('patch-objcopy-macho', unrelated)])
        with_unrelated, _ = producer.recipe(git)
        assert with_unrelated['recipe']['files'] == initial['recipe']['files']
        assert with_unrelated['source'] == initial['source']
        assert [path.name for path, subdir, _ in producer.recipe(git)[1]
                if subdir == 'llvm'] == ['patch-cmake-extra', 'patch-cmake-runtime']
        verify(with_unrelated)

        # The runtime verifier does not hash ignored source-tree content again.
        selected_change = cmake + b'# changed selected runtime patch\n'
        cmake_path.write_bytes(selected_change)
        write_distinfo([('patch-cmake-runtime', selected_change), ('patch-cmake-extra', cmake_extra),
                        ('patch-objcopy-macho', unrelated)])
        changed, _ = producer.recipe(git)
        assert changed['recipe']['files'] != initial['recipe']['files']
        try:
            verify(initial)
        except SDKError as error:
            assert 'recipe inputs changed' in str(error)
        else:
            raise AssertionError('accepted changed selected CMake patch')

        # Archive selection remains independently bound to the common hashes.
        write_distinfo([('patch-cmake-runtime', selected_change), ('patch-cmake-extra', cmake_extra),
                        ('patch-objcopy-macho', unrelated)], sha512='d' * 128)
        try:
            producer.recipe(git)
        except SDKError as error:
            assert 'archive selection differs' in str(error)
        else:
            raise AssertionError('accepted mismatched LLVM archive selection')

        # Selected patches still require their declared pkgsrc checksum.
        write_distinfo([('patch-cmake-runtime', selected_change), ('patch-cmake-extra', cmake_extra),
                        ('patch-objcopy-macho', unrelated)])
        bad_info = llvm_distinfo.read_text().replace(sha1_patch(selected_change), '0' * 40)
        llvm_distinfo.write_text(bad_info)
        try:
            producer.recipe(git)
        except SDKError as error:
            assert 'common LLVM patch checksum differs' in str(error)
        else:
            raise AssertionError('accepted bad selected patch checksum')

        # Strict patch-name inventory remains in force, including ignored files.
        (llvm / 'patches/patch-undeclared').write_bytes(unrelated)
        try:
            producer.recipe(git)
        except SDKError as error:
            assert 'undeclared or duplicate common LLVM patch' in str(error)
        else:
            raise AssertionError('accepted undeclared LLVM patch')
        assert baseline['source'] == initial['source']
    print('PASS: relevant LLVM source identity, selected patch/archive integrity, strict inventory')


if __name__ == '__main__':
    main()
