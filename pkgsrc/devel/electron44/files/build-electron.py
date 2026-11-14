#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Bind the Electron recipe's prepared source to selected SDK tools and GN/Ninja."""
import argparse
from contextlib import contextmanager
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import sys
import types
import tempfile
import time


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
                 'process', 'paths', 'jsonio', 'darwin_sdk', 'darwin_runtime', 'compiler_bindings', 'cpu_capacity',
                 'inventory', 'sourceprep', 'native_generator_runtime', 'publication'):
        module = importlib.import_module('emberbsd_sdk' + ('.' + name if name else ''))
        require(Path(module.__file__).resolve() == package / ((name or '__init__') + '.py'),
                'SDK module origin differs: ' + module.__name__)
        result[name] = module
    for name, field, version in (('', 'API_VERSION', 1), ('host_prefix', 'HOST_PREFIX_API', 2),
                                 ('application_toolchain', 'APPLICATION_TOOLCHAIN_API', 2),
                                 ('darwin_sdk', 'DARWIN_SDK_API', 1),
                                 ('publication', 'DIRECTORY_PUBLICATION_API', 1)):
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


def verify_source(workspace, ports, git, *, allow_ordered_prefix=False):
    source = local_module('electron_build_source', 'prepare-build-sources.py')
    record = json.loads((workspace / 'source-inputs/ports-build-sources.json').read_text())
    rows = source.read_series(Path(__file__).with_name('source-series.json'), ports / 'probes/electron/patches')
    expected = [source.series_record(row) for row in rows]
    actual = record.get('patches')
    matches = actual == expected
    if allow_ordered_prefix and isinstance(actual, list):
        matches = matches or (0 < len(actual) < len(expected) and actual == expected[:len(actual)])
    require(record.get('version') == 1 and matches,
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
                            Path(__file__).with_name('source-series.json'),
                            previous_prepared=getattr(options, 'previous_prepared', None))
    return source.materialize(options.workspace, options.destination, result, git=options.git)



def selected_control_git(path):
    git = Path(path).resolve(strict=True)
    require(git.is_file() and os.access(git, os.X_OK), 'selected Git is not executable')
    return str(git)


def source_owner_environment(environment):
    captured = dict(environment)
    source_cache = os.environ.get('EMBER_PREPARED_SOURCE_CACHE')
    if source_cache is None:
        captured.pop('EMBER_PREPARED_SOURCE_CACHE', None)
    else:
        captured['EMBER_PREPARED_SOURCE_CACHE'] = source_cache
    return captured


def native_required_roles(platform):
    roles = ('python', 'gn', 'ninja', 'node', 'rustc', 'rustfmt', 'bindgen', 'wayland-scanner',
             'pkg-config', 'rollup', 'tsc', 'clang', 'cc', 'cxx', 'cpp', 'ar', 'nm', 'strip', 'objcopy', 'readelf',
             'sh', 'env', 'sed', 'touch', 'cp', 'objdump')
    if platform == 'darwin':
        roles += ('dsymutil',)
    if platform.startswith('netbsd'):
        roles += ('paxctl',)
    return roles


def host_paxctl_arguments(native):
    if native.host['os'] == 'NetBSD':
        return {'v8_host_paxctl': native.tool('paxctl')}
    return {}


def _native_inputs(options, sdk):
    roles = native_required_roles(sys.platform)
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
    # Dawn runs its Tint source generator with the Ports lang/go127 toolchain;
    # it uses only the standard library, so module and toolchain downloads
    # stay off and the build cache lives in the work tree.
    environment.update(GOTOOLCHAIN='local', GOPROXY='off', GOFLAGS='-mod=readonly',
                       GOCACHE=str(Path(options.work) / 'go-cache'),
                       GOPATH=str(Path(options.work) / 'go-path'))
    providers = local_module('electron_node_providers', 'node-providers.py').select(native, electron=True)
    environment.update(providers['environment'])
    if native.host['os'] == 'Darwin':
        require(options.macos_sdk and options.xcode_version_plist and options.macos_minimum,
                'Darwin requires explicit SDK, Xcode version plist and deployment version')
        require(re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,2}', options.macos_minimum),
                'invalid Darwin deployment version')
        require(tuple(int(part) for part in options.macos_minimum.split('.')) >= (14, 0),
                'Electron CA renderer requires macOS 14.0 or newer')
        metadata = sdk['darwin_sdk'].read_metadata(str(options.macos_sdk),
                    xcode_version_plist=str(options.xcode_version_plist))
        environment['SDKROOT'] = metadata['sdk_path']
        environment['GYP_MACOS_SDK_PATH'] = metadata['sdk_path']
        environment['GYP_XCODE_VERSION_PLIST'] = str(Path(options.xcode_version_plist).resolve(strict=True))
        environment['MACOSX_DEPLOYMENT_TARGET'] = options.macos_minimum
        # Crashpad runs the selected devel/mig frontend from PATH; it requires an
        # explicit preprocessor and migcom (pkgsrc/devel/mig/README.md).
        migcom = Path(options.host_prefix) / 'libexec' / 'migcom'
        require(migcom.is_file() and os.access(migcom, os.X_OK), 'selected host prefix has no migcom')
        environment.update(MIGCC=native.tool('clang'), MIGCOM=str(migcom))
    return native, environment, providers


def native_inputs(options, sdk):
    native, environment, _providers = _native_inputs(options, sdk)
    return native, environment


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


def arguments(options, native, tools, rust_version, launcher, providers=None):
    cpu = {'amd64': 'x64', 'aarch64': 'arm64'}[options.target]
    host_cpu = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'x64', 'amd64': 'x64'}.get(native.host['cpu'])
    require(host_cpu is not None, 'unsupported GN host CPU: ' + native.host['cpu'])
    values = dict(target_os='netbsd', target_cpu=cpu, is_clang=options.compiler_family == 'clang',
        custom_toolchain='//build/toolchain/linux/unbundle:default',
        unbundle_host_is_clang=options.host_compiler_family == 'clang',
        use_sysroot=True, target_sysroot=str(options.sysroot), emberbsd_target_sysroot=str(options.sysroot),
        clang_base_path=str(options.host_prefix), clang_use_chrome_plugins=False,
        use_custom_libcxx=options.compiler_family != 'clang',
        use_custom_libcxx_for_host=False, use_custom_libunwind=False,
        use_lld=options.compiler_family == 'clang', use_thin_lto=False,
        use_system_libdrm=True, use_system_libffi=True, use_bundled_fontconfig=False,
        # Electron's wrappable_pointer_tags.h and node cppgc_helpers.h need the
        # Node cppgc tag when V8_ENABLE_SANDBOX is on (Electron patch: 0x5000).
        node_embedder_cppheap_pointer_tag='0x5000',
        rust_sysroot_absolute=str(options.host_prefix), rust_bindgen_root=str(options.host_prefix),
        rustc_version=rust_version, emberbsd_rust_unstable_features=True, wayland_scanner_executable=native.tool('wayland-scanner'),
        emberbsd_target_strip=tools['strip'], emberbsd_target_objcopy=tools['objcopy'],
        pkg_config=native.tool('pkg-config'), host_pkg_config=native.tool('pkg-config'),
        unbundle_linker_launcher=launcher, concurrent_links=1,
        is_debug=False, is_component_build=False,
        enable_swiftshader=False, enable_swiftshader_vulkan=False, angle_enable_swiftshader=False,
        dawn_use_swiftshader=False,
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
        use_vaapi=False,
        # Type-aware ESLint/Stylelint WebUI checks ship no output and need the
        # eslint/stylelint npm stack, which Ports does not package yet.
        enable_webui_lint=False)
    go = Path(options.host_prefix) / 'go127' / 'bin' / 'go'
    require(go.is_file() and os.access(go, os.X_OK), 'selected host prefix has no lang/go127')
    values['dawn_host_go_path'] = str(go)
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
    values.update(host_paxctl_arguments(native))
    values.update(emberbsd_electron_node=native.tool('node'),
                  emberbsd_electron_version_provider=str(Path(__file__).with_name('electron-version-provider.py').resolve()),
                  emberbsd_electron_provider_selector=str(Path(__file__).with_name('node-providers.py').resolve()),
                  emberbsd_electron_sdk_source=str(options.sdk_source),
                  emberbsd_electron_host_prefix=str(options.host_prefix),
                  emberbsd_electron_npm_runner=str(Path(__file__).with_name('electron-npm-runner.py').resolve()))
    if providers is None:
        providers = local_module('electron_node_providers', 'node-providers.py').select(native, electron=True)
    values.update(providers['arguments'])
    values['emberbsd_node_provider_inputs'] = list(values['emberbsd_node_provider_inputs'])
    provider_root = Path(getattr(options, 'native_binding_root', options.work))
    values['emberbsd_node_provider_inputs'].append(str(provider_root / 'devtools-provider.json'))
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
    if not selected:
        record = dict(commands={role: list(native.command(role)) for role in ('cc', 'cxx', 'cpp')},
                      flags={name: list(flags) for name, flags in native.abi_flags.items()},
                      link_flags={'cc': [], 'cxx': []})
        parent = getattr(options, 'native_binding_root', options.work)
        return bind_versioned(sdk, native, parent / 'native-commands', record)
    require(stage and native.host['os'] == 'Darwin' and
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
    host_toolchain = getattr(options, 'host_buildlink_host_toolchain', False)
    if not any(selected):
        require(not host_toolchain, 'host buildlink host toolchain requires a stage')
        return None
    require(all(selected[i] for i in (0, 2, 3)) and host_binding,
            'native host buildlink needs pkgsrc, makeconf, bmake mk and native C++ binding')
    require(not host_toolchain or (selected[1] and not getattr(options, 'host_runtime_root', None)),
            'host buildlink host toolchain requires a stage and the selected prefix runtime')
    root = getattr(options, 'native_binding_root', options.work)
    config = root / 'configuration.json'
    saved = json.loads(config.read_text()) if config.is_file() else {}
    previous = saved.get('environment', {}).get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK')
    script = Path(__file__).with_name('host-buildlink.py')
    record = Path(host_binding['cxx']).parent / 'commands.json'
    def command(work):
        return [native.tool('python'), '-B', str(script), '--sdk-source', str(options.sdk_source),
                '--pkgsrc-root', str(selected[0]), '--host-prefix', str(options.host_prefix),
                *(['--stage-root', str(selected[1])] if selected[1] else []),
                *(['--host-toolchain'] if host_toolchain else []),
                *(['--shared-ffmpeg'] if getattr(options, 'shared_ffmpeg', False) else []),
                *(['--shared-minizip'] if getattr(options, 'shared_minizip', False) else []),
                *(['--shared-xml'] if getattr(options, 'shared_xml', False) else []),
                *(['--shared-image'] if getattr(options, 'shared_image', False) else []),
                *(['--shared-font'] if getattr(options, 'shared_font', False) else []),
                *(['--shared-pdf-libraries'] if getattr(options, 'shared_pdf_libraries', False) else []),
                *(['--shared-codecs'] if getattr(options, 'shared_codecs', False) else []),
                *(['--shared-openh264'] if getattr(options, 'shared_openh264', False) else []),
                *(['--shared-pffft'] if getattr(options, 'shared_pffft', False) else []),
                *(['--shared-cpuinfo'] if getattr(options, 'shared_cpuinfo', False) else []),
                *(['--shared-vulkan'] if getattr(options, 'shared_vulkan', False) else []),
                *(['--shared-spirv-tools'] if getattr(options, 'shared_spirv_tools', False) else []),
                *(['--shared-woff2'] if getattr(options, 'shared_woff2', False) else []),
                *(['--shared-snappy'] if getattr(options, 'shared_snappy', False) else []),
                *(['--shared-expat'] if getattr(options, 'shared_expat', False) else []), '--base-makeconf', str(selected[2]),
                '--binding-record', str(record), '--bmake-mk', str(selected[3]),
                '--work', str(work), '--lock-root', str(options.lock_root)]
    requested = getattr(options, 'reuse_host_buildlink', None)
    if requested is not None:
        require(getattr(options, 'phase', None) == 'reconfigure' and previous,
                'host buildlink reuse requires an existing configuration')
        requested = Path(requested)
        require(requested.is_absolute() and requested.parent == root and
                re.fullmatch(r'host-buildlink-[0-9]+', requested.name) and
                not requested.is_symlink() and requested.resolve(strict=True) == requested,
                'requested host buildlink is outside the Electron output')
        previous = Path(previous)
        require(previous.parent == root and re.fullmatch(r'host-buildlink-[0-9]+', previous.name),
                'saved host buildlink is outside the Electron output')
        for index in range(10000):
            candidate = root / ('host-buildlink-' + str(index))
            if not os.path.lexists(candidate):
                break
        else:
            raise ValueError('too many retained host buildlink contexts')
        sdk['process'].capture(command(candidate), env=environment)
        result = sdk['process'].capture(command(requested) + ['--refresh-from', str(candidate)], env=environment)
        environment['EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'] = str(requested)
        return result.stdout.decode('utf-8', 'strict').strip()
    if not previous and (getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)):
        for candidate in sorted(root.glob('host-buildlink-*')):
            if not (candidate / 'selection.json').is_file():
                continue
            try:
                result = sdk['process'].capture(command(candidate) + ['--check'], env=environment)
            except sdk['process'].CommandError as error:
                if error.returncode == 3:
                    continue
                raise
            environment['EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'] = str(candidate)
            return result.stdout.decode('utf-8', 'strict').strip()
        raise ValueError('initial resume has no compatible existing host buildlink')
    if previous:
        previous = Path(previous)
        require(previous.parent == root and previous.name.startswith('host-buildlink-'),
                'saved host buildlink work is outside the Electron output')
        marker = previous / '.host-buildlink-extension.json'
        if os.path.lexists(marker):
            require(getattr(options, 'phase', None) != 'build',
                    'host buildlink extension requires reconfigure recovery')
            require(marker.is_file() and not marker.is_symlink(), 'invalid host buildlink extension journal')
            candidate = Path(json.loads(marker.read_text())['candidate'])
            require(candidate.parent == root and re.fullmatch(r'host-buildlink-[0-9]+', candidate.name),
                    'host buildlink extension candidate is outside the Electron output')
            result = sdk['process'].capture(command(previous) + ['--extend-from', str(candidate)], env=environment)
            environment['EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'] = str(previous)
            return result.stdout.decode('utf-8', 'strict').strip()
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
    if previous:
        try:
            refreshed = sdk['process'].capture(command(previous) + ['--refresh-from', str(work)], env=environment)
        except sdk['process'].CommandError as error:
            if error.returncode != 3:
                raise
        else:
            environment['EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'] = str(previous)
            return refreshed.stdout.decode('utf-8', 'strict').strip()
        try:
            extended = sdk['process'].capture(command(previous) + ['--extend-from', str(work)], env=environment)
        except sdk['process'].CommandError as error:
            if error.returncode != 3:
                raise
            require(not os.path.lexists(previous / '.host-buildlink-extension.json'),
                    'host buildlink extension requires reconfigure recovery')
        else:
            environment['EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'] = str(previous)
            return extended.stdout.decode('utf-8', 'strict').strip()
    environment['EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'] = str(work)
    return result.stdout.decode('utf-8', 'strict').strip()


def additive_host_buildlink_relocation(old_args, new_args, old_env, new_env, work):
    """Accept a new buildlink directory only when all previous links survive."""
    key = 'emberbsd_protobuf_native_prefix'
    if old_args.get(key) == new_args.get(key):
        return set()
    context_key = 'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'
    records, prefixes, contexts = [], [], []
    for arguments, environment in ((old_args, old_env), (new_args, new_env)):
        context = Path(environment.get(context_key, ''))
        require(context.is_absolute() and context.parent == work and
                re.fullmatch(r'host-buildlink-[0-9]+', context.name) and
                context.resolve(strict=True) == context,
                'host buildlink relocation has an invalid context')
        prefix = Path(arguments.get(key, ''))
        require(prefix.is_absolute() and prefix.is_relative_to(context) and
                prefix.name == '.buildlink' and prefix.resolve(strict=True) == prefix,
                'host buildlink relocation has an invalid prefix')
        record_path = context / 'selection.json'
        require(record_path.is_file() and not record_path.is_symlink(),
                'host buildlink selection is not a regular file')
        record = json.loads(record_path.read_text())
        links = record.get('identity', {}).get('links')
        invocation = record.get('invocation')
        require(isinstance(links, dict) and links and isinstance(invocation, dict) and
                invocation.get('work') == str(context), 'invalid host buildlink selection')
        for relative, target in links.items():
            require(isinstance(relative, str) and isinstance(target, str),
                    'invalid host buildlink link')
            path = Path(relative)
            require(path.parts and not path.is_absolute() and
                    all(part not in ('.', '..') for part in path.parts) and
                    str(path) == relative and Path(target).is_absolute(),
                    'invalid host buildlink link path')
            link = prefix / path
            require(link.is_symlink() and os.readlink(link) == target,
                    'host buildlink link differs from selection: ' + relative)
        records.append(record)
        prefixes.append(prefix.relative_to(context))
        contexts.append(context)
    require(prefixes[0] == prefixes[1], 'host buildlink prefix layout changed')
    old_links, new_links = (record['identity']['links'] for record in records)
    require(all(new_links.get(name) == target for name, target in old_links.items()),
            'host buildlink relocation removed or replaced an existing link')
    old_call, new_call = (record['invocation'] for record in records)
    relocated_root = old_call.get('pkgsrc_root') != new_call.get('pkgsrc_root')
    if relocated_root:
        owner = local_module('electron_host_buildlink', 'host-buildlink.py')
        proof = local_module('electron_host_buildlink_relocation', 'host-buildlink-relocation.py')
        proof.verify(records[0], records[1], contexts[0], contexts[1], owner)
    selection_keys = {'shared_ffmpeg', 'shared_minizip', 'shared_xml', 'shared_image', 'shared_font', 'shared_codecs', 'shared_openh264', 'shared_pffft', 'shared_expat', 'shared_cpuinfo', 'shared_vulkan', 'shared_woff2', 'shared_snappy', 'shared_pdf_libraries', 'shared_spirv_tools'}
    ignored = {'work', 'pkgsrc_root'} if relocated_root else {'work'}
    for name in (set(old_call) | set(new_call)) - ignored - selection_keys:
        require(old_call.get(name) == new_call.get(name),
                'host buildlink relocation changed an unrelated input: ' + name)
    for name in selection_keys:
        before, after = old_call.get(name), new_call.get(name)
        require(before in (None, 'yes') and after in (None, 'yes') and
                (before is None or after == 'yes'),
                'host buildlink relocation removed a selected provider')
    return {key}


def runtime_view_entries(directory, label):
    view = Path(directory).resolve(strict=True)
    require(view.is_dir(), label + ' is not a directory')
    entries = sorted(view.iterdir(), key=lambda path: path.name)
    require(entries and all(path.is_file() for path in entries),
            label + ' must contain only files')
    return {path.name: str(path.resolve(strict=True)) for path in entries}


def additive_protoc_runtime_view(old_arguments, values, options):
    """Validate a new scoped protoc view as an additive selected-provider extension."""
    old_view_value = old_arguments.get('emberbsd_protoc_runtime_view')
    new_view_value = values.get('emberbsd_protoc_runtime_view')
    if not old_view_value or not new_view_value:
        return set()
    old_view = Path(old_view_value).resolve(strict=True)
    new_view = Path(new_view_value).resolve(strict=True)
    if old_view == new_view:
        return set()
    require(old_arguments.get('emberbsd_protoc_runtime_launcher') ==
            values.get('emberbsd_protoc_runtime_launcher'),
            'protoc runtime launcher changed')
    old_entries = runtime_view_entries(old_view, 'saved protoc runtime view')
    new_entries = runtime_view_entries(new_view, 'candidate protoc runtime view')
    require(set(old_entries) <= set(new_entries),
            'protoc runtime view removed an existing alias')
    require(set(old_entries) < set(new_entries),
            'protoc runtime view change must add at least one alias')
    for name, target in old_entries.items():
        require(new_entries.get(name) == target,
                'protoc runtime view changed an existing alias: ' + name)

    selected_prefix = values.get('emberbsd_native_pkg_config_prefix')
    require(isinstance(selected_prefix, str) and selected_prefix,
            'protoc runtime view extension needs the selected native buildlink')
    buildlink_lib = (Path(selected_prefix) / 'lib').resolve(strict=True)
    runtime_root = getattr(options, 'host_runtime_root', None)
    require(runtime_root, 'protoc runtime view extension needs the selected host runtime')
    selected_runtime = Path(runtime_root).resolve(strict=True)
    selected_runtime_lib = (selected_runtime / 'lib').resolve(strict=True)
    require(buildlink_lib.is_dir() and selected_runtime_lib.is_dir(),
            'selected native buildlink or host runtime library directory is missing')
    added_names = set(new_entries) - set(old_entries)
    for name in sorted(added_names):
        require(Path(name).name == name and ':' not in name,
                'invalid new protoc runtime alias')
        buildlink_entry = buildlink_lib / name
        require(buildlink_entry.is_file(),
                'new protoc runtime alias is absent from selected buildlink: ' + name)
        target = Path(new_entries[name])
        selected_target = buildlink_entry.resolve(strict=True)
        require(target == selected_target,
                'new protoc runtime alias does not match selected buildlink provider: ' + name)
        require(target.is_relative_to(selected_runtime_lib),
                'new protoc runtime target is outside selected host runtime: ' + name)

    old_inputs = old_arguments.get('emberbsd_protoc_runtime_inputs')
    new_inputs = values.get('emberbsd_protoc_runtime_inputs')
    require(isinstance(old_inputs, list) and all(isinstance(item, str) for item in old_inputs) and
            isinstance(new_inputs, list) and all(isinstance(item, str) for item in new_inputs),
            'invalid protoc runtime input lists')
    old_input_set, new_input_set = set(old_inputs), set(new_inputs)
    require(len(old_input_set) == len(old_inputs) and len(new_input_set) == len(new_inputs) and
            all(Path(item).is_absolute() for item in old_input_set | new_input_set),
            'protoc runtime inputs must be unique absolute paths')
    old_targets, new_targets = set(old_entries.values()), set(new_entries.values())
    require(old_targets <= old_input_set and new_targets <= new_input_set,
            'protoc runtime input list omits a view target')
    added_targets = new_targets - old_targets
    require(new_input_set == old_input_set | added_targets,
            'protoc runtime inputs changed beyond added view targets')

    permitted = {'emberbsd_protoc_runtime_view', 'emberbsd_protoc_runtime_inputs'}
    for prefix in ('node_host_runtime', 'perfetto_host_runtime'):
        view_key, inputs_key = prefix + '_view', prefix + '_inputs'
        old_pair = (old_arguments.get(view_key), old_arguments.get(inputs_key))
        new_pair = (values.get(view_key), values.get(inputs_key))
        if old_pair == (None, None):
            require(new_pair == old_pair,
                    prefix + ' runtime selection was enabled during reconfigure')
        else:
            require(old_pair == (old_view_value, old_arguments.get('emberbsd_protoc_runtime_inputs')) and
                    new_pair == (new_view_value, new_inputs),
                    prefix + ' runtime selection changed independently of the protoc view')
            permitted.update((view_key, inputs_key))
    return permitted


def recipe_source_metadata(recipe, *, allow_empty_patches=False):
    patches = recipe / 'patches'
    require(patches.is_dir() or allow_empty_patches, 'common package patch inventory is missing')
    files = sorted(patches.glob('patch-*')) if patches.is_dir() else []
    require(files or allow_empty_patches, 'common package patch inventory is empty')
    return {'distinfo': hashlib.sha256((recipe/'distinfo').read_bytes()).hexdigest(),
            'patches': {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in files}}


def validate_package_source(package, expected, export_recipe, *, distinfo, package_path, allow_empty_patches=False):
    require(recipe_source_metadata(export_recipe, allow_empty_patches=allow_empty_patches) == expected,
            'selected pkgsrc patch inventory or distinfo differs from common owner')
    metadata = {}
    for line in (package / '+BUILD_VERSION').read_text().splitlines():
        name, separator, digest = line.partition(': ')
        # pkgsrc may record a PATCHDIR with a relative path through the
        # package directory (e.g. fonts/harfbuzz/../../fonts/harfbuzz).
        # Compare canonical repository-relative paths and reject collisions.
        name = os.path.normpath(name)
        require(separator and not os.path.isabs(name) and name != '..' and
                not name.startswith('../') and name not in metadata,
                'invalid package source metadata')
        metadata[name] = digest
    prefix = package_path + '/patches/'
    actual = {name[len(prefix):]: digest for name, digest in metadata.items() if name.startswith(prefix)}
    require(actual == expected['patches'], 'selected package patch inventory differs from common source')
    if distinfo:
        require(metadata.get(package_path + '/distinfo') == expected['distinfo'],
                'selected package distinfo differs from common source')


def protobuf_package_source(package, owner_recipe, export_recipe, *, distinfo, package_path="devel/protobuf", allow_empty_patches=False):
    """Compare installed pkgsrc source metadata with its selected owner."""
    expected = recipe_source_metadata(owner_recipe, allow_empty_patches=allow_empty_patches)
    validate_package_source(package, expected, export_recipe, distinfo=distinfo,
                            package_path=package_path, allow_empty_patches=allow_empty_patches)


def selected_protoc_command(options, native, protoc, runtime_view):
    """Select direct platform protoc or the existing explicit scoped runtime."""
    if runtime_view:
        return [native.tool('python'), str(options.sdk_source / 'scripts/run-darwin-with-runtime.py'),
                '--runtime-view', str(runtime_view), '--', str(protoc)]
    require(native.host['os'] in ('Darwin', 'Linux', 'NetBSD') and
            (native.host['os'] != 'Darwin' or options.host_compiler_family == 'clang') and
            not getattr(options, 'host_runtime_root', None),
            'direct common protobuf requires the selected platform host ABI')
    return [str(protoc)]



def native_installed_package_dirs(options, prefix):
    """Index pkgdb metadata directories once; the SDK selects actual load owners."""
    if getattr(options, '_native_generator_packages', None) is not None:
        return options._native_generator_packages
    database = Path(prefix).resolve(strict=True) / 'pkgdb'
    require(database.is_dir() and not database.is_symlink(), 'native pkgdb is unavailable')
    result = []
    for item in sorted(database.iterdir()):
        require(not item.is_symlink(), 'native pkgdb contains a linked entry')
        if not item.is_dir():
            continue
        require(all((item / name).is_file() and not (item / name).is_symlink()
                    for name in ('+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION')),
                'native pkgdb contains incomplete package metadata: ' + item.name)
        result.append(str(item))
    require(result, 'native pkgdb contains no package metadata')
    options._native_generator_packages = result
    return result

def platform_protoc_inputs(options, sdk, native, protoc, selection):
    """Track direct native dylibs through the selected host buildlink pkgdb."""
    prefix = Path(options.host_prefix).resolve(strict=True)
    if native.host['os'] != 'Darwin':
        runtime = sdk['native_generator_runtime']
        require(getattr(runtime, 'NATIVE_GENERATOR_RUNTIME_API', None) == 1,
                'unsupported native generator runtime API')
        packages = native_installed_package_dirs(options, prefix)
        return runtime.runtime_inputs(str(prefix), str(protoc), native.host, packages,
                                      search_path=native.path)
    image = sdk['darwin_runtime'].read_macho_runtime(str(protoc), native.host)
    owners = {}
    for item in selection:
        path = Path(item)
        if path.name != '+CONTENTS':
            continue
        package = path.resolve(strict=True).parent
        for line in path.read_text().splitlines():
            if line.startswith('lib/'):
                owners.setdefault(line, []).append(package)
    inputs = {str(protoc)}
    for row in image['loads'] + image['implicit_loads']:
        name = row['name']
        if name.startswith('/usr/lib/') or name.startswith('/System/Library/'):
            continue
        path = Path(name)
        require(path.is_absolute(), 'platform protoc has an unselected runtime load')
        resolved = path.resolve(strict=True)
        require(resolved.is_relative_to(prefix) and resolved.is_file(),
                'platform protoc runtime load escapes selected native prefix')
        relative = str(path.relative_to(prefix)) if path.is_relative_to(prefix) else ''
        packages = owners.get(relative, [])
        require(len(packages) == 1, 'platform protoc runtime load has no unique selected package owner')
        inputs.add(str(resolved))
        for metadata in ('+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION'):
            inputs.add(str((packages[0] / metadata).resolve(strict=True)))
    return sorted(inputs)


def common_protobuf(options, sdk, native, environment, buildlink, runtime_view):
    common = getattr(options, 'protobuf_source', None)
    common_inputs = (getattr(options, 'protobuf_ports_source', None),
                     getattr(options, 'protobuf_archive', None),
                     getattr(options, 'protobuf_patch', None))
    require(bool(common) == all(bool(item) for item in common_inputs),
            'common protobuf needs the source, owner, archive and patch inputs together')
    require(common or not any(common_inputs), 'incomplete common protobuf source selection')
    if common:
        require(buildlink, 'common protobuf requires the selected native buildlink')
        owner = Path(common_inputs[0]) / 'scripts/source-inputs/protobuf/source.py'
        require(owner.is_file(), 'common protobuf source owner is missing')
        verified = sdk['process'].capture([native.tool('python'), '-B', str(owner), '--sdk-source', str(options.sdk_source),
            '--git', selected_control_git(options.git), 'verify-source', '--source', str(common),
            '--archive', str(common_inputs[1]), '--patch', str(common_inputs[2])],
            env=source_owner_environment(environment))
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
        sdk['host_prefix'].validate_host_executable(str(options.host_prefix), str(protoc),
                                                    native.host, search_path=native.path)
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
            selected_protoc_command(options, native, protoc, runtime_view) + ['--version'],
            env=environment).stdout.decode('utf-8', 'strict').strip()
        match = re.fullmatch(r'libprotoc ([0-9]+(?:\.[0-9]+)+)', version_output)
        require(match and normalized_version(match.group(1)) == source_version,
                'selected host protoc version differs from the common source')
        result = dict(emberbsd_common_protobuf=True, emberbsd_protobuf_native_prefix=buildlink,
                      emberbsd_protobuf_target_prefix=str(options.sysroot / 'usr/pkg'),
                      emberbsd_protoc=str(protoc))
        if not runtime_view:
            result['emberbsd_protoc_runtime_inputs'] = platform_protoc_inputs(
                options, sdk, native, protoc, selected)
        return result
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
NODE_CONFIGURE_V8_PATH_KEYS = frozenset(('emberbsd_node_configure_inputs',
                                         'emberbsd_node_configure_dependencies'))


def verified_node_configure_v8_path_change(old_arguments, new_arguments, v8_source):
    """Allow only the verified V8 root substitution in Node configure inputs."""
    changed = any(old_arguments.get(name) != new_arguments.get(name)
                  for name in NODE_CONFIGURE_V8_PATH_KEYS)
    if not changed:
        return False

    old_inputs = old_arguments.get('emberbsd_node_configure_inputs')
    new_inputs = new_arguments.get('emberbsd_node_configure_inputs')

    def parse_inputs(rows, label):
        require(type(rows) is list and all(type(row) is str for row in rows),
                label + ' must be a string list')
        parsed, seen = [], set()
        for row in rows:
            name, separator, value = row.partition('=')
            require(separator and name and value and name not in seen,
                    label + ' contains an invalid or duplicate key')
            seen.add(name)
            parsed.append((name, value))
        roots = [value for name, value in parsed if name == 'v8-source']
        require(len(roots) == 1 and Path(roots[0]).is_absolute(),
                label + ' must contain exactly one absolute v8-source')
        return roots[0]

    old_root = parse_inputs(old_inputs, 'saved Node configure inputs')
    parse_inputs(new_inputs, 'new Node configure inputs')
    new_root = str(Path(v8_source).resolve())
    expected_inputs = [row if name != 'v8-source' else 'v8-source=' + new_root
                       for row in old_inputs
                       for name, separator, _ in (row.partition('='),)]
    require(new_inputs == expected_inputs,
            'Node configure inputs changed beyond the verified V8 source path')

    old_dependencies = old_arguments.get('emberbsd_node_configure_dependencies')
    new_dependencies = new_arguments.get('emberbsd_node_configure_dependencies')
    require(type(old_dependencies) is list and all(type(row) is str for row in old_dependencies) and
            type(new_dependencies) is list and all(type(row) is str for row in new_dependencies),
            'Node configure dependencies must be string lists')
    old_receipt = str(Path(old_root) / 'emberbsd-prepared-source.json')
    require(old_dependencies.count(old_receipt) == 1,
            'saved Node configure dependencies must contain the V8 receipt exactly once')
    new_receipt = str(Path(new_root) / 'emberbsd-prepared-source.json')
    expected_dependencies = sorted(new_receipt if row == old_receipt else row
                                   for row in old_dependencies)
    require(new_dependencies == expected_dependencies,
            'Node configure dependencies changed beyond the verified V8 receipt path')
    return True



def verified_node_configure_path_change(old_arguments, new_arguments, v8_source, python, sdk_source, environment,
                                        selected_node_owner):
    """Return only Node configure keys covered by a verified path transition."""
    def gyp_roots(arguments):
        rows = arguments.get('emberbsd_node_configure_inputs')
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, str) and row.startswith('gyp-pkgsrc=')]
    if (gyp_roots(old_arguments) != gyp_roots(new_arguments) or
            old_arguments.get('emberbsd_node_configure_helper') != new_arguments.get('emberbsd_node_configure_helper')):
        proof = local_module('electron_node_configure_relocation', 'node-configure-relocation.py')
        return proof.verify(old_arguments, new_arguments, python, sdk_source, environment, selected_node_owner)
    if verified_node_configure_v8_path_change(old_arguments, new_arguments, v8_source):
        return set(NODE_CONFIGURE_V8_PATH_KEYS)
    return set()


def verified_node_source_refresh(old_arguments, new_arguments, old_environment, new_environment, node_source):
    """Allow only a common-Node receipt refresh verified by producer_inputs."""
    old_hash = old_environment.get('EMBERBSD_NODE_SOURCE_SHA256')
    new_hash = new_environment.get('EMBERBSD_NODE_SOURCE_SHA256')
    old_receipt = old_arguments.get('emberbsd_node_source_identity')
    new_receipt = new_arguments.get('emberbsd_node_source_identity')
    if all(value is None for value in (old_hash, new_hash, old_receipt, new_receipt)):
        return False
    require(isinstance(old_hash, str) and re.fullmatch(r'[0-9a-f]{64}', old_hash) and
            isinstance(new_hash, str) and re.fullmatch(r'[0-9a-f]{64}', new_hash),
            'reconfigure requires verified common Node source identities')
    require(isinstance(old_receipt, str) and Path(old_receipt).is_absolute() and
            Path(old_receipt).name == 'emberbsd-prepared-source.json',
            'saved Node source identity must be an absolute prepared-source receipt')
    require(node_source, 'reconfigure requires the verified common Node source')
    expected_receipt = Path(node_source).resolve(strict=True) / 'emberbsd-prepared-source.json'
    require(new_receipt == str(expected_receipt) and expected_receipt.is_file(),
            'new Node source identity must name the verified common Node receipt')
    return old_hash != new_hash or old_receipt != new_receipt


def verified_common_source_refresh(old_arguments, new_arguments, old_environment,
                                   new_environment, options, work):
    """Allow verified source receipt changes while retaining existing views."""
    permitted = set()
    if verified_node_source_refresh(old_arguments, new_arguments, old_environment,
                                    new_environment, options.node_source):
        permitted.add('EMBERBSD_NODE_SOURCE_SHA256')
    require(new_arguments.get('v8_prepared_source_receipt') == '//v8/emberbsd-prepared-source.json' and
            new_arguments.get('v8_version_hash_salt_files') == [] and
            new_arguments.get('v8_version_hash_salt') == '',
            'reconfigure requires the verified common V8 receipt salt')
    links = {
        'PERFETTO': (options.perfetto_source, ('src/third_party/perfetto',)),
        'PROTOBUF': (options.protobuf_source, ('src/third_party/protobuf/src',
                                                'src/third_party/protobuf/third_party')),
    }
    for name in ('V8', 'PERFETTO', 'PROTOBUF'):
        key = 'EMBERBSD_' + name + '_SOURCE_SHA256'
        old, new = old_environment.get(key), new_environment.get(key)
        require(isinstance(old, str) and re.fullmatch(r'[0-9a-f]{64}', old) and
                isinstance(new, str) and re.fullmatch(r'[0-9a-f]{64}', new),
                'reconfigure requires verified common ' + name + ' source identities')
        if old == new:
            continue
        if name in links:
            root, paths = links[name]
            require(root and Path(root).is_absolute(), 'common ' + name + ' source is missing')
            root = Path(root).resolve(strict=True)
            for relative in paths:
                link = work / 'source-view' / relative
                target = root if name == 'PERFETTO' else root / Path(relative).name
                require(link.is_symlink() and Path(os.readlink(link)) == target,
                        'common ' + name + ' source root changed')
        permitted.add(key)
    return permitted


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
        # The selected V8 tree is already the complete common prepared source,
        # including its effective recipe patches. Key serialized caches to
        # that verified tree receipt instead of Electron's legacy bundled V8
        # patch-list salt, which does not describe this selected source tree.
        values.update(v8_prepared_source_receipt='//v8/emberbsd-prepared-source.json',
                      v8_version_hash_salt_files=[], v8_version_hash_salt='')
    if node:
        owner = (getattr(options, 'node_ports_source', None) or options.ports_source) / 'scripts/source-inputs/node/source.py'
        require(owner.is_file(), 'common Node source owner is missing')
        commands.append(('NODE', [native.tool('python'), '-B', str(owner), '--sdk-source', str(options.sdk_source),
                                  'verify-source', '--source', str(node), '--pkgsrc-root', str(node_export)]))
        values.update(node_path='//third_party/electron_node',
                      # The common Node builds embedder sources only when this
                      # hook is selected; generating electron_natives.cc alone
                      # does not register Electron's bootstrap modules.
                      node_embedder_builtins_target='//electron:electron_js2c',
                      node_embedder_builtins_output='electron_natives.cc',
                      node_inspector_string_traits_header=(
                          'third_party/inspector_protocol/crdtp/chromium/protocol_traits.h'),
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
        result = sdk['process'].capture(command, env=source_owner_environment(environment))
        record = json.loads(result.stdout.decode('utf-8', 'strict'))
        environment['EMBERBSD_' + name + '_SOURCE_SHA256'] = hashlib.sha256(
            json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return values





ML_PROVIDERS = ('ruy', 'pthreadpool', 'gemmlowp', 'farmhash', 'ml-dtypes',
                'neon2sse', 'fxdiv', 'fft2d', 'litert', 'openxla')



def common_flatc(options, sdk, native, environment):
    """Bind the selected native FlatBuffers generator and its real inputs."""
    prefix = Path(options.host_prefix).resolve(strict=True)
    db = prefix / 'pkgdb'
    result = sdk['process'].capture([str(prefix/'sbin/pkg_info'), '-K', str(db), '-E',
                                     'flatbuffers>=0'], env=environment).stdout.decode().splitlines()
    require(len(result) == 1 and '/' not in result[0], 'selected native FlatBuffers package is ambiguous')
    package = db/result[0]
    require('PKGPATH=devel/flatbuffers' in (package/'+BUILD_INFO').read_text().splitlines(),
            'native flatc has a different owner')
    tool = (prefix/'bin/flatc').resolve(strict=True)
    require(tool.is_file() and os.access(tool, os.X_OK) and tool.is_relative_to(prefix),
            'native flatc is outside selected prefix')
    require('bin/flatc' in (package/'+CONTENTS').read_text().splitlines(), 'flatc package ownership differs')
    sdk['host_prefix'].validate_host_executable(str(prefix), str(tool), native.host, search_path=native.path)
    recipe = Path(options.host_buildlink_pkgsrc)/'devel/flatbuffers'
    protobuf_package_source(package, recipe, recipe, distinfo=True,
                            package_path='devel/flatbuffers', allow_empty_patches=True)
    version = sdk['process'].capture([str(tool), '--version'], env=environment).stdout.decode().strip()
    match = re.fullmatch(r'flatc version ([0-9]+(?:\.[0-9]+)+)', version)
    require(match is not None, 'selected flatc returned an invalid version')
    version_header = prefix / 'include/flatbuffers/base.h'
    require('include/flatbuffers/base.h' in (package/'+CONTENTS').read_text().splitlines() and
            version_header.is_file() and version_header.resolve(strict=True).is_relative_to(prefix),
            'native FlatBuffers version header is not package-owned')
    text = version_header.read_text()
    parts = []
    for field in ('MAJOR', 'MINOR', 'REVISION'):
        found = re.findall(r'^#define\s+FLATBUFFERS_VERSION_' + field + r'\s+([0-9]+)\s*$', text, re.M)
        require(len(found) == 1, 'invalid native FlatBuffers version header')
        parts.append(found[0])
    require(match.group(1) == '.'.join(parts), 'selected flatc version differs from its package headers')
    if native.host['os'] == 'Darwin':
        image = sdk['darwin_runtime'].read_macho_runtime(str(tool), native.host)
        loads = image['loads'] + image['implicit_loads']
        require(all(row['name'].startswith(('/usr/lib/', '/System/Library/')) for row in loads),
                'native flatc has non-platform runtime dependencies requiring explicit selection')
        inputs = sorted([str(tool)] + [str((package/name).resolve(strict=True))
                                      for name in ('+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION')])
    else:
        runtime = sdk['native_generator_runtime']
        require(getattr(runtime, 'NATIVE_GENERATOR_RUNTIME_API', None) == 1,
                'unsupported native generator runtime API')
        packages = native_installed_package_dirs(options, prefix)
        inputs = runtime.runtime_inputs(str(prefix), str(tool), native.host, sorted(packages),
                                        search_path=native.path)
    return {'emberbsd_flatc': str(tool), 'emberbsd_flatc_inputs': sorted(set(inputs + [str(version_header.resolve(strict=True))]))}

def common_ml_sources(options, sdk, native, environment):
    """Validate each explicitly selected common source once per producer pass."""
    paths = {name: getattr(options, 'ml_' + name.replace('-', '_') + '_source', None)
             for name in ML_PROVIDERS}
    archives = {name: getattr(options, 'ml_' + name.replace('-', '_') + '_archive', None)
                for name in ML_PROVIDERS}
    controls = tuple(getattr(options, name, None) for name in
                     ('ml_patch', 'ml_export_patch', 'ml_ports_source', 'ml_pkgsrc_export'))
    bindings = tuple(getattr(options, 'ml_' + name.replace('-', '_') + '_' + role, None)
                     for name in ML_PROVIDERS for role in ('ports_source', 'pkgsrc_export', 'export_patch'))
    if not any(paths.values()) and not any(archives.values()) and not any(controls) and not any(bindings) and getattr(options, 'activate_common_providers', False):
        return {}
    require(all(paths.values()) and all(archives.values()) and getattr(options, 'ml_patch', None) and
            getattr(options, 'ml_pkgsrc_export', None) and getattr(options, 'ml_ports_source', None) and
            getattr(options, 'ml_export_patch', None),
            'Electron requires all verified common ML sources and patch tool')
    identities = {}
    for name, selected in paths.items():
        selected = absolute(selected, 'common ML source: ' + name)
        kind = name if name in ('litert', 'openxla') else 'ml-sources'
        key = 'ml_' + name.replace('-', '_')
        selected_owner = getattr(options, key + '_ports_source', None)
        selected_export = getattr(options, key + '_pkgsrc_export', None)
        selected_export_patch = getattr(options, key + '_export_patch', None)
        if selected_export is None and selected_owner is None:
            selected_export = options.ml_pkgsrc_export
        require(selected_export is not None or selected_export_patch is None,
                'common ML export patch requires an export: ' + name)
        owner = (selected_owner or options.ml_ports_source) / 'scripts/source-inputs' / kind / 'source.py'
        require(owner.is_file(), 'common ML source owner missing: ' + name)
        command = [native.tool('python'), '-B', str(owner)]
        if kind == 'ml-sources':
            command += ['--package', 'devel/' + name]
        command += ['--sdk-source', str(options.sdk_source), '--git', selected_control_git(options.git),
                    'verify-source', '--source', str(selected), '--archive', str(archives[name]),
                    '--patch', str(options.ml_patch)]
        if selected_export is not None:
            command += ['--pkgsrc-export', str(selected_export)]
        try:
            result = sdk['process'].capture(command, env=source_owner_environment(environment))
        except sdk['process'].CommandError as error:
            # A fast-path owner needs no export check. If it falls back to the
            # shared export, select that export's distinct patch explicitly.
            if selected_export is None or b'shared pkgsrc export was made from different inputs' not in error.stderr:
                raise
            result = sdk['process'].capture(command + ['--export-patch', str(selected_export_patch or options.ml_export_patch)],
                                             env=source_owner_environment(environment))
        record = json.loads(result.stdout.decode('utf-8', 'strict'))
        digest = record.get('tree_sha256') if isinstance(record, dict) else None
        require(record.get('package') == 'devel/' + name and isinstance(digest, str) and
                re.fullmatch(r'[0-9a-f]{64}', digest), 'invalid verified ML source: ' + name)
        identities[name] = digest
        environment['EMBERBSD_ML_' + name.upper().replace('-', '_') + '_SHA256'] = digest
    options.ml_identities = identities
    options.ml_sdk = sdk
    options.ml_sources = {name: Path(path).resolve(strict=True) for name, path in paths.items()}
    selector = local_module('electron_header_providers', 'header-providers.py')
    options.ml_headers = selector.select(options, sdk, native, environment, source_check=protobuf_package_source)
    for name, record in options.ml_headers.items():
        environment['EMBERBSD_ML_HEADER_' + name.upper() + '_SHA256'] = record['identity']
    return {'use_litert_tflite': True, **common_flatc(options, sdk, native, environment)}


def common_boringssl_source(options, sdk, native, environment):
    """Verify the explicit common source using the shared archive owner."""
    selected = absolute(options.boringssl_source, 'common BoringSSL source')
    archive = absolute(options.boringssl_archive, 'common BoringSSL archive', directory=False)
    owner = Path(options.ports_source) / 'scripts/source-inputs/boringssl/source.py'
    require(owner.is_file(), 'common BoringSSL source owner is missing')
    command = [native.tool('python'), '-B', str(owner), '--sdk-source', str(options.sdk_source),
               '--git', selected_control_git(options.git), 'verify-source', '--source', str(selected),
               '--archive', str(archive), '--patch', str(options.ml_patch)]
    result = sdk['process'].capture(command, env=source_owner_environment(environment))
    record = json.loads(result.stdout.decode('utf-8', 'strict'))
    digest = record.get('tree_sha256') if isinstance(record, dict) else None
    require(isinstance(record, dict) and record.get('package') == 'security/boringssl' and isinstance(digest, str) and
            re.fullmatch(r'[0-9a-f]{64}', digest), 'invalid verified BoringSSL source')
    options.boringssl_identity = digest
    options.boringssl_selected = selected
    environment['EMBERBSD_BORINGSSL_SOURCE_SHA256'] = digest


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



def selected_owned_library(prefix, link_name, owners, directory='lib'):
    """Bind the selected logical and resolved library files to pkgdb ownership."""
    prefix = Path(prefix).resolve(strict=True)
    logical = prefix / directory / link_name
    resolved = logical.resolve(strict=True)
    require(resolved.is_relative_to(prefix) and resolved.is_file(), 'selected library escapes its prefix')
    contents = set()
    for package in owners:
        contents.update((Path(package) / '+CONTENTS').read_text().splitlines())
    require(str(logical.relative_to(prefix)) in contents and str(resolved.relative_to(prefix)) in contents,
            'selected library is not owned by the verified package')
    return str(resolved)


# Names are package owners and installed ABI names, not a parallel resolver.
COMMON_MEDIA_LIBRARIES = {
    'libyuv': ('multimedia/libyuv', 'libyuv', ('include/libyuv.h', 'include/libyuv/')),
    'libsrtp': ('security/libsrtp', 'libsrtp2', ('include/srtp2/',)),
    'crc32c': ('devel/crc32c', 'libcrc32c', ('include/crc32c/',)),
}


def common_media_libraries(options, native, environment, buildlink):
    from emberbsd_sdk import paths
    """Select installed common host/target libraries and their owned inputs."""
    host_prefix = Path(options.host_prefix).resolve(strict=True)
    host_db = host_prefix / 'pkgdb'
    def packages_by_path(db):
        result = {}
        for package in db.iterdir():
            info = package / '+BUILD_INFO'
            if info.is_file():
                for line in info.read_text().splitlines():
                    if line.startswith('PKGPATH='):
                        result.setdefault(line[len('PKGPATH='):], []).append(package)
        return result
    host_packages = packages_by_path(host_db)
    target_prefix = Path(options.sysroot) / 'usr/pkg'
    target_db = target_prefix / 'pkgdb'
    target_packages = packages_by_path(target_db)
    options._common_native_packages = host_packages
    options._common_target_packages = target_packages
    result = {}
    selections = {}
    for name, (pkgpath, library, header_prefixes) in COMMON_MEDIA_LIBRARIES.items():
        selections[name] = {}
        hosts = host_packages.get(pkgpath, [])
        targets = target_packages.get(pkgpath, [])
        require(len(hosts) == len(targets) == 1, 'ambiguous common media package: ' + pkgpath)
        host, target = hosts[0], targets[0]
        selections[name]['source'] = {'pkgpath': pkgpath, 'package': host.name}
        require(host.name == target.name, 'host and target common media versions differ: ' + pkgpath)
        owner = Path(options.ports_source) / 'pkgsrc' / pkgpath
        exported = Path(options.host_buildlink_pkgsrc) / pkgpath
        selections[name]['source']['distinfo_sha256'] = hashlib.sha256((exported / 'distinfo').read_bytes()).hexdigest()
        for package in (host, target):
            protobuf_package_source(package, owner, exported, distinfo=True,
                                    package_path=pkgpath, allow_empty_patches=True)
        native_suffix = '.dylib' if native.host['os'] == 'Darwin' else '.so'
        for role, package, prefix, suffix in (
                ('host', host, host_prefix, native_suffix),
                ('target', target, target_prefix, '.so')):
            prefix = prefix.resolve(strict=True)
            headers = []
            header_hashes = {}
            header_files = {}
            manifest = (package / '+CONTENTS').read_text().splitlines()
            for index, line in enumerate(manifest):
                if any(line == key or (key.endswith('/') and line.startswith(key)) for key in header_prefixes):
                    path = prefix / line
                    resolved = path.resolve(strict=True)
                    require(resolved.is_relative_to(prefix) and resolved.is_file(),
                            'common media header escapes prefix: ' + str(path))
                    headers.append(str(resolved))
                    require(index + 1 < len(manifest) and
                            re.fullmatch(r'@comment MD5:[0-9a-f]{32}', manifest[index + 1]),
                            'common media header lacks package checksum: ' + line)
                    expected_md5 = manifest[index + 1].split(':', 1)[1]
                    stream, info = paths.open_regular(resolved)
                    with stream:
                        data = stream.read()
                        require(paths.stable_identity(os.fstat(stream.fileno())) == paths.stable_identity(info),
                                'common media header changed during verification: ' + line)
                    paths.verify_stable(resolved, info)
                    require(hashlib.md5(data, usedforsecurity=False).hexdigest() == expected_md5,
                            'common media header differs from installed package: ' + line)
                    header_hashes[line] = hashlib.sha256(data).hexdigest()
                    header_files[line] = {'path': str(resolved), 'md5': expected_md5,
                                          'stable': list((info.st_dev, info.st_ino, info.st_mode,
                                                          info.st_size, info.st_mtime_ns, info.st_ctime_ns))}
            require(headers and len(headers) == len(set(headers)), 'missing or duplicate headers: ' + pkgpath)
            selected = selected_owned_library(prefix, library + suffix, [package])
            selections[name][role] = {'header_hashes': header_hashes, 'header_files': header_files,
                                     'package': str(package), 'prefix': str(prefix)}
            result['emberbsd_' + name + '_' + role + '_library'] = selected
            result['emberbsd_' + name + '_' + role + '_headers'] = str(prefix / 'include')
            result['emberbsd_' + name + '_' + role + '_inputs'] = sorted(set(headers + [selected] +
                [str(package / item) for item in ('+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION')]))
        if name in ('libyuv', 'libsrtp'):
            host_headers = selections[name]['host']['header_hashes']
            target_headers = selections[name]['target']['header_hashes']
            differing = sorted(key for key in set(host_headers) | set(target_headers)
                               if host_headers.get(key) != target_headers.get(key))
            require(not differing, 'host and target public headers differ for ' + pkgpath + ': ' + ', '.join(differing))
    options.media_header_selections = {name: selections[name] for name in ('libyuv', 'libsrtp')}
    media_view = local_module('electron_media_header_view', 'media-header-view.py')
    for name in media_view.NAMES:
        environment['EMBERBSD_MEDIA_HEADER_' + name.upper() + '_SHA256'] = media_view.identity(options.media_header_selections, name)
    return result




def compression_recipe_catalog(options, sdk, native, environment):
    """Derive selected recipes once per effective owner-input change."""
    owner = Path(options.ports_source).resolve(strict=True)
    selector_path = owner/'scripts/pkgsrc-source-identity.py'
    spec = importlib.util.spec_from_file_location('electron_pkgsrc_source_identity', selector_path)
    require(spec and spec.loader, 'pkgsrc source identity owner is unavailable')
    selector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selector)
    git = selected_control_git(options.git)
    packages = ('archivers/brotli', 'archivers/zstd')
    if getattr(options, 'shared_ffmpeg', False):
        packages += ('multimedia/ffmpeg9',)
    if getattr(options, 'shared_minizip', False):
        packages += ('devel/zlib', 'archivers/minizip-ng')
    if getattr(options, 'shared_xml', False):
        packages += ('textproc/libxml2', 'textproc/libxslt')
    if getattr(options, 'shared_image', False):
        packages += ('graphics/libjpeg-turbo', 'graphics/libwebp')
    if getattr(options, 'shared_font', False):
        packages += ('graphics/freetype2', 'fonts/harfbuzz')
    if getattr(options, 'shared_pdf_libraries', False):
        packages += ('graphics/lcms2', 'graphics/openjpeg', 'graphics/tiff')
    if getattr(options, 'shared_pffft', False):
        packages += ('audio/pffft',)
    if getattr(options, 'shared_expat', False):
        packages += ('textproc/expat',)
    if getattr(options, 'shared_cpuinfo', False):
        packages += ('sysutils/cpuinfo',)
    if getattr(options, 'shared_vulkan', False):
        packages += ('graphics/vulkan-loader', 'graphics/vulkan-headers')
    if getattr(options, 'shared_woff2', False):
        packages += ('fonts/woff2',)
    if getattr(options, 'shared_snappy', False):
        packages += ('devel/snappy',)
    if getattr(options, 'shared_spirv_tools', False):
        packages += ('parallel/spirv-tools', 'parallel/spirv-headers')
    if getattr(options, 'shared_openh264', False):
        packages += ('multimedia/openh264',)
    if getattr(options, 'shared_codecs', False):
        packages += ('multimedia/dav1d', 'multimedia/libaom', 'multimedia/libvpx', 'audio/libopus', 'audio/flac')
    identities = {name: selector.git_package_identity(owner, name, git) for name in packages}
    config_root = getattr(options, 'native_binding_root', None) or options.work
    config = Path(config_root)/'configuration.json'
    saved = json.loads(config.read_text()) if config.is_file() else {}
    raw = saved.get('environment', {}).get('EMBERBSD_COMPRESSION_RECIPE_CATALOG')
    previous = json.loads(raw) if raw else None
    valid = (isinstance(previous, dict) and set(previous) == {'version', 'identities', 'recipes'} and
             previous['version'] == 1 and set(previous['identities']) == set(packages) and
             set(previous['recipes']) == set(packages) and
             all(selector.equivalent_effective_package(previous['identities'][name], identities[name])
                 for name in packages))
    if valid:
        return previous
    require(getattr(options, 'phase', '') != 'build',
            'common compression owner inputs changed; reconfigure required')
    with tempfile.TemporaryDirectory(prefix='electron-compression-export-') as temp:
        output = Path(temp)/'pkgsrc'
        sdk['process'].capture([native.tool('python'), '-B', str(owner/'scripts/prepare-pkgsrc.py'),
            str(output), '--git', git, '--patch', str(options.ml_patch)],
            env=source_owner_environment(environment))
        recipes = {name: recipe_source_metadata(output/name, allow_empty_patches=True) for name in packages}
    return {'version': 1, 'identities': identities, 'recipes': recipes}


def common_compression(options, sdk, native, environment, buildlink):
    """Validate existing common Brotli/Zstd packages and select the native tool."""
    require(buildlink, 'common compression requires the selected host buildlink')
    catalog = compression_recipe_catalog(options, sdk, native, environment)
    options._compression_catalog = catalog
    environment['EMBERBSD_COMPRESSION_RECIPE_CATALOG'] = json.dumps(catalog, sort_keys=True, separators=(',', ':'))
    record = {}
    for name, pkgpath in (('brotli', 'archivers/brotli'), ('zstd', 'archivers/zstd')):
        hosts = options._common_native_packages.get(pkgpath, [])
        targets = options._common_target_packages.get(pkgpath, [])
        require(len(hosts) == len(targets) == 1 and hosts[0].name == targets[0].name,
                'common compression package mismatch: ' + pkgpath)
        exported = Path(options.host_buildlink_pkgsrc) / pkgpath
        for package in (hosts[0], targets[0]):
            validate_package_source(package, catalog['recipes'][pkgpath], exported,
                                    distinfo=True, package_path=pkgpath, allow_empty_patches=True)
        record[name] = {'package': hosts[0].name,
                        'distinfo': hashlib.sha256((exported/'distinfo').read_bytes()).hexdigest()}
    selection_work = environment.get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK')
    require(selection_work, 'common compression needs selected host buildlink metadata')
    selection = json.loads((Path(selection_work)/'selection.json').read_text())['identity']['inputs']
    host_prefix = Path(options.host_prefix).resolve(strict=True)
    for pkgpath, modules in (('archivers/brotli', ('libbrotlidec', 'libbrotlienc')),
                             ('archivers/zstd', ('libzstd',))):
        host_package = options._common_native_packages[pkgpath][0]
        target_package = options._common_target_packages[pkgpath][0]
        for module in modules:
            entry = 'lib/pkgconfig/' + module + '.pc'
            require(entry in (host_package/'+CONTENTS').read_text().splitlines() and
                    entry in (target_package/'+CONTENTS').read_text().splitlines() and
                    str(host_prefix/entry) in selection,
                    'common compression pkg-config provider is not selected: ' + module)
    versions = []
    for role, prefix in (('host', Path(buildlink)), ('target', Path(options.sysroot)/'usr/pkg')):
        env = dict(environment, PKG_CONFIG_LIBDIR=str(prefix/'lib/pkgconfig'))
        env.pop('PKG_CONFIG_PATH', None)
        if role == 'host':
            env.pop('PKG_CONFIG_SYSROOT_DIR', None)
        else:
            env['PKG_CONFIG_SYSROOT_DIR'] = str(options.sysroot)
        command = [native.tool('pkg-config')] + (['--define-prefix'] if role == 'host' else [])
        command += ['--modversion', 'libbrotlidec', 'libbrotlienc', 'libzstd']
        output = sdk['process'].capture(command, env=env).stdout.decode('utf-8', 'strict').splitlines()
        require(len(output) == 3 and output[0] == output[1],
                'common compression pkg-config returned invalid versions')
        versions.append(output)
    require(versions[0] == versions[1], 'host and target compression package versions differ')
    package = options._common_native_packages['archivers/brotli'][0]
    manifest = (package/'+CONTENTS').read_text().splitlines()
    require(manifest.count('bin/brotli') == 1, 'native Brotli executable has no unique owner')
    tool = (Path(options.host_prefix)/'bin/brotli').resolve(strict=True)
    index = manifest.index('bin/brotli')
    require(index + 1 < len(manifest) and re.fullmatch(r'@comment MD5:[0-9a-f]{32}', manifest[index+1]),
            'native Brotli executable has no package checksum')
    stream, info = sdk['paths'].open_regular(tool)
    with stream:
        data = stream.read()
        require(sdk['paths'].stable_identity(os.fstat(stream.fileno())) == sdk['paths'].stable_identity(info),
                'native Brotli executable changed during verification')
    sdk['paths'].verify_stable(tool, info)
    require(hashlib.md5(data, usedforsecurity=False).hexdigest() == manifest[index+1].split(':', 1)[1],
            'native Brotli executable differs from installed package')
    sdk['host_prefix'].validate_host_executable(str(options.host_prefix), str(tool), native.host,
                                                search_path=native.path)
    inputs = platform_protoc_inputs(options, sdk, native, tool, selection)
    options.compression_identity = hashlib.sha256(json.dumps(record, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()
    environment['EMBERBSD_COMPRESSION_SOURCE_SHA256'] = options.compression_identity
    return {'emberbsd_brotli_native_tool': str(tool), 'emberbsd_brotli_native_inputs': inputs}


def common_minizip(options, sdk, native, environment, buildlink):
    """Select matching installed common zlib and compatibility minizip."""
    if not getattr(options, 'shared_minizip', False):
        return {}
    require(buildlink, 'shared minizip requires selected host buildlink')
    selection_work = environment.get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK')
    require(selection_work, 'shared minizip needs host buildlink metadata')
    selection = json.loads((Path(selection_work)/'selection.json').read_text())['identity']['inputs']
    host_prefix = Path(options.host_prefix).resolve(strict=True)
    record = {}
    for path, module, minimum in (('devel/zlib', 'zlib', (1, 3, 2, 7)),
                                  ('archivers/minizip-ng', 'minizip', (4, 2, 2, 2))):
        hosts = options._common_native_packages.get(path, [])
        targets = options._common_target_packages.get(path, [])
        require(len(hosts) == len(targets) == 1 and hosts[0].name == targets[0].name,
                'shared compression provider missing or mismatched: ' + path)
        match = re.fullmatch(r'[^-]+(?:-ng)?-(\d+)\.(\d+)\.(\d+)(?:nb(\d+))?', hosts[0].name)
        require(match and tuple(int(n or 0) for n in match.groups()) >= minimum,
                'shared compression provider is too old: ' + path)
        recipe = options._compression_catalog['recipes'][path]
        exported = Path(options.host_buildlink_pkgsrc)/path
        for package in (hosts[0], targets[0]):
            validate_package_source(package, recipe, exported, distinfo=True,
                                    package_path=path, allow_empty_patches=True)
            manifest = (package/'+CONTENTS').read_text().splitlines()
            require('lib/pkgconfig/' + module + '.pc' in manifest,
                    'missing owned pkg-config file: ' + module)
        require(str(host_prefix/'lib/pkgconfig'/(module+'.pc')) in selection and
                (Path(buildlink)/'lib/pkgconfig'/(module+'.pc')).is_file(),
                'host pkg-config provider is not selected: ' + module)
        versions = []
        for role, prefix in (('host', Path(buildlink)), ('target', Path(options.sysroot)/'usr/pkg')):
            env = dict(environment, PKG_CONFIG_LIBDIR=str(prefix/'lib/pkgconfig'))
            env.pop('PKG_CONFIG_PATH', None)
            if role == 'host':
                env.pop('PKG_CONFIG_SYSROOT_DIR', None)
            else:
                env['PKG_CONFIG_SYSROOT_DIR'] = str(options.sysroot)
            command = [native.tool('pkg-config')] + (['--define-prefix'] if role == 'host' else [])
            version = sdk['process'].capture(command + ['--modversion', module], env=env).stdout.decode().strip()
            require(version, 'empty pkg-config version: ' + module)
            versions.append(version)
        require(versions[0] == versions[1], 'host and target provider versions differ: ' + module)
        record[path] = {'package': hosts[0].name, 'recipe': recipe, 'version': versions[0]}
    for package, prefix in ((options._common_native_packages['archivers/minizip-ng'][0], host_prefix),
                            (options._common_target_packages['archivers/minizip-ng'][0], Path(options.sysroot)/'usr/pkg')):
        manifest = (package/'+CONTENTS').read_text().splitlines()
        require('include/minizip' in manifest and 'include/minizip-ng/unzip.h' in manifest,
                'minizip compatibility headers missing')
        require((prefix/'include/minizip').resolve(strict=True) == (prefix/'include/minizip-ng').resolve(strict=True),
                'minizip compatibility header alias is invalid')
    environment['EMBERBSD_MINIZIP_SOURCE_SHA256'] = hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    values = {}
    for role, db, prefix, suffix in (
            ('host', options._common_native_packages, host_prefix,
             '.dylib' if native.host['os'] == 'Darwin' else '.so'),
            ('target', options._common_target_packages, Path(options.sysroot)/'usr/pkg', '.so')):
        for label, path, libname, headers in (
                ('zlib', 'devel/zlib', 'libz', ('include/zlib.h', 'include/zconf.h')),
                ('minizip', 'archivers/minizip-ng', 'libminizip-ng',
                 ('include/minizip-ng/ioapi.h', 'include/minizip-ng/unzip.h',
                  'include/minizip-ng/zip.h', 'include/minizip-ng/crypt.h',
                  'include/minizip-ng/iowin32.h'))):
            package = db[path][0]
            manifest = (package/'+CONTENTS').read_text().splitlines()
            library = selected_owned_library(prefix, libname + suffix, [package])
            files = []
            for entry in headers:
                require(entry in manifest, 'missing owned header: ' + entry)
                header = (prefix/entry).resolve(strict=True)
                require(header.is_relative_to(prefix.resolve(strict=True)) and header.is_file(),
                        'provider header escapes selected prefix')
                index = manifest.index(entry)
                require(index + 1 < len(manifest) and
                        re.fullmatch(r'@comment MD5:[0-9a-f]{32}', manifest[index+1]) and
                        hashlib.md5(header.read_bytes(), usedforsecurity=False).hexdigest() ==
                        manifest[index+1].split(':', 1)[1], 'provider header differs: ' + entry)
                files.append(str(header))
            values['emberbsd_' + label + '_' + role + '_libraries'] = [library]
            values['emberbsd_' + label + '_' + role + '_inputs'] = sorted(set(
                files + [library] + [str(package/item) for item in ('+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION')]))
    return values


def common_ffmpeg(options, sdk, native, environment, buildlink):
    """Select matching current FFmpeg packages for the host and target graph."""
    if not getattr(options, 'shared_ffmpeg', False):
        return {}
    require(buildlink, 'shared FFmpeg requires selected host buildlink')
    pkgpath = 'multimedia/ffmpeg9'
    hosts = options._common_native_packages.get(pkgpath, [])
    targets = options._common_target_packages.get(pkgpath, [])
    require(len(hosts) == len(targets) == 1 and hosts[0].name == targets[0].name,
            'shared FFmpeg host and target packages differ or are missing')
    match = re.fullmatch(r'ffmpeg9-(\d+)\.(\d+)\.(\d+)(?:nb(\d+))?', hosts[0].name)
    require(match and tuple(int(n or 0) for n in match.groups()) >= (9, 0, 2, 7),
            'shared FFmpeg requires ffmpeg9>=9.0.2nb7')
    exported = Path(options.host_buildlink_pkgsrc) / pkgpath
    expected = options._compression_catalog['recipes'][pkgpath]
    for package in (hosts[0], targets[0]):
        validate_package_source(package, expected, exported, distinfo=True,
                                package_path=pkgpath, allow_empty_patches=True)
    selection_work = environment.get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK')
    require(selection_work, 'shared FFmpeg needs host buildlink metadata')
    selection = json.loads((Path(selection_work)/'selection.json').read_text())['identity']['inputs']
    host_prefix = Path(options.host_prefix).resolve(strict=True)
    modules = ('libavcodec', 'libavformat', 'libavutil')
    for package, suffix in ((hosts[0], '.dylib' if native.host['os'] == 'Darwin' else '.so'),
                            (targets[0], '.so')):
        manifest = (package/'+CONTENTS').read_text().splitlines()
        for module in modules:
            require('lib/ffmpeg9/pkgconfig/' + module + '.pc' in manifest and
                    'lib/ffmpeg9/' + module + suffix in manifest,
                    'shared FFmpeg package lacks ' + module)
    for module in modules:
        require(str(host_prefix/'lib/ffmpeg9/pkgconfig'/(module + '.pc')) in selection and
                (Path(buildlink)/'lib/pkgconfig'/(module + '.pc')).is_file(),
                'native FFmpeg pkg-config provider is not selected: ' + module)
    versions = []
    for role, prefix in (('host', Path(buildlink)), ('target', Path(options.sysroot)/'usr/pkg')):
        dirs = ([prefix/'lib/ffmpeg9/pkgconfig', prefix/'lib/pkgconfig']
                if role == 'target' else [prefix/'lib/pkgconfig'])
        env = dict(environment, PKG_CONFIG_LIBDIR=os.pathsep.join(map(str, dirs)))
        env.pop('PKG_CONFIG_PATH', None)
        if role == 'host':
            env.pop('PKG_CONFIG_SYSROOT_DIR', None)
        else:
            env['PKG_CONFIG_SYSROOT_DIR'] = str(options.sysroot)
        command = [native.tool('pkg-config')] + (['--define-prefix'] if role == 'host' else [])
        output = sdk['process'].capture(command + ['--modversion', *modules], env=env).stdout.decode().splitlines()
        require(len(output) == len(modules) and all(output), 'invalid FFmpeg pkg-config versions')
        versions.append(output)
    require(versions[0] == versions[1], 'host and target FFmpeg versions differ')
    identity = {'package': hosts[0].name, 'recipe': expected, 'versions': versions[0]}
    environment['EMBERBSD_FFMPEG_SOURCE_SHA256'] = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    environment['EMBERBSD_FFMPEG_TARGET_PKGCONFIG'] = 'yes'
    values = {'use_system_ffmpeg': True, 'is_component_ffmpeg': False}
    for role, package, prefix, suffix in (
            ('host', hosts[0], host_prefix, '.dylib' if native.host['os'] == 'Darwin' else '.so'),
            ('target', targets[0], Path(options.sysroot)/'usr/pkg', '.so')):
        manifest = (package/'+CONTENTS').read_text().splitlines()
        headers = [line for line in manifest if line.startswith('include/ffmpeg9/') and
                   not line.startswith('@') and line.endswith('.h')]
        require(headers, 'shared FFmpeg package has no public headers')
        libraries = [selected_owned_library(prefix, module + suffix, [package], 'lib/ffmpeg9')
                     for module in modules]
        files = []
        for entry in headers:
            path = (prefix/entry).resolve(strict=True)
            require(path.is_relative_to(prefix.resolve(strict=True)) and path.is_file(),
                    'shared FFmpeg header escapes selected prefix')
            index = manifest.index(entry)
            require(index + 1 < len(manifest) and
                    re.fullmatch(r'@comment MD5:[0-9a-f]{32}', manifest[index+1]),
                    'shared FFmpeg header has no package checksum: ' + entry)
            stream, info = sdk['paths'].open_regular(path)
            with stream:
                digest = hashlib.md5(stream.read(), usedforsecurity=False).hexdigest()
                require(sdk['paths'].stable_identity(os.fstat(stream.fileno())) == sdk['paths'].stable_identity(info),
                        'shared FFmpeg header changed during verification: ' + entry)
            sdk['paths'].verify_stable(path, info)
            require(digest == manifest[index+1].split(':', 1)[1],
                    'shared FFmpeg header differs from installed package: ' + entry)
            files.append(str(path))
        values['emberbsd_ffmpeg_' + role + '_libraries'] = libraries
        values['emberbsd_ffmpeg_' + role + '_inputs'] = sorted(set(files + libraries +
            [str(package/item) for item in ('+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION')]))
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
    native_suffix = '.dylib' if native.host['os'] == 'Darwin' else '.so'
    host_prefix = host_packages[0].parent.parent
    target_prefix = options.sysroot / 'usr/pkg'
    values = {'icu_use_data_file': False, 'v8_enable_temporal_systemicu': True}
    for role, prefix, suffix, owners in (('host', host_prefix, native_suffix, host_packages),
                                         ('target', target_prefix, '.so', packages[1:])):
        for name in ('icuuc', 'icui18n'):
            values['emberbsd_' + name + '_' + role + '_library'] = selected_owned_library(
                prefix, 'lib' + name + suffix, owners)
    return values


def common_re2(options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_re2', False):
        return {}
    require(buildlink, 'shared RE2 requires the selected native buildlink')
    versions = []
    for prefix, host in ((Path(buildlink), True), (options.sysroot / 'usr/pkg', False)):
        env = dict(environment, PKG_CONFIG_LIBDIR=str(prefix / 'lib/pkgconfig'))
        env.pop('PKG_CONFIG_PATH', None)
        env.pop('PKG_CONFIG_SYSROOT_DIR', None)
        command = [native.tool('pkg-config')] + (['--define-prefix'] if host else [])
        version = sdk['process'].capture(command + ['--modversion', 're2'], env=env).stdout.decode().strip()
        require(version, 'selected RE2 package has no version')
        versions.append(version)
    require(len(set(versions)) == 1, 'selected RE2 package versions differ')
    selection_work = environment.get('EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK')
    require(selection_work, 'shared RE2 needs host buildlink metadata')
    selection = json.loads((Path(selection_work) / 'selection.json').read_text())['identity']['inputs']
    hosts = [Path(name).resolve(strict=True).parent for name in selection
             if Path(name).name == '+BUILD_INFO' and
             'PKGPATH=devel/re2' in Path(name).read_text().splitlines()]
    require(len(hosts) == 1, 'ambiguous selected host RE2 package')
    db = options.sysroot / 'usr/pkg/pkgdb'
    targets = [path for path in db.iterdir() if (path / '+BUILD_INFO').is_file() and
               'PKGPATH=devel/re2' in (path / '+BUILD_INFO').read_text().splitlines()]
    require(len(targets) == 1, 'ambiguous selected target RE2 package')
    records = [(path / '+BUILD_VERSION').read_bytes() for path in hosts + targets]
    require(records[0] == records[1], 'host and target RE2 packages come from different recipes')
    distinfo = hashlib.sha256((options.host_buildlink_pkgsrc / 'devel/re2/distinfo').read_bytes()).hexdigest()
    require(('devel/re2/distinfo: ' + distinfo) in records[0].decode().splitlines(),
            'selected RE2 package distinfo differs from the shared recipe')
    environment['EMBERBSD_SHARED_RE2_VERSION'] = versions[0]
    environment['EMBERBSD_SHARED_RE2_SOURCE_SHA256'] = hashlib.sha256(records[0]).hexdigest()
    native_suffix = '.dylib' if native.host['os'] == 'Darwin' else '.so'
    return {'emberbsd_re2_host_library': selected_owned_library(hosts[0].parent.parent, 'libre2' + native_suffix, hosts),
            'emberbsd_re2_target_library': selected_owned_library(options.sysroot / 'usr/pkg', 'libre2.so', targets)}


def common_v8_metagen(options, sdk, native, environment, tools):
    selected = (getattr(options, 'v8_metagen_libclang_so', None),
                getattr(options, 'v8_metagen_bindings_dir', None),
                getattr(options, 'v8_metagen_runtime_view', None))
    if not any(selected):
        return {}
    require(all(selected) and options.v8_source,
            'V8 metagen requires common V8, selected libclang, bindings and runtime view')
    require(options.compiler_family == 'clang' and native.host['os'] == 'Darwin',
            'V8 metagen scoped selection requires Darwin and target Clang')
    prefix = (options.host_runtime_root or options.host_prefix).resolve(strict=True)
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
    extras = getattr(options, 'v8_metagen_runtime_extra', None) or []
    extra_paths = []
    for selected_file in extras:
        selected_file = absolute(selected_file, 'V8 metagen extra runtime input', directory=False)
        real = selected_file.resolve(strict=True)
        require(real.is_file() and real.is_relative_to(prefix), 'V8 metagen extra input outside selected host stage')
        relative = str(selected_file.relative_to(prefix))
        owners = [entry for entry in (prefix / 'pkgdb').iterdir()
                  if (entry / '+BUILD_INFO').is_file() and (entry / '+CONTENTS').is_file()
                  and relative in (entry / '+CONTENTS').read_text().splitlines()]
        require(len(owners) == 1, 'V8 metagen extra input has no unique package owner: ' + relative)
        actual.append(str(real))
        extra_paths.append(str(real.relative_to(prefix)))
    options.v8_metagen_selection = {'version': 1,
        'aliases': {entry.name: str(target.relative_to(prefix))
                    for entry, target in zip(entries, resolved)},
        'extra': sorted(set(extra_paths))}
    descriptor = str(Path(getattr(options, 'native_binding_root', options.work)) / 'v8-metagen-selection.json')
    actual.append(descriptor)
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
    helper = ((getattr(options, 'node_ports_source', None) or options.ports_source) /
              'scripts/source-inputs/node/configure-inputs.py').resolve(strict=True)
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


def platform_libcxx_hardening(options, sdk, host_binding, environment):
    """Check the selected native SDK headers for V8's extensive hardening."""
    source = b"""#include <__config>
#if !defined(_LIBCPP_VERSION) || !defined(_LIBCPP_HARDENING_MODE) || \
    !defined(_LIBCPP_HARDENING_MODE_EXTENSIVE) || _LIBCPP_HARDENING_MODE != _LIBCPP_HARDENING_MODE_EXTENSIVE
#error selected libc++ does not support extensive hardening
#endif
#define EMBER_ABI___1 1
#define EMBER_ABI_CAT_(x) EMBER_ABI_##x
#define EMBER_ABI_CAT(x) EMBER_ABI_CAT_(x)
#if EMBER_ABI_CAT(_LIBCPP_ABI_NAMESPACE) != 1
#error selected libc++ has the wrong ABI namespace
#endif
"""
    sdk['process'].capture([host_binding['cxx'], '-stdlib=libc++', '-isysroot', str(options.macos_sdk),
                            '-mmacosx-version-min=' + options.macos_minimum,
                            '-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_EXTENSIVE',
                            '-x', 'c++', '-fsyntax-only', '-'], env=environment, input=source)
    return True


DEVTOOLS_JS_ROOTS = {
    'acorn': 'devel/node-acorn',
    'js-yaml': 'devel/node-js-yaml', 'yargs': 'devel/node-yargs',
    'svgo': 'devel/node-svgo', 'uuid': 'devel/node-uuid',
    'cssnano': 'devel/node-cssnano',
    'postcss': 'devel/node-postcss', '@types/node': 'devel/node-types-node',
    'undici-types': 'devel/node-undici-types', '@types/estree': 'devel/node-types-estree',
    '@types/filesystem': 'devel/node-types-filesystem', '@types/filewriter': 'devel/node-types-filewriter',
    '@types/json-schema': 'devel/node-types-json-schema',
}


def devtools_provider_identity(options, sdk, native, environment):
    """Identify the selected common JavaScript closure using its owning helper."""
    projection = options.ports_source / 'profiles/common-build-tools/javascript-projection.py'
    pkg_admin = options.host_prefix / 'sbin/pkg_admin'
    sdk['host_prefix'].validate_host_executable(str(options.host_prefix), str(pkg_admin),
                                                native.host, search_path=native.path)
    command = [native.tool('python'), '-B', '-I', '-S', str(projection),
               '--prefix', str(options.host_prefix), '--node', native.tool('node'),
               '--pkg-admin', str(pkg_admin)]
    for name, pkgpath in sorted(DEVTOOLS_JS_ROOTS.items()):
        command += ['--root', name + '=' + pkgpath]
    data = json.loads(sdk['process'].capture(command, env=environment).stdout)
    require(data.get('schemaVersion') == 1 and isinstance(data.get('modules'), list),
            'invalid DevTools JavaScript projection')
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write_devtools_identity(work, sdk, environment):
    """Update the shared Ninja input only when provider identity changes."""
    path = Path(work) / 'devtools-provider.json'
    value = {'schemaVersion': 1, 'sha256': environment['EMBERBSD_DEVTOOLS_PROVIDER_SHA256']}
    require(not path.is_symlink(), 'DevTools provider input must be a regular file')
    if path.exists():
        require(path.is_file(), 'DevTools provider input must be a regular file')
        if json.loads(path.read_text()) == value:
            return
    sdk['jsonio'].write_json(str(path), value, exclusive=False)



def write_v8_metagen_selection(work, sdk, record):
    if record is None:
        return
    path = Path(work) / 'v8-metagen-selection.json'
    require(not path.is_symlink(), 'V8 metagen selection must be a regular file')
    if path.exists():
        require(path.is_file(), 'V8 metagen selection must be a regular file')
        if json.loads(path.read_text()) == record:
            return
    sdk['jsonio'].write_json(str(path), record, exclusive=False)


def protoc_selection(options, sdk, environment, values):
    """Fingerprint selected generator payloads, independent of installation times."""
    tool = values.get('emberbsd_protoc')
    if not tool:
        return
    work = Path(getattr(options, 'native_binding_root', options.work)).resolve(strict=True)
    roots = [(Path(options.host_prefix).resolve(strict=True), '$PREFIX'),
             (Path(options.sdk_source).resolve(strict=True), '$SDK'),
             (Path(options.sysroot).resolve(strict=True), '$SYSROOT'), (work, '$WORK')]
    for field, label in (('host_runtime_root', '$HOST_RUNTIME'),
                         ('protoc_runtime_view', '$PROTOC_RUNTIME_VIEW')):
        value = getattr(options, field, None)
        if value:
            roots.append((Path(value).resolve(strict=True), label))
    roots.sort(key=lambda item: len(item[0].parts), reverse=True)
    files = {}
    for name in [tool, *values.get('emberbsd_protoc_runtime_inputs', [])]:
        path = Path(name).resolve(strict=True)
        if path.name in ('+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION'):
            continue
        require(path.is_file(), 'selected protoc input is not a file: ' + str(path))
        key = next((label + '/' + str(path.relative_to(root)) for root, label in roots
                    if path.is_relative_to(root)), str(path))
        digest = sdk['inventory'].sha256_file(str(path))
        require(key not in files or files[key] == digest, 'ambiguous selected protoc input')
        files[key] = digest
    record = {'version': 1, 'files': dict(sorted(files.items()))}
    encoded = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
    environment['EMBERBSD_PROTOC_SELECTION_SHA256'] = hashlib.sha256(encoded).hexdigest()
    options.protoc_selection = record
    descriptor = str(work / 'protoc-selection.json')
    inputs = values.setdefault('emberbsd_protoc_runtime_inputs', [])
    require(descriptor not in inputs, 'duplicate protoc selection input')
    inputs.append(descriptor)
    inputs.sort()


def write_protoc_selection(work, sdk, record):
    path = Path(work) / 'protoc-selection.json'
    require(not path.is_symlink(), 'protoc selection input must be a regular file')
    if path.exists():
        require(path.is_file(), 'protoc selection input must be a regular file')
        if json.loads(path.read_text()) == record:
            return
    sdk['jsonio'].write_json(str(path), record, exclusive=False)


def additive_protoc_selection(old_arguments, new_arguments, work, *, runtime_change=False):
    path = str(Path(work) / 'protoc-selection.json')
    old = old_arguments.get('emberbsd_protoc_runtime_inputs', [])
    new = new_arguments.get('emberbsd_protoc_runtime_inputs', [])
    require(isinstance(old, list) and isinstance(new, list), 'invalid protoc selection input lists')
    if path in old:
        require(old.count(path) == new.count(path) == 1, 'protoc selection input changed')
        return set()
    require(new.count(path) == 1 and (runtime_change or sorted(new) == sorted(old + [path])),
            'protoc selection migration changed unrelated inputs')
    return {'emberbsd_protoc_runtime_inputs'}

def producer_inputs(options, sdk):
    native, environment, providers = _native_inputs(options, sdk)
    environment['EMBERBSD_DEVTOOLS_PROVIDER_SHA256'] = devtools_provider_identity(options, sdk, native, environment)
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
    values = arguments(options, native, tools, rust, launcher, providers=providers)
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
    values.update(common_re2(options, sdk, native, environment, buildlink))
    values.update(common_media_libraries(options, native, environment, buildlink))
    if not getattr(options, 'activate_common_providers', False):
        values.update(common_compression(options, sdk, native, environment, buildlink))
        values.update(common_ffmpeg(options, sdk, native, environment, buildlink))
        values.update(common_minizip(options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_xml', False):
            values.update(local_module('electron_xml_provider', 'xml-provider.py').select(
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library),
                options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_image', False):
            values.update(local_module('electron_image_provider', 'image-provider.py').select(
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library),
                options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_pdf_libraries', False):
            values.update(local_module('electron_pdfium_provider', 'pdfium-provider.py').select(
                local_module('electron_image_provider', 'image-provider.py'),
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library),
                options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_codecs', False):
            values.update(local_module('electron_codec_provider', 'codec-provider.py').select(
                local_module('electron_image_provider', 'image-provider.py'),
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library),
                options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_pffft', False):
            values.update(local_module('electron_codec_provider', 'codec-provider.py').select_pffft(
                local_module('electron_image_provider', 'image-provider.py'),
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library),
                options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_expat', False):
            values.update(local_module('electron_codec_provider', 'codec-provider.py').select_expat(
                local_module('electron_image_provider', 'image-provider.py'),
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library),
                options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_cpuinfo', False):
            values.update(local_module('electron_codec_provider', 'codec-provider.py').select_cpuinfo(
                local_module('electron_image_provider', 'image-provider.py'),
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library),
                options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_vulkan', False):
            values.update(local_module('electron_vulkan_provider', 'vulkan-provider.py').select(
                local_module('electron_image_provider', 'image-provider.py'),
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library),
                options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_woff2', False):
            values.update(local_module('electron_codec_provider', 'codec-provider.py').select_woff2(
                local_module('electron_image_provider', 'image-provider.py'),
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library),
                options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_snappy', False):
            values.update(local_module('electron_codec_provider', 'codec-provider.py').select_snappy(
                local_module('electron_image_provider', 'image-provider.py'),
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library),
                options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_spirv_tools', False):
            values.update(local_module('electron_codec_provider', 'codec-provider.py').select_spirv_tools(
                local_module('electron_image_provider', 'image-provider.py'),
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library,
                                      atomic_write=local_module('electron_protobuf_source_view',
                                                                'protobuf-source-view.py')._write_transaction_marker),
                options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_openh264', False):
            values.update(local_module('electron_codec_provider', 'codec-provider.py').select_openh264(
                local_module('electron_image_provider', 'image-provider.py'),
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library),
                options, sdk, native, environment, buildlink))
        if getattr(options, 'shared_font', False):
            values.update(local_module('electron_image_provider', 'image-provider.py').select_fonts(
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      selected_owned_library=selected_owned_library),
                options, sdk, native, environment, buildlink))
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
    host_tool_view = getattr(options, 'host_tool_runtime_view', None)
    if host_tool_view:
        require(runtime_view, 'Compiled host tools need the SDK launcher selected with protoc')
        view = absolute(host_tool_view, 'host tool runtime view')
        require(':' not in str(view), 'host tool runtime view cannot contain a colon')
        entries = sorted(view.iterdir())
        require(entries and all(item.is_file() for item in entries),
                'host tool runtime view must contain only files')
        actual = sorted({str(item.resolve(strict=True)) for item in entries})
        values.update(emberbsd_host_tool_runtime_launcher=values['emberbsd_protoc_runtime_launcher'],
                      emberbsd_host_tool_runtime_view=str(view),
                      emberbsd_host_tool_runtime_inputs=sorted(set(values['emberbsd_protoc_runtime_inputs'] + actual)))
    values.update(common_protobuf(options, sdk, native, environment, buildlink, runtime_view))
    protoc_selection(options, sdk, environment, values)
    values.update(common_undici(options, sdk, environment))
    values.update(common_embedder_sources(options, sdk, native, environment))
    values.update(common_ml_sources(options, sdk, native, environment))
    if not getattr(options, 'activate_common_providers', False):
        common_boringssl_source(options, sdk, native, environment)
        if any(getattr(options, name, None) for name in ('ots_source', 'ots_archive', 'ots_patch', 'ots_pkgsrc_export', 'ots_export_patch')):
            ots_view = local_module('electron_ots_source_view', 'ots-source-view.py')
            values.update(local_module('electron_ots_provider', 'ots-provider.py').select(
                types.SimpleNamespace(require=require, git=selected_control_git,
                                      source_environment=source_owner_environment,
                                      view=local_module('electron_protobuf_source_view', 'protobuf-source-view.py')),
                ots_view, options, sdk, native, environment))
        if any(getattr(options, name, None) for name in ('leveldb_source', 'leveldb_archive', 'leveldb_patch', 'leveldb_pkgsrc_export', 'leveldb_export_patch')):
            leveldb_view = local_module('electron_leveldb_source_view', 'leveldb-source-view.py')
            values.update(local_module('electron_leveldb_provider', 'leveldb-provider.py').select(
                types.SimpleNamespace(require=require, git=selected_control_git,
                                      source_environment=source_owner_environment,
                                      view=local_module('electron_protobuf_source_view', 'protobuf-source-view.py')),
                leveldb_view, options, sdk, native, environment))
        if getattr(options, 'shared_spirv_tools', False):
            require(all(getattr(options, name, None) for name in ('spirv_source', 'spirv_archive', 'spirv_patch')),
                    'shared SPIRV-Tools requires verified common source inputs')
            spirv_view = local_module('electron_spirv_source_view', 'spirv-source-view.py')
            values.update(local_module('electron_spirv_provider', 'spirv-provider.py').select(
                types.SimpleNamespace(require=require, git=selected_control_git,
                                      source_environment=source_owner_environment,
                                      view=local_module('electron_protobuf_source_view', 'protobuf-source-view.py')),
                spirv_view, options, sdk, native, environment))
        if any(getattr(options, name, None) for name in ('sqlite_source', 'sqlite_archive', 'sqlite_amalgamation', 'sqlite_patch', 'sqlite_pkgsrc_export', 'sqlite_export_patch')):
            sqlite_view = local_module('electron_sqlite_source_view', 'sqlite-source-view.py')
            local_module('electron_sqlite_provider', 'sqlite-provider.py').select(
                types.SimpleNamespace(require=require, validate_package_source=validate_package_source,
                                      git=selected_control_git, source_environment=source_owner_environment,
                                      view=local_module('electron_protobuf_source_view', 'protobuf-source-view.py')),
                sqlite_view, options, sdk, native, environment)
    values.update(common_v8_metagen(options, sdk, native, environment, tools))
    if options.compiler_family == 'clang':
        target_root = getattr(options, 'target_runtime_stage', None) or options.sysroot
        hardening_header(target_root, 'usr/pkg/llvm/include/c++/v1', '__1')
        values['external_libcxx_has_extensive_hardening'] = True
    if host_binding and native.host['os'] == 'Darwin' and options.host_compiler_family == 'clang':
        values.update(emberbsd_native_cpu={'aarch64': 'arm64', 'arm64': 'arm64',
                                           'amd64': 'x64', 'x86_64': 'x64'}[native.host['cpu']],
                      emberbsd_native_cc=host_binding['cc'], emberbsd_native_cxx=host_binding['cxx'],
                      emberbsd_native_libcxx_hardened=(bool(getattr(options, 'host_runtime_root', None)) or
                          platform_libcxx_hardening(options, sdk, host_binding, environment)))
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
        return {}
    src = Path(native.tool('dsymutil')).resolve(strict=True)
    dest = workspace / 'src/tools/clang/dsymutil/bin/dsymutil'
    if dest.exists() or dest.is_symlink():
        require(dest.is_symlink() and os.readlink(dest) == str(src),
                'existing dsymutil differs from selected native tool')
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(src)
    return {str(dest): str(src)}


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



def gn_source(options, *, retired=False, legacy_ml_root=None, refresh_selected=False, previous_view=None):
    require(previous_view is None or (getattr(options, 'phase', '') == 'configure' and
            not getattr(options, 'verify_selected_source_view', False) and
            Path(previous_view) == options.work.parent / 'source-view'),
            'previous source view is only available to an initial origin factory')
    require(not refresh_selected or (getattr(options, 'verify_selected_source_view', False) and
                                     not retired and legacy_ml_root is None),
            'selected refresh requires a new frozen source view')
    require(legacy_ml_root is None or getattr(options, 'verify_selected_source_view', False),
            'legacy ML recovery requires selected verification')
    require(not retired or getattr(options, 'verify_selected_source_view', False),
            'retired source view requires selected verification')
    common = getattr(options, 'protobuf_source', None)
    if not (common or getattr(options, 'node_source', None) or getattr(options, 'perfetto_source', None) or getattr(options, 'v8_source', None) or getattr(options, 'shared_abseil', False) or getattr(options, 'shared_icu', False) or getattr(options, 'shared_re2', False)):
        require(not retired, 'retired source view requires a mirrored view')
        return options.workspace / 'src'
    view = local_module('electron_protobuf_source_view', 'protobuf-source-view.py')
    sources = dict(node=getattr(options, 'node_source', None), perfetto=getattr(options, 'perfetto_source', None),
                   v8=getattr(options, 'v8_source', None),
                   system_abseil=getattr(options, 'shared_abseil', False),
                   system_icu=getattr(options, 'shared_icu', False),
                   system_re2=getattr(options, 'shared_re2', False),
                   node_modules=Path(options.host_prefix) / 'lib/node_modules',
                   protobuf_protoc=(Path(options.host_prefix) / 'bin/protoc') if common else None)
    destination = getattr(options, 'source_view_destination', options.work / 'source-view')
    require(destination.is_absolute() and destination.parent == options.work,
            'source view destination must be a sibling in the selected work directory')
    verify_selected = getattr(options, 'verify_selected_source_view', False)
    if verify_selected:
        require(not (retired or refresh_selected) or not any(destination.parent.glob('.' + destination.name + '.*-migration')),
                'selected source view refuses pending component migration')
        require(options.phase == 'build' and not any(getattr(options, name, False) for name in
                ('refresh_source_view', 'activate_common_ml', 'activate_common_providers',
                 'migrate_devtools_modules_only', 'resume_configure', 'retry_configure')),
                'selected source view requires frozen provider selections')
    def refresh_leaves(current):
        created = getattr(options, 'source_view_created_files', None)
        extra = ({'created_files': created,
                  'publication': options.source_view_publication} if created else {})
        links = getattr(options, 'source_view_created_links', None)
        if links:
            extra['created_links'] = links
        return view._refresh_leaves(options.workspace / 'src', common, destination,
                                    current, **extra)

    if getattr(options, 'activate_common_providers', False):
        require(options.phase == 'reconfigure', 'common provider activation requires reconfigure')
        return view.activate_common_components(options.workspace / 'src', common, destination, **sources)
    if getattr(options, 'migrate_devtools_modules_only', False):
        require(options.phase == 'reconfigure', 'DevTools migration requires reconfigure')
        return view.migrate_devtools_modules(options.workspace / 'src', common, destination, **sources)

    ids = getattr(options, 'ml_identities', None)
    if ids:
        ml = local_module('electron_ml_source_view', 'ml-source-view.py')
        headers = local_module('electron_header_source_view', 'header-source-view.py')
        selected = options.ml_headers
        boring = local_module('electron_boringssl_source_view', 'boringssl-source-view.py')
        old_boring = getattr(options, 'old_boringssl_identity', None)
        new_boring = options.boringssl_identity
        media = local_module('electron_media_header_view', 'media-header-view.py')
        media_selected = options.media_header_selections
        old_media = getattr(options, 'old_media_header_identities', None)
        new_media = {name: media.identity(media_selected, name) for name in media.NAMES}
        compression = local_module('electron_compression_source_view', 'compression-source-view.py')
        old_compression = getattr(options, 'old_compression_identity', None)
        new_compression = options.compression_identity
        old_pdf = bool(getattr(options, 'old_pdf_identity', None))
        new_pdf = bool(getattr(options, 'shared_pdf_libraries', False))
        require(new_pdf or not old_pdf, 'disabling shared PDF libraries requires a new source view')
        if new_pdf:
            require(getattr(options, 'pdf_identity', None), 'verified PDF library selection is missing')
        pdf_marker = destination.parent / ('.' + destination.name + '.pdfium-components-migration')
        old_font = bool(getattr(options, 'old_font_identity', None))
        new_font = bool(getattr(options, 'shared_font', False))
        require(new_font or not old_font, 'disabling shared font requires a new source view')
        font_marker = destination.parent / ('.' + destination.name + '.font-table-components-migration')
        font_view = (local_module('electron_font_table_view', 'font-table-view.py')
                     if old_font or new_font or old_pdf or new_pdf or os.path.lexists(font_marker) or os.path.lexists(pdf_marker) else None)
        font_table = getattr(options, 'font_table', None)
        old_codecs = bool(getattr(options, 'old_codec_identity', None))
        new_codecs = bool(getattr(options, 'shared_codecs', False))
        codec_names = ('dav1d', 'libaom', 'libvpx', 'opus', 'flac')
        codec_marker = destination.parent / ('.' + destination.name + '.codec-components-migration')
        old_pffft = bool(getattr(options, 'old_pffft_identity', None))
        new_pffft = bool(getattr(options, 'shared_pffft', False))
        pffft_names = ('pffft',)
        pffft_marker = destination.parent / ('.' + destination.name + '.pffft-components-migration')
        old_expat = bool(getattr(options, 'old_expat_identity', None))
        new_expat = bool(getattr(options, 'shared_expat', False))
        expat_names = ('expat',)
        expat_marker = destination.parent / ('.' + destination.name + '.expat-components-migration')
        old_cpuinfo = bool(getattr(options, 'old_cpuinfo_identity', None))
        new_cpuinfo = bool(getattr(options, 'shared_cpuinfo', False))
        cpuinfo_names = ('cpuinfo',)
        cpuinfo_marker = destination.parent / ('.' + destination.name + '.cpuinfo-components-migration')
        old_vulkan = bool(getattr(options, 'old_vulkan_identity', None))
        new_vulkan = bool(getattr(options, 'shared_vulkan', False))
        vulkan_names = ('vulkan-loader', 'vulkan-headers')
        vulkan_marker = destination.parent / ('.' + destination.name + '.vulkan-components-migration')
        require(new_vulkan or not old_vulkan, 'disabling shared Vulkan requires a new source view')
        vulkan_registry = getattr(options, 'vulkan_registry', None)
        if old_vulkan or new_vulkan:
            require(vulkan_registry is not None, 'verified Vulkan registry is missing')
        old_woff2 = bool(getattr(options, 'old_woff2_identity', None))
        new_woff2 = bool(getattr(options, 'shared_woff2', False))
        woff2_names = ('woff2',)
        woff2_marker = destination.parent / ('.' + destination.name + '.woff2-components-migration')
        old_snappy = bool(getattr(options, 'old_snappy_identity', None))
        new_snappy = bool(getattr(options, 'shared_snappy', False))
        snappy_names = ('snappy',)
        snappy_marker = destination.parent / ('.' + destination.name + '.snappy-components-migration')
        old_openh264 = bool(getattr(options, 'old_openh264_identity', None))
        new_openh264 = bool(getattr(options, 'shared_openh264', False))
        openh264_names = ('openh264',)
        openh264_marker = destination.parent / ('.' + destination.name + '.openh264-components-migration')
        old_image = bool(getattr(options, 'old_image_identity', None))
        new_image = bool(getattr(options, 'shared_image', False))
        image_names = ('libwebp',)
        image_marker = destination.parent / ('.' + destination.name + '.image-components-migration')
        old_ots = getattr(options, 'old_ots_selection', None)
        new_ots = getattr(options, 'ots_selection', None)
        ots_marker = destination.parent / ('.' + destination.name + '.ots-components-migration')
        ots = (local_module('electron_ots_source_view', 'ots-source-view.py')
               if old_ots or new_ots or os.path.lexists(ots_marker) else None)
        old_leveldb = getattr(options, 'old_leveldb_selection', None)
        new_leveldb = getattr(options, 'leveldb_selection', None)
        leveldb_marker = destination.parent / ('.' + destination.name + '.leveldb-components-migration')
        leveldb = (local_module('electron_leveldb_source_view', 'leveldb-source-view.py')
               if old_leveldb or new_leveldb or os.path.lexists(leveldb_marker) else None)
        old_spirv = getattr(options, 'old_spirv_selection', None)
        new_spirv = getattr(options, 'spirv_selection', None)
        spirv_marker = destination.parent / ('.' + destination.name + '.spirv-components-migration')
        spirv = (local_module('electron_spirv_source_view', 'spirv-source-view.py')
               if old_spirv or new_spirv or os.path.lexists(spirv_marker) else None)
        old_sqlite = getattr(options, 'old_sqlite_selection', None)
        new_sqlite = getattr(options, 'sqlite_selection', None)
        sqlite_marker = destination.parent / ('.' + destination.name + '.sqlite-components-migration')
        sqlite = (local_module('electron_sqlite_source_view', 'sqlite-source-view.py')
                  if old_sqlite or new_sqlite or os.path.lexists(sqlite_marker) else None)
        old_xml = bool(getattr(options, 'old_xml_identity', None))
        new_xml = bool(getattr(options, 'shared_xml', False))
        xml_names = ('libxml', 'libxslt')
        xml_marker = destination.parent / ('.' + destination.name + '.xml-components-migration')
        old_minizip = bool(getattr(options, 'old_minizip_identity', None))
        new_minizip = bool(getattr(options, 'shared_minizip', False))
        minizip_marker = destination.parent / ('.' + destination.name + '.minizip-components-migration')
        old_ffmpeg = bool(getattr(options, 'old_ffmpeg_identity', None))
        new_ffmpeg = bool(getattr(options, 'shared_ffmpeg', False))
        ffmpeg_marker = destination.parent / ('.' + destination.name + '.ffmpeg-components-migration')
        compression_marker = destination.parent / ('.' + destination.name + '.compression-components-migration')
        if verify_selected:
            # Identities are selected and verified before this selected-view pass.
            # Equal old/new state prevents activation and runs every existing
            # component verifier against the supplied view.
            old_boring, old_media, old_compression = new_boring, new_media, new_compression
            old_pdf, old_font, old_codecs = new_pdf, new_font, new_codecs
            old_pffft, old_expat, old_cpuinfo = new_pffft, new_expat, new_cpuinfo
            old_vulkan, old_woff2, old_snappy = new_vulkan, new_woff2, new_snappy
            old_openh264, old_image, old_xml = new_openh264, new_image, new_xml
            old_minizip, old_ffmpeg = new_minizip, new_ffmpeg
            old_ots, old_leveldb, old_spirv, old_sqlite = new_ots, new_leveldb, new_spirv, new_sqlite
        compression_root = destination / 'src/third_party'
        if (new_pffft and not old_pffft and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(pffft_marker) and
                all((compression_root/name).is_dir() and not (compression_root/name).is_symlink()
                    for name in pffft_names)):
            compression.verify_view(view, options.workspace / 'src', destination, pffft_names)
            old_pffft = True
        if (new_expat and not old_expat and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(expat_marker) and
                all((compression_root/name).is_dir() and not (compression_root/name).is_symlink()
                    for name in expat_names)):
            compression.verify_view(view, options.workspace / 'src', destination, expat_names)
            old_expat = True
        if (new_cpuinfo and not old_cpuinfo and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(cpuinfo_marker) and
                all((compression_root/name).is_dir() and not (compression_root/name).is_symlink()
                    for name in cpuinfo_names)):
            compression.verify_view(view, options.workspace / 'src', destination, cpuinfo_names)
            old_cpuinfo = True
        if (new_vulkan and not old_vulkan and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(vulkan_marker) and
                all((compression_root/name).is_dir() and not (compression_root/name).is_symlink()
                    for name in vulkan_names)):
            compression.verify_view(view, options.workspace / 'src', destination, vulkan_names, registry=vulkan_registry)
            old_vulkan = True
        if (new_woff2 and not old_woff2 and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(woff2_marker) and
                all((compression_root/name).is_dir() and not (compression_root/name).is_symlink()
                    for name in woff2_names)):
            compression.verify_view(view, options.workspace / 'src', destination, woff2_names)
            old_woff2 = True
        if (new_snappy and not old_snappy and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(snappy_marker) and
                all((compression_root/name).is_dir() and not (compression_root/name).is_symlink()
                    for name in snappy_names)):
            compression.verify_view(view, options.workspace / 'src', destination, snappy_names)
            old_snappy = True
        if (new_openh264 and not old_openh264 and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(openh264_marker) and
                all((compression_root/name).is_dir() and not (compression_root/name).is_symlink()
                    for name in openh264_names)):
            compression.verify_view(view, options.workspace / 'src', destination, openh264_names)
            old_openh264 = True
        if (new_codecs and not old_codecs and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(codec_marker) and
                all((compression_root/name).is_dir() and not (compression_root/name).is_symlink()
                    for name in codec_names)):
            compression.verify_view(view, options.workspace / 'src', destination, codec_names)
            old_codecs = True
        if (new_image and not old_image and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(image_marker) and
                all((compression_root/name).is_dir() and not (compression_root/name).is_symlink()
                    for name in image_names)):
            compression.verify_view(view, options.workspace / 'src', destination, image_names)
            old_image = True
        if (new_xml and not old_xml and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(xml_marker) and
                all((compression_root/name).is_dir() and not (compression_root/name).is_symlink()
                    for name in xml_names)):
            compression.verify_view(view, options.workspace / 'src', destination, xml_names)
            old_xml = True
        ffmpeg_root = compression_root / 'ffmpeg'
        if (new_ffmpeg and not old_ffmpeg and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(ffmpeg_marker) and ffmpeg_root.is_dir() and
                not ffmpeg_root.is_symlink()):
            # GN can fail after this exact projection was committed but before
            # the configuration receipt was replaced. Reject any foreign view.
            compression.verify_view(view, options.workspace / 'src', destination, ('ffmpeg',))
            old_ffmpeg = True
        ots_root = compression_root / 'ots'
        if (new_ots and old_ots != new_ots and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(ots_marker) and ots_root.is_dir() and not ots_root.is_symlink()):
            try:
                ots.verify_view(view, options.workspace / 'src', destination, new_ots, options.ml_sdk['sourceprep'])
            except (ValueError, OSError):
                require(old_ots is not None, 'foreign OTS projection during recovery')
                ots.verify_view(view, options.workspace / 'src', destination, old_ots, options.ml_sdk['sourceprep'])
            else:
                old_ots = new_ots
        leveldb_root = compression_root / 'leveldatabase'
        if (new_leveldb and old_leveldb != new_leveldb and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(leveldb_marker) and leveldb_root.is_dir() and not leveldb_root.is_symlink()):
            try:
                leveldb.verify_view(view, options.workspace / 'src', destination, new_leveldb, options.ml_sdk['sourceprep'])
            except (ValueError, OSError):
                require(old_leveldb is not None, 'foreign LEVELDB projection during recovery')
                leveldb.verify_view(view, options.workspace / 'src', destination, old_leveldb, options.ml_sdk['sourceprep'])
            else:
                old_leveldb = new_leveldb
        spirv_root = compression_root / 'spirv-tools'
        if (new_spirv and old_spirv != new_spirv and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(spirv_marker) and spirv_root.is_dir() and not spirv_root.is_symlink()):
            try:
                spirv.verify_view(view, options.workspace / 'src', destination, new_spirv, options.ml_sdk['sourceprep'])
            except (ValueError, OSError):
                require(old_spirv is not None, 'foreign SPIRV projection during recovery')
                spirv.verify_view(view, options.workspace / 'src', destination, old_spirv, options.ml_sdk['sourceprep'])
            else:
                old_spirv = new_spirv
        sqlite_root = compression_root / 'sqlite'
        if (new_sqlite and old_sqlite != new_sqlite and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(sqlite_marker) and sqlite_root.is_dir() and not sqlite_root.is_symlink()):
            try:
                sqlite.verify_view(view, options.workspace / 'src', destination, new_sqlite)
            except (ValueError, OSError):
                if old_sqlite is None and options.phase == 'configure' and (
                        getattr(options, 'retry_configure', False) or
                        getattr(options, 'resume_configure', False)):
                    old_sqlite = sqlite.recover_equivalent_initial(
                        view, options.workspace / 'src', destination, new_sqlite)
                require(old_sqlite is not None, 'foreign SQLite projection during recovery')
                sqlite.verify_view(view, options.workspace / 'src', destination, old_sqlite)
            else:
                old_sqlite = new_sqlite
        minizip_root = compression_root / 'zlib'
        if (new_minizip and not old_minizip and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(minizip_marker) and minizip_root.is_dir() and
                not minizip_root.is_symlink()):
            compression.verify_view(view, options.workspace / 'src', destination, ('zlib',))
            old_minizip = True
        if (old_compression is None and not os.path.lexists(compression_marker) and
                all((compression_root/name).is_dir() and not (compression_root/name).is_symlink()
                    for name in compression.NAMES)):
            # A configure retry can find a completed projection before the
            # final configuration receipt was written.
            compression.verify_view(view, options.workspace / 'src', destination)
            old_compression = new_compression
        if (new_font and not old_font and not new_pdf and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                not os.path.lexists(font_marker) and
                (compression_root/'pdfium').is_dir() and not (compression_root/'pdfium').is_symlink()):
            font_view.verify_view(view, options.workspace / 'src', destination, font_table)
            old_font = True
        if (new_pdf and not old_pdf and not os.path.lexists(pdf_marker) and
                not os.path.lexists(font_marker) and
                (options.phase == 'reconfigure' or
                 (options.phase == 'configure' and (getattr(options, 'retry_configure', False) or
                                                    getattr(options, 'resume_configure', False)))) and
                (compression_root/'pdfium').is_dir() and not (compression_root/'pdfium').is_symlink()):
            try:
                font_view.verify_pdfium(view, options.workspace / 'src', destination,
                                        font_table if new_font else None, True)
            except (ValueError, OSError):
                require((old_font or new_font) and font_table is not None,
                        'foreign PDFium projection during recovery')
                font_view.verify_view(view, options.workspace / 'src', destination, font_table)
                old_font = True
            else:
                old_pdf, old_font = True, new_font
        old_ml = getattr(options, 'old_ml_identities', None)
        old_headers = getattr(options, 'old_header_identities', None)
        new_headers = {name: data['identity'] for name, data in selected.items()}
        if verify_selected:
            old_ml, old_headers = ids, new_headers
        sp = options.ml_sdk['sourceprep']
        boring_marker = destination.parent / ('.' + destination.name + '.boringssl-components-migration')
        boring_root = compression_root / boring.NAME
        if (old_boring is None and not os.path.lexists(boring_marker) and
                boring_root.is_dir() and not boring_root.is_symlink()):
            # The projection can finish before the configuration receipt is saved.
            boring.verify_view(view, options.workspace / 'src', destination, new_boring, sp)
            old_boring = new_boring
        def selected_sources(ml_ids, header_ids, media_ids=None, compression_id=None, boring_id=None):
            result = dict(sources)
            checks, names = [], []
            if ml_ids:
                names.extend(ml.NAMES)
                checks.append(lambda: ml.verify_view(view, options.workspace / 'src', destination, ml_ids, sp,
                                                     **({'legacy_root': legacy_ml_root} if legacy_ml_root is not None else {})))
            if header_ids:
                names.extend(headers.NAMES)
                records = {name: dict(selected[name], identity=header_ids[name]) for name in headers.NAMES}
                checks.append(lambda: headers.verify_view(view, options.workspace / 'src', destination, records, sp))
            if media_ids:
                names.extend(media.NAMES)
                checks.append(lambda: media.verify_view(view, options.workspace / 'src', destination, media_ids, sp))
            if boring_id:
                names.append(boring.NAME)
                checks.append(lambda: boring.verify_view(view, options.workspace / 'src', destination, boring_id, sp))
            if old_font or old_pdf:
                names.append(font_view.NAME)
                if old_pdf:
                    checks.append(lambda: font_view.verify_pdfium(view, options.workspace / 'src', destination,
                                                                font_table if old_font else None, True))
                else:
                    checks.append(lambda: font_view.verify_view(view, options.workspace / 'src', destination, font_table))
            if old_ots:
                names.append(ots.NAME)
                checks.append(lambda: ots.verify_view(view, options.workspace / 'src', destination, old_ots, sp))
            if old_leveldb:
                names.append(leveldb.NAME)
                checks.append(lambda: leveldb.verify_view(view, options.workspace / 'src', destination, old_leveldb, sp))
            if old_spirv:
                names.append(spirv.NAME)
                checks.append(lambda: spirv.verify_view(view, options.workspace / 'src', destination, old_spirv, sp))
            if old_sqlite:
                names.append(sqlite.NAME)
                checks.append(lambda: sqlite.verify_view(view, options.workspace / 'src', destination, old_sqlite))
            if old_pffft:
                names.extend(pffft_names)
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination, pffft_names))
            if old_expat:
                names.extend(expat_names)
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination, expat_names))
            if old_cpuinfo:
                names.extend(cpuinfo_names)
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination, cpuinfo_names))
            if old_vulkan:
                names.extend(vulkan_names)
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination, vulkan_names, registry=vulkan_registry))
            if old_woff2:
                names.extend(woff2_names)
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination, woff2_names))
            if old_snappy:
                names.extend(snappy_names)
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination, snappy_names))
            if old_openh264:
                names.extend(openh264_names)
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination, openh264_names))
            if old_codecs:
                names.extend(codec_names)
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination, codec_names))
            if old_image:
                names.extend(image_names)
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination, image_names))
            if old_xml:
                names.extend(xml_names)
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination, xml_names))
            if old_minizip:
                names.append('zlib')
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination, ('zlib',)))
            if old_ffmpeg:
                names.append('ffmpeg')
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination, ('ffmpeg',)))
            if compression_id:
                names.extend(compression.NAMES)
                checks.append(lambda: compression.verify_view(view, options.workspace / 'src', destination))
            if names:
                result.update(ml_names=names, ml_verify=lambda: [check() for check in checks])
            return result
        selection_refreshed = False
        selection_verified = False
        selection_needs_final = False
        # Pending recovery always takes the original full verification path.
        # The memo is scoped to this locked invocation and still forces a final check.
        clean_selection = (not getattr(options, 'resume_configure', False) and
                           not getattr(options, 'retry_configure', False) and
                           not os.path.lexists(destination.parent / ('.' + destination.name + '-refresh-incomplete')) and
                           not any(destination.parent.glob('.' + destination.name + '.*-migration')))
        fresh_selection = (clean_selection and options.phase == 'configure' and
                           not getattr(options, 'refresh_source_view', False) and
                           not os.path.lexists(destination))
        reuse_selection = (clean_selection and options.phase == 'reconfigure' and
                           os.path.lexists(destination))
        selection_default = object()
        def verify_selection(ml_ids, header_ids, media_ids=old_media, compression_id=selection_default, boring_id=selection_default, *, force=False):
            nonlocal selection_refreshed, selection_verified, selection_needs_final
            if reuse_selection and selection_verified and not force:
                selection_needs_final = True
                return destination / 'src'
            if compression_id is selection_default:
                compression_id = old_compression
            if boring_id is selection_default:
                boring_id = old_boring
            current = selected_sources(ml_ids, header_ids, media_ids, compression_id, boring_id)
            if (getattr(options, 'refresh_source_view', False) and
                    options.phase == 'reconfigure' and not selection_refreshed):
                result = refresh_leaves(current)
                selection_refreshed = True
            else:
                result = view.verify(options.workspace / 'src', common, destination, **current)
            selection_verified = True
            selection_needs_final = False
            return result
        def finish_selection(result):
            if selection_needs_final:
                return verify_selection(ids, new_headers, new_media, new_compression, new_boring, force=True)
            return result
        if os.path.lexists(font_marker):
            require(new_font and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'font table transaction recovery requires shared font reconfigure')
            font_view.activate(view, options.workspace / 'src', destination, font_table,
                               lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring))
            old_font = True
        if os.path.lexists(pdf_marker):
            require(new_pdf and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'PDFium transaction recovery requires shared PDF libraries reconfigure')
            font_view.activate_pdfium(view, options.workspace / 'src', destination,
                                      font_table if old_font else None, old_pdf,
                                      font_table if new_font else None, new_pdf,
                                      lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring))
            old_pdf, old_font = new_pdf, new_font
        if os.path.lexists(ots_marker):
            require(new_ots and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'OTS transaction recovery requires selected OTS reconfigure')
            ots.activate(view, options.workspace / 'src', destination, new_ots, old_ots, sp,
                         lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring))
            old_ots = new_ots
        if os.path.lexists(leveldb_marker):
            require(new_leveldb and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'LEVELDB transaction recovery requires selected LEVELDB reconfigure')
            leveldb.activate(view, options.workspace / 'src', destination, new_leveldb, old_leveldb, sp,
                         lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring))
            old_leveldb = new_leveldb
        if os.path.lexists(spirv_marker):
            require(new_spirv and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'SPIRV transaction recovery requires selected SPIRV reconfigure')
            spirv.activate(view, options.workspace / 'src', destination, new_spirv, old_spirv, sp,
                         lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring))
            old_spirv = new_spirv
        if os.path.lexists(sqlite_marker):
            require(new_sqlite and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'SQLite transaction recovery requires selected SQLite reconfigure')
            sqlite.activate(view, options.workspace / 'src', destination, new_sqlite, old_sqlite,
                            lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring))
            old_sqlite = new_sqlite
        if os.path.lexists(pffft_marker):
            require(new_pffft and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'PFFFT transaction recovery requires shared PFFFT reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                                 pffft_names, 'pffft-components')
            old_pffft = True
        if os.path.lexists(expat_marker):
            require(new_expat and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'EXPAT transaction recovery requires shared EXPAT reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                                 expat_names, 'expat-components')
            old_expat = True
        if os.path.lexists(cpuinfo_marker):
            require(new_cpuinfo and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'CPUINFO transaction recovery requires shared CPUINFO reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                                 cpuinfo_names, 'cpuinfo-components')
            old_cpuinfo = True
        if os.path.lexists(vulkan_marker):
            require(new_vulkan and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'VULKAN transaction recovery requires shared VULKAN reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                                 vulkan_names, 'vulkan-components', registry=vulkan_registry)
            old_vulkan = True
        if os.path.lexists(woff2_marker):
            require(new_woff2 and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'WOFF2 transaction recovery requires shared WOFF2 reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                                 woff2_names, 'woff2-components')
            old_woff2 = True
        if os.path.lexists(snappy_marker):
            require(new_snappy and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'SNAPPY transaction recovery requires shared SNAPPY reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                                 snappy_names, 'snappy-components')
            old_snappy = True
        if os.path.lexists(openh264_marker):
            require(new_openh264 and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'OpenH264 transaction recovery requires shared OpenH264 reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                                 openh264_names, 'openh264-components')
            old_openh264 = True
        if os.path.lexists(codec_marker):
            require(new_codecs and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'codec transaction recovery requires shared codecs reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                                 codec_names, 'codec-components')
            old_codecs = True
        if os.path.lexists(image_marker):
            require(new_image and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'image transaction recovery requires shared image reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                                 image_names, 'image-components')
            old_image = True
        if os.path.lexists(xml_marker):
            require(new_xml and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'XML transaction recovery requires shared XML reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                                 xml_names, 'xml-components')
            old_xml = True
        if os.path.lexists(ffmpeg_marker):
            require(new_ffmpeg and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'FFmpeg transaction recovery requires shared FFmpeg reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                                 ('ffmpeg',), 'ffmpeg-components')
            old_ffmpeg = True
        if os.path.lexists(minizip_marker):
            require(new_minizip and (options.phase == 'reconfigure' or
                    getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)),
                    'minizip transaction recovery requires shared minizip reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                                 ('zlib',), 'minizip-components')
            old_minizip = True
        if os.path.lexists(boring_marker):
            require(options.phase == 'reconfigure' or getattr(options, 'resume_configure', False) or
                    getattr(options, 'retry_configure', False),
                    'BoringSSL transaction recovery requires configure or reconfigure')
            boring.activate(view, options.workspace / 'src', destination, options.boringssl_selected,
                            new_boring, options.ml_sdk['inventory'], sp,
                            lambda: verify_selection(old_ml, old_headers, old_media, old_compression, old_boring),
                            old_digest=old_boring)
            old_boring = new_boring
        if os.path.lexists(compression_marker):
            require(options.phase == 'reconfigure' or getattr(options, 'resume_configure', False) or
                    getattr(options, 'retry_configure', False),
                    'compression transaction recovery requires configure or reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, None))
            old_compression = new_compression
        new_view = not os.path.lexists(destination)
        if new_view:
            require(getattr(options, 'phase', '') == 'configure', 'common source view is missing')
            view.create(options.workspace / 'src', common, destination, **sources,
                        previous_view=previous_view, created_files=getattr(options, 'source_view_created_files', None))
            # Only a successfully created view in a fresh ordinary configure
            # may reuse verified selections within this invocation.
            if fresh_selection:
                reuse_selection = True
        initial = getattr(options, 'resume_configure', False) or getattr(options, 'retry_configure', False)
        transition = (new_view or getattr(options, 'activate_common_ml', False) or
                      (old_ml is not None and (old_ml != ids or old_headers != new_headers)))
        if initial and not transition:
            marker = destination.parent / ('.' + destination.name + '.ml-components-migration')
            header_marker = destination.parent / ('.' + destination.name + '.header-components-migration')
            legacy = all((destination/'src/third_party'/name).is_symlink() for name in ml.NAMES)
            transition = os.path.lexists(marker) or os.path.lexists(header_marker) or legacy
            if legacy and not os.path.lexists(marker):
                view.complete_initial(options.workspace / 'src', common, destination, **sources)
        if transition:
            if not new_view and not initial:
                require(options.phase == 'reconfigure', 'ML transition requires reconfigure')
            ml.activate(view, options.workspace / 'src', destination, options.ml_sources, ids,
                options.ml_sdk['inventory'], sp, lambda: verify_selection(old_ml, old_headers),
                old_identities=old_ml)
            headers.activate(view, options.workspace / 'src', destination, selected,
                options.ml_sdk['inventory'], sp, lambda: verify_selection(ids, old_headers),
                old_identities=old_headers)
            transition_result = verify_selection(ids, new_headers)
        media_marker = destination.parent / ('.' + destination.name + '.media-header-components-migration')
        if old_media != new_media or os.path.lexists(media_marker):
            require(options.phase == 'reconfigure' or new_view or initial,
                    'media header transition requires reconfigure')
            media.activate(view, options.workspace / 'src', destination, media_selected,
                           options.ml_sdk['inventory'], sp,
                           lambda: verify_selection(ids, new_headers, old_media),
                           old_identities=old_media)
            transition_result = verify_selection(ids, new_headers, new_media)
            transition = True
        compression_transition = old_compression != new_compression or os.path.lexists(compression_marker)
        if compression_transition:
            require(options.phase == 'reconfigure' or new_view or initial,
                    'compression transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, old_compression))
            verify_selection(ids, new_headers, new_media, new_compression)
        if not new_pdf and (old_font != new_font or os.path.lexists(font_marker)):
            require(new_font, 'disabling shared font requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'font table transition requires reconfigure')
            font_view.activate(view, options.workspace / 'src', destination, font_table,
                               lambda: verify_selection(ids, new_headers, new_media, new_compression))
            old_font = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_pdf != new_pdf or (new_pdf and old_font != new_font) or os.path.lexists(pdf_marker):
            require(new_pdf, 'disabling shared PDF libraries requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'PDFium transition requires reconfigure')
            font_view.activate_pdfium(view, options.workspace / 'src', destination,
                                      font_table if old_font else None, old_pdf,
                                      font_table if new_font else None, new_pdf,
                                      lambda: verify_selection(ids, new_headers, new_media, new_compression))
            old_pdf, old_font = new_pdf, new_font
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_ots != new_ots or os.path.lexists(ots_marker):
            require(new_ots, 'disabling common OTS requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'OTS transition requires reconfigure')
            ots.activate(view, options.workspace / 'src', destination, new_ots, old_ots, sp,
                         lambda: verify_selection(ids, new_headers, new_media, new_compression))
            old_ots = new_ots
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_leveldb != new_leveldb or os.path.lexists(leveldb_marker):
            require(new_leveldb, 'disabling common LEVELDB requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'LEVELDB transition requires reconfigure')
            leveldb.activate(view, options.workspace / 'src', destination, new_leveldb, old_leveldb, sp,
                         lambda: verify_selection(ids, new_headers, new_media, new_compression))
            old_leveldb = new_leveldb
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_spirv != new_spirv or os.path.lexists(spirv_marker):
            require(new_spirv, 'disabling common SPIRV requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'SPIRV transition requires reconfigure')
            spirv.activate(view, options.workspace / 'src', destination, new_spirv, old_spirv, sp,
                         lambda: verify_selection(ids, new_headers, new_media, new_compression))
            old_spirv = new_spirv
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_sqlite != new_sqlite or os.path.lexists(sqlite_marker):
            require(new_sqlite, 'disabling common SQLite requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'SQLite transition requires reconfigure')
            sqlite.activate(view, options.workspace / 'src', destination, new_sqlite, old_sqlite,
                            lambda: verify_selection(ids, new_headers, new_media, new_compression))
            old_sqlite = new_sqlite
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_ffmpeg != new_ffmpeg or os.path.lexists(ffmpeg_marker):
            require(new_ffmpeg, 'disabling shared FFmpeg requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'FFmpeg transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, new_compression),
                                 ('ffmpeg',), 'ffmpeg-components')
            old_ffmpeg = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_minizip != new_minizip or os.path.lexists(minizip_marker):
            require(new_minizip, 'disabling shared minizip requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'minizip transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, new_compression),
                                 ('zlib',), 'minizip-components')
            old_minizip = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_pffft != new_pffft or os.path.lexists(pffft_marker):
            require(new_pffft, 'disabling shared PFFFT requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'PFFFT transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, new_compression),
                                 pffft_names, 'pffft-components')
            old_pffft = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_expat != new_expat or os.path.lexists(expat_marker):
            require(new_expat, 'disabling shared EXPAT requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'EXPAT transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, new_compression),
                                 expat_names, 'expat-components')
            old_expat = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_cpuinfo != new_cpuinfo or os.path.lexists(cpuinfo_marker):
            require(new_cpuinfo, 'disabling shared CPUINFO requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'CPUINFO transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, new_compression),
                                 cpuinfo_names, 'cpuinfo-components')
            old_cpuinfo = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_vulkan != new_vulkan or os.path.lexists(vulkan_marker):
            require(new_vulkan, 'disabling shared VULKAN requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'VULKAN transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, new_compression),
                                 vulkan_names, 'vulkan-components', registry=vulkan_registry)
            old_vulkan = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_woff2 != new_woff2 or os.path.lexists(woff2_marker):
            require(new_woff2, 'disabling shared WOFF2 requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'WOFF2 transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, new_compression),
                                 woff2_names, 'woff2-components')
            old_woff2 = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_snappy != new_snappy or os.path.lexists(snappy_marker):
            require(new_snappy, 'disabling shared SNAPPY requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'SNAPPY transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, new_compression),
                                 snappy_names, 'snappy-components')
            old_snappy = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_openh264 != new_openh264 or os.path.lexists(openh264_marker):
            require(new_openh264, 'disabling shared OpenH264 requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'OpenH264 transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, new_compression),
                                 openh264_names, 'openh264-components')
            old_openh264 = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_codecs != new_codecs or os.path.lexists(codec_marker):
            require(new_codecs, 'disabling shared codecs requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'codec transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, new_compression),
                                 codec_names, 'codec-components')
            old_codecs = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_image != new_image or os.path.lexists(image_marker):
            require(new_image, 'disabling shared image requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'image transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, new_compression),
                                 image_names, 'image-components')
            old_image = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_xml != new_xml or os.path.lexists(xml_marker):
            require(new_xml, 'disabling shared XML requires a new source view')
            require(options.phase == 'reconfigure' or new_view or initial,
                    'XML transition requires reconfigure')
            compression.activate(view, options.workspace / 'src', destination,
                                 lambda: verify_selection(ids, new_headers, new_media, new_compression),
                                 xml_names, 'xml-components')
            old_xml = True
            transition_result = verify_selection(ids, new_headers, new_media, new_compression)
            transition = True
        if old_boring != new_boring or os.path.lexists(boring_marker):
            require(options.phase == 'reconfigure' or new_view or initial,
                    'BoringSSL source transition requires reconfigure')
            boring.activate(view, options.workspace / 'src', destination, options.boringssl_selected,
                            new_boring, options.ml_sdk['inventory'], sp,
                            lambda: verify_selection(ids, new_headers, new_media, new_compression, old_boring),
                            old_digest=old_boring)
            return finish_selection(verify_selection(ids, new_headers, new_media, new_compression, new_boring))
        if compression_transition:
            return finish_selection(verify_selection(ids, new_headers, new_media, new_compression, new_boring))
        if transition:
            return finish_selection(transition_result)
        sources = selected_sources(ids, new_headers, new_media, new_compression, new_boring)
    if refresh_selected:
        return refresh_leaves(sources)
    if getattr(options, 'refresh_source_view', False):
        require(options.phase == 'reconfigure', 'source refresh requires reconfigure')
        if (ids or getattr(options, 'source_view_created_files', None) or
                getattr(options, 'source_view_created_links', None)):
            return refresh_leaves(sources)
        return view.refresh(options.workspace / 'src', common, destination, **sources)
    if not os.path.lexists(destination):
        require(getattr(options, 'phase', '') == 'configure',
                'common source view is missing; configure a new output')
        return view.create(options.workspace / 'src', common, destination, **sources)
    if getattr(options, 'resume_configure', False):
        return view.complete_initial(options.workspace / 'src', common, destination, **sources)
    if getattr(options, 'retry_configure', False):
        return refresh_leaves(sources)
    return view.verify(options.workspace / 'src', common, destination, **sources, **({'_retired': True} if retired else {}))



def require_common_v8(options):
    require(getattr(options, 'v8_source', None) and getattr(options, 'v8_ports_source', None) and
            getattr(options, 'v8_pkgsrc', None),
            'Electron 45 requires the verified common V8 source, owner and pkgsrc export')


def require_common_node(options):
    require(getattr(options, 'node_source', None) and getattr(options, 'node_pkgsrc', None),
            'Electron 45 requires the verified common Node source and pkgsrc export')


def require_common_dependencies(options):
    """Require the shared library and source providers for an Electron build."""
    require(all(getattr(options, name, False) for name in
                ('shared_abseil', 'shared_icu', 'shared_re2', 'shared_undici')),
            'Electron requires common Abseil, ICU, RE2 and Undici')
    require(all(getattr(options, name, None) for name in
                ('protobuf_source', 'protobuf_ports_source', 'protobuf_archive', 'protobuf_patch')),
            'Electron requires the verified common Protobuf source and owner inputs')
    require(getattr(options, 'boringssl_source', None) and getattr(options, 'boringssl_archive', None),
            'Electron requires the verified common BoringSSL source and archive')


def require_common_perfetto(options):
    require(all(getattr(options, name, None) for name in
                ('perfetto_source', 'perfetto_ports_source', 'perfetto_archive', 'perfetto_patch')),
            'Electron 45 requires the verified common Perfetto source, owner, archive and patch')


def prepare_source_inputs(options, native, environment, sdk):
    ensure_lastchange(options.workspace, native, environment, sdk)
    if not getattr(options, 'shared_ffmpeg', False):
        ensure_ffmpeg_netbsd_config(options.workspace)
    options.source_view_created_links = ensure_host_dsymutil(options.workspace, native) or {}


def prepare_build_inputs(options, native, environment, sdk):
    prepare_source_inputs(options, native, environment, sdk)
    require_rust_std(options.host_prefix, options.target)


def keep_going_limit(options):
    value = getattr(options, 'keep_going', 1)
    require(type(value) is int and value >= 0,
            'Ninja keep-going limit must be a nonnegative integer')
    return value


def run_ninja(options, sdk, native, source_root, environment):
    output = options.work / 'out'
    sdk['process'].run_logged([native.tool('ninja'), '-C', str(output), '-j', str(options.jobs),
                              '-k', str(keep_going_limit(options)),
                              'electron_dist_zip'], str(options.work / 'build.log'),
                             cwd=str(source_root), env=environment,
                             append=(options.work / 'build.log').exists())
    archive = output / 'dist.zip'
    require(archive.is_file(), 'Electron producer did not create dist.zip')



@contextmanager
def configure_stage(name):
    start = time.monotonic()
    print(f'configure: {name} begin', flush=True)
    try:
        yield
    finally:
        print(f'configure: {name} end ({time.monotonic() - start:.1f}s)', flush=True)


def require_electron_static_assets(options):
    """Check the default app's selected package files from Electron's GN list."""
    filenames = (options.workspace / 'src/electron/filenames.gni').read_text()
    match = re.search(r'(?ms)^\s*default_app_octicon_sources\s*=\s*\[(.*?)^\s*\]', filenames)
    require(match is not None, 'Electron octicon source list is missing')
    entries = re.findall(r'"([^"\n]+)"', match.group(1))
    require(entries and not re.sub(r'"[^"\n]+"|[\s,]', '', match.group(1)),
            'invalid Electron octicon source list')
    modules = (options.host_prefix / 'lib/node_modules').resolve(strict=True)
    for entry in entries:
        path = Path(entry)
        require(not path.is_absolute() and '..' not in path.parts and
                path.parts[:3] == ('node_modules', '@primer', 'octicons'),
                'invalid Electron octicon source path')
        selected = modules.joinpath(*path.parts[1:])
        require(selected.is_file() and selected.resolve().is_relative_to(modules),
                'missing common Electron octicon asset: ' + entry)


def configure(options):
    require_common_v8(options)
    require_common_node(options)
    require_common_perfetto(options)
    require_common_dependencies(options)
    sdk = load_sdk(options.sdk_source)
    with configure_stage('source verify'):
        verify_source(options.workspace, options.ports_source, options.git)
        require_electron_static_assets(options)
    work = options.work
    resume = getattr(options, 'resume_configure', False)
    retry = getattr(options, 'retry_configure', False)
    if resume or retry:
        require(work.is_dir() and not work.is_symlink() and not (work / 'configuration.json').exists(),
                'initial resume requires existing unconfigured work')
        output = work / 'out'
        require(output.is_dir() and not output.is_symlink(), 'initial configure output is missing')
        names = {item.name for item in output.iterdir()}
        require(('args.gn' in names and not names.intersection({'build.ninja', '.ninja_log', '.ninja_deps'})) if retry
                else names == {'args.gn'},
                'initial configure retry cannot reuse Ninja output')
    else:
        require(not work.exists(), 'configure output must be new; retain an unsuccessful output for diagnosis')
        work.mkdir()
        output = work / 'out'
    with configure_stage('producer inputs'):
        native, environment, values = producer_inputs(options, sdk)
    if resume or retry:
        args_file = output / 'args.gn'
        require(args_file.is_file() and not args_file.is_symlink(), 'initial GN args are missing')
        old_args = args_file.read_text()
        current_args = gn_arguments(values)
        if not retry:
            require(old_args == current_args, 'initial resume GN arguments changed')
    else:
        output.mkdir()
        (output / 'args.gn').write_text(gn_arguments(values))
    with configure_stage('prepare inputs'):
        prepare_build_inputs(options, native, environment, sdk)
    with configure_stage('source view refresh'):
        source_root = gn_source(options)
    write_devtools_identity(work, sdk, environment)
    write_protoc_selection(work, sdk, options.protoc_selection)
    write_v8_metagen_selection(work, sdk, getattr(options, 'v8_metagen_selection', None))
    if retry and old_args != current_args:
        with tempfile.NamedTemporaryFile(mode='w', dir=output, prefix='.args-', delete=False) as handle:
            temporary = Path(handle.name)
            try:
                handle.write(current_args)
                handle.flush()
                os.fsync(handle.fileno())
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        try:
            os.replace(temporary, args_file)
        finally:
            temporary.unlink(missing_ok=True)
    with configure_stage('GN'):
        sdk['process'].run_logged([native.tool('gn'), 'gen', str(output),
            '--script-executable=' + native.tool('python'), '--ninja-executable=' + native.tool('ninja'),
            '--root-target=//electron', '--root-pattern=//electron:electron_dist_zip', '--fail-on-unused-args'],
            str(work / 'configure.log'), cwd=str(source_root), env=environment,
            append=retry and os.path.lexists(work / 'configure.log'))
    # This is the actual producer invocation, not a qualification record.
    local_module('electron_build_source', 'prepare-build-sources.py').atomic_json(work / 'configuration.json',
        dict(arguments=values, environment=environment, source=str(options.workspace),
             sdk=str(options.sdk_source), host_prefix=str(options.host_prefix), target=options.target))



def minizip_activation_args(options, old_environment, environment, old_arguments, values):
    """Allow only the first verified addition; later selection changes stay guarded."""
    if not getattr(options, 'shared_minizip', False):
        return set()
    key = 'EMBERBSD_MINIZIP_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')),
            'verified minizip identity is missing')
    names = {'emberbsd_' + provider + '_' + role + '_' + kind
             for provider in ('zlib', 'minizip') for role in ('host', 'target')
             for kind in ('libraries', 'inputs')}
    if old_environment.get(key):
        return set()
    require(all(old_arguments.get(name) in (None, []) for name in names),
            'minizip activation cannot replace existing GN inputs')
    require(all(isinstance(values.get(name), list) and values[name] for name in names),
            'verified minizip GN inputs are incomplete')
    return names


def image_activation_args(options, old_environment, environment, old_arguments, values):
    """Allow the first verified image selection, retaining later identity checks."""
    if not getattr(options, 'shared_image', False):
        return set()
    key = 'EMBERBSD_IMAGE_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')), 'verified image identity is missing')
    names = {'emberbsd_' + provider + '_' + role + '_' + kind
             for provider in ('jpeg', 'webp') for role in ('host', 'target')
             for kind in ('libraries', 'inputs')}
    names.update(('emberbsd_common_image', 'use_system_libjpeg'))
    if old_environment.get(key):
        return set()
    require(all(old_arguments.get(name) in (None, False, []) for name in names),
            'image activation cannot replace existing GN inputs')
    require(all(values.get(name) for name in names), 'verified image GN inputs are incomplete')
    return names


def ots_activation_args(options, old_environment, environment, old_arguments, values, receipt_name):
    selection = getattr(options, 'ots_selection', None)
    if not selection:
        return set()
    require(values.get('emberbsd_common_ots') is True and values.get('emberbsd_ots_identity') ==
            str(Path(selection['path']) / receipt_name), 'verified OTS GN inputs are incomplete')
    require(old_arguments.get('emberbsd_common_ots') in (None, False, True), 'invalid previous OTS selection')
    require(environment.get('EMBERBSD_OTS_SELECTION') == json.dumps(selection, sort_keys=True, separators=(',', ':')),
            'verified OTS selection identity is missing')
    previous = old_environment.get('EMBERBSD_OTS_SELECTION')
    if not previous:
        require(old_arguments.get('emberbsd_ots_identity') in (None, ''),
                'OTS activation cannot replace an unrelated identity')
        return {'emberbsd_common_ots', 'emberbsd_ots_identity'}
    if previous != environment.get('EMBERBSD_OTS_SELECTION'):
        return {'emberbsd_ots_identity'}
    return set()



def leveldb_activation_args(options, old_environment, environment, old_arguments, values, receipt_name):
    selection = getattr(options, 'leveldb_selection', None)
    if not selection:
        return set()
    require(values.get('emberbsd_common_leveldb') is True and values.get('emberbsd_leveldb_identity') ==
            str(Path(selection['path']) / receipt_name), 'verified LEVELDB GN inputs are incomplete')
    require(old_arguments.get('emberbsd_common_leveldb') in (None, False, True), 'invalid previous LEVELDB selection')
    require(environment.get('EMBERBSD_LEVELDB_SELECTION') == json.dumps(selection, sort_keys=True, separators=(',', ':')),
            'verified LEVELDB selection identity is missing')
    previous = old_environment.get('EMBERBSD_LEVELDB_SELECTION')
    if not previous:
        require(old_arguments.get('emberbsd_leveldb_identity') in (None, ''),
                'LEVELDB activation cannot replace an unrelated identity')
        return {'emberbsd_common_leveldb', 'emberbsd_leveldb_identity'}
    if previous != environment.get('EMBERBSD_LEVELDB_SELECTION'):
        return {'emberbsd_leveldb_identity'}
    return set()


def spirv_activation_args(options, old_environment, environment, old_arguments, values, receipt_name, *, origin=False):
    if not getattr(options, 'shared_spirv_tools', False):
        return set()
    selection = getattr(options, 'spirv_selection', None)
    require(selection and values.get('emberbsd_spirv_source_identity') ==
            str(Path(selection['path']) / receipt_name), 'verified SPIRV source is incomplete')
    keys = ('EMBERBSD_SPIRV_TOOLS_SOURCE_SHA256', 'EMBERBSD_SPIRV_HEADERS_SOURCE_SHA256',
            'EMBERBSD_SPIRV_LINK_SOURCE_SHA256', 'EMBERBSD_SPIRV_CORE_SOURCE_SHA256')
    require(all(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')) for key in keys),
            'verified SPIRV package identities are incomplete')
    require(environment.get('EMBERBSD_SPIRV_SELECTION') == json.dumps(selection, sort_keys=True, separators=(',', ':')),
            'verified SPIRV source identity is missing')
    names = {'emberbsd_common_spirv_tools', 'emberbsd_spirv_source_identity'}
    names.update('emberbsd_' + name + '_' + role + '_' + kind
                 for name in ('spirv_tools', 'spirv_link', 'spirv_core')
                 for role in ('host', 'target') for kind in ('libraries', 'inputs'))
    names.update('emberbsd_spirv_tools_' + role + '_table' for role in ('host', 'target'))
    names.update('emberbsd_spirv_headers_' + role + '_inputs' for role in ('host', 'target'))
    require(all(values.get(name) for name in names), 'verified SPIRV GN inputs are incomplete')
    if origin:
        require(old_environment.get('EMBERBSD_SPIRV_SELECTION'),
                'source-origin transition requires the saved SPIRV selection')
    if not old_environment.get('EMBERBSD_SPIRV_SELECTION'):
        require(not any(old_environment.get(key) for key in keys), 'partial previous SPIRV selection')
        require(all(old_arguments.get(name) in (None, False, '', []) for name in names),
                'SPIRV activation cannot replace unrelated GN inputs')
        return names
    if origin:
        old_selection = json.loads(old_environment['EMBERBSD_SPIRV_SELECTION'])
        sourceprep = options.ml_sdk['sourceprep']
        view = local_module('electron_protobuf_source_view', 'protobuf-source-view.py')
        spirv = local_module('electron_spirv_source_view', 'spirv-source-view.py')
        require(spirv.selection(view, sourceprep, old_selection['path']) == old_selection and
                spirv.selection(view, sourceprep, selection['path']) == selection and
                old_selection['tree_sha256'] == selection['tree_sha256'],
                'SPIRV source-origin payload changed')
        require(all(re.fullmatch(r'[0-9a-f]{64}', old_environment.get(key, '')) for key in keys),
                'saved SPIRV package identities are incomplete')
        changed = set()
        if any(old_environment.get(key) != environment.get(key) for key in keys):
            changed = provider_revision_args(options, 'SPIRV', (
                ('spirv_tools', 'spirv-tools', 'libraries'),
                ('spirv_link', 'spirv-tools', 'libraries'),
                ('spirv_core', 'spirv-tools', 'libraries'),
                ('spirv_headers', 'spirv-headers', None),
            ), old_arguments, values)
        if old_selection != selection:
            changed.add('emberbsd_spirv_source_identity')
        return changed
    require(all(old_environment.get(key) == environment.get(key) for key in keys),
            'SPIRV package identities changed during reconfigure')
    if old_environment['EMBERBSD_SPIRV_SELECTION'] != environment['EMBERBSD_SPIRV_SELECTION']:
        return {'emberbsd_spirv_source_identity'}
    return set()


def pffft_activation_args(options, old_environment, environment, old_arguments, values):
    if not getattr(options, 'shared_pffft', False):
        return set()
    key = 'EMBERBSD_PFFFT_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')), 'verified PFFFT identity is missing')
    names = {'emberbsd_pffft_' + role + '_' + kind
             for role in ('host', 'target') for kind in ('libraries', 'inputs')}
    names.add('emberbsd_common_pffft')
    if old_environment.get(key):
        return set()
    require(all(old_arguments.get(name) in (None, False, []) for name in names),
            'PFFFT activation cannot replace existing GN inputs')
    require(all(values.get(name) for name in names), 'verified PFFFT GN inputs are incomplete')
    return names

def expat_activation_args(options, old_environment, environment, old_arguments, values):
    if not getattr(options, 'shared_expat', False):
        return set()
    key = 'EMBERBSD_EXPAT_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')), 'verified EXPAT identity is missing')
    names = {'emberbsd_expat_' + role + '_' + kind
             for role in ('host', 'target') for kind in ('libraries', 'inputs')}
    names.add('emberbsd_common_expat')
    if old_environment.get(key):
        return set()
    require(all(old_arguments.get(name) in (None, False, []) for name in names),
            'EXPAT activation cannot replace existing GN inputs')
    require(all(values.get(name) for name in names), 'verified EXPAT GN inputs are incomplete')
    return names

def cpuinfo_activation_args(options, old_environment, environment, old_arguments, values):
    if not getattr(options, 'shared_cpuinfo', False):
        return set()
    key = 'EMBERBSD_CPUINFO_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')), 'verified CPUINFO identity is missing')
    names = {'emberbsd_cpuinfo_' + role + '_' + kind
             for role in ('host', 'target') for kind in ('libraries', 'inputs')}
    names.add('emberbsd_common_cpuinfo')
    if old_environment.get(key):
        return set()
    require(all(old_arguments.get(name) in (None, False, []) for name in names),
            'CPUINFO activation cannot replace existing GN inputs')
    require(all(values.get(name) for name in names), 'verified CPUINFO GN inputs are incomplete')
    return names

def vulkan_activation_args(options, old_environment, environment, old_arguments, values):
    if not getattr(options, 'shared_vulkan', False):
        return set()
    key = 'EMBERBSD_VULKAN_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')), 'verified Vulkan identity is missing')
    names = {'emberbsd_vulkan_' + role + '_' + kind
             for role in ('host', 'target') for kind in ('library', 'inputs', 'runtime_dir')}
    names.update('emberbsd_vulkan_headers_' + role + '_' + kind
                 for role in ('host', 'target') for kind in ('include', 'inputs'))
    names.add('emberbsd_common_vulkan')
    if old_environment.get(key):
        return set()
    require(all(old_arguments.get(name) in (None, False, '', []) for name in names),
            'Vulkan activation cannot replace existing GN inputs')
    require(all(values.get(name) for name in names), 'verified Vulkan GN inputs are incomplete')
    require(old_arguments.get('angle_use_custom_libvulkan') in (None, True, False) and
            values.get('angle_use_custom_libvulkan') is False,
            'Vulkan activation requires system loader search')
    names.add('angle_use_custom_libvulkan')
    return names


def woff2_activation_args(options, old_environment, environment, old_arguments, values):
    if not getattr(options, 'shared_woff2', False):
        return set()
    key = 'EMBERBSD_WOFF2_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')), 'verified WOFF2 identity is missing')
    names = {'emberbsd_woff2_' + role + '_' + kind
             for role in ('host', 'target') for kind in ('libraries', 'inputs')}
    names.add('emberbsd_common_woff2')
    if old_environment.get(key):
        return set()
    require(all(old_arguments.get(name) in (None, False, []) for name in names),
            'WOFF2 activation cannot replace existing GN inputs')
    require(all(values.get(name) for name in names), 'verified WOFF2 GN inputs are incomplete')
    return names

def snappy_activation_args(options, old_environment, environment, old_arguments, values):
    if not getattr(options, 'shared_snappy', False):
        return set()
    key = 'EMBERBSD_SNAPPY_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')), 'verified SNAPPY identity is missing')
    names = {'emberbsd_snappy_' + role + '_' + kind
             for role in ('host', 'target') for kind in ('libraries', 'inputs')}
    names.add('emberbsd_common_snappy')
    if old_environment.get(key):
        return set()
    require(all(old_arguments.get(name) in (None, False, []) for name in names),
            'SNAPPY activation cannot replace existing GN inputs')
    require(all(values.get(name) for name in names), 'verified SNAPPY GN inputs are incomplete')
    return names

def openh264_activation_args(options, old_environment, environment, old_arguments, values):
    if not getattr(options, 'shared_openh264', False):
        return set()
    key = 'EMBERBSD_OPENH264_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')), 'verified OpenH264 identity is missing')
    names = {'emberbsd_openh264_' + role + '_' + kind
             for role in ('host', 'target') for kind in ('libraries', 'inputs')}
    names.add('emberbsd_common_openh264')
    if old_environment.get(key):
        return set()
    require(all(old_arguments.get(name) in (None, False, []) for name in names),
            'OpenH264 activation cannot replace existing GN inputs')
    require(all(values.get(name) for name in names), 'verified OpenH264 GN inputs are incomplete')
    require(old_arguments.get('rtc_system_openh264') in (None, False) and
            values.get('rtc_system_openh264') is False,
            'OpenH264 activation requires the shared encoder wrapper')
    names.add('rtc_system_openh264')
    return names


def pdfium_activation_args(options, old_environment, environment, old_arguments, values):
    """Allow only the first verified common PDF library selection."""
    if not getattr(options, 'shared_pdf_libraries', False):
        return set()
    key = 'EMBERBSD_PDF_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')), 'verified PDF identity is missing')
    names = {'emberbsd_' + provider + '_' + role + '_' + kind
             for provider in ('lcms2', 'openjpeg', 'tiff') for role in ('host', 'target')
             for kind in ('libraries', 'inputs')}
    names.update(('emberbsd_common_pdf', 'use_system_lcms2', 'use_system_libopenjpeg2', 'use_system_libtiff'))
    if old_environment.get(key):
        return set()
    require(all(old_arguments.get(name) in (None, False, []) for name in names),
            'PDF activation cannot replace existing GN inputs')
    require(all(values.get(name) for name in names), 'verified PDF GN inputs are incomplete')
    return names


def provider_revision_args(options, label, providers, old_arguments, values):
    """Validate a package-revision-only update of selected provider bindings."""
    revisions = {}
    changed = set()
    for provider, base, library_kind in providers:
        for role in ('host', 'target'):
            prefix = (Path(options.host_prefix) if role == 'host' else Path(options.sysroot) / 'usr/pkg').resolve(strict=True)
            db = prefix / 'pkgdb'
            stem = 'emberbsd_' + provider + '_' + role
            inputkey = stem + '_inputs'
            if library_kind is None:
                require(provider == 'spirv_headers' and base == 'spirv-headers' and
                        stem + '_libraries' not in old_arguments and stem + '_libraries' not in values,
                        label + ' header-only provider is invalid')
            else:
                libkey = stem + '_' + library_kind
                require(old_arguments.get(libkey) == values.get(libkey) and values.get(libkey),
                        label + ' library changed during revision update')
            def split_inputs(items):
                require(isinstance(items, list) and all(isinstance(item, str) for item in items) and
                        len(items) == len(set(items)), 'invalid ' + label + ' revision inputs')
                records, ordinary = [], []
                for item in items:
                    require(Path(item).is_absolute(), 'invalid ' + label + ' input path')
                    path = Path(item)
                    if path.is_relative_to(db):
                        records.append(path)
                    else:
                        require('/pkgdb/' not in item, 'foreign ' + label + ' package database')
                        ordinary.append(item)
                require(len(records) == 3 and len({p.parent for p in records}) == 1 and
                        {p.name for p in records} == {'+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION'} and
                        records[0].parent.parent == db, 'invalid ' + label + ' package records')
                version_pattern = {'spirv-tools': r'\d+\.\d+',
                                   'spirv-headers': r'\d+\.\d+\.\d+\.\d+'}.get(
                                       base, r'\d+\.\d+\.\d+')
                match = re.fullmatch(re.escape(base) + '-(' + version_pattern + r')(?:nb(\d+))?',
                                     records[0].parent.name)
                require(match is not None, 'invalid ' + label + ' package identity')
                return sorted(ordinary), (match.group(1), int(match.group(2) or 0))
            before, old_version = split_inputs(old_arguments.get(inputkey))
            after, new_version = split_inputs(values.get(inputkey))
            require(before == after and old_version[0] == new_version[0] and
                    new_version[1] >= old_version[1], label + ' revision inputs changed incompatibly')
            revisions[(provider, role)] = (old_version, new_version)
            if old_arguments[inputkey] != values[inputkey]:
                changed.add(inputkey)
    require(all(revisions[(provider, 'host')] == revisions[(provider, 'target')]
                for provider, _, _ in providers) and
            any(before != after for before, after in revisions.values()),
            label + ' role revisions differ or did not advance')
    return changed


def codec_activation_args(options, old_environment, environment, old_arguments, values):
    """Allow a verified codec activation or compatible package revision update."""
    if not getattr(options, 'shared_codecs', False):
        return set()
    key = 'EMBERBSD_CODEC_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')), 'verified codec identity is missing')
    providers = (('dav1d', 'dav1d', 'libraries'), ('aom', 'libaom', 'libraries'),
                 ('vpx', 'libvpx', 'libraries'), ('opus', 'libopus', 'libraries'),
                 ('flac', 'flac', 'libraries'))
    names = {'emberbsd_' + provider + '_' + role + '_' + kind
             for provider, _, _ in providers for role in ('host', 'target')
             for kind in ('libraries', 'inputs')}
    names.add('emberbsd_common_codecs')
    old_identity = old_environment.get(key)
    if old_identity:
        require(re.fullmatch(r'[0-9a-f]{64}', old_identity), 'previous codec identity is invalid')
        if old_identity == environment[key]:
            return set()
        return provider_revision_args(options, 'codec', providers, old_arguments, values)
    require(all(old_arguments.get(name) in (None, False, []) for name in names),
            'codec activation cannot replace existing GN inputs')
    require(all(values.get(name) for name in names), 'verified codec GN inputs are incomplete')
    return names


def font_activation_args(options, old_environment, environment, old_arguments, values):
    """Allow the initial verified font selection without weakening later checks."""
    if not getattr(options, 'shared_font', False):
        return set()
    key = 'EMBERBSD_FONT_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')), 'verified font identity is missing')
    names = {'emberbsd_' + provider + '_' + role + '_' + kind
             for provider in ('freetype', 'harfbuzz') for role in ('host', 'target')
             for kind in ('libraries', 'inputs')}
    names.update(('emberbsd_common_font', 'use_system_freetype', 'use_system_harfbuzz'))
    if old_environment.get(key):
        return set()
    require(all(old_arguments.get(name) in (None, False, []) for name in names),
            'font activation cannot replace existing GN inputs')
    require(all(values.get(name) for name in names), 'verified font GN inputs are incomplete')
    return names


def xml_activation_args(options, old_environment, environment, old_arguments, values):
    """Allow a verified XML activation or compatible package revision update."""
    if not getattr(options, 'shared_xml', False):
        return set()
    key = 'EMBERBSD_XML_SOURCE_SHA256'
    require(re.fullmatch(r'[0-9a-f]{64}', environment.get(key, '')), 'verified XML identity is missing')
    names = {'emberbsd_' + provider + '_' + role + '_' + kind
             for provider in ('xml', 'xslt') for role in ('host', 'target')
             for kind in ('library', 'inputs')}
    old_identity = old_environment.get(key)
    if old_identity:
        require(re.fullmatch(r'[0-9a-f]{64}', old_identity), 'previous XML identity is invalid')
        if old_identity == environment[key]:
            return set()
        # producer_inputs has already verified the current packages and payloads.
        return provider_revision_args(options, 'XML',
            (('xml', 'libxml2', 'library'), ('xslt', 'libxslt', 'library')),
            old_arguments, values)
    require(all(old_arguments.get(name) in (None, '', []) for name in names),
            'XML activation cannot replace existing GN inputs')
    require(all(values.get(name) for name in names), 'verified XML GN inputs are incomplete')
    return names


def common_activation_allowlist(options, old_environment, environment, old_arguments, values):
    """Allow initial activation or an identical verified common-provider retry."""
    if not getattr(options, 'activate_common_providers', False):
        return set(), set()
    require(all(getattr(options, name, False) for name in
                ('shared_abseil', 'shared_icu', 'shared_re2', 'shared_undici')) and
            getattr(options, 'protobuf_source', None),
            'common provider activation requires all selected providers')
    env_names = {'EMBERBSD_PROTOBUF_SOURCE_SHA256'} | {
        'EMBERBSD_SHARED_' + provider + '_' + suffix
        for provider in ('ABSEIL', 'ICU', 'RE2') for suffix in ('VERSION', 'SOURCE_SHA256')}
    require(all(isinstance(environment.get(name), str) and environment[name] for name in env_names),
            'common provider activation requires verified identities')
    first = all(name not in old_environment for name in env_names)
    identical = all(old_environment.get(name) == environment[name] for name in env_names)
    require(first or identical, 'common provider identity changed or is partially selected')
    args = {'emberbsd_abseil_host_headers', 'emberbsd_abseil_host_inputs',
            'emberbsd_abseil_target_headers', 'emberbsd_abseil_target_inputs',
            'icu_use_data_file', 'v8_enable_temporal_systemicu',
            'emberbsd_icuuc_host_library', 'emberbsd_icuuc_target_library',
            'emberbsd_icui18n_host_library', 'emberbsd_icui18n_target_library',
            'emberbsd_re2_host_library', 'emberbsd_re2_target_library',
            'emberbsd_common_protobuf', 'emberbsd_protobuf_native_prefix',
            'emberbsd_protobuf_target_prefix', 'emberbsd_protoc', 'emberbsd_protoc_runtime_inputs',
            'node_shared_undici_path', 'node_shared_undici_input'}
    if first:
        require(all(name not in old_arguments for name in args - {'icu_use_data_file', 'v8_enable_temporal_systemicu'}),
                'common provider activation cannot replace an existing selection')
    else:
        for name in args:
            if name == 'emberbsd_protoc_runtime_inputs' and old_arguments.get(name) != values.get(name):
                require(additive_protoc_selection(old_arguments, values, options.work) == {name},
                        'common provider retry cannot change protoc inputs')
            else:
                require(old_arguments.get(name) == values.get(name),
                        'common provider retry cannot change selected GN inputs')
    require(values.get('emberbsd_common_protobuf') is True and
            values.get('icu_use_data_file') is False and values.get('v8_enable_temporal_systemicu') is True and
            all(values.get(name) for name in args - {'icu_use_data_file'}),
            'common provider activation produced incomplete GN inputs')
    for name in (set(old_environment) | set(environment)) - env_names - {
            'CC', 'CXX', 'HOME', 'TMPDIR', 'TMP', 'TEMP', 'USER', 'LOGNAME',
            'EMBERBSD_PROTOC_SELECTION_SHA256'}:
        require(old_environment.get(name) == environment.get(name),
                'unrelated producer input changed during common provider activation: ' + name)
    swiftshader_keys = ('enable_swiftshader', 'enable_swiftshader_vulkan', 'angle_enable_swiftshader', 'dawn_use_swiftshader')
    swiftshader_changed = (verified_swiftshader_disable(old_arguments, values)
                           if any(name in values for name in swiftshader_keys) else set())
    for name in (set(old_arguments) | set(values)) - args - swiftshader_changed:
        require(old_arguments.get(name) == values.get(name),
                'unrelated GN input changed during common provider activation: ' + name)
    return (env_names, args) if first else (set(), set())


def migrate_devtools_only(options, work):
    """Guard an explicit migration until a later GN reconfiguration succeeds."""
    (work / 'reconfigure-incomplete').write_text('GN reconfiguration incomplete\n')
    return gn_source(options)



def verified_swiftshader_disable(old_arguments, new_arguments):
    """Allow only disabling the optional bundled software renderer."""
    keys = ('enable_swiftshader', 'enable_swiftshader_vulkan', 'angle_enable_swiftshader', 'dawn_use_swiftshader')
    require(all(new_arguments.get(key) is False for key in keys),
            'bundled SwiftShader is disabled in this producer')
    require(all(old_arguments.get(key) is None or type(old_arguments[key]) is bool for key in keys),
            'invalid prior SwiftShader selection')
    return {key for key in keys if old_arguments.get(key) is not False}

def verified_host_deployment_change(old_args, new_args, old_env, new_env, options, native):
    """Accept only a coherent Darwin minimum and its derived V8 host flag."""
    old = old_args.get('mac_deployment_target')
    new = new_args.get('mac_deployment_target')
    if old == new:
        return False
    require(native.host.get('os') == 'Darwin', 'host deployment change requires Darwin')
    valid = lambda value: (isinstance(value, str) and
        re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,2}', value) and
        tuple(int(part) for part in value.split('.')) >= (14, 0))
    require(valid(old) and valid(new) and new == options.macos_minimum,
            'invalid host deployment minimum')
    require(old_env.get('MACOSX_DEPLOYMENT_TARGET') == old and
            new_env.get('MACOSX_DEPLOYMENT_TARGET') == new,
            'host deployment environment disagrees with GN')
    old_flags = old_args.get('v8_metagen_host_extra_flags')
    new_flags = new_args.get('v8_metagen_host_extra_flags')
    require(type(old_flags) == type(new_flags) and
            (old_flags is None or isinstance(old_flags, list)),
            'invalid V8 host deployment flags')
    if old_flags is not None:
        prefixes = ('-mmacos-version-min=', '-mmacosx-version-min=')
        expected = []
        count = 0
        for flag in old_flags:
            require(isinstance(flag, str), 'invalid V8 host deployment flag')
            match = next((prefix for prefix in prefixes if flag.startswith(prefix)), None)
            if match:
                require(flag == match + old, 'old V8 host deployment flag disagrees')
                flag = match + new
                count += 1
            expected.append(flag)
        require(count <= 1 and new_flags == expected, 'V8 host deployment flags changed')
    return True


def equivalent_spirv_catalog(old_raw, new_raw):
    """Allow only proven SPIRV recipe-identity revisions in the catalog."""
    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'))

    def parse(raw):
        require(isinstance(raw, str), 'invalid compression catalog')
        try:
            value = json.loads(raw)
        except (TypeError, ValueError) as error:
            raise ValueError('invalid compression catalog') from error
        require(canonical(value) == raw,
                'noncanonical compression catalog')
        require(isinstance(value, dict) and set(value) == {'version', 'identities', 'recipes'} and
                type(value['version']) is int and value['version'] == 1 and
                isinstance(value['identities'], dict) and isinstance(value['recipes'], dict),
                'invalid compression catalog schema')
        return value

    old, new = parse(old_raw), parse(new_raw)
    spirv = {'parallel/spirv-tools', 'parallel/spirv-headers'}
    keys = set(old['identities'])
    require(spirv <= keys and keys == set(new['identities']) == set(old['recipes']) == set(new['recipes']) and
            canonical(old['recipes']) == canonical(new['recipes']), 'compression catalog providers changed')
    for name in keys:
        before, after = old['identities'][name], new['identities'][name]
        if name not in spirv:
            require(canonical(before) == canonical(after), 'unrelated compression catalog identity changed')
            continue
        fields = {'api', 'package', 'upstream', 'effective_package_sha256'}
        require(isinstance(before, dict) and isinstance(after, dict) and
                set(before) == set(after) == fields and before['package'] == after['package'] == name and
                type(before['api']) is int and type(after['api']) is int and before['api'] == after['api'] == 3 and
                before['upstream'] == after['upstream'] and
                isinstance(before['upstream'], str) and re.fullmatch(r'[0-9a-f]{40}', before['upstream']) and
                all(isinstance(identity['effective_package_sha256'], str) and
                    re.fullmatch(r'[0-9a-f]{64}', identity['effective_package_sha256'])
                    for identity in (before, after)), 'invalid SPIRV catalog identity')
    return True


def ml_alias_migration_mode(work, config_path, saved_bytes, legacy_root, *, origin, cleanup_only, build_after, marker_text):
    stable, backup = work / 'source-view', work / '.source-view-origin-backup'
    marker, previous = work / 'reconfigure-incomplete', work / '.source-view-origin-old-configuration.json'
    candidate = work / '.source-view-origin-candidate'
    require(origin and not cleanup_only and not build_after and legacy_root.is_absolute() and
            config_path.is_file() and not config_path.is_symlink() and config_path.read_bytes() == saved_bytes and
            stable.is_dir() and not stable.is_symlink() and not os.path.lexists(candidate),
            'invalid ML alias migration transaction')
    if not any(os.path.lexists(p) for p in (marker, previous, backup)):
        require(legacy_root == stable, 'initial ML alias root must be the stable view')
        return 'initial'
    require(legacy_root.name == 'source-view' and legacy_root.parent.parent == work and
            legacy_root.parent.name.startswith('.source-view-origin-factory-') and
            legacy_root.parent.name != '.source-view-origin-factory-' and
            not os.path.lexists(legacy_root.parent) and
            marker.is_file() and not marker.is_symlink() and marker.read_text() == marker_text and
            previous.is_file() and not previous.is_symlink() and previous.read_bytes() == saved_bytes and
            backup.is_dir() and not backup.is_symlink(), 'invalid ML alias recovery transaction')
    return 'recovery'


def complete_ml_alias_migration(mode, stable, backup, legacy_root, verify_old, verify_new, migrate, prepare_metadata):
    """Verify and normalize both views before generating new source metadata."""
    if mode == 'initial':
        verify_old(stable, legacy_root=stable)
        migrate(stable, stable)
        verify_old(stable)
    else:
        require(mode == 'recovery', 'invalid ML alias migration mode')
        verify_old(backup, legacy_root=stable)
        verify_new(stable, legacy_root=legacy_root)
        migrate(backup, stable)
        migrate(stable, legacy_root)
        verify_old(backup)
        verify_new(stable)
    prepare_metadata()


def verify_source_origin_provider_invariants(old_environment, new_environment, *, verified_spirv=False):
    """Keep every other selected provider unchanged during an origin switch."""
    selections = {
        'EMBERBSD_OTS_SELECTION', 'EMBERBSD_LEVELDB_SELECTION',
        'EMBERBSD_SPIRV_SELECTION', 'EMBERBSD_SQLITE_SELECTION',
        'EMBERBSD_COMPRESSION_RECIPE_CATALOG', 'EMBERBSD_FFMPEG_TARGET_PKGCONFIG',
        'EMBERBSD_DEVTOOLS_PROVIDER_SHA256',
    }
    for key in set(old_environment) | set(new_environment):
        selected_hash = (key.startswith('EMBERBSD_') and
                         key.endswith(('_SOURCE_SHA256', '_SELECTION_SHA256')))
        projected_hash = (key.startswith(('EMBERBSD_ML_', 'EMBERBSD_MEDIA_HEADER_')) and
                          key.endswith('_SHA256'))
        spirv_keys = ('EMBERBSD_SPIRV_SELECTION', 'EMBERBSD_SPIRV_TOOLS_SOURCE_SHA256',
                      'EMBERBSD_SPIRV_HEADERS_SOURCE_SHA256', 'EMBERBSD_SPIRV_LINK_SOURCE_SHA256',
                      'EMBERBSD_SPIRV_CORE_SOURCE_SHA256')
        if ((selected_hash or projected_hash or key in selections) and
                key not in ('EMBERBSD_NODE_SOURCE_SHA256', 'EMBERBSD_V8_SOURCE_SHA256') and
                not (verified_spirv and key in spirv_keys)):

            if (key == 'EMBERBSD_COMPRESSION_RECIPE_CATALOG' and verified_spirv and
                    old_environment.get(key) != new_environment.get(key)):
                equivalent_spirv_catalog(old_environment.get(key), new_environment.get(key))
                continue
            require(old_environment.get(key) == new_environment.get(key),
                    'source-origin transition changed another provider: ' + key)


def saved_source_origin_inputs(saved):
    """Recover only the old source roots explicitly recorded by the producer."""
    workspace = Path(saved['source'])
    receipt = Path(saved['arguments']['emberbsd_node_source_identity'])
    rows = saved['arguments']['emberbsd_node_configure_inputs']
    require(workspace.is_absolute() and receipt.is_absolute() and
            receipt.name == 'emberbsd-prepared-source.json' and
            type(rows) is list and all(type(row) is str for row in rows),
            'invalid saved source origin inputs')
    roots = [row.partition('=')[2] for row in rows if row.startswith('v8-source=')]
    require(len(roots) == 1 and Path(roots[0]).is_absolute(),
            'saved Node configure inputs need exactly one V8 source')
    return workspace, receipt.parent, Path(roots[0])


def verify_saved_source_provider(options, sdk, native, environment, saved, role, source):
    """Check the complete payload and saved producer identity of an old source."""
    require(source.is_absolute() and source.resolve(strict=True) == source,
            'saved ' + role + ' source path changed')
    owner = options.ports_source / 'scripts/source-inputs' / role.lower() / 'source.py'
    require(owner.is_file(), 'common ' + role + ' source owner is missing')
    result = sdk['process'].capture(
        [native.tool('python'), '-B', str(owner), '--sdk-source', str(options.sdk_source),
         'verify-payload', '--source', str(source)], env=source_owner_environment(environment))
    record = json.loads(result.stdout.decode('utf-8', 'strict'))
    actual = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    require(actual == saved['environment'].get('EMBERBSD_' + role + '_SOURCE_SHA256'),
            'saved ' + role + ' source identity changed')


def reconfigure(options):
    keep_going_limit(options)
    build_after_reconfigure = getattr(options, 'build_after_reconfigure', False)
    require(not getattr(options, 'migrate_ml_alias_root', None) or
            (getattr(options, 'previous_source', None) and not build_after_reconfigure),
            'ML alias migration requires separate source-origin reconfigure')
    require(not (getattr(options, 'activate_common_providers', False) and
                 getattr(options, 'ml_ruy_source', None)),
            'common provider activation is a separate stage from ML selection')
    if build_after_reconfigure:
        require(options.jobs > 0, 'Ninja job count must be positive')
        require(not getattr(options, 'activate_common_providers', False) or
                getattr(options, 'ml_ruy_source', None),
                'common provider transition without ML sources cannot run Ninja')
    require_common_v8(options)
    require_common_node(options)
    require_common_perfetto(options)
    require_common_dependencies(options)
    """Regenerate an existing GN graph while preserving its toolchain identity."""
    sdk = load_sdk(options.sdk_source)
    source_record = verify_source(options.workspace, options.ports_source, options.git,
                                 allow_ordered_prefix=getattr(options, 'migrate_devtools_modules_only', False))
    # Only patch-created regular files from the verified source receipt may
    # populate a missing derived subtree during an explicit incremental refresh.
    options.source_view_created_files = {
        str(options.workspace / 'src' / name): row['after']
        for name, row in (source_record or {}).get('paths', {}).items()
        if 'before' in row and row['before'] is None and
        isinstance(row.get('after'), str) and re.fullmatch(r'[0-9a-f]{64}', row['after'])}
    options.source_view_publication = sdk.get('publication')
    work = options.work
    output = work / 'out'
    origin = getattr(options, 'previous_source', None)
    saved_bytes = (options.origin_saved_configuration if origin else
                   (work / 'configuration.json').read_bytes())
    saved = json.loads(saved_bytes)
    cleanup_only = bool(origin and saved['source'] == str(options.workspace))
    require(saved['source'] == str(options.workspace if cleanup_only or not origin else origin) and
            saved['sdk'] == str(options.sdk_source) and
            saved['host_prefix'] == str(options.host_prefix) and saved['target'] == options.target,
            'reconfigure inputs differ from configuration')
    if origin:
        require(not build_after_reconfigure and not any(getattr(options, name, False) for name in
                ('activate_common_ml', 'activate_common_providers', 'migrate_devtools_modules_only')),
                'source-origin transition requires a separate reconfigure')
        require(getattr(options, 'refresh_source_view', False),
                'source-origin transition requires source-view refresh')
        if not cleanup_only:
            verify_source(origin, options.ports_source, options.git)
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
        # The Go caches belong to the real work tree, not the scratch binding.
        environment.update(GOCACHE=str(work / 'go-cache'), GOPATH=str(work / 'go-path'))
        new_directory = saved_binding_directory(candidate.work, environment)
        new_commands = json.loads((new_directory / 'commands.json').read_text())
        require(binding_identity(new_commands) == binding_identity(old_commands),
                'target compiler, sysroot or runtime changed')
        # Prepared Node actions encode the selected providers in their argv.
        permitted_env = {'CC', 'CXX', 'EMBERBSD_HOST_NODE', 'EMBERBSD_HOST_PYTHON',
                         'EMBERBSD_HOST_TYPESCRIPT', 'EMBERBSD_HOST_ROLLUP',
                         'HOME', 'TMPDIR', 'TMP', 'TEMP', 'USER', 'LOGNAME'}
        old_env = saved['environment']
        require(re.fullmatch(r'[0-9a-f]{64}', environment.get('EMBERBSD_PROTOC_SELECTION_SHA256', '')),
                'selected protoc fingerprint is missing')
        permitted_env.add('EMBERBSD_PROTOC_SELECTION_SHA256')
        options.protoc_selection = candidate.protoc_selection
        options.v8_metagen_selection = getattr(candidate, 'v8_metagen_selection', None)
        options.vulkan_registry = getattr(candidate, 'vulkan_registry', None)
        require(not (getattr(options, 'activate_common_ml', False) and
                    getattr(options, 'activate_common_providers', False)),
                'select only one common provider migration')
        require(not getattr(options, 'activate_common_ml', False) or getattr(candidate, 'ml_identities', None),
                'common ML activation requires verified inputs')
        if getattr(candidate, 'ml_identities', None):
            options.ml_identities, options.ml_sources, options.ml_sdk = candidate.ml_identities, candidate.ml_sources, sdk
            options.ml_headers = candidate.ml_headers
            options.media_header_selections = candidate.media_header_selections
            if not getattr(options, 'activate_common_providers', False):
                options.boringssl_identity = candidate.boringssl_identity
                options.boringssl_selected = candidate.boringssl_selected
                options.old_boringssl_identity = old_env.get('EMBERBSD_BORINGSSL_SOURCE_SHA256')
                permitted_env.add('EMBERBSD_BORINGSSL_SOURCE_SHA256')
                options.compression_identity = candidate.compression_identity
                options.old_compression_identity = old_env.get('EMBERBSD_COMPRESSION_SOURCE_SHA256')
                options.old_pffft_identity = old_env.get('EMBERBSD_PFFFT_SOURCE_SHA256')
                permitted_env.add('EMBERBSD_PFFFT_SOURCE_SHA256')
                options.old_expat_identity = old_env.get('EMBERBSD_EXPAT_SOURCE_SHA256')
                permitted_env.add('EMBERBSD_EXPAT_SOURCE_SHA256')
                options.old_cpuinfo_identity = old_env.get('EMBERBSD_CPUINFO_SOURCE_SHA256')
                permitted_env.add('EMBERBSD_CPUINFO_SOURCE_SHA256')
                options.old_vulkan_identity = old_env.get('EMBERBSD_VULKAN_SOURCE_SHA256')
                permitted_env.add('EMBERBSD_VULKAN_SOURCE_SHA256')
                options.old_woff2_identity = old_env.get('EMBERBSD_WOFF2_SOURCE_SHA256')
                permitted_env.add('EMBERBSD_WOFF2_SOURCE_SHA256')
                options.old_snappy_identity = old_env.get('EMBERBSD_SNAPPY_SOURCE_SHA256')
                permitted_env.add('EMBERBSD_SNAPPY_SOURCE_SHA256')
                options.old_openh264_identity = old_env.get('EMBERBSD_OPENH264_SOURCE_SHA256')
                permitted_env.add('EMBERBSD_OPENH264_SOURCE_SHA256')
                options.old_codec_identity = old_env.get('EMBERBSD_CODEC_SOURCE_SHA256')
                permitted_env.add('EMBERBSD_CODEC_SOURCE_SHA256')
                options.old_image_identity = old_env.get('EMBERBSD_IMAGE_SOURCE_SHA256')
                permitted_env.add('EMBERBSD_IMAGE_SOURCE_SHA256')
                options.old_font_identity = old_env.get('EMBERBSD_FONT_SOURCE_SHA256')
                options.old_pdf_identity = old_env.get('EMBERBSD_PDF_SOURCE_SHA256')
                options.pdf_identity = getattr(candidate, 'pdf_identity', None)
                permitted_env.add('EMBERBSD_PDF_SOURCE_SHA256')
                options.font_table = getattr(candidate, 'font_table', None)
                permitted_env.add('EMBERBSD_FONT_SOURCE_SHA256')
                options.ots_selection = getattr(candidate, 'ots_selection', None)
                options.old_ots_selection = json.loads(old_env['EMBERBSD_OTS_SELECTION']) if old_env.get('EMBERBSD_OTS_SELECTION') else None
                permitted_env.add('EMBERBSD_OTS_SELECTION')
                options.leveldb_selection = getattr(candidate, 'leveldb_selection', None)
                options.old_leveldb_selection = json.loads(old_env['EMBERBSD_LEVELDB_SELECTION']) if old_env.get('EMBERBSD_LEVELDB_SELECTION') else None
                permitted_env.add('EMBERBSD_LEVELDB_SELECTION')
                options.spirv_selection = getattr(candidate, 'spirv_selection', None)
                options.old_spirv_selection = json.loads(old_env['EMBERBSD_SPIRV_SELECTION']) if old_env.get('EMBERBSD_SPIRV_SELECTION') else None
                permitted_env.add('EMBERBSD_SPIRV_SELECTION')
                permitted_env.update(('EMBERBSD_SPIRV_TOOLS_SOURCE_SHA256', 'EMBERBSD_SPIRV_HEADERS_SOURCE_SHA256',
                                      'EMBERBSD_SPIRV_LINK_SOURCE_SHA256', 'EMBERBSD_SPIRV_CORE_SOURCE_SHA256'))
                options.sqlite_selection = getattr(candidate, 'sqlite_selection', None)
                options.old_sqlite_selection = json.loads(old_env['EMBERBSD_SQLITE_SELECTION']) if old_env.get('EMBERBSD_SQLITE_SELECTION') else None
                permitted_env.add('EMBERBSD_SQLITE_SELECTION')
                options.old_xml_identity = old_env.get('EMBERBSD_XML_SOURCE_SHA256')
                permitted_env.add('EMBERBSD_XML_SOURCE_SHA256')
                options.old_minizip_identity = old_env.get('EMBERBSD_MINIZIP_SOURCE_SHA256')
                permitted_env.add('EMBERBSD_MINIZIP_SOURCE_SHA256')
                options.old_ffmpeg_identity = old_env.get('EMBERBSD_FFMPEG_SOURCE_SHA256')
                permitted_env.update(('EMBERBSD_FFMPEG_SOURCE_SHA256', 'EMBERBSD_FFMPEG_TARGET_PKGCONFIG'))
                permitted_env.update(('EMBERBSD_COMPRESSION_SOURCE_SHA256', 'EMBERBSD_COMPRESSION_RECIPE_CATALOG'))
            ml_keys = {'EMBERBSD_ML_' + name.upper().replace('-', '_') + '_SHA256': name for name in ML_PROVIDERS}
            old_ml = {name: old_env[key] for key, name in ml_keys.items() if key in old_env}
            require(not old_ml or len(old_ml) == len(ML_PROVIDERS), 'partial saved ML selection')
            if not old_ml:
                require(getattr(options, 'activate_common_ml', False), 'initial ML transition needs explicit activation')
            options.old_ml_identities = old_ml or None
            header_keys = {'EMBERBSD_ML_HEADER_' + name.upper() + '_SHA256': name
                           for name in ('eigen3', 'flatbuffers', 'fp16')}
            old_headers = {name: old_env[key] for key, name in header_keys.items() if key in old_env}
            require(not old_headers or len(old_headers) == len(header_keys), 'partial saved header selection')
            require(bool(old_headers) == bool(old_ml), 'saved ML and header selections disagree')
            options.old_header_identities = old_headers or None
            media_keys = {'EMBERBSD_MEDIA_HEADER_' + name.upper() + '_SHA256': name for name in ('libyuv', 'libsrtp')}
            old_media = {name: old_env[key] for key, name in media_keys.items() if key in old_env}
            require(not old_media or len(old_media) == len(media_keys), 'partial saved media header selection')
            options.old_media_header_identities = old_media or None
            permitted_env.update(media_keys)
            permitted_env.update(ml_keys)
            permitted_env.update(header_keys)
        activation_env, activation_args = common_activation_allowlist(
            options, old_env, environment, saved['arguments'], values)
        permitted_env.update(activation_env)
        swiftshader_changed = verified_swiftshader_disable(saved['arguments'], values)
        deployment_changed = verified_host_deployment_change(
            saved['arguments'], values, old_env, environment, options, native)
        if deployment_changed:
            permitted_env.add('MACOSX_DEPLOYMENT_TARGET')
        permitted_env.add('EMBERBSD_DEVTOOLS_PROVIDER_SHA256')
        # producer_inputs has already verified each current owner and payload.
        refreshed_sources = verified_common_source_refresh(
            saved['arguments'], values, old_env, environment, options, work)
        permitted_env.update(refreshed_sources)
        node_source_refresh = 'EMBERBSD_NODE_SOURCE_SHA256' in refreshed_sources
        spirv_args = spirv_activation_args(options, old_env, environment, saved['arguments'], values,
                                           sdk['sourceprep'].PREPARED_TREE_RECEIPT,
                                           origin=bool(origin and not cleanup_only))
        if origin and not cleanup_only:
            verify_source_origin_provider_invariants(old_env, environment, verified_spirv=bool(spirv_args))
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
        without_descriptor = dict(values)
        old_without_descriptor = dict(saved['arguments'])
        descriptor = str(work / 'protoc-selection.json')
        for arguments in (without_descriptor, old_without_descriptor):
            if 'emberbsd_protoc_runtime_inputs' in arguments:
                arguments['emberbsd_protoc_runtime_inputs'] = [path for path in
                    arguments['emberbsd_protoc_runtime_inputs'] if path != descriptor]
        permitted_runtime_args = additive_protoc_runtime_view(old_without_descriptor, without_descriptor, options)
        permitted_runtime_args.update(additive_protoc_selection(saved['arguments'], values, work,
            runtime_change='emberbsd_protoc_runtime_inputs' in permitted_runtime_args))
        v8_descriptor = str(work / 'v8-metagen-selection.json')
        old_v8 = saved['arguments'].get('v8_metagen_runtime_inputs', [])
        new_v8 = values.get('v8_metagen_runtime_inputs', [])
        if v8_descriptor in new_v8 and set(old_v8) - {v8_descriptor} == set(new_v8) - {v8_descriptor}:
            permitted_runtime_args.add('v8_metagen_runtime_inputs')
        minizip_args = minizip_activation_args(options, old_env, environment, saved['arguments'], values)
        xml_args = xml_activation_args(options, old_env, environment, saved['arguments'], values)
        ots_args = ots_activation_args(options, old_env, environment, saved['arguments'], values,
                                       sdk['sourceprep'].PREPARED_TREE_RECEIPT)
        leveldb_args = leveldb_activation_args(options, old_env, environment, saved['arguments'], values,
                                       sdk['sourceprep'].PREPARED_TREE_RECEIPT)
        codec_args = codec_activation_args(options, old_env, environment, saved['arguments'], values)
        pdf_args = pdfium_activation_args(options, old_env, environment, saved['arguments'], values)
        pffft_args = pffft_activation_args(options, old_env, environment, saved['arguments'], values)
        expat_args = expat_activation_args(options, old_env, environment, saved['arguments'], values)
        cpuinfo_args = cpuinfo_activation_args(options, old_env, environment, saved['arguments'], values)
        vulkan_args = vulkan_activation_args(options, old_env, environment, saved['arguments'], values)
        woff2_args = woff2_activation_args(options, old_env, environment, saved['arguments'], values)
        snappy_args = snappy_activation_args(options, old_env, environment, saved['arguments'], values)
        openh264_args = openh264_activation_args(options, old_env, environment, saved['arguments'], values)
        image_args = image_activation_args(options, old_env, environment, saved['arguments'], values)
        font_args = font_activation_args(options, old_env, environment, saved['arguments'], values)
        buildlink_args = additive_host_buildlink_relocation(
            saved['arguments'], values, old_env, environment, work)
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
                         'use_litert_tflite', 'emberbsd_flatc', 'emberbsd_flatc_inputs',
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
                         'emberbsd_protobuf_native_prefix', 'emberbsd_protobuf_target_prefix',
                         'emberbsd_abseil_host_headers', 'emberbsd_abseil_host_inputs',
                         'emberbsd_abseil_target_headers', 'emberbsd_abseil_target_inputs',
                         'v8_enable_temporal_systemicu',
                         'emberbsd_icuuc_host_library', 'emberbsd_icuuc_target_library',
                         'emberbsd_icui18n_host_library', 'emberbsd_icui18n_target_library',
                         'emberbsd_re2_host_library', 'emberbsd_re2_target_library',
                         'emberbsd_protoc',
                         'emberbsd_common_image',
                         'use_system_libjpeg',
                         'emberbsd_jpeg_host_libraries',
                         'emberbsd_jpeg_host_inputs',
                         'emberbsd_jpeg_target_libraries',
                         'emberbsd_jpeg_target_inputs',
                         'emberbsd_webp_host_libraries',
                         'emberbsd_webp_host_inputs',
                         'emberbsd_webp_target_libraries',
                         'emberbsd_webp_target_inputs',
                         'emberbsd_zlib_host_libraries',
                         'emberbsd_zlib_host_inputs',
                         'emberbsd_zlib_target_libraries',
                         'emberbsd_zlib_target_inputs',
                         'emberbsd_minizip_host_libraries',
                         'emberbsd_minizip_host_inputs',
                         'emberbsd_minizip_target_libraries',
                         'emberbsd_minizip_target_inputs',
                         'custom_toolchain', 'v8_snapshot_toolchain', 'v8_host_paxctl', 'emberbsd_mac_toolchain_bin',
                         'emberbsd_sdk_source', 'mac_sdk_path', 'mac_deployment_target',
                         'apple_linker_launcher', 'unbundle_linker_launcher', 'concurrent_links',
                         'rust_sysroot_absolute', 'rust_bindgen_root', 'rustc_version',
                         'use_custom_libcxx', 'use_custom_libcxx_for_host', 'use_custom_libunwind',
                         'external_libcxx_has_extensive_hardening', 'emberbsd_native_libcxx_hardened', 'emberbsd_native_cpu',
                         'emberbsd_native_cc', 'emberbsd_native_cxx',
                         'use_lld', 'emberbsd_target_strip', 'emberbsd_target_objcopy'}
        if getattr(options, 'shared_ffmpeg', False):
            require(saved['arguments'].get('use_system_ffmpeg') in (None, False, True),
                    'invalid previous FFmpeg selection')
        identity_args.update(('emberbsd_common_ots', 'emberbsd_ots_identity'))
        identity_args.update(('emberbsd_common_leveldb', 'emberbsd_leveldb_identity'))
        identity_args.update(('emberbsd_common_spirv_tools', 'emberbsd_spirv_source_identity'))
        identity_args.update('emberbsd_' + name + '_' + role + '_' + kind
                             for name in ('spirv_tools', 'spirv_link', 'spirv_core')
                             for role in ('host', 'target') for kind in ('libraries', 'inputs'))
        identity_args.update('emberbsd_spirv_tools_' + role + '_table' for role in ('host', 'target'))
        identity_args.update('emberbsd_spirv_headers_' + role + '_inputs' for role in ('host', 'target'))
        identity_args.add('emberbsd_common_pffft')
        identity_args.update('emberbsd_pffft_' + role + '_' + kind
                             for role in ('host', 'target') for kind in ('libraries', 'inputs'))
        identity_args.add('emberbsd_common_expat')
        identity_args.update('emberbsd_expat_' + role + '_' + kind
                             for role in ('host', 'target') for kind in ('libraries', 'inputs'))
        identity_args.add('emberbsd_common_cpuinfo')
        identity_args.update('emberbsd_cpuinfo_' + role + '_' + kind
                             for role in ('host', 'target') for kind in ('libraries', 'inputs'))
        identity_args.update(('emberbsd_common_vulkan', 'angle_use_custom_libvulkan'))
        identity_args.update('emberbsd_vulkan_' + role + '_' + kind
                             for role in ('host', 'target') for kind in ('library', 'inputs', 'runtime_dir'))
        identity_args.update('emberbsd_vulkan_headers_' + role + '_' + kind
                             for role in ('host', 'target') for kind in ('include', 'inputs'))
        identity_args.add('emberbsd_common_woff2')
        identity_args.update('emberbsd_woff2_' + role + '_' + kind
                             for role in ('host', 'target') for kind in ('libraries', 'inputs'))
        identity_args.add('emberbsd_common_snappy')
        identity_args.update('emberbsd_snappy_' + role + '_' + kind
                             for role in ('host', 'target') for kind in ('libraries', 'inputs'))
        identity_args.update(('emberbsd_common_openh264', 'rtc_system_openh264'))
        identity_args.update('emberbsd_openh264_' + role + '_' + kind
                             for role in ('host', 'target') for kind in ('libraries', 'inputs'))
        identity_args.update(('emberbsd_common_pdf', 'use_system_lcms2', 'use_system_libopenjpeg2', 'use_system_libtiff'))
        identity_args.update('emberbsd_' + provider + '_' + role + '_' + kind
                             for provider in ('lcms2', 'openjpeg', 'tiff')
                             for role in ('host', 'target') for kind in ('libraries', 'inputs'))
        identity_args.add('emberbsd_common_codecs')
        identity_args.update('emberbsd_' + provider + '_' + role + '_' + kind
                             for provider in ('dav1d', 'aom', 'vpx', 'opus', 'flac')
                             for role in ('host', 'target') for kind in ('libraries', 'inputs'))
        identity_args.update(('enable_swiftshader', 'enable_swiftshader_vulkan', 'angle_enable_swiftshader', 'dawn_use_swiftshader'))
        identity_args.update('emberbsd_' + provider + '_' + role + '_' + kind
                             for provider in ('xml', 'xslt') for role in ('host', 'target')
                             for kind in ('library', 'inputs'))
        identity_args.update('emberbsd_' + provider + '_' + role + '_' + kind
                             for provider in ('freetype', 'harfbuzz') for role in ('host', 'target')
                             for kind in ('libraries', 'inputs'))
        identity_args.update(('emberbsd_common_font', 'use_system_freetype', 'use_system_harfbuzz'))
        identity_args.update('node_shared_' + feature for feature in NODE_SHARED_FEATURES)
        node_provider_path_changed = verified_node_configure_path_change(
            saved['arguments'], values, options.v8_source, native.tool('python'),
            options.sdk_source, source_owner_environment(environment),
            getattr(options, 'node_ports_source', None) or options.ports_source)
        for name in identity_args:
            if name in swiftshader_changed:
                continue
            if deployment_changed and name in ('mac_deployment_target', 'v8_metagen_host_extra_flags'):
                continue
            if node_source_refresh and name == 'emberbsd_node_source_identity':
                continue
            if (name in activation_args or name in minizip_args or name in xml_args or
                    name in image_args or name in font_args or name in pdf_args or name in codec_args or name in openh264_args or name in pffft_args or name in expat_args or name in cpuinfo_args or name in vulkan_args or name in ots_args or name in leveldb_args or name in spirv_args or name in woff2_args or name in snappy_args or name in buildlink_args):
                continue
            if name in ('use_litert_tflite', 'emberbsd_flatc', 'emberbsd_flatc_inputs') and getattr(options, 'activate_common_ml', False) and not old_ml:
                continue
            if name in permitted_runtime_args:
                continue
            if name in node_provider_path_changed:
                continue
            require(values.get(name) == saved['arguments'].get(name), 'GN identity changed: ' + name)

        # Preserve previous bindings. The final path appears in GN/Ninja command
        # lines so a changed record forces the corresponding commands to rerun.
        bound = bind_versioned(sdk, native, work / 'target-commands', new_commands)
        environment['CC'] = shlex.quote(bound['cc'])
        environment['CXX'] = shlex.quote(bound['cxx'])
        if build_after_reconfigure:
            prepare_build_inputs(options, native, environment, sdk)
        elif (not cleanup_only and not getattr(options, 'migrate_devtools_modules_only', False) and
              not getattr(options, 'migrate_ml_alias_root', None)):
            prepare_source_inputs(options, native, environment, sdk)

        if getattr(options, 'migrate_devtools_modules_only', False):
            require(not build_after_reconfigure, 'migration-only cannot build')
            migrate_devtools_only(options, work)
            return

        if origin:
            expected_config = dict(arguments=values, environment=environment, source=str(options.workspace),
                                   sdk=str(options.sdk_source), host_prefix=str(options.host_prefix),
                                   target=options.target)
            config_path = work / 'configuration.json'
            def config_is_new():
                return (config_path.is_file() and not config_path.is_symlink() and
                        json.loads(config_path.read_bytes()) == expected_config)
            old_workspace, old_node, old_v8 = saved_source_origin_inputs(saved)
            old_spirv = (json.loads(old_env['EMBERBSD_SPIRV_SELECTION'])
                         if old_env.get('EMBERBSD_SPIRV_SELECTION') else None)
            if not cleanup_only:
                require(old_workspace == origin, 'saved old workspace changed')
                verify_saved_source_provider(options, sdk, native, environment, saved, 'NODE', old_node)
                verify_saved_source_provider(options, sdk, native, environment, saved, 'V8', old_v8)

            def view_options(path, source, node, v8, *, factory=False):
                selected = argparse.Namespace(**vars(options))
                selected.work = path.parent
                selected.source_view_destination = path
                selected.workspace, selected.node_source, selected.v8_source = source, node, v8
                selected.phase = 'configure' if factory else 'build'
                selected.verify_selected_source_view = not factory
                for name in ('refresh_source_view', 'activate_common_ml', 'activate_common_providers',
                             'migrate_devtools_modules_only', 'resume_configure', 'retry_configure'):
                    setattr(selected, name, False)
                if factory:
                    for name in tuple(vars(selected)):
                        if name.startswith('old_'):
                            setattr(selected, name, None)
                return selected

            def verify_old(path, *, legacy_root=None):
                require(not cleanup_only, 'old configuration is unavailable')
                for relative, target in (('v8', old_v8), ('third_party/electron_node', old_node)):
                    link = path / 'src' / relative
                    require(link.is_symlink() and os.readlink(link) == str(target),
                            'old source provider link changed: ' + relative)
                previous_options = view_options(path, old_workspace, old_node, old_v8)
                previous_options.spirv_selection = old_spirv
                previous_options.source_view_created_files = None
                previous_options.source_view_created_links = None
                previous_options.source_view_publication = None
                result = gn_source(previous_options, retired=True, legacy_ml_root=legacy_root)
                require(result == path / 'src', 'old source view verification returned another path')

            def verify_new(path, *, legacy_root=None):
                result = gn_source(view_options(path, options.workspace, options.node_source, options.v8_source),
                                   legacy_ml_root=legacy_root)
                require(result == path / 'src', 'new source view verification returned another path')

            def prepare_existing_new(path):
                result = gn_source(view_options(path, options.workspace, options.node_source, options.v8_source),
                                   refresh_selected=True)
                require(result == path / 'src', 'new source view refresh returned another path')

            def build_new(path):
                result = gn_source(view_options(path, options.workspace, options.node_source, options.v8_source,
                                                factory=True), previous_view=work / 'source-view')
                require(result == path / 'src', 'source view factory returned another path')

            def commit_config():
                try:
                    write_devtools_identity(work, sdk, environment)
                    write_protoc_selection(work, sdk, options.protoc_selection)
                    write_v8_metagen_selection(work, sdk, getattr(options, 'v8_metagen_selection', None))
                    (output / 'args.gn').write_text(gn_arguments(values))
                    sdk['process'].run_logged([native.tool('gn'), 'gen', str(output),
                        '--script-executable=' + native.tool('python'), '--ninja-executable=' + native.tool('ninja'),
                        '--root-target=//electron', '--root-pattern=//electron:electron_dist_zip', '--fail-on-unused-args'],
                        str(work / 'reconfigure.log'), cwd=str(work / 'source-view/src'), env=environment,
                        append=(work / 'reconfigure.log').exists())
                    local_module('electron_build_source', 'prepare-build-sources.py').atomic_json(
                        config_path, expected_config)
                except BaseException:
                    if not config_is_new():
                        (output / 'args.gn').write_text(old_args)
                    raise

            transition = local_module('electron_source_origin_transition', 'source-origin-transition.py')
            legacy_factory = getattr(options, 'migrate_ml_alias_root', None)
            if legacy_factory is not None:
                stable, backup = work / 'source-view', work / '.source-view-origin-backup'
                mode = ml_alias_migration_mode(work, config_path, saved_bytes, legacy_factory, origin=origin,
                                               cleanup_only=cleanup_only, build_after=build_after_reconfigure,
                                               marker_text=transition.MARKER)
                ml = local_module('electron_ml_source_view', 'ml-source-view.py')
                view = local_module('electron_protobuf_source_view', 'protobuf-source-view.py')
                complete_ml_alias_migration(
                    mode, stable, backup, legacy_factory, verify_old, verify_new,
                    lambda path, previous: ml.migrate_aliases(view, path, previous),
                    lambda: prepare_source_inputs(options, native, environment, sdk))
            transition.transition(work, saved_configuration=saved_bytes, config_is_new=config_is_new,
                                  verify_old=verify_old, verify_new=verify_new,
                                  build_new=build_new, prepare_existing_new=prepare_existing_new,
                                  commit_config=commit_config)
            return

        # A failed or interrupted GN run may leave a partial graph. The marker
        # prevents build until a later successful reconfigure repairs it.
        marker = work / 'reconfigure-incomplete'
        marker.write_text('GN reconfiguration incomplete\n')
        try:
            source_root = gn_source(options)
            write_devtools_identity(work, sdk, environment)
            write_protoc_selection(work, sdk, options.protoc_selection)
            write_v8_metagen_selection(work, sdk, getattr(options, 'v8_metagen_selection', None))
            (output / 'args.gn').write_text(gn_arguments(values))
            sdk['process'].run_logged([native.tool('gn'), 'gen', str(output),
                '--script-executable=' + native.tool('python'), '--ninja-executable=' + native.tool('ninja'),
                '--root-target=//electron', '--root-pattern=//electron:electron_dist_zip', '--fail-on-unused-args'],
                str(work / 'reconfigure.log'), cwd=str(source_root), env=environment,
                append=(work / 'reconfigure.log').exists())
            local_module('electron_build_source', 'prepare-build-sources.py').atomic_json(
                work / 'configuration.json',
                dict(arguments=values, environment=environment, source=str(options.workspace),
                     sdk=str(options.sdk_source), host_prefix=str(options.host_prefix), target=options.target))
        except BaseException:
            (output / 'args.gn').write_text(old_args)
            raise
        marker.unlink()
        if build_after_reconfigure:
            # Keep Ninja failures outside the GN rollback path: the new graph
            # and configuration are valid even if the compile is interrupted.
            run_ninja(options, sdk, native, source_root, environment)

def build(options):
    keep_going_limit(options)
    require_common_v8(options)
    require_common_node(options)
    require_common_perfetto(options)
    require_common_dependencies(options)
    require(not (options.work / 'reconfigure-incomplete').exists(),
            'incomplete reconfiguration; rerun reconfigure before build')
    sdk = load_sdk(options.sdk_source)
    verify_source(options.workspace, options.ports_source, options.git)
    native, environment, values = producer_inputs(options, sdk)
    prepare_build_inputs(options, native, environment, sdk)
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
    options.old_boringssl_identity = saved_env['EMBERBSD_BORINGSSL_SOURCE_SHA256']
    options.old_compression_identity = saved_env['EMBERBSD_COMPRESSION_SOURCE_SHA256']
    options.old_pffft_identity = saved_env.get('EMBERBSD_PFFFT_SOURCE_SHA256')
    options.old_expat_identity = saved_env.get('EMBERBSD_EXPAT_SOURCE_SHA256')
    options.old_cpuinfo_identity = saved_env.get('EMBERBSD_CPUINFO_SOURCE_SHA256')
    options.old_vulkan_identity = saved_env.get('EMBERBSD_VULKAN_SOURCE_SHA256')
    options.old_woff2_identity = saved_env.get('EMBERBSD_WOFF2_SOURCE_SHA256')
    options.old_snappy_identity = saved_env.get('EMBERBSD_SNAPPY_SOURCE_SHA256')
    options.old_openh264_identity = saved_env.get('EMBERBSD_OPENH264_SOURCE_SHA256')
    options.old_codec_identity = saved_env.get('EMBERBSD_CODEC_SOURCE_SHA256')
    options.old_image_identity = saved_env.get('EMBERBSD_IMAGE_SOURCE_SHA256')
    options.old_font_identity = saved_env.get('EMBERBSD_FONT_SOURCE_SHA256')
    options.old_pdf_identity = saved_env.get('EMBERBSD_PDF_SOURCE_SHA256')
    options.old_ots_selection = json.loads(saved_env['EMBERBSD_OTS_SELECTION']) if saved_env.get('EMBERBSD_OTS_SELECTION') else None
    options.old_leveldb_selection = json.loads(saved_env['EMBERBSD_LEVELDB_SELECTION']) if saved_env.get('EMBERBSD_LEVELDB_SELECTION') else None
    options.old_spirv_selection = json.loads(saved_env['EMBERBSD_SPIRV_SELECTION']) if saved_env.get('EMBERBSD_SPIRV_SELECTION') else None
    options.old_sqlite_selection = json.loads(saved_env['EMBERBSD_SQLITE_SELECTION']) if saved_env.get('EMBERBSD_SQLITE_SELECTION') else None
    options.old_xml_identity = saved_env.get('EMBERBSD_XML_SOURCE_SHA256')
    options.old_minizip_identity = saved_env.get('EMBERBSD_MINIZIP_SOURCE_SHA256')
    options.old_ffmpeg_identity = saved_env.get('EMBERBSD_FFMPEG_SOURCE_SHA256')
    options.old_media_header_identities = {name: saved_env['EMBERBSD_MEDIA_HEADER_' + name.upper() + '_SHA256']
                                           for name in ('libyuv', 'libsrtp')}
    write_protoc_selection(options.work, sdk, options.protoc_selection)
    write_v8_metagen_selection(options.work, sdk, getattr(options, 'v8_metagen_selection', None))
    fingerprint = options.work / 'devtools-provider.json'
    require(not fingerprint.is_symlink() and fingerprint.is_file() and
            json.loads(fingerprint.read_text()) ==
            {'schemaVersion': 1, 'sha256': environment['EMBERBSD_DEVTOOLS_PROVIDER_SHA256']},
            'DevTools provider input changed; reconfigure required')
    output = options.work / 'out'
    require((output / 'args.gn').read_text() == gn_arguments(values), 'configured GN arguments changed')
    source_root = gn_source(options)
    run_ninja(options, sdk, native, source_root, saved_env)


def context_keys(*paths):
    """Canonicalize lock keys without changing producer input paths."""
    return sorted({str(Path(path).resolve(strict=False)) for path in paths if path is not None})


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    def nonnegative_integer(value):
        try:
            result = int(value)
        except ValueError as error:
            raise argparse.ArgumentTypeError('must be an integer >= 0') from error
        if result < 0:
            raise argparse.ArgumentTypeError('must be an integer >= 0')
        return result

    sub = parser.add_subparsers(dest='phase', required=True)
    source = sub.add_parser('prepare')
    for name in ('workspace', 'ports-source', 'pkgsrc', 'archive', 'destination', 'git', 'patch'):
        source.add_argument('--' + name, type=Path, required=True)
    source.add_argument('--previous-prepared', type=Path)
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
                     'ots-source', 'ots-archive', 'ots-patch', 'ots-pkgsrc-export', 'ots-export-patch',
                     'leveldb-source', 'leveldb-archive', 'leveldb-patch', 'leveldb-pkgsrc-export', 'leveldb-export-patch',
                     'spirv-source', 'spirv-archive', 'spirv-patch', 'spirv-pkgsrc-export', 'spirv-export-patch',
                     'sqlite-source', 'sqlite-archive', 'sqlite-amalgamation', 'sqlite-patch',
                     'sqlite-pkgsrc-export', 'sqlite-export-patch',
                     'protobuf-source', 'protobuf-ports-source', 'protobuf-archive', 'protobuf-patch',
                     'node-source', 'node-pkgsrc', 'node-ports-source', 'gyp-source', 'gyp-pkgsrc', 'perfetto-source', 'perfetto-ports-source',
                     'perfetto-archive', 'perfetto-patch', 'v8-source', 'v8-ports-source', 'v8-pkgsrc',
                     'v8-metagen-libclang-so', 'v8-metagen-bindings-dir', 'v8-metagen-runtime-view',
                     'host-tool-runtime-view', 'boringssl-source', 'boringssl-archive', 'ml-patch', 'ml-pkgsrc-export', 'ml-ports-source', 'ml-export-patch', *( 'ml-' + name + '-' + role for name in ML_PROVIDERS for role in ('source', 'archive'))):
            command.add_argument('--' + name, type=Path)
        command.add_argument('--v8-metagen-runtime-extra', type=Path, action='append', default=[])
        for provider in ML_PROVIDERS:
            for role in ('ports-source', 'pkgsrc-export', 'export-patch'):
                command.add_argument('--ml-' + provider + '-' + role, type=Path)
        command.add_argument('--host-buildlink-host-toolchain', action='store_true')
        command.add_argument('--perfetto-scoped-runtime', action='store_true')
        command.add_argument('--node-scoped-runtime', action='store_true')
        command.add_argument('--shared-undici', action='store_true')
        command.add_argument('--shared-abseil', action='store_true')
        command.add_argument('--shared-icu', action='store_true')
        command.add_argument('--shared-re2', action='store_true')
        command.add_argument('--shared-ffmpeg', action='store_true')
        command.add_argument('--shared-minizip', action='store_true')
        command.add_argument('--shared-xml', action='store_true')
        command.add_argument('--shared-image', action='store_true')
        command.add_argument('--shared-font', action='store_true')
        command.add_argument('--shared-pdf-libraries', action='store_true')
        command.add_argument('--shared-codecs', action='store_true')
        command.add_argument('--shared-openh264', action='store_true')
        command.add_argument('--shared-expat', action='store_true')
        command.add_argument('--shared-cpuinfo', action='store_true')
        command.add_argument('--shared-vulkan', action='store_true')
        command.add_argument('--shared-spirv-tools', action='store_true')
        command.add_argument('--shared-woff2', action='store_true')
        command.add_argument('--shared-snappy', action='store_true')
        command.add_argument('--shared-pffft', action='store_true')
        if phase == 'configure':
            initial = command.add_mutually_exclusive_group()
            initial.add_argument('--resume-configure', action='store_true',
                                 help='resume an initial incomplete configuration without GN outputs')
            initial.add_argument('--retry-configure', action='store_true',
                                 help='retry failed GN with verified selected inputs')
        if phase == 'reconfigure':
            command.add_argument('--previous-source', type=Path,
                                 help='verify and replace the previously configured source workspace')
            command.add_argument('--migrate-ml-alias-root', type=Path,
                                 help='migrate verified legacy ML aliases from an explicit prior view root')
            command.add_argument('--reuse-host-buildlink', type=Path,
                                 help='reuse an equivalent existing host buildlink context')
            command.add_argument('--activate-common-ml', action='store_true',
                                 help='activate verified common ML sources without replacing the source view')
            command.add_argument('--activate-common-providers', action='store_true',
                                 help='activate verified common providers without replacing the source view')
            command.add_argument('--migrate-devtools-modules-only', action='store_true',
                                 help='migrate verified DevTools modules and require subsequent GN reconfigure')
            command.add_argument('--refresh-source-view', action='store_true',
                                 help='recompose generated sources, preserving existing Ninja objects')
            command.add_argument('--build-after-reconfigure', action='store_true',
                                 help='run Ninja after a successful reconfigure without releasing input locks')
        command.add_argument('--macos-minimum')
        command.add_argument('--gcc-platform-reason')
        command.add_argument('--jobs', type=int)
        if phase in ('reconfigure', 'build'):
            command.add_argument('--keep-going', type=nonnegative_integer, default=1,
                                 help='continue independent Ninja jobs until N jobs fail (0 means no failure limit)')
    options = parser.parse_args()
    try:
        for name, value in vars(options).items():
            if isinstance(value, Path):
                require(value.is_absolute(), '--' + name.replace('_', '-') + ' must be absolute')
        if options.phase == 'prepare':
            print('Materialized source files:', prepare(options))
        else:
            sdk = load_sdk(options.sdk_source)
            options.jobs = sdk['cpu_capacity'].resolve_jobs(options.jobs)
            exclusive = context_keys(options.workspace, options.work)
            with sdk['process'].ContextLocks(exclusive, str(options.lock_root)):
                origin_roots = ()
                if getattr(options, 'previous_source', None):
                    previous = options.work / '.source-view-origin-old-configuration.json'
                    marker = options.work / 'reconfigure-incomplete'
                    backup = options.work / '.source-view-origin-backup'
                    current = options.work / 'configuration.json'
                    if os.path.lexists(previous):
                        require(previous.is_file() and not previous.is_symlink(),
                                'invalid saved source-origin configuration')
                        saved_path = previous
                    else:
                        require(not os.path.lexists(backup), 'old view lacks saved configuration')
                        saved_path = current
                    require(saved_path.is_file() and not saved_path.is_symlink(),
                            'invalid producer configuration')
                    options.origin_saved_configuration = saved_path.read_bytes()
                    origin_saved = json.loads(options.origin_saved_configuration)
                    origin_roots = saved_source_origin_inputs(origin_saved)
                    if origin_saved['environment'].get('EMBERBSD_SPIRV_SELECTION'):
                        saved_spirv = json.loads(origin_saved['environment']['EMBERBSD_SPIRV_SELECTION'])
                        require(Path(saved_spirv['path']).is_absolute(), 'invalid saved SPIRV source')
                        origin_roots += (Path(saved_spirv['path']),)
                    cleanup_only = (not os.path.lexists(previous) and
                                    not os.path.lexists(backup) and
                                    marker.is_file() and not marker.is_symlink() and
                                    marker.read_text() == 'GN reconfiguration incomplete\nsource-origin-v1\n' and
                                    origin_roots[0] == options.workspace)
                    require(origin_roots[0] == options.previous_source or cleanup_only,
                            'previous source differs from saved producer configuration')
                selected = (options.ports_source, options.sdk_source, options.protobuf_source,
                            options.protobuf_ports_source, options.protobuf_archive, options.protobuf_patch,
                            options.node_source, options.node_pkgsrc, options.node_ports_source, options.gyp_source, options.gyp_pkgsrc, options.perfetto_source,
                            options.perfetto_ports_source, options.perfetto_archive, options.perfetto_patch,
                            options.v8_source, options.v8_ports_source, options.v8_pkgsrc,
                            options.v8_metagen_libclang_so, options.v8_metagen_bindings_dir, options.v8_metagen_runtime_view,
                            options.target_runtime_stage, options.target_runtime_base, options.host_runtime_root, options.protoc_runtime_view,
                            options.host_prefix, options.sysroot, options.host_buildlink_pkgsrc,
                            options.boringssl_source, options.boringssl_archive,
                            options.ots_source, options.ots_archive, options.ots_patch, options.ots_pkgsrc_export, options.ots_export_patch,
                            options.leveldb_source, options.leveldb_archive, options.leveldb_patch, options.leveldb_pkgsrc_export, options.leveldb_export_patch,
                            options.spirv_source, options.spirv_archive, options.spirv_patch, options.spirv_pkgsrc_export, options.spirv_export_patch,
                            options.sqlite_source, options.sqlite_archive, options.sqlite_amalgamation,
                            options.sqlite_patch, options.sqlite_pkgsrc_export, options.sqlite_export_patch,
                            options.host_buildlink_stage_root, options.ml_patch, options.ml_pkgsrc_export, options.ml_ports_source, options.ml_export_patch,
                            *(getattr(options, 'ml_' + name.replace('-', '_') + '_' + role)
                              for name in ML_PROVIDERS for role in ('source', 'archive', 'ports_source', 'pkgsrc_export', 'export_patch')))
                shared = [key for key in context_keys(*selected, *origin_roots) if key not in exclusive]
                with sdk['process'].ContextLocks(shared, str(options.lock_root), shared=True):
                    {'configure': configure, 'reconfigure': reconfigure, 'build': build}[options.phase](options)
    except Exception as error:
        parser.exit(1, 'Electron ' + options.phase + ' failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
