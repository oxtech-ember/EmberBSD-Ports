#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise Rollup's real Rust allocator crate with the shared mimalloc provider."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tomllib


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('host-prefix', 'vendor', 'rollup-source', 'mimalloc-libdir', 'sdk-root',
                 'sdk-source', 'utility-path', 'lock-root', 'link-context', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--deployment-target', required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('this runtime regression covers native Darwin')
    for value in vars(args).values():
        if isinstance(value, Path) and not value.is_absolute():
            parser.error('select absolute paths')
    recipe = Path(__file__).resolve().parents[1]
    ports = recipe.parents[2]
    helper = ports / 'profiles/common-build-tools/cargo-config.py'
    cargo = module(helper, 'cargo_config')
    prepare = module(recipe / 'files/prepare.py', 'rollup_prepare')
    prefix = args.host_prefix.resolve()
    for name in ('cargo', 'rustc', 'clang', 'clang++', 'llvm-ar', 'ld64.lld', 'mksh', 'python3.15'):
        path = prefix / 'bin' / name
        assert path.resolve().is_relative_to(prefix) and os.access(path, os.X_OK), path
    for crate, version in (('mimalloc-safe', '0.1.67'), ('libmimalloc-sys2', '0.1.63')):
        manifest = tomllib.loads((args.vendor / (crate + '-' + version) / 'Cargo.toml').read_text())
        assert manifest['package']['name'] == crate and manifest['package']['version'] == version
    build_script = args.vendor / 'libmimalloc-sys2-0.1.63/build.rs'
    before = hashlib.sha256(build_script.read_bytes()).hexdigest()
    args.work.mkdir(parents=True, exist_ok=False)
    overrides = args.work / 'mimalloc-links.toml'
    target = subprocess.check_output([str(prefix / 'bin/rustc'), '-vV'], text=True).split('host: ', 1)[1].splitlines()[0]
    prepare.prepare(args.rollup_source, '4.65.1', target, 'darwin-arm64', args.mimalloc_libdir, overrides)
    flags = ['-isysroot', str(args.sdk_root), '-mmacosx-version-min=' + args.deployment_target,
             '--start-no-unused-arguments', '--ld-path=' + str(prefix / 'bin/ld64.lld'), '--end-no-unused-arguments']
    env = dict(os.environ, PATH=str(args.utility_path), SDKROOT=str(args.sdk_root),
               MACOSX_DEPLOYMENT_TARGET=args.deployment_target, CARGO_NET_OFFLINE='true',
               CMAKE='/unavailable-cmake-build-script-must-be-skipped')
    env.pop('DYLD_LIBRARY_PATH', None)
    env.pop('DYLD_INSERT_LIBRARIES', None)
    launcher = [str(prefix / 'bin/python3.15'), '-B', str(args.sdk_source / 'scripts/link-launcher.py'),
                '--lock-root', str(args.lock_root), '--context', str(args.link_context), '--']
    results = []
    for name in ('shared-provider', 'missing-override'):
        directory = args.work / name
        (directory / 'src').mkdir(parents=True)
        (directory / 'Cargo.toml').write_text('''[package]
name="shared-mimalloc-consumer"
version="0.1.0"
edition="2021"
[dependencies]
mimalloc-safe={version="=0.1.67",default-features=false,features=["v3"]}
''')
        (directory / 'src/main.rs').write_text('''use mimalloc_safe::MiMalloc;
#[global_allocator] static ALLOCATOR: MiMalloc = MiMalloc;
extern "C" {
    fn mi_version() -> i32;
    fn mi_check_owned(p: *const std::ffi::c_void) -> bool;
    fn malloc(size: usize) -> *mut std::ffi::c_void;
    fn free(p: *mut std::ffi::c_void);
}
fn main() {
    assert_eq!(unsafe { mi_version() }, 30600);
    let value = Box::new(17u64);
    assert!(unsafe { mi_check_owned((&*value as *const u64).cast()) });
    unsafe { let p = malloc(91); assert!(!p.is_null()); assert!(!mi_check_owned(p)); free(p); }
    let handles: Vec<_> = (0..4).map(|id| std::thread::spawn(move || {
        let mut values = Vec::new();
        for n in 0..1000 { values.push(vec![id as u8; n + 1]); }
        values
    })).collect();
    for handle in handles { let data = handle.join().unwrap(); assert_eq!(data.len(), 1000); drop(data); }
    println!("real mimalloc-safe v3 shared allocator and cross-thread frees passed");
}
''')
        config = directory / 'cargo/config.toml'
        cargo.configure(config=config, vendor=args.vendor, output=directory / 'out',
                        rustc=prefix / 'bin/rustc', shell=prefix / 'bin/mksh',
                        tool_path=str(args.utility_path), mode='native', target=target,
                        host_cc=shlex.join([str(prefix / 'bin/clang'), *flags]),
                        host_cxx=shlex.join([str(prefix / 'bin/clang++'), *flags]),
                        host_ar=str(prefix / 'bin/llvm-ar'), target_cc='', target_cxx='', target_ar='',
                        host_linker_launcher=shlex.join(launcher),
                        build_script_overrides=overrides if name == 'shared-provider' else None)
        command = [str(prefix / 'bin/python3.15'), '-B', '-I', '-S', str(helper), 'run',
                   '--cargo', str(prefix / 'bin/cargo'), '--config', str(config), '--source', str(directory), '--']
        lock = subprocess.run(command + ['generate-lockfile', '--offline'], env=env, capture_output=True, text=True)
        (directory / 'lock.log').write_text(lock.stdout + lock.stderr)
        assert lock.returncode == 0, lock.stdout + lock.stderr
        argv = command + ['build', '--offline', '--locked', '--jobs', '1', '-vv']
        process = subprocess.run(argv, env=env, capture_output=True, text=True)
        output = process.stdout + process.stderr
        (directory / 'build-run.log').write_text(output)
        if name == 'shared-provider':
            assert process.returncode == 0, output
            # Restrict runtime library selection to the consumer, not Cargo and
            # its compiler/build-script subprocesses.
            executable = directory / 'out' / target / 'debug/shared-mimalloc-consumer'
            runtime = subprocess.run([str(executable)], env=dict(env, DYLD_LIBRARY_PATH=str(args.mimalloc_libdir)),
                                     capture_output=True, text=True)
            (directory / 'runtime.log').write_text(runtime.stdout + runtime.stderr)
            assert runtime.returncode == 0 and 'real mimalloc-safe v3 shared allocator' in runtime.stdout, runtime.stdout + runtime.stderr
            assert not [p for p in (directory / 'out').rglob('build-script-build')
                        if p.parent.name.startswith('libmimalloc-sys2-')], 'shared override unexpectedly compiled its bundled allocator build script'
        else:
            assert process.returncode != 0, output
            assert 'unavailable-cmake-build-script-must-be-skipped' in output and 'failed to run custom build command for `libmimalloc-sys2' in output, output
        results.append({'case': name, 'argv': argv, 'exit_code': process.returncode})
    assert before == hashlib.sha256(build_script.read_bytes()).hexdigest(), 'vendor was mutated'
    (args.work / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
    print('Actual mimalloc-safe/libmimalloc-sys2 shared-provider execution and missing-override causal failure passed.')


if __name__ == '__main__':
    main()
