#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Python migration of bundle-plasma.rb at 2313b5f8.
"""Audit an amd64 Plasma closure for installation media. Never install it."""
import sys
sys.dont_write_bytecode = True
import hashlib
import os
from pathlib import Path
import posixpath
import re
import shutil
import tempfile

MANIFESTS = ('packages.sha256', 'install-order.txt', 'roots.txt', 'target.txt')
PROGRAMS = ('startplasma-wayland', 'kwin_wayland', 'plasmashell', 'Xwayland', 'dbus-run-session')
INSTALLER_LIMIT = 512 * 1024 * 1024
PRODUCER_TIMEOUT = 1800
METADATA_LIMIT = 16 * 1024 * 1024


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_sdk(argv):
    global capture_streamed, CommandError, ProcessOwnershipError, paths, sha256_file
    global write_json, publication, sdk_source
    ports = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ports / 'profiles/development-toolchain/runtime/recipe/files'))
    import sdk_source
    args = sdk_source.arguments(argv)
    from emberbsd_sdk import paths, publication, stream, tarstream
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import write_json
    capabilities = ((stream, 'PRODUCER_STREAM_API'), (tarstream, 'TAR_STREAM_API'),
                    (tarstream, 'TAR_HEADER_FACTS_API'), (publication, 'DIRECTORY_PUBLICATION_API'))
    check(all(type(getattr(module, name, None)) is int and getattr(module, name) == 1
              for module, name in capabilities), 'SDK stream/raw-tar/header-facts/publication API1 required')
    publication.require_directory_publication()
    capture_streamed = stream.capture_streamed
    return args, sdk_source.load()


def command(argv, env):
    return capture_streamed([os.fspath(a) for a in argv], env=env,
                            stdout_limit=METADATA_LIMIT, timeout=PRODUCER_TIMEOUT).value


def fingerprint(directory):
    packages = directory / 'packages'
    check(packages.is_dir() and not packages.is_symlink(), 'Missing regular packages directory')
    names = sorted(p.name for p in packages.iterdir())
    check(names, 'Empty package set')
    check(all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+\-]*-[0-9][A-Za-z0-9_.+\-]*\.tgz', name)
              for name in names), 'Unsafe package filename')
    hashes = {}
    for name in [*MANIFESTS, *('packages/' + name for name in names)]:
        path = directory / name
        check(path.is_file() and not path.is_symlink(), 'Missing regular ' + name)
        hashes[name] = sha256_file(path)
    return hashes


def sha512_file(path):
    stream, identity = paths.open_regular(path)
    with stream:
        result = hashlib.file_digest(stream, 'sha512').hexdigest()
    paths.verify_stable(path, identity)
    return result


def source_revision(env):
    root = Path(__file__).resolve().parent
    try:
        revision = command(['git', '-c', 'maintenance.auto=false', '-c', 'gc.auto=0',
                            '-C', root, 'rev-parse', 'HEAD'], env)
    except (FileNotFoundError, CommandError):
        return None
    try:
        changes = command(['git', '-C', root, 'status', '--porcelain'], env)
        clean = not changes
    except CommandError:
        clean = False
    return dict(revision=revision.decode('ascii').strip(), working_tree_clean=clean)


def lines(data):
    return data.splitlines()


def installed_files(contents, archive):
    files, cwd = {}, None
    records = lines(contents)
    index = 0
    while index < len(records):
        line = records[index]
        if line == b'@ignore':
            index += 1
        elif line.startswith(b'@cwd '):
            cwd = line[5:]
        elif line and not line.startswith(b'@'):
            check(cwd is not None and cwd.startswith(b'/'), 'Package has no absolute installation prefix')
            path = posixpath.normpath(posixpath.join(cwd, line))
            following = records[index + 1] if index + 1 < len(records) else b''
            link = following[len(b'@comment Symlink:'):] if following.startswith(b'@comment Symlink:') else None
            check(path not in files, 'Duplicate installed path: ' + os.fsdecode(path))
            files[path] = dict(archive=archive, member=line, symlink=link)
        index += 1
    return files


def executable_provider(files, path, tar, env):
    visited = set()
    while True:
        check(path not in visited, 'Plasma program symlink cycle: ' + os.fsdecode(path))
        visited.add(path)
        entry = files.get(path)
        check(entry is not None, 'Missing Plasma program: ' + os.fsdecode(path))
        if entry['symlink'] is not None:
            path = posixpath.normpath(posixpath.join(posixpath.dirname(path), entry['symlink']))
            continue
        listing = command([tar, '-tvf', entry['archive'], '--', os.fsdecode(entry['member'])], env).splitlines()
        check(len(listing) == 1, 'Ambiguous Plasma program archive entry: ' + os.fsdecode(path))
        mode = listing[0][:10]
        executable = re.fullmatch(rb'[-h][rwxStTs-]{9}', mode) and any(mode[i] in b'xst' for i in (3, 6, 9))
        check(executable, 'Plasma program is not executable: ' + os.fsdecode(path))
        return entry['archive'].name.removesuffix('.tgz')


def build(args, sdk):
    check(len(args) == 2, 'Usage: bundle-plasma.py [--sdk-source SDK] AMD64_PACKAGE_SET NEW_OUTPUT')
    source = Path(paths.canonical_existing(args[0]))
    output = Path(paths.path_string(args[1]))
    check(not os.path.lexists(output), 'Output already exists')
    output = Path(paths.canonical_existing(output.parent)) / output.name
    check(paths.relative_inside(output, source) is None, 'Output must be outside the source package set')
    source_hashes = fingerprint(source)
    tar = os.environ.get('BSDTAR', 'bsdtar')
    env = dict(os.environ, BSDTAR=tar, COPYFILE_DISABLE='1')
    env.pop('TAR_OPTIONS', None)
    check(b'libarchive' in command([tar, '--version'], env), 'Use bsdtar/libarchive')
    cross = Path(__file__).resolve().parents[2] / 'probes/plasma-mobile/toolkit/cross'
    installer, auditor = cross / 'install-package-set.sh', cross / 'prepare-package-set.py'
    workspace = Path(tempfile.mkdtemp(prefix='.' + output.name + '-', dir=output.parent))
    audit_incomplete = retain = False
    try:
        snapshot = workspace / 'source'
        (snapshot / 'packages').mkdir(parents=True)
        for relative, digest in source_hashes.items():
            destination = snapshot / relative
            shutil.copyfile(source / relative, destination)
            shutil.copymode(source / relative, destination)
            check(sha256_file(destination) == digest, 'Source changed while copying: ' + relative)
        command(['sh', installer, '--target', 'amd64', '--verify-only', snapshot], env)
        database = workspace / 'pkgdb'; database.mkdir()
        contents = {}
        order = (snapshot / 'install-order.txt').read_text().splitlines()
        for archive in order:
            path = snapshot / 'packages' / archive
            plist = command([tar, '-xOf', path, '+CONTENTS'], env)
            directory = database / archive.removesuffix('.tgz'); directory.mkdir()
            metadata = [b'+CONTENTS']; records = lines(plist)
            for index, line in enumerate(records):
                if line == b'@ignore':
                    check(index + 1 < len(records), 'Missing ignored metadata entry')
                    if records[index + 1].startswith(b'+'):
                        metadata.append(records[index + 1])
            for entry in metadata:
                check(re.fullmatch(rb'\+[A-Za-z0-9_.-]+', entry), 'Unsafe package metadata name')
                (directory / os.fsdecode(entry)).write_bytes(plist if entry == b'+CONTENTS' else
                    command([tar, '-xOf', path, os.fsdecode(entry)], env))
            contents[archive] = plist
        roots = (snapshot / 'roots.txt').read_text().splitlines()
        index = workspace / 'archives.txt'
        index.write_text(''.join(str(snapshot / 'packages' / name) + '\n' for name in order))
        verified = workspace / 'verified'
        # Retain even when the auditor cannot write its own uncertainty marker.
        audit_incomplete = True
        command([sys.executable, '-B', '-I', '-S', auditor, '--sdk-source', sdk,
                 '--target', 'amd64', database, index, verified, *roots], env)
        audit_incomplete = False
        check(sorted((verified / 'install-order.txt').read_text().splitlines()) == sorted(order),
              'Package set contains archives outside its root dependency closure')
        files = {}
        for archive in order:
            for path, entry in installed_files(contents[archive], verified / 'packages' / archive).items():
                check(path not in files, 'Overlapping package payload: ' + os.fsdecode(path))
                files[path] = entry
        programs = {name: executable_provider(files, b'/usr/pkg/bin/' + name.encode(), tar, env) for name in PROGRAMS}
        payload = workspace / 'payload'; payload.mkdir()
        (verified / 'packages').rename(payload / 'All')
        (payload / 'All').chmod(0o755)
        packages = []
        for name in sorted(order):
            path = payload / 'All' / name; path.chmod(0o644)
            packages.append(dict(file=name, bytes=path.stat().st_size,
                                 sha256=sha256_file(path), sha512=sha512_file(path)))
        (payload / 'ROOTS').write_text('\n'.join(roots) + '\n')
        (payload / 'SHA512').write_text(''.join(f"SHA512 ({p['file']}) = {p['sha512']}\n" for p in packages))
        (payload / 'PROFILE').write_text('plasma\n')
        shutil.rmtree(snapshot)
        result = workspace / 'result'; result.mkdir()
        archive = result / 'desktop-plasma.tar.xz'
        command([tar, '--no-xattrs', '--no-acls', '--no-fflags', '--format=pax',
                 '--uid', '0', '--gid', '0', '--uname', 'root', '--gname', 'wheel',
                 '-cJf', archive, '-C', payload, 'All', 'ROOTS', 'SHA512', 'PROFILE'], env)
        size, digest = archive.stat().st_size, sha512_file(archive)
        (result / 'SHA512').write_text('SHA512 (desktop-plasma.tar.xz) = ' + digest + '\n')
        provenance = dict(format='emberbsd-installer-plasma-v1', profile='plasma',
            target=dict(OPSYS='NetBSD', OS_VERSION='11.0', MACHINE_ARCH='x86_64', OBJECT_FMT='ELF'),
            source_sha256=source_hashes, roots=roots, packages=packages, required_programs=programs,
            producer=source_revision(env),
            tools_sha256={path.name: sha256_file(path) for path in (Path(__file__), installer, auditor)},
            bundle=dict(file='desktop-plasma.tar.xz', bytes=size, sha512=digest),
            installer_capacity=dict(limit_bytes=INSTALLER_LIMIT, fits_current_limit=size <= INSTALLER_LIMIT),
            validation='Fresh native verify-only and full metadata, payload digest and target ELF audit; no target execution')
        write_json(result / 'PROVENANCE.json', provenance)
        check(fingerprint(source) == source_hashes, 'Source package set changed during bundle preparation')
        try:
            publication.publish_directory_noreplace(result, output)
        except OSError as error:
            raise RuntimeError('Cannot publish bundle output: ' + str(error)) from error
        print('SHA512 (desktop-plasma.tar.xz) = ' + digest)
        print(f'Bundle bytes: {size}; current installer limit: {INSTALLER_LIMIT}; fits: {str(size <= INSTALLER_LIMIT).lower()}')
        if size > INSTALLER_LIMIT:
            print('Bundle exceeds the current installer capacity; OS capacity acceptance is required.')
        print('Prepared Plasma bundle: ' + str(output))
    except ProcessOwnershipError as error:
        retain = True
        try:
            write_json(workspace / sdk_source.PRODUCER_QUARANTINE,
                       dict(status='unproven', sid=error.sid, reason=error.reason))
        except Exception as marker_error:
            print('Cannot write quarantine marker: ' + str(marker_error), file=sys.stderr)
        raise
    finally:
        if audit_incomplete or retain:
            print('Retained incomplete auditor workspace: ' + str(workspace), file=sys.stderr)
        else:
            shutil.rmtree(workspace)


def main(argv=None):
    try:
        args, sdk = load_sdk(sys.argv[1:] if argv is None else argv)
        sdk_source.install_signal_handlers()
    except Exception as error:
        print('FAIL: SDK API1 with stream/raw-tar/header-facts/publication capabilities is required: ' + str(error), file=sys.stderr)
        return 1
    try:
        build(args, sdk)
        return 0
    except CommandError as error:
        if error.stdout:
            print(error.stdout.decode('utf-8', 'replace'), file=sys.stderr, end='')
        print('FAIL: ' + str(error), file=sys.stderr)
        return error.returncode if error.returncode >= 0 else 128 - error.returncode
    except Exception as error:
        print('FAIL: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
