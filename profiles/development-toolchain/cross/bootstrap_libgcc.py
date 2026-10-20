# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; static GCC16 support for the first source-built OS seed.
"""Build headerless static support. This is not the POSIX runtime provider."""

from pathlib import Path
import re
import shlex

from emberbsd_sdk import elf, jsonio, paths
from host import TARGETS, VERSION, capture, environment, logged, process, require, sha, target_tools


def setting(path, name, value):
    paths.regular_file(path)
    values = re.findall(r'^' + re.escape(name) + r'\s*=\s*(\S+)\s*$', path.read_text(), re.M)
    return values == [value]


def build(work, prefix, target, make, count, env):
    triplet, machine, _, _ = TARGETS[target]
    frontend = work / 'build/gcc/Makefile'
    require(setting(frontend, 'inhibit_libc', 'true'),
            'Static bootstrap requires the headerless kernel frontend')
    inputs = work / 'inputs.txt'
    receipt = inputs.read_text().splitlines()
    require(receipt.count('mode=kernel') == 1 and receipt.count('bootstrap_libgcc=yes') == 1,
            'Missing explicit static bootstrap selection')
    compiler = prefix / 'bin' / (triplet + '-gcc')
    version = process.capture([str(compiler), '-v'], env=environment(env))
    banner = (version.stdout + version.stderr).decode('utf-8')
    require('Thread model: single' in banner.splitlines(),
            'Static bootstrap requires a single-thread kernel compiler')
    configured = re.findall(r'^Configured with: (.+)$', banner, re.M)
    require(len(configured) == 1 and {'--without-headers', '--disable-shared', '--disable-threads'}.issubset(shlex.split(configured[0])),
            'Static bootstrap requires the headerless, nonshared kernel configuration')
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
    jsonio.write_json(record, dict(format='emberbsd-bootstrap-libgcc', version=1,
        scope='static-libgcc-bootstrap-only', target=target, triplet=triplet,
        gcc_version=VERSION, threads='single', shared=False,
        qualification='installed-target-objects', execution_acceptance='not-run',
        inputs_sha256=sha(inputs), frontend_makefile_sha256=sha(frontend),
        libgcc_makefile_sha256=sha(library), archive=archive, files=files), exclusive=True)
