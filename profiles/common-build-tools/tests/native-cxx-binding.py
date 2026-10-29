#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check explicit host compiler binding routing using the selected native tools."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'host-prefix', 'binding-record'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
sys.path.insert(0, str(a.sdk_source.resolve(strict=True) / 'src'))
from emberbsd_sdk import compiler_bindings
from emberbsd_sdk.errors import SDKError
source = Path(__file__).resolve().parents[1] / 'cross/prepare-native-tools.py'
spec = importlib.util.spec_from_file_location('native_binding_adapter', source)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
args = argparse.Namespace(host_prefix=str(a.host_prefix), compiler_family='clang', fetch_mode='fetch')
tools = adapter.selection(args)
selected = adapter.select_native_cxx(tools, str(a.binding_record))
assert selected['adapters']['cxx'] == str(a.binding_record.parent / 'cxx')
record = json.loads(a.binding_record.read_text())
commands = {role:spec['argv'] for role, spec in record['commands'].items()}
with tempfile.TemporaryDirectory(prefix='native-cxx-routing-') as temp:
    for index, bad in enumerate((['--sysroot=/foreign'], ['-mmacos-version-min=27.0'])):
        changed = dict(commands, cc=commands['cc'] + bad)
        path = Path(temp) / str(index)
        runtime = dict(record['native_cxx_runtime'])
        if 'platform_cxxabi' in runtime:
            runtime['platform_cxxabi'] = True
        compiler_bindings.bind_compilers(path, commands=changed, flags=record['flags'],
                                        python=tools.tool('python'), native_cxx_runtime=runtime)
        try:
            adapter.select_native_cxx(tools, str(path / 'commands.json'))
        except SDKError:
            pass
        else:
            raise AssertionError('mismatched native compiler context accepted')
print('PASS: selected native binding and mismatched compiler contexts')
