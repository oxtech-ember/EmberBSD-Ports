#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Run reconfigure against real GN; fake only producer selection and SDK I/O."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace

p = argparse.ArgumentParser()
p.add_argument('--host-prefix', type=Path, required=True)
p.add_argument('--sdk-source', type=Path, required=True)
args = p.parse_args(); host = args.host_prefix
owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / 'electron44/files/build-electron.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
class Native:
    path = str(host / 'bin')
    def tool(self, name):
        return str(host / 'bin' / ('python3.15' if name == 'python' else name))
class Process:
    @staticmethod
    def run_logged(argv, log, **kwargs):
        r = subprocess.run(argv, cwd=kwargs['cwd'], env=kwargs['env'], capture_output=True, text=True)
        Path(log).write_text(r.stdout + r.stderr)
        if r.returncode: raise RuntimeError(r.stdout + r.stderr)
class Source:
    @staticmethod
    def atomic_json(path, value):
        tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(value)); tmp.replace(path)
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
    (src/'BUILDCONFIG.gn').write_text('declare_args() {\n emberbsd_node_provider_inputs=[]\n emberbsd_typescript_definitions=[]\n feature=false\n clang_version=""\n}\nset_default_toolchain("//:tools")\n')
    (src/'BUILD.gn').write_text('toolchain("tools") {\n tool("stamp") { command="touch {{output}}" }\n}\n')
    (src/'electron/build/args').mkdir(parents=True)
    (src/'electron/build/args/release.gn').write_text('')
    gnfile = src/'electron/BUILD.gn'; gnfile.write_text('group("electron_dist_zip") {}\n')
    old = dict(emberbsd_node_provider_inputs=['old'], emberbsd_typescript_definitions=['old'], feature=False, target_cpu='x64', clang_version='23')
    new = dict(emberbsd_node_provider_inputs=['new'], emberbsd_typescript_definitions=['new'], feature=True, target_cpu='x64', clang_version='23')
    env = {'PATH':str(host/'bin') + ':/usr/bin', 'EMBERBSD_HOST_TYPESCRIPT':'/old', 'EMBERBSD_HOST_NODE':'/old-node', 'CC':str(work/'target-commands/cc'), 'CXX':str(work/'target-commands/cxx')}
    opt = SimpleNamespace(workspace=src.parent, ports_source=root, sdk_source=root, host_prefix=host, target='amd64', compiler_family='clang', work=work, git=Path('/usr/bin/git'))
    try: b.require_common_v8(opt); raise AssertionError('accepted missing common V8')
    except ValueError: pass
    opt.v8_source = root/'v8'; opt.v8_ports_source = root/'owner'; opt.v8_pkgsrc = root/'pkgsrc'
    try: b.require_common_node(opt); raise AssertionError('accepted missing common Node')
    except ValueError: pass
    opt.node_source = root/'node'; opt.node_pkgsrc = root/'node-pkgsrc'
    saved = dict(arguments=old, environment=env, source=str(src.parent), sdk=str(root), host_prefix=str(host), target='amd64')
    config = work/'configuration.json'; config.write_text(json.dumps(saved)); before = config.read_bytes()
    (out/'args.gn').write_text(b.gn_arguments(old)); (out/'build.ninja').write_text('old graph')
    obj=out/'retained.o'; obj.write_bytes(b'object')
    sdk=b.load_sdk(args.sdk_source); sdk['process']=Process()
    b.load_sdk=lambda _: sdk; b.verify_source=lambda *args: None
    b.gn_source=lambda _: src  # Composition is tested separately.
    local=b.local_module; b.local_module=lambda name, file: Source if file == 'prepare-build-sources.py' else local(name,file)
    state={'commands':commands, 'values':new}
    def inputs(candidate, sdk):
        bound=b.bind_versioned(sdk, Native(), candidate.work/'target-commands', state['commands'])
        return Native(), {'PATH':state.get('path', Native.path), 'EMBERBSD_CONTROL_GIT':state.get('git', '/usr/bin/git'), 'EMBERBSD_HOST_TYPESCRIPT':'/new', 'EMBERBSD_HOST_NODE':str(host/'bin/node'), 'CC':bound['cc'], 'CXX':bound['cxx'], **state.get('extra', {})}, state['values']
    b.producer_inputs=inputs
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
    assert json.loads(config.read_text())['environment']['EMBERBSD_HOST_TYPESCRIPT']=='/new'
    assert (out/'build.ninja').read_text()!='old graph' and obj.read_bytes()==b'object' and json.loads(binding.read_text())==commands
    b.reconfigure(opt)  # Already migrated configurations are reusable.
    assert not (work/'reconfigure-incomplete').exists() and obj.read_bytes()==b'object'
    print('real GN success, failure/recovery, input mismatch and object preservation passed')
