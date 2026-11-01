#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Run reconfigure/build orchestration against real GN and bounded fixtures."""
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
    (src/'BUILDCONFIG.gn').write_text('declare_args() {\n emberbsd_node_provider_inputs=[]\n emberbsd_typescript_definitions=[]\n v8_prepared_source_receipt=""\n v8_version_hash_salt_files=[]\n v8_version_hash_salt=""\n feature=false\n clang_version=""\n}\nset_default_toolchain("//:tools")\n')
    (src/'BUILD.gn').write_text('toolchain("tools") {\n tool("stamp") { command="touch {{output}}" }\n}\n')
    (src/'electron/build/args').mkdir(parents=True)
    (src/'electron/build/args/release.gn').write_text('')
    gnfile = src/'electron/BUILD.gn'; gnfile.write_text('group("electron_dist_zip") {}\n')
    old = dict(emberbsd_node_provider_inputs=['old'], emberbsd_typescript_definitions=['old'], feature=False, target_cpu='x64', clang_version='23')
    new = dict(emberbsd_node_provider_inputs=['new'], emberbsd_typescript_definitions=['new'], feature=True, target_cpu='x64', clang_version='23',
               v8_prepared_source_receipt='//v8/emberbsd-prepared-source.json',
               v8_version_hash_salt_files=[], v8_version_hash_salt='')
    env = {'PATH':str(host/'bin') + ':/usr/bin', 'EMBERBSD_HOST_TYPESCRIPT':'/old', 'EMBERBSD_HOST_NODE':'/old-node',
           'EMBERBSD_V8_SOURCE_SHA256':'a' * 64, 'CC':str(work/'target-commands/cc'), 'CXX':str(work/'target-commands/cxx')}
    env.update(GOCACHE=str(work/'go-cache'), GOPATH=str(work/'go-path'))
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
                          'GOCACHE':str(candidate.work/'go-cache'), 'GOPATH':str(candidate.work/'go-path'),
                          'CC':bound['cc'], 'CXX':bound['cxx'], **state.get('extra', {})}, state['values']
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
    assert not (work/'reconfigure-incomplete').exists()
    assert json.loads(config.read_text())['environment']['EMBERBSD_V8_SOURCE_SHA256']=='e' * 64
    assert obj.read_bytes()==b'object' and len(Source.stage_calls)==1
    assert calls == {'verify':1, 'producer':1, 'gn_source':1, 'lastchange':1,
                     'ffmpeg':1, 'dsymutil':1, 'rust_std':1}
    assert phase_order == ['lastchange', 'ffmpeg', 'dsymutil', 'rust_std', 'source-view']

    state['v8_sha'] = 'f' * 64
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
    assert not (work/'reconfigure-incomplete').exists()
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
    print('real GN reconfigure, combined Ninja, standalone build, failure recovery and object preservation passed')
