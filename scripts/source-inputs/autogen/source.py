#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare libopts from the common AutoGen distfile or an installed package."""
import argparse
import hashlib
import importlib.util
import os
import platform
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source
sys.path.append(str(PORTS / 'scripts'))
import prepared_receipt
from recipe import generation_recipe
import tearoff


def main():
    sdk_source.install_signal_handlers()
    sdk, argv = sdk_source.load_sdk(sys.argv[1:])
    from emberbsd_sdk import host_prefix, jsonio, paths, process, sourceprep
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.publication import publish_directory_noreplace
    if 'verify-source' in argv:
        return verify_source(argv, sdk, jsonio, paths, process, sourceprep, SDKError)
    if '--archive' in argv:
        return prepare_distfile(argv, sdk, jsonio, paths, sourceprep, SDKError, publish_directory_noreplace)
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('export', 'host-prefix', 'pkg-admin', 'make', 'makeconf', 'git', 'patch'):
        parser.add_argument('--' + name, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--output')
    selection.add_argument('--source')
    parser.add_argument('--make-arg', action='append', default=[])
    parser.add_argument('--package', help='installed AutoGen package name when more than one is present')
    args = parser.parse_args(argv)

    def need(ok, message):
        if not ok:
            raise SDKError(message)

    def read(path):
        handle, before = paths.open_regular(str(path))
        with handle:
            data = handle.read()
        paths.verify_stable(str(path), before)
        return data

    def digest(path):
        return hashlib.sha256(read(path)).hexdigest()

    for value in (args.export, args.host_prefix, args.pkg_admin, args.make, args.makeconf, args.git, args.patch, args.output or args.source):
        need(os.path.isabs(value), 'select absolute input and output paths')
    prefix = Path(paths.canonical_existing(args.host_prefix))
    spec = importlib.util.spec_from_file_location('pkgsrc_source_identity', PORTS / 'scripts/pkgsrc-source-identity.py')
    selector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selector)
    exported = selector.shared_export(args.export, PORTS, args.git, sdk, args.patch)
    recipe = Path(paths.canonical_existing(exported / 'devel/autogen'))
    search_path = os.pathsep.join(str(prefix / item) for item in ('bin', 'gnu/bin', 'sbin'))
    for tool in (args.make, args.pkg_admin):
        host_prefix.validate_host_executable(str(prefix), tool,
            {'os': platform.system(), 'cpu': platform.machine()}, search_path=search_path)
    env = process.sanitized_environment()
    env.update(MAKECONF=args.makeconf, PATH=search_path)
    query = subprocess.run([args.make, '-C', str(recipe), *args.make_arg,
                            '-V', '${PKGNAME}', '-V', '${CONFIGURE_ARGS}', '-V', '${PKG_OPTIONS}'],
                           env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, check=True)
    lines = query.stdout.splitlines()
    need(len(lines) == 3 and re.fullmatch(r'autogen-[0-9]+(?:\.[0-9]+)+(?:nb[0-9]+)?', lines[0]),
         'cannot identify selected AutoGen package and configure arguments')
    current_name, configure_args, options = lines
    version = re.sub(r'nb[0-9]+$', '', current_name)
    installed = sorted(p.name for p in (prefix / 'var/db/pkg').glob(version + '*')
                       if re.fullmatch(re.escape(version) + r'(?:nb[0-9]+)?', p.name))
    name = args.package if args.package else (installed[0] if len(installed) == 1 else '')
    need(name in installed, 'select one installed AutoGen package matching the common source version')
    db = prefix / 'var/db/pkg' / name
    rows = {}
    for line in read(db / '+BUILD_VERSION').decode('utf-8').splitlines():
        path, sep, value = line.partition(': ')
        need(bool(sep) and path not in rows and re.fullmatch('[0-9a-f]{64}', value),
             'invalid AutoGen package build metadata')
        rows[path] = value
    expected = {'devel/autogen/distinfo': digest(recipe / 'distinfo')}
    for patch in sorted((recipe / 'patches').glob('patch-*')):
        expected['devel/autogen/patches/' + patch.name] = digest(patch)
    recorded = {k: v for k, v in rows.items()
                if k == 'devel/autogen/distinfo' or k.startswith('devel/autogen/patches/')}
    need(recorded == expected, 'installed AutoGen source or patchset differs from current recipe')
    info = read(db / '+BUILD_INFO').decode('utf-8').splitlines()
    config = [line.removeprefix('CONFIGURE_ARGS=') for line in info if line.startswith('CONFIGURE_ARGS=')]
    def generation_args(value):
        return [arg for arg in shlex.split(value)
                if not arg.startswith(('--prefix=', '--infodir=', '--mandir='))]
    need(len(config) == 1 and generation_args(config[0]) == generation_args(configure_args),
         'installed AutoGen configure arguments differ from current recipe')
    installed_options = [line.removeprefix('PKG_OPTIONS=') for line in info if line.startswith('PKG_OPTIONS=')]
    need(installed_options == [options] if installed_options else not options,
         'installed AutoGen options differ from current recipe')
    contents = read(db / '+CONTENTS').decode('utf-8').splitlines()
    entries = [line for line in contents if re.fullmatch(r'share/autogen/libopts-[0-9]+(?:\.[0-9]+)+\.tar\.gz', line)]
    need(len(entries) == 1, 'installed AutoGen lacks a unique libopts tearoff')
    archive = prefix / entries[0]
    subprocess.run([args.pkg_admin, '-K', str(prefix / 'var/db/pkg'), 'check', name],
                   env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    archive_hash = digest(archive)
    root_name = archive.name.removesuffix('.tar.gz')
    identity = {'package': name, 'recipe': expected, 'configure_args': generation_args(configure_args),
                'archive_sha256': archive_hash, 'options': options,
                'generation_recipe': generation_recipe(recipe)}
    if args.source:
        result = sourceprep.validate_prepared_tree(args.source, package='devel/autogen', identity=identity)
        sys.stdout.buffer.write(jsonio.json_bytes(result))
        return
    output = Path(args.output)
    output = Path(paths.canonical_existing(str(output.parent)), output.name)
    need(not os.path.lexists(output), 'prepared source output already exists')
    paths.reject_overlap(str(output), str(PORTS))
    with tempfile.TemporaryDirectory(prefix='.autogen-libopts-', dir=output.parent) as tmp:
        sourceprep.extract_archive(archive, tmp, root_name, 'AutoGen libopts')
        root = Path(tmp) / root_name
        need((root / 'libopts.c').is_file() and (root / 'autoopts/options.h').is_file(),
             'AutoGen tearoff lacks expected libopts source')
        need(digest(archive) == archive_hash, 'AutoGen tearoff changed while preparing')
        result = prepared_receipt.write(root, package='devel/autogen', identity=identity)
        publish_directory_noreplace(root, output)
    sys.stdout.buffer.write(jsonio.json_bytes(result))


def prepare_distfile(argv, sdk, jsonio, paths, sourceprep, SDKError, publish_directory_noreplace):
    """Prepare or check the tearoff from the checksummed AutoGen distfile.

    No AutoGen, Guile or configure step runs: the distfile is checked against
    the recipe distinfo, the complete recipe patchset is applied and the
    tearoff is assembled as mklibsrc.sh does. The identity keeps the
    installed-package schema; configure_args and options are empty because
    no configuration contributes to the payload.
    """
    parser = argparse.ArgumentParser(description=prepare_distfile.__doc__)
    for name in ('export', 'git', 'patch', 'archive'):
        parser.add_argument('--' + name, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--output')
    selection.add_argument('--source')
    args = parser.parse_args(argv)

    def need(ok, message):
        if not ok:
            raise SDKError(message)

    def read(path):
        handle, before = paths.open_regular(str(path))
        with handle:
            data = handle.read()
        paths.verify_stable(str(path), before)
        return data

    for value in (args.export, args.git, args.patch, args.archive, args.output or args.source):
        need(os.path.isabs(value), 'select absolute input and output paths')
    spec = importlib.util.spec_from_file_location('pkgsrc_source_identity', PORTS / 'scripts/pkgsrc-source-identity.py')
    selector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selector)
    current = selector.identity(PORTS, 'devel/autogen', args.git, sdk)
    exported = selector.shared_export(args.export, PORTS, args.git, sdk, args.patch)
    recipe = Path(paths.canonical_existing(exported / 'devel/autogen'))
    makefile = read(recipe / 'Makefile').decode('utf-8')
    distnames = re.findall(r'^DISTNAME=\s*(autogen-[0-9]+(?:\.[0-9]+)+)\s*$', makefile, re.M)
    revisions = re.findall(r'^PKGREVISION=\s*([0-9]+)\s*$', makefile, re.M)
    need(len(distnames) == 1 and len(revisions) <= 1 and
         not re.search(r'^(?:PKGNAME|EXTRACT_SUFX)\s*[+?:!]?=(?!\s*\.tar\.xz\s*$)', makefile, re.M),
         'cannot identify the common AutoGen distfile from its recipe')
    distname = distnames[0]
    name = distname + ('nb' + revisions[0] if revisions and revisions[0] != '0' else '')
    archive_name = distname + '.tar.xz'
    info = read(recipe / 'distinfo').decode('utf-8')
    wanted = {}
    for label, key in (('SHA512', 'sha512'), ('BLAKE2s', 'blake2s'), ('Size', 'size')):
        values = re.findall(r'^' + label + r' \(' + re.escape(archive_name) + r'\) = (\S+)(?: bytes)?$', info, re.M)
        need(len(values) == 1, 'ambiguous AutoGen distfile ' + label)
        wanted[key] = int(values[0]) if key == 'size' else values[0]
    declared = dict(re.findall(r'^SHA1 \((patch-[^)]+)\) = ([0-9a-f]{40})$', info, re.M))
    patches = sorted((recipe / 'patches').glob('patch-*'))
    need(sorted(declared) == [p.name for p in patches], 'AutoGen patch inventory differs from distinfo')
    expected = {'devel/autogen/distinfo': hashlib.sha256(read(recipe / 'distinfo')).hexdigest()}
    deltas = []
    for path in patches:
        delta = read(path)
        filtered = b''.join(line for line in delta.splitlines(keepends=True) if b'$NetBSD' not in line)
        need(hashlib.sha1(filtered).hexdigest() == declared[path.name], 'AutoGen patch checksum differs: ' + path.name)
        expected['devel/autogen/patches/' + path.name] = hashlib.sha256(delta).hexdigest()
        deltas.append((path, delta))
    archive = Path(paths.canonical_existing(args.archive))
    need(archive.name == archive_name, 'AutoGen distfile name differs from recipe')
    data = read(archive)
    hashes = sourceprep.archive_hashes(data)
    need(all(hashes[key] == wanted[key] for key in ('sha512', 'blake2s', 'size')),
         'AutoGen distfile checksum differs from recipe')
    identity = {'package': name, 'recipe': expected, 'configure_args': [],
                'archive_sha256': hashes['sha256'], 'options': '',
                'generation_recipe': generation_recipe(recipe)}
    if args.source:
        need(os.path.isdir(args.source), 'prepared AutoGen libopts source is missing')
        work_parent = None
    else:
        output = Path(args.output)
        output = Path(paths.canonical_existing(str(output.parent)), output.name)
        need(not os.path.lexists(output), 'prepared source output already exists')
        paths.reject_overlap(str(output), str(PORTS))
        work_parent = output.parent
    with tempfile.TemporaryDirectory(prefix='.autogen-libopts-', dir=work_parent) as tmp:
        tmp = Path(tmp)
        packed = tmp / archive_name
        packed.write_bytes(data)
        (tmp / 'src').mkdir()
        sourceprep.extract_archive(packed, tmp / 'src', distname, 'AutoGen')
        root = tmp / 'src' / distname
        for index, (path, delta) in enumerate(deltas):
            # pkgsrc headers may name './dir/file' (patch-ae); patch -p0 treats
            # that as 'dir/file'. Apply a copy with only that prefix removed so
            # the SDK's strict header check still guards every other path.
            local = re.sub(rb'^(---|\+\+\+) \./', rb'\1 ', delta, flags=re.M)
            if local != delta:
                path = tmp / ('normalized-' + path.name)
                path.write_bytes(local)
            sourceprep.apply_patch(args.patch, path, local, root, 'AutoGen',
                patch_args=('-p0', '-f', '-N', '-F0', '-V', 'none'),
                backup_directory=tmp / ('patch-backups-' + str(index)), allow_dev_null=True)
        need(not any(p.name.endswith(('.orig', '.rej')) for p in root.rglob('*')),
             'AutoGen patch left a backup or reject')
        (tmp / 'out').mkdir()
        try:
            result_root = tearoff.assemble(root, tmp / 'out')
        except (OSError, ValueError) as error:
            raise SDKError('cannot assemble AutoGen libopts tearoff: ' + str(error)) from error
        need((result_root / 'libopts.c').is_file() and (result_root / 'autoopts/options.h').is_file(),
             'AutoGen tearoff lacks expected libopts source')
        need(sourceprep.archive_hashes(read(archive)) == hashes, 'AutoGen distfile changed while preparing')
        need(current == selector.identity(PORTS, 'devel/autogen', args.git, sdk),
             'common AutoGen export inputs changed during preparation')
        result = prepared_receipt.write(result_root, package='devel/autogen', identity=identity)
        if args.source:
            existing = sourceprep.validate_prepared_tree(args.source, package='devel/autogen', identity=identity)
            need(existing['tree_sha256'] == result['tree_sha256'],
                 'prepared AutoGen libopts differs from the checksummed distfile and patchset')
            result = existing
        else:
            publish_directory_noreplace(result_root, output)
    sys.stdout.buffer.write(jsonio.json_bytes(result))


def verify_source(argv, sdk, jsonio, paths, process, sourceprep, SDKError):
    """Verify an already prepared tearoff without installed AutoGen tools."""
    parser = argparse.ArgumentParser(description=verify_source.__doc__)
    parser.add_argument('--git', required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    check = sub.add_parser('verify-source')
    check.add_argument('--source', required=True)
    check.add_argument('--patch', required=True)
    check.add_argument('--pkgsrc-export')
    args = parser.parse_args(argv)
    if not all(os.path.isabs(x) for x in (args.git, args.source, args.patch)):
        raise SDKError('select absolute Git, patch and source paths')
    record = jsonio.read_json(str(Path(args.source) / sourceprep.PREPARED_TREE_RECEIPT))
    identity = record.get('identity') if isinstance(record, dict) else None
    record = sourceprep.validate_prepared_tree(args.source, package='devel/autogen', identity=identity)
    if (not isinstance(identity, dict) or
            set(identity) != {'package', 'recipe', 'configure_args', 'options', 'archive_sha256', 'generation_recipe'} or
            not re.fullmatch(r'autogen-[0-9]+(?:\.[0-9]+)+(?:nb[0-9]+)?', str(identity.get('package', ''))) or
            not isinstance(identity.get('recipe'), dict) or
            not isinstance(identity.get('generation_recipe'), dict) or
            not isinstance(identity.get('configure_args'), list) or
            not all(isinstance(value, str) for value in identity['configure_args']) or
            not isinstance(identity.get('options'), str) or
            not re.fullmatch(r'[0-9a-f]{64}', str(identity.get('archive_sha256', '')))):
        raise SDKError('unrecognized AutoGen tearoff identity')
    spec = importlib.util.spec_from_file_location('pkgsrc_source_identity', PORTS / 'scripts/pkgsrc-source-identity.py')
    selector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selector)
    current = selector.identity(PORTS, 'devel/autogen', args.git, sdk)
    with tempfile.TemporaryDirectory(prefix='.autogen-verify-') as temporary:
        if args.pkgsrc_export:
            exported = selector.shared_export(args.pkgsrc_export, PORTS, args.git, sdk, args.patch)
        else:
            exported = Path(temporary) / 'pkgsrc'
            process.capture([sys.executable, '-B', str(PORTS / 'scripts/prepare-pkgsrc.py'),
                             str(exported), '--git', args.git, '--patch', args.patch],
                            env=process.sanitized_environment())
        recipe = exported / 'devel/autogen'
        def digest(path):
            f, before = paths.open_regular(str(path))
            with f:
                data = f.read()
            paths.verify_stable(str(path), before)
            return hashlib.sha256(data).hexdigest()
        expected = {'devel/autogen/distinfo': digest(recipe / 'distinfo')}
        for patch in sorted((recipe / 'patches').glob('patch-*')):
            expected['devel/autogen/patches/' + patch.name] = digest(patch)
        if identity['recipe'] != expected or identity['generation_recipe'] != generation_recipe(recipe):
            raise SDKError('prepared libopts source differs from the current common AutoGen recipe, source or patchset')
        if current != selector.identity(PORTS, 'devel/autogen', args.git, sdk):
            raise SDKError('common AutoGen export inputs changed during verification')
    sys.stdout.buffer.write(jsonio.json_bytes(record))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sdk_source.exit_error(error, 'AutoGen libopts source: ')
