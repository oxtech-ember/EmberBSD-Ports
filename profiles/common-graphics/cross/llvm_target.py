# SPDX-License-Identifier: BSD-2-Clause
# Validate generated LLVM target facts. Never supply query answers.
import json
import hashlib
from pathlib import Path
import re


def for_processor(processor):
    if processor == 'aarch64':
        return dict(processor=processor, backend='aarch64', machine=183)
    if processor == 'x86_64':
        return dict(processor=processor, backend='x86', machine=62)
    raise ValueError('target must be configured for NetBSD/aarch64 or NetBSD/x86_64')


def for_triple(triple):
    match = re.fullmatch(r'(aarch64|x86_64)-(?:unknown)?-netbsd(?:11(?:\.[0-9]+)*)?', str(triple))
    if not match:
        raise ValueError('unsupported NetBSD LLVM target triple')
    return for_processor(match[1])


def validate(cache, definitions, components):
    if cache.get('CMAKE_SYSTEM_NAME') != 'NetBSD':
        raise ValueError('target must be configured for NetBSD/aarch64 or NetBSD/x86_64')
    if 'CMAKE_SYSTEM_VERSION' in cache and not re.fullmatch(r'11(?:\.[0-9]+)*', cache['CMAKE_SYSTEM_VERSION']):
        raise ValueError('target metadata must use the NetBSD 11 ABI')
    spec = for_processor(cache.get('CMAKE_SYSTEM_PROCESSOR'))
    for key in ('LLVM_HOST_TRIPLE', 'LLVM_DEFAULT_TARGET_TRIPLE'):
        triple = json.loads(definitions[key])
        if triple != cache.get(key) or for_triple(triple) != spec:
            raise ValueError('inconsistent or non-NetBSD target ' + key)
    names = ['bitwriter', 'engine', 'mcdisassembler', 'mcjit', 'core', 'executionengine', 'scalaropts', 'transformutils', 'instcombine', 'native', 'orcjit', spec['backend']]
    for name in names:
        if not re.search(r'\{ "' + re.escape(name) + r'",', components):
            raise ValueError('missing target LLVM component: ' + name)
    if not re.search(r'\{ "native", nullptr, true, \{"' + re.escape(spec['backend']) + r'"\} \}', components):
        raise ValueError('native LLVM component disagrees with target processor')
    return spec


def validate_elf(path, spec):
    from emberbsd_sdk.elf import read_elf_header
    if read_elf_header(str(__import__('pathlib').Path(path).resolve(strict=True)), spec['machine'], 3) is None:
        raise ValueError('LLVM library is not shared little-endian ELF64 for the selected target')
    return True


def installed_headers(prefix, source=None, build=None, install_manifest=None):
    """Hash installed LLVM headers; optionally compare each with its build input."""
    include = (Path(prefix) / 'include').resolve(strict=True)
    result = hashlib.sha256()
    count = 0
    installed = set()
    for group in ('llvm', 'llvm-c'):
        root = include / group
        if not root.is_dir() or not root.resolve(strict=True).is_relative_to(include):
            raise ValueError('installed LLVM headers missing or outside prefix')
        for path in sorted(root.rglob('*')):
            if not path.is_file():
                continue
            if not path.resolve(strict=True).is_relative_to(include):
                raise ValueError('installed LLVM header escapes prefix')
            relative = path.relative_to(include)
            installed.add(str(relative))
            content = path.read_bytes()
            if source is not None:
                candidates = (Path(source) / 'include' / relative, Path(build) / 'include' / relative)
                if not any(candidate.is_file() and candidate.read_bytes() == content for candidate in candidates):
                    raise ValueError('installed LLVM header differs from build: ' + str(relative))
            result.update(str(relative).encode() + b'\0' + hashlib.sha256(content).digest())
            count += 1
    if not count:
        raise ValueError('installed LLVM headers are empty')
    if install_manifest is not None:
        lines = Path(install_manifest).read_text().splitlines()
        expected = {line.removeprefix('/usr/pkg/include/') for line in lines
                    if line.startswith(('/usr/pkg/include/llvm/', '/usr/pkg/include/llvm-c/'))}
        if not expected or installed != expected:
            raise ValueError('installed LLVM header set differs from CMake install manifest')
    return {'count': count, 'sha256': result.hexdigest()}
