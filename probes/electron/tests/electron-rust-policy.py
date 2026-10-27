#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check Chromium's explicit stable-Rust unstable policy with GN and rustc."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'work', 'git', 'gn', 'rustc', 'bindgen', 'host-prefix', 'macos-sdk', 'utility-path'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    source, work, prefix = Path(args.source), Path(args.work), Path(args.host_prefix)
    assert source.is_absolute() and work.is_absolute() and not work.exists() and not work.is_relative_to(source)
    work.mkdir(parents=True)
    env = dict(PATH=args.utility_path, LC_ALL='C', PYTHONDONTWRITEBYTECODE='1',
               SDKROOT=args.macos_sdk, LIBCLANG_PATH=str(prefix / 'lib'),
               CLANG_PATH=str(prefix / 'bin/clang'), RUSTFMT=str(prefix / 'bin/rustfmt'))
    commands = []
    def run(label, argv, *, cwd=work, environment=env, error=None):
        result = subprocess.run(list(map(str, argv)), cwd=cwd, env=environment, capture_output=True, text=True)
        output = result.stdout + result.stderr
        (work / (label + '.log')).write_text(output)
        commands.append(dict(label=label, argv=list(map(str, argv)), status=result.returncode,
                             rustc_bootstrap=environment.get('RUSTC_BOOTSTRAP')))
        assert (result.returncode == 0 if error is None else result.returncode != 0 and error in output), label + ': ' + output
        return result.stdout
    owner = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('rust_policy', owner / 'electron44/files/rust-policy.py')
    policy = importlib.util.module_from_spec(spec); spec.loader.exec_module(policy)
    version = run('version', [args.rustc, '-vV'])
    scoped, banner = policy.apply(env, version)
    assert 'RUSTC_BOOTSTRAP' not in env and scoped['RUSTC_BOOTSTRAP']=='1'
    assert run('scoped-version', [args.rustc, '-vV'], environment=scoped)==version
    for bad in (version.replace('1.99.1','1.99.0'), version.replace('1.99.1','1.99.1-nightly'), version+'release: 1.99.1\n'):
        try: policy.apply(env,bad)
        except ValueError: pass
        else: raise AssertionError('unsupported Rust release accepted')
    base=work/'baseline'
    names=('build/config/rust.gni','build/rust/allocator/BUILD.gn','build/rust/allocator/lib.rs',
           'build/rust/allocator/alloc_error_handler_impl.h')
    before={}
    for name in names:
        path=base/name;path.parent.mkdir(parents=True,exist_ok=True);data=(source/name).read_bytes();path.write_bytes(data)
        before[name]=hashlib.sha256(data).hexdigest()
    patched=work/'patched';shutil.copytree(base,patched)
    patch=owner/'patches/gn-chromium-rust-policy.patch'
    run('patch-check',[args.git,'apply','--check',patch],cwd=patched)
    run('patch',[args.git,'apply',patch],cwd=patched)
    def fixture(label, *, selected=True, release=banner, environment=scoped, error=None):
        root=work/label; shutil.copytree(patched,root)
        for name in ('build/config/chrome_build.gni','build/config/compiler/compiler.gni',
                     'build/config/sanitizers/sanitizers.gni','build/toolchain/toolchain.gni'):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('')
        (root/'.gn').write_text('buildconfig="//BUILDCONFIG.gn"\nscript_executable='+json.dumps(sys.executable)+'\n')
        (root/'BUILDCONFIG.gn').write_text('''build_with_chromium = true
is_wasm = false
is_android = false
is_ios = false
is_linux = false
is_chromeos = false
is_fuchsia = false
is_mac = false
is_win = false
is_apple = false
is_bsd = true
host_os = "mac"
target_os = "netbsd"
host_cpu = "arm64"
target_cpu = "x64"
current_os = target_os
current_cpu = target_cpu
host_toolchain = "//:host"
current_toolchain = "//:target"
toolchain_for_rust_host_build_tools = false
import("//build/config/rust.gni")
set_default_toolchain("//:target")
''')
        # Consume the exact allocator target body, rather than copy its feature list.
        allocator=(root/'build/rust/allocator/BUILD.gn').read_text()
        start=allocator.index('  rust_static_library("allocator") {')
        finish=allocator.index('\n  if (rust_allocator_uses_allocator_impls_h)',start)
        (root/'BUILD.gn').write_text('''set_defaults("rust_static_library") {
  configs = [ "//build/config/compiler:disallow_unstable_features" ]
}
template("rust_static_library") {
  group(target_name) {
    metadata = { flags = invoker.rustflags }
    not_needed(invoker, "*")
  }
}
rust_allocator_uses_allocator_impls_h = false
'''+allocator[start:finish]+'''
group("probe") {
  metadata = { capability = [ rustc_nightly_capability ] version = [ rustc_version ] }
}
toolchain("target") { tool("stamp") { command="touch {{output}}" } }
''')
        out=root/'out';out.mkdir()
        (out/'args.gn').write_text('rust_sysroot_absolute='+json.dumps(str(prefix))+'\nrustc_version='+json.dumps(release)+'\nemberbsd_rust_unstable_features='+str(selected).lower()+'\n')
        run(label+'-gn',[args.gn,'gen',out],cwd=root,environment=environment,error=error)
        if error:return None
        value=json.loads(run(label+'-desc',[args.gn,'desc',out,'//:*','metadata','--format=json'],cwd=root,environment=environment))
        return value
    configured=fixture('selected')
    assert configured['//:probe']['metadata']['capability']==[True], configured
    assert configured['//:probe']['metadata']['version']==[banner]
    flags=configured['//:allocator']['metadata']['flags']
    assert flags==['-Zallow-features=linkage,rustc_attrs'],flags
    stable=fixture('stable-default',selected=False,environment=env)
    assert stable['//:probe']['metadata']['capability']==[False]
    fixture('missing-scoped-env',environment=env,error='scoped environment')
    fixture('wrong-version',release=banner.replace('1.99.1','1.99.0'),error='stable Rust 1.99.1')
    nightly=fixture('nightly-default',selected=False,release=banner.replace('1.99.1','1.100.0-nightly'),environment=env)
    assert nightly['//:probe']['metadata']['capability']==[True]
    (work/'ordinary.rs').write_text('pub fn value() -> u32 { 42 }\n')
    # These are the real unconditional Chromium flags, which must be supported
    # without deleting diagnostics or changing the compiler's release channel.
    config=(source/'build/config/compiler/BUILD.gn').read_text()
    flags_begin=config.index('  rustflags += [\n    # To make Rust .d files compatible with ninja')
    flags_end=config.index('\n  ]',flags_begin)
    import re
    common=re.findall(r'"(-Z[^\"]+)"',config[flags_begin:flags_end])
    assert common==['-Zdep-info-omit-d-target','-Zmacro-backtrace','-Zremap-cwd-prefix=.','-Zexternal-clangrt']
    ordinary=[args.rustc,'--crate-name','ordinary','--crate-type','rlib','--edition=2024',
              '--emit=metadata,dep-info','ordinary.rs','-o','ordinary.rmeta',*common,'-Zallow-features=']
    run('ordinary-without-policy',ordinary,error='nightly')
    run('ordinary-policy',ordinary,environment=scoped)
    # Generate the actual C++ FFI declaration with the common bindgen provider.
    run('allocator-bindgen',[args.bindgen,patched/names[3],'--enable-cxx-namespaces','--no-layout-tests',
                            '--output','allocator_ffi.rs','--','-x','c++','-isysroot',args.macos_sdk])
    run('allocator-ffi',[args.rustc,'--crate-name','alloc_error_handler_impl_ffi','--crate-type','rlib',
                         '--edition=2024','allocator_ffi.rs','-o','liballocator_ffi.rlib'])
    allocator=[args.rustc,'--crate-name','allocator','--crate-type','rlib','--edition=2024',
               '--cfg','RUST_ALLOCATOR_NIGHTLY_CAPABILITY',patched/names[2],
               '--extern','alloc_error_handler_impl_ffi='+str(work/'liballocator_ffi.rlib'),
               '--emit=obj','-o','allocator.o',*common,*flags]
    run('actual-allocator',allocator,environment=scoped)
    run('allocator-missing-allowlist',allocator[:-1]+['-Zallow-features='],environment=scoped,error='not in the list of allowed features')
    (work/'ordinary.rs').write_text('#![feature(linkage)]\npub fn value() -> u32 { 42 }\n')
    run('ordinary-feature-refusal',ordinary,environment=scoped,error='not in the list of allowed features')
    alien=work/'allocator-extra-feature.rs';alien.write_text('#![feature(portable_simd)]\n'+(patched/names[2]).read_text())
    run('allocator-extra-feature-refusal',[str(alien) if str(item)==str(patched/names[2]) else item for item in allocator],environment=scoped,error='not in the list of allowed features')
    assert before=={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in names}
    (work/'result.json').write_text(json.dumps(dict(scope='actual GN, stable Rust flags and actual native allocator object; no target stdlib or Electron runtime claim',version=version,commands=commands),indent=2)+'\n')
    print('PASS: stable Rust identity, explicit GN capability, real Chromium flags/allocator, scoped environment and feature allowlist refusals')


if __name__=='__main__':main()
