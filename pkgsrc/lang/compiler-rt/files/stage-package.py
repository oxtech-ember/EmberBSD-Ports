#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compose one pkgsrc role from the shared LLVM full runtime stage."""
import argparse
import os
import re
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "llvm/files"))
import sdk_source

sdk_source.load_sdk()
from emberbsd_sdk import llvm_runtime, inventory, application_toolchain
from emberbsd_sdk.elf import read_elf_dynamic

NAMES = {'libcxx': 'libc++', 'libcxxabi': 'libc++abi', 'libunwind': 'libunwind'}

def select(record, component, role):
    prefix = record['prefix'] + '/'
    if prefix != 'usr/pkg/llvm/':
        raise ValueError('runtime prefix must be usr/pkg/llvm')
    name = NAMES[component]
    paths = sorted(set(record['files']) | set(record['symlinks']))
    if role == 'runtime':
        selected = [prefix + 'lib/' + name + '.so.1', record['artifacts'][component]['shared'],
                    prefix + 'share/licenses/' + component + '/LICENSE.TXT']
    else:
        selected = [prefix + 'lib/' + name + '.a', prefix + 'lib/' + name + '.so']
        if component == 'libcxx':
            selected += [p for p in paths if p.startswith(prefix + 'include/c++/') and p.rsplit('/', 1)[-1] not in ('cxxabi.h', '__cxxabi_config.h')]
            selected += [p for p in paths if p.startswith(prefix + 'lib/libc++experimental.') or p == prefix + 'lib/libc++.modules.json']
        elif component == 'libcxxabi':
            selected += [prefix + 'include/c++/v1/cxxabi.h', prefix + 'include/c++/v1/__cxxabi_config.h']
        elif component == 'libunwind':
            selected += [p for p in paths if p.startswith(prefix + 'include/') and not p.startswith(prefix + 'include/c++/')]
    if not selected or any(p not in paths for p in selected):
        raise ValueError('required component files are missing')
    return sorted(set(p.removeprefix('usr/pkg/') for p in selected))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('plist', 'install'))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--stage'); source.add_argument('--sysroot')
    parser.add_argument('--base')
    parser.add_argument('--pkgsrc-root', required=True)
    parser.add_argument('--target', choices=('amd64','aarch64'), required=True)
    parser.add_argument('--component', choices=tuple(NAMES), required=True)
    parser.add_argument('--role', choices=('runtime','devel'), required=True)
    parser.add_argument('--destdir')
    args = parser.parse_args()
    if args.stage:
        if not args.base: raise ValueError('stage requires --base')
        runtime_root = args.stage
        record = llvm_runtime.validate_stage(args.stage, target=args.target,
            required_components=llvm_runtime.FULL_COMPONENTS, base=args.base)
    else:
        runtime_root = args.sysroot
        record = application_toolchain.load_clang_runtime(args.sysroot, target=args.target)
    ports = Path(args.pkgsrc_root).resolve(strict=True)
    version = re.search(r'^LLVM_VERSION=\s*(\S+)', (ports / 'lang/llvm/version.mk').read_text(), re.M)
    if not version or record['compiler_family'] != 'clang' or record['llvm_version'] != version.group(1):
        raise ValueError('stage compiler or LLVM version differs')
    distinfo = (ports / 'lang/llvm/distinfo').read_text()
    archive = record['source']
    if 'SHA512 (' + archive['archive'] + ') = ' + archive['sha512'] not in distinfo.splitlines():
        raise ValueError('LLVM source archive differs')
    # Compare patches affecting the packaged runtimes, not unrelated builtins,
    # test drivers, version allowlists or historical producer implementation.
    relevant = {}
    for directory in ('lang/compiler-rt/patches', 'lang/llvm/patches'):
        for path in (ports / directory).glob('patch-*'):
            body = path.read_text()
            if any(line.startswith(('--- ', '+++ ')) and any(marker in line for marker in
                    ('cmake/', 'libunwind/', 'libcxx/', 'libcxxabi/'))
                   for line in body.splitlines()):
                relevant['pkgsrc/' + str(path.relative_to(ports))] = inventory.sha256_file(str(path))
    for name in record['recipe']['files']:
        if '/patches/' in name and not (ports / name.removeprefix('pkgsrc/')).is_file():
            raise ValueError('recorded producer patch is missing: ' + name)
    recorded = {name: digest for name, digest in record['recipe']['files'].items()
                if '/patches/' in name and name in relevant}
    if relevant != recorded:
        raise ValueError('runtime-relevant source patches differ')
    dynamic = read_elf_dynamic(str(Path(runtime_root) / record['artifacts'][args.component]['shared']), machine=record['elf_machine'])
    allowed = {'libc.so.12', 'libm.so.0', 'libpthread.so.1', 'librt.so.1',
               'libc++.so.1', 'libc++abi.so.1', 'libunwind.so.1'}
    required = {'libcxx': {'libc++abi.so.1', 'libunwind.so.1'},
                'libcxxabi': {'libunwind.so.1'}, 'libunwind': set()}[args.component]
    if set(dynamic['needed']) - allowed or not required <= set(dynamic['needed']):
        raise ValueError('runtime dependency closure differs: ' + repr(dynamic['needed']))
    if dynamic['soname'] != NAMES[args.component] + '.so.1' or dynamic['runpath'] != '/usr/pkg/llvm/lib':
        raise ValueError('runtime SONAME or search path differs')
    files = select(record, args.component, args.role)
    if args.operation == 'plist':
        print('\n'.join(files)); return
    if not args.destdir or not os.path.isabs(args.destdir):
        raise ValueError('absolute DESTDIR required')
    root = Path(args.destdir) / 'usr/pkg'
    for path in files:
        source = Path(runtime_root) / 'usr/pkg' / path
        dest = root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if os.path.lexists(dest): raise ValueError('destination exists: ' + str(dest))
        if source.is_symlink(): os.symlink(os.readlink(source), dest)
        else: shutil.copy2(source, dest)

if __name__ == '__main__':
    try: main()
    except (ValueError, OSError) as error: sys.exit(str(error))
