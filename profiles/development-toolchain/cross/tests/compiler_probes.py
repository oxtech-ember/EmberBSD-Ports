# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; real GCC16 split DWARF and LTO/binutils host probes.
from pathlib import Path
import os
import re
from emberbsd_sdk import elf
from host import *
from target_options import parse


def split_dwarf(args):
    target, _, args = parse(args)
    require(len(args) == 2, 'Usage: split-dwarf.py [--target TARGET] PREFIX NEW_WORK --sdk-source SOURCE')
    prefix, work = build_path(args[0]), new_path(args[1])
    triplet = TARGETS[target][0]
    work.mkdir()
    (work / 'test.c').write_text('struct split_record { long value; }; struct split_record split_data;\n')
    env = {'PATH': '/usr/bin:/bin'}
    logged([prefix / 'bin' / (triplet + '-gcc'), '-O2', '-gdwarf-5', '-gsplit-dwarf', '-c', work / 'test.c', '-o', work / 'test.o'], work / 'compile.log', env)
    require((work / 'test.dwo').is_file() and (work / 'test.dwo').stat().st_size, 'Missing split DWARF object')
    readelf = prefix / 'bin' / (triplet + '-readelf')
    info = capture([readelf, '--debug-dump=info', work / 'test.o'], env)
    (work / 'info.txt').write_text(info)
    require('DW_UT_skeleton' in info and 'DW_UT_split_compile' in info, 'Missing skeleton or split compile unit')
    strings = capture([readelf, '--debug-dump=str-offsets', work / 'test.dwo'], env)
    (work / 'strings.txt').write_text(strings)
    require('split_record' in strings, 'Missing indexed DWARF5 type string')
    print('PASS: installed GCC creates and follows split DWARF without tool-path overrides')


def lto_binutils(args):
    require(len(args) == 2, 'Usage: lto-binutils.py PREFIX NEW_WORK --sdk-source SOURCE')
    prefix, work = build_path(args[0]), new_path(args[1])
    triplet = 'aarch64--netbsd'
    tools = check_compilers(prefix, 'aarch64')
    libexec = prefix / 'libexec/gcc' / triplet / VERSION
    collect2, plugin, wrapper = [libexec / name for name in ('collect2', 'liblto_plugin.so', 'lto-wrapper')]
    for path in (collect2, plugin, wrapper):
        require(os.access(path, os.X_OK), 'Required GCC16 LTO tool missing: ' + str(path))
    for name in ('gcc', 'g++'):
        for tool in ('as', 'ld'):
            require(capture([tools[name], '-print-prog-name=' + tool]).strip() == str(tools[tool]), 'Unexpected target tool lookup')
    for name in ('as', 'ld', 'readelf'):
        require(re.search(r'GNU .* 2[.]47([.]|\s|$)', capture([tools[name], '--version']).splitlines()[0]), 'GNU ' + name + '2.47 required')
    work.mkdir()
    fields = dict(target=triplet, gcc=str(tools['gcc']), gxx=str(tools['g++']), **{name: str(tools[name]) for name in ('as', 'ld', 'readelf')}, collect2=str(collect2), plugin=str(plugin), lto_wrapper=str(wrapper))
    (work / 'inputs.txt').write_text(''.join(key + '=' + value + '\n' for key, value in fields.items()) + ''.join(capture([tools[name], '--version']).splitlines()[0] + '\n' for name in ('gcc', 'g++', 'as', 'ld', 'readelf')) + digest_rows([tools[name] for name in ('gcc', 'g++', 'as', 'ld', 'readelf')]))
    source = '__attribute__((noreturn)) void\n_start(void)\n{\n    for (;;)\n        __asm__ volatile("wfe");\n}\n'
    (work / 'probe.c').write_text(source)
    (work / 'probe.cc').write_text('extern "C" ' + source)
    for compiler, suffix, name in [('gcc', 'c', 'c'), ('g++', 'cc', 'cxx')]:
        flags = ['-v', '-O2', '-flto', '-fuse-linker-plugin', '-ffreestanding', '-fno-stack-protector'] + (['-fno-exceptions', '-fno-rtti'] if compiler == 'g++' else []) + ['-nostdlib', '-nostartfiles', '-Wl,-e,_start', '-Wl,-v']
        image = work / ('probe-' + name + '.elf')
        log = work / (name + '-link.log')
        logged([tools[compiler]] + flags + [work / ('probe.' + suffix), '-o', image], log)
        data = log.read_text()
        require(all(str(path) in data for path in (collect2, plugin, wrapper, tools['ld'], tools['as'])), 'LTO selected unexpected tools')
        require(elf.read_elf_header(image, machine=183, required_type=2) is not None, 'LTO output is not AArch64 ELF executable')
        (Path(str(image) + '.header')).write_text(capture([tools['readelf'], '-h', image]))
    print('PASS: C/C++ LTO uses collect2, GCC plugin and default Binutils2.47; both outputs are AArch64 ELF executables')
