# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; static GCC16 support for the first source-built OS seed.
"""Build static support without target libc. This is not the POSIX runtime."""

from pathlib import Path
import os
import re
import shlex

from emberbsd_sdk import elf, inventory, jsonio, paths
from host import VERSION, build_path, capture, environment, logged, process, require, sha, target_metadata, target_tools


def setting(path, name, value):
    paths.regular_file(path)
    values = re.findall(r'^' + re.escape(name) + r'\s*=\s*(\S+)\s*$', path.read_text(), re.M)
    return values == [value]


def headers(root, target):
    root = build_path(root)
    paths.real_directory(root)
    require(root.resolve(strict=True) == root, 'Bootstrap headers need a real sysroot path')
    source = os.environ.get('EMBERBSD_SYSROOT_SOURCE', '')
    require(re.fullmatch(r'[0-9a-f]{40}', source),
            'Set EMBERBSD_SYSROOT_SOURCE to the verified full EmberBSD source commit')
    provenance = os.environ.get('EMBERBSD_SYSROOT_PROVENANCE')
    if provenance:
        provenance = build_path(provenance)
        paths.regular_file(provenance)
        provenance = dict(path=str(provenance), sha256=sha(provenance))
    metadata = target_metadata(target)
    rows = inventory.snapshot_tree(root, machine=metadata['machine'])
    require(not any('elf' in row or 'archive' in row for row in rows.values()),
            'Bootstrap header sysroot must not contain compiled target libraries or objects')
    for name in ('stddef.h', 'stdio.h', 'sys/types.h', 'sys/cdefs.h', 'sys/common_ansi.h', 'machine/ansi.h'):
        inventory.required_file(root, 'usr/include/' + name)
    machine = Path(inventory.required_file(root, 'usr/include/machine/ansi.h'))
    require(machine == root / 'usr/include' / metadata['header_directory'] / 'ansi.h',
            'Bootstrap headers do not select the requested machine ABI')
    for relative in metadata['required_headers']:
        inventory.required_file(root, 'usr/include/' + relative)
    return dict(format='emberbsd-bootstrap-header-inputs', version=1, root=str(root),
                target=target, source_commit=source, provenance=provenance or None,
                source_qualification='caller-verified-EmberBSD-commit', inventory=rows)


def build(work, prefix, target, make, count, env):
    metadata = target_metadata(target)
    triplet, machine = metadata['triplet'], metadata['machine']
    frontend = work / 'build/gcc/Makefile'
    require(setting(frontend, 'inhibit_libc', 'true'),
            'Static bootstrap requires inhibit_libc=true in the kernel frontend')
    inputs = work / 'inputs.txt'
    receipt = inputs.read_text().splitlines()
    require(receipt.count('mode=kernel') == 1 and receipt.count('bootstrap_libgcc=yes') == 1,
            'Missing explicit static bootstrap selection')
    header_file = work / 'bootstrap-headers.json'
    header_inputs = jsonio.read_json(header_file)
    header_hash = sha(header_file)
    header_root = Path(header_inputs['root'])
    require(headers(header_root, target) == header_inputs, 'Bootstrap headers changed before static support build')
    compiler = prefix / 'bin' / (triplet + '-gcc')
    version = process.capture([str(compiler), '-v'], env=environment(env))
    banner = (version.stdout + version.stderr).decode('utf-8')
    require('Thread model: single' in banner.splitlines(),
            'Static bootstrap requires a single-thread kernel compiler')
    configured = re.findall(r'^Configured with: (.+)$', banner, re.M)
    require(len(configured) == 1 and {'--without-headers', '--disable-shared', '--disable-threads'}.issubset(shlex.split(configured[0])),
            'Static bootstrap requires --without-headers and the nonshared kernel configuration')
    require('--with-sysroot=' + str(header_root) in shlex.split(configured[0]) and
            capture([compiler, '-print-sysroot']).strip() == str(header_root),
            'Static bootstrap compiler does not select the recorded header sysroot')
    record = work / 'bootstrap-libgcc.json'
    require(paths.entry(record) is None, 'Static bootstrap receipt already exists')
    target_env = dict(env, **target_tools(prefix, target))
    logged([make, '-j' + count, 'all-target-libgcc'], work / 'bootstrap-libgcc-build.log',
           target_env, work / 'build', quarantine=work)
    library = work / 'build' / triplet / 'libgcc/Makefile'
    require(setting(library, 'enable_shared', 'no'), 'Static bootstrap enabled shared libgcc')
    logged([make, 'install-target-libgcc'], work / 'bootstrap-libgcc-install.log',
           target_env, work / 'build', quarantine=work)
    require(not list(prefix.rglob('libgcc_s.so*')), 'Shared libgcc is not a static bootstrap output')
    require(paths.entry(prefix / 'include/c++') is None, 'Static bootstrap contains a C++ runtime')
    directory = prefix / 'lib/gcc' / triplet / VERSION
    names = ['libgcc.a', 'crtbegin.o', 'crtbeginS.o', 'crtend.o', 'crtendS.o']
    names += [name for name in ('libgcov.a', 'libgcc_eh.a', 'crtbeginT.o', 'crtfastmath.o')
              if paths.entry(directory / name) is not None]
    files, archive = {}, None
    for name in names:
        installed = directory / name
        paths.regular_file(installed)
        reported = capture([compiler, '-print-file-name=' + name]).strip()
        require(Path(reported).is_absolute() and Path(reported).is_file() and
                Path(reported).resolve(strict=True) == installed.resolve(strict=True),
                'Compiler does not select the installed bootstrap file: ' + name)
        if name.endswith('.a'):
            inspected = elf.read_archive(installed, machine)
            require(inspected['elf_members'] > 0, 'Static bootstrap archive is empty: ' + name)
            if name == 'libgcc.a':
                archive = inspected
        else:
            require(elf.read_elf_header(installed, machine=machine, required_type=1) is not None,
                    'Bootstrap CRT is not a target relocatable object: ' + name)
        files[str(installed.relative_to(prefix))] = sha(installed)
    require(headers(header_root, target) == header_inputs, 'Bootstrap headers changed during static support build')
    require(sha(header_file) == header_hash, 'Bootstrap header input record changed during static support build')
    jsonio.write_json(record, dict(format='emberbsd-bootstrap-libgcc', version=1,
        scope='static-libgcc-bootstrap-only', target=target, triplet=triplet,
        gcc_version=VERSION, threads='single', shared=False,
        qualification='installed-target-objects', execution_acceptance='not-run',
        inputs_sha256=sha(inputs), bootstrap_headers_sha256=header_hash,
        frontend_makefile_sha256=sha(frontend),
        libgcc_makefile_sha256=sha(library), archive=archive, files=files), exclusive=True)
