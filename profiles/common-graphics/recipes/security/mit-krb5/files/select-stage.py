#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Select an audited MIT Kerberos staging partition.
import os
from pathlib import Path
import re
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
    from emberbsd_sdk.stage import STAGE_PARTITION_API, partition_stage
    if type(STAGE_PARTITION_API) is not int or STAGE_PARTITION_API != 1:
        raise ValueError('The selected SDK must provide stage partition API 1')
    if part not in ('runtime', 'devel') or len(lists) != 3:
        raise ValueError('unknown MIT Kerberos package part or manifest count')
    if not os.path.isabs(stage):
        raise ValueError('absolute staging path required')
    full, runtime, devel = map(manifest, lists)
    # pkgsrc adds these two examples to the runtime after upstream install.
    generated = {'share/examples/rc.d/kadmind', 'share/examples/rc.d/kdc'} if part == 'runtime' else set()
    full |= generated
    runtime |= generated
    keep_empty = ('lib/krb5/plugins/authdata', 'lib/krb5/plugins/libkrb5', 'share/gnats') if part == 'runtime' else ()
    result = partition_stage(stage, full, {'runtime': runtime, 'devel': devel}, part,
                             dependencies={'devel': ('runtime',)}, keep_empty=keep_empty)
    print(f"PASS: complete MIT Kerberos stage has an exhaustive, disjoint {part} partition; {result['complete_files']} files")


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
