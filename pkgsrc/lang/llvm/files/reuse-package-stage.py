#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Verify an explicitly accepted LLVM build.
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import stat
import sys
sys.dont_write_bytecode = True
from sdk_source import load_sdk

MACHO_MAGIC = tuple(bytes.fromhex(h) for h in ('cffaedfe', 'cefaedfe', 'feedfacf', 'feedface', 'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca'))


def check(value, message):
    from emberbsd_sdk.errors import SDKError
    if not value:
        raise SDKError(message)


def hash_file(path):
    from emberbsd_sdk.paths import canonical_existing, regular_file
    from emberbsd_sdk.inventory import sha256_file
    real = canonical_existing(path)
    return dict(path=real, sha256=sha256_file(real), mode=regular_file(real).st_mode & 0o7777)


def tree(path, excludes=()):
    from emberbsd_sdk.inventory import snapshot_tree
    # Preserve the schema-1 immutable receipt representation. Directories had
    # no row. SDK still validates all directories and links before this mapping.
    result = {}
    for name, row in snapshot_tree(path, exclude=excludes).items():
        if row['kind'] == 'file':
            result[name] = ['file', row['mode'], row['sha256']]
        elif row['kind'] == 'link':
            result[name] = ['link', row['target']]
    return result


def context(path):
    from emberbsd_sdk.jsonio import read_json
    from emberbsd_sdk.paths import real_directory
    value = read_json(path, max_bytes=128 * 1024 * 1024)
    check(type(value['schema']) is int and value['schema'] in (1, 2), 'Unsupported LLVM input schema')
    target, arch = value['target'], value['target']['arch']
    triple = {'aarch64': 'aarch64--netbsd', 'x86_64': 'x86_64--netbsd'}.get(arch)
    check(triple and target == dict(opsys='NetBSD', version='11.0', arch=arch, triple=triple), 'Unsupported LLVM target ABI')
    check(value['version'] == '23.1.4', 'Unsupported LLVM source version')
    check(type(value['install_strip']) is bool, 'Explicit CMake install strip mode required')
    check(isinstance(value['flags'], dict) and value['flags'], 'Missing compile contract')
    for key in ('source', 'build', 'recipe', 'sdk_recipe'):
        p = value[key]
        check(os.path.isabs(p) and p != '/', f'Invalid {key} tree')
        real_directory(p)
    check(value['build'].startswith(value['source'] + '/'), 'Build must belong to the recorded LLVM source')
    reject_quarantine(value)
    for kind in ('compiler', 'native_tools', 'patches', 'target_abi'):
        paths = value['files'][kind]
        check(isinstance(paths, list) and paths and len(set(paths)) == len(paths), f'Missing or duplicate {kind} inputs')
        for p in paths:
            check(os.path.isabs(p) and os.path.isfile(p), f'Invalid {kind} input')
    for key in ('cmake', 'tar', 'python' if value['schema'] == 2 else 'perl'):
        check(value[key] in value['files']['native_tools'] and os.access(value[key], os.X_OK), f'{key} must be an explicit executable native input')
    runtime = value['runtime']
    check(re.fullmatch('[0-9a-f]{64}', runtime['sha256']), 'Expected accepted runtime SHA256 required')
    check(hash_file(runtime['archive'])['sha256'] == runtime['sha256'], 'Runtime archive drift')
    return value


def snapshot(value):
    reject_quarantine(value)
    build = value['build']
    check(not os.path.islink(build + '/install_manifest.txt'), 'CMake install manifest must not be a symlink')
    return dict(files={kind: {p: hash_file(p) for p in paths} for kind, paths in value['files'].items()},
                source=tree(value['source'], [os.path.relpath(build, value['source'])]),
                build=tree(build, ['install_manifest.txt']), recipe=tree(value['recipe']), sdk_recipe=tree(value['sdk_recipe']),
                manifests={kind: hash_file(p) for kind, p in value['manifests'].items()}, runtime=hash_file(value['runtime']['archive']))


def run(command, env=None):
    from emberbsd_sdk.process import capture
    result = capture(command, env=env)
    if result.stdout:
        sys.stdout.buffer.write(result.stdout)
    return result


def validate_full_stage(value, stage):
    from emberbsd_sdk.process import capture
    from emberbsd_sdk.elf import read_elf_header
    lists = value['manifests']
    check(set(lists) == {'devel', 'full', 'runtime'}, 'Three normalized LLVM PLISTs required')
    selector = value['recipe'] + '/files/select-package-stage.py'
    run([value['python'], '-B', selector, '--sdk-source', value['sdk_source'], 'check', stage, lists['full'], lists['runtime'], lists['devel'], lists['full']])
    archive = value['runtime']['archive']
    info = capture([value['tar'], '-xOf', archive, '+BUILD_INFO']).stdout.decode()
    target = value['target']
    for key, expected in dict(OPSYS=target['opsys'], OS_VERSION=target['version'], MACHINE_ARCH=target['arch'], OBJECT_FMT='ELF').items():
        check([line for line in info.splitlines() if line.startswith(key + '=')] == [key + '=' + expected], f'Runtime {key} mismatch')
    contents = capture([value['tar'], '-xOf', archive, '+CONTENTS']).stdout.decode().splitlines()
    cwd = [line for line in contents if line.startswith('@cwd ')]
    check(cwd and all(line == '@cwd /usr/pkg' for line in cwd), 'Runtime package prefix mismatch')
    check([line for line in contents if line.startswith('@name ')] == ['@name llvm-23.1.4nb1'], 'Runtime package identity mismatch')
    expected = [s for s in Path(lists['runtime']).read_text().splitlines() if s and not s.startswith('@comment ')]
    actual = []
    for i, name in enumerate(contents):
        if not name or name.startswith('@') or (i > 0 and contents[i - 1] == '@ignore'):
            continue
        check(name in expected, f'Unexpected runtime file: {name}')
        actual.append(name)
        item, comment = stage + '/' + name, contents[i + 1] if i + 1 < len(contents) else ''
        if comment.startswith('@comment MD5:'):
            # MD5 is the pkgsrc manifest format, not a new provenance digest.
            check(os.path.isfile(item) and not os.path.islink(item), f'Runtime stage bytes differ: {name}')
            with open(item, 'rb') as handle:
                digest = hashlib.file_digest(handle, 'md5').hexdigest()
            check(digest == comment.removeprefix('@comment MD5:'), f'Runtime stage bytes differ: {name}')
        elif comment.startswith('@comment Symlink:'):
            check(os.path.islink(item) and os.readlink(item) == comment.removeprefix('@comment Symlink:'), f'Runtime stage link differs: {name}')
        else:
            check(False, f'Missing runtime digest: {name}')
    check(sorted(actual) == sorted(expected), 'Incomplete runtime stage comparison')
    machine = 183 if target['arch'] == 'aarch64' else 62
    for name, row in tree(stage).items():
        if row[0] != 'file':
            continue
        path = stage + '/' + name
        with open(path, 'rb') as handle:
            header = handle.read(20)
        if header.startswith(b'\x7fELF'):
            read_elf_header(path, machine=machine)
        else:
            check(not header.startswith(MACHO_MAGIC), f'Host Mach-O in stage: {name}')


def input_roots(value):
    from emberbsd_sdk.paths import canonical_existing
    return [canonical_existing(value[key]) for key in ('source', 'build', 'recipe', 'sdk_recipe')]


def reject_overlaps(path, roots, message):
    from emberbsd_sdk.paths import reject_overlap
    for root in roots:
        try:
            reject_overlap(path, root)
        except Exception as error:
            raise ValueError(message) from error


def quarantine_path(value):
    from emberbsd_sdk.paths import canonical_existing, real_directory
    build = canonical_existing(value['build'])
    real_directory(build)
    # The reserved marker travels with the build if any ancestor is renamed.
    # Reject it before snapshots. Remove it only after proven process drainage.
    return str(Path(build) / '.llvm-reuse-quarantine.json')


def reject_quarantine(value):
    path = quarantine_path(value)
    check(not os.path.lexists(path), f'LLVM build is quarantined; inspect {path}')


def guarded_install(value, command, log, env):
    from emberbsd_sdk.errors import ProcessOwnershipError
    from emberbsd_sdk.jsonio import read_json, write_json
    from emberbsd_sdk.paths import canonical_existing, regular_file, stable_identity
    from emberbsd_sdk.process import run_logged
    reject_quarantine(value)
    marker = quarantine_path(value)
    state = dict(schema=1, state='install-started', build=canonical_existing(value['build']), log=log)
    # Create before launch. Abrupt caller death must also refuse the next reuse.
    write_json(marker, state, mode=0o600)
    identity = stable_identity(regular_file(marker))

    def clear():
        check(stable_identity(regular_file(marker)) == identity and read_json(marker) == state,
              'LLVM quarantine marker changed during install')
        os.unlink(marker)

    try:
        run_logged(command, log, env=env)
    except ProcessOwnershipError as error:
        # Keep the initial marker even if the diagnostic update fails.
        check(stable_identity(regular_file(marker)) == identity, 'LLVM quarantine marker changed during install')
        write_json(marker, dict(state, state='ownership-uncertain', sid=error.sid, reason=error.reason), exclusive=False, mode=0o600)
        raise
    except BaseException:
        # The SDK reports uncertain ownership with its distinct typed error.
        # A completed producer failure or a drained interruption is retryable.
        clear()
        raise
    else:
        clear()


def empty_destination(destdir, pkgsrc_skeleton):
    entries = os.listdir(destdir)
    if not entries:
        return
    check(pkgsrc_skeleton, 'SDK DESTDIR must be empty')
    message = 'SDK DESTDIR must be empty or contain only the canonical empty /usr/pkg skeleton'
    check(set(entries) == {'usr'}, message)
    parent = Path(destdir) / 'usr'
    for path, expected in ((parent, {'pkg'}), (parent / 'pkg', set())):
        info = path.lstat()
        check(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o755, message)
        check(set(os.listdir(path)) == expected, message)


def install_full(value, destdir, *, pkgsrc_skeleton=False):
    from emberbsd_sdk.paths import real_directory
    check(value['schema'] == 2, 'Legacy LLVM receipts support verification only; record current Python inputs before install')
    check(os.path.isabs(destdir) and destdir != '/', 'Existing private DESTDIR required')
    reject_quarantine(value)
    real_directory(destdir)
    reject_overlaps(destdir, input_roots(value), 'SDK DESTDIR overlaps LLVM inputs')
    empty_destination(destdir, pkgsrc_skeleton)
    command = [value['cmake'], '--install', value['build'], '--prefix', '/usr/pkg']
    if value['install_strip']:
        command.append('--strip')
    log = destdir + '.llvm-install.log'
    reject_overlaps(log, input_roots(value), 'SDK install log overlaps LLVM inputs')
    guarded_install(value, command, log, dict(os.environ, DESTDIR=destdir, PYTHONDONTWRITEBYTECODE='1'))
    check(all(p.startswith('usr/pkg/') for p in tree(destdir)), 'Install wrote outside the target prefix')
    return destdir + '/usr/pkg'


def record(config, destdir, output):
    from emberbsd_sdk.paths import canonical_new
    from emberbsd_sdk.jsonio import write_json
    check(not os.path.lexists(output), 'Receipt already exists')
    value = context(config)
    check(os.path.isabs(output) and os.path.isdir(os.path.dirname(output)), 'Absolute receipt path with an existing parent required')
    output = canonical_new(output)
    reject_overlaps(output, input_roots(value) + [destdir], 'Receipt overlaps LLVM inputs or reference stage')
    before = snapshot(value)
    stage = install_full(value, destdir)
    validate_full_stage(value, stage)
    stage_files = tree(stage)
    validate_full_stage(value, stage)
    check(tree(stage) == stage_files, 'Reference stage changed during validation')
    check(stage_files, 'Empty reference stage')
    check(snapshot(value) == before and context(config) == value, 'Inputs changed while recording the stage')
    write_json(output, dict(schema=2, context=value, inputs=before, stage=stage_files), mode=0o600)


def verify(config, receipt_path, expected_hash):
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import read_json
    check(re.fullmatch('[0-9a-f]{64}', expected_hash), 'Explicit accepted receipt SHA256 required')
    check(sha256_file(receipt_path) == expected_hash, 'Accepted receipt drift')
    receipt = read_json(receipt_path, max_bytes=128 * 1024 * 1024)
    check(type(receipt['schema']) is int and receipt['schema'] in (1, 2), 'Unsupported LLVM receipt schema')
    value = context(config)
    check(value == receipt['context'], 'Current compile/ABI/source contract differs from the receipt')
    check(snapshot(value) == receipt['inputs'], 'LLVM source, patch, compiler, tool or object drift')
    check(sha256_file(receipt_path) == expected_hash, 'Accepted receipt drift')
    return receipt


def install(config, receipt_path, expected_hash, destdir):
    receipt = verify(config, receipt_path, expected_hash)
    stage = install_full(receipt['context'], destdir, pkgsrc_skeleton=True)
    check(tree(stage) == receipt['stage'], 'Installed LLVM stage differs from the accepted full stage')
    verify(config, receipt_path, expected_hash)
    print('PASS: accepted LLVM objects produced an exact SDK input stage; package checks remain required.')


if __name__ == '__main__':
    from sdk_source import exit_error, install_signal_handlers
    install_signal_handlers()
    try:
        _, args = load_sdk()
        command = args.pop(0) if args else ''
        check(command in ('record', 'verify', 'install') and len(args) == (4 if command == 'install' else 3),
              'Use record CONFIG DESTDIR RECEIPT, verify CONFIG RECEIPT SHA256, or install CONFIG RECEIPT SHA256 DESTDIR')
        globals()[command](*args)
    except Exception as error:
        exit_error(error)
