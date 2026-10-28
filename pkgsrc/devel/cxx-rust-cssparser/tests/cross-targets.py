#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise actual make target selection without building or running targets."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('bmake', 'host-cc', 'host-cxx', 'host-ar'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
variables = ('PKG_FAIL_REASON', 'RUST_TARGET', '_EMBER_CSS_CC', '_EMBER_CSS_CXX', '_EMBER_CSS_GNU_TRIPLET', 'TOOL_DEPENDS')
with tempfile.TemporaryDirectory(prefix='ember-css-targets-') as tmp:
    work = Path(tmp).resolve()
    fixture = work / 'fixture.mk'
    fixture.write_text(f'''USE_CROSS_COMPILE?=yes
CROSS_OPSYS=NetBSD
CROSS_OS_VERSION=11.0
CROSS_MACHINE_ARCH?=aarch64
MACHINE_ARCH?=${{CROSS_MACHINE_ARCH}}
MACHINE_GNU_PLATFORM?=aarch64--netbsd
WRKDIR={work}/work
WRAPPER_BINDIR={work}/wrappers
EMBERBSD_CROSS_HOST_PREFIX={work}/host
EMBERBSD_CROSS_BUILD_CC={a.host_cc}
EMBERBSD_CROSS_BUILD_CXX={a.host_cxx}
EMBERBSD_CROSS_BUILD_AR={a.host_ar}
AR=/absolute/cross-ar
FILESDIR={root}
.include "{root}/cross.mk"
show:
.for key in {' '.join(variables)}
\t@printf '%s\\n' ${{${{key}}:Q}}
.endfor
''')
    def query(*overrides):
        result = subprocess.run([str(a.bmake), '-r', '-m', '/', '-f', str(fixture), 'show', *overrides],
                                check=True, text=True, stdout=subprocess.PIPE)
        values = result.stdout.splitlines()
        if len(values) != len(variables):
            raise ValueError(result.stdout)
        return dict(zip(variables, values))
    arm = query(); assert not arm['PKG_FAIL_REASON'] and arm['RUST_TARGET'] == 'aarch64-unknown-netbsd'
    assert 'rust-std-aarch64-netbsd-1.99.1' in arm['TOOL_DEPENDS']
    amd = query('CROSS_MACHINE_ARCH=x86_64', 'MACHINE_ARCH=x86_64', 'MACHINE_GNU_PLATFORM=x86_64--netbsd')
    assert not amd['PKG_FAIL_REASON'] and amd['RUST_TARGET'] == 'x86_64-unknown-netbsd'
    assert amd['_EMBER_CSS_CC'] == str(work / 'wrappers/cc') and amd['_EMBER_CSS_CXX'] == str(work / 'wrappers/c++')
    assert amd['_EMBER_CSS_GNU_TRIPLET'] == 'x86_64--netbsd' and 'rust-std-x86_64-netbsd-1.99.1' in amd['TOOL_DEPENDS']
    assert query('CROSS_MACHINE_ARCH=riscv64')['PKG_FAIL_REASON']
    assert query('CROSS_MACHINE_ARCH=x86_64')['PKG_FAIL_REASON']
    assert query('RUST_TARGET=x86_64-unknown-netbsd')['PKG_FAIL_REASON']
    native = query('USE_CROSS_COMPILE=no'); assert not native['RUST_TARGET'] and not native['TOOL_DEPENDS']
print('PASS: selected host tools, both cross targets and mixed-target refusal')
