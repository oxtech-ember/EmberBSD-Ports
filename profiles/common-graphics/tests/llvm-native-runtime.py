#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real native ELF closure, not LLVM acceptance.
import os
from pathlib import Path
import shutil
import struct
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cross'))
import llvm_sdk as sdk
import llvm_native as native


def test(args):
    if len(args) != 1:
        raise ValueError('usage: HOST_CXX=/absolute/g++ llvm-native-runtime.py --sdk-source SDK ABS_NEW_WORK')
    work = Path(sdk.new_destination(args[0]))
    cxx = os.environ['HOST_CXX']
    if not cxx.startswith('/') or not os.access(cxx, os.X_OK):
        raise ValueError('HOST_CXX must be an absolute executable')
    work.mkdir()
    checks = []

    def check(name, condition):
        if not condition:
            raise ValueError('FAIL: ' + name)
        checks.append(name)
        print('PASS: ' + name, flush=True)

    def reject(name, message, callback):
        try:
            callback()
        except ValueError as error:
            check(name, message in str(error))
        else:
            raise ValueError('accepted ' + name)

    def run(name, *command, producer=False):
        if producer:
            sdk.command_file(work / (name + '.command'), command)
            sdk.produce(command, work / (name + '.log'))
            return None
        out, err, status = sdk.query(*command)
        sdk.write_json(work / (name + '.json'), dict(command=command, stdout=out, stderr=err, exit=status))
        if status:
            raise ValueError(name + ' failed: ' + err)
        return out

    check('GNU Linux selectors accept ordinary and unknown-vendor spellings', all(native.platform(p) == 'linux-gnu' for p in ('x86_64-linux-gnu', 'x86_64-unknown-linux-gnu', 'aarch64-linux-gnu', 'aarch64-unknown-linux-gnu')))
    for triple in ('x86_64--linux-gnu', 'aarch64--linux-gnu', 'x86_64-linux-musl', 'aarch64--netbsd', 'riscv64-linux-gnu'):
        reject('rejects unsupported native selector ' + triple, 'unsupported native LLVM triple', lambda: native.platform(triple))
    check('Darwin selector remains available', native.platform('arm64-apple-darwin25.0.0') == 'darwin')
    triple = native.capture(cxx, '-dumpmachine')
    compiler = native.compiler(cxx, triple, [])
    sdk.write_json(work / 'compiler.json', dict(triple=triple, version=native.capture(cxx, '--version'), **compiler))
    check('real GCC16 reports existing native header roots and runtime libraries', bool(compiler['header_roots']) and len(compiler['compiler_libraries']) == 2 and all(Path(p).is_file() for p in compiler['compiler_libraries']))
    other = 'x86_64-linux-gnu' if triple.startswith('aarch64-') else 'aarch64-linux-gnu'
    reject('rejects a compiler/LLVM architecture mismatch', 'architectures differ', lambda: native.compiler(cxx, other, []))
    original = work / 'original'
    (original / 'bin').mkdir(parents=True)
    source = str(Path(__file__).with_suffix('.cpp'))
    binary = str(original / 'bin/llvm-config.real')
    flags = [cxx, '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread', source]
    run('compile', *flags, '-o', binary, producer=True)
    runtime = native.retain(binary, str(original), triple, compiler['compiler_libraries'])
    sdk.write_json(original / 'runtime.json', runtime)
    trace = native.verify(binary, str(original), runtime)
    (work / 'original-loader.txt').write_text(trace)
    check('real copied loader resolves complete native ELF closure inside payload', all(p.startswith(str(original) + '/native/lib/') for p in native.loaded(trace).values()))
    expected = 'PASS: native threads, containers, exceptions and I/O\n'
    check('real GCC16 native contract executes with retained loader and runtime', run('original-run', str(original / runtime['loader']), '--inhibit-cache', '--library-path', str(original / 'native/lib'), binary) == expected)
    direct = work / 'direct-loader'
    (direct / 'bin').mkdir(parents=True)
    direct_binary = str(direct / 'bin/llvm-config.real')
    loader = next(f for f in runtime['files'] if f['path'] == runtime['loader'])
    run('direct-loader-compile', *flags, '-Wl,--no-as-needed', loader['source'], '-Wl,--as-needed', '-o', direct_binary, producer=True)
    check('real native ELF retains interpreter as a direct dependency', loader['name'] in native.dynamic(direct_binary, native.executable(os.environ.get('NATIVE_READELF', 'readelf')))['needed'])
    direct_runtime = native.retain(direct_binary, str(direct), triple, compiler['compiler_libraries'])
    check('direct-loader dependency resolves to one complete retained closure', len(native.loaded(native.verify(direct_binary, str(direct), direct_runtime))) == len(direct_runtime['files']))
    check('direct-loader native program executes with retained runtime', run('direct-loader-run', str(direct / direct_runtime['loader']), '--inhibit-cache', '--library-path', str(direct / 'native/lib'), direct_binary) == expected)
    sealed = work / 'sealed'
    (sealed / 'bin').mkdir(parents=True)
    shutil.copyfile(binary, sealed / 'bin/llvm-config.real')
    (sealed / 'bin/llvm-config.real').chmod(0o755)
    native.copy(binary, str(original), str(sealed), runtime, copied_binary=str(sealed / 'bin/llvm-config.real'))
    check('native seal copies executable, loader and each GCC/system DSO byte for byte', all(sdk.digest(original / p) == sdk.digest(sealed / p) for p in ['bin/llvm-config.real', *[f['path'] for f in runtime['files']]]))
    (sealed / 'bin/llvm-config').write_text('#!/bin/sh\nset -eu\nbase=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)\n' + native.launcher(runtime) + '\n')
    (sealed / 'bin/llvm-config').chmod(0o755)
    original.rename(work / 'retained-original')
    check('sealed native program survives removal of original helper path', run('sealed-run', str(sealed / 'bin/llvm-config')) == expected and all(p.startswith(str(sealed) + '/native/lib/') for p in native.loaded(native.verify(str(sealed / 'bin/llvm-config.real'), str(sealed), runtime)).values()))
    library = next(f for f in runtime['files'] if f['name'] == 'libstdc++.so.6')
    for mutation in ('changed', 'missing', 'symlink'):
        clone = work / mutation
        shutil.copytree(sealed, clone)
        path = clone / library['path']
        if mutation == 'changed':
            with path.open('ab') as stream:
                stream.write(b'changed runtime')
        else:
            path.unlink()
            if mutation == 'symlink':
                path.symlink_to(library['source'])
        reject('rejects ' + mutation + ' copied GCC runtime before loading', 'retained native runtime changed', lambda: native.verify(str(clone / 'bin/llvm-config.real'), str(clone), runtime))
    clone = work / 'escaped'
    shutil.copytree(sealed, clone)
    (clone / 'native/lib').rename(clone / 'outside')
    (clone / 'native/lib').symlink_to('../outside')
    reject('rejects native library-directory symlink escape', 'escapes the payload', lambda: native.verify(str(clone / 'bin/llvm-config.real'), str(clone), runtime))
    wrong = work / 'wrong-machine'
    data = bytearray((sealed / 'bin/llvm-config.real').read_bytes())
    struct.pack_into('<H', data, 18, 183 if native.machine(triple) == 62 else 62)
    wrong.write_bytes(data)
    reject('rejects wrong native ELF machine without executing it', 'wrong native ELF architecture', lambda: native.verify(str(wrong), str(sealed), runtime))
    reject('rejects unresolved loader dependency', 'unresolved native loader entry', lambda: native.loaded('libmissing.so.1 => not found\n'))
    if triple.startswith('x86_64-'):
        reject('rejects duplicate loader entries', 'duplicate or unsafe', lambda: native.loaded('libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x1)\n' * 2))
    sdk.write_json(work / 'receipt.json', dict(scope='Native Linux GCC16 ELF runtime retention and copy only; no LLVM or target metadata acceptance', source_sha256=sdk.digest(source), binary_sha256=sdk.digest(sealed / 'bin/llvm-config.real'), runtime=runtime, checks=checks))
    return 0


if __name__ == '__main__':
    sys.exit(sdk.main(test))
