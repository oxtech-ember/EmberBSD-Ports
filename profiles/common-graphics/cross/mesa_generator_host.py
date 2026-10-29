# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Shared Mesa native-host policy.
"""Select supported native Mesa hosts and their inspection tools."""
from pathlib import Path
import os
import platform
import struct


def require(condition, message):
    if not condition:
        raise ValueError(message)


def host_policy(host_os=None, host_cpu=None, compiler_family='clang'):
    host_os = platform.system() if host_os is None else host_os
    host_cpu = platform.machine() if host_cpu is None else host_cpu
    compiler_families = {
        ('Darwin', 'arm64'): {'clang', 'gcc'},
        ('Linux', 'x86_64'): {'clang'},
    }
    supported = compiler_families.get((host_os, host_cpu), set())
    require(compiler_family in supported,
            'Unsupported native Mesa host: ' + str(host_os) + '/' + str(host_cpu) + '/' + str(compiler_family))
    return dict(os=host_os, cpu=host_cpu, compiler_family=compiler_family,
                inspector='otool' if host_os == 'Darwin' else 'llvm-readelf',
                loader='dyld' if host_os == 'Darwin' else '/usr/bin/ldd')


def required_roles(base_roles, policy):
    roles = list(base_roles)
    if policy['os'] == 'Darwin':
        roles.append('otool')
    return tuple(dict.fromkeys(roles))


def require_prefix_tool(path, prefix, role):
    prefix = Path(prefix).resolve(strict=True)
    try:
        selected = Path(path).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValueError('Selected native ' + role + ' is unavailable') from error
    require(selected.is_file() and os.access(selected, os.X_OK),
            'Selected native ' + role + ' is not executable')
    require(selected.is_relative_to(prefix) and selected != prefix,
            'Selected native ' + role + ' escapes selected native prefix')
    return selected


def inspection_tool(native, policy):
    prefix = Path(native.bundle_root).resolve(strict=True)
    path = (Path(native.tool('otool')) if policy['os'] == 'Darwin'
            else prefix / 'bin/llvm-readelf')
    require_prefix_tool(path, prefix, policy['inspector'])
    # Keep the selected alias as argv[0]: llvm-readelf may resolve to
    # llvm-readobj, whose output format differs when invoked by that name.
    return path


def loader_key(interpreter_request):
    """Return the PT_INTERP basename used as the ldd map key."""
    return Path(interpreter_request).name


def is_system_library_path(path):
    value = str(path)
    return any(value == root or value.startswith(root + '/')
               for root in ('/lib', '/lib64', '/usr/lib', '/usr/lib64'))


def loader_tool(policy):
    if policy['os'] == 'Darwin':
        return None
    path = Path(policy['loader'])
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValueError('Explicit native ldd is unavailable') from error
    require(resolved == Path('/usr/bin/ldd') and resolved.is_file() and os.access(resolved, os.X_OK),
            'Explicit native ldd is unavailable')
    return resolved


def validate_binary(path, policy):
    path = Path(path)
    with path.open('rb') as stream:
        header = stream.read(20)
    if policy['os'] == 'Darwin':
        require(header[:8] == struct.pack('<II', 0xfeedfacf, 0x0100000c),
                'Expected native ARM64 Mach-O')
        return 'Mach-O-arm64'
    require(len(header) >= 20 and header[:4] == b'\x7fELF' and
            header[4] == 2 and header[5] == 1 and header[6] == 1,
            'Expected native ELF64 little-endian image')
    require(struct.unpack_from('<H', header, 16)[0] in (2, 3),
            'Expected native ELF executable or shared object')
    require(struct.unpack_from('<H', header, 18)[0] == 62,
            'wrong native ELF architecture: expected x86_64')
    return 'ELF64-x86_64'
