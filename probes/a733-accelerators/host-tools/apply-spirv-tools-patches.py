#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Origin: EmberBSD contributors (AI-assisted). Port of the checked Ruby helper.
"""Apply only the reviewed SPIRV-Tools function-order change."""
import hashlib
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'pkgsrc/lang/llvm/files'))
import sdk_source

PIN = 'ef96ed763b43b59b33b31b362f09a02b729fa1c9'
ORIGINAL = 'e28e267843867c9818303022b1ba8e33b6c9eb5a710d20d92b687d0b7ddc9620'
PATCHED = '74ee3b81eea4054aec67d0870171a31483834b8d5d39c9778b20b28f8e99855f'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def apply(arguments):
    from emberbsd_sdk.process import capture
    if len(arguments) != 1:
        raise ValueError('Use apply-spirv-tools-patches.py --sdk-source SDK SOURCE')
    source = Path(arguments[0]).resolve(strict=True)
    patch = Path(__file__).with_name('spirv-tools-2026.4-function-order.patch')
    target = source / 'source/link/linker.cpp'

    def git(*arguments):
        return capture(['git', '-C', str(source), *map(str, arguments)]).stdout.decode('utf-8')

    if git('rev-parse', 'HEAD').strip() != PIN:
        raise ValueError('Wrong SPIRV-Tools revision')
    status = git('status', '--porcelain')
    before = digest(target)
    if before == ORIGINAL:
        if status:
            raise ValueError('SPIRV-Tools source is not clean')
        git('apply', '--check', patch)
        git('apply', patch)
    elif before == PATCHED:
        if status != ' M source/link/linker.cpp\n':
            raise ValueError('Unrelated SPIRV-Tools source changes')
    else:
        raise ValueError('Unexpected linker source hash')
    if digest(target) != PATCHED:
        raise ValueError('Patched linker hash mismatch')
    print(f'SPIRV-Tools {PIN}: stable function order; patch SHA256 {digest(patch)}')


if __name__ == '__main__':
    sdk_source.install_signal_handlers()
    try:
        if sys.version_info[:2] != (3, 15):
            raise ValueError('Host Python 3.15 is required')
        _, arguments = sdk_source.load_sdk()
        apply(arguments)
    except Exception as error:
        sdk_source.exit_error(error)
