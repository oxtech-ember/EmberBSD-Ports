#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Apply the shared libXt patches to a pristine 1.3.1 archive.

The archive must be the distinfo-pinned libXt-1.3.1.tar.xz. Patch checksums
follow pkgsrc mk/checksum/distinfo.awk: lines containing $NetBSD are removed
before SHA1. Every patch must apply with zero fuzz. xt.pc.in must gain
Libs.private for the relocation helper and must keep the upstream Libs line.
"""
import argparse
import hashlib
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path

RECIPE = Path(__file__).resolve().parents[1]
RCS_LINE = re.compile(rb'^.*\$NetBSD.*\n', re.M)


def fail(message):
    raise SystemExit('FAIL: ' + message)


def pkgsrc_patch_sha1(path):
    return hashlib.sha1(RCS_LINE.sub(b'', path.read_bytes())).hexdigest()


def distinfo_fields(text):
    fields = {}
    for line in text.splitlines():
        if ' (' not in line or ' = ' not in line:
            continue
        kind, rest = line.split(' (', 1)
        name, value = rest.split(') = ', 1)
        fields[(kind, name)] = value.removesuffix(' bytes') if kind == 'Size' else value
    return fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('distfile', type=Path, help='absolute libXt-1.3.1.tar.xz pinned by distinfo')
    args = parser.parse_args()
    archive = args.distfile.resolve()
    if not archive.is_file():
        fail('distfile is not a file: ' + str(archive))
    info = distinfo_fields((RECIPE / 'distinfo').read_text())
    data = archive.read_bytes()
    checks = {
        'BLAKE2s': hashlib.blake2s(data).hexdigest(),
        'SHA512': hashlib.sha512(data).hexdigest(),
        'Size': str(len(data)),
    }
    for kind, actual in checks.items():
        recorded = info.get((kind, 'libXt-1.3.1.tar.xz'))
        if recorded != actual:
            fail(f'{kind} of the archive does not match distinfo')
    patches = sorted((RECIPE / 'patches').glob('patch-*'))
    if not patches:
        fail('the libXt recipe has no patches')
    for patch in patches:
        recorded = info.get(('SHA1', patch.name))
        if pkgsrc_patch_sha1(patch) != recorded:
            fail('distinfo SHA1 does not match ' + patch.name)
    with tempfile.TemporaryDirectory(prefix='libxt-clean-') as tmp:
        root = Path(tmp)
        with tarfile.open(archive) as tar:
            tar.extractall(root, filter='data')
        source = root / 'libXt-1.3.1'
        original = (source / 'xt.pc.in').read_text()
        if 'Libs: -L${libdir} -lXt\n' not in original or '-Wl,-rpath' in original:
            fail('the archive is not the pristine xt.pc.in this recipe patches')
        for patch in patches:
            completed = subprocess.run(
                ['patch', '--posix', '-p0', '-F0', '-V', 'none', '-i', str(patch)],
                cwd=source, text=True, capture_output=True)
            output = completed.stdout + completed.stderr
            if completed.returncode != 0 or 'FAILED' in output:
                fail(patch.name + ' did not apply:\n' + output)
            if patch.name == 'patch-xt.pc.in' and 'offset' in output:
                fail('patch-xt.pc.in applied away from its recorded lines:\n' + output)
        expected = original + '\nLibs.private: @X11_RELOC_DL_LIBS@\n'
        produced = (source / 'xt.pc.in').read_text()
        if produced != expected:
            fail('xt.pc.in did not keep the upstream Libs line and add Libs.private')
    print('PASS: pristine libXt 1.3.1 accepts every shared patch; xt.pc.in keeps upstream Libs')


if __name__ == '__main__':
    main()
