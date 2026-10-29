# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Bind an explicitly selected SDK Darwin C++ runtime and its loader view."""
import json
import os
import re
from pathlib import Path


def select(binding_path, view_path):
    from emberbsd_sdk import compiler_bindings
    binding = Path(binding_path).resolve(strict=True)
    view = Path(view_path).resolve(strict=True)
    if not binding.is_file() or not view.is_dir() or ':' in str(view):
        raise ValueError('native binding and runtime view must exist')
    record = json.loads(binding.read_text())
    if record.get('version') != 4:
        raise ValueError('a native C++ ABI identity binding version 4 is required')
    context = compiler_bindings.validate_native_compiler_context(record)
    # compiler_argv also validates the selected ABI identity and header/library paths.
    compiler_bindings.compiler_argv(record, 'cxx', ['-c', '/dev/null', '-o', '/dev/null'])
    runtime = record['native_cxx_runtime']
    identity = runtime['abi_identity']
    library = (Path(runtime['library_dir']) / identity['linker_target']).resolve(strict=True)
    selected = view / identity['linker_target']
    if not selected.is_symlink() or selected.resolve(strict=True) != library:
        raise ValueError('runtime view does not select the declared C++ library')
    # The view is deliberately finite: no DYLD injection of unselected libraries.
    cow_prefix = library.parents[2]
    allowed = {identity['linker_target']: library}
    for name in ('libLLVM.23.1.dylib', 'libclang-cpp.23.1.dylib'):
        path = view / name
        if path.exists():
            allowed[name] = (cow_prefix / 'lib' / name).resolve(strict=True)
    entries = list(view.iterdir())
    if {item.name for item in entries} != set(allowed):
        raise ValueError('runtime view contains an undeclared library')
    for item in entries:
        if not item.is_symlink() or item.resolve(strict=True) != allowed[item.name]:
            raise ValueError('runtime view maps outside the selected COW libraries')
    return {'record': record, 'binding': str(binding), 'view': str(view),
            'include_dir': runtime['include_dir'], 'library': str(library),
            'linker_target': identity['linker_target'],
            'abi_view': runtime['platform_cxxabi']['view'],
            'namespace': identity['namespace'], 'context': context,
            'cow_prefix': str(cow_prefix)}


def argv(selection, arguments):
    from emberbsd_sdk import compiler_bindings
    return compiler_bindings.compiler_argv(selection['record'], 'cxx', arguments)


def declared_system_libraries(selection, flags, capture):
    """Resolve only native llvm-config's declared non-system link inputs."""
    prefix = Path(selection['cow_prefix'])
    otool = prefix / 'bin/otool'
    if not os.access(otool, os.X_OK):
        raise ValueError('selected native otool is unavailable')
    cxx_lines = capture(str(otool), '-D', selection['library']).splitlines()
    if len(cxx_lines) != 2 or not cxx_lines[1].startswith('/'):
        raise ValueError('invalid declared C++ install name')
    cxx_name = Path(cxx_lines[1].strip())
    if cxx_name.name != selection['linker_target'] or cxx_name.parent.name != 'libc++':
        raise ValueError('C++ install name differs from binding identity')
    canonical_lib = cxx_name.parent.parent
    names = [str(cxx_name)]
    files = [selection['library']]
    for flag in flags:
        if flag == '-lm':
            continue
        if not re.fullmatch(r'-l[A-Za-z0-9_+.-]+', flag) or flag.startswith('-lLLVM'):
            raise ValueError('unsupported native system library: ' + flag)
        library = (prefix / 'lib' / ('lib' + flag[2:] + '.dylib')).resolve(strict=True)
        if not library.is_relative_to(prefix.resolve(strict=True)):
            raise ValueError('native library escapes selected prefix')
        lines = capture(str(otool), '-D', str(library)).splitlines()
        if len(lines) != 2 or not lines[1].startswith('/'):
            raise ValueError('invalid native library install name')
        install_name = Path(lines[1].strip())
        installed_alias = prefix / 'lib' / install_name.name
        if (install_name.parent != canonical_lib or not installed_alias.exists() or
                installed_alias.resolve(strict=True) != library):
            raise ValueError('native library install name differs from selected prefix')
        files.append(str(library))
        names.append(str(install_name))
    return files, names
