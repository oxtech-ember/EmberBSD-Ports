#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the native CLI, selected libclang and generated Rust bindings."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tomllib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rustc', required=True)
    parser.add_argument('--cc', required=True)
    parser.add_argument('--cppflags', default='')
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    target = config['build']['target']
    binary = Path(config['build']['target-dir']) / target / 'release/bindgen'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    def run(label, command, *, env=None, success=True):
        result = subprocess.run([str(x) for x in command], cwd=output,
                                env=env, text=True, capture_output=True)
        (output / (label + '.log')).write_text(result.stdout + result.stderr)
        if (result.returncode == 0) != success:
            raise RuntimeError(f'{label}: unexpected exit {result.returncode}; see {output}')
        return result.stdout

    assert run('version', [binary, '--version']).strip() == 'bindgen 0.73.2'
    header = output / 'probe.h'
    header.write_text('#include <stdint.h>\n'
                      'typedef struct { uint32_t value; } Probe;\n'
                      'uint32_t probe_answer(Probe value);\n')
    flags = shlex.split(args.cppflags)
    sdk = os.environ.get('SDKROOT')
    if sdk:
        flags += ['-isysroot', sdk]
    generated = output / 'bindings.rs'
    command = [binary, header, '--allowlist-type', 'Probe', '--allowlist-function',
               'probe_answer', '--output', generated, '--', '--target=' + target, *flags]
    run('c-bindings', command)
    source = output / 'probe.c'
    source.write_text('#include "probe.h"\n'
                      'uint32_t probe_answer(Probe value) { return value.value + 1; }\n')
    obj = output / 'probe.o'
    run('c-compile', [*shlex.split(args.cc), *flags, '-c', source, '-o', obj])
    consumer = output / 'main.rs'
    consumer.write_text('include!("bindings.rs");\n'
                        'fn main() { assert_eq!(unsafe { probe_answer(Probe { value: 41 }) }, 42); }\n')
    executable = output / 'consumer'
    linker = config['target'][target]['linker']
    run('rust-compile', [args.rustc, '--target', target, '-C', 'linker=' + linker,
                        '-C', 'link-arg=' + str(obj), consumer, '-o', executable])
    run('consumer', [executable])

    cpp = output / 'probe.hpp'
    cpp.write_text('namespace fixture { struct Cxx { int value; }; }\n')
    cpp_bindings = output / 'cpp_bindings.rs'
    run('cpp-bindings', [binary, cpp, '--allowlist-type', 'fixture::Cxx',
                         '--output', cpp_bindings, '--', '-x', 'c++',
                         '--target=' + target, *flags])
    assert 'fixture_Cxx' in cpp_bindings.read_text()
    run('cpp-rust', [args.rustc, '--target', target, '--crate-type', 'lib',
                    '--emit=metadata', cpp_bindings, '-o', output / 'cpp.rmeta'])

    missing = dict(os.environ, LIBCLANG_PATH=str(output / 'missing-libclang'))
    run('missing-libclang', command, env=missing, success=False)
    print('PASS: C/C++ generation, Rust FFI consumer and missing-libclang control')


if __name__ == '__main__':
    main()
