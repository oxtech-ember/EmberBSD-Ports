#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Bind the Electron recipe's prepared source to selected SDK tools and GN/Ninja."""
import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_sdk(root):
    root = Path(root).resolve(strict=True)
    package = root / 'src/emberbsd_sdk'
    sys.path.insert(0, str(package.parent))
    result = {}
    for name in ('', 'host_prefix', 'application_toolchain', 'target_toolchain', 'targets',
                 'process', 'paths', 'darwin_sdk', 'compiler_bindings'):
        module = importlib.import_module('emberbsd_sdk' + ('.' + name if name else ''))
        require(Path(module.__file__).resolve() == package / ((name or '__init__') + '.py'),
                'SDK module origin differs: ' + module.__name__)
        result[name] = module
    for name, field, version in (('', 'API_VERSION', 1), ('host_prefix', 'HOST_PREFIX_API', 2),
                                 ('application_toolchain', 'APPLICATION_TOOLCHAIN_API', 2),
                                 ('darwin_sdk', 'DARWIN_SDK_API', 1)):
        require(getattr(result[name], field, None) == version, 'unsupported SDK contract: ' + field)
    return result


def absolute(value, label, *, directory=True):
    path = Path(value)
    require(path.is_absolute(), label + ' must be absolute')
    path = path.resolve(strict=True)
    require(path.is_dir() if directory else path.is_file(), label + ' has the wrong file type')
    return path


def gn_value(value):
    if type(value) is bool:
        return 'true' if value else 'false'
    if type(value) is int:
        return str(value)
    if isinstance(value, list):
        return '[ ' + ', '.join(gn_value(item) for item in value) + ' ]'
    require(isinstance(value, str) and not any(ord(c) < 32 for c in value), 'invalid GN string')
    return json.dumps(value, ensure_ascii=False).replace('$', r'\$')


def verify_source(workspace, ports, git):
    source = local_module('electron_build_source', 'prepare-build-sources.py')
    record = json.loads((workspace / 'source-inputs/ports-build-sources.json').read_text())
    rows = source.read_series(Path(__file__).with_name('source-series.json'), ports / 'probes/electron/patches')
    expected = [{key: row[key] for key in ('path', 'root', 'strip', 'sha256')} for row in rows]
    require(record.get('version') == 1 and record.get('patches') == expected,
            'prepare sources with the current complete ordered recipe series')
    for name, revision in record['source_revisions'].items():
        repository = workspace / source.bsd.relative(name)
        require(repository.resolve(strict=True) == repository, 'source repository path changed: ' + name)
        require(source.bsd.git_bytes(git, repository, 'rev-parse', 'HEAD').decode().strip() == revision,
                'prepared source HEAD changed: ' + name)
    for name, row in record['paths'].items():
        path, data = source.current_file(workspace / 'src', name)
        require(source.digest(data) == row['after'], 'prepared source bytes changed: ' + name)
    return record


def prepare(options):
    source = local_module('electron_build_source', 'prepare-build-sources.py')
    result = source.prepare(options.workspace, options.pkgsrc, options.archive, options.destination,
                            options.git, options.patch, options.ports_source / 'probes/electron/patches',
                            Path(__file__).with_name('source-series.json'))
    return source.materialize(options.workspace, options.destination, result, git=options.git)



def selected_control_git(path):
    git = Path(path).resolve(strict=True)
    require(git.is_file() and os.access(git, os.X_OK), 'selected Git is not executable')
    return str(git)

def native_inputs(options, sdk):
    roles = ('python', 'gn', 'ninja', 'node', 'rustc', 'rustfmt', 'bindgen', 'wayland-scanner',
             'pkg-config', 'rollup', 'tsc', 'clang', 'cc', 'cxx', 'cpp', 'ar', 'nm', 'strip', 'objcopy', 'readelf',
             'sh', 'env', 'sed', 'touch', 'cp')
    if sys.platform == 'darwin':
        roles += ('dsymutil',)
    native = sdk['host_prefix'].load_host_prefix(options.host_prefix, required_roles=roles,
                                                compiler_family=options.host_compiler_family)
    require(Path(sys.executable).resolve() == Path(native.tool('python')).resolve(),
            'run the build controller with the selected host-prefix Python')
    environment = sdk['process'].sanitized_environment()
    # Git is a control input for source metadata, not a build-tool fallback.
    control_git = selected_control_git(options.git)
    environment.update(PATH=native.path, EMBERBSD_CONTROL_GIT=control_git, PYTHONDONTWRITEBYTECODE='1',
                       EMBERBSD_HOST_NODE=native.tool('node'),
                       CLANG_PATH=native.tool('clang'), RUSTFMT=native.tool('rustfmt'),
                       LIBCLANG_PATH=str(options.host_prefix / 'lib'))
    providers = local_module('electron_node_providers', 'node-providers.py').select(native)
    environment.update(providers['environment'])
    if native.host['os'] == 'Darwin':
        require(options.macos_sdk and options.xcode_version_plist and options.macos_minimum,
                'Darwin requires explicit SDK, Xcode version plist and deployment version')
        require(re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,2}', options.macos_minimum),
                'invalid Darwin deployment version')
        metadata = sdk['darwin_sdk'].read_metadata(str(options.macos_sdk),
                    xcode_version_plist=str(options.xcode_version_plist))
        environment['SDKROOT'] = metadata['sdk_path']
        environment['MACOSX_DEPLOYMENT_TARGET'] = options.macos_minimum
    return native, environment



def prefer_chromium_libcxx_headers(cxx):
    """Keep Chromium's libc++ headers ahead of SDK and compiler headers."""
    out = []
    i = 0
    while i < len(cxx):
        if cxx[i] == '-nostdinc++':
            i += 1
            continue
        if cxx[i] == '-isystem' and i + 1 < len(cxx):
            nxt = cxx[i + 1]
            if '/include/c++/v1' in nxt or re.search(r'/lib/clang/[^/]+/include$', nxt):
                i += 2
                continue
        out.append(cxx[i])
        i += 1
    require(out != cxx, 'bound cxx lacked SDK/resource header flags to drop for custom libc++')
    return out


def bind_versioned(sdk, native, parent, record):
    """Publish immutable adapters whose path changes with their complete inputs."""
    identity = dict(record=record, python=str(Path(native.tool('python')).resolve()),
                    sdk_module=str(Path(sdk['compiler_bindings'].__file__).resolve()),
                    sdk_module_sha256=hashlib.sha256(Path(sdk['compiler_bindings'].__file__).read_bytes()).hexdigest())
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    parent.mkdir(parents=True, exist_ok=True)
    return sdk['compiler_bindings'].bind_compilers(str(parent / digest), commands=record['commands'],
        flags=record['flags'], link_flags=record['link_flags'], python=native.tool('python'))


def binding_identity(record):
    """Compare compiler, target and runtime identity, allowing command flags to evolve."""
    selected = {}
    for role in ('cc', 'cxx', 'cpp'):
        words = record['commands'][role]
        require(words and Path(words[0]).is_absolute(), 'invalid selected compiler')
        selected[role] = [words[0]]
        for prefix in ('--target=', '--sysroot=', '-resource-dir='):
            matches = [word for word in words if word.startswith(prefix)]
            require(len(matches) == 1, 'missing or ambiguous compiler identity: ' + prefix)
            selected[role].append(matches[0])
    for role in ('cc', 'cxx'):
        words = record['link_flags'][role]
        selected[role + '_runtime'] = []
        for prefix in ('--ld-path=', '--rtlib=', '--unwindlib=') + (('-stdlib=',) if role == 'cxx' else ()):
            matches = [word for word in words if word.startswith(prefix)]
            require(len(matches) == 1, 'missing or ambiguous runtime identity: ' + prefix)
            selected[role + '_runtime'].append(matches[0])
    return selected


def saved_binding_directory(work, environment):
    cc = shlex.split(environment['CC'])
    cxx = shlex.split(environment['CXX'])
    require(len(cc) == len(cxx) == 1, 'saved compiler bindings are not executable paths')
    c, x = Path(cc[0]), Path(cxx[0])
    root = (work / 'target-commands').resolve(strict=True)
    require(c.name == 'cc' and x.name == 'cxx' and c.parent == x.parent and
            c.parent.resolve(strict=True).is_relative_to(root), 'saved compiler bindings escape work')
    return c.parent


def target_inputs(options, sdk, native, environment, work):
    target = sdk['targets'].target_definition(options.target)
    if options.compiler_family == 'clang':
        compiler = sdk['target_toolchain'].clang_compiler(str(options.compiler_prefix), target['triplet'],
                                                         host=native.host, env=environment)
        runtime = sdk['application_toolchain'].load_clang_runtime(str(options.sysroot), target=options.target)
        commands = sdk['application_toolchain'].clang_application_commands(compiler, str(options.sysroot), runtime)
        commands = {role: commands[role] for role in ('cc', 'cxx', 'cpp')}
        commands['cxx'] = prefer_chromium_libcxx_headers(commands['cxx'])
        links = {role: sdk['application_toolchain'].clang_application_link_flags(
            compiler, str(options.sysroot), runtime, language=language)
            for role, language in (('cc', 'c'), ('cxx', 'c++'))}
        record = dict(format='emberbsd-compiler-binding', version=1, commands=commands,
                      flags={name: [] for name in ('cppflags', 'cflags', 'cxxflags', 'ldflags')},
                      aliases={}, link_flags=links)
        bound = bind_versioned(sdk, native, work / 'target-commands', record)
        binaries = {role: row['selected_path'] for role, row in compiler['binaries'].items()}
        return dict(binaries, cc=bound['cc'], cxx=bound['cxx'], cpp=bound['cpp'])
    # An explicit rare-platform GCC profile consumes the existing common owner.
    # No error in the Clang route reaches this branch.
    require(options.gcc_os_tools and options.gcc_platform_reason,
            'GCC needs an explicit platform reason and OS tools input')
    owner = options.ports_source / 'profiles/common-build-tools/cross/prepare-tools.py'
    output = work / 'target-gcc-tools'
    sdk['process'].run_logged([native.tool('python'), '-B', '-S', str(owner),
        '--sdk-source', str(options.sdk_source), '--compiler-family', 'gcc',
        '--host-compiler-family', options.host_compiler_family, '--target', options.target,
        str(options.compiler_prefix), str(options.gcc_os_tools), str(output)],
        str(work / 'gcc-tools.log'), env=environment)
    names = dict(cc='gcc', cxx='g++', cpp='cpp', ar='ar', nm='nm', strip='strip',
                 objcopy='objcopy', readelf='readelf')
    return {role: str(output / 'bin' / (target['triplet'] + '-' + name)) for role, name in names.items()}


def arguments(options, native, tools, rust_version, launcher):
    cpu = {'amd64': 'x64', 'aarch64': 'arm64'}[options.target]
    host_cpu = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'x64', 'amd64': 'x64'}.get(native.host['cpu'])
    require(host_cpu is not None, 'unsupported GN host CPU: ' + native.host['cpu'])
    values = dict(target_os='netbsd', target_cpu=cpu, is_clang=options.compiler_family == 'clang',
        custom_toolchain='//build/toolchain/linux/unbundle:default',
        unbundle_host_is_clang=options.host_compiler_family == 'clang',
        use_sysroot=True, target_sysroot=str(options.sysroot), emberbsd_target_sysroot=str(options.sysroot),
        clang_base_path=str(options.host_prefix), clang_use_chrome_plugins=False,
        use_custom_libcxx=True, use_custom_libcxx_for_host=False, use_custom_libunwind=False,
        use_lld=options.compiler_family == 'clang', use_thin_lto=False,
        rust_sysroot_absolute=str(options.host_prefix), rust_bindgen_root=str(options.host_prefix),
        rustc_version=rust_version, emberbsd_rust_unstable_features=True, wayland_scanner_executable=native.tool('wayland-scanner'),
        emberbsd_target_strip=tools['strip'], emberbsd_target_objcopy=tools['objcopy'],
        pkg_config=native.tool('pkg-config'), host_pkg_config=native.tool('pkg-config'),
        unbundle_linker_launcher=launcher, concurrent_links=1,
        is_debug=False, is_component_build=False,
        # These profiles describe upstream OS/compiler binaries. NetBSD's
        # separately selected compiler/runtime has no matching PGO profile.
        chrome_pgo_phase=0, v8_builtins_profiling_log_file='',
        # PipeWire/portal needs libpipewire + GBM/EGL not in clang-final yet;
        # WebRTC default is is_linux && use_sysroot. Disable until Mesa/pipewire land.
        rtc_use_pipewire=False,
        # WebRTC X11 desktop capture needs libXfixes/Xdamage/Xtst/Xcomposite,
        # which clang-final does not provide yet.
        rtc_use_x11_extensions=False,
        # VA-API (media/gpu/chromeos, vaapi) needs libva headers/libs, which
        # clang-final does not provide yet; Chromium defaults it on for x64.
        use_vaapi=False)
    if native.host['os'] == 'Darwin':
        family = options.host_compiler_family
        values.update(host_toolchain='//build/toolchain/mac:' + family + '_' + host_cpu,
            v8_snapshot_toolchain='//build/toolchain/mac:' + family + '_' + host_cpu + '_v8_' + cpu,
            emberbsd_sdk_source=str(options.sdk_source),
            emberbsd_xcode_version_plist=str(options.xcode_version_plist),
            emberbsd_mac_toolchain_bin=str(options.host_prefix / 'bin'),
            mac_sdk_path=str(options.macos_sdk), mac_deployment_target=options.macos_minimum,
            apple_linker_launcher=launcher)
        if family == 'gcc':
            values.update(mac_gcc_cc=native.tool('cc'), mac_gcc_cxx=native.tool('cxx'),
                          mac_gcc_llvm_bin_path=str(options.host_prefix / 'bin'))
    elif native.host['os'] in ('Linux', 'NetBSD'):
        values['host_toolchain'] = '//build/toolchain/linux/unbundle:host'
    else:
        raise ValueError('unsupported GN host OS: ' + native.host['os'])
    values.update(local_module('electron_node_providers', 'node-providers.py').select(native)['arguments'])
    return values


def producer_inputs(options, sdk):
    native, environment = native_inputs(options, sdk)
    tools = target_inputs(options, sdk, native, environment, options.work)
    for role in ('cc', 'cxx', 'ar', 'nm', 'readelf'):
        environment[role.upper()] = shlex.quote(tools[role])
    for role in ('cc', 'cxx', 'ar', 'nm'):
        environment['BUILD_' + role.upper()] = shlex.quote(native.tool(role))
    if options.compiler_family == 'gcc':
        for name in ('CFLAGS', 'CXXFLAGS', 'ASFLAGS', 'LDFLAGS'):
            environment[name] = shlex.join(['--sysroot=' + str(options.sysroot)])
    verbose_rust = sdk['process'].capture([native.tool('rustc'), '-vV'], env=environment).stdout.decode()
    environment, rust = local_module('electron_rust_policy', 'rust-policy.py').apply(environment, verbose_rust)
    launcher = shlex.join([native.tool('python'), str(options.sdk_source / 'scripts/link-launcher.py'),
                          '--lock-root', str(options.lock_root), '--context', str(options.link_context), '--'])
    values = arguments(options, native, tools, rust, launcher)
    return native, environment, values


def gn_arguments(values):
    return 'import("//electron/build/args/release.gn")\n' + ''.join(
        name + ' = ' + gn_value(value) + '\n' for name, value in sorted(values.items()))





def require_rust_std(host_prefix, target):
    """Use the target component installed by the shared Rust package."""
    triplet = {'amd64': 'x86_64-unknown-netbsd', 'aarch64': 'aarch64-unknown-netbsd'}[target]
    dest = Path(host_prefix) / 'lib/rustlib' / triplet / 'lib'
    require(dest.is_dir() and any(dest.glob('libstd-*.rlib')) and any(dest.glob('libcore-*.rlib')),
            'target Rust std missing; install the shared pkgsrc lang/rust-std-' + triplet.split('-')[0] + '-netbsd package')


def ensure_allocator_shim_throw_netbsd(workspace):
    """NetBSD/BSD: empty __THROW for libc malloc; noexcept __THROW in cpp_symbols."""
    shim = (workspace / 'src/base/allocator/partition_allocator/src/partition_alloc'
            / 'shim')
    path = shim / 'allocator_shim_internals.h'
    require(path.is_file(), 'allocator_shim_internals.h missing')
    text = path.read_text()
    needle = '#ifndef __THROW   // Not a glibc system'
    idx = text.find(needle)
    require(idx >= 0, 'allocator_shim_internals.h __THROW block missing')
    window = text[idx:idx + 450]
    # PA buildflags are linux-shaped for this target; gate on compiler predefines.
    stale = '#if defined(_NOEXCEPT) && !PA_BUILDFLAG(IS_NETBSD) && !PA_BUILDFLAG(IS_BSD)\n'
    if stale in window:
        text = text.replace(stale, '#if defined(_NOEXCEPT) && !defined(__NetBSD__) && !defined(__FreeBSD__) && !defined(__OpenBSD__)\n', 1)
        path.write_text(text)
        window = text[idx:idx + 450]
    if '!defined(__NetBSD__)' not in window:
        old = (
            '#ifndef __THROW   // Not a glibc system\n'
            '#ifdef _NOEXCEPT  // LLVM libc++ uses noexcept instead\n'
            '#define __THROW _NOEXCEPT\n'
            '#else\n'
            '#define __THROW\n'
            '#endif  // !_NOEXCEPT\n'
            '#endif'
        )
        new = (
            '#ifndef __THROW   // Not a glibc system\n'
            '// NetBSD/BSD libc headers declare malloc family without exception specs;\n'
            '// mapping __THROW to _NOEXCEPT then mismatches those decls under clang.\n'
            '#if defined(_NOEXCEPT) && !defined(__NetBSD__) && !defined(__FreeBSD__) && !defined(__OpenBSD__)\n'
            '#define __THROW _NOEXCEPT\n'
            '#else\n'
            '#define __THROW\n'
            '#endif  // !_NOEXCEPT || BSD/NetBSD\n'
            '#endif'
        )
        require(old in text, 'allocator_shim_internals.h __THROW block not recognized')
        path.write_text(text.replace(old, new, 1))

    # cpp_symbols: a header-level "#define __THROW noexcept" leaks into
    # allocator_shim_override_libc_symbols.h (included next by allocator_shim.cc)
    # and breaks libc malloc decls. Strip any such block; the C++ overrides get a
    # literal noexcept from ensure_allocator_shim_cpp_noexcept instead.
    cpp = shim / 'allocator_shim_override_cpp_symbols.h'
    require(cpp.is_file(), 'allocator_shim_override_cpp_symbols.h missing')
    ctext = cpp.read_text()
    block = (
        '\n'
        '// EmberBSD/NetBSD: libc malloc must keep empty __THROW (see internals.h),\n'
        '// but libc++ operator new/delete decls use noexcept \u2014 remap for this header.\n'
        '#if PA_BUILDFLAG(IS_NETBSD) || PA_BUILDFLAG(IS_BSD)\n'
        '#undef __THROW\n'
        '#define __THROW noexcept\n'
        '#endif\n'
    )
    if block in ctext:
        cpp.write_text(ctext.replace(block, '', 1))


def ensure_allocator_shim_cpp_noexcept(workspace):
    """libc++ declares replaceable operator new/delete noexcept; with __THROW empty on
    BSD (see ensure_allocator_shim_throw_netbsd) the C++ shim overrides lose it."""
    path = (workspace / 'src/base/allocator/partition_allocator/src/partition_alloc'
            / 'shim' / 'allocator_shim_override_cpp_symbols.h')
    require(path.is_file(), 'allocator_shim_override_cpp_symbols.h missing')
    text = path.read_text()
    if ') __THROW {' not in text:
        return
    path.write_text(text.replace(') __THROW {', ') noexcept {'))



def ensure_bindgen_dyld_fallback(workspace):
    """run_bindgen sets DYLD_LIBRARY_PATH to the host LLVM lib dir, which makes
    /usr/lib/libiconv.2.dylib (needed by libxml2) resolve to GNU libiconv lacking
    _iconv, so libclang fails to dlopen. Use DYLD_FALLBACK_LIBRARY_PATH instead."""
    path = workspace / 'src/build/rust/gni_impl/run_bindgen.py'
    require(path.is_file(), 'run_bindgen.py missing')
    text = path.read_text()
    old = 'env["DYLD_LIBRARY_PATH"] = args.ld_library_path'
    if old in text:
        path.write_text(text.replace(old, 'env["DYLD_FALLBACK_LIBRARY_PATH"] = args.ld_library_path', 1))


def ensure_host_dsymutil(workspace, native):
    """Bind Chromium's macOS tool path to the selected native-prefix tool."""
    if native.host['os'] != 'Darwin':
        return
    src = Path(native.tool('dsymutil')).resolve(strict=True)
    dest = workspace / 'src/tools/clang/dsymutil/bin/dsymutil'
    if dest.exists() or dest.is_symlink():
        require(dest.resolve(strict=True) == src, 'existing dsymutil differs from selected native tool')
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(src)


def ensure_rollup_darwin_arm64(workspace, host_prefix, environment):
    """Yarn may omit optional @rollup/rollup-darwin-arm64; fabricate from host rollup.darwin-arm64.node."""
    import json, shutil
    electron = workspace / 'src/electron'
    nm = electron / 'node_modules' / '@rollup' / 'rollup-darwin-arm64'
    marker = nm / 'rollup.darwin-arm64.node'
    if marker.is_file():
        return
    host_node = Path(host_prefix) / 'lib' / 'node_modules' / 'rollup' / 'dist' / 'rollup.darwin-arm64.node'
    host_pkg = Path(host_prefix) / 'lib' / 'node_modules' / '@rollup' / 'rollup-darwin-arm64'
    if host_pkg.is_dir():
        nm.parent.mkdir(parents=True, exist_ok=True)
        if nm.exists():
            shutil.rmtree(nm)
        shutil.copytree(host_pkg, nm)
        return
    require(host_node.is_file(), 'host rollup.darwin-arm64.node missing for @rollup/rollup-darwin-arm64')
    ver = '4.60.4'
    pkg_json = Path(host_prefix) / 'lib' / 'node_modules' / 'rollup' / 'package.json'
    if pkg_json.is_file():
        ver = json.loads(pkg_json.read_text()).get('version') or ver
    if nm.exists():
        shutil.rmtree(nm)
    nm.mkdir(parents=True)
    shutil.copy2(host_node, marker)
    (nm / 'package.json').write_text(json.dumps({
        'name': '@rollup/rollup-darwin-arm64',
        'version': ver,
        'os': ['darwin'],
        'cpu': ['arm64'],
        'main': 'rollup.darwin-arm64.node',
    }, indent=2) + "\n")


def ensure_ffmpeg_netbsd_config(workspace):
    """DEPS ffmpeg-copy-config-netbsd only teaches copy_config.sh; config trees are not generated here.
    Reuse linux configs for netbsd (same approach as fuchsia/chromeos -> linux in ffmpeg_options.gni).

    Linux copies set HAVE_GETAUXVAL=1, but NetBSD has neither getauxval(3) nor
    <sys/auxv.h>. Clear the flag in every netbsd config.h/config.asm so
    libavutil/cpu.c skips the Linux auxv include (x86 still uses CPUID)."""
    import shutil
    root = workspace / 'src/third_party/ffmpeg/chromium/config'
    if not root.is_dir():
        return
    for brand in sorted(p for p in root.iterdir() if p.is_dir()):
        linux = brand / 'linux'
        netbsd = brand / 'netbsd'
        if not linux.is_dir():
            continue
        if not netbsd.is_dir():
            shutil.copytree(linux, netbsd)
        for cfg in netbsd.rglob('*'):
            if cfg.name not in ('config.h', 'config.asm'):
                continue
            text = cfg.read_text()
            fixed = (text
                     .replace('#define HAVE_GETAUXVAL 1', '#define HAVE_GETAUXVAL 0')
                     .replace('%define HAVE_GETAUXVAL 1', '%define HAVE_GETAUXVAL 0'))
            if fixed != text:
                cfg.write_text(fixed)
    require((root / 'Chrome/netbsd/x64/config.asm').is_file() or not (root / 'Chrome/linux/x64/config.asm').is_file(),
            'ffmpeg Chrome/netbsd/x64/config.asm missing after linux copy')


def ensure_lastchange(workspace, native, environment, sdk):
    """Mirror DEPS lastchange / lastchange_dawn / lastchange_skia / gpu_lists_version (gclient hooks not run)."""
    script = workspace / 'src/build/util/lastchange.py'
    output = workspace / 'src/build/util/LASTCHANGE'
    require(script.is_file(), 'Chromium lastchange.py missing from prepared source')
    python = native.tool('python')
    run = lambda args: sdk['process'].capture([python, '-B', str(script), *args],
                                              cwd=str(workspace), env=environment)
    run(['-o', str(output)])
    stamp = Path(str(output) + '.committime')
    require(stamp.is_file() and stamp.read_text().strip().isdigit(),
            'lastchange did not write LASTCHANGE.committime')
    # lastchange_dawn
    dawn_rev = workspace / 'src/gpu/webgpu/DAWN_VERSION'
    dawn_hdr = workspace / 'src/gpu/webgpu/dawn_commit_hash.h'
    require((workspace / 'src/third_party/dawn').is_dir(), 'third_party/dawn missing for lastchange_dawn')
    run(['-m', 'DAWN_COMMIT_HASH', '-s', str(workspace / 'src/third_party/dawn'),
         '--revision', str(dawn_rev), '--header', str(dawn_hdr)])
    require(dawn_rev.is_file() and dawn_rev.read_text().strip(),
            'lastchange_dawn did not write gpu/webgpu/DAWN_VERSION')
    require(dawn_hdr.is_file() and 'DAWN_COMMIT_HASH' in dawn_hdr.read_text(),
            'lastchange_dawn did not write gpu/webgpu/dawn_commit_hash.h')
    # lastchange_skia
    skia_hdr = workspace / 'src/skia/ext/skia_commit_hash.h'
    require((workspace / 'src/third_party/skia').is_dir(), 'third_party/skia missing for lastchange_skia')
    run(['-m', 'SKIA_COMMIT_HASH', '-s', str(workspace / 'src/third_party/skia'),
         '--header', str(skia_hdr)])
    require(skia_hdr.is_file() and 'SKIA_COMMIT_HASH' in skia_hdr.read_text(),
            'lastchange_skia did not write skia/ext/skia_commit_hash.h')
    # gpu_lists_version
    gpu_hdr = workspace / 'src/gpu/config/gpu_lists_version.h'
    run(['-m', 'GPU_LISTS_VERSION', '--revision-id-only', '--header', str(gpu_hdr)])
    require(gpu_hdr.is_file() and 'GPU_LISTS_VERSION' in gpu_hdr.read_text(),
            'gpu_lists_version did not write gpu/config/gpu_lists_version.h')


def configure(options):
    sdk = load_sdk(options.sdk_source)
    verify_source(options.workspace, options.ports_source, options.git)
    work = options.work
    require(not work.exists(), 'configure output must be new; retain an unsuccessful output for diagnosis')
    work.mkdir()
    native, environment, values = producer_inputs(options, sdk)
    ensure_lastchange(options.workspace, native, environment, sdk)
    ensure_ffmpeg_netbsd_config(options.workspace)
    ensure_host_dsymutil(options.workspace, native)
    ensure_rollup_darwin_arm64(options.workspace, options.host_prefix, environment)
    require_rust_std(options.host_prefix, options.target)
    ensure_allocator_shim_throw_netbsd(options.workspace)
    ensure_bindgen_dyld_fallback(options.workspace)
    ensure_allocator_shim_cpp_noexcept(options.workspace)
    output = work / 'out'; output.mkdir()
    (output / 'args.gn').write_text(gn_arguments(values))
    sdk['process'].run_logged([native.tool('gn'), 'gen', str(output),
        '--script-executable=' + native.tool('python'), '--ninja-executable=' + native.tool('ninja'),
        '--root-target=//electron', '--root-pattern=//electron:electron_dist_zip', '--fail-on-unused-args'],
        str(work / 'configure.log'), cwd=str(options.workspace / 'src'), env=environment)
    # This is the actual producer invocation, not a qualification record.
    local_module('electron_build_source', 'prepare-build-sources.py').atomic_json(work / 'configuration.json',
        dict(arguments=values, environment=environment, source=str(options.workspace),
             sdk=str(options.sdk_source), host_prefix=str(options.host_prefix), target=options.target))



def reconfigure(options):
    """Regenerate an existing GN graph while preserving its toolchain identity."""
    sdk = load_sdk(options.sdk_source)
    verify_source(options.workspace, options.ports_source, options.git)
    work = options.work
    output = work / 'out'
    saved = json.loads((work / 'configuration.json').read_text())
    require(saved['source'] == str(options.workspace) and saved['sdk'] == str(options.sdk_source) and
            saved['host_prefix'] == str(options.host_prefix) and saved['target'] == options.target,
            'reconfigure inputs differ from configuration')
    require(options.compiler_family == 'clang', 'reconfigure currently supports Clang bindings only')
    require((output / 'build.ninja').is_file(), 'existing GN graph is missing')
    old_args = gn_arguments(saved['arguments'])
    require((work / 'reconfigure-incomplete').exists() or
            (output / 'args.gn').read_text() == old_args, 'configured GN arguments changed')
    old_directory = saved_binding_directory(work, saved['environment'])
    old_commands = json.loads((old_directory / 'commands.json').read_text())

    # Resolve and bind into a separate scratch directory, so a mismatch never
    # mutates the existing bindings or graph. Their contents are compared below.
    with tempfile.TemporaryDirectory(prefix='electron-reconfigure-') as scratch:
        candidate = argparse.Namespace(**vars(options))
        candidate.work = Path(scratch)
        native, environment, values = producer_inputs(candidate, sdk)
        new_directory = saved_binding_directory(candidate.work, environment)
        new_commands = json.loads((new_directory / 'commands.json').read_text())
        require(binding_identity(new_commands) == binding_identity(old_commands),
                'target compiler, sysroot or runtime changed')
        # Provider paths are read from the environment by actions; Ninja does
        # not fingerprint those values in old graphs. Refuse to reuse such a
        # graph across a provider change until actions track that selection.
        permitted_env = {'CC', 'CXX',
                         'HOME', 'TMPDIR', 'TMP', 'TEMP', 'USER', 'LOGNAME'}
        old_env = saved['environment']
        # Migrate exactly the old control-Git PATH, never arbitrary tool paths.
        control_git = selected_control_git(options.git)
        require(environment.get('EMBERBSD_CONTROL_GIT') == control_git,
                'selected control Git changed')
        require(environment.get('PATH') == native.path, 'build PATH is not prefix-only')
        if 'EMBERBSD_CONTROL_GIT' not in old_env:
            require(old_env.get('PATH') == native.path + os.pathsep + str(Path(control_git).parent),
                    'old build PATH is not the selected Git migration')
        else:
            require(old_env.get('EMBERBSD_CONTROL_GIT') == control_git and old_env.get('PATH') == native.path,
                    'control Git or build PATH changed')
        permitted_env.update(('PATH', 'EMBERBSD_CONTROL_GIT'))
        for name in (set(environment) | set(old_env)) - permitted_env:
            require(environment.get(name) == old_env.get(name), 'producer input changed: ' + name)
        identity_args = {'target_os', 'target_cpu', 'target_sysroot', 'emberbsd_target_sysroot',
                         'is_clang', 'unbundle_host_is_clang', 'clang_base_path', 'host_toolchain',
                         'custom_toolchain', 'v8_snapshot_toolchain', 'emberbsd_mac_toolchain_bin',
                         'emberbsd_sdk_source', 'mac_sdk_path', 'mac_deployment_target',
                         'apple_linker_launcher', 'unbundle_linker_launcher', 'concurrent_links',
                         'rust_sysroot_absolute', 'rust_bindgen_root', 'rustc_version',
                         'use_custom_libcxx', 'use_custom_libcxx_for_host', 'use_custom_libunwind',
                         'use_lld', 'emberbsd_target_strip', 'emberbsd_target_objcopy'}
        for name in identity_args:
            require(values.get(name) == saved['arguments'].get(name), 'GN identity changed: ' + name)

        # Preserve previous bindings. The final path appears in GN/Ninja command
        # lines so a changed record forces the corresponding commands to rerun.
        bound = bind_versioned(sdk, native, work / 'target-commands', new_commands)
        environment['CC'] = shlex.quote(bound['cc'])
        environment['CXX'] = shlex.quote(bound['cxx'])

        # A failed or interrupted GN run may leave a partial graph. The marker
        # prevents build until a later successful reconfigure repairs it.
        marker = work / 'reconfigure-incomplete'
        marker.write_text('GN reconfiguration incomplete\n')
        try:
            (output / 'args.gn').write_text(gn_arguments(values))
            sdk['process'].run_logged([native.tool('gn'), 'gen', str(output),
                '--script-executable=' + native.tool('python'), '--ninja-executable=' + native.tool('ninja'),
                '--root-target=//electron', '--root-pattern=//electron:electron_dist_zip', '--fail-on-unused-args'],
                str(work / 'reconfigure.log'), cwd=str(options.workspace / 'src'), env=environment)
            local_module('electron_build_source', 'prepare-build-sources.py').atomic_json(
                work / 'configuration.json',
                dict(arguments=values, environment=environment, source=str(options.workspace),
                     sdk=str(options.sdk_source), host_prefix=str(options.host_prefix), target=options.target))
        except BaseException:
            (output / 'args.gn').write_text(old_args)
            raise
        marker.unlink()

def build(options):
    require(not (options.work / 'reconfigure-incomplete').exists(),
            'incomplete reconfiguration; rerun reconfigure before build')
    sdk = load_sdk(options.sdk_source)
    verify_source(options.workspace, options.ports_source, options.git)
    native, environment, values = producer_inputs(options, sdk)
    ensure_lastchange(options.workspace, native, environment, sdk)
    ensure_ffmpeg_netbsd_config(options.workspace)
    ensure_host_dsymutil(options.workspace, native)
    ensure_rollup_darwin_arm64(options.workspace, options.host_prefix, environment)
    require_rust_std(options.host_prefix, options.target)
    ensure_allocator_shim_throw_netbsd(options.workspace)
    ensure_bindgen_dyld_fallback(options.workspace)
    ensure_allocator_shim_cpp_noexcept(options.workspace)
    saved = json.loads((options.work / 'configuration.json').read_text())
    require(saved['source'] == str(options.workspace) and saved['sdk'] == str(options.sdk_source) and
            saved['host_prefix'] == str(options.host_prefix) and saved['target'] == options.target,
            'build inputs differ from configuration')
    require(options.jobs > 0, 'Ninja job count must be positive')
    saved_env = saved['environment']
    for name in set(environment) | set(saved_env):
        if name not in ('HOME', 'TMPDIR', 'TMP', 'TEMP', 'USER', 'LOGNAME'):
            require(saved_env.get(name) == environment.get(name), 'producer input changed: ' + name)
    require(saved['arguments'] == values, 'GN selection changed; configure a new output')
    output = options.work / 'out'
    require((output / 'args.gn').read_text() == gn_arguments(values), 'configured GN arguments changed')
    sdk['process'].run_logged([native.tool('ninja'), '-C', str(output), '-j', str(options.jobs),
                              'electron_dist_zip'], str(options.work / 'build.log'),
                             cwd=str(options.workspace / 'src'), env=saved_env,
                             append=(options.work / 'build.log').exists())
    archive = output / 'dist.zip'
    require(archive.is_file(), 'Electron producer did not create dist.zip')
    with archive.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    stage = local_module('electron_runtime_stage', 'stage-runtime.py')
    stage.stage_runtime(str(archive), str(options.work / 'runtime'), archive_sha256=digest,
                        target=options.target, sdk=stage.load_sdk(options.sdk_source))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='phase', required=True)
    source = sub.add_parser('prepare')
    for name in ('workspace', 'ports-source', 'pkgsrc', 'archive', 'destination', 'git', 'patch'):
        source.add_argument('--' + name, type=Path, required=True)
    for phase in ('configure', 'reconfigure', 'build'):
        command = sub.add_parser(phase)
        for name in ('workspace', 'ports-source', 'sdk-source', 'host-prefix', 'compiler-prefix',
                     'sysroot', 'work', 'git', 'lock-root', 'link-context'):
            command.add_argument('--' + name, type=Path, required=True)
        command.add_argument('--target', choices=('amd64', 'aarch64'), required=True)
        command.add_argument('--compiler-family', choices=('clang', 'gcc'), default='clang')
        command.add_argument('--host-compiler-family', choices=('clang', 'gcc'), default='clang')
        for name in ('macos-sdk', 'xcode-version-plist', 'gcc-os-tools'):
            command.add_argument('--' + name, type=Path)
        command.add_argument('--macos-minimum')
        command.add_argument('--gcc-platform-reason')
        command.add_argument('--jobs', type=int, default=1)
    options = parser.parse_args()
    try:
        for name, value in vars(options).items():
            if isinstance(value, Path):
                require(value.is_absolute(), '--' + name.replace('_', '-') + ' must be absolute')
        if options.phase == 'prepare':
            print('Materialized source files:', prepare(options))
        else:
            sdk = load_sdk(options.sdk_source)
            with sdk['process'].ContextLocks([str(options.workspace), str(options.work)], str(options.lock_root)):
                {'configure': configure, 'reconfigure': reconfigure, 'build': build}[options.phase](options)
    except Exception as error:
        parser.exit(1, 'Electron ' + options.phase + ' failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
