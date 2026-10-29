#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Create the Electron host dependency view with the selected pkgsrc buildlink phase."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def identity(process, command, env, consumer, view, host_prefix, extras):
    """Capture this actual buildlink selection, not an SDK qualification."""
    def query(*variables):
        args = command[:-1]
        for variable in variables:
            args += ['-V', variable]
        return process.capture(args, env=env).stdout.decode('utf-8', 'strict').splitlines()

    makefiles, tree = query('.MAKE.MAKEFILES', '_BUILDLINK_TREE')
    inputs = {}
    def add(path):
        path = Path(path).resolve(strict=True)
        if path.is_file() and str(path) not in inputs:
            with path.open('rb') as handle:
                inputs[str(path)] = hashlib.file_digest(handle, 'sha256').hexdigest()
    for path in extras:
        add(path)
    for name in makefiles.split():
        path = Path(name)
        add(path if path.is_absolute() else consumer / path)
    providers = tree.split()
    variables = [variable + '.' + name for name in providers
                 for variable in ('BUILDLINK_API_DEPENDS', 'BUILDLINK_PREFIX', 'USE_BUILTIN')]
    details = query(*variables) if variables else []
    if len(details) != 3 * len(providers):
        raise ValueError('incomplete buildlink provider selection')
    for index, name in enumerate(providers):
        api, prefix, builtin = details[index * 3:index * 3 + 3]
        if builtin == 'yes':
            continue
        patterns = api.split()
        if not patterns:
            continue
        db = Path(prefix) / 'pkgdb'
        for pattern in patterns:
            output = process.capture([str(host_prefix / 'sbin/pkg_info'), '-K', str(db),
                                      '-E', pattern], env=env).stdout.decode('utf-8', 'strict')
            names = output.splitlines()
            if len(names) != 1:
                raise ValueError('ambiguous selected buildlink provider: ' + pattern)
            package = db / names[0]
            add(package / '+CONTENTS')
            add(package / '+BUILD_INFO')
    links = {}
    for parent, dirs, files in os.walk(view, followlinks=False):
        dirs.sort(); files.sort()
        for name in dirs + files:
            path = Path(parent) / name
            if path.is_symlink():
                links[str(path.relative_to(view))] = os.readlink(path)
                target = path.resolve(strict=True)
                if target.is_dir():
                    raise ValueError('host buildlink directory symlinks are unsupported')
                if not target.is_file():
                    raise ValueError('host buildlink symlink target is not a file')
                add(target)
            elif path.is_file():
                add(path)
    return dict(inputs=inputs, links=links)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'pkgsrc-root', 'host-prefix', 'stage-root',
                 'base-makeconf', 'binding-record', 'bmake-mk', 'work', 'lock-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--check', action='store_true', help='check an existing view identity')
    args = parser.parse_args()
    for name, value in vars(args).items():
        if isinstance(value, Path) and not value.is_absolute():
            parser.error('--' + name.replace('_', '-') + ' must be absolute')
    sdk_root = args.sdk_source.resolve(strict=True)
    sys.path.insert(0, str(sdk_root / 'src'))
    from emberbsd_sdk import darwin_makeconf, host_prefix, process
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk import paths
    for module in (darwin_makeconf, host_prefix, process, paths):
        if Path(module.__file__).resolve() != sdk_root / 'src/emberbsd_sdk' / (module.__name__.split('.')[-1] + '.py'):
            raise SDKError('selected SDK module origin differs')
    native = host_prefix.load_host_prefix(args.host_prefix, required_roles=('make', 'python'),
                                         compiler_family='clang')
    if Path(sys.executable).resolve() != Path(native.tool('python')).resolve():
        raise SDKError('run with the selected host Python')
    source = args.pkgsrc_root.resolve(strict=True)
    if not (source / 'mk/bsd.pkg.mk').is_file():
        raise SDKError('selected pkgsrc export is incomplete')
    owner = Path(__file__).resolve().parent
    deps = owner.parent / 'host-dependencies.mk'
    inputs = (deps, owner / 'host-buildlink/Makefile', owner / 'host-buildlink/PLIST')
    if not all(p.is_file() for p in inputs):
        raise SDKError('Electron host consumer inputs are missing')
    work = args.work
    invocation = {name: str(value) for name, value in vars(args).items()
                  if isinstance(value, Path)}
    paths.reject_overlap(str(work), str(source))
    paths.reject_overlap(str(work), str(args.host_prefix))
    paths.reject_overlap(str(work), str(args.stage_root))
    with process.ContextLocks([str(work)], str(args.lock_root), shared=args.check):
        with process.ContextLocks([str(source), str(args.host_prefix), str(args.stage_root),
                                   str(args.binding_record), str(args.sdk_source)],
                                  str(args.lock_root), shared=True):
            if args.check:
                consumer = work / 'pkgsrc/devel/electron-host-context'
                view = work / 'objects/devel/electron-host-context/work/.buildlink'
                env = process.sanitized_environment()
                env.update(PATH=native.path, MAKECONF=str(work / 'make.conf'), EMBERBSD_SDK_SOURCE=str(sdk_root))
                command = [native.tool('make'), '-m', str(args.bmake_mk), '-C', str(consumer),
                           'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                           'EMBERBSD_ELECTRON_HOST_DEPENDENCIES=' + str(deps), 'wrapper']
                saved = json.loads((work / 'selection.json').read_text())
                if saved.get('invocation') != invocation:
                    print('host buildlink selection changed', file=sys.stderr)
                    sys.exit(3)
                try:
                    current = identity(process, command, env, consumer, view, args.host_prefix,
                                       (Path(__file__), args.binding_record, deps,
                                        source / 'EMBERBSD-PKGSRC-REVISION',
                                        Path(darwin_makeconf.__file__)))
                except (FileNotFoundError, process.CommandError):
                    print('host buildlink selection changed', file=sys.stderr)
                    sys.exit(3)
                if saved.get('identity') != current:
                    print('host buildlink selection changed', file=sys.stderr)
                    sys.exit(3)
                print(view)
                return
            if os.path.lexists(work):
                raise SDKError('host buildlink work already exists')
            work.mkdir(parents=True)
            tree = work / 'pkgsrc'; tree.mkdir()
            for item in source.iterdir():
                if item.name != 'devel':
                    (tree / item.name).symlink_to(item, target_is_directory=item.is_dir())
            devel = tree / 'devel'; devel.mkdir()
            for item in (source / 'devel').iterdir():
                if item.name == 'electron-host-context':
                    raise SDKError('host consumer name collides with pkgsrc')
                (devel / item.name).symlink_to(item, target_is_directory=item.is_dir())
            consumer = devel / 'electron-host-context'; consumer.mkdir()
            (consumer / 'Makefile').symlink_to(inputs[1])
            (consumer / 'PLIST').symlink_to(inputs[2])
            makeconf = work / 'make.conf'
            darwin_makeconf.write_native_stage_makeconf(
                base=str(args.base_makeconf), output=str(makeconf), stage_root=str(args.stage_root),
                prefix=str(args.host_prefix), object_root=str(work / 'objects'),
                packages=str(work / 'packages'), binding_record=str(args.binding_record),
                python=native.tool('python'), buildlinks=[])
            env = process.sanitized_environment()
            env.update(PATH=native.path, MAKECONF=str(makeconf), EMBERBSD_SDK_SOURCE=str(sdk_root))
            command = [native.tool('make'), '-m', str(args.bmake_mk), '-C', str(consumer),
                       'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                       'EMBERBSD_ELECTRON_HOST_DEPENDENCIES=' + str(deps), 'wrapper']
            process.run_logged(command, str(work / 'buildlink.log'), env=env)
            view = work / 'objects/devel/electron-host-context/work/.buildlink'
            if not (view / 'lib/pkgconfig').is_dir():
                raise SDKError('pkgsrc did not create the host buildlink view')
            selected = identity(process, command, env, consumer, view, args.host_prefix,
                                (Path(__file__), args.binding_record, deps,
                                 source / 'EMBERBSD-PKGSRC-REVISION',
                                 Path(darwin_makeconf.__file__)))
            (work / 'selection.json').write_text(json.dumps(
                dict(identity=selected, invocation=invocation), sort_keys=True))
            print(view)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sys.exit('Electron host buildlink failed: ' + str(error))
