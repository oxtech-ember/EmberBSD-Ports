#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the Darwin Node GYP frontend and its release and debug symbol choices."""

import argparse
import ast
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def compiled_flags(makefile, configuration):
    flags = []
    for variable in ('CFLAGS_', 'CFLAGS_CC_'):
        match = re.search('^' + variable + configuration + r' := (.*?)(?:\n\s*\n)',
                          makefile, re.MULTILINE | re.DOTALL)
        if not match:
            raise ValueError(f'missing {variable}{configuration}')
        flags.extend(match[1].replace('\\\n', ' ').split())
    return flags


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('node-source', 'host-prefix', 'macos-sdk', 'xcode-plist', 'work-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    source = args.node_source.resolve(strict=True)
    host = args.host_prefix.resolve(strict=True)
    sdk = args.macos_sdk.resolve(strict=True)
    gyp = host / 'share/gyp'
    python = host / 'bin/python3.15'
    env = dict(os.environ, PATH=str(host / 'bin') + ':' + str(host / 'gnu/bin'),
               NODE_GYP_SOURCE=str(gyp), GYP_MACOS_SDK_PATH=str(sdk),
               GYP_XCODE_VERSION_PLIST=str(args.xcode_plist.resolve(strict=True)))
    base = json.loads((source / 'config.gypi').read_text().split('\n', 1)[1])
    runtime_conditions = ast.literal_eval((source / 'node.gypi').read_text())['conditions']
    runtime_debug = next(condition for condition in runtime_conditions
                         if condition[0].strip() == 'debug_node=="true"')
    with tempfile.TemporaryDirectory(dir=args.work_dir.resolve(strict=True)) as temporary:
        root = Path(temporary)
        tools = root / 'tools'
        tools.mkdir()
        for name in ('gyp_node.py', 'node-build.gypi'):
            shutil.copyfile(source / 'tools' / name, tools / name)
        shutil.copyfile(source / 'common.gypi', root / 'common.gypi')
        (root / 'unit.cc').write_text('extern "C" int probe(int n) { return n + 1; }\n')
        (root / 'node.gyp').write_text(repr({'targets': [
            {'target_name': 'engine', 'type': 'static_library', 'sources': ['unit.cc']},
            {'target_name': 'runtime', 'type': 'static_library', 'sources': ['unit.cc'],
             'conditions': [runtime_debug]},
        ]}))
        for case in ('normal', 'symbols', 'node-only', 'addon'):
            base['variables'].update(debug_symbols=str(case == 'symbols').lower(),
                                     debug_node=str(case == 'node-only').lower())
            (root / 'config.gypi').write_text(repr(base))
            if case == 'addon':
                argv = [python, '-B', gyp / 'gyp_main.py', '-f', 'make-mac', '--depth=.',
                        '-Dcomponent=static_library', '-Dlibrary=static_library',
                        '-I', 'common.gypi', '-I', 'config.gypi', 'node.gyp']
                output = root
            else:
                argv = [python, '-B', tools / 'gyp_node.py', '-f', 'make-mac']
                output = root / 'out'
            subprocess.run(argv, cwd=root, env=env, check=True)
            for target in ('engine', 'runtime'):
                makefile = (output / (target + '.target.mk')).read_text()
                for mode in ('Debug', 'Release'):
                    expected = (mode == 'Debug' or case in ('symbols', 'addon') or
                                (case == 'node-only' and target == 'runtime'))
                    obj = root / 'unit.o'
                    flags = compiled_flags(makefile, mode)
                    subprocess.run([host / 'bin/clang++', '-isysroot', sdk, *flags,
                                    '-c', root / 'unit.cc', '-o', obj], env=env, check=True)
                    sections = subprocess.check_output([host / 'bin/llvm-size', '-m', obj],
                                                       text=True, env=env)
                    if ('(__DWARF, __debug_info)' in sections) != expected:
                        raise ValueError(f'{case} {target} {mode} has incorrect DWARF sections')
    print('Verified Darwin release, debug, --debug-symbols, --debug-node and addon output.')


if __name__ == '__main__':
    main()
