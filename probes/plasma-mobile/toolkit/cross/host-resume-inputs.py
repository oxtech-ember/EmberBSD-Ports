#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the last Qt host input block, allowing an additive runtime view."""
import hashlib
import os
import platform
from pathlib import Path
import re
import subprocess
import sys

# First producer with whole-view identities, before additive resume support.
PREDECESSOR = '2987bc8a260733ebcec67eeda99d1da40488a40fb4493fda76e37a3a28ebd329'
PREDECESSOR_CMAKE = '4ec29e9a317a7b794b4f5de60dd940065a3c034bf1c8230df92163eb9fe6ac67'

def fail(message):
    raise ValueError(message)

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect_loads(otool, path):
    arch = {'arm64': 'arm64', 'x86_64': 'x86_64'}.get(platform.machine())
    if not arch:
        fail('unsupported Darwin host architecture')
    result = subprocess.run([otool, '-arch', arch, '-l', str(path)], capture_output=True, text=True, check=True)
    output = result.stdout + result.stderr
    if 'is not an object file' in output:
        return None, []
    if not output.splitlines() or not output.splitlines()[0].endswith(':'):
        fail('cannot inspect host image: ' + str(path))
    identity = None
    loads = []
    commands = re.split(r'(?m)^Load command [0-9]+\s*$', output)[1:]
    for command in commands:
        match = re.search(r'(?m)^\s*cmd (LC_[A-Z0-9_]+)\s*$', command)
        if not match:
            fail('unexpected otool command output: ' + str(path))
        kind = match.group(1)
        if kind not in ('LC_ID_DYLIB', 'LC_LOAD_DYLIB', 'LC_LOAD_WEAK_DYLIB',
                        'LC_REEXPORT_DYLIB', 'LC_LOAD_UPWARD_DYLIB', 'LC_LAZY_LOAD_DYLIB'):
            continue
        name = re.search(r'(?m)^\s*name (.+) \(offset [0-9]+\)\s*$', command)
        if not name:
            fail('missing otool dependency name: ' + str(path))
        if kind == 'LC_ID_DYLIB':
            if identity is not None:
                fail('multiple dylib identities: ' + str(path))
            identity = name.group(1)
        else:
            loads.append(name.group(1))
    return identity, loads


def check_additions(view, old_names, work, prefix, native_prefix, otool, incremental=False):
    additions = {p.name: p for p in Path(view).iterdir() if p.name not in old_names}
    if not additions:
        return
    prefix = Path(prefix).resolve(strict=True)
    native_prefix = Path(native_prefix).resolve(strict=True)
    if not Path(otool).is_absolute() or not Path(otool).is_file() or not Path(otool).resolve().is_relative_to(prefix):
        fail('missing selected LLVM otool')
    install_names = {}
    for name, path in additions.items():
        real = path.resolve(strict=True)
        if not real.is_relative_to(prefix) and not real.is_relative_to(native_prefix):
            fail('addition outside selected native prefixes: ' + name)
        identity, _ = inspect_loads(otool, path)
        if identity is None or Path(identity).name != name:
            fail('addition is not the expected Mach-O provider: ' + name)
        install_names[name] = identity
    recorded = []
    qtbase = Path(work) / 'qtbase'
    for dirname in ('bin', 'libexec', 'lib', 'plugins'):
        directory = qtbase / dirname
        if directory.is_dir():
            for path in directory.rglob('*'):
                if path.is_file() and not path.is_symlink() and (os.access(path, os.X_OK) or path.name.endswith('.dylib')):
                    recorded.append(path)
    recorded.extend(Path(view) / name for name in old_names)
    if not recorded:
        fail('no prior Qt host images to inspect')
    # Inspect the selected prefix as well, so additions cannot shadow any of its
    # system or external static dependencies even outside the Qt image tree.
    other = [p for p in (Path(prefix) / 'lib').glob('*.dylib')
             if p.is_file() and p.name not in additions]
    referenced = set()
    seen = set()
    for path in recorded + other:
        real = path.resolve(strict=True)
        if real in seen:
            continue
        seen.add(real)
        for load in inspect_loads(otool, path)[1]:
            name = Path(load).name
            if name not in additions:
                continue
            if path in recorded:
                referenced.add(name)
            if load != install_names[name]:
                fail('addition install name differs from previous dependency: ' + load)
            if load.startswith('@'):
                fail('ambiguous previous dependency: ' + load)
            if not load.startswith('/') or load.startswith(('/usr/lib/', '/System/Library/')):
                fail('addition shadows system dependency: ' + load)
            previous = Path(load)
            if os.path.normpath(load) != load:
                fail('noncanonical previous dependency: ' + load)
            if not previous.is_relative_to(prefix) and not previous.is_relative_to(native_prefix):
                fail('previous dependency outside selected native prefixes: ' + load)
            if previous.exists() and not incremental:
                fail('addition shadows existing provider: ' + load)
    if not incremental and referenced != set(additions):
        fail('addition lacks previous static Qt dependency: ' + ', '.join(sorted(set(additions) - referenced)))

def check(inputs, script, view, profile, prefix, deployment, work, native_prefix, otool, incremental="0"):
    if incremental not in ("0", "1"):
        fail("invalid incremental reconfigure selection")
    incremental = incremental == "1"
    lines = Path(inputs).read_text().splitlines()
    pattern = re.compile(r'^([0-9a-f]{64})  ((?:.*/)?probes/plasma-mobile/toolkit/cross/build-host-tools\.sh)$')
    starts = [(i, pattern.fullmatch(line)) for i, line in enumerate(lines) if pattern.fullmatch(line)]
    if not starts:
        fail('missing previous producer input')
    start, match = starts[-1]
    block = lines[start:]
    old_script = match.group(2)
    if not incremental and os.path.abspath(old_script) != os.path.abspath(script):
        fail('producer path changed')
    if not incremental and match.group(1) not in (PREDECESSOR, PREDECESSOR_CMAKE, digest(script)):
        fail('unsupported previous producer identity')
    def value(key):
        values = [line[len(key)+1:] for line in block if line.startswith(key + '=')]
        if len(values) != 1:
            fail('missing or ambiguous previous ' + key)
        return values[0]
    if value('profile') != profile or value('host_package_prefix') != prefix or value('host_deployment_target') != deployment:
        fail('previous host configuration differs')
    old_view = value('host_runtime_view')
    old_identity = value('host_runtime_view_identity')
    if not old_view:
        if view or old_identity != 'none':
            fail('cannot add a runtime view to a build without one')
        return match.group(1), start + 1
    if not view or not Path(view).is_dir():
        fail('previous runtime view is missing')
    prefix_path = old_view + '/'
    records = []
    for line in block:
        m = re.fullmatch(r'([0-9a-f]{64})  (/.+)', line)
        if m and m.group(2).startswith(prefix_path):
            name = m.group(2)[len(prefix_path):]
            if not name or '/' in name or name in ('.', '..'):
                fail('invalid runtime entry')
            records.append((name, m.group(1), line))
    if not records or len({name for name, _, _ in records}) != len(records):
        fail('missing or duplicate previous runtime entry')
    records.sort(key=lambda x: x[0])
    recorded = ''.join(line + '\n' for _, _, line in records).encode()
    if hashlib.sha256(recorded).hexdigest() != old_identity:
        fail('previous runtime identity differs from its entries')
    unchanged = set()
    for name, expected, _ in records:
        entry = Path(view) / name
        if not entry.is_file():
            fail('previous runtime entry changed: ' + name)
        if digest(entry) != expected:
            if not incremental:
                fail('previous runtime entry changed: ' + name)
        else:
            unchanged.add(name)
    check_additions(view, unchanged, work, prefix, native_prefix, otool, incremental)
    return match.group(1), start + 1

if __name__ == '__main__':
    try:
        if len(sys.argv) not in (10, 11):
            fail('usage: host-resume-inputs.py INPUTS SCRIPT VIEW PROFILE PREFIX DEPLOYMENT WORK NATIVE_PREFIX OTOOL')
        print(*check(*sys.argv[1:]))
    except (OSError, ValueError) as error:
        print('Qt host resume: ' + str(error), file=sys.stderr)
        sys.exit(1)
