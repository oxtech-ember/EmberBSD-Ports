#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Select an audited MIT Kerberos staging partition.
import os
from pathlib import Path
import re
import stat
import sys
sys.dont_write_bytecode = True
from sdk_source import load_sdk


def manifest(path):
    from emberbsd_sdk.paths import regular_file
    regular_file(path)
    result = set()
    for name in Path(path).read_text().splitlines():
        if not name or re.match(r'^@comment(?: |$)|^@pkgdir ', name):
            continue
        if (re.search(r'[\x00-\x20\x7f]', name) or name.startswith(('/', '@')) or name.endswith('/')
                or '${' in name or any(p in ('', '.', '..') for p in name.split('/'))):
            raise ValueError(f'unsafe manifest entry: {name}')
        if name in result:
            raise ValueError(f'duplicate manifest entry: {name}')
        result.add(name)
    if not result:
        raise ValueError('empty MIT Kerberos partition')
    return result


def select(part, stage, *lists):
    from emberbsd_sdk.paths import real_directory, canonical_existing
    from emberbsd_sdk.inventory import snapshot_tree
    if part not in ('runtime', 'devel') or len(lists) != 3:
        raise ValueError('unknown MIT Kerberos package part or manifest count')
    if not os.path.isabs(stage) or stage == '/':
        raise ValueError('absolute regular staging directory required')
    real_directory(stage)
    if canonical_existing(stage) != stage:
        raise ValueError('staging root must have a normalized path with real ancestors')
    full, runtime, devel = map(manifest, lists)
    if runtime & devel:
        raise ValueError('MIT Kerberos partitions overlap')
    if runtime | devel != full:
        raise ValueError('MIT Kerberos partition union differs from the complete PLIST')
    wanted = {'runtime': runtime, 'devel': devel}[part]
    # pkgsrc installs the two runtime rc.d examples after upstream install.
    generated = {'share/examples/rc.d/kadmind', 'share/examples/rc.d/kdc'} if part == 'runtime' else set()
    full |= generated
    wanted |= generated
    runtime |= generated
    before = snapshot_tree(stage)
    actual = {name for name, row in before.items() if row['kind'] != 'directory'}
    directories = [os.path.join(stage, name) for name, row in before.items() if row['kind'] == 'directory']
    if actual - full:
        raise ValueError('unlisted staged file: ' + sorted(actual - full)[0])
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
                    raise ValueError(f'escaping MIT Kerberos stage link: {name}')
                resolved.pop()
                continue
            relative = '/'.join(resolved + [component])
            path = os.path.join(stage, relative)
            if os.path.islink(path):
                hops += 1
                if hops > 64:
                    raise ValueError(f'cyclic or excessive MIT Kerberos stage link: {name}')
                if name in runtime and relative not in runtime:
                    raise ValueError(f'runtime link uses SDK: {name} -> {relative}')
                target = os.readlink(path)
                if not target or re.search(r'[\x00-\x20\x7f]', target) or target.endswith('/') or os.path.isabs(target):
                    raise ValueError(f'unsafe MIT Kerberos stage link: {name}')
                todo[:0] = target.split('/')
                continue
            if not os.path.exists(path):
                raise ValueError(f'missing MIT Kerberos stage link target: {name}')
            if todo and not os.path.isdir(path):
                raise ValueError(f'non-directory MIT Kerberos link component: {name}')
            resolved.append(component)
        terminal = '/'.join(resolved)
        if terminal not in actual or not os.path.isfile(os.path.join(stage, terminal)):
            raise ValueError(f'MIT Kerberos stage link does not resolve to a listed file: {name}')
        if name in runtime and terminal not in runtime:
            raise ValueError(f'runtime link resolves to SDK: {name} -> {terminal}')
    if snapshot_tree(stage) != before:
        raise ValueError('stage changed during partition verification')
    for name in sorted(actual - wanted):
        os.unlink(os.path.join(stage, name))
    for directory in sorted(directories, key=lambda p: p.count('/'), reverse=True):
        if not os.listdir(directory) and not (part == 'runtime' and os.path.relpath(directory, stage) in ('lib/krb5/plugins/authdata', 'lib/krb5/plugins/libkrb5', 'share/gnats')):
            os.rmdir(directory)
    print(f'PASS: complete MIT Kerberos stage has an exhaustive, disjoint {part} partition')


if __name__ == '__main__':
    from sdk_source import exit_error, install_signal_handlers
    install_signal_handlers()
    try:
        _, args = load_sdk()
        if len(args) != 5:
            raise ValueError('usage: select-package-stage.py [--sdk-source SOURCE] runtime|devel STAGE FULL_PLIST RUNTIME_PLIST DEVEL_PLIST')
        select(*args)
    except Exception as error:
        exit_error(error)
