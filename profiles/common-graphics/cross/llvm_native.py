# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Inspect and retain real native runtimes.
import os
from pathlib import Path
import re
import shutil
import struct
import llvm_sdk as sdk


def platform(triple):
    if re.fullmatch(r'(?:arm64|aarch64|x86_64)-apple-darwin[0-9.]*', triple):
        return 'darwin'
    if re.fullmatch(r'(x86_64|aarch64)-(?:unknown-)?linux-gnu', triple):
        return 'linux-gnu'
    raise ValueError('unsupported native LLVM triple: ' + triple)


def machine(triple):
    if platform(triple) != 'linux-gnu':
        raise ValueError('expected native Linux GNU triple')
    return 183 if triple.startswith('aarch64-') else 62


def capture(*command, env=None):
    return sdk.capture(*command, env=env)


def executable(name):
    path = name if name.startswith('/') else shutil.which(name)
    if not path or not os.access(path, os.X_OK) or not Path(path).is_file():
        raise ValueError('missing native tool: ' + name)
    return str(Path(path).resolve(strict=True))


def validate_header(path, roots, *, forbidden):
    if not sdk.safe_absolute(path):
        raise ValueError('unsafe native header dependency: ' + path)
    resolved = str(Path(path).resolve(strict=True))
    if any(resolved == root or resolved.startswith(root + '/') for root in forbidden):
        raise ValueError('native header resolves inside a target tree: ' + path)
    if not any(path.startswith(root + '/') or resolved.startswith(root + '/') for root in roots):
        raise ValueError('unexpected native header dependency: ' + path)
    return resolved


def elf(path, expected_machine):
    from emberbsd_sdk.elf import read_elf_header
    try:
        info = read_elf_header(str(Path(path).resolve(strict=True)), expected_machine)
        if info is None or info['type'] not in (2, 3):
            raise ValueError('wrong ELF type')
    except Exception as error:
        raise ValueError('wrong native ELF architecture: ' + str(path)) from error


def darwin(binary, triple):
    with open(binary, 'rb') as stream:
        header = stream.read(32)
    expected = 0x100000c if triple.startswith(('arm64-', 'aarch64-')) else 0x1000007
    if len(header) != 32 or struct.unpack_from('<III', header)[:2] != (0xfeedfacf, expected) or struct.unpack_from('<I', header, 12)[0] != 2:
        raise ValueError('wrong native Mach-O executable architecture')
    linked = capture('/usr/bin/otool', '-L', binary)
    for line in linked.splitlines()[1:]:
        fields = line.split()
        if not fields or not fields[0].startswith(('/usr/lib/', '/System/Library/')):
            raise ValueError('unexpected native runtime dependency: ' + line.strip())
    return linked + '\n'


def dynamic(path, readelf):
    text = capture(readelf, '-dW', path)
    needed = re.findall(r'\(NEEDED\).*\[([^\]]+)\]', text)
    sonames = re.findall(r'\(SONAME\).*\[([^\]]+)\]', text)
    if len(sonames) > 1:
        raise ValueError('duplicate native SONAME')
    for name in needed + sonames:
        if not re.fullmatch(r'[A-Za-z0-9_+.-]+', name) or '..' in name:
            raise ValueError('unsafe native dependency name: ' + name)
        if name.startswith('libLLVM'):
            raise ValueError('native shared LLVM dependency is unsupported')
    return dict(needed=needed, soname=sonames[0] if sonames else None)


def compiler(cxx, triple, flags):
    if not re.match(r'16\.', capture(cxx, '-dumpfullversion')):
        raise ValueError('Linux helper requires GCC16')
    macros = capture(cxx, '-dM', '-E', '-x', 'c++', '/dev/null')
    if not re.search(r'^#define __GNUC__ 16$', macros, re.M) or re.search(r'^#define __clang__ ', macros, re.M):
        raise ValueError('Linux helper requires genuine GCC16')
    if machine(capture(cxx, '-dumpmachine')) != machine(triple):
        raise ValueError('native compiler and LLVM architectures differ')
    out, err, status = sdk.query(cxx, *flags, '-E', '-v', '-x', 'c++', '/dev/null', '-o', '/dev/null')
    if status:
        raise ValueError('native include search failed: ' + out + err)
    search = re.search(r'#include <\.\.\.> search starts here:\n(.*?)End of search list\.', err, re.S)
    if not search:
        raise ValueError('native compiler did not report include search roots')
    roots = list(dict.fromkeys(str(Path(p.strip()).resolve(strict=True)) for p in search[1].splitlines()))
    if not roots or not all(sdk.safe_absolute(p) and p != '/' for p in roots):
        raise ValueError('unsafe native include root')
    libraries = []
    for name in ('libstdc++.so', 'libgcc_s.so.1'):
        path = capture(cxx, '-print-file-name=' + name)
        if not path.startswith('/') or not Path(path).is_file():
            raise ValueError('native compiler runtime missing: ' + name)
        libraries.append(str(Path(path).resolve(strict=True)))
    return dict(header_roots=roots, compiler_libraries=libraries)


def loaded(text):
    result = {}
    for line in text.splitlines():
        if re.fullmatch(r'\s*linux-vdso(?:64)?\.so\.1 \(0x[0-9a-f]+\)\s*', line):
            continue
        match = re.fullmatch(r'\s*(\S+) => (/\S+) \(0x[0-9a-f]+\)\s*', line)
        if match:
            name, path = match.groups()
        else:
            match = re.fullmatch(r'\s*(/\S+) \(0x[0-9a-f]+\)\s*', line)
            if not match:
                raise ValueError('unresolved native loader entry: ' + line.strip())
            path = match[1]
            name = Path(path).name
        if name in result or not sdk.safe_absolute(path):
            raise ValueError('duplicate or unsafe native loader entry: ' + name)
        result[name] = str(Path(path).resolve(strict=True))
    return result


def retain(binary, work, triple, compiler_libraries, *, forbidden=()):
    readelf = executable(os.environ.get('NATIVE_READELF', 'readelf'))
    ldd = executable('ldd')
    elf(binary, machine(triple))
    interpreters = re.findall(r'\[Requesting program interpreter: ([^\]]+)\]', capture(readelf, '-lW', binary))
    if len(interpreters) != 1 or not sdk.safe_absolute(interpreters[0]):
        raise ValueError('expected one native ELF interpreter')
    interpreter = str(Path(interpreters[0]).resolve(strict=True))
    # Do not inherit loader injection or ambient search paths.
    search = list(dict.fromkeys(str(Path(p).parent) for p in compiler_libraries))
    trace = capture(ldd, binary, env={'LD_LIBRARY_PATH': ':'.join(search)}) + '\n'
    paths = loaded(trace)
    loader_name = Path(interpreters[0]).name
    if paths.get(loader_name) != interpreter:
        raise ValueError('native loader differs from ELF interpreter')
    if set(compiler_libraries) - set(paths.values()):
        raise ValueError('loaded runtime is not the selected GCC16 runtime')
    files = []
    for name, path in paths.items():
        if any(path == root or path.startswith(root + '/') for root in forbidden):
            raise ValueError('native runtime resolves inside a target tree')
        elf(path, machine(triple))
        info = dynamic(path, readelf)
        if info['soname'] != name:
            raise ValueError('native runtime filename differs from its SONAME')
        files.append(dict(name=name, source=path, path='native/lib/' + name, sha256=sdk.digest(path), needed=info['needed']))
    info = dynamic(binary, readelf)
    needed = info['needed'] + [name for file in files for name in file['needed']]
    if set(needed) - set(paths):
        raise ValueError('native runtime closure is incomplete')
    reachable = {loader_name, *info['needed']}
    while True:
        more = {name for file in files if file['name'] in reachable for name in file['needed']}
        if not more - reachable:
            break
        reachable.update(more)
    if set(paths) != reachable:
        raise ValueError('native loader reports an unexplained library')
    (Path(work) / 'native/lib').mkdir(parents=True)
    for file in files:
        shutil.copyfile(file['source'], Path(work) / file['path'])
        os.chmod(Path(work) / file['path'], 0o755)
        if sdk.digest(file['source']) != file['sha256']:
            raise ValueError('native runtime changed while copying')
    receipt = dict(format='ember-llvm-native-runtime-v1', triple=triple, loader='native/lib/' + loader_name,
                   files=files, tools={p: sdk.digest(p) for p in (readelf, ldd)}, original_loader_output=trace)
    verify(binary, work, receipt)
    return receipt


def verify(binary, work, receipt):
    if receipt['format'] != 'ember-llvm-native-runtime-v1':
        raise ValueError('unsupported native runtime receipt')
    expected_machine = machine(receipt['triple'])
    elf(binary, expected_machine)
    files = receipt['files']
    if len({f['name'] for f in files}) != len(files):
        raise ValueError('duplicate native runtime payload')
    expected = {}
    for file in files:
        name, relative = file['name'], file['path']
        if not re.fullmatch(r'[A-Za-z0-9_+.-]+', name) or '..' in name or relative != 'native/lib/' + name:
            raise ValueError('unsafe retained native runtime path')
        path = Path(work).resolve(strict=True) / relative
        if not path.is_file() or path.is_symlink() or sdk.digest(path) != file['sha256']:
            raise ValueError('retained native runtime changed')
        if path.resolve(strict=True) != path:
            raise ValueError('retained native runtime escapes the payload')
        elf(path, expected_machine)
        expected[name] = str(path)
    loader = receipt['loader']
    if not any(f['path'] == loader for f in files):
        raise ValueError('retained native loader is not in the payload')
    text = capture(str(Path(work) / loader), '--inhibit-cache', '--library-path', str(Path(work) / 'native/lib'), '--list', binary)
    if loaded(text) != expected:
        raise ValueError('retained loader resolves outside the copied native closure')
    return text + '\n'


def copy(binary, old, work, receipt, *, copied_binary):
    verify(binary, old, receipt)
    for file in receipt['files']:
        destination = Path(work) / file['path']
        if os.path.lexists(destination):
            raise ValueError('native runtime destination exists')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(old) / file['path'], destination)
        destination.chmod(0o755)
    verify(copied_binary, work, receipt)


def launcher(receipt):
    if not receipt:
        return 'exec "$base/bin/llvm-config.real" "$@"'
    loader = receipt['loader']
    if not re.fullmatch(r'native/lib/[A-Za-z0-9_+.-]+', loader) or '..' in loader:
        raise ValueError('unsafe native launcher loader')
    return ('unset LD_PRELOAD LD_AUDIT LD_LIBRARY_PATH\n'
            f'exec "$base/{loader}" --inhibit-cache --library-path "$base/native/lib" "$base/bin/llvm-config.real" "$@"')
