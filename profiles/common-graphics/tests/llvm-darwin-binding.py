#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the SDK-selected native binding and runtime-view contract."""
import argparse
from pathlib import Path
import sys
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--sdk-source', required=True)
p.add_argument('--binding', required=True)
p.add_argument('--view', required=True)
a = p.parse_args()
sys.path[:0] = [str(Path(a.sdk_source)/'src'), str(Path(__file__).resolve().parents[1]/'cross')]
import llvm_darwin_binding as binding
selected = binding.select(a.binding, a.view)
assert selected['namespace'] == '__ember1'
def fake_otool(tool, option, path):
    assert option == '-D'
    name = selected['linker_target'] if path == selected['library'] else Path(path).name
    if path != selected['library']:
        for stem in ('libzstd', 'libxml2', 'libz'):
            if name.startswith(stem):
                aliases = list((Path(selected['cow_prefix']) / 'lib').glob(stem + '.*.dylib'))
                name = next((p.name for p in aliases if p.is_symlink() and p.resolve() == Path(path)), name)
                break
    # Any canonical absolute library directory; the check compares only its shape.
    base = str(Path(tempfile.gettempdir()) / 'install-names' / 'lib') + '/'
    return path + '\n' + base + ('libc++/' if name.startswith('libc++_') else '') + name
files, names = binding.declared_system_libraries(selected, ['-lm', '-lz', '-lzstd', '-lxml2'], fake_otool)
assert len(files) == 4 and names[0].endswith('/libc++/libc++_ember1.1.dylib')
try: binding.declared_system_libraries(selected, ['-lLLVM'], fake_otool)
except ValueError as error: assert 'unsupported native system library' in str(error)
else: raise AssertionError('shared LLVM flag accepted as a system library')
command = binding.argv(selected, ['-c', '/dev/null', '-o', '/dev/null'])
assert selected['include_dir'] in command and selected['abi_view'] in command
with tempfile.TemporaryDirectory() as tmp:
    bad = Path(tmp) / selected['linker_target']
    bad.symlink_to('/bin/sh')
    try: binding.select(a.binding, tmp)
    except ValueError as error: assert 'declared C++ library' in str(error)
    else: raise AssertionError('incorrect runtime view accepted')
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for item in Path(a.view).iterdir():
        (root / item.name).symlink_to(item.resolve(strict=True))
    (root / 'injected.dylib').symlink_to('/bin/sh')
    try: binding.select(a.binding, tmp)
    except ValueError as error: assert 'undeclared library' in str(error)
    else: raise AssertionError('injected library accepted')
print('PASS: SDK v4 selection, wrong-view and injection refusals')
