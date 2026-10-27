#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check NetBSD GN resource routing and actual ELF/resource completeness tools."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'work', 'gn', 'git', 'clang', 'ar', 'utility-path'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    source, work = Path(args.source), Path(args.work)
    if not source.is_absolute() or not work.is_absolute() or work.exists() or work.is_relative_to(source):
        parser.error('source must be absolute; work must be new and outside source')
    work.mkdir(parents=True)
    env = {'PATH': args.utility_path, 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}
    commands = []

    def run(label, command, *, cwd=work, error=None):
        result = subprocess.run(list(map(str, command)), cwd=cwd, env=env, capture_output=True, text=True)
        text = result.stdout + result.stderr
        (work / (label + '.log')).write_text(text)
        commands.append(dict(label=label, argv=list(map(str, command)), status=result.returncode))
        if error is None:
            assert result.returncode == 0, label + ': ' + text
        else:
            assert result.returncode != 0 and error in text, label + ': ' + text
        return result.stdout

    members = ('build/toolchain/gcc_toolchain.gni', 'electron/BUILD.gn')
    baseline = work / 'baseline'
    before = {}
    for name in members:
        target = baseline / name; target.parent.mkdir(parents=True, exist_ok=True)
        data = (source / name).read_bytes(); target.write_bytes(data)
        before[name] = hashlib.sha256(data).hexdigest()
    patched = work / 'patched'; shutil.copytree(baseline, patched)
    patch = Path(__file__).resolve().parents[1] / 'patches/electron-netbsd-resource-allowlist.patch'
    run('patch-check', [args.git, 'apply', '--check', patch], cwd=patched)
    run('patch', [args.git, 'apply', patch], cwd=patched)

    def gn_case(label, tree, platform, *, strip=False, component=False, error=None, expected=True):
        root = work / label; root.mkdir()
        gcc = (tree / members[0]).read_text()
        imports = re.findall(r'^import\("//([^"]+)"\)', gcc, re.M)
        for name in imports:
            target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text('')
        target = root / members[0]; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(gcc)
        (root / '.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\n')
        (root / 'BUILDCONFIG.gn').write_text('''set_default_toolchain("//:tc")
is_official_build = false
is_cronet_build = false
is_chromeos = false
is_linux = PLATFORM == "linux"
is_netbsd = PLATFORM == "netbsd"
strip_debug_info = STRIP
is_component_build = COMPONENT
target_os = PLATFORM
'''.replace('PLATFORM', json.dumps(platform)).replace('STRIP', str(strip).lower()).replace('COMPONENT', str(component).lower()))
        electron = (tree / members[1]).read_text()
        selection = re.search(r'electron_use_resource_allowlist =\n[^\n]+', electron).group(0)
        (root / 'BUILD.gn').write_text('import("//build/toolchain/gcc_toolchain.gni")\n' + selection + '\n' +
            'write_file("$root_build_dir/selected.json", electron_use_resource_allowlist, "json")\n' +
            'group("all") {}\ntoolchain("tc") { tool("stamp") { command = "touch {{output}}" } }\n')
        run(label, [args.gn, 'gen', root / 'out', '--args=enable_resource_allowlist_generation=true'], cwd=root, error=error)
        if error is None:
            assert json.loads((root / 'out/selected.json').read_text()) == str(expected).lower()

    gn_case('baseline-netbsd', baseline, 'netbsd', error='does not work for target_os=netbsd')
    gn_case('netbsd', patched, 'netbsd')
    gn_case('linux-baseline', baseline, 'linux')
    gn_case('linux', patched, 'linux')
    gn_case('mac', patched, 'mac', expected=False)
    gn_case('unported-platform', patched, 'openbsd', error='does not work for target_os=openbsd')
    gn_case('stripped-refused', patched, 'netbsd', strip=True, error='requires strip_debug_info=false')
    gn_case('component-refused', patched, 'netbsd', component=True, error='requires is_component_build=false')

    obj = work / 'obj'; obj.mkdir()
    code = 'namespace ui { template<int N> __attribute__((noinline)) void AllowlistedResource() { asm volatile(""); } }\n'
    code += 'extern "C" void use_resources() {\n' + ''.join('ui::AllowlistedResource<' + str(i) + '>();\n' for i in range(1000, 1101)) + '}\n'
    (work / 'resources.cc').write_text(code)
    run('clang-netbsd-object', [args.clang, '--target=x86_64--netbsd', '-ffreestanding', '-fno-exceptions',
        '-fno-rtti', '-g', '-O0', '-c', 'resources.cc', '-o', 'obj/resources.o'])
    assert (obj / 'resources.o').read_bytes().startswith(b'\x7fELF')
    run('thin-archive', [args.ar, 'rcT', 'obj/resources.a', 'obj/resources.o'])
    wrapper = source / 'build/toolchain/gcc_solink_wrapper.py'
    run('collect-inputs', [sys.executable, '-B', wrapper, '--readelf', '/readelf-must-not-run',
                           '--nm', '/nm-must-not-run', '--output', 'inputs.so', '--tocfile', 'inputs.TOC',
                           '--', '/linker-must-not-run', '--collect-inputs-only', 'obj/resources.a'])
    generator = source / 'tools/resources/generate_resource_allowlist.py'
    run('extract-elf', [sys.executable, '-B', generator, '-o', 'elf.txt', 'obj/resources.o'])
    run('extract-inputs', [sys.executable, '-B', generator, '-o', 'inputs.txt', 'inputs.so'])
    expected = ''.join(str(i) + '\n' for i in range(1000, 1101))
    assert (work / 'elf.txt').read_text() == (work / 'inputs.txt').read_text() == expected
    sys.path.insert(0, str(source / 'tools/grit'))
    pack = importlib.import_module('grit.format.data_pack')
    resources = {i: b'present' for i in range(1000, 1101)}
    pack.WriteDataPack(resources, str(work / 'complete.pak'), pack.UTF8)
    del resources[1050]
    pack.WriteDataPack(resources, str(work / 'missing.pak'), pack.UTF8)
    check = [sys.executable, '-B', source / 'electron/build/check_resource_allowlist.py',
             '--allowlist', 'inputs.txt', '--gen-dir', str(work), '--grit-dir', str(source / 'tools/grit')]
    run('complete-resources', [*check, '--pak', 'complete.pak', '--stamp', 'complete.stamp'])
    run('missing-resource-refused', [*check, '--pak', 'missing.pak', '--stamp', 'missing.stamp'],
        error='are not present in any shipped .pak file')
    assert (work / 'complete.stamp').is_file() and not (work / 'missing.stamp').exists()
    assert before == {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in members}
    result = dict(scope='GN platform checks, NetBSD ELF object, actual thin archive/input collector and resource pak checker; no target execution or full Electron build',
                  gn_cases=8, resource_ids=101, commands=commands)
    (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: 8 GN cases, 101 actual ELF resource IDs, thin archive collection, pak completeness and missing-resource refusal')


if __name__ == '__main__':
    main()
