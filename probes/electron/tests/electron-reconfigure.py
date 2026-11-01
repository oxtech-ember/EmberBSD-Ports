#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Run reconfigure/build orchestration against real GN and bounded fixtures."""
import argparse
from contextlib import nullcontext, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

p = argparse.ArgumentParser()
p.add_argument('--host-prefix', type=Path, required=True)
p.add_argument('--sdk-source', type=Path, required=True)
args = p.parse_args(); host = args.host_prefix
owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / 'electron44/files/build-electron.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

class LockStub:
    @staticmethod
    def ContextLocks(*_args, **_kwargs): return nullcontext()

selected = []
def controller_cli(extra):
    paths = {name: Path('/tmp/electron-cli-' + name) for name in (
        'workspace', 'ports-source', 'sdk-source', 'host-prefix', 'compiler-prefix',
        'sysroot', 'work', 'git', 'lock-root', 'link-context')}
    argv = [str(owner / 'electron44/files/build-electron.py'), 'build']
    for name, path in paths.items(): argv.extend(('--' + name, str(path)))
    argv.extend(('--target', 'amd64', *extra))
    with patch.object(sys, 'argv', argv), \
         patch.object(b, 'load_sdk', return_value={'process': LockStub}), \
         patch.object(b, 'build', side_effect=lambda options: selected.append(options)):
        b.main()

controller_cli([])
assert selected[-1].keep_going == 1, 'CLI default must preserve Ninja -k 1 behavior'
controller_cli(['--keep-going', '0'])
assert selected[-1].keep_going == 0, 'CLI must accept Ninja keep-going 0'
selected.clear(); sdk_loads = []
with patch.object(sys, 'argv', [str(owner / 'electron44/files/build-electron.py'), 'build',
        '--workspace', '/tmp/w', '--ports-source', '/tmp/p', '--sdk-source', '/tmp/s',
        '--host-prefix', '/tmp/h', '--compiler-prefix', '/tmp/c', '--sysroot', '/tmp/t',
        '--work', '/tmp/o', '--git', '/tmp/g', '--lock-root', '/tmp/l', '--link-context', '/tmp/k',
        '--target', 'amd64', '--keep-going', '-1']), \
     patch.object(b, 'load_sdk', side_effect=lambda *_: sdk_loads.append(True)), \
     redirect_stderr(io.StringIO()) as stderr:
    try: b.main(); raise AssertionError('accepted negative keep-going')
    except SystemExit as error: assert error.code == 2
assert not selected and not sdk_loads and 'keep-going' in stderr.getvalue()

class Native:
    path = str(host / 'bin')
    def tool(self, name):
        return str(host / 'bin' / ('python3.15' if name == 'python' else name))
class Process:
    calls = 0
    ninja_calls = []
    events = []
    ninja_failure = False
    @staticmethod
    def run_logged(argv, log, *, append=False, **kwargs):
        if Path(argv[0]).name == 'ninja':
            Process.events.append('ninja')
            Process.ninja_calls.append(list(argv))
            with Path(log).open('a' if append else 'x') as stream:
                stream.write('fixture Ninja invocation\n')
                if Process.ninja_failure:
                    stream.write('fixture Ninja failure\n')
                    raise RuntimeError('fixture Ninja failure')
                output = Path(argv[argv.index('-C') + 1])
                (output / 'dist.zip').write_bytes(b'fixture Electron archive')
            return
        Process.calls += 1
        Process.events.append('gn')
        with Path(log).open('a' if append else 'x') as stream:
            stream.write(f'fixture GN invocation {Process.calls}\n')
            r = subprocess.run(argv, cwd=kwargs['cwd'], env=kwargs['env'], capture_output=True, text=True)
            stream.write(r.stdout + r.stderr)
        if r.returncode: raise RuntimeError(r.stdout + r.stderr)
class Source:
    stage_calls = []
    @staticmethod
    def atomic_json(path, value):
        tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(value)); tmp.replace(path)
    @staticmethod
    def load_sdk(_):
        return {'fixture': True}
    @staticmethod
    def stage_runtime(archive, destination, **kwargs):
        assert Path(archive).read_bytes() == b'fixture Electron archive'
        Source.stage_calls.append((archive, destination, kwargs))
with tempfile.TemporaryDirectory(prefix='electron-reconfigure-test-') as temp:
    root = Path(temp); src = root/'source/src'; src.mkdir(parents=True)
    work = root/'work'; out = work/'out'; out.mkdir(parents=True)
    (work/'target-commands').mkdir(); binding = work/'target-commands/commands.json'
    base=[str(host/'bin/clang'), '--target=x86_64--netbsd', '--sysroot=/target', '-resource-dir=/target/clang']
    commands=dict(format='emberbsd-compiler-binding',version=1, aliases={},
                  commands={'cc':base, 'cxx':base, 'cpp':base},
                  flags={name:[] for name in ('cppflags','cflags','cxxflags','ldflags')},
                  link_flags={'cc':['--ld-path=/ld','--rtlib=compiler-rt','--unwindlib=libunwind'],
                              'cxx':['--ld-path=/ld','--rtlib=compiler-rt','--unwindlib=libunwind','-stdlib=libc++']})
    binding.write_text(json.dumps(commands))
    (src/'.gn').write_text('buildconfig="//BUILDCONFIG.gn"\n')
    (src/'BUILDCONFIG.gn').write_text('declare_args() {\n emberbsd_node_provider_inputs=[]\n emberbsd_typescript_definitions=[]\n emberbsd_node_source_identity=""\n emberbsd_node_configure_helper=""\n emberbsd_node_configure_inputs=[]\n emberbsd_node_configure_dependencies=[]\n node_module_version=0\n emberbsd_native_pkg_config_prefix=""\n emberbsd_protoc_runtime_launcher=""\n emberbsd_protoc_runtime_view=""\n emberbsd_protoc_runtime_inputs=[]\n node_host_runtime_python=""\n node_host_runtime_launcher=""\n node_host_runtime_view=""\n node_host_runtime_inputs=[]\n perfetto_host_runtime_launcher=""\n perfetto_host_runtime_view=""\n perfetto_host_runtime_inputs=[]\n v8_prepared_source_receipt=""\n v8_version_hash_salt_files=[]\n v8_version_hash_salt=""\n feature=false\n clang_version=""\n}\nset_default_toolchain("//:tools")\n')
    (src/'BUILD.gn').write_text('toolchain("tools") {\n tool("stamp") { command="touch {{output}}" }\n}\n')
    (src/'electron/build/args').mkdir(parents=True)
    (src/'electron/build/args/release.gn').write_text('')
    gnfile = src/'electron/BUILD.gn'; gnfile.write_text('group("electron_dist_zip") {}\n')
    old_v8_root = str((root/'work/electron45-inputs-2/v8-source').resolve())
    new_v8_root = str((root/'work/electron45-inputs-2/v8-source-9fbbb688').resolve())
    node_configure_paths = {
        'gyp-source': root/'gyp-source', 'gyp-pkgsrc': root/'gyp-pkgsrc',
        'v8-source': old_v8_root, 'inspector-source': root/'inspector-source',
        'sdk-source': root/'sdk-source', 'jinja-root': root/'jinja-root',
        'zlib-source': root/'zlib-source', 'v8-cxx-wrapper': root/'v8-cxx-wrapper',
        'v8-selected-clang': root/'v8-selected-clang', 'v8-libclang': root/'v8-libclang',
        'v8-python-bindings': root/'v8-python-bindings', 'v8-clang-resource': root/'v8-clang-resource',
    }
    old_node_configure_inputs = [name+'='+str(path) for name,path in node_configure_paths.items()]
    old_node_configure_dependencies = sorted(str(path) for path in (
        root/'ports/scripts/source-inputs/node/configure-inputs.py',
        root/'gyp-source/emberbsd-prepared-source.json',
        root/'gyp-pkgsrc/devel/gyp/files/verify-source.py',
        root/'gyp-pkgsrc/EMBERBSD-PKGSRC-REVISION',
        root/'gyp-pkgsrc/EMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py',
        Path(old_v8_root)/'emberbsd-prepared-source.json',
        root/'inspector-source/emberbsd-prepared-source.json',
        root/'jinja-root/jinja2/__init__.py', root/'v8-cxx-wrapper', root/'v8-selected-clang',
        root/'v8-libclang', root/'v8-python-bindings/clang/cindex.py',
        root/'v8-python-bindings/clang/__init__.py'))
    new_node_configure_inputs = [row if not row.startswith('v8-source=') else 'v8-source='+new_v8_root
                                 for row in old_node_configure_inputs]
    new_node_configure_dependencies = sorted(
        str(Path(new_v8_root)/'emberbsd-prepared-source.json')
        if row == str(Path(old_v8_root)/'emberbsd-prepared-source.json') else row
        for row in old_node_configure_dependencies)
    native_runtime = root/'native-runtime'; runtime_lib = native_runtime/'lib'; runtime_lib.mkdir(parents=True)
    for name in ('libprotobuf.36.2.0.dylib', 'libz.1.dylib', 'libre2.11.0.0.dylib', 'libother.dylib'):
        (runtime_lib/name).write_bytes(name.encode())
    foreign_runtime = root/'foreign-runtime'; foreign_lib = foreign_runtime/'lib'; foreign_lib.mkdir(parents=True)
    (foreign_lib/'libforeign.dylib').write_bytes(b'foreign provider')
    buildlink = root/'host-buildlink'; buildlink_lib = buildlink/'lib'; buildlink_lib.mkdir(parents=True)
    for name in ('libprotobuf.36.2.0.dylib', 'libz.1.dylib', 'libre2.11.dylib'):
        target = {'libre2.11.dylib':'libre2.11.0.0.dylib'}.get(name, name)
        (buildlink_lib/name).symlink_to(runtime_lib/target)
    (buildlink_lib/'libforeign.dylib').symlink_to(foreign_lib/'libforeign.dylib')
    old_view = root/'protoc-runtime-old'; old_view.mkdir()
    new_view = root/'protoc-runtime-new'; new_view.mkdir()
    for alias, target in (('libprotobuf.36.2.0.dylib', runtime_lib/'libprotobuf.36.2.0.dylib'),
                          ('libz.1.dylib', runtime_lib/'libz.1.dylib')):
        (old_view/alias).symlink_to(target)
        (new_view/alias).symlink_to(target)
    (new_view/'libre2.11.dylib').symlink_to(runtime_lib/'libre2.11.0.0.dylib')
    launcher = root/'run-darwin-with-runtime.py'; launcher.write_text('# fixture SDK launcher input\n')
    old_runtime_inputs = sorted((str(launcher.resolve()), str((runtime_lib/'libprotobuf.36.2.0.dylib').resolve()),
                                 str((runtime_lib/'libz.1.dylib').resolve())))
    new_runtime_inputs = sorted(old_runtime_inputs + [str((runtime_lib/'libre2.11.0.0.dylib').resolve())])
    old_node_source = root/'node-old'; old_node_source.mkdir()
    old_node_receipt = old_node_source/'emberbsd-prepared-source.json'
    old_node_receipt.write_text('{"source":"old"}\n')
    new_node_source = root/'node-new'; new_node_source.mkdir()
    new_node_receipt = new_node_source/'emberbsd-prepared-source.json'
    new_node_receipt.write_text('{"source":"new"}\n')
    old = dict(emberbsd_node_provider_inputs=['old'], emberbsd_typescript_definitions=['old'],
               emberbsd_node_source_identity=str(old_node_receipt), node_module_version=130,
               emberbsd_node_configure_helper=str(root/'ports/scripts/source-inputs/node/configure-inputs.py'),
               emberbsd_node_configure_inputs=old_node_configure_inputs,
               emberbsd_node_configure_dependencies=old_node_configure_dependencies,
               feature=False, target_cpu='x64', clang_version='23',
               emberbsd_native_pkg_config_prefix=str(buildlink),
               emberbsd_protoc_runtime_launcher=str(launcher),
               emberbsd_protoc_runtime_view=str(old_view),
               emberbsd_protoc_runtime_inputs=old_runtime_inputs,
               node_host_runtime_python=str(host/'bin/python3.15'),
               node_host_runtime_launcher=str(launcher),
               node_host_runtime_view=str(old_view), node_host_runtime_inputs=old_runtime_inputs,
               perfetto_host_runtime_launcher=str(launcher),
               perfetto_host_runtime_view=str(old_view), perfetto_host_runtime_inputs=old_runtime_inputs)
    new = dict(emberbsd_node_provider_inputs=['new'], emberbsd_typescript_definitions=['new'], feature=True, target_cpu='x64', clang_version='23',
               emberbsd_native_pkg_config_prefix=str(buildlink),
               emberbsd_protoc_runtime_launcher=str(launcher),
               emberbsd_protoc_runtime_view=str(new_view),
               emberbsd_protoc_runtime_inputs=new_runtime_inputs,
               node_host_runtime_python=str(host/'bin/python3.15'),
               node_host_runtime_launcher=str(launcher),
               node_host_runtime_view=str(new_view), node_host_runtime_inputs=new_runtime_inputs,
               perfetto_host_runtime_launcher=str(launcher),
               perfetto_host_runtime_view=str(new_view), perfetto_host_runtime_inputs=new_runtime_inputs,
               node_module_version=130,
               v8_prepared_source_receipt='//v8/emberbsd-prepared-source.json',
               v8_version_hash_salt_files=[], v8_version_hash_salt='')
    new.update(emberbsd_node_source_identity=str(new_node_receipt.resolve(strict=True)),
               emberbsd_node_configure_helper=old['emberbsd_node_configure_helper'],
               emberbsd_node_configure_inputs=new_node_configure_inputs,
               emberbsd_node_configure_dependencies=new_node_configure_dependencies)
    env = {'PATH':str(host/'bin') + ':/usr/bin', 'EMBERBSD_HOST_TYPESCRIPT':'/old', 'EMBERBSD_HOST_NODE':'/old-node',
           'EMBERBSD_V8_SOURCE_SHA256':'a' * 64, 'EMBERBSD_NODE_SOURCE_SHA256':'a' * 64,
           'EMBERBSD_ELECTRON_NODE_ABI_HELPER_SHA256':'c' * 64,
           'EMBERBSD_ELECTRON_NODE_ABI_HEADER_SHA256':'d' * 64,
           'CC':str(work/'target-commands/cc'), 'CXX':str(work/'target-commands/cxx')}
    env.update(GOCACHE=str(work/'go-cache'), GOPATH=str(work/'go-path'))
    opt = SimpleNamespace(workspace=src.parent, ports_source=root, sdk_source=root, host_prefix=host,
                          host_runtime_root=native_runtime, target='amd64', compiler_family='clang',
                          work=work, git=Path('/usr/bin/git'))
    try: b.require_common_v8(opt); raise AssertionError('accepted missing common V8')
    except ValueError: pass
    opt.v8_source = Path(new_v8_root); opt.v8_ports_source = root/'owner'; opt.v8_pkgsrc = root/'pkgsrc'
    try: b.require_common_node(opt); raise AssertionError('accepted missing common Node')
    except ValueError: pass
    opt.node_source = new_node_source; opt.node_pkgsrc = root/'node-pkgsrc'
    assert new['emberbsd_node_source_identity'] == str(
        opt.node_source.resolve(strict=True)/'emberbsd-prepared-source.json')
    saved = dict(arguments=old, environment=env, source=str(src.parent), sdk=str(root), host_prefix=str(host), target='amd64')
    config = work/'configuration.json'; config.write_text(json.dumps(saved)); before = config.read_bytes()
    (out/'args.gn').write_text(b.gn_arguments(old)); (out/'build.ninja').write_text('old graph')
    obj=out/'retained.o'; obj.write_bytes(b'object')
    sdk=b.load_sdk(args.sdk_source); sdk['process']=Process()
    b.load_sdk=lambda _: sdk
    calls = {'verify':0, 'producer':0, 'gn_source':0, 'lastchange':0,
             'ffmpeg':0, 'dsymutil':0, 'rust_std':0}
    phase_order = []
    def verify_source(*_): calls['verify'] += 1
    def gn_source(_): calls['gn_source'] += 1; phase_order.append('source-view'); return src
    b.verify_source=verify_source
    b.gn_source=gn_source  # Composition is tested separately.
    def prerequisite(name):
        calls[name] += 1; phase_order.append(name)
    b.ensure_lastchange=lambda *args: prerequisite('lastchange')
    b.ensure_ffmpeg_netbsd_config=lambda *args: prerequisite('ffmpeg')
    b.ensure_host_dsymutil=lambda *args: prerequisite('dsymutil')
    b.require_rust_std=lambda *args: prerequisite('rust_std')
    local=b.local_module; b.local_module=lambda name, file: Source if file in ('prepare-build-sources.py', 'stage-runtime.py') else local(name,file)
    state={'commands':commands, 'values':new}
    def inputs(candidate, sdk):
        calls['producer'] += 1
        bound=b.bind_versioned(sdk, Native(), candidate.work/'target-commands', state['commands'])
        return Native(), {'PATH':state.get('path', Native.path), 'EMBERBSD_CONTROL_GIT':state.get('git', '/usr/bin/git'),
                          'EMBERBSD_HOST_TYPESCRIPT':'/new', 'EMBERBSD_HOST_NODE':str(host/'bin/node'),
                          'EMBERBSD_V8_SOURCE_SHA256':state.get('v8_sha', 'b' * 64),
                          'EMBERBSD_NODE_SOURCE_SHA256':state.get('node_sha', 'b' * 64),
                          'EMBERBSD_ELECTRON_NODE_ABI_HELPER_SHA256':state.get('node_abi_helper_sha', 'c' * 64),
                          'EMBERBSD_ELECTRON_NODE_ABI_HEADER_SHA256':state.get('node_abi_header_sha', 'd' * 64),
                          'GOCACHE':str(candidate.work/'go-cache'), 'GOPATH':str(candidate.work/'go-path'),
                          'CC':bound['cc'], 'CXX':bound['cxx'], **state.get('extra', {})}, state['values']
    b.producer_inputs=inputs
    opt.keep_going = -1
    for phase in (b.reconfigure, b.build):
        before_calls = dict(calls); before_process = (Process.calls, len(Process.ninja_calls))
        try: phase(opt); raise AssertionError('accepted negative programmatic keep-going')
        except ValueError as error: assert 'keep-going limit' in str(error)
        assert calls == before_calls and (Process.calls, len(Process.ninja_calls)) == before_process
        assert config.read_bytes() == before and (out/'args.gn').read_text() == b.gn_arguments(old)
        assert (out/'build.ninja').read_text() == 'old graph' and obj.read_bytes() == b'object'
        assert not (work/'reconfigure-incomplete').exists()
    del opt.keep_going
    state['path']=Native.path + ':/bin'
    try: b.reconfigure(opt); raise AssertionError('accepted external PATH')
    except ValueError as e: assert 'PATH is not prefix-only' in str(e)
    state.pop('path'); state['git']='/wrong/git'
    try: b.reconfigure(opt); raise AssertionError('accepted changed control Git')
    except ValueError as e: assert 'selected control Git changed' in str(e)
    state.pop('git'); state['extra']={'CCACHE_DIR':'/foreign'}
    try: b.reconfigure(opt); raise AssertionError('accepted unrelated environment change')
    except ValueError as e: assert 'producer input changed: CCACHE_DIR' in str(e)
    state.pop('extra'); saved['environment']['PATH'] = Native.path + ':/wrong'
    config.write_text(json.dumps(saved))
    try: b.reconfigure(opt); raise AssertionError('accepted unrelated old PATH')
    except ValueError as e: assert 'old build PATH' in str(e)
    config.write_bytes(before)
    with_identity = json.loads(before)
    with_identity['environment']['EMBERBSD_PROTOBUF_SOURCE_SHA256'] = 'old'
    config.write_text(json.dumps(with_identity))
    state['extra'] = {'EMBERBSD_PROTOBUF_SOURCE_SHA256': 'new'}
    try: b.reconfigure(opt); raise AssertionError('accepted changed common protobuf identity')
    except ValueError as e: assert 'producer input changed: EMBERBSD_PROTOBUF_SOURCE_SHA256' in str(e)
    state.pop('extra'); config.write_bytes(before)
    for invalid in (
        dict(new, v8_prepared_source_receipt='//custom/receipt.json'),
        dict(new, v8_version_hash_salt_files=['//electron/patches/v8/.patches']),
        dict(new, v8_version_hash_salt='custom-salt'),
        {key: value for key, value in new.items() if key != 'v8_prepared_source_receipt'},
    ):
        state['values'] = invalid
        try: b.reconfigure(opt); raise AssertionError('accepted noncanonical common V8 cache identity')
        except ValueError as e: assert 'verified common V8 receipt salt' in str(e)
        assert config.read_bytes()==before and (out/'build.ninja').read_text()=='old graph' and not (work/'reconfigure-incomplete').exists()
    state['values'] = new; state['v8_sha'] = 'invalid'
    try: b.reconfigure(opt); raise AssertionError('accepted invalid V8 source identity')
    except ValueError as e: assert 'verified common V8 source identities' in str(e)
    assert config.read_bytes()==before and not (work/'reconfigure-incomplete').exists()
    missing_old = json.loads(before); missing_old['environment'].pop('EMBERBSD_V8_SOURCE_SHA256')
    config.write_text(json.dumps(missing_old))
    state.pop('v8_sha')
    try: b.reconfigure(opt); raise AssertionError('accepted missing previous V8 source identity')
    except ValueError as e: assert 'verified common V8 source identities' in str(e)
    assert not (work/'reconfigure-incomplete').exists()
    config.write_bytes(before)
    state['extra'] = {'EMBERBSD_PROTOBUF_SOURCE_SHA256':'new'}
    try: b.reconfigure(opt); raise AssertionError('accepted V8 and unrelated provider changes together')
    except ValueError as e: assert 'producer input changed: EMBERBSD_PROTOBUF_SOURCE_SHA256' in str(e)
    state.pop('extra'); config.write_bytes(before)
    state['values'] = new; state['node_sha'] = 'invalid'
    try: b.reconfigure(opt); raise AssertionError('accepted malformed verified Node source identity')
    except ValueError as e: assert 'verified common Node source identities' in str(e)
    assert config.read_bytes()==before and not (work/'reconfigure-incomplete').exists()
    state.pop('node_sha')
    missing_node_hash = json.loads(before)
    missing_node_hash['environment'].pop('EMBERBSD_NODE_SOURCE_SHA256')
    config.write_text(json.dumps(missing_node_hash))
    try: b.reconfigure(opt); raise AssertionError('accepted missing previous Node source identity')
    except ValueError as e: assert 'verified common Node source identities' in str(e)
    config.write_bytes(before)
    state['values'] = dict(new, emberbsd_node_source_identity=str(root/'wrong/emberbsd-prepared-source.json'))
    try: b.reconfigure(opt); raise AssertionError('accepted wrong Node receipt path')
    except ValueError as e: assert 'verified common Node receipt' in str(e)
    state['values'] = dict(new, node_module_version=131)
    try: b.reconfigure(opt); raise AssertionError('accepted changed Node ABI version')
    except ValueError as e: assert 'GN identity changed: node_module_version' in str(e)
    state['values'] = new
    for field, state_key in (('EMBERBSD_ELECTRON_NODE_ABI_HELPER_SHA256', 'node_abi_helper_sha'),
                             ('EMBERBSD_ELECTRON_NODE_ABI_HEADER_SHA256', 'node_abi_header_sha')):
        state[state_key] = 'e' * 64
        try: b.reconfigure(opt); raise AssertionError('accepted changed Node ABI input hash: ' + field)
        except ValueError as e: assert 'producer input changed: ' + field in str(e)
        state.pop(state_key)
    malformed_old_node = json.loads(before)
    malformed_old_node['arguments']['emberbsd_node_source_identity'] = str(root/'old-node.json')
    config.write_text(json.dumps(malformed_old_node))
    (out/'args.gn').write_text(b.gn_arguments(malformed_old_node['arguments']))
    try: b.reconfigure(opt); raise AssertionError('accepted malformed saved Node receipt path')
    except ValueError as e: assert 'saved Node source identity' in str(e)
    config.write_bytes(before); (out/'args.gn').write_text(b.gn_arguments(old))
    assert old_node_configure_inputs != new_node_configure_inputs
    assert old_node_configure_dependencies != new_node_configure_dependencies
    assert old['emberbsd_node_source_identity'] != new['emberbsd_node_source_identity']
    assert new['emberbsd_node_source_identity'] == str(new_node_receipt.resolve())

    for changed_inputs, changed_dependencies, message in (
        ([row if not row.startswith('gyp-source=') else 'gyp-source='+str(root/'other-gyp')
          for row in new_node_configure_inputs], new_node_configure_dependencies,
         'Node configure inputs changed beyond the verified V8 source path'),
        ([row if not row.startswith('v8-selected-clang=') else 'v8-selected-clang='+str(root/'other-clang')
          for row in new_node_configure_inputs], new_node_configure_dependencies,
         'Node configure inputs changed beyond the verified V8 source path'),
        (new_node_configure_inputs,
         sorted(row.replace('gyp-source/emberbsd-prepared-source.json',
                            'other-gyp/emberbsd-prepared-source.json')
                for row in new_node_configure_dependencies),
         'Node configure dependencies changed beyond the verified V8 receipt path'),
        (new_node_configure_inputs + ['v8-source='+new_v8_root], new_node_configure_dependencies,
         'new Node configure inputs contains an invalid or duplicate key'),
        ([row for row in new_node_configure_inputs if not row.startswith('v8-source=')],
         new_node_configure_dependencies,
         'new Node configure inputs must contain exactly one absolute v8-source'),
    ):
        state['values'] = dict(new, emberbsd_node_configure_inputs=changed_inputs,
                               emberbsd_node_configure_dependencies=changed_dependencies)
        try: b.reconfigure(opt); raise AssertionError('accepted a non-V8 Node configure identity change')
        except ValueError as e: assert message in str(e)
        assert config.read_bytes()==before and (out/'build.ninja').read_text()=='old graph'
        assert not (work/'reconfigure-incomplete').exists()

    state['values'] = new
    def reject_runtime_view(candidate, message):
        state['values'] = candidate
        try: b.reconfigure(opt); raise AssertionError('accepted invalid runtime view extension')
        except ValueError as error: assert message in str(error), str(error)
        assert config.read_bytes()==before and (out/'build.ninja').read_text()=='old graph'
        assert (out/'args.gn').read_text()==b.gn_arguments(old) and obj.read_bytes()==b'object'
        assert not (work/'reconfigure-incomplete').exists()
        state['values'] = new

    removed_alias = new_view/'libz.1.dylib'; removed_alias.unlink()
    reject_runtime_view(new, 'removed an existing alias')
    removed_alias.symlink_to(runtime_lib/'libz.1.dylib')

    replaced_alias = new_view/'libz.1.dylib'; replaced_alias.unlink()
    replaced_alias.symlink_to(runtime_lib/'libother.dylib')
    reject_runtime_view(new, 'changed an existing alias')
    replaced_alias.unlink(); replaced_alias.symlink_to(runtime_lib/'libz.1.dylib')

    foreign_alias = new_view/'libforeign.dylib'; foreign_alias.symlink_to(foreign_lib/'libforeign.dylib')
    reject_runtime_view(new, 'outside selected host runtime')
    foreign_alias.unlink()

    selected_re2 = buildlink_lib/'libre2.11.dylib'
    selected_re2.unlink(); selected_re2.symlink_to(runtime_lib/'libother.dylib')
    reject_runtime_view(new, 'does not match selected buildlink provider')
    selected_re2.unlink(); selected_re2.symlink_to(runtime_lib/'libre2.11.0.0.dylib')

    reject_runtime_view(dict(new, emberbsd_protoc_runtime_launcher=str(root/'different-launcher.py')),
                        'launcher changed')
    reject_runtime_view(dict(new, emberbsd_protoc_runtime_inputs=new_runtime_inputs +
                             [str(root/'unselected-input.dylib')]),
                        'changed beyond added view targets')
    reject_runtime_view(dict(new, node_host_runtime_inputs=old_runtime_inputs),
                        'node_host_runtime runtime selection changed independently')
    reject_runtime_view(dict(new, perfetto_host_runtime_view=str(old_view)),
                        'perfetto_host_runtime runtime selection changed independently')

    for malformed_old_inputs, message in (
        (old_node_configure_inputs + ['v8-source='+old_v8_root],
         'saved Node configure inputs contains an invalid or duplicate key'),
        ([row for row in old_node_configure_inputs if not row.startswith('v8-source=')],
         'saved Node configure inputs must contain exactly one absolute v8-source'),
    ):
        malformed_saved = json.loads(before)
        malformed_saved['arguments']['emberbsd_node_configure_inputs'] = malformed_old_inputs
        config.write_text(json.dumps(malformed_saved))
        malformed_gn = b.gn_arguments(malformed_saved['arguments'])
        (out/'args.gn').write_text(malformed_gn)
        try: b.reconfigure(opt); raise AssertionError('accepted malformed saved V8 path identity')
        except ValueError as e: assert message in str(e)
        assert config.read_text()==json.dumps(malformed_saved)
        assert (out/'args.gn').read_text()==malformed_gn and not (work/'reconfigure-incomplete').exists()
        config.write_bytes(before)
        (out/'args.gn').write_text(b.gn_arguments(old))

    try: b.selected_control_git(root/'missing-git'); raise AssertionError('accepted missing Git')
    except FileNotFoundError: pass
    nonexec=root/'not-executable'; nonexec.write_text('file')
    try: b.selected_control_git(nonexec); raise AssertionError('accepted non-executable Git')
    except ValueError as e: assert 'not executable' in str(e)
    opt.target='aarch64'
    try: b.reconfigure(opt); raise AssertionError('accepted changed target')
    except ValueError as e: assert 'inputs differ' in str(e)
    opt.target='amd64'; opt.compiler_family='gcc'
    try: b.reconfigure(opt); raise AssertionError('accepted changed compiler family')
    except ValueError as e: assert 'Clang bindings' in str(e)
    opt.compiler_family='clang'; state['commands']=json.loads(json.dumps(commands))
    state['commands']['commands']['cc'][2]='--sysroot=/other'
    try: b.reconfigure(opt); raise AssertionError('accepted changed compiler')
    except ValueError as e: assert 'compiler, sysroot or runtime' in str(e)
    assert config.read_bytes()==before and (out/'build.ninja').read_text()=='old graph' and not (work/'reconfigure-incomplete').exists()
    state['commands']=commands
    state['values']=dict(new, target_cpu='arm64')
    try: b.reconfigure(opt); raise AssertionError('accepted changed target CPU')
    except ValueError as e: assert 'GN identity changed: target_cpu' in str(e)
    assert config.read_bytes()==before and not (work/'reconfigure-incomplete').exists()
    state['values']=dict(new, clang_version='24')
    try: b.reconfigure(opt); raise AssertionError('accepted changed Clang resource version')
    except ValueError as e: assert 'GN identity changed: clang_version' in str(e)
    assert config.read_bytes()==before and not (work/'reconfigure-incomplete').exists()
    state['values']=dict(new, unbundle_linker_launcher='different')
    try: b.reconfigure(opt); raise AssertionError('accepted changed linker launcher')
    except ValueError as e: assert 'GN identity changed: unbundle_linker_launcher' in str(e)
    assert config.read_bytes()==before and not (work/'reconfigure-incomplete').exists()
    state['values']=new; gnfile.write_text('not valid GN\n')
    try: b.reconfigure(opt); raise AssertionError('accepted invalid GN')
    except RuntimeError: pass
    assert (work/'reconfigure-incomplete').exists() and config.read_bytes()==before and (out/'args.gn').read_text()==b.gn_arguments(old)
    try: b.build(opt); raise AssertionError('accepted incomplete graph')
    except ValueError as e: assert 'incomplete reconfiguration' in str(e)
    gnfile.write_text('group("electron_dist_zip") {}\n'); b.reconfigure(opt)
    assert not (work/'reconfigure-incomplete').exists() and json.loads(config.read_text())['arguments']==new
    saved_after = json.loads(config.read_text())
    assert saved_after['environment']['EMBERBSD_HOST_TYPESCRIPT']=='/new'
    assert saved_after['environment']['EMBERBSD_V8_SOURCE_SHA256']=='b' * 64
    assert saved_after['environment']['EMBERBSD_NODE_SOURCE_SHA256']=='b' * 64
    assert saved_after['arguments']['emberbsd_node_source_identity']==str(new_node_receipt.resolve())
    assert saved_after['arguments']['node_module_version']==130
    assert saved_after['arguments']['emberbsd_node_configure_inputs']==new_node_configure_inputs
    assert saved_after['arguments']['emberbsd_node_configure_dependencies']==new_node_configure_dependencies
    gn_args = (out/'args.gn').read_text()
    assert 'v8_prepared_source_receipt = "//v8/emberbsd-prepared-source.json"\n' in gn_args
    assert 'v8_version_hash_salt_files = [  ]\n' in gn_args and 'v8_version_hash_salt = ""\n' in gn_args
    assert (out/'build.ninja').read_text()!='old graph' and obj.read_bytes()==b'object' and json.loads(binding.read_text())==commands
    log = work/'reconfigure.log'
    assert 'fixture GN invocation 1' in log.read_text() and 'fixture GN invocation 2' in log.read_text()
    first_log = log.read_text()
    b.reconfigure(opt)  # Already migrated configurations are reusable.
    second_log = log.read_text()
    assert second_log.startswith(first_log) and 'fixture GN invocation 3' in second_log
    gnfile.write_text('not valid GN\n')
    try: b.reconfigure(opt); raise AssertionError('accepted invalid GN on reconfigure retry path')
    except RuntimeError: pass
    failed_log = log.read_text()
    assert failed_log.startswith(second_log) and 'fixture GN invocation 4' in failed_log
    gnfile.write_text('group("electron_dist_zip") {}\n'); b.reconfigure(opt)
    recovered_log = log.read_text()
    assert recovered_log.startswith(failed_log) and 'fixture GN invocation 5' in recovered_log
    assert not (work/'reconfigure-incomplete').exists() and obj.read_bytes()==b'object'
    assert not Process.ninja_calls, 'ordinary reconfigure must not invoke Ninja'

    opt.build_after_reconfigure = True; opt.jobs = 0
    calls.update(verify=0, producer=0, gn_source=0, lastchange=0, ffmpeg=0, dsymutil=0, rust_std=0)
    phase_order.clear()
    saved_before_bad_jobs = config.read_bytes(); prior_gn_count = Process.calls
    try: b.reconfigure(opt); raise AssertionError('accepted nonpositive combined jobs')
    except ValueError as e: assert 'Ninja job count must be positive' in str(e)
    assert config.read_bytes()==saved_before_bad_jobs and not (work/'reconfigure-incomplete').exists()
    assert Process.calls==prior_gn_count and not any(calls.values())
    opt.jobs = 16
    prior_ninja_count = len(Process.ninja_calls)
    prior_gn_count = Process.calls
    state['v8_sha'] = 'd' * 64
    gnfile.write_text('not valid GN\n')
    saved_before_failure = config.read_bytes()
    try: b.reconfigure(opt); raise AssertionError('accepted combined GN failure')
    except RuntimeError: pass
    assert len(Process.ninja_calls)==prior_ninja_count and Process.calls==prior_gn_count+1
    assert Process.events[-1]=='gn' and config.read_bytes()==saved_before_failure
    assert (out/'args.gn').read_text()==b.gn_arguments(new)
    assert (work/'reconfigure-incomplete').exists()
    assert calls == {'verify':1, 'producer':1, 'gn_source':1, 'lastchange':1,
                     'ffmpeg':1, 'dsymutil':1, 'rust_std':1}
    assert phase_order == ['lastchange', 'ffmpeg', 'dsymutil', 'rust_std', 'source-view']

    gnfile.write_text('group("electron_dist_zip") {}\n')
    state['v8_sha'] = 'e' * 64
    Process.ninja_failure = False
    calls.update(verify=0, producer=0, gn_source=0, lastchange=0, ffmpeg=0, dsymutil=0, rust_std=0)
    phase_order.clear()
    prior_gn_count = Process.calls
    b.reconfigure(opt)
    assert Process.calls==prior_gn_count+1 and Process.events[-2:]==['gn', 'ninja']
    assert len(Process.ninja_calls)==prior_ninja_count+1
    assert Process.ninja_calls[-1][Process.ninja_calls[-1].index('-j') + 1]=='16'
    assert Process.ninja_calls[-1][Process.ninja_calls[-1].index('-k') + 1]=='1'
    assert not (work/'reconfigure-incomplete').exists()
    assert json.loads(config.read_text())['environment']['EMBERBSD_V8_SOURCE_SHA256']=='e' * 64
    assert obj.read_bytes()==b'object' and len(Source.stage_calls)==1
    assert calls == {'verify':1, 'producer':1, 'gn_source':1, 'lastchange':1,
                     'ffmpeg':1, 'dsymutil':1, 'rust_std':1}
    assert phase_order == ['lastchange', 'ffmpeg', 'dsymutil', 'rust_std', 'source-view']

    state['v8_sha'] = 'f' * 64
    opt.keep_going = 0
    Process.ninja_failure = True
    calls.update(verify=0, producer=0, gn_source=0, lastchange=0, ffmpeg=0, dsymutil=0, rust_std=0)
    phase_order.clear()
    prior_gn_count = Process.calls
    prior_ninja_count = len(Process.ninja_calls)
    try: b.reconfigure(opt); raise AssertionError('accepted fixture Ninja failure')
    except RuntimeError as error: assert 'fixture Ninja failure' in str(error)
    assert Process.calls==prior_gn_count+1 and Process.events[-2:]==['gn', 'ninja']
    assert len(Process.ninja_calls)==prior_ninja_count+1
    assert Process.ninja_calls[-1][Process.ninja_calls[-1].index('-j') + 1]=='16'
    assert Process.ninja_calls[-1][Process.ninja_calls[-1].index('-k') + 1]=='0'
    assert not (work/'reconfigure-incomplete').exists()
    assert (out/'build.ninja').is_file() and (out/'args.gn').read_text()==b.gn_arguments(new)
    assert json.loads(config.read_text())['environment']['EMBERBSD_V8_SOURCE_SHA256']=='f' * 64
    assert obj.read_bytes()==b'object' and len(Source.stage_calls)==1
    assert calls == {'verify':1, 'producer':1, 'gn_source':1, 'lastchange':1,
                     'ffmpeg':1, 'dsymutil':1, 'rust_std':1}
    assert phase_order == ['lastchange', 'ffmpeg', 'dsymutil', 'rust_std', 'source-view']

    # A separate ordinary build keeps its own verification/prerequisite path.
    Process.ninja_failure = False
    calls.update(verify=0, producer=0, gn_source=0, lastchange=0, ffmpeg=0, dsymutil=0, rust_std=0)
    phase_order.clear()
    b.build(opt)
    assert Process.events[-1]=='ninja' and len(Process.ninja_calls)==prior_ninja_count+2
    assert Process.ninja_calls[-1][Process.ninja_calls[-1].index('-j') + 1]=='16'
    assert calls == {'verify':1, 'producer':1, 'gn_source':1, 'lastchange':1,
                     'ffmpeg':1, 'dsymutil':1, 'rust_std':1}
    assert phase_order == ['lastchange', 'ffmpeg', 'dsymutil', 'rust_std', 'source-view']
    assert obj.read_bytes()==b'object' and len(Source.stage_calls)==2

    # Isolate a common Node receipt refresh from V8, runtime-view and provider changes.
    node_refresh_source = root/'node-refresh'; node_refresh_source.mkdir()
    node_refresh_receipt = node_refresh_source/'emberbsd-prepared-source.json'
    node_refresh_receipt.write_text('{"source":"refreshed"}\n')
    opt.build_after_reconfigure = False
    opt.node_source = node_refresh_source
    state['values'] = dict(new, emberbsd_node_source_identity=str(node_refresh_receipt.resolve(strict=True)))
    state['node_sha'] = 'e' * 64
    calls.update(verify=0, producer=0, gn_source=0, lastchange=0, ffmpeg=0, dsymutil=0, rust_std=0)
    phase_order.clear()
    prior_gn_count = Process.calls
    b.reconfigure(opt)
    refreshed = json.loads(config.read_text())
    assert Process.calls==prior_gn_count+1 and Process.events[-1]=='gn'
    assert refreshed['environment']['EMBERBSD_NODE_SOURCE_SHA256']=='e' * 64
    assert refreshed['environment']['EMBERBSD_V8_SOURCE_SHA256']=='f' * 64
    assert refreshed['arguments']['emberbsd_node_source_identity']==str(node_refresh_receipt.resolve())
    assert refreshed['arguments']['node_module_version']==130
    assert obj.read_bytes()==b'object' and not (work/'reconfigure-incomplete').exists()
    print('real GN reconfigure, combined Ninja, standalone build, failure recovery and object preservation passed')
