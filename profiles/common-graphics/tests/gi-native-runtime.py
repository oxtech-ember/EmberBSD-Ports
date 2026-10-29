#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the scanner's selected runtime handling on its patched source."""
import argparse
import ast
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
args = parser.parse_args()
tree = ast.parse(args.source.read_text())
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name == '_emberbsd_native_runtime_view')
module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
sys = SimpleNamespace(platform='darwin')
scope = {'os': os, 'sys': sys}
exec(compile(module, str(args.source), 'exec'), scope)
run = scope[function.name]
with tempfile.TemporaryDirectory() as view:
    with patch.dict(os.environ, {'DYLD_LIBRARY_PATH': '/build/a:/build/b',
                                 'EMBERBSD_NATIVE_RUNTIME_VIEW': view}, clear=True):
        run(); run()
        assert os.environ['DYLD_LIBRARY_PATH'] == '/build/a:/build/b:' + view
    with patch.dict(os.environ, {'EMBERBSD_NATIVE_RUNTIME_VIEW': view}, clear=True):
        run(); assert os.environ['DYLD_LIBRARY_PATH'] == view
    with patch.dict(os.environ, {'DYLD_LIBRARY_PATH': '/build/a'}, clear=True):
        run(); assert os.environ['DYLD_LIBRARY_PATH'] == '/build/a'
    with patch.dict(os.environ, {'EMBERBSD_NATIVE_RUNTIME_VIEW': 'relative'}, clear=True):
        try: run()
        except ValueError as e: assert 'invalid EMBERBSD_NATIVE_RUNTIME_VIEW' in str(e)
        else: raise AssertionError('relative view accepted')
    for bad in (view + ':bad', view + '/missing'):
        with patch.dict(os.environ, {'EMBERBSD_NATIVE_RUNTIME_VIEW': bad}, clear=True):
            try: run()
            except ValueError as e: assert 'invalid EMBERBSD_NATIVE_RUNTIME_VIEW' in str(e)
            else: raise AssertionError('invalid view accepted')
    sys.platform = 'linux'
    with patch.dict(os.environ, {'EMBERBSD_NATIVE_RUNTIME_VIEW': view}, clear=True):
        run(); assert 'DYLD_LIBRARY_PATH' not in os.environ
print('GI scanner native runtime view PASS')
