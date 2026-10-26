#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), not submitted upstream.
"""Evaluate native and target family selection in the production GN leaf.

The fixture captures toolchain inputs. It does not compile, link, run Ninja,
or validate the full Chromium graph. --source contains the applied leaf.
An optional --baseline-source demonstrates the original inherited-mode bug.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


MEMBER = Path('build/toolchain/linux/unbundle/BUILD.gn')


def evaluate(gn, source, root, name, target_clang, host_clang=None,
             expected_host=True, error=None):
    work = root / name
    work.mkdir()
    production = (source / MEMBER).read_text()
    (work / MEMBER.parent).mkdir(parents=True)
    (work / MEMBER).write_text(production)
    (work / '.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\n')
    (work / 'BUILDCONFIG.gn').write_text('''
declare_args() {
  is_clang = OUTER
}
current_os = "netbsd"
current_cpu = "x64"
set_default_toolchain("//:fixture")
'''.replace('OUTER', str(target_clang).lower()))
    (work / 'BUILD.gn').write_text('''
group("all") { deps = [ "//build/toolchain/linux/unbundle:default",
                         "//build/toolchain/linux/unbundle:host" ] }
toolchain("fixture") {
  tool("stamp") { command = "not-executed" }
}
''')
    capture = '''
template("gcc_toolchain") {
  _args = invoker.toolchain_args
  assert(_args.current_cpu == current_cpu, "Target CPU changed")
  assert(_args.current_os == current_os, "Target OS changed")
  _effective_clang = is_clang
  if (defined(_args.is_clang)) {
    _effective_clang = _args.is_clang
  }
  _expected = TARGET
  _cc = "/sdk/target/clang"
  _cxx = "/sdk/target/clang++"
  _ar = "/sdk/target/llvm-ar"
  _nm = "/sdk/target/llvm-nm"
  _asm = "-DTARGET_ASM=1"
  if (target_name == "host") {
    _expected = HOST
    _cc = "/sdk/native/clang"
    _cxx = "/sdk/native/clang++"
    _ar = "/sdk/native/llvm-ar"
    _nm = "/sdk/native/llvm-nm"
    _asm = "-DHOST_ASM=1"
  }
  assert(_effective_clang == _expected, "Compiler family leaked across toolchains")
  assert(invoker.cc == _cc && invoker.cxx == _cxx, "Compiler path changed")
  assert(invoker.ar == _ar && invoker.nm == _nm, "Object tool path changed")
  assert(invoker.ld == _cxx, "Link driver changed")
  assert(invoker.extra_asmflags == _asm, "Assembler flags crossed toolchains")
  _result = "gcc"
  if (_effective_clang) { _result = "clang" }
  write_file("$root_build_dir/$target_name.family", [ _result ])
  not_needed(invoker, "*")
  group(target_name) {}
}
'''.replace('TARGET', str(target_clang).lower(), 1).replace('HOST', str(expected_host).lower(), 1)
    (work / 'build/toolchain/gcc_toolchain.gni').write_text(capture)
    args = []
    if host_clang is not None:
        args.append('unbundle_host_is_clang=' + json.dumps(host_clang))
    environment = dict(os.environ)
    for role, filename in (('CC', 'clang'), ('CXX', 'clang++'),
                           ('AR', 'llvm-ar'), ('NM', 'llvm-nm')):
        environment[role] = '/sdk/target/' + filename
        environment['BUILD_' + role] = '/sdk/native/' + filename
    environment.update(READELF='/sdk/target/llvm-readelf',
                       ASFLAGS='-DTARGET_ASM=1', BUILD_ASFLAGS='-DHOST_ASM=1')
    command = [str(gn), 'gen', str(work / 'out'), '--root=' + str(work)]
    if args:
        command.append('--args=' + ' '.join(args))
    result = subprocess.run(command, env=environment, cwd=work,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=15, check=False)
    if error:
        if result.returncode == 0 or error not in result.stdout:
            raise AssertionError(name + ': expected refusal\n' + result.stdout)
    else:
        if result.returncode != 0:
            raise AssertionError(name + ': GN failed\n' + result.stdout)
        for leaf, expected in (('default', target_clang), ('host', expected_host)):
            actual = (work / 'out' / (leaf + '.family')).read_text().strip()
            if actual != ('clang' if expected else 'gcc'):
                raise AssertionError(name + ': wrong compiler family for ' + leaf)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--gn', required=True, type=Path)
    parser.add_argument('--baseline-source', type=Path)
    options = parser.parse_args()
    if not options.gn.is_absolute() or not options.gn.is_file():
        parser.error('--gn must be an absolute executable path')
    count = 0
    with tempfile.TemporaryDirectory(prefix='gn-unbundle-family-') as temporary:
        root = Path(temporary)
        for target in (False, True):
            evaluate(options.gn, options.source, root, 'default-' + str(target), target)
            count += 1
            for host in (False, True):
                evaluate(options.gn, options.source, root,
                         '-'.join((str(target), str(host))), target,
                         host, expected_host=host)
                count += 1
        if options.baseline_source:
            evaluate(options.gn, options.baseline_source, root, 'baseline-default',
                     False, error='Compiler family leaked across toolchains')
            evaluate(options.gn, options.baseline_source, root, 'baseline-explicit',
                     True, False, expected_host=False,
                     error='Compiler family leaked across toolchains')
            count += 2
    print(json.dumps({'tests': count, 'status': 'PASS',
                      'scope': 'GN family/path/flag selection only; no compilation'}))


if __name__ == '__main__':
    main()
