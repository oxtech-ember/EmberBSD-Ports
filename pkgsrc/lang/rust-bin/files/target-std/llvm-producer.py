#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Build a Rust target std with the selected common Clang/LLVM runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

p = argparse.ArgumentParser()
for name in ('source', 'work', 'host-prefix', 'compiler-prefix', 'sysroot', 'sdk-source', 'macos-sdk', 'lock-root', 'link-context'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--target', choices=('amd64', 'aarch64', 'wasm32-wasip1'), required=True)
p.add_argument('--macos-minimum', required=True)
p.add_argument('--jobs', type=int, required=True)
p.add_argument('--plan', action='store_true', help='check the bootstrap plan without building target std')
a = p.parse_args()
if a.jobs < 1: p.error('jobs must be positive')
if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,2}', a.macos_minimum):
    p.error('macOS deployment version must be numeric')
for name in ('source','work','host_prefix','compiler_prefix','sysroot','sdk_source','macos_sdk','lock_root','link_context'):
    path = getattr(a, name)
    if not path.is_absolute(): p.error(name + ' must be absolute')
    setattr(a, name, path.resolve(strict=True))
for out in (a.source, a.work):
    for provider in (a.host_prefix, a.compiler_prefix, a.sysroot, a.sdk_source):
        if out.is_relative_to(provider) or provider.is_relative_to(out):
            p.error('work/source overlaps an input provider')
sys.path.insert(0, str(a.sdk_source/'src'))
import emberbsd_sdk
from emberbsd_sdk import application_toolchain, compiler_bindings, host_prefix, process, target_toolchain, targets
modules = (emberbsd_sdk, application_toolchain, compiler_bindings, host_prefix, process, target_toolchain, targets)
if emberbsd_sdk.API_VERSION != 1 or application_toolchain.APPLICATION_TOOLCHAIN_API != 2 or compiler_bindings.COMPILER_BINDINGS_API not in (2, 3):
    raise ValueError('incompatible selected SDK API')
if any(not Path(module.__file__).resolve().is_relative_to(a.sdk_source/'src/emberbsd_sdk') for module in modules):
    raise ValueError('SDK module origin differs from the selected source')
native = host_prefix.load_host_prefix(a.host_prefix, required_roles=('python','rustc','cargo','cc','cxx','cpp','ar','sh','readelf'), compiler_family='clang')
if Path(sys.executable).resolve() != Path(native.tool('python')).resolve(): p.error('use selected native Python')
if native.host['os'] != 'Darwin': p.error('this producer currently supports Darwin hosts')
env = process.sanitized_environment()
(a.work/'tmp').mkdir(exist_ok=True); (a.work/'cargo-home').mkdir(exist_ok=True)
env.update(PATH=native.path, CARGO_NET_OFFLINE='true', CARGO_HOME=str(a.work/'cargo-home'),
           TMPDIR=str(a.work/'tmp'),
           PYTHONDONTWRITEBYTECODE='1')
for name in ('RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','CARGO_BUILD_TARGET','RUSTC_BOOTSTRAP',
             'RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_TARGET_DIR',
             'DYLD_LIBRARY_PATH','DYLD_FRAMEWORK_PATH','DYLD_INSERT_LIBRARIES'):
    env.pop(name, None)
def capture(args):
    return subprocess.run([str(x) for x in args], env=env, text=True, capture_output=True, check=True).stdout
version = capture([native.tool('rustc'), '-vV'])
if 'commit-hash: 58cf8f9c35b355199727627d07ae34a4e2846d67\n' not in version:
    raise ValueError('selected Rust compiler is not the pinned 1.99.1 commit')
host = next(line[6:] for line in version.splitlines() if line.startswith('host: '))
if host not in ('aarch64-apple-darwin','x86_64-apple-darwin'):
    raise ValueError('unsupported Rust build host')
expected_host = {'arm64':'aarch64-apple-darwin', 'aarch64':'aarch64-apple-darwin',
                 'x86_64':'x86_64-apple-darwin', 'amd64':'x86_64-apple-darwin'}.get(native.host['cpu'])
if host != expected_host: raise ValueError('Rust compiler host differs from selected native CPU')
triplet = {'amd64':'x86_64-unknown-netbsd','aarch64':'aarch64-unknown-netbsd', 'wasm32-wasip1':'wasm32-wasip1'}[a.target]
if a.target == 'wasm32-wasip1':
    if a.compiler_prefix != a.host_prefix: p.error('WASI compiler must be the selected native prefix')
    wasm_ld = (a.host_prefix / 'bin/wasm-ld').resolve(strict=True)
    if not wasm_ld.is_relative_to(a.host_prefix) or not wasm_ld.is_file():
        p.error('selected wasm linker must belong to the native prefix')
    resource = Path(capture([native.tool('cc'), '-print-resource-dir']).strip()).resolve(strict=True)
    if not resource.is_relative_to(a.host_prefix) or not (resource / 'lib/wasm32-unknown-wasip1/libclang_rt.builtins.a').is_file():
        p.error('selected WASI compiler-rt builtins are missing')
    if a.sysroot != (a.host_prefix / 'wasi').resolve(strict=True):
        p.error('WASI target requires the selected host prefix wasi-libc sysroot')
    for item in ('lib/wasm32-wasip1/libc.a', 'lib/wasm32-wasip1/crt1-command.o',
                 'lib/wasm32-wasip1/crt1-reactor.o', 'include/wasm32-wasip1/stdlib.h'):
        if not (a.sysroot / item).is_file(): p.error('missing WASI libc input: ' + item)
    wasm_flags = ['--target=wasm32-wasip1', '--sysroot=' + str(a.sysroot)]
    target = compiler_bindings.bind_compilers(a.work/'target-commands',
        commands={role:[native.tool(role), *wasm_flags] for role in ('cc','cxx','cpp')},
        flags={name:[] for name in ('cppflags','cflags','cxxflags','ldflags')},
        python=native.tool('python'),
        link_flags={role:['--ld-path='+str(wasm_ld)] for role in ('cc','cxx')})
else:
    definition = targets.target_definition(a.target)
    compiler = target_toolchain.clang_compiler(str(a.compiler_prefix), definition['triplet'], host=native.host, env=env)
    runtime = application_toolchain.load_clang_runtime(str(a.sysroot), target=a.target)
    target = application_toolchain.bind_clang_application_commands(a.work/'target-commands', compiler, str(a.sysroot), runtime, python=native.tool('python'))
env.update(SDKROOT=str(a.macos_sdk), MACOSX_DEPLOYMENT_TARGET=a.macos_minimum)
flags = ['-isysroot',str(a.macos_sdk),'-mmacosx-version-min='+a.macos_minimum]
commands = {role:[native.tool(role),*flags] for role in ('cc','cxx','cpp')}
common_flags = {name:[] for name in ('cppflags','cflags','cxxflags','ldflags')}
host_tools = compiler_bindings.bind_compilers(a.work/'host-commands', commands=commands, flags=common_flags,
    python=native.tool('python'), link_flags={role:['--ld-path='+native.tool('ld')] for role in ('cc','cxx')})
def linker_binding(name, compiler_path):
    command = [native.tool('python'), str(a.sdk_source/'scripts/link-launcher.py'),
               '--lock-root', str(a.lock_root), '--context', str(a.link_context), '--', compiler_path]
    identity = json.dumps(command, separators=(',', ':')).encode() + Path(compiler_bindings.__file__).read_bytes()
    directory = a.work/name
    directory.mkdir(exist_ok=True)
    return compiler_bindings.bind_compilers(directory/hashlib.sha256(identity).hexdigest(),
        commands={role:command for role in ('cc','cxx','cpp')}, flags=common_flags,
        python=native.tool('python'))['cc']
target_linker = linker_binding('target-linker', str(wasm_ld) if a.target == 'wasm32-wasip1' else target['cc'])
host_linker = linker_binding('host-linker', host_tools['cc'])
env.update(CC=host_tools['cc'], CXX=host_tools['cxx'], AR=native.tool('ar'))
env['CARGO_TARGET_'+host.upper().replace('-', '_')+'_LINKER'] = host_linker
def q(value): return json.dumps(str(value))
config = f'''change-id = "ignore"
[build]
build = {q(host)}
host = [{q(host)}]
target = [{q(triplet)}]
rustc = {q(native.tool('rustc'))}
cargo = {q(native.tool('cargo'))}
local-rebuild = true
locked-deps = true
vendor = true
extended = false
jobs = {a.jobs}
build-dir = {q(a.work/'out')}
[llvm]
download-ci-llvm = false
[rust]
channel = "stable"
download-rustc = false
remap-debuginfo = true
[target.{triplet}]
cc = {q(target['cc'])}
cxx = {q(target['cxx'])}
ar = {q(native.tool('ar'))}
linker = {q(target_linker)}
{("wasi-root = " + q(a.sysroot)) if a.target == "wasm32-wasip1" else 'llvm-libunwind = "system"'}
[target.{host}]
cc = {q(host_tools['cc'])}
cxx = {q(host_tools['cxx'])}
ar = {q(native.tool('ar'))}
linker = {q(host_linker)}
'''
(a.source/'bootstrap.toml').write_text(config)
command = [native.tool('python'),str(a.source/'x.py'),'build','library','--stage','0','--target',triplet,'-j'+str(a.jobs)]
plan = subprocess.run([*command,'--dry-run'],cwd=a.source,env=env,text=True,capture_output=True)
(a.work/'std-plan.log').write_text(plan.stdout + plan.stderr)
if plan.returncode:
    raise RuntimeError('Rust bootstrap plan failed; inspect '+str(a.work/'std-plan.log'))
if 'Building stage0 library artifacts' not in plan.stdout+plan.stderr or any(
        name in plan.stdout+plan.stderr for name in ('Building stage1','Building LLVM','Building LLD','Building stage0 compiler')):
    raise RuntimeError('unexpected Rust bootstrap build plan')
if a.plan:
    print('Rust stage0 target std plan accepted for', triplet)
    sys.exit(0)
subprocess.run(command, cwd=a.source, env=env, check=True)
print('Rust std producer completed for',triplet)
# Link with the newly built target std; this does not execute the target.
stage = a.work/'out'/host/'stage0-sysroot'
component = stage/'lib/rustlib'/triplet/'lib'
expected = ('libstd-*.rlib','libcore-*.rlib','liballoc-*.rlib','libpanic_abort-*.rlib') if a.target == 'wasm32-wasip1' else ('libstd-*.rlib','libcore-*.rlib','liballoc-*.rlib','libpanic_unwind-*.rlib','libstd-*.so')
for name in expected:
    if len(list(component.glob(name))) != 1: raise RuntimeError('missing or duplicate Rust component: '+name)
probe = a.work/'std-consumer.rs'
probe.write_text('fn main() { println!("{}", std::env::args().count()); }\n')
consumer = a.work/'std-consumer'
subprocess.run([native.tool('rustc'),'--target',triplet,'--sysroot',str(stage),'-C','linker='+target_linker,
                '-C','default-linker-libraries',str(probe),'-o',str(consumer)],env=env,check=True)
if a.target == 'wasm32-wasip1':
    if consumer.read_bytes()[:4] != b'\0asm': raise RuntimeError('Rust output is not WebAssembly')
    print('Rust WASI preview1 std and consumer link passed; target execution not tested')
    sys.exit(0)
readelf = native.tool('readelf')
for path in (consumer, next(component.glob('libstd-*.so'))):
    header = capture([readelf,'-h',path])
    machine = {'amd64':'Advanced Micro Devices X86-64', 'aarch64':'AArch64'}[a.target]
    if 'ELF64' not in header or machine not in header:
        raise RuntimeError('Rust output has the wrong target ELF: '+str(path))
    dynamic = capture([readelf,'-d',path])
    if 'libgcc_s' in dynamic or 'libunwind.so' not in dynamic:
        raise RuntimeError('Rust output does not select only the LLVM unwinder: '+str(path))
    (a.work/(path.name+'.dynamic.txt')).write_text(dynamic)
print('Rust target std and static-std consumer link against LLVM libunwind; target execution not tested')
