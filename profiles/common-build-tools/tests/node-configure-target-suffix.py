#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the actual Node configure suffix branch across target flavors."""
import argparse
import ast
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', required=True, type=Path, help='prepared Node source')
a = p.parse_args()
tree = ast.parse((a.source / 'configure.py').read_text())
function = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'configure_node')
branch = next(x for x in function.body if isinstance(x, ast.If) and
              any(isinstance(y, ast.Name) and y.id == 'shlib_suffix' for y in ast.walk(x)))
format_branch = next(x for x in function.body if isinstance(x, ast.If) and
                     isinstance(x.test, ast.Compare) and
                     any(isinstance(y, ast.Constant) and y.value == '%s' for y in ast.walk(x.test)))
wrapper = ast.parse('def suffix(flavor, node_module_version):\n    pass\n')
wrapper.body[0].body = [branch, format_branch, ast.Return(value=ast.Name(id='shlib_suffix', ctx=ast.Load()))]
ast.fix_missing_locations(wrapper)
namespace = {}
exec(compile(wrapper, str(a.source / 'configure.py'), 'exec'), namespace)
for flavor, expected in {'netbsd': 'so.1162674177', 'linux': 'so.1162674177',
                         'mac': '1162674177.dylib', 'ios': '1162674177.dylib',
                         'android': 'so', 'aix': '1162674177.a',
                         'os400': '1162674177.a', 'zos': '1162674177.x'}.items():
    actual = namespace['suffix'](flavor, '1162674177')
    if actual != expected:
        raise AssertionError(f'{flavor}: {actual!r} != {expected!r}')
print('PASS: Node shlib suffix follows resolved target flavor')
