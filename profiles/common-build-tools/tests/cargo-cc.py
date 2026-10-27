#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Run real cc-1.4.6 build scripts through the shared native Cargo tool route."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tomllib

HELPER = Path(__file__).resolve().parents[1]/'cargo-config.py'
spec = importlib.util.spec_from_file_location('cargo_config', HELPER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('host-prefix', 'vendor', 'work', 'sdk-root', 'utility-path'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--deployment-target', required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('this runtime regression currently covers native Darwin')
    if not args.work.is_absolute() or args.work.exists():
        parser.error('use a new absolute work directory')
    for path in (args.host_prefix, args.vendor, args.sdk_root, args.utility_path):
        if not path.is_absolute() or not path.is_dir():
            parser.error('missing absolute input directory: '+str(path))
    prefix = args.host_prefix.resolve()
    for name in ('cargo', 'rustc', 'clang', 'clang++', 'ld64.lld', 'llvm-ar', 'mksh'):
        path = prefix/'bin'/name
        if not path.resolve().is_relative_to(prefix) or not os.access(path, os.X_OK):
            parser.error('missing selected prefix executable: '+str(path))
    cc_info = tomllib.loads((args.vendor/'cc-1.4.6/Cargo.toml').read_text())
    assert cc_info['package']['name'] == 'cc' and cc_info['package']['version'] == '1.4.6'
    args.work.mkdir()
    include = args.work/'headers with spaces'
    include.mkdir()
    (include/'cpp_only.h').write_text('#define HEADER_VALUE 42\n')
    flags = ['-isysroot', str(args.sdk_root), '-mmacosx-version-min='+args.deployment_target,
             '--start-no-unused-arguments', '--ld-path='+str(prefix/'bin/ld64.lld'),
             '--end-no-unused-arguments']
    cc = shlex.join([str(prefix/'bin/clang'), *flags])
    cxx = shlex.join([str(prefix/'bin/clang++'), *flags])
    common = '''#include <cpp_only.h>
#ifndef CPP_ONLY
#error missing_cpp_only
#endif
#if CPP_ONLY != HEADER_VALUE
#error wrong_cpp_only_value
#endif
#if ORDER != 2
#error wrong_flag_order
#endif
'''
    env = dict(os.environ, PATH=str(args.utility_path), SDKROOT=str(args.sdk_root),
               MACOSX_DEPLOYMENT_TARGET=args.deployment_target, CARGO_NET_OFFLINE='true',
               CC='/undeclared-cc', CXX='/undeclared-cxx', AR='/undeclared-ar',
               CPPFLAGS='-DPOISONED_CPPFLAGS', CFLAGS='-DPOISONED_CFLAGS')
    results = {}
    for case in ('fixed', 'missing-include', 'missing-define'):
        directory = args.work/case
        (directory/'src').mkdir(parents=True)
        (directory/'Cargo.toml').write_text('''[package]
name = "cargo-cc-routing-probe"
version = "0.1.0"
edition = "2021"
[build-dependencies]
cc = "=1.4.6"
''')
        (directory/'build.rs').write_text('''fn main() {
    cc::Build::new().file("answer.c").warnings_into_errors(true).compile("answer_c");
    cc::Build::new().cpp(true).file("answer.cc").warnings_into_errors(true).compile("answer_cpp");
}
''')
        (directory/'answer.c').write_text(common+'int answer_c(void) { return CPP_ONLY; }\n')
        (directory/'answer.cc').write_text(common+'#include <vector>\n'
            'extern "C" int answer_cpp(void) { std::vector<int> values{CPP_ONLY, ORDER}; return values[0]; }\n')
        (directory/'src/main.rs').write_text('''extern "C" { fn answer_c() -> i32; fn answer_cpp() -> i32; }
fn main() { assert_eq!(unsafe { answer_c() + answer_cpp() }, 84); println!("native C/C++ CPPFLAGS passed"); }
''')
        cppflags = ['-I'+str(include), '-DCPP_ONLY=42', '-DORDER=1']
        if case == 'missing-include':
            cppflags = [word for word in cppflags if not word.startswith('-I')]
        if case == 'missing-define':
            cppflags.remove('-DCPP_ONLY=42')
        config = directory/'cargo/config.toml'
        host, target = module.configure(config=config, vendor=args.vendor, output=directory/'out',
                         rustc=prefix/'bin/rustc', shell=prefix/'bin/mksh',
                         tool_path=str(args.utility_path), mode='native', target='',
                         host_cc=cc, host_cxx=cxx, host_ar=str(prefix/'bin/llvm-ar'),
                         target_cc='', target_cxx='', target_ar='',
                         host_cppflags=shlex.join(cppflags), host_cflags='-UORDER -DORDER=2',
                         host_cxxflags='-UORDER -DORDER=2 -std=c++20')
        command = [sys.executable, '-B', '-I', '-S', str(HELPER), 'run',
                   '--cargo', str(prefix/'bin/cargo'), '--config', str(config),
                   '--source', str(directory), '--']
        result = subprocess.run(command+['generate-lockfile', '--offline'], env=env,
                                capture_output=True, text=True)
        (directory/'lock.log').write_text(result.stdout+result.stderr)
        assert not result.returncode, result.stdout+result.stderr
        result = subprocess.run(command+['run', '--offline', '--locked', '--jobs', '1', '-vv'],
                                env=env, capture_output=True, text=True)
        (directory/'build-run.log').write_text(result.stdout+result.stderr)
        if case == 'fixed':
            assert not result.returncode and 'native C/C++ CPPFLAGS passed' in result.stdout, result.stdout+result.stderr
            results[case] = 'actual Cargo, cc-1.4.6, C/C++ archive/link and native Rust execution passed'
        else:
            diagnostic = 'cpp_only.h' if case == 'missing-include' else 'missing_cpp_only'
            assert result.returncode and diagnostic in result.stderr, result.stdout+result.stderr
            assert not (directory/'out'/target/'debug/cargo-cc-routing-probe').exists()
            results[case] = 'actual cc build script refused: '+diagnostic
    summary = {'results': results, 'scope': 'native Darwin only; no cross Rust target or Rollup build'}
    (args.work/'result.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
