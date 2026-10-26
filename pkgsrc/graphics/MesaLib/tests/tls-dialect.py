#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check actual Mesa TLS guard expressions. Never configure or compile."""
import argparse
import ast
from pathlib import Path
import re
from types import SimpleNamespace


def require(condition, message):
    if not condition:
        raise ValueError(message)


def guard_expressions(source):
    block = re.search(r'^if not have_mtls_dialect\n(.*?)^endif$', source, re.M | re.S)
    require(block is not None, 'missing upstream TLS selection block')
    require("cc.run('int __thread x; int main() { return x; }'," in block[1] and
            'c_cpp_args += tlsdesc_arg' in block[1], 'upstream TLS probe changed')
    lines, expressions = iter(block[1].splitlines()), []
    for line in lines:
        if not line.startswith(('  if ', '  elif ')):
            continue
        expression = line.strip().split(' ', 1)[1]
        while expression.count('(') > expression.count(')'):
            expression += ' ' + next(lines).strip()
        tree = ast.parse(expression, mode='eval')
        calls = {'meson.is_cross_build', 'meson.can_run_host_binaries',
                 'host_machine.system', 'host_machine.cpu_family'}
        for node in ast.walk(tree):
            require(isinstance(node, (ast.Expression, ast.BoolOp, ast.And, ast.Or,
                    ast.UnaryOp, ast.Not, ast.Compare, ast.Eq, ast.Constant,
                    ast.Call, ast.Attribute, ast.Name, ast.Load)), 'unexpected guard syntax')
            if isinstance(node, ast.Call):
                require(ast.unparse(node.func) in calls and not node.args and not node.keywords,
                        'unexpected guard call')
        expressions.append(compile(tree, '<actual-meson-tls-guard>', 'eval'))
    require(len(expressions) == 2, 'unexpected TLS selection branches')
    return expressions


def check_matrix(source):
    guards = guard_expressions(source)
    checks = 0
    for system, cpu, native_probe in (
        ('netbsd', 'x86_64', False), ('netbsd', 'aarch64', True),
        ('freebsd', 'x86_64', False), ('freebsd', 'aarch64', False),
        ('linux', 'x86_64', True), ('linux', 'aarch64', True),
    ):
        for cross, can_run, expected in ((False, True, native_probe),
                                         (True, False, False), (True, True, native_probe)):
            namespace = dict(host_machine=SimpleNamespace(system=lambda: system,
                             cpu_family=lambda: cpu),
                             meson=SimpleNamespace(is_cross_build=lambda: cross,
                             can_run_host_binaries=lambda: can_run))
            probe = not any(eval(guard, {'__builtins__': {}}, namespace) for guard in guards)
            require(probe == expected,
                    f'wrong TLS probe selection: {system}/{cpu}, cross={cross}, can_run={can_run}')
            checks += 1
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('meson_build', type=Path, help='actual patched upstream meson.build')
    args = parser.parse_args()
    source = args.meson_build.read_text()
    checks = check_matrix(source)
    source = re.search(r'^if not have_mtls_dialect\n.*?^endif$', source, re.M | re.S)[0]
    bsd_guard = ("host_machine.system() == 'freebsd' or (\n"
                 "    host_machine.system() == 'netbsd' and host_machine.cpu_family() == 'x86_64')")
    mutations = (
        (bsd_guard, "host_machine.system() == 'freebsd'"),
        (bsd_guard, bsd_guard.replace(" and host_machine.cpu_family() == 'x86_64'", '')),
        ('meson.is_cross_build() and not meson.can_run_host_binaries()',
         'meson.is_cross_build() and meson.can_run_host_binaries()'),
    )
    for old, new in mutations:
        require(source.count(old) == 1, 'causal control no longer matches actual source')
        try:
            check_matrix(source.replace(old, new, 1))
        except ValueError:
            checks += 1
        else:
            raise ValueError('TLS selection regression accepted a deliberate defect')
    print(f'PASS: {checks} actual-condition native/cross and causal checks; no configure/build/runtime')


if __name__ == '__main__':
    main()
