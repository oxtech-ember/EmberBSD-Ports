#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors.
"""Reject a valid archive with old runtime metadata and inspect provider boundaries."""
import importlib.util
from pathlib import Path
import sys
import tempfile

scripts = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(scripts))
import hashlib
from cross_bulk_provider import package_interface, provider_key

spec = importlib.util.spec_from_file_location('archive', scripts / 'cross-bulk-archive.py')
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    info = root / 'pkg_info'
    info.write_text('#!/bin/sh\ncat "$3"\n')
    info.chmod(0o700)
    # The selected pkg_info emits the archive or installed registration.
    name = 'qt6-qtbase-devel-6.12.0nb24'
    binary = root / 'binary'
    installed = root / 'db'
    required = root / 'resolved'
    manifest = '@name ' + name + '\n@pkgdep qt6-qtbase-6.12.0nb20\n'
    binary.write_text(manifest)
    installed.write_text(manifest)
    info.write_text('#!/bin/sh\ncase "$3" in /*) cat "$3" ;; *) cat "' + str(installed) + '" ;; esac\n')
    required.write_text('full\tqt6-qtbase-6.12.0nb21\tqt6-qtbase-6.12.0nb21\n')
    def refuse():
        try:
            archive.validate(binary, name, required, [str(info)])
        except ValueError:
            return
        raise AssertionError('accepted mismatched metadata')
    refuse()
    binary.write_text(manifest.replace('nb20', 'nb21'))
    refuse()
    installed.write_text(binary.read_text())
    archive.validate(binary, name, required, [str(info)])

build = 'OPSYS=NetBSD\nMACHINE_ARCH=aarch64\nLOCALBASE=/usr/pkg\nPKGPATH=graphics/freetype2\nPROVIDES=/usr/pkg/lib/libft.so.6\n'
zero = '0' * 32
def compare(name, *, header=zero, lib=zero, static=zero, read='identical-library', extra=''):
    contents = (f'@cwd /usr/pkg\n@name {name}\n@blddep bzip2-1\n@pkgdep bzip2>=1\n'
                f'include/ft.h\n@comment MD5:{header}\nlib/libft.a\n@comment MD5:{static}\n'
                f'lib/libft.so.6\n@comment MD5:{lib}\n@cwd /usr/pkg\n@ignore\n+BUILD_INFO\n')
    return package_interface(name, (contents + extra).encode(), build,
                             lambda path, md5: read, inspect_file=lambda path, md5: md5,
                             inspect_link=lambda path, target: None)
before = compare('ft-1.0nb1')
assert compare('ft-1.0nb2') == before
assert compare('ft-1.0.1') == before
assert compare('different-ft-1.0.1') != before
assert compare('ft-1.0.1', header='1'*32) != before
assert compare('ft-1.0nb2', static='1'*32) != before
assert compare('ft-1.0nb2', read='unqualified-library') != before
try:
    compare('ft-1.0.1', extra='@exec record-install-state %D\n')
except ValueError as error:
    assert 'unclassified package directive' in str(error)
else:
    raise AssertionError('compared an unqualified installation command')

with tempfile.TemporaryDirectory() as folder:
    prefix = Path(folder)
    db, cache = prefix / 'pkgdb', prefix / 'cache'
    resolved = prefix / 'resolved'
    dso = prefix / 'lib/libft.so.6'
    dso.parent.mkdir()
    dso.write_bytes(b'\x7fELFfile-bytes')
    md5 = hashlib.md5(dso.read_bytes()).hexdigest()
    def select(name):
        resolved.write_text('full ft>=1 ' + name + '\n')
        pkg = db / name
        pkg.mkdir(parents=True)
        (pkg / '+CONTENTS').write_text(f'@cwd /usr/pkg\n@name {name}\nlib/libft.so.6\n@comment MD5:{md5}\n')
        (pkg / '+BUILD_INFO').write_text(build)
    def current():
        return provider_key(resolved, db, db, cache=cache)
    select('ft-1.0')
    initial = current()
    select('ft-1.0.1')
    assert current() == initial
    dso.chmod(0o700)
    assert current() != initial
    dso.write_bytes(b'\x7fELFdifferent')
    before_cache = set(cache.iterdir())
    for _ in range(2):
        try:
            current()
        except ValueError as error:
            assert 'differs from registered package' in str(error)
        else:
            raise AssertionError('trusted changed installed file')
        assert set(cache.iterdir()) == before_cache
print('PASS: exact Qt archive and installed requirements, provider revision, ELF, headers and static archives')
