# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; real GCC16 split DWARF and LTO/binutils host probes.
from pathlib import Path
import os
import re
import subprocess
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


def plugin_needed_warnings(args):
    require(len(args) == 3, 'Usage: plugin-needed-warnings.py PREFIX SYSROOT NEW_WORK --sdk-source SOURCE')
    prefix, sysroot, work = build_path(args[0]), build_path(args[1]), new_path(args[2])
    tools = check_compilers(prefix, 'aarch64')
    sections = capture([tools['readelf'], '-S', '-W', sysroot / 'usr/lib/libc.so'])
    require('.gnu.warning.gets' in sections, 'Sysroot libc has no link-time warning sections')
    work.mkdir()
    # libm needs libc through DT_NEEDED. Only a direct reference may warn.
    # NetBSD's base ld copies DT_NEEDED entries by default; test both modes.
    indirect = '#include <math.h>\ndouble g(double x){return sin(x);}\n'
    direct = 'extern char *gets(char *);\nchar *h(char *s){return gets(s);}\n'
    cases = [('indirect', indirect, [], '-lm', True),
             ('indirect-copy', indirect, ['-Wl,--copy-dt-needed-entries'], '-lm', True),
             ('direct', direct, [], '-lc', False)]
    for name, source, flags, library, valid in cases:
        (work / (name + '.c')).write_text(source)
        argv = [str(tools['gcc']), '-v', '--sysroot=' + str(sysroot), '-O2', '-fPIC', '-shared', '-Wl,--fatal-warnings', '-Wl,--as-needed'] + flags + [str(work / (name + '.c')), '-o', str(work / (name + '.so')), library]
        result = subprocess.run(argv, env=environment(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = result.stdout.decode('utf-8', 'replace')
        (work / (name + '.log')).write_text(output)
        require('liblto_plugin' in output, 'The link did not load the GCC LTO plugin: ' + name)
        warnings = [line for line in output.splitlines() if 'warning:' in line]
        if valid:
            require(result.returncode == 0 and not warnings, '%s: libc through DT_NEEDED produced %d link warnings' % (name, len(warnings)))
        else:
            require(result.returncode != 0 and any('gets' in line for line in warnings), 'Direct gets reference did not produce a fatal link warning')
    print('PASS: plugin links warn only for direct references, not for libc loaded through DT_NEEDED')
