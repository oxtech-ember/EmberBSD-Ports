#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Apply the shared libXt patches to a pristine 1.3.1 archive.

The archive must be the distinfo-pinned libXt-1.3.1.tar.xz. Patch checksums
follow pkgsrc mk/checksum/distinfo.awk: lines containing $NetBSD are removed
before SHA1. Every patch must apply with GNU patch at zero fuzz (-F0).
Darwin patch rejects --posix, so the tool is EMBERBSD_TEST_GPATCH, gpatch,
or a patch binary that reports itself as GNU patch. xt.pc.in must gain
Libs.private for the relocation helper and must keep the upstream Libs line.
"""
import argparse
import hashlib
import os
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


def patch_reports_gnu(command):
    completed = subprocess.run([str(command), '--version'], text=True, capture_output=True)
    return 'GNU patch' in completed.stdout + completed.stderr


def gnu_patch_executable(explicit=None, search=None):
    """Return GNU patch, never BSD or Darwin patch.

    An explicit --patch or EMBERBSD_TEST_GPATCH value is used as given and
    must report itself as GNU patch. Otherwise prefer gpatch, the name used
    where patch is the BSD tool, then a patch binary that reports GNU patch.
    The caller keeps zero fuzz with -F0. BSD patch rejects --posix.
    """
    if explicit is None and search is None:
        explicit = os.environ.get('EMBERBSD_TEST_GPATCH') or None
    if explicit:
        if not patch_reports_gnu(explicit):
            fail('GNU patch is required, not ' + str(explicit))
        return str(explicit)
    directories = search
    if directories is None:
        directories = os.environ.get('PATH', '').split(os.pathsep)
    for name in ('gpatch', 'patch'):
        for directory in directories:
            if not directory:
                continue
            candidate = Path(directory) / name
            if candidate.is_file() and os.access(candidate, os.X_OK) and patch_reports_gnu(candidate):
                return str(candidate)
    fail('GNU patch is required; set EMBERBSD_TEST_GPATCH or install gpatch')


def check_patch_tool():
    """BSD/Darwin patch rejects --posix. Selection must be an explicit GNU
    patch, gpatch on PATH, or a patch binary that reports itself as GNU patch.
    """
    with tempfile.TemporaryDirectory(prefix='libxt-patch-') as tmp:
        root = Path(tmp)
        bsd = root / 'bsd'
        gnu = root / 'gnu'
        bsd.mkdir()
        gnu.mkdir()
        (bsd / 'patch').write_text(
            '#!/bin/sh\n'
            'if [ "$1" = --version ]; then echo "patch 2.0-12u11 FreeBSD"; exit 0; fi\n'
            'echo "patch: unrecognized option --posix" >&2\nexit 2\n')
        (gnu / 'gpatch').write_text(
            '#!/bin/sh\n'
            'if [ "$1" = --version ]; then echo "GNU patch 2.7.6"; exit 0; fi\n'
            'exit 0\n')
        (bsd / 'patch').chmod(0o755)
        (gnu / 'gpatch').chmod(0o755)
        selected = gnu_patch_executable(search=[str(bsd), str(gnu)])
        if Path(selected).name != 'gpatch':
            fail('BSD patch was selected ahead of gpatch: ' + selected)
        explicit = gnu / 'gpatch'
        selected = gnu_patch_executable(explicit, search=[str(bsd)])
        if selected != str(explicit):
            fail('explicit GNU patch was ignored: ' + selected)
        try:
            gnu_patch_executable(bsd / 'patch', search=[str(gnu)])
        except SystemExit as error:
            if 'GNU patch' not in str(error):
                raise
        else:
            fail('an explicit BSD patch was accepted')
        (gnu / 'patch').write_text((gnu / 'gpatch').read_text())
        (gnu / 'patch').chmod(0o755)
        (gnu / 'gpatch').unlink()
        selected = gnu_patch_executable(search=[str(gnu), str(bsd)])
        if Path(selected).name != 'patch' or 'gnu' not in selected:
            fail('GNU patch was not the fallback when gpatch is absent: ' + selected)
    print('PASS: libXt patch check selects GNU patch and refuses BSD patch --posix')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('distfile', nargs='?', type=Path,
                        help='absolute libXt-1.3.1.tar.xz pinned by distinfo')
    parser.add_argument('--patch', type=Path,
                        help='GNU patch or gpatch; default is EMBERBSD_TEST_GPATCH, then gpatch, then GNU patch')
    parser.add_argument('--check-patch-tool', action='store_true',
                        help='check GNU patch selection without a distfile')
    args = parser.parse_args()
    if args.check_patch_tool:
        check_patch_tool()
        return
    if args.distfile is None:
        fail('distfile is required unless --check-patch-tool is set')
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
        patch_tool = gnu_patch_executable(args.patch)
        for patch in patches:
            completed = subprocess.run(
                [patch_tool, '--posix', '-p0', '-F0', '-V', 'none', '-i', str(patch)],
                cwd=source, text=True, capture_output=True)
            output = completed.stdout + completed.stderr
            if completed.returncode != 0 or 'FAILED' in output or 'fuzz' in output.lower():
                fail(patch.name + ' did not apply with zero fuzz:\n' + output)
            if patch.name == 'patch-xt.pc.in' and 'offset' in output:
                fail('patch-xt.pc.in applied away from its recorded lines:\n' + output)
        expected = original + '\nLibs.private: @X11_RELOC_DL_LIBS@\n'
        produced = (source / 'xt.pc.in').read_text()
        if produced != expected:
            fail('xt.pc.in did not keep the upstream Libs line and add Libs.private')
    print('PASS: pristine libXt 1.3.1 accepts every shared patch; xt.pc.in keeps upstream Libs')


if __name__ == '__main__':
    main()
