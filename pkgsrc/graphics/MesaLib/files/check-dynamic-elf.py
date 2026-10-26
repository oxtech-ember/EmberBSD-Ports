#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Reject known unsupported NetBSD Mesa dynamic ELF relocation contracts."""
import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode = True
MACHINES = {'x86_64': 62, 'aarch64': 183}
X86_TLSDESC = {34, 35, 36}
SCOPE = 'Known NetBSD dynamic TLS incompatibility only; not runtime admission'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_elf_api(sdk_source):
    selector = Path(__file__).resolve().parents[3] / 'lang/llvm/files/sdk_source.py'
    require(selector.is_file(), 'missing shared SDK source selector')
    spec = importlib.util.spec_from_file_location('_mesa_dynamic_sdk_source', selector)
    require(spec is not None and spec.loader is not None, 'cannot load shared SDK source selector')
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    selected, remaining = loader.load_sdk(['--sdk-source', str(sdk_source)])
    require(not remaining, 'unexpected SDK selector arguments')
    api = importlib.import_module('emberbsd_sdk.elf')
    paths = importlib.import_module('emberbsd_sdk.paths')
    package = Path(selected) / 'src/emberbsd_sdk'
    require(Path(api.__file__).resolve().is_relative_to(package.resolve()) and
            type(getattr(api, 'ELF_RELOCATIONS_API', None)) is int and
            api.ELF_RELOCATIONS_API == 1 and
            callable(getattr(api, 'read_elf_relocations', None)) and
            callable(getattr(api, 'read_elf_dynamic', None)) and
            Path(paths.__file__).resolve().is_relative_to(package.resolve()) and
            all(callable(getattr(paths, name, None)) for name in
                ('regular_file', 'open_regular', 'verify_stable')),
            'selected SDK lacks ELF_RELOCATIONS_API=1 and dynamic ELF readers')
    return api, paths


def regular_files(root):
    require(root.is_absolute(), '--library-dir must be absolute')
    require(stat.S_ISDIR(root.lstat().st_mode) and root.resolve(strict=True) == root,
            'library directory must be a real directory without symlink ancestors')
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            path = Path(entry.path)
            mode = entry.stat(follow_symlinks=False).st_mode
            if stat.S_ISLNK(mode):
                target = path.resolve(strict=False)
                require(target.is_relative_to(root) or not target.is_dir(),
                        'directory symlink escapes staged library directory: ' + str(path))
                continue
            if stat.S_ISDIR(mode):
                pending.append(path)
            elif stat.S_ISREG(mode):
                yield path


def check_policy(scan, arch):
    require(scan.get('class') == 64 and scan.get('endian') == 'little' and
            scan.get('machine') == MACHINES[arch] and scan.get('type') == 3,
            'staged ELF is not an ELF64LE shared object for ' + arch)
    if arch == 'x86_64':
        forbidden = sorted(set(scan['types']) & X86_TLSDESC)
        require(not forbidden and scan['tlsdesc']['plt'] is None and scan['tlsdesc']['got'] is None,
                'unsupported NetBSD x86_64 TLSDESC: relocation types=' + str(forbidden) +
                ', dynamic tags=' + str(scan['tlsdesc']))


def inspect_libraries(root, arch, api, paths):
    results = []
    for path in regular_files(root):
        before = paths.regular_file(path)
        stream, _ = paths.open_regular(path)
        with stream:
            magic = stream.read(4)
        if magic != b'\x7fELF':
            paths.verify_stable(path, before)
            require('.so' not in path.name, 'non-ELF staged DSO: ' + str(path))
            continue
        dynamic = api.read_elf_dynamic(path, machine=MACHINES[arch])
        require(dynamic.get('class') == 64 and dynamic.get('endian') == 'little' and
                dynamic.get('machine') == MACHINES[arch] and dynamic.get('type') == 3,
                'staged ELF is not an ELF64LE shared object for ' + arch + ': ' + str(path))
        scan = api.read_elf_relocations(path, machine=MACHINES[arch])
        try:
            check_policy(scan, arch)
        except ValueError as error:
            raise ValueError(str(path) + ': ' + str(error)) from error
        stream, _ = paths.open_regular(path)
        with stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        paths.verify_stable(path, before)
        results.append({'path': path.relative_to(root).as_posix(), 'sha256': digest,
                        'size': before.st_size, 'relocations': scan})
    require(results, 'no regular ELF shared objects in staged library directory')
    return sorted(results, key=lambda result: result['path'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True, type=Path)
    parser.add_argument('--arch', required=True, choices=tuple(MACHINES))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-sdk', action='store_true')
    mode.add_argument('--library-dir', type=Path)
    args = parser.parse_args()
    try:
        require(args.sdk_source.is_absolute(), '--sdk-source must be absolute')
        api, paths = load_elf_api(args.sdk_source)
        result = {'check': 'Mesa dynamic ELF', 'arch': args.arch,
                  'elf_relocations_api': api.ELF_RELOCATIONS_API, 'scope': SCOPE}
        if args.check_sdk:
            result['mode'] = 'sdk-capability'
        else:
            result['mode'] = 'staged-libraries'
            result['libraries'] = inspect_libraries(args.library_dir, args.arch, api, paths)
        print(json.dumps(result, sort_keys=True))
    except Exception as error:
        print('FAIL: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
