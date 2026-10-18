#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Authenticate the complete upstream native SDK.
import os
from pathlib import Path
import platform
import sys
sys.dont_write_bytecode = True
from llvm_host import checked_paths, extract_source, load_sdk, log_run, query


def prepare(args):
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import write_json
    if len(args) != 2:
        raise ValueError('Use ARCHIVE NEW_WORK')
    archive, work = args
    checked_paths(args)
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('This native SDK requires Darwin arm64')
    if sha256_file(archive) != '3dcfd88aec10be204a24037bcb0dc0ad777882e9dbe8ac60e2639060d8a794b1':
        raise ValueError('Pinned native SDK SHA256 differs')
    os.mkdir(work)
    write_json(work + '/inputs.json', {p: sha256_file(p) for p in (archive, __file__)})
    extract_source(archive, work)
    prefix = work + '/LLVM-23.1.3-macOS-ARM64'
    if query([prefix + '/bin/llvm-config', '--version']) != '23.1.3':
        raise ValueError('Unexpected LLVM version')
    outputs = {}
    for tool in ('llvm-tblgen', 'clang-tblgen'):
        version = query([prefix + '/bin/' + tool, '--version'])
        if 'LLVM version 23.1.3' not in version:
            raise ValueError('Unexpected generator version')
        outputs['bin/' + tool] = dict(version=version, sha256=sha256_file(prefix + '/bin/' + tool))
    for name in ('lib/libclang.dylib', 'lib/libclangHandleCXX.a', 'lib/libLTO.dylib', 'lib/cmake/llvm/LLVMConfig.cmake', 'lib/cmake/clang/ClangConfig.cmake'):
        if Path(prefix, name).stat().st_size == 0:
            raise ValueError('Empty SDK input: ' + name)
        outputs[name] = dict(sha256=sha256_file(os.path.realpath(prefix + '/' + name)))
    write_json(work + '/outputs.json', outputs)
    log_run(work + '/clang.version', [prefix + '/bin/clang', '--version'])
    log_run(work + '/libclang.dependencies', ['otool', '-L', prefix + '/lib/libclang.dylib'])
    print('Verified native LLVM/Clang SDK: ' + prefix)


if __name__ == '__main__':
    try:
        _, args = load_sdk()
        prepare(args)
    except Exception as error:
        sys.exit(f'FAIL: {error}')
