# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; Python host controllers for the shared GCC16 toolchain.
import os
import argparse
from pathlib import Path
import platform
import re
import shutil
import sys
import urllib.request
import argparse

import sdk_source
from emberbsd_sdk import (application_toolchain, inventory, jsonio, native_toolset, paths,
                          sysroot_transfer, target_toolchain)
from host import *
from target_options import FIRMWARE_TARGETS, parse
from bootstrap_libgcc import build as build_bootstrap_libgcc, headers as bootstrap_headers

HERE = PROFILE / 'cross'
PORTS = PROFILE.parents[1]
GMP_RAND_PATCH_SHA256 = '7ac7687eee380a35f2289baf2bf964c42b82c02bca2272aef6e2e46b23e87736'


def host_math_main(args):
    native_clang = args[:1] == ['--native-clang']
    if native_clang:
        args = args[1:]
    require(len(args) == 3, 'Usage: host-math.py [--native-clang] ARCHIVES NETBSD_TOOLDIR NEW_WORK --sdk-source SOURCE')
    archives, tools = [build_path(value) for value in args[:2]]
    work = new_path(args[2])
    count = jobs()
    delta = HERE / 'patches/gmp-t-rand-varargs.patch'
    require(sha(delta) == GMP_RAND_PATCH_SHA256, 'GMP test patch SHA256 mismatch')
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
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument('--host-prefix', action='append')
    parser.add_argument('--host-compiler-family', choices=('clang', 'gcc'), action='append')
    options, args = parser.parse_known_args(args)
    for values in (options.host_prefix, options.host_compiler_family):
        require(values is None or len(values) == 1, 'Duplicate native Binutils selection')
    target, _, args = parse(args, kernel_target_allowed=True)
    require(len(args) == 1, 'Usage: build-binutils.py [--target TARGET] --host-prefix PREFIX '
            '[--host-compiler-family clang|gcc] NEW_WORK --sdk-source SOURCE')
    native = None
    # The enclosing explicit GCC and firmware producers keep their existing
    # host compiler selection. Standalone Binutils uses the shared prefix API.
    if make_override is None or options.host_prefix or options.host_compiler_family:
        from binutils_host import native_selection
        prefix = (options.host_prefix or [os.environ.get('EMBERBSD_HOST_PREFIX')])[0]
        family = (options.host_compiler_family or [os.environ.get('EMBERBSD_HOST_COMPILER_FAMILY', 'clang')])[0]
        native = native_selection(prefix, family)
    return _build_binutils(target, args[0], make_override, native=native)


def _build_binutils(target, new_work, make_override=None, native=None):
    require(target in TARGETS or target in KERNEL_TARGETS or target in FIRMWARE_TARGETS,
            'Unsupported Binutils target: ' + target)
    triplet = target_triplet(target) if target in TARGETS or target in KERNEL_TARGETS else FIRMWARE_TARGETS[target]
    work, count = new_path(new_work), jobs()
    if native is None:
        make = str(make_override) if make_override else os.environ.get('GMAKE', 'gmake')
        require(shutil.which(make), 'GNU make missing')
        cc, cxx = host_compilers()
        env = {'CC': cc, 'CXX': cxx, 'MAKEINFO': 'true'}
        tar, patch_command = 'tar', 'patch'
    else:
        selected, env = native
        make = selected.tool('gmake')
        require(make_override is None or str(make_override) == make,
                'GNU make differs from the selected native prefix')
        cc, cxx = selected.tool('cc'), selected.tool('cxx')
        tar, patch_command = selected.tool('bsdtar'), selected.tool('patch')
    recipe = PORTS / 'pkgsrc/devel/binutils'
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
    if native is not None:
        from binutils_host import native_environment
        env = native_environment(selected, env, work)
    archive = work / archive_name
    selected_archive = os.environ.get('EMBER_BINUTILS_ARCHIVE')
    if selected_archive:
        shutil.copyfile(build_path(selected_archive), archive)
    else:
        part = work / (archive_name + '.part')
        with urllib.request.urlopen(url) as source, part.open('xb') as output:
            shutil.copyfileobj(source, output)
        part.rename(archive)
    require(sha(archive) == expected and inventory.hash_file(archive, 'sha512') == sha512[0] and archive.stat().st_size == int(sizes[0]), 'Binutils archive hash or size mismatch')
    source, build, prefix = [work / name for name in ('src', 'build', 'prefix')]
    for directory in (source, build, prefix):
        directory.mkdir()
    logged([tar, '-xf', archive, '--strip-components=1', '-C', source], work / 'extract.log', env)
    with (work / 'patch.log').open('wb') as log:
        for name in patches:
            patch_log = work / (name + '.log')
            logged([patch_command, '-f', '-N', '-F', '0', '-p0', '-d', source, '-i', recipe / 'patches' / name], patch_log, env)
            log.write(('patch=' + name + '\n').encode() + patch_log.read_bytes())
    configure = [source / 'configure', '--target=' + triplet, '--prefix=' + str(prefix), '--program-prefix=' + triplet + '-', '--enable-plugins', '--disable-nls', '--disable-gprofng']
    if native is not None:
        configure.insert(0, selected.tool('sh'))
        configure.append('--with-system-zlib')
    if platform.system() in ('Linux', 'Darwin'):
        configure.append('--disable-libctf')
    logged(configure, work / 'configure.log', env, build)
    logged([make, '-j' + count], work / 'build.log', env, build)
    logged([make, 'install'], work / 'install.log', env, build)
    require_tools(prefix, triplet, BINUTILS)
    for name in ('as', 'ld', 'readelf'):
        require(' 2.47' in capture([prefix / 'bin' / (triplet + '-' + name), '--version'], env=env).splitlines()[0], 'Unexpected GNU tool version')
    require(any(path.is_file() for path in (prefix / triplet / 'lib/ldscripts').iterdir()), 'Installed Binutils linker scripts missing')
    receipt = platform.platform() + '\ntarget=' + target + '\ntriplet=' + triplet + '\nhost_cc=' + cc + '\nhost_cxx=' + cxx + '\ngmake=' + make + '\njobs=' + count + '\nconfigure=' + ' '.join(str(arg) for arg in configure[1:]) + '\n'
    receipt += capture([cc, '--version'], env=env) + capture([cc, '-dumpmachine'], env=env) + capture([cxx, '--version'], env=env) + capture([make, '--version'], env=env) + capture([prefix / 'bin' / (triplet + '-as'), '--version'], env=env) + capture([prefix / 'bin' / (triplet + '-ld'), '--version'], env=env) + digest_rows([archive, recipe / 'distinfo'] + sorted((recipe / 'patches').glob('patch-*')))
    receipt += digest_rows(policy_sources() + sorted(HERE.glob('*.py')))
    if native is not None:
        from binutils_host import CONTRACT
        receipt += digest_rows([CONTRACT])
    (work / 'inputs.txt').write_text(receipt)
    if native is not None:
        from binutils_host import write_bfd_input
        write_bfd_input(work, triplet, capture, env, host_prefix=selected.bundle_root)
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
    target, mode, args = parse(args, kernel_allowed=True, bootstrap_allowed=True, fortran_allowed=True)
    if mode != 'applications-fortran':
        return _build_compiler(target, mode, args)
    owned = {}
    try:
        return _build_compiler(target, mode, args, owned=owned)
    except ProcessOwnershipError as error:
        if owned:
            from fortran_support import quarantine_work
            quarantine_work(owned, error)
        raise


def _build_compiler(target, mode, args, *, owned=None):
    fortran = mode == 'applications-fortran'
    bootstrap_libgcc = mode == 'kernel-bootstrap'
    if bootstrap_libgcc:
        mode = 'kernel'
    has_sysroot = mode != 'kernel' or bootstrap_libgcc
    require(len(args) in ((5, 6) if has_sysroot else (4, 5)), 'Usage: build.py [--target TARGET] [--with-fortran | --kernel [--bootstrap-libgcc]] PKGSRC ARCHIVE [SYSROOT_OR_BOOTSTRAP_HEADERS] TOOLDIR [MATH] NEW_WORK --sdk-source SOURCE')
    count = jobs()
    values = [build_path(value) for value in args]
    pkgsrc, archive = values[:2]
    offset = 3 if has_sysroot else 2
    sysroot = values[2] if has_sysroot else None
    tools, *remaining = values[offset:]
    math = remaining[0] if len(remaining) == 2 else os.environ.get('EMBER_HOST_MATH_PREFIX')
    work = new_path(values[-1])
    triplet = target_triplet(target)
    header_inputs = bootstrap_headers(sysroot, target) if bootstrap_libgcc else None
    if bootstrap_libgcc:
        paths.reject_overlap(sysroot, work)
    if sysroot and not bootstrap_libgcc:
        require((sysroot / 'usr/include/stddef.h').is_file() and (sysroot / ('usr/pkg/gcc16/lib/gcc/' + triplet + '/' + VERSION + '/crtbegin.o')).is_file(), 'The sysroot must contain selected target GCC16 package')
        require((sysroot / ('usr/pkg/gcc16/include/c++/' + triplet)).is_dir(), 'Selected target GCC16 C++ headers missing')
    make = tools / 'bin/nbgmake'
    require(os.access(make, os.X_OK), 'Bootstrap GNU make missing')
    if math:
        math = check_math(math)
    audit_source(pkgsrc, archive, runtime=False)
    if fortran:
        from fortran_support import source_state
        fortran_sources = source_state(pkgsrc, archive)
    cc, cxx = host_compilers()
    work.mkdir()
    if owned is not None:
        identity = paths.real_directory(work)
        owned.update(path=str(work), device=identity.st_dev, inode=identity.st_ino)
    if bootstrap_libgcc:
        jsonio.write_json(work / 'bootstrap-headers.json', header_inputs)
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
    if bootstrap_libgcc:
        receipt += 'bootstrap_libgcc=yes\ninhibit_libc=true\nseed_source=' + header_inputs['source_commit'] + '\n'
        receipt += digest_rows([work / 'bootstrap-headers.json'])
    if fortran:
        receipt += 'languages=c,c++,fortran\n'
    (work / 'inputs.txt').write_text(receipt)
    logged([cc, '-O2', '-I' + str(math / 'include'), HERE / 'tests/host-gmp.c', math / 'lib/libgmp.a', '-o', work / 'host-gmp'], work / 'host-gmp-build.log')
    logged([work / 'host-gmp'], work / 'host-gmp.log')
    logged([work / 'host-gmp', 'timer'], work / 'host-gmp.log', append=True)
    prepare_source(pkgsrc, archive, work / 'src', runtime=False)
    configure = [work / 'src/configure', '--target=' + triplet, '--prefix=' + str(prefix)]
    configure += ['--without-headers', '--disable-shared', '--disable-threads'] if mode == 'kernel' else ['--with-sysroot=' + str(sysroot), '--with-gxx-include-dir=' + str(sysroot / 'usr/pkg/gcc16/include/c++')]
    if bootstrap_libgcc:
        configure.append('--with-sysroot=' + str(sysroot))
    configure += ['--with-' + name + '=' + str(math) for name in ('gmp', 'mpfr', 'mpc')] + ['--with-as=' + str(prefix / 'bin' / (triplet + '-as')), '--with-ld=' + str(prefix / 'bin' / (triplet + '-ld')), '--enable-languages=' + ('c,c++,fortran' if fortran else 'c,c++'), '--disable-bootstrap', '--disable-multilib', '--disable-nls', '--without-isl']
    flags = os.environ.get('HOST_CPPFLAGS', '')
    env = {'CC': cc, 'CXX': cxx, 'CPPFLAGS': flags, 'CFLAGS': '-O2 ' + flags, 'CXXFLAGS': '-O2 ' + flags, 'LDFLAGS': os.environ.get('HOST_LDFLAGS', '')}
    if bootstrap_libgcc:
        # GCC preserves this configure input when a header sysroot is present.
        # The first static support build must still avoid target libc calls.
        env['inhibit_libc'] = 'true'
    logged(configure, work / 'configure.log', env, work / 'build')
    logged([make, '-j' + count, 'all-gcc'], work / 'build.log', env, work / 'build')
    logged([make, 'install-gcc'], work / 'install.log', env, work / 'build')
    check_compilers(prefix, target)
    # install-gcc shares this prefix. The kernel still needs size afterwards.
    require_tools(prefix, triplet, BINUTILS)
    import contextlib
    import importlib.util
    spec = importlib.util.spec_from_file_location('gcc16_compiler_probes', HERE / 'tests/compiler_probes.py')
    probes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probes)
    with (work / 'split-dwarf.log').open('x') as output, contextlib.redirect_stdout(output):
        probes.split_dwarf(['--target', target, str(prefix), str(work / 'split-dwarf')])
    if target in KERNEL_TARGETS:
        arm_probe = work / 'armv7-abi'
        with (work / 'armv7-abi.log').open('x') as output, contextlib.redirect_stdout(output):
            probes.armv7_abi(['--target', target, str(prefix), str(arm_probe)])
        with (work / 'inputs.txt').open('a') as output:
            output.write((arm_probe / 'inputs.txt').read_text())
    if target == 'aarch64':
        with (work / 'lto-binutils.log').open('x') as output, contextlib.redirect_stdout(output):
            probes.lto_binutils([prefix, work / 'lto-binutils'])
        with (work / 'inputs.txt').open('a') as output:
            output.write((work / 'lto-binutils/inputs.txt').read_text())
    if bootstrap_libgcc:
        build_bootstrap_libgcc(work, prefix, target, make, count, env)
    if fortran:
        from fortran_support import qualify
        capability = qualify(prefix, target, work / 'fortran-check', fortran_sources, pkgsrc, archive, quarantine=work)
        with (work / 'inputs.txt').open('a') as output:
            output.write(digest_rows([capability]))
    print('GCC16 cross compiler built: ' + str(prefix))
    print('Kernel build and boot remain separate.' if mode == 'kernel' else 'Run the compiled acceptance programs on EmberBSD before accepting this toolchain.')


def select_test_toolchain(family, prefix, sysroot, target, host_prefix=None):
    """Select one target compiler and its matching application runtime."""
    triplet = TARGETS[target][0]
    require((sysroot / 'usr/include/stddef.h').is_file(), 'Selected target C headers missing')
    if family == 'clang':
        require(getattr(application_toolchain, 'APPLICATION_TOOLCHAIN_API', None) == 2,
                'Clang target tests require SDK application toolchain API2')
        require(host_prefix is not None,
                'Clang target tests require --host-prefix for the selected native SDK tools')
        native = native_toolset.load_host_prefix(host_prefix,
            required_roles={'cc', 'cxx', 'cpp', 'python'}, compiler_family='clang')
        require(Path(sys.executable).resolve() == Path(native.tool('python')).resolve(),
                'Controller Python differs from the selected native SDK prefix')
        compiler = target_toolchain.clang_compiler(prefix, triplet,
            host=dict(native.host), env={'PATH':native.path})
        runtime = application_toolchain.load_clang_runtime(sysroot, target=target)
        sysroot_identity = clang_sysroot_identity(sysroot, target, runtime)
        compile_commands = application_toolchain.clang_application_commands(
            compiler, sysroot, runtime, link=False)
        link_commands = application_toolchain.clang_application_commands(
            compiler, sysroot, runtime, link=True)
        return dict(family='clang', cc=compile_commands['cc'], cxx=compile_commands['cxx'],
            cc_link=link_commands['cc'], cxx_link=link_commands['cxx'],
            readelf=compiler['binaries']['readelf']['selected_path'],
            identity=dict(format='emberbsd-target-test-compiler', version=1, family='clang',
                triplet=compiler['triplet'], compiler_version=compiler['version'],
                reported_triplet=compiler['reported_triplet'],
                binary_sha256={name:compiler['binaries'][name]['sha256']
                               for name in ('cc', 'cxx', 'ld', 'readelf')}),
            compiler_banner=capture([*compile_commands['cc'], '--version']),
            runtime_rows=clang_runtime_rows(sysroot, runtime),
            sysroot_identity=sysroot_identity)
    require(family == 'gcc', 'Unsupported target compiler family: ' + str(family))
    require(host_prefix is None, '--host-prefix is only used for Clang target tests')
    tools = check_compilers(prefix, target)
    gcc_root = sysroot / 'usr/pkg/gcc16'
    require((gcc_root / 'lib/gcc' / triplet / VERSION / 'crtbegin.o').is_file() and
            (gcc_root / 'include/c++' / triplet).is_dir(),
            'Selected target GCC16 runtime missing')
    runtime_rows = []
    for role, name in (('libstdc++', 'libstdc++.so.7'), ('libgcc_s', 'libgcc_s.so.1')):
        path = (gcc_root / 'lib' / name).resolve(strict=True)
        require(paths.inside(path, gcc_root), 'Target runtime escapes sysroot GCC16 prefix')
        runtime_rows.append((role, '/' + path.relative_to(sysroot.resolve()).as_posix(), sha(path)))
    gcc_flags = ['--sysroot=' + str(sysroot), '-B' + str(gcc_root / 'lib/gcc' / triplet / VERSION) + '/',
                 '-L' + str(gcc_root / 'lib'), '-Wl,-rpath,/usr/pkg/gcc16/lib']
    cxx_flags = gcc_flags[:]
    for directory in ('', '/' + triplet, '/backward'):
        cxx_flags += ['-isystem', str(gcc_root / 'include/c++') + directory]
    cc, cxx = [str(tools['gcc'])] + gcc_flags, [str(tools['g++'])] + cxx_flags
    version_output = process.capture([tools['gcc'], '-v'], env=environment())
    return dict(family='gcc', cc=cc, cxx=cxx, cc_link=cc, cxx_link=cxx,
        identity=dict(format='emberbsd-target-test-compiler', version=1, family='gcc',
            triplet=triplet, compiler_version=VERSION,
            binary_sha256={name:inventory.sha256_file(Path(tools[name]).resolve(strict=True))
                           for name in ('gcc', 'g++', 'readelf')}),
        readelf=str(tools['readelf']),
        compiler_banner=(version_output.stdout + version_output.stderr).decode('utf-8', 'strict'),
        runtime_rows=runtime_rows, sysroot_identity=None)


def compile_test_options(args):
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument('--compiler-family', choices=('clang', 'gcc'), default='clang')
    parser.add_argument('--host-prefix')
    return parser.parse_known_args(args)


def compile_tests_main(args):
    options, args = compile_test_options(args)
    target, _, args = parse(args)
    require(len(args) == 3, 'Usage: compile-tests.py [--compiler-family clang|gcc] [--host-prefix PREFIX] [--target TARGET] PREFIX SYSROOT NEW_OUTPUT --sdk-source SOURCE')
    prefix, sysroot = [build_path(value) for value in args[:2]]
    out = new_path(args[2])
    selected = select_test_toolchain(options.compiler_family, prefix, sysroot, target,
                                     options.host_prefix)
    cc, cxx = selected['cc'], selected['cxx']
    cc_link, cxx_link = selected['cc_link'], selected['cxx_link']
    readelf, family = selected['readelf'], selected['family']
    runtime_rows, compiler_banner = selected['runtime_rows'], selected['compiler_banner']
    identity = selected['identity']
    out.mkdir()
    (out / 'target.txt').write_text(target + '\n')
    (out / 'compiler-family.txt').write_text(family + '\n')
    (out / 'runtime-files.tsv').write_text(''.join('\t'.join(row) + '\n' for row in runtime_rows))
    (out / 'compiler.txt').write_text(compiler_banner)
    jsonio.write_json(out / 'compiler-identity.json', identity)
    source = PROFILE / 'tests'
    sdk_root = Path(sdk_source.load())
    (out / 'source-sha256.tsv').write_text(''.join(
        path + '\t' + digest + '\n' for path, digest in
        target_test_source_inventory(PROFILE, HERE, sdk_root)))
    if selected['sysroot_identity'] is not None:
        jsonio.write_json(out / 'sysroot-identity.json', selected['sysroot_identity'])
    for suffix in ('', '-lto'):
        logged(cc_link + ['-std=c11', '-O2'] + (['-flto'] if suffix else []) + ['-Wall', '-Wextra', '-Werror', '-pthread', source / 'atomic-tls.c', '-o', out / ('atomic-tls' + suffix)], out / ('atomic-tls' + suffix + '-build.log'))
    programs = [('float-constexpr.o', cxx + ['-std=c++20', '-O3', '-Wall', '-Wextra', '-Werror', '-c', HERE / 'tests/float-constexpr.cc']), ('libboundary.so', cxx_link + ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared', source / 'boundary.cc', '-Wl,-soname,libboundary.so']), ('boundary', cxx_link + ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread', source / 'boundary-main.cc', '-L' + str(out), '-Wl,-rpath,$ORIGIN', '-lboundary'])]
    for name, arguments in programs:
        logged(arguments + ['-o', out / name], out / (name + '-build.log'))
    dynamic = capture([readelf, '-d', out / 'boundary', out / 'libboundary.so'])
    (out / 'dynamic.txt').write_text(dynamic)
    require(not any(('RPATH' in line or 'RUNPATH' in line or 'NEEDED' in line) and any(str(path) in line for path in (prefix, sysroot, out)) for line in dynamic.splitlines()), 'Host path leaked into target dynamic dependencies')
    for name in ('check-runtime.sh', 'target-options.sh'):
        shutil.copy2(HERE / 'tests/target' / name, out / name)
    shutil.copy2(HERE / 'tests/target/run-target.sh', out / 'run-target.sh')
    print('Cross-compiled ' + family + ' tests: ' + str(out) + '; compilation does not establish target execution acceptance')


def clang_runtime_rows(sysroot, runtime):
    """Bind the shared guest checker to artifact paths in the verified SDK runtime record."""
    rows = []
    for role in ('libcxx', 'libcxxabi', 'libunwind'):
        relative = runtime['artifacts'][role]['shared']
        path = (sysroot / relative).resolve(strict=True)
        require(paths.inside(path, sysroot), 'Clang runtime artifact escapes selected sysroot: ' + role)
        rows.append((role, '/' + path.relative_to(sysroot.resolve()).as_posix(), sha(path)))
    return rows


def clang_sysroot_identity(sysroot, target, runtime):
    """Record verified Clang runtime and build/import provenance, not acceptance."""
    build_path = sysroot / sysroot_transfer.RECEIPT
    import_path = sysroot / application_toolchain.IMPORT_RECORD
    require(not (build_path.is_file() and import_path.is_file()),
            'Ambiguous selected SDK sysroot provenance')
    if build_path.is_file():
        receipt_path = build_path
        receipt = jsonio.read_json(receipt_path)
        runtime_bundle = receipt.get('signature', {}).get('runtime')
        source = 'build-receipt'
        manifest_sha256 = None
    elif import_path.is_file():
        receipt_path = import_path
        receipt = jsonio.read_json(receipt_path)
        manifest = receipt.get('manifest')
        require(isinstance(manifest, dict), 'Invalid selected SDK import manifest')
        manifest_sha256 = receipt.get('manifest_sha256')
        require(sysroot_transfer._hash_json(manifest) == manifest_sha256,
                'Selected SDK import manifest digest changed')
        runtime_bundle = manifest.get('runtime')
        source = 'import-record'
    else:
        raise SDKError('Selected SDK sysroot record disappeared after runtime verification')
    require(isinstance(runtime_bundle, dict) and runtime_bundle.get('manifest') == runtime,
            'Selected SDK sysroot runtime record differs from API2 selection')
    return dict(format='emberbsd-target-test-sysroot-input', version=1,
        scope='verified-compiler-runtime-input', execution_acceptance='not-run', target=target,
        source_record=source, source_record_sha256=sha(receipt_path),
        portable_manifest_sha256=manifest_sha256,
        runtime_manifest_sha256=sysroot_transfer._hash_json(runtime),
        runtime_bundle_sha256=sysroot_transfer._hash_json(runtime_bundle))


def target_test_source_inventory(profile, cross, sdk_root):
    """Return deterministic hashes for test inputs and selected source controllers."""
    ports_root = profile.parents[1]
    explicit = [profile / 'tests/atomic-tls.c', profile / 'tests/boundary.cc',
        profile / 'tests/boundary-main.cc', profile / 'tests/boundary.h',
        cross / 'tests/float-constexpr.cc', cross / 'tests/target/run-target.sh',
        cross / 'tests/target/check-runtime.sh', cross / 'tests/target/target-options.sh']
    controller_python = [*profile.glob('*.py'), *cross.glob('*.py'),
                         *(profile / 'runtime/recipe/files').rglob('*.py')]
    sdk_python = sorted((sdk_root / 'src/emberbsd_sdk').rglob('*.py'))
    rows = []
    for path in sorted(set(explicit + controller_python)):
        rows.append(('ports/' + path.relative_to(ports_root).as_posix(), sha(path)))
    for path in sdk_python:
        rows.append(('sdk/' + path.relative_to(sdk_root).as_posix(), sha(path)))
    rows.sort(key=lambda row: row[0])
    require(len({row[0] for row in rows}) == len(rows), 'Duplicate target-test source inventory path')
    return rows


def check_runtime_main(args):
    require(len(args) == 2, 'Usage: check-runtime.py PREFIX OUTPUT --sdk-source SOURCE')
    prefix = Path(args[0]).resolve(strict=True)
    output = Path(args[1])
    loaded = [line.split() for line in (output / 'loaded.txt').read_text().splitlines()]
    family = (output / 'compiler-family.txt').read_text().strip()
    expected_roles = {'clang': ('libcxx', 'libcxxabi', 'libunwind'),
                      'gcc': ('libstdc++', 'libgcc_s')}
    require(family in expected_roles, 'Invalid compiler family receipt')
    rows = [line.split('\t') for line in (output / 'runtime-files.tsv').read_text().splitlines()]
    require(all(len(row) == 3 and re.fullmatch(r'[0-9a-f]{64}', row[2]) for row in rows),
            'Invalid target runtime file receipt')
    require(len(rows) == len(expected_roles[family]) and
            {row[0] for row in rows} == set(expected_roles[family]),
            'Target runtime receipt has missing or duplicate roles')
    for role, guest_path, expected in rows:
        marker = '/usr/pkg/llvm/' if family == 'clang' else '/usr/pkg/gcc16/'
        require(guest_path.startswith(marker), 'Target runtime path escapes selected prefix: ' + guest_path)
        relative = guest_path[len(marker):]
        actual = (prefix / relative).resolve(strict=True)
        require(paths.inside(actual, prefix), 'Runtime outside selected compiler prefix')
        require(sha(actual) == expected, 'Host runtime SHA256 differs from compile receipt: ' + role)
        files = []
        target_root = prefix.parents[2]
        for row in loaded:
            if len(row) != 2 or row[0] != 'LOADED' or not row[1].startswith('/'):
                continue
            try:
                loaded_file = (target_root / row[1].lstrip('/')).resolve(strict=True)
            except OSError:
                continue
            if paths.inside(loaded_file, target_root) and loaded_file == actual:
                files.append(row[1])
        require(len(files) == 1, 'Expected one loaded target runtime: ' + role)


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
