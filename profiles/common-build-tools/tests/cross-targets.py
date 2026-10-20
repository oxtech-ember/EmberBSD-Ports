#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Explicit target selection; compiler fixtures.
import os
from pathlib import Path
import subprocess
import sys
import tempfile
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk, args = load_sdk()
if len(args) != 1:
    sys.exit('Use BMAKE')
bmake = args[0]
root = Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory(prefix='ember-cross-targets-') as temporary:
    work = Path(temporary)
    tools = 'gcc g++ cpp gcc-ar gcc-nm gcc-ranlib ar as ld nm objcopy objdump ranlib readelf strip'.split()
    for p in ('compiler/bin', 'os/bin', 'sysroot/usr/pkg/gcc16/lib'):
        (work / p).mkdir(parents=True)
    for triple in ('aarch64--netbsd', 'x86_64--netbsd'):
        for name in tools:
            path = work / 'compiler/bin' / (triple + '-' + name)
            path.write_text(f'#!{sys.executable}\nimport sys\nif sys.argv[1] == "-dumpmachine": print({triple!r})\nelif sys.argv[1] == "-dumpfullversion": print("16.2.0")\n')
            path.chmod(0o755)
        install = work / 'os/bin' / (triple + '-install')
        install.write_text('#!' + sys.executable + '\n')
        install.chmod(0o755)
        crt = work / 'sysroot/usr/pkg/gcc16/lib/gcc' / triple / '16.2.0'
        crt.mkdir(parents=True)
        (crt / 'crtbeginS.o').write_text('fixture')
    (work / 'sysroot/usr/pkg/gcc16/lib/libstdc++.so.7').write_text('fixture')
    for target in ('aarch64', 'amd64'):
        triple = 'x86_64--netbsd' if target == 'amd64' else 'aarch64--netbsd'
        result = subprocess.run([sys.executable, '-B', str(root / 'profiles/common-build-tools/cross/prepare-tools.py'), '--sdk-source', sdk, '--target', target, str(work / 'compiler'), str(work / 'os'), str(work / ('tools-' + target))], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert (work / ('tools-' + target) / 'bin' / (triple + '-gcc')).is_symlink()
    (work / 'Makefile').write_text(f'BSD_PKG_MK=yes\nPKGPATH=devel/ember-target-fixture\nEMBERBSD_CROSS_TOOLS={work}/compiler\nEMBERBSD_CROSS_SYSROOT={work}/sysroot\nEMBERBSD_CROSS_HOST_PREFIX={work}/os\n.include "{root}/profiles/common-build-tools/cross/mk.conf"\n')

    def read(*arguments):
        result = subprocess.run([bmake, '-f', str(work / 'Makefile'), *arguments], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout.strip()

    assert read('-v', 'CROSS_MACHINE_ARCH') == 'aarch64'
    assert read('EMBERBSD_CROSS_TARGET=amd64', '-v', 'CROSS_MACHINE_ARCH') == 'x86_64'
    assert read('EMBERBSD_CROSS_TARGET=amd64', '-v', 'CC').endswith('/x86_64--netbsd-gcc')
    assert not read('EMBERBSD_CROSS_TARGET=amd64', '-v', 'PKG_FAIL_REASON')
    assert 'Unsupported cross target' in read('EMBERBSD_CROSS_TARGET=mips', '-v', 'PKG_FAIL_REASON')
    assert 'selected cross target' in read('EMBERBSD_CROSS_TARGET=amd64', 'CROSS_MACHINE_ARCH=aarch64', '-v', 'PKG_FAIL_REASON')
    # GNU ld resolves base DT_NEEDED entries of package libraries through rpath-link.
    for target in ('aarch64', 'amd64'):
        for language in ('cc', 'cxx'):
            append = read('EMBERBSD_CROSS_TARGET=' + target, '-v', 'CWRAPPERS_APPEND.' + language).split()
            assert '-Wl,-rpath-link,' + str(work / 'sysroot/usr/lib') in append, append
        assert '/usr/lib' not in read('EMBERBSD_CROSS_TARGET=' + target, '-v', 'LDFLAGS').replace('/usr/pkg/', '')
    # Stale non-TLS C++ headers fail; the TLS header passes.
    config = work / 'sysroot/usr/pkg/gcc16/include/c++/x86_64--netbsd/bits/c++config.h'
    config.parent.mkdir(parents=True)
    config.write_text('/* #undef _GLIBCXX_HAVE_TLS */\n')
    assert 'TLS runtime stage' in read('EMBERBSD_CROSS_TARGET=amd64', '-v', 'PKG_FAIL_REASON')
    config.write_text('#define _GLIBCXX_HAVE_TLS 1\n#define _GLIBCXX_HAVE_TLS 1\n')
    assert 'TLS runtime stage' in read('EMBERBSD_CROSS_TARGET=amd64', '-v', 'PKG_FAIL_REASON')
    config.write_text('#define _GLIBCXX_HAVE_TLS 1\n')
    assert not read('EMBERBSD_CROSS_TARGET=amd64', '-v', 'PKG_FAIL_REASON')
    deps = read('EMBERBSD_CROSS_TARGET=amd64', 'EMBERBSD_GCC16_RUNTIME_PROVIDER=runtime', '-v', 'DEPENDS')
    assert 'gcc16-runtime>=16.2.0nb5:../../lang/gcc16-runtime' in deps and 'gcc16>=' not in deps
    arguments = ['EMBERBSD_CROSS_TARGET=amd64', 'EMBERBSD_GCC16_RUNTIME_PROVIDER=runtime', 'PKGPATH=lang/gcc16-runtime']
    assert not read(*arguments, '-v', 'DEPENDS') and not read(*arguments, '-v', 'PKG_FAIL_REASON')
    assert 'requires the runtime provider' in read('PKGPATH=lang/gcc16-runtime', '-v', 'PKG_FAIL_REASON')
    assert 'not a provider' in read('PKGPATH=lang/gcc16-libs', '-v', 'PKG_FAIL_REASON')
    assert 'single GCC16 runtime provider' in read('EMBERBSD_GCC16_RUNTIME_PROVIDER=invalid', '-v', 'PKG_FAIL_REASON')
    (work / 'sysroot/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/crtbeginS.o').unlink()
    assert 'GCC16 CRT and runtime' in read('EMBERBSD_CROSS_TARGET=amd64', '-v', 'PKG_FAIL_REASON')
print('PASS: explicit ARM/amd64 target fixtures, unsupported and mixed target refusals; no compiler build')
