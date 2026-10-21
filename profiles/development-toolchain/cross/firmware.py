# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; finite firmware-only GCC16 frontend producer policy.
import os
from pathlib import Path
import struct

import pipeline
from host import *
from pipeline import host_math_main, relocate_binutils
from target_options import FIRMWARE_TARGETS, parse_firmware

TRIPLET = FIRMWARE_TARGETS['arm-none-eabi']
ARM_FLAGS = ['-mthumb', '-mcpu=cortex-m4', '-mfloat-abi=soft']


def check_compiler(prefix):
    tools = {name: Path(prefix) / 'bin' / (TRIPLET + '-' + name) for name in ['gcc'] + TOOLS}
    for name, tool in tools.items():
        require(os.access(tool, os.X_OK), 'Missing firmware cross tool: ' + name)
    require(capture([tools['gcc'], '-dumpmachine']).strip() == TRIPLET, 'Firmware compiler target mismatch')
    require(capture([tools['gcc'], '-dumpfullversion']).strip() == VERSION, 'GCC 16.2.0 is required')
    macros = capture([tools['gcc']] + ARM_FLAGS + ['-dM', '-E', '-x', 'c', '-'], input=b'\n').splitlines()
    required = ['__GNUC__ 16', '__ARM_ARCH_7EM__ 1', '__thumb__ 1', '__SOFTFP__ 1', '__SIZEOF_POINTER__ 4']
    require(all('#define ' + value in macros for value in required) and not any(line.startswith(('#define __NetBSD__ ', '#define __linux__ ')) for line in macros), 'Firmware compiler ABI mismatch')
    for name in ('as', 'ld'):
        selected = Path(capture([tools['gcc'], '-print-prog-name=' + name]).strip())
        require(selected.is_absolute() and selected.resolve(strict=True) == tools[name].resolve(strict=True), 'Firmware compiler tool selection mismatch: ' + name)
    for name in ('as', 'ld', 'readelf'):
        version = capture([tools[name], '--version']).splitlines()[0]
        require(version.startswith('GNU ') and ' 2.47' in version, 'Firmware Binutils 2.47 required: ' + name)
    return tools


def assembly_probe(tools, work):
    directory = work / 'assembly-check'
    directory.mkdir()
    source, output = directory / 'firmware.S', directory / 'firmware.o'
    source.write_text('.syntax unified\n.thumb\n.text\n.global firmware_probe\n.type firmware_probe, %function\n.thumb_func\nfirmware_probe:\n movs r0, #1\n bx lr\n.size firmware_probe, .-firmware_probe\n')
    logged([tools['gcc']] + ARM_FLAGS + ['-c', '-x', 'assembler-with-cpp', source, '-o', output], directory / 'compile.log', quarantine=work)
    header = output.read_bytes()[:52]
    require(len(header) == 52 and header[:7] == b'\x7fELF\x01\x01\x01', 'Firmware object is not ELF32 little-endian')
    kind, machine = struct.unpack_from('<HH', header, 16)
    flags = struct.unpack_from('<I', header, 36)[0]
    require(kind == 1 and machine == 40 and flags & 0xff000000 == 0x05000000, 'Firmware object is not relocatable ARM EABI5')
    (directory / 'attributes.txt').write_text(capture([tools['readelf'], '-hA', output]))
    (directory / 'sha256.txt').write_text(digest_rows([source, output]))


def build_main(args):
    target, args = parse_firmware(args)
    require(len(args) in (4, 5), 'Usage: build-firmware.py --target arm-none-eabi PKGSRC ARCHIVE TOOLDIR [MATH] NEW_WORK --sdk-source SOURCE')
    values = [build_path(value) for value in args]
    pkgsrc, archive, tools = values[:3]
    work, count = new_path(values[-1]), jobs()
    math = values[3] if len(values) == 5 else os.environ.get('EMBER_HOST_MATH_PREFIX')
    make = tools / 'bin/nbgmake'
    require(os.access(make, os.X_OK), 'Bootstrap GNU make missing')
    if math:
        math = check_math(math)
    audit_source(pkgsrc, archive, runtime=False)
    cc, cxx = host_compilers()
    work.mkdir()
    if not math:
        host_math_main([os.environ.get('EMBER_HOST_MATH_ARCHIVES', str(work / 'host-archives')), str(tools), str(work / 'host-math')])
        math = check_math(work / 'host-math/prefix')
    prefix = work / 'toolchain'
    for directory in (work / 'build', prefix, prefix / 'bin'):
        directory.mkdir()
    pipeline._build_binutils(target, str(work / 'binutils'), make_override=make)
    relocate_binutils(work / 'binutils/prefix', prefix, TRIPLET, work)
    recipe = pkgsrc / 'lang/gcc16'
    receipt = platform.platform() + '\nmode=firmware\ntarget=' + target + '\ntriplet=' + TRIPLET + '\nsysroot=\nlanguages=c\nhost_cc=' + cc + '\nhost_cxx=' + cxx + '\nhost_math=' + str(math) + '\njobs=' + count + '\n'
    receipt += capture([cc, '--version']) + capture([cc, '-dumpmachine']) + capture([cxx, '--version'])
    receipt += digest_rows([archive, recipe / 'distinfo'] + sorted((recipe / 'patches').glob('patch-*')) + [math / 'lib' / ('lib' + name + '.a') for name in ('gmp', 'mpfr', 'mpc')])
    receipt += digest_rows(policy_sources() + sorted(pipeline.HERE.glob('*.py'))) + (work / 'binutils/inputs.txt').read_text()
    (work / 'inputs.txt').write_text(receipt)
    logged([cc, '-O2', '-I' + str(math / 'include'), pipeline.HERE / 'tests/host-gmp.c', math / 'lib/libgmp.a', '-o', work / 'host-gmp'], work / 'host-gmp-build.log', quarantine=work)
    logged([work / 'host-gmp'], work / 'host-gmp.log', quarantine=work)
    logged([work / 'host-gmp', 'timer'], work / 'host-gmp.log', append=True, quarantine=work)
    prepare_source(pkgsrc, archive, work / 'src', runtime=False, quarantine=work)
    configure = [work / 'src/configure', '--target=' + TRIPLET, '--prefix=' + str(prefix), '--without-headers', '--disable-shared', '--disable-threads', '--enable-languages=c', '--disable-bootstrap', '--disable-multilib', '--disable-nls', '--without-isl', '--with-cpu=cortex-m4', '--with-mode=thumb', '--with-float=soft']
    configure += ['--with-' + name + '=' + str(math) for name in ('gmp', 'mpfr', 'mpc')] + ['--with-as=' + str(prefix / 'bin' / (TRIPLET + '-as')), '--with-ld=' + str(prefix / 'bin' / (TRIPLET + '-ld'))]
    flags = os.environ.get('HOST_CPPFLAGS', '')
    env = {'CC': cc, 'CXX': cxx, 'CPPFLAGS': flags, 'CFLAGS': '-O2 ' + flags, 'CXXFLAGS': '-O2 ' + flags, 'LDFLAGS': os.environ.get('HOST_LDFLAGS', '')}
    with (work / 'inputs.txt').open('a') as receipt_file:
        receipt_file.write('configure=' + ' '.join(str(value) for value in configure[1:]) + '\nhost_cppflags=' + flags + '\nhost_ldflags=' + env['LDFLAGS'] + '\n')
    logged(configure, work / 'configure.log', env, work / 'build', quarantine=work)
    logged([make, '-j' + count, 'all-gcc'], work / 'build.log', env, work / 'build', quarantine=work)
    logged([make, 'install-gcc'], work / 'install.log', env, work / 'build', quarantine=work)
    assembly_probe(check_compiler(prefix), work)
    print('GCC16 firmware C frontend built: ' + str(prefix))
    print('No target runtime or application sysroot was built. Firmware execution remains separate.')
