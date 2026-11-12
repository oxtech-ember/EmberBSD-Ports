#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise the actual Fortran policy with bmake metadata and build goals."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--policy', type=Path, required=True)
p.add_argument('--version-include', type=Path, required=True)
p.add_argument('--metadata-include', type=Path, required=True)
a = p.parse_args()
assert a.bmake.is_absolute() and a.policy.is_absolute()
with tempfile.TemporaryDirectory(prefix='fortran-metadata-') as tmp:
    root = Path(tmp)
    buildlink = root / 'lang/flang-rt/buildlink3.mk'
    buildlink.parent.mkdir(parents=True)
    buildlink.write_text('DEPENDS+= flang-rt>=23:../../lang/flang-rt\n')
    (root / 'EMBERBSD-METADATA-GOALS.MK').write_bytes(a.metadata_include.read_bytes())
    policy = root / 'fortran.mk'
    policy.write_bytes(a.policy.read_bytes())
    (root / 'EMBERBSD-CROSS-FLANG-VERSION.MK').write_bytes(a.version_include.read_bytes())
    makefile = root / 'test.mk'
    makefile.write_text('''USE_LANGUAGES= c fortran
TOOLS_USE_CROSS_COMPILE= yes
USE_CROSS_COMPILE= yes
EMBERBSD_CROSS_COMPILER_FAMILY?= clang
PKGSRC_COMPILER?= clang
EMBERBSD_FLANG= /nonexistent/emberbsd-flang
PKGSRCDIR= %s
WRKDIR= %s
TOOLDIR= /nonexistent/toolchain
EMBERBSD_FORTRAN_CAPABILITY= /nonexistent/capability
EMBERBSD_FORTRAN_PYTHON= /nonexistent/python
EMBERBSD_FORTRAN_PORTS_SOURCE= /nonexistent/ports
EMBERBSD_SDK_SOURCE= /nonexistent/sdk
.include "%s"
show-var show-vars all:
\t@printf 'depends=%%s\\nbuild=%%s\\nfc=%%s\\nfail=%%s\\n' '${DEPENDS}' '${BUILD_DEPENDS}' '${FC}' '${PKG_FAIL_REASON}'
''' % (root, root, policy))
    def run(*goals, family='clang', compiler='clang', extra=()):
        return subprocess.run([str(a.bmake), '-r', '-f', str(makefile),
                               'EMBERBSD_CROSS_COMPILER_FAMILY='+family,
                               'PKGSRC_COMPILER='+compiler, *extra, *goals],
                              text=True, capture_output=True, timeout=10)
    for goal in ('show-var', 'show-vars'):
        result = run(goal)
        assert result.returncode == 0, (goal, result.stderr)
        assert 'flang-rt>=23:../../lang/flang-rt' in result.stdout, result.stdout
        assert 'fail=\n' in result.stdout, result.stdout
        assert not result.stderr, result.stderr
    native = run('show-vars', extra=('TOOLS_USE_CROSS_COMPILE=no', 'EMBERBSD_HOST_COMPILER_FAMILY=clang'))
    assert native.returncode == 0 and 'flang-rt>=23' in native.stdout and not native.stderr, (native.stdout, native.stderr)
    fake = run('show-vars', extra=('USE_CROSS_COMPILE=no',))
    assert fake.returncode == 0 and 'flang-rt>=23' not in fake.stdout and not fake.stderr, (fake.stdout, fake.stderr)
    for goals in (('all',), ('all', 'show-vars')):
        result = run(*goals)
        assert 'EMBERBSD_FLANG must select the build-host Ports flang driver' in result.stdout, result.stdout
    for goal in ('show-var', 'show-vars'):
        result = run(goal, family='gcc', compiler='gcc')
        assert result.returncode == 0, result.stderr
        assert 'gcc16-fortran-runtime-16.2.0nb1:../../lang/gcc16-fortran-runtime' in result.stdout, result.stdout
        assert 'gcc16-fortran-devel-16.2.0nb1:../../lang/gcc16-fortran-devel' in result.stdout, result.stdout
        assert '-gfortran' in result.stdout and 'fail=\n' in result.stdout, result.stdout
        assert '/nonexistent/python' not in result.stderr, result.stderr
    for goals in (('all',), ('all', 'show-vars')):
        result = run(*goals, family='gcc', compiler='gcc')
        assert 'no Fortran frontend' in result.stdout, result.stdout
        assert 'verified GCC16 Fortran runtime' in result.stdout, result.stdout
    invalid = run('show-vars', compiler='gcc')
    assert invalid.returncode != 0 and 'does not permit a package compiler substitution' in invalid.stderr
    invalid = run('show-vars', family='unknown')
    assert 'cross compiler family must be clang or gcc' in invalid.stdout, invalid.stdout
print('PASS: Fortran metadata dependency, build guards and compiler policy')
