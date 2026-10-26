#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), not submitted upstream.
"""Evaluate the production compiler-selection templates with a real GN binary.

The fixture captures the toolchain argument scope. It defines no compiler rules
and does not invoke Ninja. This does not validate the full Chromium graph.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile


def template(source, name):
    heading = 'template("' + name + '") {'
    if source.count(heading) != 1:
        raise ValueError('Expected one production template: ' + name)
    start = source.index(heading)
    depth = 0
    for match in re.finditer(r'"(?:\\.|[^"\\])*"|#[^\n]*|[{}]', source[start:]):
        token = match.group()
        if token == '{':
            depth += 1
        elif token == '}':
            depth -= 1
            if not depth:
                return source[start:start + match.end()] + '\n'
    raise ValueError('Unclosed production template: ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gn', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--baseline-source', type=Path)
    args = parser.parse_args()
    if not args.gn.is_absolute() or not args.gn.is_file():
        parser.error('--gn must name an absolute executable')
    pairs = [('build/toolchain/mac/BUILD.gn', 'mac_toolchain', 'apple_toolchain'),
             ('build/toolchain/apple/toolchain.gni', 'apple_rust_host_build_tools_toolchain', 'single_apple_toolchain')]
    rows = []
    with tempfile.TemporaryDirectory(prefix='gn-mac-gcc16-scope-') as temporary:
        top = Path(temporary)
        def check(label, production, entry, child, global_clang, selection, expected_error=None):
            work = top / label
            work.mkdir()
            (work / '.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\n')
            (work / 'BUILDCONFIG.gn').write_text('set_default_toolchain("//:fixture")\n')
            expected = selection != 'false'
            if selection == 'missing-scope':
                invocation = entry + '("observed") {}\n'
            else:
                choice = '' if selection == 'unset' else '    is_clang = ' + selection + '\n'
                invocation = entry + '("observed") {\n  toolchain_args = {\n    current_cpu = "arm64"\n' + choice + '  }\n}\n'
            capture = '''template("CHILD") {
  observed_args = invoker.toolchain_args
  assert(observed_args.is_clang == EXPECTED, "Compiler selection changed")
  assert(!defined(observed_args._invoker_toolchain_args), "Private alias leaked")
  selected_value = "true"
  if (!observed_args.is_clang) {
    selected_value = "false"
  }
  write_file("$root_build_dir/selection.txt", [ selected_value ])
  not_needed(invoker, "*")
  group(target_name) {}
}
'''.replace('CHILD', child).replace('EXPECTED', str(expected).lower())
            (work / 'BUILD.gn').write_text('is_clang = ' + str(global_clang).lower() + '\ntarget_os = "netbsd"\nmac_bin_path = "/unused"\nTESTONLY_AND_VISIBILITY = []\n' + capture + production + invocation + '''toolchain("fixture") {
  tool("stamp") {
    command = "not-executed"
    description = "Unused fixture stamp"
  }
}
''')
            command = [str(args.gn), 'gen', str(work / 'out'), '--root=' + str(work)]
            completed = subprocess.run(command, cwd=work, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, check=False, timeout=15)
            output = completed.stdout
            if expected_error:
                if completed.returncode == 0 or expected_error not in output:
                    raise AssertionError(label + ': expected refusal\n' + output)
            else:
                if completed.returncode != 0:
                    raise AssertionError(label + ': generation failed\n' + output)
                observed = (work / 'out/selection.txt').read_text().strip()
                if observed != str(expected).lower():
                    raise AssertionError(label + ': wrong selected compiler: ' + observed)
            rows.append(dict(case=label, actual_exit=completed.returncode,
                output_sha256=hashlib.sha256(output.encode()).hexdigest()))
        for path, entry, child in pairs:
            production = template((args.source / path).read_text(), entry)
            for outer in (False, True):
                for choice in ('false', 'true', 'unset'):
                    check(entry + '-' + str(outer).lower() + '-' + choice, production, entry, child, outer, choice)
            check(entry + '-missing-scope', production, entry, child, False,
                  'missing-scope', 'Toolchains must declare toolchain_args')
            if args.baseline_source:
                old = template((args.baseline_source / path).read_text(), entry)
                check(entry + '-old-parser', old, entry, child, False, 'false',
                      'Expected identifier for right-hand-side')
    print(json.dumps(dict(scope='GN template selection only; no compiler, Ninja, or full graph',
        cases=rows, passed=len(rows), temporary_fixture_removed=True), indent=2))


if __name__ == '__main__':
    main()
