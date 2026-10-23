#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Origin: EmberBSD contributors (AI-assisted). Adapt the native include-view helper.
"""Create a host include view with headers from the selected native LLVM SDK."""
import os
from pathlib import Path
import re
import sys


def prepare(host_include, llvm_include, overlay):
    paths = [host_include, llvm_include, overlay]
    if not all(re.fullmatch(r'/[A-Za-z0-9_./:-]+', value) for value in paths):
        raise ValueError('Use absolute paths without shell metacharacters')
    host, llvm, output = map(Path, paths)
    if not host.is_dir() or not all((llvm / name).is_dir() for name in ('llvm', 'llvm-c')):
        raise ValueError('Missing host or selected LLVM include directory')
    output.mkdir(parents=True, exist_ok=True)
    if output.is_symlink():
        raise ValueError('The include overlay must be a real directory')
    expected = {path.name: path for path in host.iterdir() if path.name not in ('llvm', 'llvm-c')}
    expected.update({name: llvm / name for name in ('llvm', 'llvm-c')})
    manifest = '.emberbsd-include-overlay.tsv'
    for path in output.iterdir():
        if path.name != manifest and path.name not in expected:
            raise ValueError('Unexpected include overlay entry: ' + str(path))
    for name, source in sorted(expected.items()):
        destination = output / name
        if os.path.lexists(destination):
            if not destination.is_symlink() or os.readlink(destination) != str(source):
                raise ValueError('Unexpected include overlay entry: ' + str(destination))
        else:
            destination.symlink_to(source)
    data = ''.join(name + '\t' + str(source) + '\n' for name, source in sorted(expected.items()))
    path = output / manifest
    if os.path.lexists(path):
        if path.is_symlink() or not path.is_file() or path.read_text() != data:
            raise ValueError('Changed include overlay manifest')
    else:
        with path.open('x') as stream:
            stream.write(data)
    return str(path)


if __name__ == '__main__':
    try:
        if len(sys.argv) != 4:
            raise ValueError('Use HOST_INCLUDE LLVM_INCLUDE NEW_OR_EXISTING_OVERLAY')
        prepare(*sys.argv[1:])
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
