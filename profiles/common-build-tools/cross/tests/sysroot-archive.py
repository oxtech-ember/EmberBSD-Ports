#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import hashlib
import lzma
import os
from pathlib import Path
import sys
import tarfile
import tempfile
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent / '../../pkgsrc/lang/llvm/files')]
from sdk_source import load_sdk
sdk, args = load_sdk()
from sysroot_archive import extract


def archive(path, entries, trailer=b''):
    raw = bytearray()
    for name, kind, data, target, mode in entries:
        entry = tarfile.TarInfo(name)
        entry.type, entry.linkname, entry.mode = kind, target, mode
        entry.size = len(data)
        raw.extend(entry.tobuf(format=tarfile.USTAR_FORMAT))
        raw.extend(data)
        raw.extend(bytes((-len(data)) % 512))
    raw.extend(bytes(1024))
    raw.extend(trailer)
    path.write_bytes(lzma.compress(bytes(raw)))
    return str(path)


def file(name, data=b'fixture', mode=0o644):
    return name, tarfile.REGTYPE, data, '', mode


def link(name, target, kind=tarfile.SYMTYPE, mode=0o755):
    return name, kind, b'', target, mode


checks = []
with tempfile.TemporaryDirectory(prefix='ember-sysroot-archive-') as temporary:
    work = Path(temporary)
    sentinel = work / 'outside-sentinel'
    sentinel.write_bytes(b'unchanged')
    before = sentinel.read_bytes()
    dirs = [(name, tarfile.DIRTYPE, b'', '', 0o755) for name in ('usr', 'usr/lib', 'usr/include', 'lib')]
    base = archive(work / 'base.tar.xz', dirs + [file('lib/libc.so.12.229', b'libc', 0o555), link('lib/libc.so.12', 'libc.so.12.229'),
        link('usr/lib/libc.so.12', '/lib/libc.so.12'), link('usr/lib/libproc.so', 'libproc.so.1.0')])
    comp = archive(work / 'comp.tar.xz', dirs + [file('usr/lib/libproc.so.1.0'), link('usr/lib/libproc.so', 'libproc.so.1.0'),
        file('usr/include/stdio.h', b'header', 0o444), link('usr/lib/crt-chain.o', 'usr/lib/crt-forward.o', tarfile.LNKTYPE),
        link('usr/lib/crt-forward.o', './usr/lib/crt0.o', tarfile.LNKTYPE), file('usr/lib/crt0.o', b'object'), link('usr/lib/libc.so', 'libc.so.12')])
    root = work / 'sysroot'
    old = os.umask(0o077)
    try:
        inventory = extract([base, comp], str(root))
    finally:
        os.umask(old)
    assert (root / 'lib/libc.so.12.229').read_bytes() == b'libc'
    assert (root / 'usr/include/stdio.h').stat().st_mode & 0o7777 == 0o444
    assert (root / 'usr/lib').stat().st_mode & 0o7777 == 0o755
    assert os.path.samefile(root / 'usr/lib/crt-chain.o', root / 'usr/lib/crt0.o')
    assert os.readlink(root / 'usr/lib/libc.so.12') == '../../lib/libc.so.12'
    assert (root / 'usr/lib/libc.so').read_bytes() == b'libc'
    assert inventory['usr/include/stdio.h'] == dict(type='file', mode=0o444, sha256=hashlib.sha256(b'header').hexdigest())
    checks.append('split sets preserve bytes modes aliases shared links and forward hardlinks')

    def refuse(label, entries=None, pattern='', archives=None, trailer=b'', destination=None):
        inputs = archives or [archive(work / (label + '.tar.xz'), entries or [], trailer)]
        try:
            extract(inputs, str(destination or work / ('reject-' + label)))
        except Exception as error:
            assert pattern.lower() in str(error).lower(), f'{label}: {error}'
            checks.append(label)
        else:
            raise AssertionError('Accepted invalid archive: ' + label)
        assert sentinel.read_bytes() == before

    refuse('traversal', [file('../outside-sentinel')], 'Unsafe archive member')
    refuse('absolute', [file(str(sentinel))], 'Unsafe archive member')
    for label, kind in [('file', tarfile.REGTYPE), ('link', tarfile.SYMTYPE), ('device', tarfile.CHRTYPE)]:
        refuse('root-' + label, [('.', kind, b'', '', 0o644)], 'root must be a directory')
    refuse('escape-relative-symlink', [link('usr/lib/escape', '../../../outside-sentinel')], 'link escapes')
    refuse('escape-absolute-symlink', [link('lib/escape', '/../../outside-sentinel')], 'link escapes')
    refuse('escape-relative-hardlink', [link('escape', '../outside-sentinel', tarfile.LNKTYPE)], 'Unsafe archive member')
    refuse('escape-absolute-hardlink', [link('escape', str(sentinel), tarfile.LNKTYPE)], 'Unsafe archive member')
    refuse('symlink-parent', [link('alias', '.'), link('alias/outside-link', '../outside-sentinel')], 'symlink parent')
    for label, entries in [('duplicate-file', [file('same'), file('same')]), ('duplicate-link', [link('same', 'target'), link('same', 'other')]), ('repeat-identical-link', [link('same', 'target'), link('same', 'target')])]:
        refuse(label, entries, 'Duplicate non-directory')
    for label, entries in [('duplicate-between-sets', [file('lib/libc.so.12.229')]), ('identical-file-between-sets', [file('lib/libc.so.12.229', b'libc', 0o555)]),
        ('shared-link-new-target', [link('usr/lib/libproc.so', 'other')]), ('shared-link-new-mode', [link('usr/lib/libproc.so', 'libproc.so.1.0', mode=0o777)]),
        ('repeat-shared-alias', [link('usr/lib/libproc.so', 'libproc.so.1.0'), link('usr/lib/libproc.so', 'libproc.so.1.0')])]:
        extra = archive(work / (label + '.tar.xz'), entries)
        refuse(label, pattern='Duplicate non-directory', archives=[base, extra])
    refuse('unresolved-hardlink', [link('alias', 'missing', tarfile.LNKTYPE)], 'Unresolved or cyclic')
    refuse('cyclic-hardlinks', [link('one', 'two', tarfile.LNKTYPE), link('two', 'one', tarfile.LNKTYPE)], 'Unresolved or cyclic')
    for kind in (tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE, tarfile.XHDTYPE):
        refuse('unsupported-' + kind.decode(), [('unsupported', kind, b'', '', 0o644)], 'Unsupported archive entry')
    corrupt = work / 'corrupt.tar.xz'
    data = bytearray(Path(comp).read_bytes())
    data[-1] ^= 255
    corrupt.write_bytes(data)
    refuse('corrupt-xz', pattern='xz failed', archives=[str(corrupt)])
    refuse('trailing-data', pattern='Nonzero data', trailer=b'x' * 262144)
    refuse('excessive-padding', pattern='Excessive trailing', trailer=bytes(2 * 1024 * 1024))
    refuse('existing-destination', pattern='fresh extraction', archives=[base], destination=root)
print(f'PASS: {len(checks)} archive extraction contracts; no target qualification')
