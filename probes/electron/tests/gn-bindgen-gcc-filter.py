#!/usr/bin/env python3.15
"""Check Chromium's shared libclang argument filter with the Ports GCC patch."""
import argparse
import ast
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True, help='Chromium source root')
p.add_argument('--patch', type=Path, required=True, help='Ports filter patch')
p.add_argument('--patch-tool', type=Path, required=True, help='selected patch executable')
args = p.parse_args()
root = args.source.resolve(strict=True)
gni = root / 'build/rust/gni_impl'
patch = args.patch.resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='ember-bindgen-filter-') as temp:
    tree = Path(temp)
    local = tree / 'build/rust/gni_impl'
    local.mkdir(parents=True)
    for name in ('filter_clang_args.py', 'filter_clang_args_unittest.py'):
        shutil.copy2(gni / name, local / name)
    marker = "arg.startswith('--param=')"
    if marker not in (local / 'filter_clang_args.py').read_text():
        subprocess.run([str(args.patch_tool.resolve(strict=True)), '-p1', '-F', '0', '-i', str(patch)], cwd=tree, check=True)
    assert (local / 'filter_clang_args.py').read_text().count(marker) == 1
    subprocess.run([sys.executable, '-B', str(local / 'filter_clang_args_unittest.py')], cwd=local, check=True)
    spec = importlib.util.spec_from_file_location('filter_fixture', local / 'filter_clang_args.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = ['--param=x=y', '-DABI_PROBE=1', '-I/include', '--target=aarch64-unknown-netbsd', '--sysroot=/sysroot', '-Werror']
    saved = original[:]
    expected = saved[1:-1] + ['-w', '-Wno-unknown-argument', '-Wno-unknown-warning-option', '-Wno-unused-command-line-argument']
    assert module.filter_clang_args(original) == expected
    assert original == saved
    for caller, attr in (('run_bindgen.py', 'clangargs'), ('run_rs_bindings_from_cc.py', 'clang_args')):
        parsed = ast.parse((gni / caller).read_text())
        calls = [n for n in ast.walk(parsed) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'filter_clang_args']
        assert len(calls) == 1 and len(calls[0].args) == 1
        value = calls[0].args[0]
        assert isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) and value.value.id == 'args' and value.attr == attr
print('upstream filter tests, GCC parameter, input immutability and both callers PASS')
