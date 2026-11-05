#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Create the Electron host dependency view with the selected pkgsrc buildlink phase."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import sys

# Published before catalog provenance was removed from buildlink identity.
LEGACY_SELECTION_SELF_SHA256 = 'bf32e53d13d5a2df2804064f0708ebf455b25cfbee2a36248434e7838ac4b956'


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


def check_installed_context(process, command, env, prefix):
    """Reject target metadata and an unselected native compiler or package DB."""
    variables = ('USE_CROSS_COMPILE', '_CROSS_DESTDIR', 'PKG_CONFIG_SYSROOT_DIR',
                 'PKGSRC_COMPILER', 'CLANGBASE', 'PKG_DBDIR')
    query = command[:-1] + [part for name in variables for part in ('-V', name)]
    values = process.capture(query, env=env).stdout.decode('utf-8', 'strict').splitlines()
    if len(values) != len(variables):
        raise ValueError('incomplete installed host context')
    cross, dest, pcroot, family, clangbase, pkgdb = values
    if (cross.lower() != 'no' or dest or pcroot or family != 'clang' or
            Path(clangbase).resolve() != prefix.resolve() or
            Path(pkgdb).resolve() != (prefix / 'pkgdb').resolve()):
        raise ValueError('installed host context contains target or foreign tool selection')


def migrate_legacy_selection(saved, current, invocation, script, revision):
    """Accept only the known legacy algorithm with unchanged actual inputs."""
    old = saved.get('identity')
    if (saved.get('invocation') != invocation or not isinstance(old, dict) or
            set(old) != {'inputs', 'links'} or not isinstance(old.get('inputs'), dict)):
        raise ValueError('invalid legacy host buildlink selection')
    old_inputs = dict(old['inputs'])
    current_inputs = dict(current['inputs'])
    if (old_inputs.pop(str(script), None) != LEGACY_SELECTION_SELF_SHA256 or
            old_inputs.pop(str(revision), None) is None or
            current_inputs.pop(str(script), None) is None or
            old_inputs != current_inputs or old.get('links') != current['links']):
        raise ValueError('legacy host buildlink actual inputs changed')
    return dict(identity=current, invocation=invocation)


def _normal_work_file(path, work):
    """Normalize only generated fields whose meaning is rooted in this workdir."""
    path, work = Path(path), Path(work)
    rel = path.relative_to(work).as_posix()
    data = path.read_bytes()
    prefix = str(work).encode()
    if rel == 'make.conf':
        for key, suffix in ((b'WRKOBJDIR', b'/objects'), (b'PACKAGES', b'/packages')):
            data = data.replace(key + b'= ' + prefix + suffix + b'\n',
                                key + b'= @WORK@' + suffix + b'\n')
    elif rel.endswith('/.wrapper_makevars.mk'):
        key = b'_BLNK_PHYSICAL_PATH.WRKDIR=\t'
        data = data.replace(key + prefix + b'/objects/devel/electron-host-context/work\n',
                            key + b'@WORK@/objects/devel/electron-host-context/work\n')
    elif re.fullmatch(r'objects/devel/electron-host-context/work/\.buildlink/\.buildlink_[^/]+_done', rel):
        start = prefix + b'/objects/devel/electron-host-context/work/.buildlink/'
        data = b''.join((b'@WORK@/' + line[len(start):] if line.startswith(start) and b' -> ' in line else line)
                        for line in data.splitlines(keepends=True))
    elif re.fullmatch(r'objects/devel/electron-host-context/work/\.buildlink/lib/[^/]+\.la', rel):
        old = b"libdir='" + prefix + b"/objects/devel/electron-host-context/work/.buildlink/lib'\n"
        data = data.replace(old, b"libdir='@WORK@/lib'\n")
    return hashlib.sha256(data).hexdigest()


def refresh_selection(saved, current, candidate, invocation, candidate_invocation, work, candidate_work, source, script):
    """Accept an owner-generated candidate only when all selected artifacts agree."""
    old = saved.get('identity', {})
    if saved.get('invocation') != invocation:
        raise ValueError('host buildlink invocation changed')
    expected = dict(invocation); expected['work'] = str(candidate_work)
    if candidate_invocation != expected:
        raise ValueError('host buildlink candidate invocation changed')
    if old.get('links') != current.get('links') or current.get('links') != candidate.get('links'):
        raise ValueError('host buildlink link mapping changed')
    old_inputs, now = old.get('inputs', {}), current.get('inputs', {})
    # An export may materialize formerly symlinked recipe inputs. Map only the
    # prior owner package tree to the same relative paths in the selected export.
    suffix = '/devel/electron44/files/host-buildlink.py'
    owners = [path for path in old_inputs if path.endswith(suffix)]
    if len(owners) != 1 or not str(script).endswith(suffix):
        raise ValueError('ambiguous prior host buildlink owner')
    previous_root = owners[0][:-len(suffix)]
    current_root = str(script)[:-len(suffix)]
    selected_root = str(Path(source))
    targets = {str((Path(work) / 'objects/devel/electron-host-context/work/.buildlink' / name).resolve(strict=True))
               for name in current['links']}
    def canonical(path, owner_root):
        if path not in targets and path.startswith(owner_root + '/'):
            return selected_root + path[len(owner_root):]
        return path
    def map_inputs(inputs, owner_root):
        mapped = {}
        for path, digest in inputs.items():
            path = canonical(path, owner_root)
            if path in mapped and mapped[path] != digest:
                raise ValueError('conflicting host buildlink source paths')
            mapped[path] = digest
        return mapped
    old_inputs = map_inputs(old_inputs, previous_root)
    now = map_inputs(now, current_root)
    canonical_script = canonical(str(script), current_root)
    # Makefile inputs may legitimately change; all other prior inputs remain exact.
    allowed = str(Path(source) / 'mk') + '/'
    if set(old_inputs) != set(now):
        raise ValueError('host buildlink original input set changed')
    for path, digest in old_inputs.items():
        if now[path] != digest and (path in targets or not (path.startswith(allowed) or path == canonical_script)):
            raise ValueError('host buildlink prior selected input changed: ' + path)
    def normalized(identity, base):
        result = {}
        base = Path(base)
        for path, digest in identity['inputs'].items():
            p = Path(path)
            if p.is_relative_to(base):
                key = '@WORK@/' + p.relative_to(base).as_posix()
                digest = _normal_work_file(p, base)
            else:
                key = canonical(path, current_root)
            if key in result and result[key] != digest:
                raise ValueError('conflicting regenerated host buildlink inputs')
            result[key] = digest
        return result
    if normalized(current, work) != normalized(candidate, candidate_work):
        raise ValueError('host buildlink regenerated inputs changed')
    return dict(identity=current, invocation=invocation)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'pkgsrc-root', 'host-prefix',
                 'base-makeconf', 'binding-record', 'bmake-mk', 'work', 'lock-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--shared-ffmpeg', action='store_true')
    parser.add_argument('--shared-minizip', action='store_true')
    parser.add_argument('--shared-xml', action='store_true')
    parser.add_argument('--shared-image', action='store_true')
    parser.add_argument('--shared-font', action='store_true')
    parser.add_argument('--shared-codecs', action='store_true')
    parser.add_argument('--stage-root', type=Path, help='explicit replacement stage; omit for installed prefix')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='check an existing view identity')
    mode.add_argument('--migrate-selection', action='store_true',
                      help='upgrade a matching legacy selection after validating actual inputs')
    mode.add_argument('--refresh-from', type=Path, help='refresh an equivalent owner-generated selection')
    args = parser.parse_args()
    for name, value in vars(args).items():
        if isinstance(value, Path) and not value.is_absolute():
            parser.error('--' + name.replace('_', '-') + ' must be absolute')
    sdk_root = args.sdk_source.resolve(strict=True)
    sys.path.insert(0, str(sdk_root / 'src'))
    from emberbsd_sdk import darwin_makeconf, host_prefix, process, jsonio
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk import paths
    for module in (darwin_makeconf, host_prefix, process, paths, jsonio):
        if Path(module.__file__).resolve() != sdk_root / 'src/emberbsd_sdk' / (module.__name__.split('.')[-1] + '.py'):
            raise SDKError('selected SDK module origin differs')
    native = host_prefix.load_host_prefix(args.host_prefix, required_roles=('make', 'python', 'cc', 'cxx', 'cpp'),
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
                  if isinstance(value, Path) and name != 'refresh_from'}
    if args.shared_ffmpeg:
        invocation['shared_ffmpeg'] = 'yes'
    if args.shared_minizip:
        invocation['shared_minizip'] = 'yes'
    if args.shared_xml:
        invocation['shared_xml'] = 'yes'
    if args.shared_image:
        invocation['shared_image'] = 'yes'
    if args.shared_font:
        invocation['shared_font'] = 'yes'
    if args.shared_codecs:
        invocation['shared_codecs'] = 'yes'
    paths.reject_overlap(str(work), str(source))
    paths.reject_overlap(str(work), str(args.host_prefix))
    if args.stage_root:
        paths.reject_overlap(str(work), str(args.stage_root))
    work_locks = [str(work)] + ([str(args.refresh_from)] if args.refresh_from else [])
    if args.refresh_from and args.refresh_from == work:
        raise SDKError('refresh candidate must be a separate work directory')
    with process.ContextLocks(work_locks, str(args.lock_root), shared=args.check):
        lock_inputs = [str(source), str(args.host_prefix), str(args.binding_record), str(args.sdk_source)]
        if args.stage_root:
            lock_inputs.append(str(args.stage_root))
        with process.ContextLocks(lock_inputs,
                                  str(args.lock_root), shared=True):
            if args.check or args.migrate_selection or args.refresh_from:
                consumer = work / 'pkgsrc/devel/electron-host-context'
                view = work / 'objects/devel/electron-host-context/work/.buildlink'
                env = process.sanitized_environment()
                env.update(PATH=native.path, MAKECONF=str(work / 'make.conf'), EMBERBSD_SDK_SOURCE=str(sdk_root))
                command = [native.tool('make'), '-m', str(args.bmake_mk), '-C', str(consumer),
                           *(['EMBERBSD_DARWIN_BOOTSTRAP=yes'] if args.stage_root else ['USE_CROSS_COMPILE=no']),
                           'DEPENDS_TARGET=emberbsd-refuse-unpreflighted-dependency',
                           'EMBERBSD_ELECTRON_HOST_DEPENDENCIES=' + str(deps),
                           *(['EMBERBSD_ELECTRON_SHARED_FFMPEG=yes'] if args.shared_ffmpeg else []),
                           *(['EMBERBSD_ELECTRON_SHARED_MINIZIP=yes'] if args.shared_minizip else []),
                           *(['EMBERBSD_ELECTRON_SHARED_XML=yes'] if args.shared_xml else []),
                           *(['EMBERBSD_ELECTRON_SHARED_IMAGE=yes'] if args.shared_image else []),
                           *(['EMBERBSD_ELECTRON_SHARED_FONT=yes'] if args.shared_font else []),
                           *(['EMBERBSD_ELECTRON_SHARED_CODECS=yes'] if args.shared_codecs else []), 'wrapper']
                saved = json.loads((work / 'selection.json').read_text())
                if saved.get('invocation') != invocation:
                    print('host buildlink selection changed', file=sys.stderr)
                    sys.exit(3)
                if not args.stage_root:
                    check_installed_context(process, command, env, args.host_prefix)
                try:
                    current = identity(process, command, env, consumer, view, args.host_prefix,
                                       (Path(__file__), args.binding_record, deps,
                                        Path(darwin_makeconf.__file__)))
                except (FileNotFoundError, process.CommandError):
                    print('host buildlink selection changed', file=sys.stderr)
                    sys.exit(3)
                if args.refresh_from:
                    candidate_work = args.refresh_from
                    candidate_consumer = candidate_work / 'pkgsrc/devel/electron-host-context'
                    candidate_view = candidate_work / 'objects/devel/electron-host-context/work/.buildlink'
                    candidate_env = dict(env, MAKECONF=str(candidate_work / 'make.conf'))
                    candidate_command = list(command)
                    candidate_command[candidate_command.index(str(consumer))] = str(candidate_consumer)
                    candidate_saved = jsonio.read_json(candidate_work / 'selection.json')
                    candidate = identity(process, candidate_command, candidate_env, candidate_consumer,
                                         candidate_view, args.host_prefix,
                                         (Path(__file__), args.binding_record, deps,
                                          Path(darwin_makeconf.__file__)))
                    if candidate_saved.get('identity') != candidate:
                        raise ValueError('host buildlink candidate is stale')
                    refreshed = refresh_selection(saved, current, candidate, invocation,
                                                  candidate_saved.get('invocation'), work, candidate_work,
                                                  source, Path(__file__).resolve(strict=True))
                    jsonio.write_json(work / 'selection.json', refreshed, exclusive=False)
                elif args.migrate_selection:
                    migrated = migrate_legacy_selection(
                        saved, current, invocation, Path(__file__).resolve(strict=True),
                        (source / 'EMBERBSD-PKGSRC-REVISION').resolve(strict=True))
                    jsonio.write_json(work / 'selection.json', migrated, exclusive=False)
                elif saved.get('identity') != current:
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
            if args.stage_root:
                darwin_makeconf.write_native_stage_makeconf(
                    base=str(args.base_makeconf), output=str(makeconf), stage_root=str(args.stage_root),
                    prefix=str(args.host_prefix), object_root=str(work / 'objects'),
                    packages=str(work / 'packages'), binding_record=str(args.binding_record),
                    python=native.tool('python'), buildlinks=[])
            else:
                record = json.loads(args.binding_record.read_text())
                if 'native_cxx_runtime' in record:
                    raise SDKError('installed prefix requires platform C++ binding')
                for role in ('cc', 'cxx', 'cpp'):
                    if record['commands'][role] != list(native.command(role)):
                        raise SDKError('installed binding differs from selected prefix tool: ' + role)
                if (record['flags'] != {name: list(flags) for name, flags in native.abi_flags.items()} or
                        record.get('link_flags') != {'cc': [], 'cxx': []}):
                    raise SDKError('installed binding contains foreign compiler or linker flags')
                if not (args.host_prefix / 'pkgdb').is_dir():
                    raise SDKError('installed prefix package database missing')
                for path in (args.base_makeconf, args.host_prefix, work, args.binding_record):
                    if any(char in str(path) for char in ('\n', '\r', '"', '$', '#')):
                        raise SDKError('unsupported makeconf path')
                adapters = args.binding_record.parent
                makeconf.write_text('.include "' + str(args.base_makeconf) + '"\n' +
                    'PKGSRC_COMPILER= clang\nCLANGBASE= ' + str(args.host_prefix) + '\nLOCALBASE= ' + str(args.host_prefix) + '\nPKG_DBDIR= ' + str(args.host_prefix / 'pkgdb') +
                    '\nWRKOBJDIR= ' + str(work / 'objects') + '\nPACKAGES= ' + str(work / 'packages') +
                    '\nCC= ' + str(adapters / 'cc') + '\nCXX= ' + str(adapters / 'cxx') +
                    '\nCPP= ' + str(adapters / 'cpp') + '\n')
            env = process.sanitized_environment()
            env.update(PATH=native.path, MAKECONF=str(makeconf), EMBERBSD_SDK_SOURCE=str(sdk_root))
            command = [native.tool('make'), '-m', str(args.bmake_mk), '-C', str(consumer),
                       *(['EMBERBSD_DARWIN_BOOTSTRAP=yes'] if args.stage_root else ['USE_CROSS_COMPILE=no']),
                           'DEPENDS_TARGET=emberbsd-refuse-unpreflighted-dependency',
                       'EMBERBSD_ELECTRON_HOST_DEPENDENCIES=' + str(deps),
                           *(['EMBERBSD_ELECTRON_SHARED_FFMPEG=yes'] if args.shared_ffmpeg else []),
                           *(['EMBERBSD_ELECTRON_SHARED_MINIZIP=yes'] if args.shared_minizip else []),
                           *(['EMBERBSD_ELECTRON_SHARED_XML=yes'] if args.shared_xml else []),
                           *(['EMBERBSD_ELECTRON_SHARED_IMAGE=yes'] if args.shared_image else []),
                           *(['EMBERBSD_ELECTRON_SHARED_FONT=yes'] if args.shared_font else []),
                           *(['EMBERBSD_ELECTRON_SHARED_CODECS=yes'] if args.shared_codecs else []), 'wrapper']
            if not args.stage_root:
                check_installed_context(process, command, env, args.host_prefix)
            process.run_logged(command, str(work / 'buildlink.log'), env=env)
            view = work / 'objects/devel/electron-host-context/work/.buildlink'
            if not (view / 'lib/pkgconfig').is_dir():
                raise SDKError('pkgsrc did not create the host buildlink view')
            selected = identity(process, command, env, consumer, view, args.host_prefix,
                                (Path(__file__), args.binding_record, deps,
                                 Path(darwin_makeconf.__file__)))
            (work / 'selection.json').write_text(json.dumps(
                dict(identity=selected, invocation=invocation), sort_keys=True))
            print(view)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sys.exit('Electron host buildlink failed: ' + str(error))
