#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted by OpenAI Codex (GPT-6).
"""Build the pinned Linux hardware UMD diagnostic on native AArch64 GCC16."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import tarfile
import urllib.request

REVISION = 'f35bac0513a7757f8ba6d314d93063214da89c28'
SOURCE_URL = f'https://codeload.github.com/Arm-China/Compass_NPU_Driver/tar.gz/{REVISION}'
SOURCE_SHA = '3eeb1a66ef96c511b7083543e61df491b867b646cb7ac718a34ce1266e316546'
GCC_IMAGE = 'gcc@sha256:b89e1771f0ac16e3769dd351ea8e07a6676aa690a76339c16e36c761eaaaf0f9'
OWNER = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def run(log, command, *, cwd=None, timeout=180):
    log.with_suffix(log.suffix + '.command').write_text(shlex.join(map(str, command)) + '\n')
    env = os.environ.copy()
    for key in ('CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH',
                'COMPILER_PATH', 'GCC_EXEC_PREFIX', 'MAKEFLAGS', 'MFLAGS',
                'LD_PRELOAD', 'LD_LIBRARY_PATH', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS'):
        env.pop(key, None)
    with log.open('wb') as stream:
        result = subprocess.run(list(map(str, command)), cwd=cwd, env=env,
                                stdout=stream, stderr=subprocess.STDOUT,
                                timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f'command failed ({result.returncode}): {log}\n{log.read_text()[-6000:]}')
    return log.read_text()


def download(url, maximum):
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read(maximum + 1)
    if len(data) > maximum:
        raise RuntimeError('download exceeds size limit: ' + url)
    return data


def extract(data, destination):
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        total = 0
        for member in archive.getmembers():
            parts = Path(member.name).parts
            if not parts or member.name.startswith('/') or '..' in parts:
                raise RuntimeError('unsafe archive member')
            relative = Path(*parts[1:])
            if member.islnk() or not (member.isdir() or member.isfile() or member.issym()):
                raise RuntimeError('unsupported archive member')
            total += member.size
            if total > 20 * 1024 * 1024:
                raise RuntimeError('unpacked source exceeds 20 MiB')
            path = destination / relative
            if not path.resolve().is_relative_to(destination.resolve()):
                raise RuntimeError('archive path escapes source')
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif member.issym():
                target = Path(member.linkname)
                if target.is_absolute() or not (path.parent / target).resolve().is_relative_to(destination.resolve()):
                    raise RuntimeError('archive symlink escapes source')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(target)
            elif relative.parts:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.extractfile(member).read())


def elf_bounds(text, name):
    if not all(token in text for token in ('ELF64', 'little endian', 'AArch64')):
        raise RuntimeError('not Linux AArch64 ELF: ' + name)
    needed = re.findall(r'\(NEEDED\).*\[([^\]]+)\]', text)
    allowed = {'libm.so.6', 'libc.so.6', 'libpthread.so.0', 'libdl.so.2', 'ld-linux-aarch64.so.1'}
    if not set(needed) <= allowed:
        raise RuntimeError(f'unexpected dynamic runtime in {name}: {needed}')
    if re.search(r'\((?:RPATH|RUNPATH)\)', text):
        raise RuntimeError('runtime path forbidden: ' + name)
    if re.search(r'GLIBCXX_|CXXABI_|GCC_[0-9]', text):
        raise RuntimeError('shared GCC runtime symbol requirement: ' + name)
    versions = sorted(set(re.findall(r'GLIBC_(\d+(?:\.\d+)+)', text)),
                      key=lambda v: tuple(map(int, v.split('.'))))
    if versions and tuple(map(int, versions[-1].split('.'))) > (2, 43):
        raise RuntimeError('glibc requirement exceeds Ubuntu 26.04 diagnostic boundary')
    return dict(needed=needed, glibc_versions=versions, gcc_runtime='static, excluded from exports')


def build(work, output):
    if platform.system() != 'Linux' or platform.machine() != 'aarch64':
        raise RuntimeError('native Linux/AArch64 builder required; no emulation')
    for path in (work, output):
        if not path.is_absolute() or path.exists() or any(c.isspace() for c in str(path)):
            raise RuntimeError('new absolute paths without whitespace required')
        if shutil.disk_usage(path.parent).free < 2 * 1024 ** 3:
            raise RuntimeError('at least 2 GiB free space required')
    work.mkdir()
    output.mkdir()
    logs, source, objects = work / 'logs', work / 'source', work / 'obj'
    logs.mkdir()
    source.mkdir()
    for folder in ('lib', 'bin', 'source', 'licenses'):
        (output / folder).mkdir()
    if run(logs / 'gxx-version.log', ['g++', '-dumpfullversion']).strip() != '16.2.0':
        raise RuntimeError('GCC 16.2.0 required')
    target = run(logs / 'gxx-target.log', ['g++', '-dumpmachine']).strip()
    if not target.startswith('aarch64') or 'linux' not in target:
        raise RuntimeError('Linux AArch64 GCC target required')
    for tool in ('g++', 'ld', 'ar', 'readelf', 'make', 'cppcheck', 'valgrind'):
        run(logs / (tool.replace('+', 'x') + '-full-version.log'), [tool, '--version'])
    data = download(SOURCE_URL, 4 * 1024 * 1024)
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA:
        raise RuntimeError('source archive SHA256 mismatch')
    (output / 'source' / 'Compass_NPU_Driver.tar.gz').write_bytes(data)
    extract(data, source)
    umd = source / 'Linux/driver/umd'
    header = umd / 'include/kmd/armchina_aipu.h'
    if digest(header) != 'bb46f89f293c5d4a395a90d0c1bfc9967f87cb7517f5988225a7230fdd971880':
        raise RuntimeError('pinned UAPI header differs')
    shutil.copy2(umd / 'LICENSE.TXT', output / 'licenses' / 'Compass-UMD-Apache-2.0.txt')
    for name in ('COPYING.RUNTIME', 'COPYING3', 'COPYING3.LIB'):
        url = f'https://raw.githubusercontent.com/gcc-mirror/gcc/releases/gcc-16.2.0/{name}'
        (output / 'licenses' / ('GCC-' + name)).write_bytes(download(url, 100000))
    wrapper = work / 'cxx'
    compiler = Path(shutil.which('g++')).resolve()
    # Every invocation records real options for analysis and compiler input receipts.
    wrapper.write_text('#!/bin/sh\nset -eu\n' +
                       f'exec {shlex.quote(str(compiler))} -MD -static-libstdc++ -static-libgcc '
                       '-Wl,-z,defs -Wl,--exclude-libs,ALL -Wl,-t "$@"\n')
    wrapper.chmod(0o755)
    context = umd / 'src/common/context.cpp'
    pristine_context = context.read_bytes()
    if digest(context) != 'ba6236e185ab0d33bf7407f7f03d73aa78f1273ee91504f99902422905b25ab9':
        raise RuntimeError('unexpected original context source')
    syntax_command = [str(compiler), '-std=c++14', '-Wall', '-Werror', '-O2',
                      '-DZHOUYI_V12', '-DZHOUYI_V3', '-DRTDEBUG=0',
                      '-DMACRO_UMD_VERSION="6.0.0"',
                      '-Iinclude', '-Isrc', '-Isrc/common', '-I3rdparty',
                      '-fsyntax-only', 'src/common/context.cpp']
    original = subprocess.run(syntax_command, cwd=umd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=60, check=False)
    (logs / 'context-pristine-red.log').write_bytes(original.stdout)
    if original.returncode == 0 or b'overloaded-virtual' not in original.stdout:
        raise RuntimeError('original context did not reproduce the expected GCC16 diagnostic')
    patch = OWNER / 'patches/0004-linux-f35-unused-super-graph.patch'
    patch_output = run(logs / 'patch.log', ['patch', '-f', '-N', '-F0', '-p1', '-i', patch], cwd=source)
    if re.search(r'offset|fuzz|FAILED|Reversed', patch_output, re.I):
        raise RuntimeError('patch did not apply exactly')
    if digest(context) != '52be95aa56bd7f2403123509dbc82f5ed401bd98cf45ddaca95c92a7635b6276':
        raise RuntimeError('unexpected patched context source')
    run(logs / 'context-patched-green.log', syntax_command, cwd=umd)
    patched_context = context.read_bytes()
    arguments = [
        'BUILD_TARGET_PLATFORM=hw', 'BUILD_AIPU_VERSION=aipu_v3',
        'BUILD_UMD_API_TYPE=standard_api', 'BUILD_DEBUG_FLAG=release', 'BUILD_ANDROID_NDK=',
        'COMPASS_DRV_BTENVAR_UMD_V_MAJOR=6', 'COMPASS_DRV_BTENVAR_UMD_V_MINOR=0.0',
        'COMPASS_DRV_BTENVAR_UMD_SO_NAME=libaipudrv.so.6',
        'COMPASS_DRV_BTENVAR_UMD_SO_NAME_FULL=libaipudrv.so.6.0.0',
        'COMPASS_DRV_BTENVAR_UMD_A_NAME_FULL=libaipudrv.a',
        f'COMPASS_DRV_BTENVAR_UMD_BUILD_DIR={objects}', f'BUILD_AIPU_DRV_ODIR={output / "lib"}',
        f'CXX={wrapper}', 'AR=ar',
    ]
    # The unmodified upstream make graph does not order directory creation before objects.
    run(logs / 'directories.log', ['make', *arguments, 'build-repo'], cwd=umd)
    transcript = run(logs / 'build.log', ['make', '-j2', *arguments, 'standard_api'], cwd=umd, timeout=600)
    objfiles = sorted(objects.rglob('*.o'))
    if len(objfiles) != 24 or any('simulator' in str(p) for p in objfiles):
        raise RuntimeError('expected exactly 24 hardware standard_api translation units')
    commands = []
    include_output = run(logs / 'compiler-includes.log', ['g++', '-E', '-v', '-x', 'c++', '/dev/null'])
    include_match = re.search(r'#include <\.\.\.> search starts here:\n(.*?)End of search list\.', include_output, re.S)
    if not include_match:
        raise RuntimeError('cannot determine real GCC system include directories')
    system_includes = [line.strip() for line in include_match.group(1).splitlines() if line.strip()]
    builtin_text = run(logs / 'compiler-builtins.log', ['g++', '-dM', '-E', '-x', 'c++', '/dev/null'])
    macro_names = {'__GNUC__', '__GNUC_MINOR__', '__GNUC_PATCHLEVEL__', '__aarch64__',
                   '__linux__', '__LP64__', '__BYTE_ORDER__', '__ORDER_LITTLE_ENDIAN__'}
    macros = []
    for line in builtin_text.splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) == 3 and parts[1] in macro_names:
            macros.append('-D' + parts[1] + '=' + parts[2])
    analysis_options = [value for path in system_includes for value in ('-isystem', path)] + macros
    for line in transcript.splitlines():
        if line.startswith(str(wrapper) + ' ') and ' -c ' in line:
            argv = shlex.split(line)
            if any('SIMULATION' in arg or 'BUILD_PYTHON_API' in arg for arg in argv):
                raise RuntimeError('unexpected simulator/Python build')
            commands.append(dict(directory=str(umd), file=argv[argv.index('-c') + 1],
                                 arguments=[str(compiler), '-MD', *analysis_options, *argv[1:]]))
    if len(commands) != 24:
        raise RuntimeError('missing real compile commands')
    database = work / 'compile_commands.json'
    write_json(database, commands)
    analyze = ['cppcheck', '--project=' + str(database), '--enable=warning,performance,portability',
               '--platform=unix64', '--check-level=normal', '--template=gcc']
    try:
        context.write_bytes(pristine_context)
        before_analysis = run(logs / 'cppcheck-pristine.log', analyze, timeout=600)
    finally:
        context.write_bytes(patched_context)
    after_analysis = run(logs / 'cppcheck-patched.log', analyze, timeout=600)
    def findings(text):
        return {re.sub(r':\d+(?::\d+)?:', ':LINE:', line) for line in text.splitlines()
                if ': warning:' in line or ': error:' in line}
    introduced = sorted(findings(after_analysis) - findings(before_analysis))
    write_json(logs / 'cppcheck-comparison.json', dict(
        inherited=sorted(findings(after_analysis) & findings(before_analysis)), introduced=introduced))
    if introduced:
        raise RuntimeError('patch introduced new Cppcheck diagnostics')
    consumer = output / 'bin/compass-linux-no-device'
    shutil.copy2(OWNER / 'tests/linux-no-device.cpp', output / 'source')
    run(logs / 'consumer-build.log', [wrapper, '-std=c++14', '-Wall', '-Wextra', '-Werror', '-O2',
                                    '-I' + str(umd / 'include'), '-pthread',
                                    OWNER / 'tests/linux-no-device.cpp', '-ldl', '-o', consumer], timeout=180)
    library = output / 'lib/libaipudrv.so.6.0.0'
    elf = {}
    for path in (library, consumer):
        text = run(logs / (path.name + '.elf.log'), ['readelf', '-h', '-d', '--version-info', path])
        elf[path.name] = elf_bounds(text, path.name)
    if '[libaipudrv.so.6]' not in (logs / (library.name + '.elf.log')).read_text():
        raise RuntimeError('wrong library SONAME')
    run(logs / 'no-device.log', ['timeout', '--kill-after=5', '30', consumer, library])
    foreign_source = work / 'foreign-vdso.cpp'
    foreign_source.write_text('extern "C" const int compass_foreign_vdso = 1;\n')
    foreign = work / 'linux-vdso.so.1'
    run(logs / 'foreign-build.log', [wrapper, '-shared', '-fPIC', foreign_source, '-o', foreign])
    # A real additional DSO with a vDSO-like basename must fail the loader inventory.
    control = subprocess.run(['timeout', '--kill-after=5', '30', str(consumer), str(library), str(foreign)],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40, check=False)
    (logs / 'foreign-rejection.log').write_bytes(control.stdout)
    if control.returncode != 1 or b'foreign loaded provider' not in control.stdout:
        raise RuntimeError('foreign-library causal control did not fail for the expected reason')
    run(logs / 'memcheck.log', ['timeout', '--kill-after=5', '90', 'valgrind', '--tool=memcheck',
                              '--leak-check=full', '--show-leak-kinds=all', '--track-origins=yes',
                              '--errors-for-leak-kinds=definite,indirect,possible', '--error-exitcode=97',
                              consumer, library], timeout=100)
    inputs = {}
    for path in objects.rglob('*.d'):
        text = path.read_text().replace('\\\n', ' ')
        for item in shlex.split(text.split(':', 1)[1]):
            dependency = (umd / item).resolve()
            if not dependency.is_file():
                raise RuntimeError('unresolved compiler dependency: ' + str(dependency))
            inputs[str(dependency)] = digest(dependency)
    for tool in ('g++', 'ld', 'ar', 'readelf', 'make', 'cppcheck', 'valgrind'):
        path = Path(shutil.which(tool)).resolve()
        inputs[str(path)] = digest(path)
    for name in ('libstdc++.a', 'libgcc.a', 'libgcc_eh.a'):
        path = Path(run(logs / (name + '.path.log'), ['g++', '-print-file-name=' + name]).strip()).resolve()
        if not path.is_file():
            raise RuntimeError('unresolved static GCC runtime: ' + name)
        inputs[str(path)] = digest(path)
    write_json(output / 'source/build-inputs.json', inputs)
    write_json(output / 'receipt.json', dict(
        source_url=SOURCE_URL, source_revision=REVISION, source_sha256=SOURCE_SHA,
        uapi_sha256=digest(header), umd_version='6.0.0', build='hardware standard_api aipu_v3',
        patches=[dict(name=patch.name, sha256=digest(patch),
                      context_pristine_sha256=hashlib.sha256(pristine_context).hexdigest(),
                      context_patched_sha256=hashlib.sha256(patched_context).hexdigest())],
        compiler='GCC 16.2.0', gcc_image=GCC_IMAGE, target=target, units=len(objfiles), elf=elf,
        gcc_source_url='https://gcc.gnu.org/pub/gcc/releases/gcc-16.2.0/gcc-16.2.0.tar.xz',
        analysis='Cppcheck of actual commands, GCC include paths and selected target builtins; not all compiler intrinsics are modeled. Unchanged upstream findings retained.',
        boundary='Linux diagnostic only. No /dev/aipu, ioctls, model or physical NPU execution. No certification.',
    ))
    shutil.copytree(logs, output / 'logs')
    shutil.copy2(OWNER / 'linux-candidate.py', output / 'source')
    shutil.copy2(patch, output / 'source')
    shutil.copy2(OWNER / 'linux-diagnostic.md', output / 'source')
    free_before = shutil.disk_usage(work.parent).free
    # The checked original archive and exact adaptation patch are retained above.
    # All logs, unique consumer source and build-input receipts are already copied.
    shutil.rmtree(work)
    write_json(output / 'cleanup.json', dict(removed=[str(work)],
               absent=not work.exists(), free_before=free_before,
               free_after=shutil.disk_usage(work.parent).free))
    files = sorted(path for path in output.rglob('*') if path.is_file())
    (output / 'SHA256SUMS').write_text(''.join(f'{digest(path)}  {path.relative_to(output)}\n' for path in files))
    print(json.dumps(dict(status='pass', output=str(output), units=len(objfiles)), sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.work, args.output)


if __name__ == '__main__':
    main()
