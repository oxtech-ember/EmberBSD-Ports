#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare libopts from an installed common AutoGen package."""
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


def main():
    sdk_source.install_signal_handlers()
    sdk, argv = sdk_source.load_sdk(sys.argv[1:])
    from emberbsd_sdk import host_prefix, jsonio, paths, process, sourceprep
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.publication import publish_directory_noreplace
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
                'archive_sha256': archive_hash, 'options': options}
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
        result = sourceprep.write_prepared_tree_receipt(root, package='devel/autogen', identity=identity)
        sourceprep.validate_prepared_tree(root, package='devel/autogen', identity=identity)
        publish_directory_noreplace(root, output)
    sys.stdout.buffer.write(jsonio.json_bytes(result))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sdk_source.exit_error(error, 'AutoGen libopts source: ')
