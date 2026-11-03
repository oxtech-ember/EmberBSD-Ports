#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Refresh native pkgsrc work sources after an add-only profile patch delta.

The caller must hold the work lease, verify the active native compiler and
configuration, and run pkgsrc build-clean before invoking this command.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import runtime
import source as owner

PREFIX = 'pkgsrc/lang/compiler-rt/'
PATCH = PREFIX + 'patches/'
DIST = PREFIX + 'distinfo'
HEADER = 'compiler-rt/include/profile/InstrProfData.inc'
RECEIPT = '.ember-profile-source-refresh.json'


def require(value, message):
    if not value:
        raise ValueError(message)


def regular(root, name, missing=False):
    """Reject traversal and links in every component of a selected file."""
    parts = Path(name).parts
    require(not Path(name).is_absolute() and parts and
            all(p not in ('', '.', '..') for p in parts), 'unsafe relative path')
    path = root
    for i, part in enumerate(parts):
        path = path / part
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            require(missing and i == len(parts) - 1, 'missing source: ' + str(path))
            return None
        require(not stat.S_ISLNK(mode), 'symlink in selected source: ' + str(path))
        require(stat.S_ISREG(mode) if i == len(parts) - 1 else stat.S_ISDIR(mode),
                'unexpected source type: ' + str(path))
    return path


def atomic(path, data, mode=0o644):
    fd, temp = tempfile.mkstemp(prefix='.profile-refresh-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def apply_files(before, after, work, kind, names, identity, check=False):
    require(work.is_dir() and work.resolve() == work, 'work must be a real directory')
    stem = kind + '-' + identity['version']
    pattern = re.compile(re.escape(stem) + r'(?:nb[0-9]+)?\Z')
    require(pattern.fullmatch(identity['package']) is not None, 'wrong selected package')
    extract_name = regular(work, '.extract_done').read_text().strip()
    configured_path = regular(work, '.configure_done', missing=True)
    configured = configured_path.read_text().strip() if configured_path else None
    require(pattern.fullmatch(extract_name) is not None, 'work extract identity differs')
    require(regular(work, '.patch_done') is not None, 'missing historical patch cookie')
    if not check:
        for cookie in ('.build_done', '.install_done', '.package_done'):
            require(not os.path.lexists(work / cookie), 'run pkgsrc build-clean before refresh')
    src = work / ('llvm-project-' + identity['version'] + '.src')
    require(src.is_dir() and not src.is_symlink(), 'wrong work source')
    pending = []
    for name in sorted(names):
        if kind == 'llvm':
            if name != HEADER:
                continue
            dstname = 'llvm/include/llvm/ProfileData/InstrProfData.inc'
        else:
            dstname = name
        old = regular(before, name, missing=True)
        new = regular(after, name)
        dest = regular(src, dstname, missing=True)
        oldbytes = old.read_bytes() if old else None
        newbytes = new.read_bytes()
        current = dest.read_bytes() if dest else None
        require(current in (oldbytes, newbytes), 'work source differs: ' + dstname)
        if current != newbytes:
            pending.append((src / dstname, newbytes, stat.S_IMODE(new.stat().st_mode)))
    require(kind != 'llvm' or HEADER in names, 'shared LLVM header is not in delta')
    receipt = work / RECEIPT
    record = dict(identity, package_kind=kind, paths=sorted(names), state='pending')
    previous = None
    same = False
    chained = False
    if os.path.lexists(receipt):
        require(not receipt.is_symlink() and receipt.is_file(), 'invalid refresh receipt')
        previous = json.loads(receipt.read_text())
        require(previous.get('state') in ('pending', 'complete'), 'invalid refresh state')
        previous_configured = previous.get('configured_before')
        if 'configured_before' in previous:
            require(isinstance(previous_configured, str) and
                    pattern.fullmatch(previous_configured) is not None,
                    'invalid prior configure identity')
        same = ({k: v for k, v in previous.items() if k not in ('state', 'configured_before')} ==
                {k: v for k, v in record.items() if k != 'state'})
        chained = (previous['state'] == 'complete' and
                   previous.get('package_kind') == kind and
                   previous.get('version') == identity['version'] and
                   previous.get('after') == identity['before'] and
                   isinstance(previous.get('package'), str) and
                   configured == previous['package'] and
                   pattern.fullmatch(previous['package']) is not None)
        require(same or chained, 'different profile source refresh')
        if same and previous['state'] == 'pending' and previous_configured is not None:
            require(configured == previous_configured, 'work configure identity differs')
        if chained:
            record['configured_before'] = configured
        elif same and previous_configured is not None:
            record['configured_before'] = previous_configured
    require(chained or configured == extract_name or
            (same and previous['state'] == 'pending' and
             previous.get('configured_before') is not None and
             configured == previous['configured_before']) or
            (previous is not None and same and previous['state'] == 'complete' and
             not pending and (configured in (None, identity['package']) or
                              (previous.get('configured_before') is not None and
                               configured == previous['configured_before']))),
            'work configure identity differs')
    if check or (same and previous['state'] == 'complete' and not pending):
        return len(pending)
    atomic(receipt, (json.dumps(record, sort_keys=True) + '\n').encode())
    for dest, data, mode in pending:
        atomic(dest, data, mode)
    record['state'] = 'complete'
    atomic(receipt, (json.dumps(record, sort_keys=True) + '\n').encode())
    return len(pending)


def selected_delta(before, current, git, ports=None, include_candidates=False):
    require(before.get('format') == 'emberbsd-llvm-source' and before.get('version') in (1, 2),
            'invalid historical source manifest')
    for key in ('llvm_version', 'components', 'source'):
        require(before.get(key) == current.get(key), 'source selection changed: ' + key)
    old = before['recipe']['files']; new = current['recipe']['files']
    require(before['recipe'].get('preparation_api', 1) ==
            current['recipe'].get('preparation_api', 1), 'source preparation changed')
    old = {k: v for k, v in old.items() if k not in owner.NON_OUTPUT_INPUTS}
    new = {k: v for k, v in new.items() if k not in owner.NON_OUTPUT_INPUTS}
    changed = {k for k in old.keys() | new.keys() if old.get(k) != new.get(k)}
    patches = changed - {DIST}
    require(DIST in changed and patches and all(k.startswith(PATCH) and k not in old for k in patches),
            'expected add-only profile patch delta')
    revision = before['recipe'].get('ports_revision')
    exported = before['version'] == 2 and revision is None
    require(exported or (isinstance(revision, str) and len(revision) == 40 and
            all(c in '0123456789abcdef' for c in revision)), 'historical Git revision missing')
    if exported:
        revision = 'HEAD'
    # One Git process verifies every historic source recipe input, including
    # unchanged patches; the recorded tree identity is never rehashed.
    keys = sorted(old)
    request = b''.join((revision + ':' + name + '\n').encode() for name in keys)
    result = subprocess.run([git, '-C', str(ports or owner.PORTS), 'cat-file', '--batch'],
                            input=request, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=True).stdout
    offset = 0
    historic_data = {}
    for name in keys:
        end = result.find(b'\n', offset)
        require(end >= 0, 'incomplete historical Git response')
        fields = result[offset:end].split()
        require(len(fields) == 3 and fields[1] == b'blob' and fields[2].isdigit(),
                'historical input is not a blob: ' + name)
        size = int(fields[2]); offset = end + 1
        data = result[offset:offset + size]
        require(len(data) == size and result[offset + size:offset + size + 1] == b'\n',
                'truncated historical Git blob')
        expected = new[DIST] if exported and name == DIST else old[name]
        require(hashlib.sha256(data).hexdigest() == expected, 'historical input differs: ' + name)
        historic_data[name] = data
        offset += size + 1
    require(offset == len(result), 'unexpected historical Git output')
    old_dist = historic_data[DIST]
    new_dist = (owner.OWNER / 'distinfo').read_bytes()
    require(hashlib.sha256(new_dist).hexdigest() == new[DIST], 'current distinfo differs')
    def unrelated(data):
        return b''.join(line for line in data.splitlines(keepends=True)
                        if not any(line.startswith(b'SHA1 (' + Path(p).name.encode() + b') = ')
                                   for p in patches))
    if exported:
        for patch in patches:
            prefix = b'SHA1 (' + Path(patch).name.encode() + b') = '
            require(sum(line.startswith(prefix) for line in new_dist.splitlines()) == 1,
                    'new patch distinfo entry is missing or duplicated')
        old_dist = unrelated(old_dist)
        require(hashlib.sha256(old_dist).hexdigest() == old[DIST], 'historical distinfo differs')
    require(unrelated(old_dist) == unrelated(new_dist), 'unrelated distinfo changed')
    names = set()
    for p in sorted(patches):
        data = (owner.OWNER / 'patches' / Path(p).name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == new[p], 'profile patch digest changed')
        require(runtime.profile_only_patch(data), 'unsupported profile patch')
        names.update(x.decode('utf-8') for x in runtime.patch_paths(data))
    if not include_candidates:
        return names
    candidates = set()
    for key, data in historic_data.items():
        if not key.startswith(PATCH) or old.get(key) != new.get(key):
            continue
        if b'compiler-rt/lib/builtins/' not in data:
            continue
        paths = runtime.patch_paths(data)
        require(paths is not None, 'unsupported unchanged builtins patch: ' + key)
        candidates.update(path.decode('utf-8') for path in paths
                          if path.startswith(b'compiler-rt/lib/builtins/') and
                          path.endswith((b'.c', b'.h', b'.inc')))
    return names, candidates - names


def mtime_plan(before, after, candidates):
    """Compare all patch-derived candidates before any timestamp write."""
    plan = []
    for name in sorted(candidates):
        old = regular(before, name)
        new = regular(after, name)
        a, b = old.stat(), new.stat()
        require(a.st_nlink == b.st_nlink == 1 and
                (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino), 'aliased source file: ' + name)
        require(old.read_bytes() == new.read_bytes(), 'unchanged patch file differs: ' + name)
        plan.append((name, a, b))
    return plan


def stat_key(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns,
            value.st_ctime_ns, value.st_nlink, value.st_mode)


def preserve_mtimes(before, after, plan):
    # Caller holds source leases across planning and writes. Validate the whole
    # write set once more before the first change, and each file when opened.
    for name, a, b in plan:
        require(stat_key(regular(before, name).stat()) == stat_key(a) and
                stat_key(regular(after, name).stat()) == stat_key(b),
                'source changed during timestamp planning: ' + name)
    count = 0
    for name, a, b in plan:
        if a.st_mtime_ns == b.st_mtime_ns:
            continue
        path = regular(after, name)
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        try:
            require(stat_key(os.fstat(fd)) == stat_key(b), 'source changed before timestamp write: ' + name)
            os.utime(fd, ns=(b.st_atime_ns, a.st_mtime_ns))
        finally:
            os.close(fd)
        count += 1
    return count


def main(argv):
    global owner
    require('--sdk-source' in argv and argv.index('--sdk-source') + 1 < len(argv),
            'select SDK source')
    sdk_source = argv[argv.index('--sdk-source') + 1]
    argv = owner.load_sdk(argv)
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('before', 'source', 'git', 'ports', 'pkgsrc-root'):
        parser.add_argument('--' + arg, required=True)
    parser.add_argument('--work')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--list-changes', action='store_true', help='emit verified source paths as JSON')
    modes.add_argument('--preserve-mtime', action='store_true', help='preserve timestamps for identical unchanged patch files')
    parser.add_argument('--check', action='store_true', help='preflight without writes')
    parser.add_argument('--package-name')
    parser.add_argument('--package-kind', choices=('compiler-rt', 'llvm'))
    args = parser.parse_args(argv)
    for value in (args.before, args.source, args.git, args.ports, args.pkgsrc_root):
        require(os.path.isabs(value), 'select absolute paths')
    exported_files = Path(args.pkgsrc_root) / 'lang/compiler-rt/files'
    # Keep the source owner's own export selection and API; the imported
    # checksum helper must be exactly the one packaged in that export.
    require((exported_files / 'profile_patch.py').read_bytes() ==
            (Path(__file__).parent / 'profile_patch.py').read_bytes(),
            'checksum helper differs from selected export')
    spec = importlib.util.spec_from_file_location('exported_profile_source',
                                                 exported_files / 'source.py')
    exported = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exported)
    exported.load_sdk(['--sdk-source', sdk_source])
    exported.select_recipe_root(args.pkgsrc_root)
    owner = exported
    before = Path(args.before); after = Path(args.source)
    for root in (before, after):
        require(root.is_dir() and root.resolve() == root, 'source root must be canonical and real')
    require(before != after and not before.is_relative_to(after) and
            not after.is_relative_to(before), 'source roots must not overlap')
    manifest = regular(before, owner.SOURCE_MANIFEST)
    regular(after, owner.SOURCE_MANIFEST)
    previous = json.loads(manifest.read_text())
    current = owner.verify_source(str(after), args.git)
    if args.list_changes:
        require(not args.check and args.work is None and args.package_name is None and
                args.package_kind is None, 'unexpected package or check arguments')
        names = selected_delta(previous, current, args.git, args.ports)
        print(json.dumps({'version': 1, 'changed_paths': sorted(names)}, sort_keys=True))
        return
    if args.preserve_mtime:
        require(args.work is None and args.package_name is None and args.package_kind is None,
                'unexpected package arguments')
        names, candidates = selected_delta(previous, current, args.git, args.ports,
                                           include_candidates=True)
        plan = mtime_plan(before, after, candidates)
        planned = sum(a.st_mtime_ns != b.st_mtime_ns for _, a, b in plan)
        updated = 0 if args.check else preserve_mtimes(before, after, plan)
        print(json.dumps({'version': 1, 'candidates': len(plan),
                          'planned': planned, 'updated': updated}, sort_keys=True))
        return
    require(args.work and os.path.isabs(args.work) and args.package_name and args.package_kind,
            'select absolute work and package identity')
    work = Path(args.work)
    names = selected_delta(previous, current, args.git, args.ports)
    identity = dict(version=current['llvm_version'], before=previous['tree_sha256'],
                    after=current['tree_sha256'], package=args.package_name)
    count = apply_files(before, after, work, args.package_kind, names, identity, check=args.check)
    print('would refresh files:' if args.check else 'refreshed files:', count)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        raise SystemExit('profile source refresh: ' + str(exc)) from exc
