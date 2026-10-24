#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A bounded package metadata migration.
import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
import tarfile
sys.dont_write_bytecode = True
from llvm_host import load_sdk, query, log_run

SCRIPTS = {'bin/analyze-build': 'tools/scan-build-py/bin/analyze-build', 'bin/git-clang-format': 'tools/clang-format/git-clang-format', 'bin/hmaptool': 'utils/hmaptool/hmaptool', 'bin/intercept-build': 'tools/scan-build-py/bin/intercept-build', 'bin/scan-build-py': 'tools/scan-build-py/bin/scan-build', 'bin/scan-view': 'tools/scan-view/bin/scan-view', 'libexec/analyze-c++': 'tools/scan-build-py/libexec/analyze-c++', 'libexec/analyze-cc': 'tools/scan-build-py/libexec/analyze-cc', 'libexec/intercept-c++': 'tools/scan-build-py/libexec/intercept-c++', 'libexec/intercept-cc': 'tools/scan-build-py/libexec/intercept-cc', 'share/clang/clang-format-diff.py': 'tools/clang-format/clang-format-diff.py', 'share/scan-view/Reporter.py': 'tools/scan-view/share/Reporter.py', 'share/scan-view/startfile.py': 'tools/scan-view/share/startfile.py'}


def prepare_packlist(contents):
    lines = ''.join(line for line in contents.splitlines(keepends=True) if not line.startswith(('@comment MD5:', '@comment Symlink:')))
    return re.sub(r'^@ignore\n[+](?:COMMENT|DESC|BUILD_VERSION|BUILD_INFO|SIZE_PKG|SIZE_ALL|INSTALL|DEINSTALL|DISPLAY)\n', '', lines, flags=re.M)


def prepare(args):
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import write_json
    from emberbsd_sdk.elf import read_elf_dynamic
    parser = argparse.ArgumentParser()
    for name in ('clang', 'lld', 'lit', 'clang-source', 'python', 'cmake', 'readelf', 'pkg-create'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('output')
    options = vars(parser.parse_args(args))
    out = Path(options.pop('output')).absolute()
    if out.exists():
        raise ValueError('Output exists: ' + str(out))
    options = {k: str(Path(v).absolute()) for k, v in options.items()}
    if not all(Path(p).exists() for p in options.values()):
        raise ValueError('Missing explicit package/source/tool input')
    version = query([options['python'], '--version'])
    if not re.match(r'^Python 3\.15\.', version):
        raise ValueError('Expected host Python3.15')
    out.mkdir()
    source_root = Path(__file__).resolve().parents[3]
    source_commit = query(['git', '-C', str(source_root), 'rev-parse', 'HEAD'])
    receipt = dict(source_commit=source_commit, helper_sha256=sha256_file(__file__), operation='repackage; no C/C++ compilation or target installation', python=version, cmake=query([options['cmake'], '--version']).splitlines()[0], packages={})
    old_rpath = b'/usr/pkg/gcc16/lib:/usr/pkg/lib:/usr/pkg/lib/python3.14/config-3.14'
    new_rpath = b'/usr/pkg/gcc16/lib:/usr/pkg/lib'
    for kind in ('clang', 'lld', 'lit'):
        archive = options[kind]
        initial_archive_hash = sha256_file(archive)
        stage = out / kind
        stage.mkdir()
        with tarfile.open(archive) as package:
            for member in package.getmembers():
                if member.name.startswith('/') or '..' in member.name.split('/') or any(ord(c) < 32 for c in member.name):
                    raise ValueError('Invalid archive path')
            package.extractall(stage, filter='data')
        contents = (stage / '+CONTENTS').read_text()
        name = 'py315-llvm-lit-23.1.4' if kind == 'lit' else kind + '-23.1.4'
        if '@name ' + name + '\n' not in contents or '@cwd /usr/pkg\n' not in contents:
            raise ValueError('Wrong package or prefix')
        build = (stage / '+BUILD_INFO').read_text()
        if not re.search(r'^OPSYS=NetBSD$', build, re.M) or not re.search(r'^MACHINE_ARCH=aarch64$', build, re.M):
            raise ValueError('Expected target NetBSD/aarch64 package')
        payload, skip = [], False
        for line in contents.splitlines():
            if skip:
                skip = False
            elif line == '@ignore':
                skip = True
            elif line and not line.startswith('@'):
                if line.startswith('/') or any(p in ('', '.', '..') for p in line.split('/')):
                    raise ValueError('Unsafe payload path')
                payload.append(line)
        last = None
        for line in contents.splitlines():
            if line.startswith('@comment MD5:'):
                if not last or hashlib.md5((stage / last).read_bytes()).hexdigest() != line.removeprefix('@comment MD5:'):
                    raise ValueError('Wrong input MD5: ' + str(last))
            elif line.startswith('@comment Symlink:'):
                if not last or os.readlink(stage / last) != line.removeprefix('@comment Symlink:'):
                    raise ValueError('Wrong input link: ' + str(last))
            elif line in payload:
                last = line

        def state(path):
            return dict(symlink=os.readlink(path)) if path.is_symlink() else dict(sha256=sha256_file(path))

        before = {rel: state(stage / rel) for rel in payload}
        expected, changes = dict(before), {}
        elf_inodes = set()
        for rel in payload:
            path = stage / rel
            if not path.is_symlink():
                with path.open('rb') as handle:
                    if handle.read(4) == b'\x7fELF':
                        elf_inodes.add(path.stat().st_ino)
        if kind == 'clang':
            for rel, source_rel in SCRIPTS.items():
                path, source = stage / rel, Path(options['clang_source'], source_rel)
                data = path.read_bytes()
                if not data.startswith(b'#!/usr/pkg/bin/python3.14\n') or data.splitlines(keepends=True)[1:] != source.read_bytes().splitlines(keepends=True)[1:]:
                    raise ValueError('Unexpected interpreter or upstream script: ' + rel)
                mode = path.stat().st_mode & 0o777
                path.chmod(mode | 0o200)
                path.write_bytes(data.replace(b'#!/usr/pkg/bin/python3.14\n', b'#!/usr/pkg/bin/python3.15\n', 1))
                path.chmod(mode)
                expected[rel] = state(path)
                changes[rel] = dict(kind='interpreter only', upstream=source_rel, upstream_sha256=sha256_file(source))
            log_run(out / 'py-compile.log', [options['python'], '-B', '-c', 'import pathlib,sys; [compile(pathlib.Path(p).read_bytes(), p, "exec") for p in sys.argv[1:]]', *[str(stage / rel) for rel in SCRIPTS]])
        changed_inodes = {}
        for rel in payload:
            path = stage / rel
            if path.is_symlink() or path.stat().st_ino not in elf_inodes:
                continue
            inode = path.stat().st_ino
            if inode in changed_inodes:
                expected[rel], changes[rel] = changed_inodes[inode]
                continue
            data = path.read_bytes()
            dynamic = read_elf_dynamic(path, machine=183)
            if any('libpython' in name for name in dynamic['needed']):
                raise ValueError('Unexpected libpython dependency: ' + rel)
            offset = data.find(old_rpath)
            if offset >= 0:
                if kind != 'clang' or data.find(old_rpath, offset + 1) >= 0:
                    raise ValueError('Unexpected or ambiguous RPATH string: ' + rel)
                cmake = out / 'change-rpath.cmake'
                cmake.write_text('file(RPATH_CHANGE FILE [==[' + str(path) + ']==] OLD_RPATH [==[' + old_rpath.decode() + ']==] NEW_RPATH [==[' + new_rpath.decode() + ']==])\n')
                log_run(out / ('rpath-' + str(len(changes)) + '.log'), [options['cmake'], '-P', str(cmake)])
                wanted = data[:offset] + new_rpath.ljust(len(old_rpath), b'\0') + data[offset + len(old_rpath):]
                if path.read_bytes() != wanted:
                    raise ValueError('Unexpected ELF byte change: ' + rel)
                expected[rel] = state(path)
                changes[rel] = dict(kind='RPATH string only', offset=offset, length=len(old_rpath))
                changed_inodes[inode] = expected[rel], changes[rel]
            dynamic = read_elf_dynamic(path, machine=183)
            paths = (dynamic['rpath'] or '').split(':') + (dynamic['runpath'] or '').split(':')
            if set(paths) - {'', '/usr/pkg/lib', '/usr/pkg/gcc16/lib'}:
                raise ValueError('Unexpected RPATH: ' + rel)
        if {rel: state(stage / rel) for rel in payload} != expected:
            raise ValueError('Unexpected payload change')
        if kind == 'lit' and any((stage / rel).read_bytes().splitlines()[0] != b'#!/usr/pkg/bin/python3.15' for rel in ('bin/lit', 'bin/llvm-lit')):
            raise ValueError('Wrong lit interpreter')
        build += 'EMBERBSD_REPACKAGE_KIND=python315-runtime-metadata\nEMBERBSD_REPACKAGE_INPUT_SHA256=' + initial_archive_hash + '\nEMBERBSD_REPACKAGE_SOURCE=' + source_commit + '\n'
        (stage / '+BUILD_INFO').write_text(build)
        plist = prepare_packlist(contents).replace('@name ' + name + '\n', '@name ' + name + 'nb1\n', 1)
        plist = re.sub(r'^@pkgdep py314-llvm-lit[^\n]*$', '@pkgdep py315-llvm-lit>=23.1.4nb1', plist, flags=re.M)
        if kind in ('clang', 'lit'):
            extra = '@pkgdep python315>=3.15.0' if kind == 'clang' else '@pkgcfl py[0-9]*-llvm-lit-[0-9]*'
            plist = plist.replace('@name ' + name + 'nb1\n', '@name ' + name + 'nb1\n' + extra + '\n', 1)
        if re.search(r'^@pkgdep (?:python314|py314-)', plist, re.M):
            raise ValueError('Old runtime dependency retained')
        plist_path = out / (kind + '.plist')
        plist_path.write_text(plist)
        result_path = out / (name + 'nb1.tgz')
        command = [options['pkg_create'], '-p', str(stage), '-I', '/usr/pkg', '-f', str(plist_path), '-c', str(stage / '+COMMENT'), '-d', str(stage / '+DESC'), '-B', str(stage / '+BUILD_INFO')]
        for entry, flag in {'+BUILD_VERSION': '-b', '+INSTALL': '-i', '+DEINSTALL': '-k', '+DISPLAY': '-D', '+SIZE_PKG': '-s', '+SIZE_ALL': '-S'}.items():
            if (stage / entry).is_file():
                command.extend([flag, str(stage / entry)])
        if (stage / '+REQUIRE').exists():
            raise ValueError('Unexpected +REQUIRE script')
        log_run(out / (kind + '-pkg-create.log'), command + [str(result_path)])
        with tarfile.open(result_path) as package:
            final_contents = package.extractfile('+CONTENTS').read().decode()
        controls = re.findall(r'^@ignore\n([+][^\n]+)\n', final_contents, re.M)
        if len(controls) != len(set(controls)):
            raise ValueError('Duplicate generated package metadata')
        (stage / '+CONTENTS').write_text(final_contents)
        if sha256_file(archive) != initial_archive_hash:
            raise ValueError('Input archive changed during operation')
        receipt['packages'][name] = dict(input_sha256=initial_archive_hash, output=str(result_path), output_sha256=sha256_file(result_path), payload_before=before, payload_after=expected, changes=changes)
    write_json(str(out / 'receipt.json'), receipt)
    print('PASS: package metadata, upstream script bodies, Python3.15 compilation, exact ELF byte changes and remaining payload.')


if __name__ == '__main__':
    from sdk_source import exit_error, install_signal_handlers
    install_signal_handlers()
    try:
        _, args = load_sdk()
        prepare(args)
    except Exception as error:
        exit_error(error)
