#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Explicit target selection; compiler fixtures.
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shlex
import shutil
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk, args = load_sdk()
if len(args) != 2:
    sys.exit('Use BMAKE NATIVE_INPUTS_MK; the include must bind a selected Ports toolset')
bmake = Path(args[0]).resolve(strict=True)
native_inputs = Path(args[1]).resolve(strict=True)
if not Path(args[0]).is_absolute() or not Path(args[1]).is_absolute():
    sys.exit('Use absolute BMAKE and NATIVE_INPUTS_MK paths')
root = Path(__file__).resolve().parents[3]


def prepare_profile(source, destination):
    destination.mkdir()
    cross = source / 'profiles/common-build-tools/cross'
    for name in ('mk.conf', 'native-tools.mk', 'prepare-native-tools.py', 'fortran.mk',
                 'sort-c.sh', 'gcc16-external-runtime.sh'):
        shutil.copy2(cross / name, destination / name)
    shutil.copy2(source / 'pkgsrc/defaults.mk.conf',
                 destination / 'EMBERBSD-DEFAULTS-MK.CONF')
    loader = destination / 'lang/llvm/files/sdk_source.py'
    loader.parent.mkdir(parents=True)
    shutil.copy2(source / 'pkgsrc/lang/llvm/files/sdk_source.py', loader)
    return destination / 'mk.conf'


with tempfile.TemporaryDirectory(prefix='ember-cross-targets-') as temporary:
    work = Path(temporary)
    cross_profile = prepare_profile(root, work / 'profile')
    tools = 'gcc g++ cpp gcc-ar gcc-nm gcc-ranlib ar as elfedit ld nm objcopy objdump ranlib readelf size strings strip'.split()
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
        result = subprocess.run([sys.executable, '-B', str(root / 'profiles/common-build-tools/cross/prepare-tools.py'), '--sdk-source', sdk, '--compiler-family', 'gcc', '--target', target, str(work / 'compiler'), str(work / 'os'), str(work / ('tools-' + target))], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert (work / ('tools-' + target) / 'bin' / (triple + '-gcc')).is_symlink()
    (work / 'Makefile').write_text(f'BSD_PKG_MK=yes\n.include "{native_inputs}"\nPKGPATH=devel/ember-target-fixture\nEMBERBSD_CROSS_COMPILER_FAMILY=gcc\nEMBERBSD_CROSS_TOOLS={work}/compiler\nEMBERBSD_CROSS_SYSROOT={work}/sysroot\nEMBERBSD_CROSS_HOST_PREFIX={work}/os\n.include "{cross_profile}"\n')

    def read(*arguments):
        result = subprocess.run([str(bmake), '-f', str(work / 'Makefile'), *arguments], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout.strip()

    assert Path(read('-v', 'EMBERBSD_NATIVE_BMAKE')).resolve(strict=True) == bmake
    assert Path(read('-v', 'EMBERBSD_CROSS_BUILD_PYTHON')).resolve(strict=True) == Path(sys.executable).resolve(strict=True)

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
    # The compiler provider imports its compiler. The runtime provider builds
    # a layered compiler with the development profile's option selection.
    compiler = ['EMBERBSD_CROSS_TARGET=amd64', 'PKGPATH=lang/gcc16']
    assert 'Import the repaired target GCC16' in read(*compiler, '-v', 'PKG_FAIL_REASON')
    assert not read(*compiler, '-v', 'GCC16_CROSS_TARGET_FLAGS')
    layered = compiler + ['EMBERBSD_GCC16_RUNTIME_PROVIDER=runtime']
    assert not read(*layered, '-v', 'PKG_FAIL_REASON')
    deps = read(*layered, '-v', 'DEPENDS').split()
    assert 'gcc16-runtime>=16.2.0nb6:../../lang/gcc16-runtime' in deps and not [d for d in deps if d.startswith('gcc16>=')], deps
    profile = (root / 'profiles/development-toolchain/mk.conf').read_text().replace('\\\n', ' ')
    expected = next(line.split('=', 1)[1].split() for line in profile.splitlines() if line.startswith('PKG_OPTIONS.gcc16='))
    assert read(*layered, '-v', 'PKG_OPTIONS.gcc16').split() == expected
    crt = str(work / 'sysroot/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0') + '/'
    assert read(*layered, '-v', 'GCC16_CROSS_TARGET_FLAGS') == '-B' + crt
    assert read(*layered, '-v', 'LIBTOOLIZE_PLIST') == 'no' and read(*compiler, '-v', 'LIBTOOLIZE_PLIST') != 'no'
    assert read(*layered, '-v', '_EMBER_GCC16_LAYER') == str(cross_profile.parent / 'gcc16-external-runtime.sh')
    assert 'emberbsd-gcc16-external-runtime' not in read('EMBERBSD_CROSS_TARGET=amd64', 'EMBERBSD_GCC16_RUNTIME_PROVIDER=runtime', '-V', '${.ALLTARGETS}').split()
    assert 'emberbsd-gcc16-external-runtime' in read(*layered, '-V', '${.ALLTARGETS}').split()
    # GCC builds its build-host libiberty with host archive tools.
    for role in ('AR', 'RANLIB'):
        assert read('-v', 'NATIVE_' + role) == read('-v', 'EMBERBSD_CROSS_BUILD_' + role)
    for language, flags in (('CC', 'CFLAGS'), ('CXX', 'CXXFLAGS')):
        expected = [read('-v', 'EMBERBSD_CROSS_BUILD_' + language)]
        expected += shlex.split(read('-v', 'NATIVE_CPPFLAGS'))
        expected += shlex.split(read('-v', 'NATIVE_' + flags))
        expected += shlex.split(read('-v', 'NATIVE_LDFLAGS'))
        assert shlex.split(read('-v', 'NATIVE_' + language)) == expected
    refused = subprocess.run([str(bmake), '-f', str(work / 'Makefile'),
                              'EMBERBSD_CROSS_BUILD_AR=ar', '-v', 'PKG_FAIL_REASON'],
                             capture_output=True, text=True)
    assert refused.returncode != 0 and 'EMBERBSD_CROSS_BUILD_AR differs from the selected Ports tool' in refused.stderr
    # bmake command-line assignments take precedence over profile assignments.
    # Every alias used by configure must reject that bypass too.
    for role in ('CC', 'CXX', 'CPP', 'AS', 'LD', 'AR', 'RANLIB', 'NM', 'STRIP'):
        reason = read('NATIVE_' + role + '=/bin/false', '-v', 'PKG_FAIL_REASON')
        expected = ('Cross generators require the selected native build compilers'
                    if role in ('CC', 'CXX', 'CPP') else
                    'NATIVE_' + role + ' differs from the selected Ports tool')
        assert expected in reason, (role, reason)
    for variable, value in (
            ('_EMBER_SDK_AR', '/usr/bin/ar'),
            ('_EMBER_NATIVE_CC_COMMAND', '/usr/bin/cc'),
            ('_EMBER_NATIVE_TOOLSET_CHECK', 'VERIFIED')):
        refused = subprocess.run([str(bmake), '-f', str(work / 'Makefile'),
                                  variable + '=' + value, '-v', 'PKG_FAIL_REASON'],
                                 capture_output=True, text=True)
        assert refused.returncode != 0 and 'Do not override reserved SDK native selection variables' in refused.stderr
    for prefix in ('NATIVE_', 'HOST_'):
        for flags in ('CPPFLAGS', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS'):
            variable = prefix + flags
            refused = subprocess.run([str(bmake), '-f', str(work / 'Makefile'),
                                      variable + '=-I/target-only', '-v', 'PKG_FAIL_REASON'],
                                     capture_output=True, text=True)
            assert refused.returncode != 0 and variable + ' differs from the selected native ABI flags' in refused.stderr
    (work / 'sysroot/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/crtbeginS.o').unlink()
    assert 'GCC16 CRT and runtime' in read('EMBERBSD_CROSS_TARGET=amd64', '-v', 'PKG_FAIL_REASON')
print('PASS: explicit ARM/amd64 target fixtures, unsupported and mixed target refusals; no compiler build')
