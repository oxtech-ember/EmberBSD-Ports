#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compare real target and host query outputs.
from pathlib import Path
import shlex
import sys
sys.dont_write_bytecode = True
import llvm_sdk as sdk
import llvm_target as target_api

OPTIONS = ['version', 'host-target', 'has-rtti', 'assertion-mode', 'targets-built', 'components', 'prefix', 'cppflags', 'cflags', 'cxxflags', 'ldflags', 'shared-mode', 'libs', 'libnames', 'libfiles', 'system-libs']
COMPONENTS = ['bitwriter', 'engine', 'mcdisassembler', 'mcjit', 'core', 'executionengine', 'scalaropts', 'transformutils', 'instcombine', 'native', 'orcjit']


def arguments(option):
    return ['--link-shared', '--' + option, *COMPONENTS] if option in OPTIONS[-5:] else ['--' + option]


def compare(args):
    if len(args) != 2:
        raise ValueError('usage: compare-llvm-config.py --sdk-source SDK COMPLETED_WORK TARGET_REFERENCE')
    work, reference = [Path(sdk.existing_directory(p)) for p in args]
    r = sdk.read_json(work / 'receipt.json')
    if (reference / 'status').read_text().strip() != 'complete':
        raise ValueError('reference capture is incomplete')
    if r['target_prefix'] == r['target_build']:
        raise ValueError('comparison requires an installed/staged prefix, not a development tree')
    target_prefix = (reference / 'prefix').read_text().strip()
    if not sdk.safe_absolute(target_prefix):
        raise ValueError('invalid reference prefix')
    target_api.for_triple(r['target_triple'])
    if (reference / 'version').read_text().strip() != '23.1.4' or (reference / 'host-target').read_text().strip() != r['target_triple']:
        raise ValueError('reference must match the selected LLVM 23.1.4 NetBSD target exactly')
    failed = []
    for option in OPTIONS:
        actual = shlex.split(sdk.capture(str(work / 'bin/llvm-config'), *arguments(option)))
        expected = shlex.split((reference / option).read_text().strip())
        if option == 'prefix':
            expected = [r['target_prefix']]
        elif option in ('cppflags', 'cflags', 'cxxflags'):
            expected = ['-I' + r['target_prefix'] + '/include' if v == '-I' + target_prefix + '/include' else v for v in expected]
        elif option == 'ldflags':
            if r['sysroot'] in (reference / option).read_text():
                raise ValueError('target reference leaks the private build sysroot')
            expected = ['-L' + r['target_prefix'] + '/lib' if i == 0 and v == '-L' + target_prefix + '/lib' else '-L' + r['sysroot'] + v[2:] if v.startswith('-L/') and not v.startswith('-L' + r['sysroot'] + '/') else v for i, v in enumerate(expected)]
        elif option == 'libfiles':
            if not all(v.startswith(target_prefix + '/lib/') for v in expected):
                raise ValueError('reference library outside its prefix')
            expected = [r['target_prefix'] + v.removeprefix(target_prefix) for v in expected]
        if actual != expected:
            print(f'FAIL: {option}\n  expected: {expected!r}\n  actual:   {actual!r}', file=sys.stderr)
            failed.append(option)
        else:
            print('PASS: ' + option + ' agrees with real target llvm-config')
    if failed:
        raise ValueError('metadata disagreement: ' + ', '.join(failed))
    return 0


if __name__ == '__main__':
    sys.exit(sdk.main(compare))
