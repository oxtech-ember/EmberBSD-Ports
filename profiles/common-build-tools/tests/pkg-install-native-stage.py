#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise native-stage pkg_add using a real Darwin libcxx package."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('pkg-add', 'archive-tool', 'host-prefix', 'package', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
for value in vars(args).values():
    if not value.is_absolute():
        parser.error('all paths must be absolute')
env = {'PATH': str(args.host_prefix / 'bin') + ':' + str(args.host_prefix / 'sbin')}

def run(command, success=True):
    result = subprocess.run([str(x) for x in command], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if (result.returncode == 0) != success:
        raise AssertionError(result.stdout)
    return result.stdout

with tempfile.TemporaryDirectory(prefix='pkg-add-native-stage-', dir=args.work_dir) as tmp:
    work = Path(tmp)
    source = work / 'source'
    source.mkdir()
    listing = work / 'files'
    listing.write_text(run([args.archive_tool, '-tf', args.package]))
    run([args.archive_tool, '-xf', args.package, '-C', source])
    info = source / '+BUILD_INFO'
    original = info.read_text()
    assert 'OPSYS=Darwin\n' in original
    match = re.search(r'^MACHINE_ARCH=([^\n]+)$', original, re.M)
    assert match and match.group(1) in ('aarch64', 'x86_64')
    def archive(name, metadata):
        info.write_text(metadata)
        path = work / (name + '.tgz')
        run([args.archive_tool, '-czf', path, '-C', source, '-T', listing])
        return path
    foreign = archive('foreign', original.replace('OPSYS=Darwin\n', 'OPSYS=NetBSD\n')
                      .replace(match.group(0), 'MACHINE_ARCH=x86_64'))
    missing = archive('missing', original.replace(match.group(0) + '\n', ''))
    for name in ('plain', 'native', 'foreign', 'missing'):
        (work / name).mkdir()
    common = ['-K', args.host_prefix / 'pkgdb']
    assert 'missing required library' in run([args.pkg_add, *common, '-P', work / 'plain', args.package], False)
    run([args.pkg_add, *common, '-S', '-P', work / 'native', args.package])
    assert (work / 'native' / str(args.host_prefix).lstrip('/') /
            'lib/libc++/libc++_ember1.1.dylib').exists()
    foreign_platform = 'NetBSD/x86_64 27.0.0'
    assert 'missing required library' in run([args.pkg_add, *common, '-S', '-P', work / 'foreign',
                                              '-m', foreign_platform, foreign], False)
    run([args.pkg_add, *common, '-S', '-P', work / 'missing', missing], False)
    assert 'requires -P' in run([args.pkg_add, '-S', args.package], False)
    assert 'missing required library' in run([args.pkg_add, '-K', work / 'root-pkgdb', '-S', '-P', '/',
                                              '-m', foreign_platform, foreign], False)
print('native stage installation and foreign/metadata negatives PASS')
