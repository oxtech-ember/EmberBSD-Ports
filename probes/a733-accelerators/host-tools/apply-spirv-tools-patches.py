#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Origin: EmberBSD contributors (AI-assisted). Port of the checked Ruby helper.
"""Apply only the reviewed shared SPIRV-Tools source patches."""
import hashlib
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'pkgsrc/lang/llvm/files'))
import sdk_source

PIN = 'ef96ed763b43b59b33b31b362f09a02b729fa1c9'
ORIGINAL = 'e28e267843867c9818303022b1ba8e33b6c9eb5a710d20d92b687d0b7ddc9620'
PATCHED = '74ee3b81eea4054aec67d0870171a31483834b8d5d39c9778b20b28f8e99855f'
TARGETS = {
    'CMakeLists.txt': ('131cec6c419d333531d280e82e3097bfc3ba721c1891d5c8e0092388f400be71',
                       'c3d589db75fbfe39fc6653ea937576c8c31725fd68c2b2623165a79add4212d6', 'patch-installed-gtest'),
    'external/CMakeLists.txt': ('c5b11328d54ced5ad055f3060f89ababd9466ac20f5aab6c7d3cd9662230879a',
                                'ad85b3b84a220a58fcb8815d2260a176b896d0ad14982269e54b3ed44cb18a35', 'patch-installed-gtest'),
    'source/link/linker.cpp': (ORIGINAL, PATCHED, 'patch-source_link_linker.cpp'),
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def apply(arguments):
    from emberbsd_sdk.process import capture
    if len(arguments) != 1:
        raise ValueError('Use apply-spirv-tools-patches.py --sdk-source SDK SOURCE')
    source = Path(arguments[0]).resolve(strict=True)
    patches = Path(__file__).resolve().parents[3] / 'pkgsrc/parallel/spirv-tools/patches'

    def git(*arguments):
        return capture(['git', '-C', str(source), *map(str, arguments)]).stdout.decode('utf-8')

    if git('rev-parse', 'HEAD').strip() != PIN:
        raise ValueError('Wrong SPIRV-Tools revision')
    modified, pending = [], []
    for name, (original, patched, patch) in TARGETS.items():
        target = source / name
        if target.is_symlink() or not target.is_file() or target.stat().st_mode & 0o111:
            raise ValueError('Unexpected SPIRV-Tools source node or mode: ' + name)
        before = digest(target)
        if before == original:
            pending.append((name, patches / patch))
        elif before == patched:
            modified.append(name)
        else:
            raise ValueError('Unexpected SPIRV-Tools source hash: ' + name)
    # A known subset can remain after interruption. Reject all other changes.
    expected = ''.join(' M ' + name + '\n' for name in sorted(modified))
    if git('status', '--porcelain', '--untracked-files=all') != expected or git('diff', '--summary'):
        raise ValueError('Unrelated SPIRV-Tools source changes')
    for name, patch in pending:
        git('apply', '--check', '-p0', '--include=' + name, patch)
    for name, patch in pending:
        git('apply', '-p0', '--include=' + name, patch)
    if any(digest(source / name) != values[1] for name, values in TARGETS.items()):
        raise ValueError('Patched SPIRV-Tools source hash mismatch')
    expected = ''.join(' M ' + name + '\n' for name in sorted(TARGETS))
    if git('status', '--porcelain', '--untracked-files=all') != expected or git('diff', '--summary'):
        raise ValueError('Unexpected final SPIRV-Tools source state')
    hashes = ', '.join(name + '=' + digest(patches / name) for name in sorted({v[2] for v in TARGETS.values()}))
    print(f'SPIRV-Tools {PIN}: shared source patches; SHA256 {hashes}')


if __name__ == '__main__':
    sdk_source.install_signal_handlers()
    try:
        if sys.version_info[:2] != (3, 15):
            raise ValueError('Host Python 3.15 is required')
        _, arguments = sdk_source.load_sdk()
        apply(arguments)
    except Exception as error:
        sdk_source.exit_error(error)
