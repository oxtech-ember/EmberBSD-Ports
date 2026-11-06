#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Create the Electron host dependency view with the selected pkgsrc buildlink phase."""
import argparse
import base64
import hashlib
import json
import os
import re
import stat
import tempfile
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
        root = prefix + b'/objects/devel/electron-host-context/work/.buildlink/'
        data = b''.join(line.replace(root, b'@WORK@/buildlink/')
                        if line.startswith(b"dependency_libs='") else line
                        for line in data.splitlines(keepends=True))
    return hashlib.sha256(data).hexdigest()


def _additive_wrapper(old, candidate, old_work, candidate_work, prefix, candidate_inputs):
    """Accept only paired new provider entries in generated make variables."""
    def lines(data, work):
        old = b'_BLNK_PHYSICAL_PATH.WRKDIR=\t' + str(work).encode() + b'/objects/devel/electron-host-context/work\n'
        return data.replace(old, b'_BLNK_PHYSICAL_PATH.WRKDIR=\t@WORK@/objects/devel/electron-host-context/work\n').splitlines(keepends=True)
    before, after = lines(old, old_work), lines(candidate, candidate_work)
    remaining = []
    old_index = 0
    for line in after:
        if old_index < len(before) and line == before[old_index]:
            old_index += 1
        else:
            remaining.append(line)
    if old_index != len(before):
        raise ValueError('existing generated wrapper line changed')
    additions = {}
    pattern = re.compile(rb'^([A-Za-z0-9_+.-]+)=[ \t]*(.*?)\n$')
    old_keys = set()
    for line in before:
        match = pattern.fullmatch(line)
        if match:
            if match.group(1) in old_keys:
                raise ValueError('duplicate existing generated wrapper key')
            old_keys.add(match.group(1))
    for line in remaining:
        match = pattern.fullmatch(line)
        if not match:
            raise ValueError('unsupported generated wrapper addition')
        key, value = match.groups()
        if key in additions or key in old_keys:
            raise ValueError('duplicate generated wrapper key')
        additions[key] = value.decode('utf-8', 'strict')
    names = {key.removeprefix(b'BUILDLINK_PREFIX.') for key in additions
             if key.startswith(b'BUILDLINK_PREFIX.')}
    for name in names:
        if not re.fullmatch(rb'[A-Za-z0-9_+.-]+', name):
            raise ValueError('invalid new generated provider name')
        if additions.get(b'BUILDLINK_PREFIX.' + name) != str(prefix):
            raise ValueError('new generated provider prefix is foreign')
        db = additions.get(b'_BLNK_PKG_DBDIR.' + name)
        if not db or Path(db).parent != Path(prefix) / 'pkgdb':
            raise ValueError('new generated provider package is foreign')
        if str(Path(db) / '+CONTENTS') not in candidate_inputs:
            raise ValueError('new generated provider package is not selected')
    consumed = {kind + name for name in names for kind in (b'BUILDLINK_PREFIX.', b'_BLNK_PKG_DBDIR.')}

    def selected_bytes(path):
        path = Path(path)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or path.resolve(strict=True) != path:
            raise ValueError('selected wrapper input is not a canonical regular file')
        data = path.read_bytes()
        after = path.lstat()
        stable = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if stable(info) != stable(after) or hashlib.sha256(data).hexdigest() != candidate_inputs.get(str(path)):
            raise ValueError('selected wrapper input differs from candidate identity')
        return data

    metadata = {}
    def selected_metadata(name):
        if name not in names:
            raise ValueError('wrapper metadata lacks a new selected provider')
        if name not in metadata:
            db = Path(additions[b'_BLNK_PKG_DBDIR.' + name])
            metadata[name] = (selected_bytes(db / '+CONTENTS').decode('utf-8', 'strict').splitlines(),
                              selected_bytes(db / '+BUILD_INFO').decode('utf-8', 'strict').splitlines())
        return metadata[name]

    file_keys = {
        b'FIND_FILES_libX11': (b'libX11', 'lib/pkgconfig/x11.pc'),
        b'FIND_FILES_libxcb': (b'libxcb', 'lib/pkgconfig/xcb.pc'),
        b'FIND_FILES_xcb-proto': (b'xcb-proto', 'share/pkgconfig/xcb-proto.pc'),
        b'FIND_FILES_xorgproto': (b'xorgproto', 'lib/pkgconfig/xproto.pc'),
        b'H_XAUTH': (b'libXau', 'include/X11/Xauth.h'),
        b'H_XDMCP': (b'libXdmcp', 'include/X11/Xdmcp.h'),
    }
    for key, (name, relative) in file_keys.items():
        if key not in additions:
            continue
        path = Path(prefix) / relative
        if additions[key] != str(path):
            raise ValueError('selected wrapper file path is foreign')
        contents, _ = selected_metadata(name)
        matches = []; cwd = None
        for index, line in enumerate(contents):
            if line == '@cwd':
                cwd = None
            elif line.startswith('@cwd '):
                cwd = line[5:]
            elif line == relative:
                if cwd != str(prefix) or index + 1 >= len(contents):
                    raise ValueError('selected wrapper file has invalid package cwd')
                matches.append(contents[index + 1])
        if len(matches) != 1 or not re.fullmatch(r'@comment MD5:[0-9a-f]{32}', matches[0]):
            raise ValueError('selected wrapper file is not uniquely owned')
        data = selected_bytes(path)
        if hashlib.md5(data, usedforsecurity=False).hexdigest() != matches[0].split(':', 1)[1]:
            raise ValueError('selected wrapper file differs from package checksum')
        consumed.add(key)
    for name in names:
        builtin = (b'IS_BUILTIN.' + name, b'USE_BUILTIN.' + name)
        present = [key for key in builtin if key in additions]
        if present:
            if len(present) != 2 or any(additions[key] != 'no' for key in builtin):
                raise ValueError('invalid new builtin provider selection')
            selected_metadata(name)
            consumed.update(builtin)
        key = b'PKG_BUILD_OPTIONS.' + name
        if key in additions:
            value = additions[key]
            if value and not re.fullmatch(r'[A-Za-z0-9_+.-]+(?: [A-Za-z0-9_+.-]+)*', value):
                raise ValueError('invalid package build options')
            _, info = selected_metadata(name)
            options = [line.removeprefix('PKG_OPTIONS=') for line in info if line.startswith('PKG_OPTIONS=')]
            if len(options) != 1 or options[0] != value:
                raise ValueError('package build options differ from selected package')
            consumed.add(key)
    if set(additions) != consumed:
        raise ValueError('unsupported or unpaired generated wrapper addition')
    candidate_path = b'_BLNK_PHYSICAL_PATH.WRKDIR=\t' + str(candidate_work).encode() + b'/objects/devel/electron-host-context/work\n'
    old_path = b'_BLNK_PHYSICAL_PATH.WRKDIR=\t' + str(old_work).encode() + b'/objects/devel/electron-host-context/work\n'
    return candidate.replace(candidate_path, old_path)


def _saved_selection_command(command, saved):
    """Query an existing wrapper using only the flags which created it."""
    selection = saved.get('invocation')
    if not isinstance(selection, dict) or not command or command[-1] != 'wrapper':
        raise ValueError('invalid saved host buildlink selection')
    flags = ('ffmpeg', 'minizip', 'xml', 'image', 'font', 'pdf_libraries',
             'codecs', 'openh264', 'pffft', 'expat', 'cpuinfo', 'spirv_tools',
             'vulkan', 'woff2', 'snappy')
    prefix = 'EMBERBSD_ELECTRON_SHARED_'
    if any(key.startswith('shared_') and key.removeprefix('shared_') not in flags
           for key in selection):
        raise ValueError('unknown saved host buildlink provider flag')
    if any(arg.startswith(prefix) and arg.split('=', 1)[0].removeprefix(prefix).lower() not in flags
           for arg in command[:-1]):
        raise ValueError('unknown requested host buildlink provider flag')
    base = [arg for arg in command[:-1] if not arg.startswith(prefix)]
    for flag in flags:
        value = selection.get('shared_' + flag)
        if value not in (None, 'yes'):
            raise ValueError('invalid saved host buildlink provider flag')
        if value == 'yes':
            base.append(prefix + flag.upper() + '=yes')
    return base + ['wrapper']


def _new_external_inputs(candidate_external, external, new_targets, invocation, prefix):
    """Admit selected pkgsrc makefiles and paired native package metadata."""
    added = set(candidate_external) - set(external) - new_targets
    if not added:
        return set()
    export = Path(invocation['pkgsrc_root']).resolve(strict=True)
    owner = Path(__file__).resolve().parents[3]
    db = (prefix / 'pkgdb').resolve(strict=True)
    metadata = set()
    for value in added:
        path = Path(value)
        if not path.is_absolute() or path.resolve(strict=True) != path or not path.is_file():
            raise ValueError('invalid new host buildlink input')
        if path.is_relative_to(db):
            rel = path.relative_to(db)
            if len(rel.parts) != 2 or rel.name not in ('+CONTENTS', '+BUILD_INFO'):
                raise ValueError('unsupported new host package metadata')
            metadata.add(path)
            continue
        if path.suffix != '.mk':
            raise ValueError('unsupported new host buildlink input')
        if path.is_relative_to(export):
            continue
        if path.is_relative_to(owner):
            exported = export / path.relative_to(owner)
            if (exported.resolve(strict=True) != exported or not exported.is_file() or
                    hashlib.sha256(exported.read_bytes()).hexdigest() != candidate_external[value]):
                raise ValueError('owner makefile differs from selected pkgsrc export')
            continue
        raise ValueError('foreign new host buildlink input')
    for path in metadata:
        peer = path.with_name('+BUILD_INFO' if path.name == '+CONTENTS' else '+CONTENTS')
        if peer not in metadata and str(peer) not in external:
            raise ValueError('incomplete new host package metadata')
    return added


def _extension_plan(saved, current, candidate, invocation, candidate_invocation,
                    work, candidate_work, prefix, *, recovery=False):
    """Validate an additive candidate before touching the existing work tree."""
    expected = dict(invocation); expected['work'] = str(candidate_work)
    prior = saved.get('invocation', {})
    optional = {'shared_ffmpeg', 'shared_minizip', 'shared_xml', 'shared_image', 'shared_font',
                'shared_pdf_libraries', 'shared_codecs', 'shared_openh264', 'shared_pffft',
                'shared_expat', 'shared_cpuinfo', 'shared_woff2', 'shared_vulkan',
                'shared_spirv_tools', 'shared_snappy'}
    if (candidate_invocation != expected or
            any(prior.get(k) != invocation.get(k) for k in (prior.keys() | invocation.keys()) - optional) or
            any(prior.get(k) not in (None, invocation.get(k)) or invocation.get(k) not in (None, 'yes')
                for k in optional)):
        raise ValueError('host buildlink extension invocation changed')
    old = saved['identity']
    if (any(current['links'].get(key) != value for key, value in old['links'].items()) or
            (not recovery and old['links'] != current['links']) or
            any(candidate['links'].get(key) != value for key, value in current['links'].items())):
        raise ValueError('existing host buildlink links changed')
    if any(candidate['links'].get(key) != value for key, value in old['links'].items()):
        raise ValueError('candidate replaced an existing host buildlink')
    work, candidate_work, prefix = Path(work), Path(candidate_work), Path(prefix)
    if any(character.isspace() or character == '\\' for path in (work, candidate_work) for character in str(path)):
        raise ValueError('host work path requires unsupported generated-file escaping')
    view_rel = Path('objects/devel/electron-host-context/work/.buildlink')
    wrapper_rel = Path('objects/devel/electron-host-context/work/.wrapper_makevars.mk')
    for link in old['links']:
        path = (work / view_rel / link).resolve(strict=True)
        if (candidate_work / view_rel / link).resolve(strict=True) != path:
            raise ValueError('candidate host buildlink target changed')
        key = str(path)
        if (key not in old['inputs'] or old['inputs'][key] != current['inputs'].get(key) or
                old['inputs'][key] != candidate['inputs'].get(key)):
            raise ValueError('existing selected host input changed')
    for key in ('binding_record', 'base_makeconf'):
        path = invocation[key]
        if (path not in old['inputs'] or old['inputs'][path] != current['inputs'].get(path) or
                old['inputs'][path] != candidate['inputs'].get(path)):
            raise ValueError('host buildlink binding or base configuration changed')
    for path, digest in old['inputs'].items():
        if Path(path).name in ('+CONTENTS', '+BUILD_INFO') and (current['inputs'].get(path) != digest or
                                                                candidate['inputs'].get(path) != digest):
            raise ValueError('existing selected host package metadata changed')
    old_generated = {Path(path).relative_to(work) for path in old['inputs'] if Path(path).is_relative_to(work)}
    new_generated = {Path(path).relative_to(candidate_work) for path in candidate['inputs'] if Path(path).is_relative_to(candidate_work)}
    if not old_generated <= new_generated:
        raise ValueError('candidate removed generated host input')
    for rel in old_generated - {wrapper_rel}:
        old_path, new_path = work / rel, candidate_work / rel
        if (old_path.is_symlink() or new_path.is_symlink() or not old_path.is_file() or not new_path.is_file() or
                old_path.stat().st_mode != new_path.stat().st_mode or
                old['inputs'][str(old_path)] != current['inputs'].get(str(old_path)) or
                _normal_work_file(old_path, work) != _normal_work_file(new_path, candidate_work)):
            raise ValueError('existing generated host input changed: ' + str(rel))
    wrapper_path = work / wrapper_rel
    candidate_wrapper_path = candidate_work / wrapper_rel
    if (wrapper_path.is_symlink() or candidate_wrapper_path.is_symlink() or
            not wrapper_path.is_file() or not candidate_wrapper_path.is_file() or
            wrapper_path.stat().st_mode != candidate_wrapper_path.stat().st_mode):
        raise ValueError('existing generated host wrapper type or mode changed')
    wrapper_before = wrapper_path.read_bytes()
    old_wrapper_hash = old['inputs'].get(str(wrapper_path))
    wrapper_current_hash = hashlib.sha256(wrapper_before).hexdigest()
    candidate_wrapper = (candidate_work / wrapper_rel).read_bytes()
    if recovery and wrapper_current_hash != old_wrapper_hash:
        old_path = b'_BLNK_PHYSICAL_PATH.WRKDIR=\t' + str(work).encode() + b'/objects/devel/electron-host-context/work\n'
        new_path = b'_BLNK_PHYSICAL_PATH.WRKDIR=\t' + str(candidate_work).encode() + b'/objects/devel/electron-host-context/work\n'
        wrapper = candidate_wrapper.replace(new_path, old_path)
        if wrapper != wrapper_before:
            raise ValueError('interrupted host wrapper has foreign content')
    else:
        if wrapper_current_hash != old_wrapper_hash:
            raise ValueError('existing generated host wrapper changed')
        wrapper = _additive_wrapper(wrapper_before, candidate_wrapper, work, candidate_work, prefix, candidate['inputs'])
    files = {}
    for rel in new_generated - old_generated:
        text = rel.as_posix()
        if not (re.fullmatch(r'objects/devel/electron-host-context/work/\.buildlink/\.buildlink_[^/]+_done', text) or
                re.fullmatch(r'objects/devel/electron-host-context/work/\.buildlink/lib/[^/]+\.la', text)):
            raise ValueError('unsupported new generated host input: ' + text)
        data = (candidate_work / rel).read_bytes()
        old_prefix = str(candidate_work / view_rel).encode()
        new_prefix = str(work / view_rel).encode()
        if text.endswith('.la'):
            data = b''.join(line.replace(old_prefix, new_prefix)
                            if line.startswith((b"dependency_libs='", b"libdir='")) else line
                            for line in data.splitlines(keepends=True))
        else:
            data = b''.join(line.replace(old_prefix + b'/', new_prefix + b'/', 1)
                            if line.startswith(old_prefix + b'/') and b' -> ' in line else line
                            for line in data.splitlines(keepends=True))
        if str(candidate_work).encode() in data:
            raise ValueError('unsupported candidate path in generated input')
        files[rel.as_posix()] = data
    added = {key: value for key, value in candidate['links'].items() if key not in old['links']}
    if any(not Path(value).is_absolute() or str(candidate_work) in value for value in added.values()):
        raise ValueError('new host buildlink target is not absolute')
    external = {key: value for key, value in current['inputs'].items() if not Path(key).is_relative_to(work)}
    candidate_external = {key: value for key, value in candidate['inputs'].items()
                          if not Path(key).is_relative_to(candidate_work)}
    new_targets = {str((candidate_work / view_rel / name).resolve(strict=True)) for name in added}
    allowed = _new_external_inputs(candidate_external, external, new_targets, invocation, prefix)
    if (set(candidate_external) != set(external) | new_targets | allowed or
            any(candidate_external.get(key) != value for key, value in external.items())):
        raise ValueError('candidate host buildlink external inputs differ')
    return wrapper, files, added


def _atomic_file(path, data, mode, *, replace, temporary_dir=None):
    fd, name = tempfile.mkstemp(prefix='.host-buildlink-', dir=temporary_dir or path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        if replace:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _safe_extension_parent(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or any(part in ('', '.', '..') for part in relative.parts):
        raise ValueError('invalid host buildlink extension path')
    parent = root
    for part in relative.parts[:-1]:
        parent = parent / part
        if os.path.lexists(parent):
            if parent.is_symlink() or not parent.is_dir():
                raise ValueError('foreign host buildlink extension directory')
        else:
            parent.mkdir()
    return root / relative


def _apply_extension(work, candidate_work, wrapper, files, links, saved, candidate):
    """Commit a validated additive plan; a marker makes interruption retryable."""
    work, candidate_work = Path(work), Path(candidate_work)
    marker = work / '.host-buildlink-extension.json'
    wrapper_rel = Path('objects/devel/electron-host-context/work/.wrapper_makevars.mk')
    view_rel = Path('objects/devel/electron-host-context/work/.buildlink')
    plan = {'candidate': str(candidate_work), 'saved': saved, 'candidate_identity': candidate,
            'wrapper': base64.b64encode(wrapper).decode(),
            'files': {k: base64.b64encode(v).decode() for k, v in sorted(files.items())},
            'links': dict(sorted(links.items()))}
    encoded = (json.dumps(plan, sort_keys=True, separators=(',', ':')) + '\n').encode()
    if os.path.lexists(marker):
        if marker.is_symlink() or not marker.is_file() or marker.read_bytes() != encoded:
            raise ValueError('foreign or changed host buildlink extension journal')
    else:
        _atomic_file(marker, encoded, 0o600, replace=False)
    for name, target in sorted(links.items()):
        path = _safe_extension_parent(work, view_rel / name)
        if os.path.lexists(path):
            if not path.is_symlink() or os.readlink(path) != target:
                raise ValueError('foreign host buildlink extension link')
        else:
            path.symlink_to(target)
    for name, data in sorted(files.items()):
        path = _safe_extension_parent(work, name)
        candidate_file = candidate_work / name
        mode = candidate_file.stat().st_mode & 0o777
        if os.path.lexists(path):
            if path.is_symlink() or not path.is_file() or path.read_bytes() != data or path.stat().st_mode & 0o777 != mode:
                raise ValueError('foreign host buildlink extension file')
        else:
            _atomic_file(path, data, mode, replace=False, temporary_dir=work)
    path = work / wrapper_rel
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    old_digest = saved['identity']['inputs'][str(path)]
    new_digest = hashlib.sha256(wrapper).hexdigest()
    if digest not in (old_digest, new_digest) or path.is_symlink():
        raise ValueError('foreign host buildlink extension wrapper')
    if digest != new_digest:
        _atomic_file(path, wrapper, path.stat().st_mode & 0o777, replace=True)


def _extension_identity(identity_value, work):
    result = {}
    work = Path(work)
    for path, digest in identity_value['inputs'].items():
        path = Path(path)
        if path.is_relative_to(work):
            key = '@WORK@/' + path.relative_to(work).as_posix()
            digest = _normal_work_file(path, work)
        else:
            key = str(path)
        if key in result and result[key] != digest:
            raise ValueError('conflicting host buildlink extension identity')
        result[key] = digest
    return {'links': identity_value['links'], 'inputs': result}


def _canonical_work(directory, *, required):
    if os.path.lexists(directory):
        if directory.is_symlink() or not directory.is_dir() or directory.resolve(strict=True) != directory:
            raise ValueError('host buildlink work must be a canonical directory')
    elif required:
        raise ValueError('host buildlink candidate directory is missing')


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
    parser.add_argument('--shared-pdf-libraries', action='store_true')
    parser.add_argument('--shared-codecs', action='store_true')
    parser.add_argument('--shared-openh264', action='store_true')
    parser.add_argument('--shared-pffft', action='store_true')
    parser.add_argument('--shared-expat', action='store_true')
    parser.add_argument('--shared-cpuinfo', action='store_true')
    parser.add_argument('--shared-vulkan', action='store_true')
    parser.add_argument('--shared-spirv-tools', action='store_true')
    parser.add_argument('--shared-woff2', action='store_true')
    parser.add_argument('--shared-snappy', action='store_true')
    parser.add_argument('--stage-root', type=Path, help='explicit replacement stage; omit for installed prefix')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='check an existing view identity')
    mode.add_argument('--migrate-selection', action='store_true',
                      help='upgrade a matching legacy selection after validating actual inputs')
    mode.add_argument('--refresh-from', type=Path, help='refresh an equivalent owner-generated selection')
    mode.add_argument('--extend-from', type=Path, help='extend an existing view from a verified additive candidate')
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
                  if isinstance(value, Path) and name not in ('refresh_from', 'extend_from')}
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
    if args.shared_pdf_libraries:
        invocation['shared_pdf_libraries'] = 'yes'
    if args.shared_codecs:
        invocation['shared_codecs'] = 'yes'
    if args.shared_openh264:
        invocation['shared_openh264'] = 'yes'
    if args.shared_pffft:
        invocation['shared_pffft'] = 'yes'
    if args.shared_expat:
        invocation['shared_expat'] = 'yes'
    if args.shared_cpuinfo:
        invocation['shared_cpuinfo'] = 'yes'
    if args.shared_vulkan:
        invocation['shared_vulkan'] = 'yes'
    if args.shared_spirv_tools:
        invocation['shared_spirv_tools'] = 'yes'
    if args.shared_woff2:
        invocation['shared_woff2'] = 'yes'
    if args.shared_snappy:
        invocation['shared_snappy'] = 'yes'
    paths.reject_overlap(str(work), str(source))
    paths.reject_overlap(str(work), str(args.host_prefix))
    if args.stage_root:
        paths.reject_overlap(str(work), str(args.stage_root))
    candidate_arg = args.refresh_from or args.extend_from
    _canonical_work(work, required=bool(args.extend_from))
    if candidate_arg:
        _canonical_work(candidate_arg, required=True)
    work_locks = [str(work)] + ([str(candidate_arg)] if candidate_arg else [])
    if candidate_arg and candidate_arg == work:
        raise SDKError('refresh candidate must be a separate work directory')
    if candidate_arg:
        paths.reject_overlap(str(work), str(candidate_arg))
    with process.ContextLocks(work_locks, str(args.lock_root), shared=args.check):
        lock_inputs = [str(source), str(args.host_prefix), str(args.binding_record), str(args.sdk_source)]
        if args.stage_root:
            lock_inputs.append(str(args.stage_root))
        with process.ContextLocks(lock_inputs,
                                  str(args.lock_root), shared=True):
            if args.check or args.migrate_selection or candidate_arg:
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
                           *(['EMBERBSD_ELECTRON_SHARED_PDF_LIBRARIES=yes'] if args.shared_pdf_libraries else []),
                           *(['EMBERBSD_ELECTRON_SHARED_CODECS=yes'] if args.shared_codecs else []),
                           *(['EMBERBSD_ELECTRON_SHARED_OPENH264=yes'] if args.shared_openh264 else []),
                           *(['EMBERBSD_ELECTRON_SHARED_PFFFT=yes'] if args.shared_pffft else []),
                           *(['EMBERBSD_ELECTRON_SHARED_EXPAT=yes'] if args.shared_expat else []),
                           *(['EMBERBSD_ELECTRON_SHARED_CPUINFO=yes'] if args.shared_cpuinfo else []),
                           *(['EMBERBSD_ELECTRON_SHARED_SPIRV_TOOLS=yes'] if args.shared_spirv_tools else []),
                           *(['EMBERBSD_ELECTRON_SHARED_VULKAN=yes'] if args.shared_vulkan else []),
                           *(['EMBERBSD_ELECTRON_SHARED_WOFF2=yes'] if args.shared_woff2 else []),
                           *(['EMBERBSD_ELECTRON_SHARED_SNAPPY=yes'] if args.shared_snappy else []), 'wrapper']
                saved = json.loads((work / 'selection.json').read_text())
                journal = work / '.host-buildlink-extension.json'
                if os.path.lexists(journal) and not args.extend_from:
                    raise ValueError('pending host buildlink extension requires recovery')
                if not args.extend_from and saved.get('invocation') != invocation:
                    print('host buildlink selection changed', file=sys.stderr)
                    sys.exit(3)
                if not args.stage_root:
                    check_installed_context(process, command, env, args.host_prefix)
                try:
                    current_command = _saved_selection_command(command, saved) if args.extend_from else command
                    current = identity(process, current_command, env, consumer, view, args.host_prefix,
                                       (Path(__file__), args.binding_record, deps,
                                        Path(darwin_makeconf.__file__)))
                except (FileNotFoundError, process.CommandError):
                    print('host buildlink selection changed', file=sys.stderr)
                    sys.exit(3)
                if candidate_arg:
                    candidate_work = candidate_arg
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
                    if args.extend_from:
                        recovering = os.path.lexists(journal)
                        if recovering and (journal.is_symlink() or not journal.is_file()):
                            raise ValueError('invalid host buildlink extension journal')
                        original = jsonio.read_json(journal)['saved'] if recovering else saved
                        if recovering and saved != original:
                            if saved != {'identity': current, 'invocation': invocation} or _extension_identity(current, work) != _extension_identity(candidate, candidate_work):
                                raise ValueError('host buildlink recovery receipt changed')
                        try:
                            wrapper, files, links = _extension_plan(original, current, candidate, invocation,
                                                                     candidate_saved.get('invocation'), work,
                                                                     candidate_work, args.host_prefix,
                                                                     recovery=recovering)
                        except (ValueError, OSError) as error:
                            if recovering:
                                raise
                            print('host buildlink cannot extend: ' + str(error), file=sys.stderr)
                            sys.exit(3)
                        _apply_extension(work, candidate_work, wrapper, files, links, original, candidate)
                        updated = identity(process, command, env, consumer, view, args.host_prefix,
                                           (Path(__file__), args.binding_record, deps,
                                            Path(darwin_makeconf.__file__)))
                        if _extension_identity(updated, work) != _extension_identity(candidate, candidate_work):
                            raise ValueError('extended host buildlink differs from candidate')
                        jsonio.write_json(work / 'selection.json', {'identity': updated, 'invocation': invocation}, exclusive=False)
                        journal.unlink()
                    else:
                        try:
                            refreshed = refresh_selection(saved, current, candidate, invocation,
                                                          candidate_saved.get('invocation'), work, candidate_work,
                                                          source, Path(__file__).resolve(strict=True))
                        except ValueError as error:
                            print('host buildlink cannot refresh: ' + str(error), file=sys.stderr)
                            sys.exit(3)
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
                           *(['EMBERBSD_ELECTRON_SHARED_PDF_LIBRARIES=yes'] if args.shared_pdf_libraries else []),
                           *(['EMBERBSD_ELECTRON_SHARED_CODECS=yes'] if args.shared_codecs else []),
                           *(['EMBERBSD_ELECTRON_SHARED_OPENH264=yes'] if args.shared_openh264 else []),
                           *(['EMBERBSD_ELECTRON_SHARED_PFFFT=yes'] if args.shared_pffft else []),
                           *(['EMBERBSD_ELECTRON_SHARED_EXPAT=yes'] if args.shared_expat else []),
                           *(['EMBERBSD_ELECTRON_SHARED_CPUINFO=yes'] if args.shared_cpuinfo else []),
                           *(['EMBERBSD_ELECTRON_SHARED_SPIRV_TOOLS=yes'] if args.shared_spirv_tools else []),
                           *(['EMBERBSD_ELECTRON_SHARED_VULKAN=yes'] if args.shared_vulkan else []),
                           *(['EMBERBSD_ELECTRON_SHARED_WOFF2=yes'] if args.shared_woff2 else []),
                           *(['EMBERBSD_ELECTRON_SHARED_SNAPPY=yes'] if args.shared_snappy else []), 'wrapper']
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
