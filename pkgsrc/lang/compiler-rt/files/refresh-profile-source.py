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
    if os.path.lexists(receipt):
        require(not receipt.is_symlink() and receipt.is_file(), 'invalid refresh receipt')
        previous = json.loads(receipt.read_text())
        require(previous.get('state') in ('pending', 'complete'), 'invalid refresh state')
        same = ({k: v for k, v in previous.items() if k != 'state'} ==
                {k: v for k, v in record.items() if k != 'state'})
        require(same, 'different profile source refresh')
    require(configured == extract_name or
            (configured in (None, identity['package']) and previous is not None and same and
             previous['state'] == 'complete' and not pending),
            'work configure identity differs')
    if check or (same and previous['state'] == 'complete' and not pending):
        return len(pending)
    atomic(receipt, (json.dumps(record, sort_keys=True) + '\n').encode())
    for dest, data, mode in pending:
        atomic(dest, data, mode)
    record['state'] = 'complete'
    atomic(receipt, (json.dumps(record, sort_keys=True) + '\n').encode())
    return len(pending)


def selected_delta(before, current, git, ports=None):
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
    require(isinstance(revision, str) and len(revision) == 40 and
            all(c in '0123456789abcdef' for c in revision), 'historical Git revision missing')
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
        require(hashlib.sha256(data).hexdigest() == old[name], 'historical input differs: ' + name)
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
    require(unrelated(old_dist) == unrelated(new_dist), 'unrelated distinfo changed')
    names = set()
    for p in sorted(patches):
        data = (owner.OWNER / 'patches' / Path(p).name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == new[p], 'profile patch digest changed')
        require(runtime.profile_only_patch(data), 'unsupported profile patch')
        names.update(x.decode('utf-8') for x in runtime.patch_paths(data))
    return names


def main(argv):
    global owner
    require('--sdk-source' in argv and argv.index('--sdk-source') + 1 < len(argv),
            'select SDK source')
    sdk_source = argv[argv.index('--sdk-source') + 1]
    argv = owner.load_sdk(argv)
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('before', 'source', 'work', 'git', 'ports', 'pkgsrc-root'):
        parser.add_argument('--' + arg, required=True)
    parser.add_argument('--check', action='store_true', help='preflight without writes')
    parser.add_argument('--package-name', required=True)
    parser.add_argument('--package-kind', choices=('compiler-rt', 'llvm'), required=True)
    args = parser.parse_args(argv)
    for value in (args.before, args.source, args.work, args.git, args.ports, args.pkgsrc_root):
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
    before = Path(args.before); after = Path(args.source); work = Path(args.work)
    for root in (before, after):
        require(root.is_dir() and root.resolve() == root, 'source root must be canonical and real')
    require(before != after, 'source roots must differ')
    manifest = regular(before, owner.SOURCE_MANIFEST)
    regular(after, owner.SOURCE_MANIFEST)
    previous = json.loads(manifest.read_text())
    current = owner.verify_source(str(after), args.git)
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
