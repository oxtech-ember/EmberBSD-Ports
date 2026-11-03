#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Select an audited LLVM staging partition.
import os
from pathlib import Path
import re
import shutil
import stat
import sys
sys.dont_write_bytecode = True
from sdk_source import load_sdk


def manifest(path):
    from emberbsd_sdk.paths import regular_file
    regular_file(path)
    result = set()
    for name in Path(path).read_text().splitlines():
        if not name or re.match(r'^@comment(?: |$)', name):
            continue
        if (re.search(r'[\x00-\x20\x7f]', name) or name.startswith(('/', '@')) or name.endswith('/')
                or '${' in name or any(p in ('', '.', '..') for p in name.split('/'))):
            raise ValueError(f'unsafe manifest entry: {name}')
        if name in result:
            raise ValueError(f'duplicate manifest entry: {name}')
        result.add(name)
    if not result:
        raise ValueError('empty LLVM partition')
    return result


def select(part, stage, *lists):
    full, runtime, devel, wanted, actual, directories = validate(part, stage, *lists)
    if part != 'check':
        for name in sorted(actual - wanted):
            os.unlink(os.path.join(stage, name))
        for directory in sorted(directories, key=lambda p: p.count('/'), reverse=True):
            if not os.listdir(directory):
                os.rmdir(directory)
    print(f'PASS: complete LLVM stage has an exhaustive, disjoint {part} partition')


def validate(part, stage, *lists):
    from emberbsd_sdk.paths import real_directory
    if part not in ('runtime', 'devel', 'check') or len(lists) != 4:
        raise ValueError('unknown LLVM package part or manifest count')
    if not os.path.isabs(stage) or stage == '/':
        raise ValueError('absolute regular staging directory required')
    real_directory(stage)
    full, runtime, devel, selected = map(manifest, lists)
    if runtime & devel:
        raise ValueError('LLVM partitions overlap')
    if runtime | devel != full:
        raise ValueError('LLVM partition union differs from the complete PLIST')
    wanted = {'check': full, 'runtime': runtime, 'devel': devel}[part]
    if wanted != selected:
        raise ValueError('selected package PLIST differs from its declared partition')
    actual, directories = set(), []
    for parent, dirs, files in os.walk(stage, followlinks=False):
        for name in dirs + files:
            path = os.path.join(parent, name)
            relative = os.path.relpath(path, stage)
            mode = os.lstat(path).st_mode
            if stat.S_ISLNK(mode) or stat.S_ISREG(mode):
                if relative not in full:
                    raise ValueError(f'unlisted staged file: {relative}')
                actual.add(relative)
            elif stat.S_ISDIR(mode):
                directories.append(path)
            else:
                raise ValueError(f'unsupported staged file type: {relative}')
    if full - actual:
        raise ValueError('missing complete-stage file: ' + sorted(full - actual)[0])
    # Resolve each link component before pruning. Runtime links cannot use SDK.
    for name in sorted(actual):
        if not os.path.islink(os.path.join(stage, name)):
            continue
        todo, resolved, hops = name.split('/'), [], 0
        while todo:
            component = todo.pop(0)
            if component in ('', '.'):
                continue
            if component == '..':
                if not resolved:
                    raise ValueError(f'escaping LLVM stage link: {name}')
                resolved.pop()
                continue
            relative = '/'.join(resolved + [component])
            path = os.path.join(stage, relative)
            if os.path.islink(path):
                hops += 1
                if hops > 64:
                    raise ValueError(f'cyclic or excessive LLVM stage link: {name}')
                if name in runtime and relative not in runtime:
                    raise ValueError(f'runtime link uses SDK: {name} -> {relative}')
                target = os.readlink(path)
                if not target or re.search(r'[\x00-\x20\x7f]', target) or target.endswith('/') or os.path.isabs(target):
                    raise ValueError(f'unsafe LLVM stage link: {name}')
                todo[:0] = target.split('/')
                continue
            if not os.path.exists(path):
                raise ValueError(f'missing LLVM stage link target: {name}')
            if todo and not os.path.isdir(path):
                raise ValueError(f'non-directory LLVM link component: {name}')
            resolved.append(component)
        terminal = '/'.join(resolved)
        if terminal not in actual or not os.path.isfile(os.path.join(stage, terminal)):
            raise ValueError(f'LLVM stage link does not resolve to a listed file: {name}')
        if name in runtime and terminal not in runtime:
            raise ValueError(f'runtime link resolves to SDK: {name} -> {terminal}')
    return full, runtime, devel, wanted, actual, directories


def copy_entries(source, destination, entries):
    for name in sorted(entries):
        src, dst = os.path.join(source, name), os.path.join(destination, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
        else:
            shutil.copy2(src, dst)


def check_empty_destination(destination, entries):
    allowed = set()
    for entry in entries:
        parts = entry.split('/')
        allowed.update('/'.join(parts[:index]) for index in range(1, len(parts)))
    for parent, dirs, files in os.walk(destination, followlinks=False):
        for name in dirs:
            path = os.path.join(parent, name)
            relative = os.path.relpath(path, destination)
            if os.path.islink(path) or not os.path.isdir(path):
                raise ValueError(f'unsafe pre-created LLVM SDK directory: {relative}')
            if relative not in allowed:
                raise ValueError(f'unlisted pre-created LLVM SDK directory: {relative}')
        if files:
            raise ValueError(f'non-empty LLVM SDK destination: {os.path.relpath(os.path.join(parent, files[0]), destination)}')


def handoff_runtime(stage, *args):
    from emberbsd_sdk.paths import canonical_existing, canonical_new, real_directory, reject_overlap
    if len(args) != 5:
        raise ValueError('runtime handoff requires four manifests and a shared stage')
    full_plist, runtime_plist, devel_plist, selected_plist, shared = args
    full, runtime, _, _, actual, _ = validate('runtime', stage, full_plist, runtime_plist,
                                               devel_plist, selected_plist)
    if not os.path.isabs(shared) or shared == '/':
        raise ValueError('absolute LLVM shared stage path required')
    stage = canonical_existing(stage)
    # Refuse a symlink at the retained path before resolving ancestors.
    if os.path.lexists(shared):
        real_directory(shared)
    shared = canonical_new(shared)
    if shared == '/':
        raise ValueError('LLVM shared stage cannot be the filesystem root')
    reject_overlap(stage, shared)
    if os.path.lexists(shared):
        real_directory(shared)
        # The fresh full installation was validated above.  The replaced tree
        # need not match its new manifest or contain the same file bytes.
        shutil.rmtree(shared)
    os.rename(stage, shared)
    os.makedirs(stage)
    copy_entries(shared, stage, runtime)
    print(f'PASS: retained fresh complete LLVM stage and copied runtime partition ({len(actual)} files)')


def copy_devel(shared, destination, *lists):
    from emberbsd_sdk.paths import canonical_existing, canonical_new, real_directory, reject_overlap
    if len(lists) != 4:
        raise ValueError('SDK copy requires four manifests')
    full_plist, runtime_plist, devel_plist, selected_plist = lists
    shared = canonical_existing(shared)
    destination = canonical_new(destination)
    reject_overlap(shared, destination)
    _, _, devel, _, actual, _ = validate('check', shared, full_plist, runtime_plist,
                                          devel_plist, full_plist)
    selected = manifest(selected_plist)
    if selected != devel:
        raise ValueError('selected package PLIST differs from its declared partition')
    # pkgsrc may have created empty PLIST directories before do-install.
    os.makedirs(destination, exist_ok=True)
    real_directory(destination)
    check_empty_destination(destination, devel)
    copy_entries(shared, destination, devel)
    print(f'PASS: copied SDK partition from retained full LLVM stage ({len(actual)} source files)')


if __name__ == '__main__':
    from sdk_source import exit_error, install_signal_handlers
    install_signal_handlers()
    try:
        _, args = load_sdk()
        if args and args[0] == 'handoff-runtime':
            if len(args) != 7:
                raise ValueError('usage: select-package-stage.py handoff-runtime STAGE FULL_PLIST RUNTIME_PLIST DEVEL_PLIST SELECTED_PLIST SHARED_STAGE')
            handoff_runtime(*args[1:])
        elif args and args[0] == 'copy-devel':
            if len(args) != 7:
                raise ValueError('usage: select-package-stage.py copy-devel SHARED_STAGE DESTINATION FULL_PLIST RUNTIME_PLIST DEVEL_PLIST SELECTED_PLIST')
            copy_devel(*args[1:])
        elif len(args) == 6:
            select(*args)
        else:
            raise ValueError('usage: select-package-stage.py runtime|devel|check STAGE FULL_PLIST RUNTIME_PLIST DEVEL_PLIST SELECTED_PLIST')
    except Exception as error:
        exit_error(error)
