#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Package the separately required base runtime.
"""Verify and package the audited GCC16 runtime for the installer."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

RUNTIME_DIR = Path(__file__).resolve().parents[1] / 'development-toolchain/runtime/recipe/files'
ARCHIVE = 'runtime-gcc16.tar.xz'
LIMIT = 64 * 1024 * 1024
META = {'+CONTENTS', '+COMMENT', '+DESC', '+BUILD_INFO', '+BUILD_VERSION', '+SIZE_PKG', '+SIZE_ALL'}
RUNTIME_FILES = re.compile(r'gcc16/lib/(?:libgcc_s\.so\.1|libstdc\+\+\.so\.7(?:\.[0-9]+)*)\Z')


def require(condition, message, error=RuntimeError):
    if not condition:
        raise error(message)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def sha512(path):
    digest = hashlib.sha512()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def command(argv, *, env=None):
    process_env = os.environ.copy()
    process_env.update({'COPYFILE_DISABLE': '1', 'LC_ALL': 'C'})
    process_env.pop('TAR_OPTIONS', None)
    if env:
        process_env.update(env)
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=process_env, check=False)
    require(result.returncode == 0,
            'Command failed: ' + str(argv[0]) + ':\n' + result.stdout + result.stderr)
    return result.stdout


def fingerprint(source, runtime):
    names = sorted((runtime.NAME + '.tgz', 'package.sha256', 'provenance.json'))
    require(sorted(path.name for path in source.iterdir()) == names,
            'Input must be the complete runtime.py create output', runtime.Invalid)
    result = {}
    for name in names:
        path = source / name
        require(path.is_file() and not path.is_symlink(),
                'Missing regular runtime input: ' + name, runtime.Invalid)
        result[name] = sha256(path)
    return result


def receipt(source, runtime):
    try:
        result = json.loads((source / 'provenance.json').read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise runtime.Invalid('Invalid runtime provenance JSON') from error
    require(isinstance(result, dict) and set(result) == {'elf', 'files', 'metadata', 'tls_abi'},
            'Invalid runtime provenance schema', runtime.Invalid)
    files = result['files']
    require(isinstance(files, list) and files and len(set(files)) == len(files)
            and all(isinstance(path, str) and RUNTIME_FILES.fullmatch(path) for path in files),
            'Unexpected runtime payload selection', runtime.Invalid)
    required_files = {'gcc16/lib/libgcc_s.so.1', 'gcc16/lib/libstdc++.so.7'}
    require(required_files <= set(files), 'Missing required runtime libraries', runtime.Invalid)

    metadata = result['metadata']
    fixed = {
        'OPSYS': 'NetBSD', 'OS_VERSION': '11.0', 'MACHINE_ARCH': 'x86_64',
        'PKGPATH': 'lang/gcc16-runtime', 'PKGNAME': runtime.NAME,
        'LICENSE': 'gnu-gpl-v3', 'GCC_VERSION': runtime.VERSION,
        'GCC_RUNTIME_SONAME': 'libstdc++.so.7',
        'GCC_RUNTIME_LIBRARIES': 'libgcc,libstdc++',
        'GCC_RUNTIME_SONAMES': 'libgcc_s.so.1,libstdc++.so.7',
        'GCC_RUNTIME_TARGET': 'amd64', 'GCC_RUNTIME_TRIPLET': 'x86_64--netbsd',
        'GCC_RUNTIME_MACHINE_ARCH': 'x86_64',
        'GCC_SOURCE_SHA256': runtime.SOURCE_SHA256,
    }
    hashes = {
        'GCC_RECIPE_SHA256', 'GCC_RECIPE_DISTINFO_SHA256',
        'GCC_RUNTIME_INPUTS_SHA256', 'GCC_RUNTIME_STAGE_SHA256',
        'GCC_RUNTIME_LINKS_SHA256', 'GCC_RUNTIME_CXX_MATH_INPUTS_SHA256',
        'GCC_RUNTIME_CXX_TLS_INPUTS_SHA256', 'EMBERBSD_PKG_CREATE_SHA256',
    }
    optional_modes = {
        'standalone-libstdcxx': {
            'GCC_RUNTIME_BUILD_MODE', 'GCC_RUNTIME_INHERITANCE_SHA256',
            'GCC_RUNTIME_PARENT_INPUTS_SHA256', 'GCC_RUNTIME_PARENT_STAGE_SHA256',
        },
        'libstdcxx-and-runtime-relro-relink': {
            'GCC_RUNTIME_BUILD_MODE', 'GCC_RUNTIME_RELINK_SHA256',
            'GCC_RUNTIME_LOCALE_INPUTS_SHA256',
        },
    }
    optional_fields = set()
    if isinstance(metadata, dict) and 'GCC_RUNTIME_BUILD_MODE' in metadata:
        mode = metadata['GCC_RUNTIME_BUILD_MODE']
        require(mode in optional_modes, 'Unknown runtime build mode', runtime.Invalid)
        optional_fields = optional_modes[mode]
        hashes.update(optional_fields - {'GCC_RUNTIME_BUILD_MODE'})
    expected_fields = (set(fixed) | hashes | optional_fields
                       | {'EMBERBSD_SEED_SOURCE', 'PKGTOOLS_VERSION'})
    require(isinstance(metadata, dict) and set(metadata) == expected_fields,
            'Invalid runtime metadata fields', runtime.Invalid)
    require(all(metadata[key] == value for key, value in fixed.items()),
            'Wrong runtime target, source or provider', runtime.Invalid)
    require(all(isinstance(metadata[key], str) and re.fullmatch(r'[0-9a-f]{64}', metadata[key])
                for key in hashes), 'Invalid runtime source receipts', runtime.Invalid)
    require(isinstance(metadata['EMBERBSD_SEED_SOURCE'], str)
            and re.fullmatch(r'[0-9a-f]{40}', metadata['EMBERBSD_SEED_SOURCE']),
            'Invalid runtime seed source receipt', runtime.Invalid)
    runtime.validate_pkgtools_version(metadata['PKGTOOLS_VERSION'])

    elf = result['elf']
    require(isinstance(elf, dict) and set(elf) == set(files),
            'Invalid runtime ELF receipts', runtime.Invalid)
    require(isinstance(result['tls_abi'], dict) and result['tls_abi'],
            'Missing runtime TLS ABI receipt', runtime.Invalid)
    return result


def unpack_runtime(package, payload, result, runtime):
    expected = set(result['files']) | {
        'share/licenses/gcc16-runtime/' + name for name in runtime.LICENSES
    }
    with tarfile.open(package, 'r:*') as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        metadata_names = set(names) & META
        actual_payload = set(names) - META
        require(len(names) == len(set(names)) and actual_payload == expected,
                'Unexpected runtime package payload: missing='
                + repr(sorted(expected - actual_payload)) + ', extra='
                + repr(sorted(actual_payload - expected)), runtime.Invalid)
        by_name = {member.name: member for member in members}
        for name in expected | metadata_names:
            member = by_name[name]
            destination = payload / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            if member.isfile():
                data = archive.extractfile(member)
                require(data is not None, 'Cannot read runtime package member: ' + name,
                        runtime.Invalid)
                with destination.open('xb') as stream:
                    shutil.copyfileobj(data, stream)
                destination.chmod(member.mode & 0o777)
            elif member.issym() and name in result['files'] and name.startswith('gcc16/lib/'):
                require(member.linkname and not member.linkname.startswith('/'),
                        'Unsafe runtime alias', runtime.Invalid)
                destination.symlink_to(member.linkname)
            else:
                require(False, 'Special file or metadata link in runtime package', runtime.Invalid)


def audit(source, payload, runtime):
    package = source / (runtime.NAME + '.tgz')
    digest_line = (source / 'package.sha256').read_text(encoding='ascii')
    require(digest_line == f'{sha256(package)}  {runtime.NAME}.tgz\n',
            'Runtime package digest mismatch', runtime.Invalid)
    result = receipt(source, runtime)
    unpack_runtime(package, payload, result, runtime)

    for name in result['files']:
        path = payload / name
        if path.is_symlink():
            target = os.readlink(path)
            resolved_name = os.path.normpath(os.path.join(os.path.dirname(name), target))
            require(not target.startswith('/') and resolved_name in result['files'],
                    'Unsafe runtime alias', runtime.Invalid)
        resolved = path.resolve(strict=True)
        try:
            resolved_name = resolved.relative_to(payload).as_posix()
        except ValueError as error:
            raise runtime.Invalid('Runtime alias escapes shipped payload') from error
        require(resolved_name in result['files'], 'Runtime alias escapes shipped payload',
                runtime.Invalid)
        soname = 'libstdc++.so.7' if 'libstdc++' in name else 'libgcc_s.so.1'
        fresh = runtime.ELF(resolved).verify(
            soname, runtime.TARGETS['amd64'], ['libgcc_s.so.1', 'libstdc++.so.7'])
        require(fresh == result['elf'][name], 'Runtime ELF receipt differs from package bytes',
                runtime.Invalid)

    for name in runtime.LICENSES:
        path = payload / 'share/licenses/gcc16-runtime' / name
        require(path.is_file() and not path.is_symlink() and path.stat().st_size > 0,
                'Missing runtime license or exception', runtime.Invalid)

    # The runtime API checks package inventory, metadata, conflicts and prefix.
    runtime.audit_package(package, payload, result)
    build_info = (payload / '+BUILD_INFO').read_text(encoding='utf-8').splitlines()
    for key, value in result['metadata'].items():
        require([line for line in build_info if line.startswith(key + '=')] == [key + '=' + value],
                'Duplicate or changed runtime metadata', runtime.Invalid)

    lines = (payload / '+CONTENTS').read_text(encoding='utf-8').splitlines()
    seen, conflicts, package_names, ignored = [], [], [], []
    index = 0
    files = result['files'] + [
        'share/licenses/gcc16-runtime/' + name for name in runtime.LICENSES
    ]
    while index < len(lines):
        line = lines[index]
        index += 1
        if line == '@cwd /usr/pkg':
            continue
        if line == '@name ' + runtime.NAME:
            package_names.append(line)
            continue
        if line.startswith('@pkgcfl '):
            conflicts.append(line.removeprefix('@pkgcfl '))
            continue
        if line == '@ignore':
            require(index < len(lines), 'Incomplete ignored metadata entry', runtime.Invalid)
            entry = lines[index]
            index += 1
            require(entry in META and entry != '+CONTENTS',
                    'Unexpected ignored runtime metadata', runtime.Invalid)
            ignored.append(entry)
            continue
        require(line in files, 'Unsafe runtime packing-list directive or payload', runtime.Invalid)
        path = payload / line
        if path.is_symlink():
            expected = '@comment Symlink:' + os.readlink(path)
        else:
            expected = '@comment MD5:' + hashlib.md5(path.read_bytes()).hexdigest()
        require(index < len(lines) and lines[index] == expected,
                'Runtime payload digest mismatch: ' + line, runtime.Invalid)
        index += 1
        seen.append(line)

    with tarfile.open(package, 'r:*') as archive:
        archive_names = {member.name for member in archive.getmembers()}
    require(sorted(seen) == sorted(files) and len(package_names) == 1
            and sorted(conflicts) == sorted(runtime.CONFLICTS)
            and len(ignored) == len(set(ignored))
            and sorted(archive_names - {'+CONTENTS'} - set(files)) == sorted(ignored),
            'Runtime packing-list inventory mismatch', runtime.Invalid)
    return result


def publish_noreplace(source, destination):
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == 'darwin':
        function = library.renamex_np
        function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        result = function(os.fsencode(source), os.fsencode(destination), 0x00000004)  # RENAME_EXCL
    elif sys.platform.startswith('linux'):
        function = library.renameat2
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
                             ctypes.c_uint]
        function.restype = ctypes.c_int
        result = function(-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    else:
        raise RuntimeError('Atomic no-replace publication requires macOS or Linux')
    if result != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), os.fspath(destination))


def build(source_arg, output_arg, runtime):
    source = Path(source_arg).resolve(strict=True)
    require(source.is_dir(), 'Runtime create output is not a directory', runtime.Invalid)
    output_arg = Path(os.path.abspath(output_arg))
    require(not os.path.lexists(output_arg), 'Output already exists', runtime.Invalid)
    parent = output_arg.parent.resolve(strict=True)
    output = parent / output_arg.name
    require(not output.is_relative_to(source),
            'Output must be outside the runtime create output', runtime.Invalid)
    hashes = fingerprint(source, runtime)
    tar = os.environ.get('BSDTAR', 'bsdtar')
    require('libarchive' in command([tar, '--version']), 'Use bsdtar/libarchive', runtime.Invalid)

    work = Path(tempfile.mkdtemp(prefix='.gcc16-bundle-', dir=parent))
    try:
        snapshot = work / 'source'
        snapshot.mkdir()
        for name in hashes:
            shutil.copy2(source / name, snapshot / name)
        require(fingerprint(snapshot, runtime) == hashes,
                'Runtime inputs changed while copying', runtime.Invalid)
        inspect = work / 'inspect'
        inspect.mkdir()
        result = audit(snapshot, inspect, runtime)

        inner = work / 'inner'
        (inner / 'All').mkdir(parents=True)
        package = inner / 'All' / (runtime.NAME + '.tgz')
        shutil.copyfile(snapshot / (runtime.NAME + '.tgz'), package)
        package.chmod(0o644)
        package_hash = sha512(package)
        (inner / 'ROOTS').write_text(runtime.NAME + '\n', encoding='ascii')
        (inner / 'PROFILE').write_text('gcc16\n', encoding='ascii')
        (inner / 'SHA512').write_text(
            f'SHA512 ({runtime.NAME}.tgz) = {package_hash}\n', encoding='ascii')

        directory = work / 'result'
        directory.mkdir()
        archive = directory / ARCHIVE
        command([tar, '--no-xattrs', '--no-acls', '--no-fflags', '--format=pax',
                 '--uid', '0', '--gid', '0', '--uname', 'root', '--gname', 'wheel',
                 '-cJf', str(archive), '-C', str(inner), 'All', 'ROOTS', 'SHA512', 'PROFILE'])
        require(archive.stat().st_size <= LIMIT,
                'Runtime bundle exceeds the 64 MiB installer capacity', runtime.Invalid)
        digest = sha512(archive)
        (directory / 'SHA512').write_text(
            f'SHA512 ({ARCHIVE}) = {digest}\n', encoding='ascii')
        runtime_path = RUNTIME_DIR / 'runtime.py'
        provenance = {
            'format': 'emberbsd-installer-gcc16-v1', 'profile': 'gcc16', 'target': 'amd64',
            'source_sha256': hashes, 'runtime_receipt': result,
            'package': {'file': runtime.NAME + '.tgz', 'bytes': package.stat().st_size,
                        'sha256': sha256(package), 'sha512': package_hash},
            'bundle': {'file': ARCHIVE, 'bytes': archive.stat().st_size,
                       'sha512': digest, 'limit_bytes': LIMIT},
            'tools_sha256': {Path(__file__).name: sha256(__file__),
                             runtime_path.name: sha256(runtime_path)},
            'validation': 'Fresh payload, metadata, conflicts, licenses and ELF audit. '
                          'Local receipts are not a source attestation. No target execution.',
        }
        (directory / 'PROVENANCE.json').write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        require(fingerprint(source, runtime) == hashes
                and sha256(package) == hashes[runtime.NAME + '.tgz'],
                'Runtime source or package changed during preparation', runtime.Invalid)
        publish_noreplace(directory, output)
        print(f'SHA512 ({ARCHIVE}) = {digest}')
        print(f'Bundle bytes: {(output / ARCHIVE).stat().st_size}; installer limit: {LIMIT}')
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv):
    sys.path.insert(0, str(RUNTIME_DIR))
    import sdk_source
    arguments = sdk_source.arguments(argv)
    import runtime
    require(len(arguments) == 2,
            'Usage: bundle-gcc16.py RUNTIME_CREATE_OUTPUT NEW_OUTPUT --sdk-source SOURCE',
            runtime.Invalid)
    build(arguments[0], arguments[1], runtime)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as error:
        print('bundle-gcc16: ' + str(error), file=sys.stderr)
        status = getattr(error, 'returncode', None)
        sys.exit((128 - status if status < 0 else status) if status else 1)
