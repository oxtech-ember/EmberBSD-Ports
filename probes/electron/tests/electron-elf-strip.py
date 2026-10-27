#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Run the real GN/Ninja ELF strip action with selected LLVM tools."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'work', 'git', 'gn', 'ninja', 'clang', 'ld', 'strip', 'objcopy', 'readelf', 'utility-path'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    source, work = Path(args.source), Path(args.work)
    if not source.is_absolute() or not work.is_absolute() or work.exists() or work.is_relative_to(source):
        parser.error('use an absolute source and new separate work directory')
    work.mkdir(parents=True)
    env = dict(PATH=args.utility_path, LC_ALL='C', PYTHONDONTWRITEBYTECODE='1')
    commands = []
    def run(label, argv, cwd=work, error=None):
        result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, capture_output=True, text=True)
        text = result.stdout + result.stderr
        (work / (label + '.log')).write_text(text)
        commands.append(dict(label=label, argv=list(map(str, argv)), status=result.returncode))
        if error is None:
            assert result.returncode == 0, label + ': ' + text
        else:
            assert result.returncode != 0 and error in text, label + ': ' + text
        return result.stdout
    baseline = work / 'baseline'
    members = ('build/linux/strip_binary.gni', 'build/linux/strip_binary.py')
    for name in members:
        path = baseline / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((source / name).read_bytes())
    before = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in members}
    patched = work / 'patched'; shutil.copytree(baseline, patched)
    patch = Path(__file__).resolve().parents[1] / 'patches/gn-selected-elf-strip.patch'
    run('patch-check', [args.git, 'apply', '--check', patch], cwd=patched)
    run('patch', [args.git, 'apply', patch], cwd=patched)
    (work / 'entry.c').write_text('int target_data = 7; int entry(void) { return target_data + 1; }\n')
    run('compile', [args.clang, '--target=x86_64--netbsd', '-ffreestanding', '-g', '-O0', '-c', 'entry.c', '-o', 'input.o'])
    run('link', [args.ld, '-e', 'entry', 'input.o', '-o', 'input.elf'])
    assert (work / 'input.elf').read_bytes().startswith(b'\x7fELF')
    run('baseline-noop', [sys.executable, '-B', baseline / members[1], '--llvm-strip-binary-path', args.strip,
        '--llvm-objcopy-binary-path', args.objcopy, '--binary-input', 'input.elf',
        '--symbol-output', 'missing.debug', '--stripped-binary-output', 'missing.elf'])
    assert not (work / 'missing.debug').exists() and not (work / 'missing.elf').exists()

    def fixture(label, *, selected=True, only_strip=False, relative=False, platform='netbsd', corrupt=False):
        root = work / label; shutil.copytree(patched, root)
        for name in ('build/config/clang/clang.gni', 'build/toolchain/toolchain.gni'):
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('')
        (root / '.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\nscript_executable = ' + json.dumps(sys.executable) + '\n')
        (root / 'BUILDCONFIG.gn').write_text('current_os = ' + json.dumps(platform) + '\nset_default_toolchain("//:tc")\n')
        (root / 'BUILD.gn').write_text('''import("//build/linux/strip_binary.gni")
strip_binary("strip_fixture") {
  binary_input = "//input.elf"
  symbol_output = "$root_out_dir/fixture.debug"
  stripped_binary_output = "$root_out_dir/fixture.elf"
}
toolchain("tc") { tool("stamp") { command = "touch {{output}}" } }
''')
        (root / 'input.elf').write_bytes(b'invalid ELF\n' if corrupt else (work / 'input.elf').read_bytes())
        values = []
        if selected:
            values.append('emberbsd_target_strip=' + json.dumps('relative-strip' if relative else args.strip))
            if not only_strip:
                values.append('emberbsd_target_objcopy=' + json.dumps(args.objcopy))
        error = 'select both' if only_strip else 'must be absolute' if relative else None
        run(label + '-gn', [args.gn, 'gen', root / 'out', '--args=' + ' '.join(values)], cwd=root, error=error)
        return root

    root = fixture('selected')
    description = json.loads(run('selected-inputs', [args.gn, 'desc', root / 'out', '//:strip_fixture', 'inputs', '--format=json'], cwd=root))
    inputs = description['//:strip_fixture']['inputs']
    assert args.strip in inputs and args.objcopy in inputs, inputs
    run('selected-ninja', [args.ninja, '-C', root / 'out', 'strip_fixture'])
    for name in ('fixture.debug', 'fixture.elf'):
        assert (root / 'out' / name).is_file()
    debug = run('debug-sections', [args.readelf, '-S', root / 'out/fixture.debug'])
    stripped = run('stripped-sections', [args.readelf, '-S', root / 'out/fixture.elf'])
    assert '.debug_info' in debug and '.debug_info' not in stripped and '.gnu_debuglink' in stripped
    fixture('unpaired', only_strip=True)
    fixture('relative', relative=True)
    default = fixture('default', selected=False)
    mac = fixture('mac', platform='mac')
    for label, tree in (('default', default), ('mac', mac)):
        inputs = run(label + '-inputs', [args.gn, 'desc', tree / 'out', '//:strip_fixture', 'inputs'], cwd=tree)
        assert '@PREFIX@/bin/llvm-strip' in inputs and '@PREFIX@/bin/llvm-objcopy' in inputs
    invalid = fixture('invalid-elf', corrupt=True)
    run('invalid-elf-ninja', [args.ninja, '-C', invalid / 'out', 'strip_fixture'], error='not recognized')
    assert not (invalid / 'out/fixture.elf').exists()
    assert before == {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in members}
    (work / 'result.json').write_text(json.dumps(dict(scope='actual GN/Ninja strip on freestanding NetBSD ELF; no target execution or runtime acceptance', commands=commands), indent=2)+'\n')
    print('PASS: real GN/Ninja ELF strip, debug extraction, baseline no-op, explicit inputs, paired/absolute guards, unchanged defaults and corrupt ELF refusal')


if __name__ == '__main__':
    main()
