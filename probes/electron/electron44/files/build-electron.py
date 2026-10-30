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
    for name in ('', 'host_prefix', 'application_toolchain', 'target_toolchain', 'targets', 'llvm_runtime',
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
    expected = [source.series_record(row) for row in rows]
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
             'sh', 'env', 'sed', 'touch', 'cp', 'objdump')
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
                       EMBERBSD_HOST_PYTHON=native.tool('python'),
                       npm_config_script_shell=native.tool('sh'),
                       CLANG_PATH=native.tool('clang'), RUSTFMT=native.tool('rustfmt'),
                       LIBCLANG_PATH=str(options.host_prefix / 'lib'))
    providers = local_module('electron_node_providers', 'node-providers.py').select(native, electron=True)
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
    runtime = record.get('native_cxx_runtime', {})
    if runtime:
        runtime_files = {'config': Path(runtime['include_dir']) / '__config_site',
                         'dylib': Path(runtime['library_dir']) / 'libc++_ember1.1.dylib'}
        identity['native_runtime_files'] = {
            name: dict(path=str(path.resolve(strict=True)),
                       sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            for name, path in runtime_files.items()}
    if runtime.get('platform_cxxabi') is True:
        require(getattr(sdk['compiler_bindings'], 'NATIVE_CXX_PLATFORM_ABI_API', 0) == 1,
                'selected SDK lacks native platform C++ ABI API 1')
        header_root = Path(runtime['sysroot']) / 'usr/include/c++/v1'
        identity['platform_cxxabi_headers'] = {
            name: dict(path=str((header_root / name).resolve(strict=True)),
                       sha256=hashlib.sha256((header_root / name).read_bytes()).hexdigest())
            for name in ('cxxabi.h', '__cxxabi_config.h')}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    parent.mkdir(parents=True, exist_ok=True)
    extra = {}
    if 'native_cxx_runtime' in record:
        require(getattr(sdk['compiler_bindings'], 'NATIVE_CXX_RUNTIME_BINDING_API', 0) == 1,
                'selected SDK lacks native C++ runtime binding API 1')
        extra['native_cxx_runtime'] = record['native_cxx_runtime']
    return sdk['compiler_bindings'].bind_compilers(str(parent / digest), commands=record['commands'],
        flags=record['flags'], link_flags=record['link_flags'], python=native.tool('python'), **extra)


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
    selected['cxx_includes'] = [words for words in record['commands']['cxx']
                                if 'include/c++/v1' in words]
    selected['runtime_library_search'] = [word for word in record['link_flags']['cxx']
                                         if word.startswith('-L')]
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


def select_target_runtime(options, sdk):
    stage = getattr(options, 'target_runtime_stage', None)
    base = getattr(options, 'target_runtime_base', None)
    require(not base or stage, 'runtime base requires a runtime stage')
    if stage:
        base = Path(base or options.sysroot).resolve(strict=True)
        runtime = sdk['llvm_runtime'].validate_stage(
            str(stage), target=options.target,
            required_components=sdk['llvm_runtime'].FULL_COMPONENTS, base=str(base))
    else:
        runtime = sdk['application_toolchain'].load_clang_runtime(str(options.sysroot), target=options.target)
    return stage, base, runtime


def target_inputs(options, sdk, native, environment, work):
    target = sdk['targets'].target_definition(options.target)
    if options.compiler_family == 'clang':
        compiler = sdk['target_toolchain'].clang_compiler(str(options.compiler_prefix), target['triplet'],
                                                         host=native.host, env=environment)
        stage, base, runtime = select_target_runtime(options, sdk)
        runtime_root = str(stage) if stage else None
        commands = sdk['application_toolchain'].clang_application_commands(compiler, str(options.sysroot),
                                                                            runtime, runtime_root=runtime_root)
        commands = {role: commands[role] for role in ('cc', 'cxx', 'cpp')}
        if not (getattr(options, 'host_runtime_root', None) and stage):
            commands['cxx'] = prefer_chromium_libcxx_headers(commands['cxx'])
        links = {role: sdk['application_toolchain'].clang_application_link_flags(
            compiler, str(options.sysroot), runtime, runtime_root=runtime_root, language=language)
            for role, language in (('cc', 'c'), ('cxx', 'c++'))}
        record = dict(format='emberbsd-compiler-binding', version=1, commands=commands,
                      flags={name: [] for name in ('cppflags', 'cflags', 'cxxflags', 'ldflags')},
                      aliases={}, link_flags=links)
        stage_sha256 = None
        if stage:
            with (Path(stage) / 'runtime.json').open('rb') as handle:
                stage_sha256 = hashlib.file_digest(handle, 'sha256').hexdigest()
        bound = bind_versioned(sdk, native, work / 'target-commands', record)
        binaries = {role: row['selected_path'] for role, row in compiler['binaries'].items()}
        return dict(binaries, cc=bound['cc'], cxx=bound['cxx'], cpp=bound['cpp'],
                    runtime_stage_sha256=stage_sha256,
                    runtime_base=str(Path(base or options.sysroot).resolve(strict=True)) if stage else None)
    # An explicit rare-platform GCC profile consumes the existing common owner.
    # No error in the Clang route reaches this branch.
    require(not getattr(options, 'target_runtime_stage', None) and not getattr(options, 'target_runtime_base', None),
            'runtime stage and base require Clang')
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
        use_custom_libcxx=not bool(getattr(options, 'host_runtime_root', None) and
                                   getattr(options, 'target_runtime_stage', None)),
        use_custom_libcxx_for_host=False, use_custom_libunwind=False,
        use_lld=options.compiler_family == 'clang', use_thin_lto=False,
        use_system_libdrm=True,
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
    values.update(emberbsd_electron_node=native.tool('node'),
                  emberbsd_electron_version_provider=str(Path(__file__).with_name('electron-version-provider.py').resolve()),
                  emberbsd_electron_provider_selector=str(Path(__file__).with_name('node-providers.py').resolve()),
                  emberbsd_electron_sdk_source=str(options.sdk_source),
                  emberbsd_electron_host_prefix=str(options.host_prefix))
    values.update(local_module('electron_node_providers', 'node-providers.py').select(native, electron=True)['arguments'])
    return values


def clang_resource_version(prefix, resource_text):
    require(resource_text and "\n" not in resource_text, 'invalid selected Clang resource directory')
    prefix = Path(prefix).resolve(strict=True)
    require(Path(resource_text).is_absolute(), 'selected Clang resource path must be absolute')
    resource = Path(resource_text).resolve(strict=True)
    require(re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', resource.name) is not None,
            'invalid selected Clang resource version')
    expected = (prefix / 'lib' / 'clang' / resource.name).resolve(strict=True)
    require(resource == expected and resource.is_relative_to(prefix) and (resource / 'include').is_dir(),
            'selected Clang resource does not match host prefix')
    return resource.name


def hardening_header(root, relative, namespace):
    config = Path(root) / relative / '__config_site'
    text = config.read_text()
    require(re.search(r'(?m)^\s*#\s*define\s+_LIBCPP_ABI_NAMESPACE\s+' +
                      re.escape(namespace) + r'\s*$', text) and
            re.search(r'(?m)^\s*#\s*define\s+_LIBCPP_HARDENING_MODE_DEFAULT\s+16\s*$', text),
            'selected libc++ headers do not provide the required ABI and hardening')


def native_runtime_binding(options, sdk, native, environment, target_tools):
    """Bind the selected native pair and probe both toolchain headers."""
    selected = getattr(options, 'host_runtime_root', None)
    stage = getattr(options, 'target_runtime_stage', None)
    if not selected and not stage:
        return None
    require(selected and stage and native.host['os'] == 'Darwin' and
            options.host_compiler_family == 'clang',
            'external hardened libc++ requires both native and target runtime selections')
    root = absolute(selected, 'native runtime root')
    hardening_header(root, 'include/libc++/v1', '__ember1')
    hardening_header(stage, 'usr/pkg/llvm/include/c++/v1', '__1')
    include = root / 'include/libc++/v1'
    library = root / 'lib/libc++'
    dylib = library / 'libc++_ember1.1.dylib'
    require(dylib.is_file(), 'selected native libc++ is missing')
    runtime_files = options.ports_source / 'pkgsrc/lang/compiler-rt/files'
    sys.path.insert(0, str(runtime_files))
    spec = importlib.util.spec_from_file_location('electron_native_libcxx', runtime_files / 'native.py')
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    producer.owner.load_sdk(['--sdk-source', str(options.sdk_source)])
    load_commands = sdk['process'].capture([native.tool('objdump'), '--macho', '--private-headers',
                                            str(dylib)], env=environment).stdout.decode('utf-8', 'strict')
    producer.validate_darwin_load_commands(load_commands, options.host_prefix)
    triplet = sdk['process'].capture([native.tool('clang'), '-dumpmachine'], env=environment).stdout.decode().strip()
    cpu = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'x86_64', 'amd64': 'x86_64'}.get(native.host['cpu'])
    require(cpu is not None, 'unsupported native libc++ CPU')
    require(getattr(sdk['compiler_bindings'], 'NATIVE_CXX_ABI_IDENTITY_API', 0) == 1,
            'selected SDK lacks native C++ ABI identity API 1')
    config = dict(include_dir=str(include), library_dir=str(library), sysroot=str(options.macos_sdk),
                  targets=[triplet, cpu + '-apple-macos'], deployment=options.macos_minimum,
                  platform_cxxabi=True,
                  abi_identity={'namespace': '__ember1', 'linker_target': 'libc++_ember1.1.dylib'})
    record = dict(commands={role: list(native.command(role)) for role in ('cc', 'cxx', 'cpp')},
                  flags={name: list(flags) for name, flags in native.abi_flags.items()},
                  link_flags={'cc': [], 'cxx': []}, native_cxx_runtime=config)
    record['flags']['cxxflags'].append('-stdlib=libc++')
    parent = getattr(options, 'native_binding_root', options.work)
    bound = bind_versioned(sdk, native, parent / 'native-commands', record)
    with tempfile.TemporaryDirectory(prefix='electron-libcxx-probe-') as directory:
        source = Path(directory) / 'probe.cc'
        source.write_text('#include <__config>\n'
            '#if !defined(_LIBCPP_VERSION) || _LIBCPP_HARDENING_MODE_DEFAULT != _LIBCPP_HARDENING_MODE_EXTENSIVE\n'
            '#error selected libc++ is not extensively hardened\n#endif\n'
            '#define EMBER_ABI___ember1 1\n#define EMBER_ABI___1 2\n'
            '#define EMBER_ABI_CAT_(x) EMBER_ABI_##x\n#define EMBER_ABI_CAT(x) EMBER_ABI_CAT_(x)\n'
            '#if EMBER_ABI_CAT(_LIBCPP_ABI_NAMESPACE) != EMBER_EXPECT_ABI\n'
            '#error selected libc++ has the wrong ABI namespace\n#endif\nint main() { return 0; }\n')
        host_flags = ['--target=' + cpu + '-apple-macos', '-isysroot', str(options.macos_sdk),
                      '-mmacos-version-min=' + options.macos_minimum, '-stdlib=libc++']
        for command, expected in (([bound['cxx'], *host_flags], '1'),
                                  ([target_tools['cxx'], '-stdlib=libc++'], '2')):
            sdk['process'].capture(command + ['-DEMBER_EXPECT_ABI=' + expected, '-std=c++23',
                                               '-fsyntax-only', str(source)], env=environment)
    return bound



def host_buildlink(options, sdk, native, environment, host_binding):
    fields = ('host_buildlink_pkgsrc', 'host_buildlink_stage_root',
              'host_buildlink_base_makeconf', 'host_buildlink_bmake_mk')
    selected = [getattr(options, name, None) for name in fields]
    if not any(selected):
        return None
    require(all(selected) and host_binding, 'native host buildlink needs its four inputs and native C++ binding')
    root = getattr(options, 'native_binding_root', options.work)
    config = root / 'configuration.json'
    saved = json.loads(config.read_text()) if config.is_file() else {}
    previous = saved.get('environment', {}).get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK')
    script = Path(__file__).with_name('host-buildlink.py')
    record = Path(host_binding['cxx']).parent / 'commands.json'
    def command(work):
        return [native.tool('python'), '-B', str(script), '--sdk-source', str(options.sdk_source),
                '--pkgsrc-root', str(selected[0]), '--host-prefix', str(options.host_prefix),
                '--stage-root', str(selected[1]), '--base-makeconf', str(selected[2]),
                '--binding-record', str(record), '--bmake-mk', str(selected[3]),
                '--work', str(work), '--lock-root', str(options.lock_root)]
    if previous:
        previous = Path(previous)
        require(previous.parent == root and previous.name.startswith('host-buildlink-'),
                'saved host buildlink work is outside the Electron output')
        try:
            result = sdk['process'].capture(command(previous) + ['--check'], env=environment)
            environment['EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'] = str(previous)
            return result.stdout.decode('utf-8', 'strict').strip()
        except sdk['process'].CommandError as error:
            if error.returncode != 3:
                raise
            require(getattr(options, 'phase', None) != 'build',
                    'host buildlink changed; reconfigure before building')
    for index in range(10000):
        work = root / ('host-buildlink-' + str(index))
        if not os.path.lexists(work):
            break
    else:
        raise ValueError('too many retained host buildlink contexts')
    require(getattr(options, 'phase', None) != 'build', 'host buildlink requires configuration')
    result = sdk['process'].capture(command(work), env=environment)
    environment['EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'] = str(work)
    return result.stdout.decode('utf-8', 'strict').strip()


def protobuf_package_source(package, owner_recipe, export_recipe, *, distinfo, package_path="devel/protobuf"):
    """Compare the package's existing pkgsrc source metadata with its owner."""
    def inventory(recipe):
        patches = recipe / 'patches'
        require(patches.is_dir(), 'common protobuf patch inventory is missing')
        files = sorted(patches.glob('patch-*'))
        require(files, 'common protobuf patch inventory is empty')
        return {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in files}
    expected = inventory(owner_recipe)
    require(inventory(export_recipe) == expected, 'selected pkgsrc protobuf patch inventory differs from common owner')
    owner_dist = hashlib.sha256((owner_recipe / 'distinfo').read_bytes()).hexdigest()
    export_dist = hashlib.sha256((export_recipe / 'distinfo').read_bytes()).hexdigest()
    require(owner_dist == export_dist, 'selected pkgsrc protobuf distinfo differs from common owner')
    metadata = {}
    for line in (package / '+BUILD_VERSION').read_text().splitlines():
        name, separator, digest = line.partition(': ')
        require(separator and name not in metadata, 'invalid protobuf package source metadata')
        metadata[name] = digest
    prefix = package_path + '/patches/'
    actual = {name[len(prefix):]: digest for name, digest in metadata.items() if name.startswith(prefix)}
    require(actual == expected, 'selected protobuf package patch inventory differs from common source')
    if distinfo:
        require(metadata.get(package_path + '/distinfo') == owner_dist,
                'selected protobuf package distinfo differs from common source')


def common_protobuf(options, sdk, native, environment, buildlink, runtime_view):
    common = getattr(options, 'protobuf_source', None)
    common_inputs = (getattr(options, 'protobuf_ports_source', None),
                     getattr(options, 'protobuf_archive', None),
                     getattr(options, 'protobuf_patch', None))
    require(bool(common) == all(bool(item) for item in common_inputs),
            'common protobuf needs the source, owner, archive and patch inputs together')
    require(common or not any(common_inputs), 'incomplete common protobuf source selection')
    if common:
        require(buildlink and runtime_view, 'common protobuf requires the native buildlink and scoped runtime view')
        owner = Path(common_inputs[0]) / 'scripts/source-inputs/protobuf/source.py'
        require(owner.is_file(), 'common protobuf source owner is missing')
        verified = sdk['process'].capture([native.tool('python'), '-B', str(owner), '--sdk-source', str(options.sdk_source),
            '--git', selected_control_git(options.git), 'verify-source', '--source', str(common),
            '--archive', str(common_inputs[1]), '--patch', str(common_inputs[2])], env=environment)
        source_identity = json.loads(verified.stdout.decode('utf-8', 'strict'))
        environment['EMBERBSD_PROTOBUF_SOURCE_SHA256'] = hashlib.sha256(
            json.dumps(source_identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        version_data = json.loads((Path(common) / 'version.json').read_text())
        versions = {row['protoc_version'] for row in version_data.values()}
        require(len(versions) == 1, 'ambiguous common protobuf source version')
        def normalized_version(value):
            require(re.fullmatch(r'[0-9]+(?:\.[0-9]+)+', value) is not None,
                    'invalid protobuf version')
            parts = [int(part) for part in value.split('.')]
            while len(parts) > 1 and parts[-1] == 0:
                parts.pop()
            return parts
        source_version = normalized_version(versions.pop())
        for prefix, native_pc in ((Path(buildlink), True), (options.sysroot / 'usr/pkg', False)):
            pcenv = dict(environment, PKG_CONFIG_LIBDIR=str(prefix / 'lib/pkgconfig'))
            pcenv.pop('PKG_CONFIG_PATH', None); pcenv.pop('PKG_CONFIG_SYSROOT_DIR', None)
            command = [native.tool('pkg-config')]
            if native_pc:
                command.append('--define-prefix')
            version = sdk['process'].capture(command + ['--modversion', 'protobuf'], env=pcenv).stdout.decode().strip()
            require(normalized_version(version) == source_version,
                    'selected protobuf package version differs from the common source')
        protoc = (Path(buildlink) / 'bin/protoc').resolve(strict=True)
        require(protoc.is_file() and os.access(protoc, os.X_OK), 'selected host protoc is missing')
        selection_work = environment.get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK')
        require(selection_work, 'selected protobuf needs actual host buildlink metadata')
        selected = json.loads((Path(selection_work) / 'selection.json').read_text())['identity']['inputs']
        host_packages = []
        for filename in selected:
            info = Path(filename)
            if info.name == '+BUILD_INFO' and 'PKGPATH=devel/protobuf' in info.read_text().splitlines():
                host_packages.append(info.resolve(strict=True).parent)
        require(len(host_packages) == 1, 'selected host protobuf package metadata is ambiguous')
        host_package = host_packages[0]
        host_prefix = host_package.parent.parent
        require(protoc.is_relative_to(host_prefix), 'selected protoc is outside its host package prefix')
        require(str(protoc.relative_to(host_prefix)) in (host_package / '+CONTENTS').read_text().splitlines(),
                'selected protoc is not owned by the selected host protobuf package')
        owner_recipe = Path(common_inputs[0]) / 'pkgsrc/devel/protobuf'
        export_recipe = Path(options.host_buildlink_pkgsrc) / 'devel/protobuf'
        protobuf_package_source(host_package, owner_recipe, export_recipe, distinfo=True)
        target_db = options.sysroot / 'usr/pkg/pkgdb'
        pkg_info = options.host_prefix / 'sbin/pkg_info'
        for name, content, needs_distinfo in (('protobuf', 'lib/libprotobuf.so', True),
                                              ('protobuf-devel', 'include/google/protobuf/message.h', False)):
            result = sdk['process'].capture([str(pkg_info), '-K', str(target_db), '-E',
                                              name + '>=' + '.'.join(str(part) for part in source_version)],
                                             env=environment).stdout.decode().strip().splitlines()
            require(len(result) == 1 and '/' not in result[0], 'selected target protobuf package is missing or ambiguous')
            package = target_db / result[0]
            require('PKGPATH=devel/' + name in (package / '+BUILD_INFO').read_text().splitlines(),
                    'selected target protobuf package has a different source owner')
            require(content in (package / '+CONTENTS').read_text().splitlines(),
                    'selected target protobuf package does not own ' + content)
            protobuf_package_source(package, owner_recipe, export_recipe, distinfo=needs_distinfo)
        version_output = sdk['process'].capture(
            [native.tool('python'), str(options.sdk_source / 'scripts/run-darwin-with-runtime.py'),
             '--runtime-view', str(runtime_view), '--', str(protoc), '--version'],
            env=environment).stdout.decode('utf-8', 'strict').strip()
        match = re.fullmatch(r'libprotoc ([0-9]+(?:\.[0-9]+)+)', version_output)
        require(match and normalized_version(match.group(1)) == source_version,
                'selected host protoc version differs from the common source')
        return dict(emberbsd_common_protobuf=True, emberbsd_protobuf_native_prefix=buildlink,
                    emberbsd_protobuf_target_prefix=str(options.sysroot / 'usr/pkg'),
                    emberbsd_protoc=str(protoc))
    return {}


def common_undici(options, sdk, environment):
    if not getattr(options, 'shared_undici', False):
        return {}
    target_db = options.sysroot / 'usr/pkg/pkgdb'
    pkg_info = options.host_prefix / 'sbin/pkg_info'
    result = sdk['process'].capture([str(pkg_info), '-K', str(target_db), '-E', 'undici>=0'],
                                     env=environment).stdout.decode().strip().splitlines()
    require(len(result) == 1 and '/' not in result[0],
            'selected target Undici package is missing or ambiguous')
    package = target_db / result[0]
    info = (package / '+BUILD_INFO').read_text().splitlines()
    require('PKGPATH=www/undici' in info and 'EMBERBSD_UNDICI_RUNTIME_PREFIX=/usr/pkg' in info,
            'selected target Undici package has a different owner or runtime prefix')
    recipe_root = getattr(options, 'host_buildlink_pkgsrc', None)
    require(recipe_root, 'shared Undici requires the selected common pkgsrc export')
    recipe = Path(recipe_root) / 'www/undici'
    metadata = {}
    for line in (package / '+BUILD_VERSION').read_text().splitlines():
        name, separator, digest = line.partition(': ')
        require(separator and name not in metadata, 'invalid Undici package source metadata')
        metadata[name] = digest
    for name in ('Makefile', 'distinfo', 'files/generate-wasm.py'):
        source = recipe / name
        require(source.is_file() and metadata.get('www/undici/' + name) ==
                hashlib.sha256(source.read_bytes()).hexdigest(),
                'selected Undici package source differs from the common recipe: ' + name)
    relative = Path('lib/node_modules/undici/loader.js')
    contents = (package / '+CONTENTS').read_text().splitlines()
    matches = [index for index, line in enumerate(contents) if line == str(relative)]
    require(len(matches) == 1 and matches[0] + 1 < len(contents),
            'selected target Undici package does not uniquely own its loader')
    checksum = re.fullmatch(r'@comment MD5:([0-9a-f]{32})', contents[matches[0] + 1])
    require(checksum, 'selected target Undici loader package checksum is missing')
    loader = options.sysroot / 'usr/pkg' / relative
    require(loader.is_file() and loader.resolve(strict=True).is_relative_to(options.sysroot.resolve(strict=True)),
            'selected target Undici loader is missing or outside the sysroot')
    data = loader.read_bytes()
    require(hashlib.md5(data, usedforsecurity=False).hexdigest() == checksum.group(1),
            'selected target Undici loader differs from package metadata')
    logical = str(Path('/usr/pkg') / relative)
    require(('createRequire("' + logical + '")').encode() in data and
            str(options.host_prefix).encode() not in data and str(options.sysroot).encode() not in data,
            'selected target Undici loader has an incorrect runtime path')
    return dict(node_shared_undici_path=logical, node_shared_undici_input=str(loader))


NODE_SHARED_FEATURES = ('ada', 'brotli', 'cares', 'ffi', 'hdr_histogram', 'http_parser',
                        'libuv', 'merve', 'nbytes', 'nghttp2', 'simdjson', 'sqlite',
                        'uvwasi', 'zstd')


def common_embedder_sources(options, sdk, native, environment):
    node = getattr(options, 'node_source', None)
    node_export = getattr(options, 'node_pkgsrc', None)
    require(bool(node) == bool(node_export), 'common Node needs source and pkgsrc export together')
    perfetto = getattr(options, 'perfetto_source', None)
    perfetto_owner = getattr(options, 'perfetto_ports_source', None)
    perfetto_archive = getattr(options, 'perfetto_archive', None)
    perfetto_patch = getattr(options, 'perfetto_patch', None)
    inputs = (perfetto_owner, perfetto_archive, perfetto_patch)
    require(bool(perfetto) == all(bool(item) for item in inputs),
            'common Perfetto needs source, owner, archive and patch together')
    require(perfetto or not any(inputs), 'incomplete common Perfetto selection')
    v8 = getattr(options, 'v8_source', None)
    v8_owner = getattr(options, 'v8_ports_source', None)
    v8_export = getattr(options, 'v8_pkgsrc', None)
    require(bool(v8) == bool(v8_owner and v8_export),
            'common V8 needs source, owner and pkgsrc export together')
    require(v8 or not (v8_owner or v8_export), 'incomplete common V8 selection')
    values = {}
    commands = []
    if v8:
        owner = v8_owner / 'scripts/source-inputs/v8/source.py'
        require(owner.is_file(), 'common V8 source owner is missing')
        commands.append(('V8', [native.tool('python'), '-B', str(owner), '--sdk-source', str(options.sdk_source),
                                'verify-source', '--source', str(v8), '--pkgsrc-root', str(v8_export)]))
    if node:
        owner = options.ports_source / 'scripts/source-inputs/node/source.py'
        require(owner.is_file(), 'common Node source owner is missing')
        commands.append(('NODE', [native.tool('python'), '-B', str(owner), '--sdk-source', str(options.sdk_source),
                                  'verify-source', '--source', str(node), '--pkgsrc-root', str(node_export)]))
        values.update(node_path='//third_party/electron_node',
                      node_config_gn_root_target='//electron',
                      node_config_gn_root_pattern='//electron:electron_dist_zip')
        for feature in NODE_SHARED_FEATURES:
            values['node_shared_' + feature] = True
        values.update(node_simdutf_include_from_target=True, use_system_simdutf=True, node_use_ffi=True)
    if perfetto:
        owner = perfetto_owner / 'scripts/source-inputs/perfetto/source.py'
        require(owner.is_file(), 'common Perfetto source owner is missing')
        commands.append(('PERFETTO', [native.tool('python'), '-B', str(owner), '--sdk-source', str(options.sdk_source),
                                      '--git', selected_control_git(options.git), 'verify-source', '--source', str(perfetto),
                                      '--archive', str(perfetto_archive), '--patch', str(perfetto_patch)]))
    if node and perfetto:
        values['node_shared_perfetto'] = True
    for name, command in commands:
        result = sdk['process'].capture(command, env=environment)
        record = json.loads(result.stdout.decode('utf-8', 'strict'))
        environment['EMBERBSD_' + name + '_SOURCE_SHA256'] = hashlib.sha256(
            json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return values




def common_abseil(options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_abseil', False):
        return {}
    require(buildlink, 'shared Abseil requires the selected native buildlink')
    versions = []
    for prefix, host in ((Path(buildlink), True), (options.sysroot / 'usr/pkg', False)):
        env = dict(environment, PKG_CONFIG_LIBDIR=str(prefix / 'lib/pkgconfig'))
        env.pop('PKG_CONFIG_PATH', None)
        env.pop('PKG_CONFIG_SYSROOT_DIR', None)
        command = [native.tool('pkg-config')]
        if host:
            command.append('--define-prefix')
        version = sdk['process'].capture(command + ['--modversion', 'absl_base'], env=env).stdout.decode().strip()
        require(version, 'selected Abseil package has no version')
        versions.append(version)
    require(versions[0] == versions[1], 'host and target Abseil versions differ')
    selection_work = environment.get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK')
    require(selection_work, 'shared Abseil needs host buildlink metadata')
    selection = json.loads((Path(selection_work) / 'selection.json').read_text())['identity']['inputs']
    host_packages = [Path(name).resolve(strict=True).parent for name in selection
                     if Path(name).name == '+BUILD_INFO' and
                     'PKGPATH=devel/abseil' in Path(name).read_text().splitlines()]
    target_db = options.sysroot / 'usr/pkg/pkgdb'
    target_packages = [path for path in target_db.iterdir() if (path / '+BUILD_INFO').is_file() and
                       'PKGPATH=devel/abseil' in (path / '+BUILD_INFO').read_text().splitlines()]
    require(len(host_packages) == len(target_packages) == 1, 'ambiguous selected Abseil packages')
    owner = options.ports_source / 'pkgsrc/devel/abseil'
    export = options.host_buildlink_pkgsrc / 'devel/abseil'
    for package in host_packages + target_packages:
        protobuf_package_source(package, owner, export, distinfo=True, package_path='devel/abseil')
    source_records = [hashlib.sha256((path / '+BUILD_VERSION').read_bytes()).hexdigest()
                      for path in host_packages + target_packages]
    environment['EMBERBSD_SHARED_ABSEIL_VERSION'] = versions[0]
    environment['EMBERBSD_SHARED_ABSEIL_SOURCE_SHA256'] = ':'.join(source_records)
    values = {}
    for role, package, prefix in (('host', host_packages[0], Path(buildlink)),
                                  ('target', target_packages[0], options.sysroot / 'usr/pkg')):
        result = sdk['process'].capture([str(options.host_prefix / 'sbin/pkg_info'), '-K', str(package.parent),
                                         '-qL', package.name], env=environment).stdout.decode('utf-8', 'strict')
        headers = []
        for line in result.splitlines():
            marker = '/include/absl/'
            if marker not in line:
                continue
            relative = Path('absl') / line.split(marker, 1)[1]
            require(not relative.is_absolute() and '..' not in relative.parts and
                    re.fullmatch(r'absl/[A-Za-z0-9_./+-]+', str(relative)) is not None,
                    'unsafe Abseil package path')
            headers.append(relative)
        require(headers and len(headers) == len(set(headers)), 'invalid Abseil include inventory')
        headers.sort()
        files = [(prefix / 'include' / path).resolve(strict=True) for path in headers]
        require(all(path.is_file() for path in files), 'selected Abseil include is missing')
        values['emberbsd_abseil_' + role + '_headers'] = [str(path) for path in headers]
        values['emberbsd_abseil_' + role + '_inputs'] = sorted(set(str(path) for path in files) |
            {str((package / '+CONTENTS').resolve(strict=True)), str((package / '+BUILD_INFO').resolve(strict=True)),
             str((package / '+BUILD_VERSION').resolve(strict=True))})
    return values



def common_icu(options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_icu', False):
        return {}
    require(buildlink, 'shared ICU requires the selected native buildlink')
    versions = []
    for prefix, host in ((Path(buildlink), True), (options.sysroot / 'usr/pkg', False)):
        env = dict(environment, PKG_CONFIG_LIBDIR=str(prefix / 'lib/pkgconfig'))
        env.pop('PKG_CONFIG_PATH', None)
        env.pop('PKG_CONFIG_SYSROOT_DIR', None)
        command = [native.tool('pkg-config')]
        if host:
            command.append('--define-prefix')
        for module in ('icu-uc', 'icu-i18n'):
            version = sdk['process'].capture(command + ['--modversion', module], env=env).stdout.decode().strip()
            require(version, 'selected ICU package has no version')
            versions.append(version)
    require(len(set(versions)) == 1, 'selected ICU package versions differ')
    selection_work = environment.get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK')
    require(selection_work, 'shared ICU needs host buildlink metadata')
    selection = json.loads((Path(selection_work) / 'selection.json').read_text())['identity']['inputs']
    host_packages = [Path(name).resolve(strict=True).parent for name in selection
                     if Path(name).name == '+BUILD_INFO' and
                     'PKGPATH=textproc/icu' in Path(name).read_text().splitlines()]
    db = options.sysroot / 'usr/pkg/pkgdb'
    def target_package(pkgpath):
        found = [path for path in db.iterdir() if (path / '+BUILD_INFO').is_file() and
                 ('PKGPATH=' + pkgpath) in (path / '+BUILD_INFO').read_text().splitlines()]
        require(len(found) == 1, 'ambiguous selected target ICU package: ' + pkgpath)
        return found[0]
    require(len(host_packages) == 1, 'ambiguous selected host ICU package')
    packages = host_packages + [target_package('textproc/icu'), target_package('textproc/icu-devel')]
    owner = options.ports_source / 'pkgsrc/textproc/icu'
    export = options.host_buildlink_pkgsrc / 'textproc/icu'
    for index, package in enumerate(packages):
        protobuf_package_source(package, owner, export, distinfo=index != 2, package_path='textproc/icu')
    records = [hashlib.sha256((path / '+BUILD_VERSION').read_bytes()).hexdigest() for path in packages]
    environment['EMBERBSD_SHARED_ICU_VERSION'] = versions[0]
    environment['EMBERBSD_SHARED_ICU_SOURCE_SHA256'] = ':'.join(records)
    return {'icu_use_data_file': False}


def common_v8_metagen(options, sdk, native, environment, tools):
    selected = (getattr(options, 'v8_metagen_libclang_so', None),
                getattr(options, 'v8_metagen_bindings_dir', None),
                getattr(options, 'v8_metagen_runtime_view', None))
    if not any(selected):
        return {}
    require(all(selected) and options.v8_source and options.host_runtime_root,
            'V8 metagen requires common V8, selected libclang, bindings and runtime view')
    require(options.compiler_family == 'clang' and native.host['os'] == 'Darwin',
            'V8 metagen scoped selection requires Darwin and target Clang')
    prefix = options.host_runtime_root.resolve(strict=True)
    libclang = absolute(selected[0], 'V8 metagen libclang', directory=False)
    bindings = absolute(selected[1], 'V8 metagen bindings')
    view = absolute(selected[2], 'V8 metagen runtime view')
    files = [libclang, bindings / 'clang/cindex.py', bindings / 'clang/__init__.py']
    packages = []
    for path, pkgpath in zip(files, ('lang/clang', 'lang/clang-python-bindings',
                                     'lang/clang-python-bindings')):
        require(path.is_file() and path.resolve(strict=True).is_relative_to(prefix),
                'V8 metagen input is absent or outside selected host stage')
        relative = str(path.relative_to(prefix))
        matches = [entry for entry in (prefix / 'pkgdb').iterdir()
                   if (entry / '+BUILD_INFO').is_file() and
                   ('PKGPATH=' + pkgpath) in (entry / '+BUILD_INFO').read_text().splitlines() and
                   (entry / '+CONTENTS').is_file() and
                   relative in (entry / '+CONTENTS').read_text().splitlines()]
        require(len(matches) == 1, 'V8 metagen file has no unique selected package owner: ' + relative)
        packages.append(matches[0])
    require(packages[1] == packages[2], 'V8 metagen Python bindings have different owners')
    script = options.sdk_source / 'scripts/run-darwin-with-runtime.py'
    result = sdk['process'].capture([native.tool('python'), '-B', str(script), '--print-inputs'],
                                    env=environment).stdout.decode('utf-8', 'strict')
    inputs = json.loads(result)
    require(isinstance(inputs, list) and inputs and
            all(isinstance(item, str) and Path(item).is_absolute() and Path(item).is_file()
                for item in inputs), 'invalid SDK runtime launcher inputs')
    require(':' not in str(view), 'V8 metagen runtime view cannot contain a colon')
    entries = sorted(view.iterdir())
    require(entries and all(item.is_file() for item in entries), 'invalid V8 metagen runtime view')
    resolved = [item.resolve(strict=True) for item in entries]
    require(all(item.is_relative_to(prefix) for item in resolved),
            'V8 metagen runtime view points outside selected host stage')
    actual = [str(item) for item in resolved]
    record = json.loads((Path(tools['cxx']).parent / 'commands.json').read_text())
    host_cxx = shlex.split(environment['BUILD_CXX'])
    require(len(host_cxx) == 1, 'invalid host C++ binding')
    host_record = json.loads((Path(host_cxx[0]).parent / 'commands.json').read_text())
    host_command = sdk['compiler_bindings'].compiler_argv(host_record, 'cxx', ['-c'])
    target_command = sdk['compiler_bindings'].compiler_argv(record, 'cxx', ['-c'])
    require(host_command and target_command and host_command[-1] == target_command[-1] == '-c',
            'invalid C++ binding compile commands')
    return dict(v8_metagen_libclang_so=str(libclang),
                v8_metagen_libclang_bindings_dir=str(bindings),
                v8_metagen_runtime_python=native.tool('python'),
                v8_metagen_runtime_launcher=str(script), v8_metagen_runtime_view=str(view),
                v8_metagen_runtime_inputs=sorted(set(inputs + actual)),
                v8_metagen_gn_executable=native.tool('gn'),
                v8_metagen_gn_root_target='//electron',
                v8_metagen_gn_root_pattern='//electron:electron_dist_zip',
                v8_metagen_extra_flags=target_command[1:-1],
                v8_metagen_host_extra_flags=host_command[1:-1])


def common_node_configure(options, native, sdk, environment, resource_text):
    if not getattr(options, 'node_source', None):
        return {}
    require(options.gyp_source and options.gyp_pkgsrc, 'Node configure needs the selected common GYP source and pkgsrc export')
    require(options.v8_source and options.v8_metagen_libclang_so and options.v8_metagen_bindings_dir,
            'Node configure needs selected V8 and V8 metagen providers')
    prefix = Path(options.host_prefix).resolve(strict=True)
    python = native.tool('python')
    jinja_file = sdk['process'].capture([python, '-c',
        'import jinja2; print(jinja2.__file__)'], env=environment).stdout.decode('utf-8', 'strict').strip()
    jinja = Path(jinja_file).resolve(strict=True)
    require(jinja.is_file() and jinja.is_relative_to(prefix), 'Jinja must belong to selected host prefix')
    resource = Path(resource_text).resolve(strict=True)
    helper = (options.ports_source / 'scripts/source-inputs/node/configure-inputs.py').resolve(strict=True)
    paths = {
        'gyp-source': Path(options.gyp_source).resolve(strict=True),
        'gyp-pkgsrc': Path(options.gyp_pkgsrc).resolve(strict=True),
        'v8-source': Path(options.v8_source).resolve(strict=True),
        'inspector-source': (prefix / 'share/inspector-protocol').resolve(strict=True),
        'sdk-source': Path(options.sdk_source).resolve(strict=True),
        'jinja-root': jinja.parent.parent,
        'zlib-source': (prefix / 'share/zlib-source').resolve(strict=True),
        'v8-cxx-wrapper': (prefix / 'libexec/cwrappers/c++-wrapper').resolve(strict=True),
        'v8-selected-clang': Path(native.tool('cxx')).resolve(strict=True),
        'v8-libclang': Path(options.v8_metagen_libclang_so).resolve(strict=True),
        'v8-python-bindings': Path(options.v8_metagen_bindings_dir).resolve(strict=True),
        'v8-clang-resource': resource,
    }
    require(all(path.is_absolute() and path.exists() for path in paths.values()),
            'Node configure provider input is missing')
    require(all(paths[name].is_relative_to(prefix) for name in
                ('inspector-source', 'jinja-root', 'zlib-source', 'v8-cxx-wrapper',
                 'v8-selected-clang', 'v8-clang-resource')),
            'Node configure host input is outside selected host prefix')
    dependencies = [helper, paths['gyp-source'] / 'emberbsd-prepared-source.json',
                    paths['gyp-pkgsrc'] / 'devel/gyp/files/verify-source.py',
                    paths['gyp-pkgsrc'] / 'EMBERBSD-PKGSRC-REVISION',
                    paths['gyp-pkgsrc'] / 'EMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py',
                    paths['v8-source'] / 'emberbsd-prepared-source.json',
                    paths['inspector-source'] / 'emberbsd-prepared-source.json', jinja,
                    paths['v8-cxx-wrapper'], paths['v8-selected-clang'], paths['v8-libclang'],
                    paths['v8-python-bindings'] / 'clang/cindex.py']
    gyp_dependencies = [p for p in paths['gyp-source'].rglob('*') if p.is_file()]
    require(all(p.resolve(strict=True).is_relative_to(paths['gyp-source']) for p in gyp_dependencies),
            'Node configure GYP dependency escapes selected source')
    dependencies += gyp_dependencies
    dependencies += [p for p in (paths['gyp-pkgsrc'] / 'devel/gyp').rglob('*') if p.is_file()]
    host_dependencies = [p for p in paths['zlib-source'].rglob('*') if p.is_file()]
    for package in (jinja.parent, jinja.parent.parent / 'markupsafe'):
        require(package.is_dir(), 'Node configure Jinja dependency is missing')
        host_dependencies += [p for p in package.rglob('*') if p.is_file() and p.suffix in ('.py', '.so')]
    require(all(path.resolve(strict=True).is_relative_to(prefix) for path in host_dependencies),
            'Node configure host dependency escapes selected prefix')
    dependencies += host_dependencies
    dependencies.append(paths['v8-python-bindings'] / 'clang/__init__.py')
    require(all(path.is_file() for path in dependencies), 'Node configure identity input is absent')
    return {'emberbsd_node_configure_helper': str(helper),
            'emberbsd_node_configure_inputs': [name + '=' + str(path) for name, path in paths.items()],
            'emberbsd_node_configure_dependencies': sorted(str(path) for path in dependencies)}


def selected_node_abi(source, native, environment, sdk):
    node = Path(source).resolve(strict=True)
    helper = node / 'tools/getmoduleversion.py'
    header = node / 'src/node_version.h'
    require(helper.is_file() and header.is_file(), 'selected Node ABI inputs are missing')
    output = sdk['process'].capture([native.tool('python'), str(helper), '--electron'], env=environment)
    abi = output.stdout.decode('ascii', 'strict').strip()
    require(abi.isdecimal() and 0 < int(abi) < 2**31, 'selected Node Electron ABI is invalid')
    hashes = {'EMBERBSD_ELECTRON_NODE_ABI_' + name + '_SHA256': hashlib.sha256(path.read_bytes()).hexdigest()
              for name, path in (('HELPER', helper), ('HEADER', header))}
    return int(abi), hashes


def producer_inputs(options, sdk):
    native, environment = native_inputs(options, sdk)
    tools = target_inputs(options, sdk, native, environment, options.work)
    host_binding = native_runtime_binding(options, sdk, native, environment, tools)
    if tools.get('runtime_stage_sha256'):
        environment['EMBERBSD_TARGET_RUNTIME_SHA256'] = tools['runtime_stage_sha256']
        environment['EMBERBSD_TARGET_RUNTIME_BASE'] = tools['runtime_base']
    for role in ('cc', 'cxx', 'ar', 'nm', 'readelf'):
        environment[role.upper()] = shlex.quote(tools[role])
    for role in ('cc', 'cxx', 'ar', 'nm'):
        selected = host_binding[role] if host_binding and role in ('cc', 'cxx') else native.tool(role)
        environment['BUILD_' + role.upper()] = shlex.quote(selected)
    if options.compiler_family == 'gcc':
        for name in ('CFLAGS', 'CXXFLAGS', 'ASFLAGS', 'LDFLAGS'):
            environment[name] = shlex.join(['--sysroot=' + str(options.sysroot)])
    verbose_rust = sdk['process'].capture([native.tool('rustc'), '-vV'], env=environment).stdout.decode()
    environment, rust = local_module('electron_rust_policy', 'rust-policy.py').apply(environment, verbose_rust)
    launcher = shlex.join([native.tool('python'), str(options.sdk_source / 'scripts/link-launcher.py'),
                          '--lock-root', str(options.lock_root), '--context', str(options.link_context), '--'])
    values = arguments(options, native, tools, rust, launcher)
    if getattr(options, 'node_source', None):
        abi, hashes = selected_node_abi(options.node_source, native, environment, sdk)
        values['node_module_version'] = abi
        values['emberbsd_node_source_identity'] = str(Path(options.node_source).resolve(strict=True) / 'emberbsd-prepared-source.json')
        environment.update(hashes)
    buildlink = host_buildlink(options, sdk, native, environment, host_binding)
    if buildlink:
        values.update(emberbsd_pkg_config_role='explicit',
                      emberbsd_native_pkg_config_prefix=buildlink,
                      emberbsd_native_pkg_config_buildlink=True)
    values.update(common_abseil(options, sdk, native, environment, buildlink))
    values.update(common_icu(options, sdk, native, environment, buildlink))
    runtime_view = getattr(options, 'protoc_runtime_view', None)
    if runtime_view:
        require(native.host['os'] == 'Darwin', 'protoc runtime view requires a Darwin host')
        view = absolute(runtime_view, 'protoc runtime view')
        require(':' not in str(view), 'protoc runtime view cannot contain a colon')
        script = options.sdk_source / 'scripts/run-darwin-with-runtime.py'
        result = sdk['process'].capture([native.tool('python'), '-B', str(script), '--print-inputs'],
                                        env=environment).stdout.decode('utf-8', 'strict')
        launcher_inputs = json.loads(result)
        require(isinstance(launcher_inputs, list) and launcher_inputs and
                all(isinstance(item, str) and Path(item).is_absolute() and Path(item).is_file()
                    for item in launcher_inputs), 'invalid SDK runtime launcher inputs')
        entries = sorted(view.iterdir())
        require(entries and all(item.is_file() for item in entries),
                'protoc runtime view must contain only files')
        actual = sorted({str(item.resolve(strict=True)) for item in entries})
        values.update(emberbsd_protoc_runtime_launcher=str(script),
                      emberbsd_protoc_runtime_view=str(view),
                      emberbsd_protoc_runtime_inputs=sorted(set(launcher_inputs + actual)))
    if getattr(options, 'node_scoped_runtime', False):
        require(runtime_view, 'Node host runtime needs the selected scoped runtime view')
        values.update(node_config_gn_root_target='//electron',
                      node_config_gn_root_pattern='//electron:electron_dist_zip',
                      node_host_runtime_python=native.tool('python'),
                      node_host_runtime_launcher=values['emberbsd_protoc_runtime_launcher'],
                      node_host_runtime_view=values['emberbsd_protoc_runtime_view'],
                      node_host_runtime_inputs=values['emberbsd_protoc_runtime_inputs'])
    if getattr(options, 'perfetto_scoped_runtime', False):
        require(runtime_view, 'Perfetto host runtime needs the selected scoped runtime view')
        values.update(perfetto_host_runtime_launcher=values['emberbsd_protoc_runtime_launcher'],
                      perfetto_host_runtime_view=values['emberbsd_protoc_runtime_view'],
                      perfetto_host_runtime_inputs=values['emberbsd_protoc_runtime_inputs'])
    values.update(common_protobuf(options, sdk, native, environment, buildlink, runtime_view))
    values.update(common_undici(options, sdk, environment))
    values.update(common_embedder_sources(options, sdk, native, environment))
    values.update(common_v8_metagen(options, sdk, native, environment, tools))
    if host_binding:
        values.update(external_libcxx_has_extensive_hardening=True,
                      emberbsd_native_cpu={'aarch64': 'arm64', 'arm64': 'arm64',
                                           'amd64': 'x64', 'x86_64': 'x64'}[native.host['cpu']],
                      emberbsd_native_cc=host_binding['cc'], emberbsd_native_cxx=host_binding['cxx'])
    resource_text = sdk['process'].capture(
        [native.tool('clang'), '-print-resource-dir'], env=environment).stdout.decode('utf-8', 'strict').strip()
    values['clang_version'] = clang_resource_version(options.host_prefix, resource_text)
    values.update(common_node_configure(options, native, sdk, environment, resource_text))
    provider_check = options.workspace / 'src/third_party/node/run_selected_providers.py'
    versions = sdk['process'].capture([native.tool('python'), str(provider_check), '--inspect',
        environment['EMBERBSD_HOST_NODE'], environment['EMBERBSD_HOST_TYPESCRIPT'],
        environment['EMBERBSD_HOST_ROLLUP']], env=environment).stdout.decode('utf-8', 'strict').splitlines()
    require(len(versions) == 3 and all(versions), 'selected Node provider versions are invalid')
    values['emberbsd_node_provider_versions'] = versions
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



def gn_source(options):
    common = getattr(options, 'protobuf_source', None)
    if not (common or getattr(options, 'node_source', None) or getattr(options, 'perfetto_source', None) or getattr(options, 'v8_source', None) or getattr(options, 'shared_abseil', False) or getattr(options, 'shared_icu', False)):
        return options.workspace / 'src'
    view = local_module('electron_protobuf_source_view', 'protobuf-source-view.py')
    sources = dict(node=getattr(options, 'node_source', None), perfetto=getattr(options, 'perfetto_source', None),
                   v8=getattr(options, 'v8_source', None),
                   system_abseil=getattr(options, 'shared_abseil', False),
                   system_icu=getattr(options, 'shared_icu', False))
    destination = options.work / 'source-view'
    if not os.path.lexists(destination):
        require(getattr(options, 'phase', '') == 'configure',
                'common source view is missing; configure a new output')
        return view.create(options.workspace / 'src', common, destination, **sources)
    return view.verify(options.workspace / 'src', common, destination, **sources)



def require_common_v8(options):
    require(getattr(options, 'v8_source', None) and getattr(options, 'v8_ports_source', None) and
            getattr(options, 'v8_pkgsrc', None),
            'Electron 45 requires the verified common V8 source, owner and pkgsrc export')


def require_common_node(options):
    require(getattr(options, 'node_source', None) and getattr(options, 'node_pkgsrc', None),
            'Electron 45 requires the verified common Node source and pkgsrc export')


def configure(options):
    require_common_v8(options)
    require_common_node(options)
    sdk = load_sdk(options.sdk_source)
    verify_source(options.workspace, options.ports_source, options.git)
    work = options.work
    require(not work.exists(), 'configure output must be new; retain an unsuccessful output for diagnosis')
    work.mkdir()
    native, environment, values = producer_inputs(options, sdk)
    ensure_lastchange(options.workspace, native, environment, sdk)
    ensure_ffmpeg_netbsd_config(options.workspace)
    ensure_host_dsymutil(options.workspace, native)
    require_rust_std(options.host_prefix, options.target)
    output = work / 'out'; output.mkdir()
    (output / 'args.gn').write_text(gn_arguments(values))
    sdk['process'].run_logged([native.tool('gn'), 'gen', str(output),
        '--script-executable=' + native.tool('python'), '--ninja-executable=' + native.tool('ninja'),
        '--root-target=//electron', '--root-pattern=//electron:electron_dist_zip', '--fail-on-unused-args'],
        str(work / 'configure.log'), cwd=str(gn_source(options)), env=environment)
    # This is the actual producer invocation, not a qualification record.
    local_module('electron_build_source', 'prepare-build-sources.py').atomic_json(work / 'configuration.json',
        dict(arguments=values, environment=environment, source=str(options.workspace),
             sdk=str(options.sdk_source), host_prefix=str(options.host_prefix), target=options.target))



def reconfigure(options):
    require_common_v8(options)
    require_common_node(options)
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
        candidate.native_binding_root = work
        native, environment, values = producer_inputs(candidate, sdk)
        new_directory = saved_binding_directory(candidate.work, environment)
        new_commands = json.loads((new_directory / 'commands.json').read_text())
        require(binding_identity(new_commands) == binding_identity(old_commands),
                'target compiler, sysroot or runtime changed')
        # Prepared Node actions encode the selected providers in their argv.
        permitted_env = {'CC', 'CXX', 'EMBERBSD_HOST_NODE', 'EMBERBSD_HOST_PYTHON',
                         'EMBERBSD_HOST_TYPESCRIPT', 'EMBERBSD_HOST_ROLLUP',
                         'HOME', 'TMPDIR', 'TMP', 'TEMP', 'USER', 'LOGNAME'}
        old_env = saved['environment']
        require(not old_env.get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK') or
                environment.get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'),
                'reconfigure cannot remove the selected host buildlink')
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
        permitted_env.update(('PATH', 'EMBERBSD_CONTROL_GIT',
                              'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'))
        for name in (set(environment) | set(old_env)) - permitted_env:
            require(environment.get(name) == old_env.get(name), 'producer input changed: ' + name)
        identity_args = {'node_module_version', 'emberbsd_node_source_identity',
                         'emberbsd_node_configure_helper', 'emberbsd_node_configure_inputs',
                         'emberbsd_node_configure_dependencies', 'target_os', 'target_cpu', 'target_sysroot', 'emberbsd_target_sysroot',
                         'is_clang', 'unbundle_host_is_clang', 'clang_base_path', 'clang_version', 'host_toolchain',
                         'emberbsd_pkg_config_role',
                         'pkg_config', 'host_pkg_config',
                         'emberbsd_protoc_runtime_launcher', 'emberbsd_protoc_runtime_view',
                         'emberbsd_protoc_runtime_inputs', 'perfetto_host_runtime_launcher',
                         'perfetto_host_runtime_view', 'perfetto_host_runtime_inputs',
                         'node_config_gn_root_target', 'node_config_gn_root_pattern',
                         'node_host_runtime_python', 'node_host_runtime_launcher',
                         'node_host_runtime_view', 'node_host_runtime_inputs',
                         'node_shared_undici_path', 'node_shared_undici_input',
                         'v8_metagen_libclang_so', 'v8_metagen_libclang_bindings_dir',
                         'v8_metagen_runtime_python', 'v8_metagen_runtime_launcher',
                         'v8_metagen_runtime_view', 'v8_metagen_runtime_inputs',
                         'v8_metagen_gn_executable', 'v8_metagen_gn_root_target',
                         'v8_metagen_gn_root_pattern', 'v8_metagen_extra_flags',
                         'v8_metagen_host_extra_flags',
                         'icu_use_data_file',
                         'node_path', 'node_shared_perfetto',
                         'node_simdutf_include_from_target', 'use_system_simdutf',
                         'node_use_ffi',
                         'emberbsd_common_protobuf',
                         'emberbsd_protobuf_target_prefix',
                         'emberbsd_protoc',
                         'custom_toolchain', 'v8_snapshot_toolchain', 'emberbsd_mac_toolchain_bin',
                         'emberbsd_sdk_source', 'mac_sdk_path', 'mac_deployment_target',
                         'apple_linker_launcher', 'unbundle_linker_launcher', 'concurrent_links',
                         'rust_sysroot_absolute', 'rust_bindgen_root', 'rustc_version',
                         'use_custom_libcxx', 'use_custom_libcxx_for_host', 'use_custom_libunwind',
                         'external_libcxx_has_extensive_hardening', 'emberbsd_native_cpu',
                         'emberbsd_native_cc', 'emberbsd_native_cxx',
                         'use_lld', 'emberbsd_target_strip', 'emberbsd_target_objcopy'}
        identity_args.update('node_shared_' + feature for feature in NODE_SHARED_FEATURES)
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
                str(work / 'reconfigure.log'), cwd=str(gn_source(options)), env=environment)
            local_module('electron_build_source', 'prepare-build-sources.py').atomic_json(
                work / 'configuration.json',
                dict(arguments=values, environment=environment, source=str(options.workspace),
                     sdk=str(options.sdk_source), host_prefix=str(options.host_prefix), target=options.target))
        except BaseException:
            (output / 'args.gn').write_text(old_args)
            raise
        marker.unlink()

def build(options):
    require_common_v8(options)
    require_common_node(options)
    require(not (options.work / 'reconfigure-incomplete').exists(),
            'incomplete reconfiguration; rerun reconfigure before build')
    sdk = load_sdk(options.sdk_source)
    verify_source(options.workspace, options.ports_source, options.git)
    native, environment, values = producer_inputs(options, sdk)
    ensure_lastchange(options.workspace, native, environment, sdk)
    ensure_ffmpeg_netbsd_config(options.workspace)
    ensure_host_dsymutil(options.workspace, native)
    require_rust_std(options.host_prefix, options.target)
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
                             cwd=str(gn_source(options)), env=saved_env,
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
        for name in ('macos-sdk', 'xcode-version-plist', 'gcc-os-tools', 'target-runtime-stage', 'target-runtime-base', 'host-runtime-root', 'protoc-runtime-view',
                     'host-buildlink-pkgsrc', 'host-buildlink-stage-root',
                     'host-buildlink-base-makeconf', 'host-buildlink-bmake-mk',
                     'protobuf-source', 'protobuf-ports-source', 'protobuf-archive', 'protobuf-patch',
                     'node-source', 'node-pkgsrc', 'gyp-source', 'gyp-pkgsrc', 'perfetto-source', 'perfetto-ports-source',
                     'perfetto-archive', 'perfetto-patch', 'v8-source', 'v8-ports-source', 'v8-pkgsrc',
                     'v8-metagen-libclang-so', 'v8-metagen-bindings-dir', 'v8-metagen-runtime-view'):
            command.add_argument('--' + name, type=Path)
        command.add_argument('--perfetto-scoped-runtime', action='store_true')
        command.add_argument('--node-scoped-runtime', action='store_true')
        command.add_argument('--shared-undici', action='store_true')
        command.add_argument('--shared-abseil', action='store_true')
        command.add_argument('--shared-icu', action='store_true')
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
                exclusive = {Path(value).resolve() for value in (options.workspace, options.work)}
                selected = (options.ports_source, options.sdk_source, options.protobuf_source,
                            options.protobuf_ports_source, options.protobuf_archive, options.protobuf_patch,
                            options.node_source, options.node_pkgsrc, options.gyp_source, options.gyp_pkgsrc, options.perfetto_source,
                            options.perfetto_ports_source, options.perfetto_archive, options.perfetto_patch,
                            options.v8_source, options.v8_ports_source, options.v8_pkgsrc,
                            options.v8_metagen_libclang_so, options.v8_metagen_bindings_dir, options.v8_metagen_runtime_view,
                            options.target_runtime_stage, options.target_runtime_base, options.host_runtime_root, options.protoc_runtime_view,
                            options.host_prefix, options.sysroot, options.host_buildlink_pkgsrc,
                            options.host_buildlink_stage_root)
                shared = sorted({str(Path(value).resolve()) for value in selected
                                 if value is not None and Path(value).resolve() not in exclusive})
                with sdk['process'].ContextLocks(shared, str(options.lock_root), shared=True):
                    {'configure': configure, 'reconfigure': reconfigure, 'build': build}[options.phase](options)
    except Exception as error:
        parser.exit(1, 'Electron ' + options.phase + ' failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
