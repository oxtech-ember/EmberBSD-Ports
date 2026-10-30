#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Prepare shared Node configure inputs and optionally run Node configure."""
import argparse
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys


def directory(value):
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f'path must be absolute: {path}')
    path = path.resolve(strict=True)
    if not path.is_dir():
        raise ValueError(f'not a directory: {path}')
    return path


def overlaps(left, right):
    return left == right or left in right.parents or right in left.parents


def prepared(root, package, sourceprep):
    receipt = root / 'emberbsd-prepared-source.json'
    record = json.loads(receipt.read_text())
    sourceprep.validate_prepared_tree(str(root), package=package, identity=record['identity'])


def prepare(args):
    node = directory(args.node_source)
    work = directory(args.work)
    v8 = directory(args.v8_source)
    inspector = directory(args.inspector_source)
    sdk = directory(args.sdk_source)
    jinja = directory(args.jinja_root)
    zlib = directory(args.zlib_source)
    gyp = directory(args.gyp_source)
    gyp_pkgsrc = directory(args.gyp_pkgsrc)
    bindings = directory(args.v8_python_bindings)
    resource = directory(args.v8_clang_resource)
    wrapper = Path(args.v8_cxx_wrapper)
    clang = Path(args.v8_selected_clang)
    libclang = Path(args.v8_libclang)
    for item in (wrapper, clang, libclang):
        if not item.is_absolute() or not item.is_file():
            raise ValueError(f'missing absolute V8 host tool: {item}')
    for provider in (v8, inspector, sdk, jinja, zlib, bindings, resource, gyp, gyp_pkgsrc):
        if overlaps(node, provider) or overlaps(work, provider):
            raise ValueError(f'work or Node source overlaps provider: {provider}')
    if work == node or node in work.parents:
        raise ValueError('work must not be inside the Node source')
    deps = node / 'deps'
    if deps.is_symlink() or deps.resolve(strict=True).parent != node:
        raise ValueError('Node deps must be a real directory inside Node source')
    destination = deps / 'v8'
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError('Node deps/v8 must be a real directory')
    sys.path.insert(0, str(sdk / 'src'))
    from emberbsd_sdk import sourceprep
    prepared(v8, 'lang/v8', sourceprep)
    prepared(inspector, 'devel/inspector-protocol', sourceprep)
    verifier = gyp_pkgsrc / 'devel/gyp/files/verify-source.py'
    subprocess.run([sys.executable, '-B', '-I', '-S', str(verifier), '--sdk-source', str(sdk),
                    '--source', str(gyp), '--pkgsrc-root', str(gyp_pkgsrc)], check=True)
    backup = work / 'node-bundled-v8'
    if backup.exists() or backup.is_symlink():
        if backup.is_symlink() or not backup.is_dir():
            raise ValueError('bundled V8 backup is not a real directory')
        prepared(destination, 'lang/v8', sourceprep)
        if (destination / 'emberbsd-prepared-source.json').read_bytes() != (v8 / 'emberbsd-prepared-source.json').read_bytes():
            raise ValueError('existing Node V8 belongs to a different provider')
    else:
        for parent, dirs, files in os.walk(v8, followlinks=False):
            for name in dirs + files:
                item = Path(parent) / name
                if item.is_symlink():
                    target = Path(os.readlink(item))
                    if target.is_absolute() or not item.resolve(strict=True).is_relative_to(v8):
                        raise ValueError(f'V8 symlink escapes prepared source: {item}')
        os.rename(destination, backup)
        shutil.copytree(v8, destination, symlinks=True)
        prepared(destination, 'lang/v8', sourceprep)
    rolled = work / 'v8-inspector-rolled'
    subprocess.run([sys.executable, '-B', str(destination / 'third_party/inspector_protocol/roll.py'),
                    '--build-source', str(inspector), '--build-root', str(work),
                    '--build-output', str(rolled), '--build-receipt',
                    str(inspector / 'emberbsd-prepared-source.json'), '--build-sdk-source', str(sdk)],
                   check=True, stdout=sys.stderr)
    return [f'-Dember_v8_cxx_wrapper={wrapper}', f'-Dember_v8_selected_clang={clang}',
            f'-Dember_v8_libclang={libclang}', f'-Dember_v8_python_bindings={bindings}',
            f'-Dember_v8_clang_resource={resource}', f'-Dinspector_protocol_root={inspector}', f'-Dv8_inspector_protocol_root={rolled}',
            f'-Dv8_inspector_work_root={work}', f'-Dv8_inspector_sdk_source={sdk}',
            f'-Dinspector_jinja_root={jinja}', f'-Dember_zlib_source={zlib}']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'configure'))
    for option in ('node-source', 'work', 'v8-source', 'inspector-source', 'sdk-source', 'jinja-root', 'zlib-source', 'v8-cxx-wrapper', 'v8-selected-clang',
                   'v8-libclang', 'v8-python-bindings', 'v8-clang-resource', 'gyp-source', 'gyp-pkgsrc'):
        p.add_argument('--' + option, required=True)
    raw = sys.argv[1:]
    if '--' in raw:
        split = raw.index('--')
        raw, rest = raw[:split], raw[split + 1:]
    else:
        rest = []
    a = p.parse_args(raw)
    try:
        defines = prepare(a)
        if a.action == 'prepare':
            if rest:
                p.error('prepare does not accept configure arguments')
            print(json.dumps({'gyp_args': defines, 'environment': {'NODE_GYP_SOURCE': str(directory(a.gyp_source))}}))
        else:
            subprocess.run([sys.executable, '-B', str(Path(a.node_source) / 'configure'), *rest, *defines],
                           cwd=a.node_source, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
                                            'NODE_GYP_SOURCE': str(directory(a.gyp_source))}, check=True)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        p.exit(1, f'node configure inputs: {error}\n')


if __name__ == '__main__':
    main()
