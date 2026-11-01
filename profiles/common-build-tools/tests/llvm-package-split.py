#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual pkgsrc PLIST contracts; no LLVM build.
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
# Build-host programs use the native GCC16 drivers; there is no /usr/bin/cc default.
HOST_CC, HOST_CXX = (os.environ.get(n) or sys.exit(n + ' must name the native GCC16 driver') for n in ('HOST_CC', 'HOST_CXX'))
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk_source, args = load_sdk()
if len(args) != 4:
    sys.exit('Use PKGSRC HOST_PREFIX CROSS_TOOLS NEW_WORK')
source, host, tools = map(os.path.realpath, args[:3])
work = Path(args[3]).absolute()
work.mkdir()
# This fixture exercises pkgsrc metadata and install hooks only. Give its
# cross profile the one header required by bsd.prefs.mk without depending on
# a retained SDK sysroot or compiling target code.
sysroot = work / 'cross-root'
(sysroot / 'usr/include').mkdir(parents=True)
(sysroot / 'usr/include/stddef.h').write_text('/* package-split test fixture */\n')
tree = work / 'pkgsrc'
tree.mkdir()
profile = Path(__file__).resolve().parents[1]
for name in os.listdir(source):
    if name.startswith('.'):
        continue
    if name in ('lang', 'devel'):
        (tree / name).mkdir()
        for package in os.listdir(Path(source, name)):
            if name != 'lang' or package not in ('llvm', 'llvm-devel'):
                (tree / name / package).symlink_to(Path(source, name, package))
    else:
        (tree / name).symlink_to(Path(source, name))
for name in ('llvm', 'llvm-devel'):
    shutil.copytree(profile / '../../pkgsrc/lang' / name, tree / 'lang' / name)
host_makeconf = os.environ.get('HOST_MAKECONF', host + '/etc/mk.conf')
(work / 'mk.conf').write_text(f'.include "{host_makeconf}"\nWRKOBJDIR= {work}/objects\nPACKAGES= {work}/packages\nPKG_DBDIR= {work}/pkgdb\nCXXFLAGS= -O2\n')
bmake = os.environ.get('BMAKE', host + '/bin/bmake')
common = [bmake, 'MAKECONF=' + str(work / 'mk.conf'), 'AWK=' + host + '/bin/nawk', 'CAT=/bin/cat', 'SED=/usr/bin/sed', 'TEST=/bin/test', 'MKDIR=/bin/mkdir -p',
    'PERL5=' + host + '/bin/perl', 'FIND=/usr/bin/find', 'LN=/bin/ln', 'INSTALL_DATA_DIR=/usr/bin/install -d', 'X11_TYPE=modular',
    'TOOL_PYTHONBIN=' + sys.executable, 'EMBERBSD_SDK_SOURCE=' + sdk_source]
for tool in ('m4', 'yacc'):
    result = subprocess.run(['/usr/bin/xcrun', '--find', tool], capture_output=True, text=True)
    (work / ('xcrun-' + tool + '.log')).write_text(result.stdout + result.stderr)
    common.append('OSX_PATH_TO_' + tool.upper() + '=' + (result.stdout.strip() if result.returncode == 0 else ''))
result = subprocess.run([host + '/sbin/pkg_info', '-K', host + '/pkgdb', '-Q', 'PKG_OPTIONS', 'libxml2'], capture_output=True, text=True)
assert result.returncode == 0, 'installed native libxml2 option receipt required: ' + result.stderr
(work / 'native-libxml2-options.txt').write_text(result.stdout)
common.append('PKG_BUILD_OPTIONS.libxml2=' + result.stdout.strip())
cross = ['USE_CROSS_COMPILE=yes', 'CROSS_OPSYS=NetBSD', 'CROSS_OS_VERSION=11.0', 'CROSS_OPSYS_VERSION=110000', 'CROSS_MACHINE_ARCH=x86_64', 'CROSS_LOWER_OPSYS=netbsd',
    'CROSS_LOWER_OPSYS_VERSUFFIX=', 'CROSS_LOWER_OS_VARIANT=', 'CROSS_LOWER_VARIANT_VERSION=', 'CROSS_LOWER_VENDOR=', 'CROSS_OBJECT_FMT=ELF', 'CROSS_LOCALBASE=/usr/pkg',
    'CROSS_DESTDIR=' + str(sysroot), 'TOOLDIR=' + tools, 'CROSS_PKG_TOOLS_BIN=' + host + '/sbin', 'USE_PKGSRC_GCC_RUNTIME=no']


def run(label, package, *arguments):
    from emberbsd_sdk.process import OwnedProcessGroup
    command = [*common, '-C', str(tree / 'lang' / package), *map(str, arguments)]
    # Use a private process group. Timeouts must not leave recursive make alive.
    import time
    path = work / (label + '.log')
    with path.open('wb') as log:
        process = OwnedProcessGroup(command, cwd=str(work), env=dict(os.environ), stdout=log, stderr=log)
        process.start()
        deadline = time.monotonic() + 30
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if process.poll() is None:
            process.stop()
            raise AssertionError(label + ': bounded source query exceeded 30 seconds')
        code = process.poll()
    output = path.read_text()
    assert code == 0, label + ': ' + output
    return output


def plist(label, package, *mode):
    directory = work / label
    run(label, package, *mode, 'WRKDIR=' + str(directory), 'plist')
    return [s for s in (directory / '.PLIST_nokeywords').read_text().splitlines() if s]


runtime = plist('runtime', 'llvm', *cross)
assert sorted(runtime) == sorted(['include/llvm/Support/LICENSE.TXT', 'lib/libLLVM.so.23.1', 'lib/libLLVM-23.so', 'lib/libLLVM.so', 'lib/libLTO.so.23.1', 'lib/libLTO.so', 'lib/libRemarks.so.23.1', 'lib/libRemarks.so'])
assert run('runtime-name', 'llvm', *cross, '-v', 'PKGNAME').strip() == 'llvm-23.1.4nb3'
sdk = plist('devel', 'llvm-devel', *cross)
assert all(p in sdk for p in ('bin/llvm-config', 'bin/llvm-tblgen', 'include/llvm/IR/Module.h', 'lib/cmake/llvm/LLVMConfig.cmake', 'lib/libLLVMCore.a',
                     'lib/cmake/llvm/emberbsd/BuildVariables.inc',
                     'lib/cmake/llvm/emberbsd/LibraryDependencies.inc',
                     'lib/cmake/llvm/emberbsd/ExtensionDependencies.inc',
                     'lib/cmake/llvm/emberbsd/llvm-config.cpp'))
assert not set(runtime) & set(sdk)
owner, full_dir = tree / 'lang/llvm', work / 'full'
run('full', 'llvm', *cross, 'WRKDIR=' + str(full_dir), 'PLIST=' + str(full_dir / '.PLIST'), 'PLIST_SRC=' + str(owner / 'PLIST'), 'plist')
full = [s for s in (full_dir / '.PLIST_nokeywords').read_text().splitlines() if s]
assert sorted(runtime + sdk) == sorted(full)
helper = owner / 'files/select-package-stage.py'
assert helper.is_file()
native_args = ['USE_CROSS_COMPILE=no', 'PKGSRC_COMPILER=gcc', 'CC=' + HOST_CC, 'CXX=' + HOST_CXX, 'USE_NATIVE_GCC=yes', 'USE_PKGSRC_GCC=no']
native = plist('native', 'llvm', *native_args)
assert 'bin/llvm-config' in native and 'include/llvm/IR/Module.h' in native
reasons = run('devel-metadata', 'llvm-devel', *cross, '-v', 'PKG_FAIL_REASON', '-v', 'DEPENDS', '-v', 'CONFLICTS', '-v', 'DISTINFO_FILE', '-v', 'PATCHDIR').splitlines()
assert not reasons[0] and 'llvm-23.1.4nb3:' in reasons[1] and 'llvm<23.1.4nb3' in reasons[2] and \
       str(owner / 'distinfo') in reasons[3] and str(owner / 'patches') in reasons[4]
consumer = tree / 'devel/llvm-split-consumer'
consumer.mkdir()
(consumer / 'Makefile').write_text('DISTNAME= llvm-split-contract-1\nCATEGORIES= devel\nCOMMENT= LLVM buildlink source contract fixture\nLICENSE= 2-clause-bsd\nMETA_PACKAGE= yes\n.include "../../mk/bsd.prefs.mk"\n.include "../../lang/llvm/buildlink3.mk"\n.include "../../mk/bsd.pkg.mk"\n')
output = run('buildlink', '../devel/llvm-split-consumer', *cross, '-v', 'BUILD_DEPENDS', '-v', 'DEPENDS',
             '-v', 'BUILDLINK_API_DEPENDS.llvm-devel', '-v', 'BUILDLINK_ABI_DEPENDS.llvm-devel',
             '-v', 'BUILDLINK_API_DEPENDS.llvm', '-v', 'BUILDLINK_ABI_DEPENDS.llvm').splitlines()
assert 'llvm-devel>=23.1.4nb5:' in output[0] and 'llvm-devel' not in output[1] and \
       'llvm>=23.1.4nb2:' in output[1]
assert 'llvm-devel>=23.1.4nb5' in output[2] and 'llvm-devel>=23.1.4nb5' in output[3]
assert 'llvm>=23.1.4nb2' in output[4] and 'llvm>=23.1.4nb2' in output[5]
fields = run('runtime-dependencies', 'llvm', *cross, '-v', 'DEPENDS', '-v', 'BUILD_DEPENDS', '-v', 'TOOL_DEPENDS', '-v', 'CMAKE_CONFIGURE_ARGS', '-v', 'PKG_FAIL_REASON', '-v', 'USE_BUILTIN.zlib').splitlines()
assert not re.search(r'llvm-devel|llvm-lit|python[0-9]', fields[0])
assert all(name + '>=' in fields[0] for name in ('zstd', 'libxml2'))
assert 'zlib>=' in fields[0] or fields[5] == 'yes'
assert 'llvm-lit>=23.1.4nb1:' in fields[1] and re.search(r'python[0-9]+>=', fields[2])
assert 'llvm-23.1.4{,nb*}:../../lang/llvm' in fields[2] and 'llvm-devel' not in fields[2]
for flag in ('LLVM_BUILD_LLVM_DYLIB=ON', 'LLVM_LINK_LLVM_DYLIB=ON', 'LLVM_ENABLE_RTTI=ON', 'BUILD_SHARED_LIBS=OFF', 'LLVM_INSTALL_TOOLCHAIN_ONLY=OFF', 'LLVM_INCLUDE_TESTS=ON', 'LLVM_INSTALL_GTEST=ON'):
    assert flag in fields[3], flag
backends = 'AArch64 AMDGPU ARM AVR BPF Hexagon Lanai LoongArch Mips MSP430 NVPTX PowerPC RISCV Sparc SPIRV SystemZ VE WebAssembly X86 XCore ARC CSKY DirectX M68k Xtensa'.split()
assert all(re.search(r'(?:[=;\"]|^)' + name + r'(?:[;\"]|$)', fields[3]) for name in backends)
assert not fields[4]
metadata = run('sdk-dependencies', 'llvm-devel', *cross, '-v', 'DEPENDS', '-v', 'WRKSRC', '-v', 'EXTRACT_ELEMENTS', '-v', 'TOOL_DEPENDS').splitlines()
assert 'llvm-lit-23.1.4' in metadata[0] and re.search(r'python[0-9]+>=', metadata[3])
assert metadata[1].endswith('/llvm') and '/llvm ' in metadata[2] and '/llvm-devel' not in metadata[2]
assert 'llvm-23.1.4{,nb*}:../../lang/llvm' in metadata[3]
# These are framework metadata queries only. No target compile is requested.
arm = [arg for arg in cross if not arg.startswith('CROSS_MACHINE_ARCH=')] + ['CROSS_MACHINE_ARCH=aarch64']
assert sorted(plist('runtime-arm', 'llvm', *arm)) == sorted(runtime)
for i, bad in enumerate(('LLVM_PACKAGE_PART=devel', 'PKGREVISION=1', 'CROSS_MACHINE_ARCH=i386')):
    reasons = run('bad-contract-' + str(i), 'llvm', *[arg for arg in cross if not arg.startswith(bad.split('=')[0] + '=')], bad, '-v', 'PKG_FAIL_REASON')
    assert reasons.strip(), bad
assert run('native-name', 'llvm', *native_args, '-v', 'PKGNAME').strip() == 'llvm-23.1.4nb6'
assert run('native-sdk-refused', 'llvm-devel', *native_args, '-v', 'PKG_FAIL_REASON').strip()
original = work / 'full-stage'
prefix = original / 'usr/pkg'
metadata_source = work / 'llvm-metadata-source'
metadata_build = metadata_source / 'cmake-pkgsrc-build'
metadata_tools = metadata_build / 'tools/llvm-config'
metadata_tools.mkdir(parents=True)
(metadata_source / 'tools/llvm-config').mkdir(parents=True)
(metadata_source / 'tools/llvm-config/llvm-config.cpp').write_text('// patched upstream llvm-config fixture\n')
metadata_values = {
    'LLVM_SRC_ROOT': str(metadata_source), 'LLVM_OBJ_ROOT': str(metadata_build),
    'LLVM_CPPFLAGS': '-I' + str(metadata_source / 'include'),
    'LLVM_CFLAGS': '-I' + str(metadata_build / 'include'),
    'LLVM_CXXFLAGS': '-isystem' + str(metadata_source / 'include'),
    'LLVM_LDFLAGS': '-L/usr/pkg/lib -Wl,-R/usr/pkg/lib',
}
(metadata_tools / 'BuildVariables.inc').write_text(''.join(
    '#define ' + key + ' ' + json.dumps(value) + '\n' for key, value in metadata_values.items()))
(metadata_tools / 'LibraryDependencies.inc').write_text('fixture libraries\n')
(metadata_tools / 'ExtensionDependencies.inc').write_text('fixture extensions\n')
(metadata_build.mkdir(exist_ok=True))
(metadata_build / 'CMakeCache.txt').write_text('CMAKE_SYSROOT:PATH=/target-sysroot\n')
for path in full:
    target = prefix / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if '/emberbsd/' not in '/' + path:
        target.write_text('source-contract fixture: ' + path + '\n')
subprocess.run([sys.executable, '-B', str(profile / '../../pkgsrc/lang/llvm/files/install-config-metadata.py'),
                str(metadata_tools), str(prefix / 'lib/cmake/llvm/emberbsd'), str(metadata_source),
                str(metadata_build), str(metadata_build / 'CMakeCache.txt')], check=True)
for name, target in {'lib/libLLVM-23.so': 'libLLVM.so.23.1', 'lib/libLLVM.so': 'libLLVM-23.so', 'lib/libLTO.so': 'libLTO.so.23.1', 'lib/libRemarks.so': 'libRemarks.so.23.1'}.items():
    (prefix / name).unlink()
    (prefix / name).symlink_to(target)
(prefix / 'lib/libLLVM.so.23.1').chmod(0o555)


def fingerprint(directory):
    result = {}
    for path in directory.rglob('*'):
        if path.is_symlink():
            result[str(path.relative_to(directory))] = ['symlink', os.readlink(path)]
        elif path.is_file():
            result[str(path.relative_to(directory))] = ['file', hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mode & 0o7777]
    return result


before = fingerprint(prefix)
assert sorted(before) == sorted(full)
for part in ('runtime', 'devel'):
    destination = work / (part + '-stage')
    shutil.copytree(original, destination, symlinks=True)
    run(part + '-select-stage', 'llvm' if part == 'runtime' else 'llvm-devel', *cross, 'WRKDIR=' + str(work / (part + '-select')), 'DESTDIR=' + str(destination), 'WRKSRC=' + str(metadata_source), 'llvm-select-stage')
    selected = runtime if part == 'runtime' else sdk
    assert fingerprint(destination / 'usr/pkg') == {p: row for p, row in before.items() if p in selected}

handoff = work / 'handoff'
shutil.copytree(original, handoff, symlinks=True)
shared = work / 'shared-full-stage'
run('shared-runtime-handoff', 'llvm', *cross, 'WRKDIR=' + str(work / 'shared-runtime'),
    'DESTDIR=' + str(handoff), 'WRKSRC=' + str(metadata_source),
    'EMBERBSD_LLVM_SHARED_STAGE=' + str(shared), 'llvm-select-stage')
assert run('runtime-python-substitution', 'llvm', *cross, '-v', 'SUBST_FILES.python').strip()
assert fingerprint(shared) == before
assert fingerprint(handoff / 'usr/pkg') == {p: row for p, row in before.items() if p in runtime}
replace_stage = work / 'runtime-reinstall'
shutil.copytree(original, replace_stage, symlinks=True)
run('shared-runtime-reinstall-plist', 'llvm', *cross, 'WRKDIR=' + str(work / 'shared-runtime-reinstall'), 'plist')
run('shared-runtime-reinstall', 'llvm', *cross, 'WRKDIR=' + str(work / 'shared-runtime-reinstall'),
    'DESTDIR=' + str(replace_stage), 'WRKSRC=' + str(metadata_source),
    'EMBERBSD_LLVM_SHARED_STAGE=' + str(shared), 'llvm-select-stage')
assert fingerprint(shared) == before, 'runtime replace changed retained full stage'
assert fingerprint(replace_stage / 'usr/pkg') == {p: row for p, row in before.items() if p in runtime}
overlap_root = work / 'overlap-root'
shutil.copytree(original, overlap_root, symlinks=True)
overlap_stage = overlap_root / 'usr/pkg'
overlap_before = fingerprint(overlap_stage)
result = subprocess.run([sys.executable, '-B', str(helper), '--sdk-source', sdk_source,
    'handoff-runtime', str(overlap_stage), str(full_dir / '.PLIST'),
    str(work / 'runtime/.PLIST'), str(work / 'devel/.PLIST'), str(work / 'runtime/.PLIST'),
    str(overlap_stage / '.nested-shared-stage')], capture_output=True, text=True)
assert result.returncode and fingerprint(overlap_stage) == overlap_before, 'overlapping handoff mutated its source stage'
sdk_stage = work / 'sdk-copy/usr/pkg'
sdk_stage.mkdir(parents=True)
(sdk_stage / 'include/llvm/IR').mkdir(parents=True)
shared_wrksrc = work / 'shared-sdk/llvm-shared-stage'
shared_wrksrc.mkdir(parents=True)
shared_vars = run('shared-sdk-vars', 'llvm-devel', *cross, 'WRKDIR=' + str(work / 'shared-sdk'),
    'EMBERBSD_LLVM_SHARED_STAGE=' + str(shared), '-v', 'NO_BUILD', '-v', 'NO_CONFIGURE', '-v', 'WRKSRC').splitlines()
assert shared_vars == ['yes', 'yes', str(work / 'shared-sdk/llvm-shared-stage')], shared_vars
assert not run('shared-sdk-python-substitution', 'llvm-devel', *cross, 'WRKDIR=' + str(work / 'shared-sdk'),
    'EMBERBSD_LLVM_SHARED_STAGE=' + str(shared), '-v', 'SUBST_FILES.python').strip()
for phase in ('extract', 'patch', 'post-extract', 'do-configure', 'do-build'):
    run('shared-sdk-' + phase, 'llvm-devel', *cross, '_PKGSRC_BARRIER=yes',
        'WRKDIR=' + str(work / 'shared-sdk'), 'EMBERBSD_LLVM_SHARED_STAGE=' + str(shared), phase)
run('shared-sdk-plist', 'llvm-devel', *cross, 'WRKDIR=' + str(work / 'shared-sdk'), 'plist')
run('shared-sdk-install', 'llvm-devel', *cross, 'WRKDIR=' + str(work / 'shared-sdk'),
    'DESTDIR=' + str(work / 'sdk-copy'), 'EMBERBSD_LLVM_SHARED_STAGE=' + str(shared), 'do-install')
assert list(shared_wrksrc.iterdir()) == [], 'shared SDK source phases populated the harmless empty WRKSRC'
assert fingerprint(sdk_stage) == {p: row for p, row in before.items() if p in sdk}
assert fingerprint(shared) == before, 'devel copy mutated the retained complete stage'
for case in ('missing', 'unknown', 'overlap', 'union', 'selected', 'symlink-parent', 'part'):
    destination = work / ('reject-' + case)
    shutil.copytree(original, destination, symlinks=True)
    stage = destination / 'usr/pkg'
    lists = [full_dir / '.PLIST', work / 'runtime/.PLIST', work / 'devel/.PLIST', work / 'runtime/.PLIST']
    part = 'runtime'
    if case == 'missing':
        (stage / sdk[0]).unlink()
    elif case == 'unknown':
        (stage / 'bin/unlisted-generator').write_text('unlisted fixture')
    elif case == 'overlap':
        lists[2] = destination / 'overlap.plist'
        lists[2].write_text((work / 'devel/.PLIST').read_text() + runtime[0] + '\n')
    elif case == 'union':
        lists[2] = destination / 'incomplete.plist'
        lists[2].write_text('\n'.join(sdk[1:]) + '\n')
    elif case == 'selected':
        lists[3] = lists[2]
    elif case == 'symlink-parent':
        outside = destination / 'outside'
        outside.mkdir()
        (outside / 'preserved').write_text('outside fixture')
        shutil.rmtree(stage / 'include')
        (stage / 'include').symlink_to(outside)
    else:
        part = 'unsupported'
    unchanged = fingerprint(stage)
    result = subprocess.run([sys.executable, '-B', str(helper), '--sdk-source', sdk_source, part, str(stage), *map(str, lists)], capture_output=True, text=True)
    (work / ('reject-' + case + '.log')).write_text(result.stdout + result.stderr)
    assert result.returncode and fingerprint(stage) == unchanged, case
print('PASS: actual pkgsrc runtime/SDK/native manifests, source/features/dependency roles, seven invalid partition guards')
print('SCOPE: source packaging contracts and text fixtures; no LLVM compilation, target execution or installed LLVM acceptance')
