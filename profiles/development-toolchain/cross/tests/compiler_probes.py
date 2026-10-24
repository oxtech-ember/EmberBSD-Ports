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
    target, _, args = parse(args, kernel_target_allowed=True)
    require(len(args) == 2, 'Usage: split-dwarf.py [--target TARGET] PREFIX NEW_WORK --sdk-source SOURCE')
    prefix, work = build_path(args[0]), new_path(args[1])
    triplet = target_triplet(target)
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


def armv7_abi(args):
    target, _, args = parse(args, kernel_target_allowed=True)
    require(target in KERNEL_TARGETS, 'The ARMv7 ABI probe requires a kernel-only target')
    require(len(args) == 2, 'Usage: armv7-abi.py --target earmv7hf PREFIX NEW_WORK --sdk-source SOURCE')
    prefix, work = build_path(args[0]), new_path(args[1])
    triplet = target_triplet(target)
    metadata = target_metadata(target)
    tools = check_compilers(prefix, target)
    work.mkdir()
    source = work / 'abi.c'
    source.write_text('__attribute__((noinline, used)) double\n'
                      'armv7_abi_probe(double left, float right)\n'
                      '{\n    return left + (double)right;\n}\n')
    env = {'PATH': '/usr/bin:/bin'}
    obj = work / 'abi.o'
    logged([tools['gcc'], '-O2', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
            '-ffreestanding', '-fno-builtin', '-fno-stack-protector',
            '-c', source, '-o', obj], work / 'compile.log', env)
    detail = capture([tools['readelf'], '-h', '-A', obj], env)
    require(re.search(r'^\s*Class:\s*ELF32\s*$', detail, re.M) and
            re.search(r'^\s*Data:.*little endian\s*$', detail, re.M) and
            re.search(r'^\s*Type:\s*REL\b', detail, re.M) and
            re.search(r'^\s*Machine:\s*ARM\b', detail, re.M),
            'ARMv7 kernel compiler did not emit a little-endian ELF32 ARM relocatable object')
    header = {'class': 32, 'machine': metadata['machine']}
    flags = re.search(r'^\s*Flags:\s*(.+)$', detail, re.M)
    abi_attribute = re.search(r'^\s*Tag_ABI_VFP_args:\s*(.+)$', detail, re.M)
    require(flags is not None and 'Version5 EABI' in flags.group(1) and
            abi_attribute is not None and abi_attribute.group(1).strip() == 'VFP registers',
            'ARMv7 kernel object does not advertise the hard-float AAPCS')
    linked = work / 'abi.elf'
    logged([tools['ld'], '-e', 'armv7_abi_probe', '-o', linked, obj],
           work / 'link.log', env)
    linked_detail = capture([tools['readelf'], '-h', linked], env)
    linked_flags = re.search(r'^\s*Flags:\s*(.+)$', linked_detail, re.M)
    require(linked_flags is not None and 'Version5 EABI' in linked_flags.group(1) and
            'hard-float ABI' in linked_flags.group(1),
            'ARMv7 linked object does not advertise the hard-float EABI')
    (work / 'header.txt').write_text(detail)
    (work / 'linked-header.txt').write_text(linked_detail)
    (work / 'inputs.txt').write_text(
        'format=earmv7hf-kernel-abi\n' +
        'target=' + target + '\n' +
        'triplet=' + triplet + '\n' +
        'elf_class=' + str(header['class']) + '\n' +
        'elf_machine=' + str(header['machine']) + '\n' +
        'abi_flags=' + flags.group(1).strip() + '\n' +
        'abi_attribute=' + abi_attribute.group(1).strip() + '\n' +
        'linked_abi_flags=' + linked_flags.group(1).strip() + '\n' +
        'required_macros=' + ','.join(metadata['required_macros']) + '\n' +
        digest_rows([source, obj, linked, tools['gcc'], tools['ld'], tools['readelf']]))
    print('PASS: GCC emits ELF32 ARMv7 hard-float EABI objects and linked images without libc')


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
    target, _, args = parse(args)
    require(len(args) == 3, 'Usage: plugin-needed-warnings.py [--target TARGET] PREFIX SYSROOT NEW_WORK --sdk-source SOURCE')
    prefix, sysroot, work = build_path(args[0]), build_path(args[1]), new_path(args[2])
    tools = check_compilers(prefix, target)
    triplet = TARGETS[target][0]
    runtime = sysroot / 'usr/pkg/gcc16'
    crt = runtime / 'lib/gcc' / triplet / VERSION
    for path in (crt / 'crtbeginS.o', crt / 'crtendS.o', crt / 'libgcc.a', runtime / 'lib/libgcc_s.so.1'):
        require(path.is_file() and paths.inside(path.resolve(strict=True), runtime), 'Selected target GCC16 CRT/runtime missing or outside sysroot: ' + str(path))
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
    common = ['--sysroot=' + str(sysroot), '-B' + str(crt) + '/', '-L' + str(runtime / 'lib'), '-Wl,-rpath,/usr/pkg/gcc16/lib', '-Wl,-rpath-link,' + str(sysroot / 'usr/lib')]
    for name, source, flags, library, valid in cases:
        (work / (name + '.c')).write_text(source)
        argv = [str(tools['gcc']), '-v'] + common + ['-O2', '-fPIC', '-shared', '-Wl,--fatal-warnings', '-Wl,--as-needed'] + flags + [str(work / (name + '.c')), '-o', str(work / (name + '.so')), library]
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
