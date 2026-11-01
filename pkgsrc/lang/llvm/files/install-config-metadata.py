#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Install target llvm-config metadata without build paths.
"""Install the small target-generated tables consumed by the host llvm-config."""
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys


def fail(message):
    print('install-config-metadata: ' + message, file=sys.stderr)
    raise SystemExit(1)


def definitions(text):
    values = {}
    for line in text.splitlines():
        match = re.fullmatch(r'#define ([A-Z][A-Z0-9_]*) (.+)', line)
        if match:
            values[match[1]] = match[2]
    return values


def macro(name, value):
    return '#define ' + name + ' ' + json.dumps(value)


def normalize_path(value, roots, sysroot):
    path = Path(os.path.normpath(value)).resolve()
    for root in roots:
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if relative.parts and relative.parts[0] == 'include':
            return str(Path('/usr/pkg/include').joinpath(*relative.parts[1:]))
        if relative.parts and relative.parts[0] == 'lib':
            return str(Path('/usr/pkg/lib').joinpath(*relative.parts[1:]))
        fail('llvm-config flags reference an uninstalled source/build path: ' + value)
    if sysroot:
        try:
            relative = path.relative_to(sysroot)
            return '/' + str(relative)
        except ValueError:
            pass
    return value


def normalize_flags(value, roots, sysroot):
    tokens = shlex.split(value)
    result = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        prefix = next((p for p in ('-isystem', '-I', '-L') if token.startswith(p) and token != p), '')
        if token in ('-isystem', '-I', '-L') and index + 1 < len(tokens):
            prefix = token
            index += 1
            result.extend((prefix, normalize_path(tokens[index], roots, sysroot)))
        elif prefix:
            result.append(prefix + normalize_path(token[len(prefix):], roots, sysroot))
        elif token.startswith('-Wl,'):
            parts = token[4:].split(',')
            for part_index, part in enumerate(parts):
                if part.startswith('-R/'):
                    parts[part_index] = '-R' + normalize_path(part[2:], roots, sysroot)
                elif part.startswith('-rpath='):
                    parts[part_index] = '-rpath=' + normalize_path(part[len('-rpath='):], roots, sysroot)
            result.append('-Wl,' + ','.join(parts))
        elif token.startswith('-R/'):
            result.append('-R' + normalize_path(token[2:], roots, sysroot))
        else:
            result.append(token)
        index += 1
    return shlex.join(result)


def main(argv):
    if len(argv) != 5:
        fail('usage: install-config-metadata.py BUILD_TOOLS DEST WRKSRC BUILD_DIR CMAKE_CACHE')
    tools, destination, source_root, build_root, cmake_cache = map(Path, argv)
    source_root = source_root.resolve()
    build_root = build_root.resolve()
    cache = cmake_cache.read_text()
    match = re.search(r'^CMAKE_SYSROOT(?::[^=]+)?=(.*)$', cache, re.M)
    sysroot = Path(match[1]).resolve() if match and match[1] else None
    roots = (build_root, source_root)
    names = ('BuildVariables.inc', 'LibraryDependencies.inc', 'ExtensionDependencies.inc')
    if any(not (tools / name).is_file() for name in names):
        fail('configured llvm-config metadata is missing')
    upstream_source = source_root / 'tools/llvm-config/llvm-config.cpp'
    if not upstream_source.is_file():
        fail('patched upstream llvm-config.cpp is missing from WRKSRC')
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        source = tools / name
        text = source.read_text()
        if name == 'BuildVariables.inc':
            values = definitions(text)
            # These sentinels force upstream's installed-prefix layout branch.
            text = re.sub(r'^#define LLVM_SRC_ROOT .+$', macro('LLVM_SRC_ROOT', '/__emberbsd_not_installed_source__'), text, flags=re.M)
            text = re.sub(r'^#define LLVM_OBJ_ROOT .+$', macro('LLVM_OBJ_ROOT', '/__emberbsd_not_installed_build__'), text, flags=re.M)
            for key in ('LLVM_CPPFLAGS', 'LLVM_CFLAGS', 'LLVM_CXXFLAGS', 'LLVM_LDFLAGS'):
                value = normalize_flags(json.loads(values[key]), roots, sysroot)
                text = re.sub(r'^#define ' + key + r' .+$', macro(key, value), text, flags=re.M)
            if any(str(root) in text for root in (*roots, *((sysroot,) if sysroot else ()))):
                fail('installed BuildVariables.inc still contains a private input path')
        (destination / name).write_text(text)
    shutil.copyfile(upstream_source, destination / 'llvm-config.cpp')
    print(destination)


if __name__ == '__main__':
    main(sys.argv[1:])
