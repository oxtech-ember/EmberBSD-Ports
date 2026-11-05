#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Direct platform protoc and explicit custom runtime remain separate."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
native = SimpleNamespace(host={'os':'Darwin'}, tool=lambda name: '/prefix/bin/' + name)
options = SimpleNamespace(sdk_source=Path('/sdk'), host_compiler_family='clang', host_runtime_root=None)
protoc = Path('/prefix/bin/protoc')
assert build.selected_protoc_command(options, native, protoc, None) == [str(protoc)]
assert build.selected_protoc_command(options, native, protoc, Path('/view')) == [
    '/prefix/bin/python', '/sdk/scripts/run-darwin-with-runtime.py', '--runtime-view', '/view', '--', str(protoc)]
options.host_runtime_root = Path('/custom')
try:
    build.selected_protoc_command(options, native, protoc, None)
    raise AssertionError('custom runtime without scoped view accepted')
except ValueError:
    pass
options.host_runtime_root = None
for system in ('Linux', 'NetBSD'):
    native.host['os'] = system
    assert build.selected_protoc_command(options, native, protoc, None) == [str(protoc)]
native.host['os'] = 'other'
try:
    build.selected_protoc_command(options, native, protoc, None)
    raise AssertionError('unverified platform accepted')
except ValueError:
    pass
print('PASS: platform direct protoc; custom runtime retains scoped launcher')

# Only dylibs owned by selected buildlink packages may become direct inputs.
import tempfile
with tempfile.TemporaryDirectory() as temporary:
    prefix = Path(temporary).resolve(); (prefix / 'bin').mkdir(); (prefix / 'lib').mkdir()
    protoc = prefix / 'bin/protoc'; protoc.write_text('binary')
    library = prefix / 'lib/libprotobuf.dylib'; library.write_text('library')
    package = prefix / 'pkgdb/protobuf'; package.mkdir(parents=True)
    contents = package / '+CONTENTS'; contents.write_text('lib/libprotobuf.dylib\n')
    for name in ('+BUILD_INFO', '+BUILD_VERSION'):
        (package / name).write_text('metadata')
    loads = [{'name': str(library)}, {'name': '/usr/lib/libc++.1.dylib'}]
    inspector = SimpleNamespace(read_macho_runtime=lambda *args: {'loads': loads, 'implicit_loads': []})
    inputs = build.platform_protoc_inputs(SimpleNamespace(host_prefix=prefix),
        {'darwin_runtime':inspector}, SimpleNamespace(host={'os':'Darwin'}), protoc, {str(contents):'hash'})
    assert str(library) in inputs and str(contents) in inputs
    for name in ('/foreign/lib.dylib', '@rpath/lib.dylib'):
        loads[0] = {'name': name}
        try:
            build.platform_protoc_inputs(SimpleNamespace(host_prefix=prefix),
                {'darwin_runtime':inspector}, SimpleNamespace(host={'os':'Darwin'}), protoc, {str(contents):'hash'})
            raise AssertionError('foreign runtime accepted')
        except (ValueError, FileNotFoundError):
            pass
print('PASS: protoc runtime inputs are selected pkgdb-owned dylibs only')

with tempfile.TemporaryDirectory() as temporary:
    prefix=Path(temporary).resolve(); (prefix/'bin').mkdir(); protoc=prefix/'bin/protoc'; protoc.touch()
    package=prefix/'pkgdb/protobuf'; package.mkdir(parents=True); contents=package/'+CONTENTS'; contents.touch()
    (package/'+BUILD_INFO').touch(); (package/'+BUILD_VERSION').touch()
    called=[]
    def trace(*args, **kwargs):
        called.append((args, kwargs)); return [str(protoc), str(contents)]
    runtime=SimpleNamespace(NATIVE_GENERATOR_RUNTIME_API=1, runtime_inputs=trace)
    options=SimpleNamespace(host_prefix=prefix); native=SimpleNamespace(host={'os':'NetBSD'},path='/selected/bin')
    result=build.platform_protoc_inputs(options, {'native_generator_runtime':runtime}, native, protoc, {str(contents):'hash'})
    assert result == [str(protoc),str(contents)] and called[0][0][3] == [str(package)]
print('PASS: ELF protoc delegates exact selected package set to SDK')
