#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Python migration of prepare-package-set.rb.
"""Audit and copy a target runtime package closure. Never install a package."""
import sys
sys.dont_write_bytecode = True
import hashlib
import os
from pathlib import Path
import posixpath
import re
import shlex
import shutil
import stat
import tempfile

# Package policy stays here. Generic process, tar and identity mechanisms are SDK.
PRODUCER_TIMEOUT = 300
METADATA_LIMIT = 16 * 1024 * 1024
CHUNK = 1024 * 1024


class AuditError(Exception):
    pass


def check(condition, message):
    if not condition:
        raise AuditError(message)


def records(data):
    parts = data.split(b'\n')
    return [part + b'\n' for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def chomp(line):
    return line[:-2] if line.endswith(b'\r\n') else line[:-1] if line.endswith((b'\r', b'\n')) else line


def display(value):
    return os.fsdecode(value)


def target_metadata(build, context, target):
    for key, value in {'OPSYS': 'NetBSD', 'OS_VERSION': '11.0',
                       'MACHINE_ARCH': target['arch'], 'OBJECT_FMT': 'ELF'}.items():
        wanted = f'{key}={value}\n'.encode()
        check([line for line in records(build) if line.startswith((key + '=').encode())] == [wanted],
              f'Wrong target {key} in {context}')


def llvm_runtime_payload(name, paths):
    check(not re.match(r'\Allvm-devel-[0-9]', name), f'LLVM SDK is forbidden in the desktop runtime closure: {name}')
    check(not re.match(r'\AlibLLVM-[0-9]', name), f'LLVM legacy provider is forbidden in the desktop runtime closure: {name}')
    if not re.match(r'\Allvm-[0-9]', name):
        return
    expected = b'''lib/libLLVM.so.23.1 lib/libLLVM-23.so lib/libLLVM.so
        lib/libLTO.so.23.1 lib/libLTO.so lib/libRemarks.so.23.1 lib/libRemarks.so
        include/llvm/Support/LICENSE.TXT'''.split()
    check(name == 'llvm-23.1.4nb1' and set(paths) == {b'/usr/pkg/' + p for p in expected},
          f'LLVM runtime package has an unprepared identity or SDK/missing payload: {name}')


def relative_name(name):
    if name.startswith(b'./'):
        name = name[2:]
    if name.endswith(b'/'):
        name = name[:-1]
    check(name and not name.startswith(b'/') and not re.search(rb'[\x00-\x1f\x7f]', name) and
          all(part not in (b'', b'.', b'..') for part in name.split(b'/')),
          f'Invalid archive path: {name!r}')
    return name


def package_manifest(contents):
    files, paths, metadata = {}, set(), [b'+CONTENTS']
    prefix = None
    lines = [chomp(line) for line in records(contents)]
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(b'@cwd '):
            prefix = line[5:]
            check(prefix.startswith(b'/'), f'Relative package prefix: {display(prefix)}')
        elif line == b'@ignore':
            i += 1
            check(i < len(lines), 'Missing ignored manifest entry')
            if lines[i].startswith(b'+'):
                metadata.append(relative_name(lines[i]))
        elif line and not line.startswith(b'@'):
            name = relative_name(line)
            check(name not in files, f'Duplicate manifest file: {display(name)}')
            comment = lines[i + 1] if i + 1 < len(lines) else b''
            match = re.fullmatch(rb'@comment (MD5:([0-9a-f]{32})|Symlink:(.*))', comment)
            check(match, f'Missing file digest or symlink target: {display(name)}')
            files[name] = ('file', match[2].decode()) if match[2] else ('symlink', match[3])
            check(prefix is not None, f'Missing package prefix: {display(name)}')
            paths.add(posixpath.join(prefix, name))
            i += 1
        i += 1
    check(len(set(metadata)) == len(metadata), 'Duplicate metadata entry in manifest')
    return files, metadata, paths


def library_metadata(build, paths, context):
    for line in records(build):
        if line.startswith(b'PROVIDES='):
            path = chomp(line[9:])
            check(path in paths, f'PROVIDES is absent from the manifest: {display(path)}: {context}')
        elif line.startswith(b'REQUIRES='):
            path = chomp(line[9:])
            check(path not in paths, f"REQUIRES names the package's own payload: {display(path)}: {context}")


SCRIPT_HELPERS = set('''AWK BASENAME CAT CHGRP CHMOD CHOWN CMP CP DIRNAME ECHO ECHO_N EGREP EXPR
 FALSE FIND GREP GROUPADD GTAR HEAD ID INSTALL_INFO LINKFARM LN LS MKDIR MV
 PERL5 PKG_ADMIN PKG_INFO PW PWD_CMD RM RMDIR SED SETENV SH SORT SU TEST
 TOUCH TR TRUE USERADD XARGS RCD_SCRIPTS_SHELL PKG_USER_SHELL
 LDCONFIG_ADD_CMD LDCONFIG_REMOVE_CMD TTF_INDEX_CMD TYPE1_INDEX_CMD
 TYPE1_POSTINDEX_CMD MKFONTDIR GTK2_UPDATE_ICON_CACHE GTK3_UPDATE_ICON_CACHE'''.split())


def install_script_paths(metadata, context):
    prefixes = [display(line[5:]).strip() for line in records(metadata[b'+CONTENTS']) if line.startswith(b'@cwd ')]
    prefixes += ['/bin', '/sbin', '/usr/bin', '/usr/sbin', '/usr/libexec', '/usr/pkg', '/usr/local', '/usr/X11R7']
    host_root = re.compile(r'\A/(?:Volumes|Users|Applications|private/(?:tmp|var/folders)|var/folders|opt/homebrew|tmp)(?:/|\Z)')
    prefixes = [prefix for prefix in prefixes if prefix != '/' and not host_root.match(prefix)]
    try:
        for name in (b'+INSTALL', b'+DEINSTALL', b'+REQUIRE'):
            for number, raw in enumerate(records(metadata.get(name, b'')), 1):
                line = display(raw)
                value = None
                helper = False
                match = re.match(r'\s*#!\s*(.*)', line)
                assignment = re.match(r'\s*(?:export\s+)?([A-Z][A-Z0-9_]*)=(.*)', line)
                if match:
                    value, helper = match[1], True
                elif assignment:
                    helper = assignment[1] in SCRIPT_HELPERS
                    if not helper and not re.match(r'''\s*["']?/''', assignment[2]):
                        continue
                    words = shlex.split(assignment[2])
                    value = words[0] if words else None
                if value is None:
                    continue
                words = shlex.split(value)
                location = f'{context}/{display(name)}:{number}'
                for word in words:
                    if word.startswith('/'):
                        check(not host_root.match(posixpath.normpath(word)), f'Host path in package script {location}: {word}')
                executable = words[0] if words else ''
                if helper and executable.startswith('/'):
                    executable = posixpath.normpath(executable)
                    check(any(executable.startswith(prefix.rstrip('/') + '/') for prefix in prefixes),
                          f'Non-target executable in package script {location}: {executable}')
    except ValueError as error:
        raise AuditError(f'Invalid serialized package script in {context}: {error}') from error


def package_library_closure(snapshots, payloads):
    providers = set().union(*payloads.values())
    for name, metadata in snapshots.items():
        for line in records(metadata[b'+BUILD_INFO']):
            if line.startswith(b'REQUIRES=/usr/pkg/'):
                path = chomp(line[9:])
                check(path in providers, f'Package-managed requirement is absent from the set: {name}: {display(path)}')


def archive_members(tar, path, target):
    def consume(stream):
        members, global_pax, local = {}, {}, {}
        try:
            for entry in tar_records(stream):
                kind = entry.typeflag
                if kind in (b'x', b'g'):
                    check(entry.size <= CHUNK, 'Oversized PAX header')
                    attributes = pax_records(entry.read(CHUNK))
                    for key in attributes:
                        check(not key.startswith(b'GNU.sparse') and key != b'SCHILY.realsize', 'Sparse package members are unsupported')
                    if kind == b'g':
                        for key, value in attributes.items():
                            if value:
                                global_pax[key] = value
                            else:
                                global_pax.pop(key, None)
                    else:
                        local.update(attributes)
                    continue
                attributes = {key: value for key, value in (global_pax | local).items() if value}
                local = {}
                if b'size' in attributes:
                    try:
                        size = int(attributes[b'size'])
                    except ValueError as error:
                        raise AuditError('Unsupported PAX size override') from error
                    check(size == entry.size, 'Unsupported PAX size override')
                name = relative_name(attributes.get(b'path', entry.name))
                link = attributes.get(b'linkpath', entry.linkname)
                check(name not in members, f'Duplicate archive member: {display(name)}')
                if kind in (b'0', b'\0'):
                    digest, header = hashlib.md5(usedforsecurity=False), bytearray()
                    data = bytearray() if name.startswith(b'+') else None
                    while chunk := entry.read(CHUNK):
                        digest.update(chunk)
                        header.extend(chunk[:64 - len(header)])
                        if data is not None:
                            data.extend(chunk)
                            check(len(data) <= METADATA_LIMIT, f'Oversized package metadata: {display(name)}')
                    if header.startswith(b'\x7fELF'):
                        check(len(header) == 64, f'Truncated ELF header: {display(name)}')
                        check(header[4] == 2, f'Unsupported ELF class: {display(name)}')
                        check(header[5] == 1, f'Unsupported ELF byte order: {display(name)}')
                        machine = int.from_bytes(header[18:20], 'little')
                        check(machine == target['elf'], f'Wrong ELF machine {machine}: {display(name)}')
                    members[name] = ('file', digest.hexdigest(), bytes(data) if data is not None else None)
                elif kind == b'1':
                    members[name] = ('hardlink', relative_name(link))
                elif kind == b'2':
                    members[name] = ('symlink', link)
                elif kind == b'5':
                    members[name] = ('directory',)
                else:
                    raise AuditError(f'Unsupported archive member type {kind!r}: {display(name)}')
        except (CommandError, ProcessOwnershipError):
            raise
        except SDKError as error:
            raise AuditError(str(error)) from error
        check(not local, 'PAX header has no following member')
        return members
    return run_streamed([tar, '-cf', '-', '--format=pax', '@' + str(path)], consume,
                        timeout=PRODUCER_TIMEOUT).value


def audit_archive(tar, path, expected, files, target):
    members = archive_members(tar, path, target)
    build = members.get(b'+BUILD_INFO', (None, None, None))
    check(len(build) == 3 and build[0] == 'file', f'Missing regular +BUILD_INFO: {path}')
    target_metadata(build[2], path, target)
    for name, data in expected.items():
        member = members.get(name, ())
        check(len(member) == 3 and member[0] == 'file' and member[2] == data,
              f'Archive metadata mismatch {display(name)}: {path}')
    def resolve(name):
        seen = set()
        while True:
            check(name not in seen, f'Hardlink cycle: {display(name)}')
            seen.add(name)
            check(name in members, f'Missing archive member: {display(name)}')
            member = members[name]
            if member[0] != 'hardlink':
                return member
            name = member[1]
    for name, wanted in files.items():
        check(resolve(name)[:2] == wanted, f'Archive payload mismatch {display(name)}: {path}')
    allowed = set(files) | set(expected)
    for name, member in members.items():
        if name not in allowed:
            check(member[0] == 'directory' and any(file.startswith(name + b'/') for file in files),
                  f'Unlisted archive member {display(name)}: {path}')


def load_sdk(argv):
    # Use the one Ports loader. It rejects ambient SDK modules and wrong API versions.
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'profiles/development-toolchain/runtime/recipe/files'))
    import sdk_source
    args = sdk_source.arguments(argv)
    from emberbsd_sdk import stream, tarstream
    check(getattr(stream, 'PRODUCER_STREAM_API', None) == 1 and
          getattr(tarstream, 'TAR_STREAM_API', None) == 1,
          'Selected SDK API1 lacks producer-stream/raw-tar capability version 1')
    from emberbsd_sdk.errors import SDKError, CommandError, ProcessOwnershipError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.targets import target_definition
    from emberbsd_sdk.jsonio import write_json
    globals().update(SDKError=SDKError, CommandError=CommandError, ProcessOwnershipError=ProcessOwnershipError,
                     sha256_file=sha256_file, target_definition=target_definition, write_json=write_json,
                     run_streamed=stream.run_streamed, capture_streamed=stream.capture_streamed,
                     tar_records=tarstream.tar_records, pax_records=tarstream.pax_records)
    return args, sdk_source


def parse_arguments(args):
    target, seen = 'aarch64', False
    while args and args[0].startswith('-'):
        option = args.pop(0)
        if option == '--':
            break
        check(option == '--target' or option.startswith('--target='), f'Unknown option: {option}')
        check(not seen, 'Duplicate target option')
        seen = True
        if '=' in option:
            target = option.split('=', 1)[1]
        else:
            check(args, 'Missing target option value')
            target = args.pop(0)
        check(target in ('aarch64', 'amd64'), f'Unsupported target: {target}')
    check(len(args) >= 4, 'Usage: prepare-package-set.py [--sdk-source SDK] [--target aarch64|amd64] PKGDB ARCHIVE_PATHS NEW_OUTPUT ROOT_PACKAGE...')
    pkgdb, index, output, *roots = args
    check(len(set(roots)) == len(roots), 'Duplicate root package')
    return target, Path(pkgdb).resolve(strict=True), Path(index), Path(os.path.abspath(output)), roots


def bounded_capture(argv, limit):
    return capture_streamed(argv, stdout_limit=limit, timeout=PRODUCER_TIMEOUT).value


def prepare(args):
    target_name, pkgdb, index, output, roots = parse_arguments(args)
    target = target_definition(target_name)
    check(not output.exists() and not output.is_symlink(), 'Output already exists')
    tar = os.environ.get('BSDTAR', 'bsdtar')
    info = os.environ.get('PKG_INFO', 'pkg_info')
    staging = Path(tempfile.mkdtemp(prefix='.' + output.name + '-', dir=output.parent))
    retain = False
    try:
        check(b'libarchive' in bounded_capture([tar, '--version'], CHUNK), 'Use bsdtar/libarchive')
        archives = {}
        for line in records(index.read_bytes()):
            path = chomp(line)
            if path:
                path = os.path.abspath(display(path))
                name = os.path.basename(path)
                archives.setdefault(name[:-4] if name.endswith('.tgz') else name, []).append(path)
        cache, packages, snapshots, manifests, payloads, order = {}, {}, {}, {}, {}, []
        def visit(name):
            check(re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.+\-]*-[0-9][a-zA-Z0-9_.+\-]*', name), f'Invalid package name: {name}')
            if packages.get(name) == 'done':
                return
            check(packages.get(name) != 'active', f'Runtime dependency cycle at {name}')
            packages[name] = 'active'
            contents = (pkgdb / name / '+CONTENTS').read_bytes()
            check([line for line in records(contents) if line.startswith(b'@name ')] == [f'@name {name}\n'.encode()], f'Package identity mismatch: {name}')
            files, metadata, paths = package_manifest(contents)
            llvm_runtime_payload(name, paths)
            manifests[name], payloads[name] = files, paths
            snapshots[name] = {entry: (pkgdb / name / display(entry)).read_bytes() for entry in metadata}
            check(snapshots[name][b'+CONTENTS'] == contents, f'Installed manifest changed during read: {name}')
            target_metadata(snapshots[name][b'+BUILD_INFO'], f'installed {name}', target)
            library_metadata(snapshots[name][b'+BUILD_INFO'], paths, f'installed {name}')
            install_script_paths(snapshots[name], f'installed {name}')
            for line in records(contents):
                if not line.startswith(b'@pkgdep '):
                    continue
                pattern = display(line[8:].strip())
                if pattern not in cache:
                    try:
                        found = bounded_capture([info, '-K', str(pkgdb), '-e', pattern], CHUNK)
                    except CommandError as error:
                        if error.returncode != 1:
                            raise
                        raise AuditError(f'Unresolved or ambiguous dependency {name}: {pattern}: {display(error.stderr)}') from error
                    names = [display(line).strip() for line in records(found)]
                    check(len(names) == 1, f'Unresolved or ambiguous dependency {name}: {pattern}')
                    cache[pattern] = names[0]
                visit(cache[pattern])
            packages[name] = 'done'
            order.append(name)
        for name in roots:
            visit(name)
        package_library_closure(snapshots, payloads)
        (staging / 'packages').mkdir()
        hashes = []
        for name in order:
            candidates, identities = [], set()
            for original in archives.get(name, []):
                try:
                    state = os.stat(original)
                except FileNotFoundError:
                    continue
                identity = (state.st_dev, state.st_ino)
                if stat.S_ISREG(state.st_mode) and identity not in identities:
                    candidates.append(original)
                    identities.add(identity)
            accepted, failures = False, []
            for original in candidates:
                try:
                    contents = bounded_capture([tar, '-xOf', original, '+CONTENTS'], METADATA_LIMIT)
                except CommandError as error:
                    if error.returncode != 1:
                        raise
                    continue
                if contents != snapshots[name][b'+CONTENTS']:
                    continue
                destination = staging / 'packages' / (name + '.tgz')
                digest = sha256_file(os.path.realpath(original))
                try:
                    audit_archive(tar, original, snapshots[name], manifests[name], target)
                except AuditError as error:
                    failures.append(f'{original}: {error}')
                    continue
                except CommandError as error:
                    if error.returncode != 1:
                        raise
                    failures.append(f'{original}: {error}')
                    continue
                shutil.copyfile(original, destination)
                shutil.copymode(original, destination)
                check(sha256_file(destination) == digest, f'Archive changed during copy: {name}')
                audit_archive(tar, destination, snapshots[name], manifests[name], target)
                hashes.append(f'{digest}  packages/{name}.tgz\n')
                accepted = True
                break
            reason = (f'No verified archive for {name}:\n' + '\n'.join(failures) if failures else
                      f'No archive with the installed manifest: {name} ({len(candidates)} candidates)')
            check(accepted, reason)
        for name, metadata in snapshots.items():
            for entry, data in metadata.items():
                check((pkgdb / name / display(entry)).read_bytes() == data, f'Installed metadata changed during audit: {name}/{display(entry)}')
        (staging / 'packages.sha256').write_text(''.join(hashes))
        (staging / 'install-order.txt').write_text(''.join(name + '.tgz\n' for name in order))
        (staging / 'roots.txt').write_text('\n'.join(roots) + '\n')
        (staging / 'target.txt').write_text(f"OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH={target['arch']}\nOBJECT_FMT=ELF\n")
        check(not output.exists() and not output.is_symlink(), 'Output appeared during audit')
        os.rename(staging, output)
        staging = None
        print(f'PASS: {len(order)} NetBSD 11.0/{target_name} packages; archived payload, ELF headers, metadata and copied SHA256 verified')
        print(f'Package files: {output}')
    except ProcessOwnershipError as error:
        retain = True
        print(f'Retained package audit workspace: {staging}', file=sys.stderr)
        try:
            write_json(staging / '.producer-ownership-unproven.json',
                       dict(status='unproven', sid=error.sid, reason=error.reason))
        except Exception as marker_error:
            print(f'Cannot write quarantine marker: {marker_error}', file=sys.stderr)
        raise
    finally:
        if staging is not None and not retain:
            shutil.rmtree(staging)


def main(argv=None):
    try:
        args, source = load_sdk(list(sys.argv[1:] if argv is None else argv))
        source.install_signal_handlers()
    except (ImportError, RuntimeError, AuditError) as error:
        print(f'FAIL: SDK API1 with producer-stream/raw-tar capability version 1 is required: {error}', file=sys.stderr)
        return 1
    try:
        prepare(args)
        return 0
    except CommandError as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return error.returncode if error.returncode >= 0 else 128 - error.returncode
    except Exception as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
