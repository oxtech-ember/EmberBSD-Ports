# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; Python host controllers for the shared GCC16 toolchain.
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import urllib.request

import sdk_source
from emberbsd_sdk import inventory, paths
from host import *
from target_options import parse

HERE = PROFILE / 'cross'
PORTS = PROFILE.parents[1]


def host_math_main(args):
    native_clang = args[:1] == ['--native-clang']
    if native_clang:
        args = args[1:]
    require(len(args) == 3, 'Usage: host-math.py [--native-clang] ARCHIVES NETBSD_TOOLDIR NEW_WORK --sdk-source SOURCE')
    archives, tools = [build_path(value) for value in args[:2]]
    work = new_path(args[2])
    count = jobs()
    delta = HERE / 'patches/gmp-t-rand-varargs.patch'
    require(sha(delta) == '7ac7687eee380a35f2289baf2bf964c42b82c02bca2272aef6e2e46b23e87736', 'GMP test patch SHA256 mismatch')
    make = tools / 'bin/nbgmake'
    require(os.access(make, os.X_OK), 'Bootstrap GNU make missing')
    cc, cxx = host_compilers(native_clang)
    archives.mkdir(parents=True, exist_ok=True)
    packages = []
    for name, version, suffix in [('gmp', '6.3.0', 'tar.xz'), ('mpfr', '4.2.2', 'tar.bz2'), ('mpc', '1.4.1', 'tar.xz')]:
        row = source_row(name, version, [HERE / 'host-sources.tsv', PROFILE / 'sources.tsv'])
        archive = archives / (name + '-' + version + '.' + suffix)
        if not archive.exists():
            part = Path(str(archive) + '.part')
            require(paths.entry(part) is None, 'Download output exists')
            with urllib.request.urlopen(row[2]) as source, part.open('xb') as target:
                shutil.copyfileobj(source, target)
            require(sha(part) == row[3], name + ' download SHA256 mismatch')
            part.rename(archive)
        require(sha(archive) == row[3], name + ' archive SHA256 mismatch')
        packages.append((name, archive))
    work.mkdir()
    prefix = work / 'prefix'
    prefix.mkdir()
    receipt = platform.platform() + '\nhost_compiler_mode=' + ('native-clang' if native_clang else 'gcc16') + '\nhost_cc=' + cc + '\nhost_cxx=' + cxx + '\ncflags=-O2 -std=gnu17\ncxxflags=-O2\n' + capture([cc, '--version']) + capture([cc, '-dumpmachine']) + capture([cxx, '--version']) + 'jobs=' + count + '\n' + digest_rows([delta] + policy_sources() + sorted(HERE.glob('*.py')))
    env = {'CC': cc, 'CXX': cxx, 'CFLAGS': '-O2 -std=gnu17', 'CXXFLAGS': '-O2'}
    for name, archive in packages:
        source, build = work / (name + '-src'), work / (name + '-build')
        source.mkdir(); build.mkdir()
        receipt += digest_rows([archive])
        logged(['tar', '-xf', archive, '--strip-components=1', '-C', source], work / (name + '-extract.log'))
        if name == 'gmp':
            logged(['patch', '-f', '-N', '-F', '0', '-p1', '-d', source, '-i', delta], work / 'gmp-patch.log')
        configure = [source / 'configure', '--prefix=' + str(prefix), '--disable-shared', '--enable-static']
        if name in ('mpfr', 'mpc'):
            configure.append('--with-gmp=' + str(prefix))
        if name == 'mpc':
            configure.append('--with-mpfr=' + str(prefix))
        logged(configure, work / (name + '-configure.log'), env, build)
        for step, targets in [('build', []), ('check', ['check']), ('install', ['install'])]:
            logged([make] + ([] if step == 'install' else ['-j' + count]) + targets, work / (name + '-' + step + '.log'), env, build)
    (work / 'inputs.txt').write_text(receipt)
    logged([cc, '-O2', '-I' + str(prefix / 'include'), HERE / 'tests/host-gmp.c', prefix / 'lib/libgmp.a', '-o', work / 'host-gmp'], work / 'host-gmp-build.log')
    logged([work / 'host-gmp'], work / 'host-gmp.log')
    logged([work / 'host-gmp', 'timer'], work / 'host-gmp.log', append=True)
    print('GCC host prerequisites built and tested: ' + str(prefix))


def binutils_main(args, make_override=None):
    target, _, args = parse(args)
    require(len(args) == 1, 'Usage: build-binutils.py [--target TARGET] NEW_WORK --sdk-source SOURCE')
    triplet = TARGETS[target][0]
    work, count = new_path(args[0]), jobs()
    make = str(make_override) if make_override else os.environ.get('GMAKE', 'gmake')
    require(shutil.which(make), 'GNU make missing')
    cc, cxx = host_compilers()
    recipe = PORTS / 'profiles/common-build-tools/recipes/devel/binutils'
    archive_name = 'binutils-2.47.tar.xz'
    records = [line.split('\t') for line in (PORTS / 'profiles/common-build-tools/sources.tsv').read_text().splitlines() if line.startswith(archive_name + '\t')]
    require(len(records) == 1, 'Pinned Binutils source missing')
    _, expected, url = records[0][:3]
    info = (recipe / 'distinfo').read_text()
    sha512 = re.findall(r'^SHA512 \(binutils-2.47.tar.xz\) = ([0-9a-f]{128})$', info, re.M)
    sizes = re.findall(r'^Size \(binutils-2.47.tar.xz\) = ([0-9]+)', info, re.M)
    require(len(sha512) == len(sizes) == 1, 'Binutils distinfo incomplete')
    patches = audit_patches(recipe, exclude_isl=False)
    work.mkdir()
    archive = work / archive_name
    selected = os.environ.get('EMBER_BINUTILS_ARCHIVE')
    if selected:
        shutil.copyfile(build_path(selected), archive)
    else:
        part = work / (archive_name + '.part')
        with urllib.request.urlopen(url) as source, part.open('xb') as output:
            shutil.copyfileobj(source, output)
        part.rename(archive)
    require(sha(archive) == expected and inventory.hash_file(archive, 'sha512') == sha512[0] and archive.stat().st_size == int(sizes[0]), 'Binutils archive hash or size mismatch')
    source, build, prefix = [work / name for name in ('src', 'build', 'prefix')]
    for directory in (source, build, prefix):
        directory.mkdir()
    logged(['tar', '-xf', archive, '--strip-components=1', '-C', source], work / 'extract.log')
    with (work / 'patch.log').open('wb') as log:
        for name in patches:
            patch_log = work / (name + '.log')
            logged(['patch', '-f', '-N', '-F', '0', '-p0', '-d', source, '-i', recipe / 'patches' / name], patch_log)
            log.write(('patch=' + name + '\n').encode() + patch_log.read_bytes())
    env = {'CC': cc, 'CXX': cxx, 'MAKEINFO': 'true'}
    configure = [source / 'configure', '--target=' + triplet, '--prefix=' + str(prefix), '--program-prefix=' + triplet + '-', '--enable-plugins', '--disable-nls', '--disable-gprofng']
    if platform.system() in ('Linux', 'Darwin'):
        configure.append('--disable-libctf')
    logged(configure, work / 'configure.log', env, build)
    logged([make, '-j' + count], work / 'build.log', env, build)
    logged([make, 'install'], work / 'install.log', env, build)
    for name in BINUTILS:
        require(os.access(prefix / 'bin' / (triplet + '-' + name), os.X_OK), 'Installed Binutils tool missing: ' + name)
    for name in ('as', 'ld', 'readelf'):
        require(' 2.47' in capture([prefix / 'bin' / (triplet + '-' + name), '--version']).splitlines()[0], 'Unexpected GNU tool version')
    require(any(path.is_file() for path in (prefix / triplet / 'lib/ldscripts').iterdir()), 'Installed Binutils linker scripts missing')
    receipt = platform.platform() + '\ntarget=' + target + '\ntriplet=' + triplet + '\nhost_cc=' + cc + '\nhost_cxx=' + cxx + '\ngmake=' + make + '\njobs=' + count + '\nconfigure=' + ' '.join(str(arg) for arg in configure[1:]) + '\n'
    receipt += capture([cc, '--version']) + capture([cc, '-dumpmachine']) + capture([cxx, '--version']) + capture([make, '--version']) + capture([prefix / 'bin' / (triplet + '-as'), '--version']) + capture([prefix / 'bin' / (triplet + '-ld'), '--version']) + digest_rows([archive, recipe / 'distinfo'] + sorted((recipe / 'patches').glob('patch-*')))
    receipt += digest_rows(policy_sources() + sorted(HERE.glob('*.py')))
    (work / 'inputs.txt').write_text(receipt)
    print('Binutils 2.47 cross tools built: ' + str(prefix))


def relocate_binutils(binutils, prefix, triplet, work):
    (prefix / triplet / 'bin').mkdir(parents=True)
    (prefix / triplet / 'lib').mkdir()
    for name in BINUTILS:
        executable = triplet + '-' + name
        shutil.copy2(binutils / 'bin' / executable, prefix / 'bin' / executable)
        (prefix / triplet / 'bin' / name).symlink_to('../../bin/' + executable)
    shutil.copytree(binutils / triplet / 'lib/ldscripts', prefix / triplet / 'lib/ldscripts')
    (work / 'linker-scripts.sha256').write_text(digest_rows(sorted((binutils / triplet / 'lib/ldscripts').iterdir())))


def build_main(args):
    target, mode, args = parse(args, kernel_allowed=True)
    require(len(args) in ((4, 5) if mode == 'kernel' else (5, 6)), 'Usage: build.py [--target TARGET] [--kernel] PKGSRC ARCHIVE [SYSROOT] TOOLDIR [MATH] NEW_WORK --sdk-source SOURCE')
    count = jobs()
    values = [build_path(value) for value in args]
    pkgsrc, archive = values[:2]
    offset = 2 if mode == 'kernel' else 3
    sysroot = None if mode == 'kernel' else values[2]
    tools, *remaining = values[offset:]
    math = remaining[0] if len(remaining) == 2 else os.environ.get('EMBER_HOST_MATH_PREFIX')
    work = new_path(values[-1])
    triplet = TARGETS[target][0]
    if sysroot:
        require((sysroot / 'usr/include/stddef.h').is_file() and (sysroot / ('usr/pkg/gcc16/lib/gcc/' + triplet + '/' + VERSION + '/crtbegin.o')).is_file(), 'The sysroot must contain selected target GCC16 package')
        require((sysroot / ('usr/pkg/gcc16/include/c++/' + triplet)).is_dir(), 'Selected target GCC16 C++ headers missing')
    make = tools / 'bin/nbgmake'
    require(os.access(make, os.X_OK), 'Bootstrap GNU make missing')
    if math:
        math = check_math(math)
    audit_source(pkgsrc, archive, runtime=False)
    cc, cxx = host_compilers()
    work.mkdir()
    if not math:
        host_math_main([os.environ.get('EMBER_HOST_MATH_ARCHIVES', str(work / 'host-archives')), str(tools), str(work / 'host-math')])
        math = check_math(work / 'host-math/prefix')
    prefix = work / 'toolchain'
    for directory in (work / 'build', prefix, prefix / 'bin'):
        directory.mkdir()
    binutils_main(['--target', target, str(work / 'binutils')], make_override=make)
    binutils = work / 'binutils/prefix'
    relocate_binutils(binutils, prefix, triplet, work)
    recipe = pkgsrc / 'lang/gcc16'
    receipt = platform.platform() + '\nmode=' + mode + '\ntarget=' + target + '\ntriplet=' + triplet + '\nhost_cc=' + cc + '\nhost_cxx=' + cxx + '\nhost_cppflags=' + os.environ.get('HOST_CPPFLAGS', '') + '\nhost_ldflags=' + os.environ.get('HOST_LDFLAGS', '') + '\n'
    receipt += capture([cc, '--version']) + capture([cc, '-dumpmachine']) + capture([cxx, '--version']) + digest_rows([archive, recipe / 'distinfo'] + sorted((recipe / 'patches').glob('patch-*'))) + capture([make, '--version']) + capture([prefix / 'bin' / (triplet + '-ld'), '--version'])
    receipt += 'sysroot=' + (str(sysroot) if sysroot else '') + '\nbootstrap_make=' + str(tools) + '\nhost_math=' + str(math) + '\njobs=' + count + '\n' + digest_rows([math / 'lib' / ('lib' + name + '.a') for name in ('gmp', 'mpfr', 'mpc')]) + (work / 'binutils/inputs.txt').read_text()
    receipt += digest_rows(policy_sources() + sorted(HERE.glob('*.py')) + sorted((HERE / 'tests').glob('*.py')))
    (work / 'inputs.txt').write_text(receipt)
    logged([cc, '-O2', '-I' + str(math / 'include'), HERE / 'tests/host-gmp.c', math / 'lib/libgmp.a', '-o', work / 'host-gmp'], work / 'host-gmp-build.log')
    logged([work / 'host-gmp'], work / 'host-gmp.log')
    logged([work / 'host-gmp', 'timer'], work / 'host-gmp.log', append=True)
    prepare_source(pkgsrc, archive, work / 'src', runtime=False)
    configure = [work / 'src/configure', '--target=' + triplet, '--prefix=' + str(prefix)]
    configure += ['--without-headers', '--disable-shared', '--disable-threads'] if mode == 'kernel' else ['--with-sysroot=' + str(sysroot), '--with-gxx-include-dir=' + str(sysroot / 'usr/pkg/gcc16/include/c++')]
    configure += ['--with-' + name + '=' + str(math) for name in ('gmp', 'mpfr', 'mpc')] + ['--with-as=' + str(prefix / 'bin' / (triplet + '-as')), '--with-ld=' + str(prefix / 'bin' / (triplet + '-ld')), '--enable-languages=c,c++', '--disable-bootstrap', '--disable-multilib', '--disable-nls', '--without-isl']
    flags = os.environ.get('HOST_CPPFLAGS', '')
    env = {'CC': cc, 'CXX': cxx, 'CPPFLAGS': flags, 'CFLAGS': '-O2 ' + flags, 'CXXFLAGS': '-O2 ' + flags, 'LDFLAGS': os.environ.get('HOST_LDFLAGS', '')}
    logged(configure, work / 'configure.log', env, work / 'build')
    logged([make, '-j' + count, 'all-gcc'], work / 'build.log', env, work / 'build')
    logged([make, 'install-gcc'], work / 'install.log', env, work / 'build')
    check_compilers(prefix, target)
    import contextlib
    import importlib.util
    spec = importlib.util.spec_from_file_location('gcc16_compiler_probes', HERE / 'tests/compiler_probes.py')
    probes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probes)
    with (work / 'split-dwarf.log').open('x') as output, contextlib.redirect_stdout(output):
        probes.split_dwarf(['--target', target, prefix, work / 'split-dwarf'])
    if target == 'aarch64':
        with (work / 'lto-binutils.log').open('x') as output, contextlib.redirect_stdout(output):
            probes.lto_binutils([prefix, work / 'lto-binutils'])
        with (work / 'inputs.txt').open('a') as output:
            output.write((work / 'lto-binutils/inputs.txt').read_text())
    print('GCC16 cross compiler built: ' + str(prefix))
    print('Kernel build and boot remain separate.' if mode == 'kernel' else 'Run the compiled acceptance programs on EmberBSD before accepting this toolchain.')


def compile_tests_main(args):
    target, _, args = parse(args)
    require(len(args) == 3, 'Usage: compile-tests.py [--target TARGET] PREFIX SYSROOT NEW_OUTPUT --sdk-source SOURCE')
    prefix, sysroot = [build_path(value) for value in args[:2]]
    out = new_path(args[2])
    triplet = TARGETS[target][0]
    tools = check_compilers(prefix, target)
    require((sysroot / 'usr/include/stddef.h').is_file() and (sysroot / ('usr/pkg/gcc16/lib/gcc/' + triplet + '/' + VERSION + '/crtbegin.o')).is_file() and (sysroot / ('usr/pkg/gcc16/include/c++/' + triplet)).is_dir(), 'Selected target GCC16 runtime missing')
    for name in ('libstdc++.so.7', 'libgcc_s.so.1'):
        require(paths.inside((sysroot / 'usr/pkg/gcc16/lib' / name).resolve(strict=True), sysroot / 'usr/pkg/gcc16'), 'Target runtime escapes sysroot GCC16 prefix')
    out.mkdir()
    (out / 'target.txt').write_text(target + '\n')
    (out / 'runtime-sha256.tsv').write_text(''.join(name + '\t' + sha((sysroot / 'usr/pkg/gcc16/lib' / version).resolve(strict=True)) + '\n' for name, version in [('libstdc++.so', 'libstdc++.so.7'), ('libgcc_s.so', 'libgcc_s.so.1')]))
    result = process.capture([str(tools['gcc']), '-v'], env=environment())
    (out / 'compiler.txt').write_bytes(result.stdout + result.stderr)
    flags = ['--sysroot=' + str(sysroot), '-B' + str(sysroot / ('usr/pkg/gcc16/lib/gcc/' + triplet + '/' + VERSION)) + '/', '-L' + str(sysroot / 'usr/pkg/gcc16/lib'), '-Wl,-rpath,/usr/pkg/gcc16/lib']
    source = PROFILE / 'tests'
    for suffix in ('', '-lto'):
        logged([tools['gcc']] + flags + ['-std=c11', '-O2'] + (['-flto'] if suffix else []) + ['-Wall', '-Wextra', '-Werror', '-pthread', source / 'atomic-tls.c', '-o', out / ('atomic-tls' + suffix)], out / ('atomic-tls' + suffix + '-build.log'))
    for directory in ('', '/' + triplet, '/backward'):
        flags += ['-isystem', str(sysroot / 'usr/pkg/gcc16/include/c++') + directory]
    programs = [('float-constexpr.o', ['-std=c++20', '-O3', '-Wall', '-Wextra', '-Werror', '-c', HERE / 'tests/float-constexpr.cc']), ('libboundary.so', ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared', source / 'boundary.cc', '-Wl,-soname,libboundary.so']), ('boundary', ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread', source / 'boundary-main.cc', '-L' + str(out), '-Wl,-rpath,$ORIGIN', '-lboundary'])]
    for name, arguments in programs:
        logged([tools['g++']] + flags + arguments + ['-o', out / name], out / (name + '-build.log'))
    dynamic = capture([tools['readelf'], '-d', out / 'boundary', out / 'libboundary.so'])
    (out / 'dynamic.txt').write_text(dynamic)
    require(not any(('RPATH' in line or 'RUNPATH' in line or 'NEEDED' in line) and any(str(path) in line for path in (prefix, sysroot, out)) for line in dynamic.splitlines()), 'Host path leaked into target dynamic dependencies')
    for name in ('check-runtime.sh', 'target-options.sh'):
        shutil.copy2(HERE / 'tests/target' / name, out / name)
    shutil.copy2(HERE / 'tests/target/run-target.sh', out / 'run-target.sh')
    print('Cross-compiled tests: ' + str(out) + '; run run-target.sh on EmberBSD')


def check_runtime_main(args):
    require(len(args) == 2, 'Usage: check-runtime.py PREFIX OUTPUT --sdk-source SOURCE')
    prefix = Path(args[0]).resolve(strict=True)
    output = Path(args[1])
    receipt = (output / 'runtime-sha256.tsv').read_text().splitlines()
    loaded = [line.split() for line in (output / 'loaded.txt').read_text().splitlines()]
    for name in ('libstdc++.so', 'libgcc_s.so'):
        matches = [line.split('\t')[1] for line in receipt if line.startswith(name + '\t') and len(line.split('\t')) == 2]
        require(len(matches) == 1 and re.fullmatch(r'[0-9a-f]{64}', matches[0]), 'Invalid runtime SHA256 receipt: ' + name)
        files = [row[1] for row in loaded if len(row) >= 2 and row[0] == 'LOADED' and name in row[1]]
        require(len(files) == 1, 'Expected one loaded ' + name)
        actual = Path(files[0]).resolve(strict=True)
        require(paths.inside(actual, prefix), 'Runtime outside prefix')
        require(sha(actual) == matches[0], 'Runtime SHA256 mismatch')


def libatomic_main(args):
    require(len(args) == 4, 'Usage: build-libatomic.py PREFIX SYSROOT ARCHIVE NEW_OUTPUT --sdk-source SOURCE')
    compiler, sysroot, archive = [build_path(value) for value in args[:3]]
    output, count = new_path(args[3]), jobs(2)
    tools = check_compilers(compiler, 'aarch64')
    triplet = TARGETS['aarch64'][0]
    crt = sysroot / 'usr/pkg/gcc16/lib/gcc' / triplet / VERSION
    require((crt / 'crtbegin.o').is_file() and (sysroot / 'usr/include/pthread.h').is_file(), 'Target runtime/header missing')
    require(sha(archive) == source_row('gcc', VERSION)[3], 'GCC archive SHA256 mismatch')
    recipe = PORTS / 'pkgsrc/local-robotics/gcc16-libatomic'
    output.mkdir()
    for name in ('source', 'build', 'logs'):
        (output / name).mkdir()
    members = 'libatomic config include config.guess config.sub ltmain.sh ltoptions.m4 ltsugar.m4 ltversion.m4 lt~obsolete.m4 libtool.m4 install-sh missing depcomp mkinstalldirs compile multilib.am config-ml.in gcc/BASE-VER COPYING3 COPYING.RUNTIME'.split()
    logged(['tar', '-xf', archive, '--strip-components=1', '-C', output / 'source'] + ['gcc-' + VERSION + '/' + name for name in members], output / 'logs/extract.log')
    flags = '-O2 -g --sysroot=' + str(sysroot) + ' -B' + str(crt) + '/ -L' + str(sysroot / 'usr/pkg/gcc16/lib') + ' -march=armv8-a'
    receipt = platform.platform() + '\n' + capture([tools['gcc'], '--version']) + capture([tools['gcc'], '-dumpmachine']) + capture([tools['ld'], '--version']) + capture(['make', '--version']) + 'sysroot=' + str(sysroot) + '\nCFLAGS=' + flags + '\njobs=' + count + '\n' + digest_rows([archive, tools['gcc'], HERE / 'build-libatomic.py', recipe / 'files/SOURCE'])
    receipt += digest_rows(policy_sources() + sorted(HERE.glob('*.py')))
    (output / 'inputs.txt').write_text(receipt)
    import shlex
    (output / 'target-macros.txt').write_text(capture([tools['gcc']] + shlex.split(flags) + ['-dM', '-E', '-x', 'c', '-'], input=b'\n'))
    env = {'CC': str(tools['gcc']), 'AR': str(tools['ar']), 'RANLIB': str(tools['ranlib']), 'NM': str(tools['nm']), 'CFLAGS': flags, 'LDFLAGS': '-Wl,-rpath,/usr/pkg/gcc16/lib'}
    build = output / 'build'
    build_triplet = capture(['sh', output / 'source/config.guess']).strip()
    logged([output / 'source/libatomic/configure', '--build=' + build_triplet, '--host=' + triplet, '--target=' + triplet, '--prefix=/usr/pkg/gcc16', '--enable-shared', '--enable-static', '--disable-multilib'], output / 'logs/configure.log', env, build)
    link_flags = '-Wc,--sysroot=' + str(sysroot) + ' -Wc,-B' + str(crt) + '/ -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-t'
    logged(['make', '-j' + count, 'V=1', 'LDFLAGS=' + link_flags, 'libatomic.la'], output / 'logs/build.log', env, build)
    logged(['make', 'DESTDIR=' + str(output / 'stage'), 'install-toolexeclibLTLIBRARIES'], output / 'logs/install.log', env, build)
    metadata = output / 'stage/usr/pkg/gcc16/lib/libatomic.la'
    data = metadata.read_text().replace('-L' + str(sysroot / 'usr/pkg/gcc16/lib'), '-L/usr/pkg/gcc16/lib')
    metadata.write_text(data)
    (output / 'libatomic.la').write_text(data)
    license_dir = output / 'stage/usr/pkg/share/licenses/gcc16-libatomic'
    license_dir.mkdir(parents=True)
    for path in [output / 'source/COPYING3', output / 'source/COPYING.RUNTIME', recipe / 'files/SOURCE']:
        shutil.copy2(path, license_dir / path.name)
    target = output / 'stage/usr/pkg/gcc16/lib/libatomic.so.3.0'
    header = capture([tools['readelf'], '-h', target])
    dynamic = capture([tools['readelf'], '-d', target])
    (output / 'logs/libatomic-elf.txt').write_text(header)
    (output / 'logs/libatomic-dynamic.txt').write_text(dynamic)
    require(re.search(r'Machine:.*AArch64', header) and re.search(r'SONAME.*\[libatomic.so.3\]', dynamic), 'libatomic target/SONAME mismatch')
    require(not re.search(r'(RPATH|RUNPATH).*\[.*(/workspace|/tmp|/home|/Users|/usr/local)', dynamic), 'Host directory in target runtime path')
    require(not re.search(r'(dependency_libs|libdir)=.*(/workspace|/tmp|/home|/Users)', data), 'Host directory in installed libtool metadata')
    shutil.copy2(PROFILE / 'tests/libatomic.cpp', output / 'atomic-contract.cpp')
    cxx_args = [tools['g++']] + shlex.split(flags) + ['-std=c++17', '-pthread']
    for suffix in ('', '/' + triplet, '/backward'):
        cxx_args += ['-isystem', str(sysroot / 'usr/pkg/gcc16/include/c++') + suffix]
    logged(cxx_args + [output / 'atomic-contract.cpp', '-L' + str(output / 'stage/usr/pkg/gcc16/lib'), '-Wl,-rpath,/usr/pkg/gcc16/lib', '-latomic', '-o', output / 'atomic-contract'], output / 'logs/consumer-build.log')
    dynamic = capture([tools['readelf'], '-d', output / 'atomic-contract'])
    (output / 'logs/consumer-dynamic.txt').write_text(dynamic)
    require(re.search(r'NEEDED.*\[libatomic.so.3\]', dynamic), 'libatomic consumer dependency missing')
    tree = inventory.snapshot_tree(output / 'stage/usr/pkg')
    plist = '\n'.join(name for name, record in tree.items() if record['kind'] in ('file', 'link')) + '\n'
    (output / 'PLIST').write_text(plist)
    if (recipe / 'PLIST').is_file():
        expected = sorted(line for line in (recipe / 'PLIST').read_text().splitlines() if line and not line.startswith('@comment'))
        require(expected == plist.splitlines(), 'libatomic package inventory mismatch')
        (output / 'expected-PLIST').write_text('\n'.join(expected) + '\n')
    print('GCC16 libatomic cross-build PASS: ' + str(output / 'stage'))
    print('Execute atomic-contract on EmberBSD; target runtime acceptance remains separate.')
